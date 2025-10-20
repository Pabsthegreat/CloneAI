"""
Voice session orchestration: keyboard input + speech recognition + speech output.
"""

from __future__ import annotations

import difflib
import os
import queue
import re
import subprocess
import sys
import threading
import time
from typing import Iterable, Optional, Tuple

from .speaker import TextToSpeechEngine
from agent.tools.ollama_client import run_ollama
from agent.config.runtime import LOCAL_PLANNER
from .recognizer import (
    SpeechRecognizer,
    SpeechRecognizerError,
    SpeechRecognizerUnavailable,
)


class VoiceModeSession:
    """Run an interactive conversational loop with hotword detection."""

    def __init__(self, hotword: str = "nebula", aliases: Optional[Iterable[str]] = None) -> None:
        self.primary_hotword = hotword.lower()
        alias_set = {self.primary_hotword}
        if aliases:
            alias_set.update(a.strip().lower() for a in aliases if a and a.strip())
        self._hotwords = sorted(alias_set)
        self._active_event = threading.Event()
        self._active_event.set()
        self._command_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._speaker = TextToSpeechEngine()
        self._recognizer_error: Optional[str] = None
        self._recognizer_notice: Optional[str] = None
        self._listening_gate = threading.Event()
        self._listening_gate.set()
        # Speech output preferences
        self._speak_full: bool = os.getenv("CLAI_VOICE_SPEAK_FULL", "true").lower() in {"1", "true", "yes", "on"}
        self._last_tts_at: float = 0.0
        # Chat mode state
        self._chat_mode: bool = False
        self._chat_history: list[tuple[str, str]] = []  # list of (role, text)
        self._chat_max_turns: int = 10  # user+assistant messages total
        self._chat_require_hotword: bool = os.getenv("CLAI_CHAT_REQUIRE_HOTWORD", "1").lower() in {"1", "true", "yes", "on"}

        try:
            self._speech_recognizer = SpeechRecognizer()
        except SpeechRecognizerUnavailable as exc:
            self._speech_recognizer = None
            self._recognizer_error = str(exc)
        except SpeechRecognizerError as exc:
            self._speech_recognizer = None
            self._recognizer_error = str(exc)
        else:
            self._recognizer_notice = getattr(self._speech_recognizer, "status_notice", None)
            self._threads.append(
                threading.Thread(
                    target=self._voice_listener_loop,
                    name="VoiceListener",
                    daemon=True,
                )
            )

        self._typing_enabled = os.getenv("CLAI_VOICE_ENABLE_TYPING", "false").lower() in {"1", "true", "yes", "on"}
        if self._typing_enabled:
            self._threads.append(
                threading.Thread(
                    target=self._keyboard_listener_loop,
                    name="KeyboardListener",
                    daemon=True,
                )
            )

    @property
    def is_active(self) -> bool:
        return self._active_event.is_set()

    def notify_already_active(self) -> None:
        """Inform the user that a session is already running."""
        hotword_label = " / ".join(h.upper() for h in self._hotwords)
        print(
            f"\n🔊 Voice mode already active. Say '{hotword_label} shutdown' or type 'shutdown' to exit.\n"
        )

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._active_event.clear()
        self._listening_gate.set()
        # Wake up queue consumers
        self._command_queue.put(("control", "shutdown"))

    def join_threads(self, timeout: float = 1.0) -> None:
        """Join worker threads with a small timeout to release mic promptly."""
        deadline = time.time() + max(0.0, timeout)
        for t in list(self._threads):
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                t.join(timeout=remaining)
            except Exception:
                pass

    def run(self) -> None:
        """Run the session until shutdown is requested."""
        hotword_label = " / ".join(h.upper() for h in self._hotwords)
        print(f"\n🎙️  Voice mode activated. Say '{hotword_label} <instruction>' to talk to your agent.")
        print(f"     Say '{hotword_label} shutdown' or type 'shutdown' to exit voice mode.")
        if self._typing_enabled:
            print("     You can still type instructions—press Enter on an empty line to skip.\n")
        else:
            print("     (Typing disabled) Set CLAI_VOICE_ENABLE_TYPING=true to type commands while listening.\n")
        greeting = "Hello, I'm Nebula. I'll be your assistant today."
        print(f"🤖 {greeting}")
        self._speak_safely(greeting, force=True)
        if not getattr(self._speaker, "available", False):
            print("ℹ️  Text-to-speech unavailable:", getattr(self._speaker, "status", "unknown"))
            print("   On macOS, try: pip install pyobjc pyttsx3")
            print("   On Linux, try: sudo apt-get install espeak && pip install pyttsx3")

        if self._recognizer_error:
            print("⚠️  Speech recognition not available:", self._recognizer_error)
            print("     Voice mode will listen for typed instructions only.\n")
        elif self._recognizer_notice:
            print(f"ℹ️  {self._recognizer_notice}\n")

        for thread in self._threads:
            thread.start()

        while self.is_active:
            try:
                source, command = self._command_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            normalized = command.strip()
            if not normalized:
                continue

            if source == "system":
                print(f"\n⚠️  {normalized}")
                continue

            if normalized.lower() in {"shutdown", "exit", "quit"}:
                self._speak_safely("Shutting down voice mode. Talk soon!")
                break

            self._handle_instruction(normalized, source)

        self._active_event.clear()

        # Allow listener threads to exit gracefully
        time.sleep(0.2)

    # --------------------------------------------------------------------- #
    # Listener loops
    # --------------------------------------------------------------------- #

    def _keyboard_listener_loop(self) -> None:
        """Capture typed instructions without blocking the main loop."""
        prompt = "Type instruction (or 'shutdown' to exit): "
        while self.is_active:
            try:
                typed = input(prompt)
            except EOFError:
                # Terminal closed
                self.request_shutdown()
                return

            if typed is None:
                continue

            self._command_queue.put(("keyboard", typed.strip()))

    def _voice_listener_loop(self) -> None:
        """Continuously listen for speech and post commands on the queue."""
        assert self._speech_recognizer is not None
        # Warm up microphone for ambient noise calibration
        try:
            self._speech_recognizer.calibrate()
        except SpeechRecognizerError as exc:
            self._command_queue.put(("system", f"Speech recognizer calibration failed: {exc}"))
            return

        while self.is_active:
            self._listening_gate.wait()
            if not self.is_active:
                break

            phrase = self._speech_recognizer.listen_phrase()
            if not phrase:
                continue

            # Ignore input for a short cooldown window after speaking
            try:
                import time as _t
                if (_t.time() - self._last_tts_at) < float(os.getenv("CLAI_VOICE_TTS_COOLDOWN", "1.2")):
                    print("   ↳ Ignored (recent TTS playback)")
                    continue
            except Exception:
                pass

            print(f"\n🎤 Heard (raw): {phrase}")

            command = self._extract_command_from_phrase(phrase)
            if command is None:
                if self._chat_mode and not self._chat_require_hotword:
                    # In chat mode, accept free-form speech without hotword
                    command = phrase.strip()
                else:
                    print("   ↳ No hotword detected; ignoring.")
                    continue

            print(f"   ↳ Parsed command: {command}")
            self._command_queue.put(("voice", command))

    # --------------------------------------------------------------------- #
    # Command processing
    # --------------------------------------------------------------------- #

    def _extract_command_from_phrase(self, phrase: str) -> Optional[str]:
        text = phrase.lower().strip()
        if not text:
            return None

        if "shutdown" in text and self._contains_hotword(text):
            return "shutdown"

        tokens_original = re.split(r"[\s,:]+", phrase.strip())
        tokens_lower = [token.lower() for token in tokens_original]

        for idx, token in enumerate(tokens_lower):
            if self._is_hotword_token(token):
                remainder = " ".join(tokens_original[idx + 1 :]).strip()
                if not remainder:
                    return None
                return remainder

        return None

    def _contains_hotword(self, text: str) -> bool:
        return any(hotword in text for hotword in self._hotwords)

    def _is_hotword_token(self, token: str) -> bool:
        token_clean = re.sub(r"[^a-z0-9]", "", token)
        candidates = {token, token_clean}
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in self._hotwords:
                return True
            for hotword in self._hotwords:
                if difflib.SequenceMatcher(None, candidate, hotword).ratio() >= 0.8:
                    return True
        return False

    def _handle_instruction(self, instruction: str, source: str) -> None:
        print(f"\n🎧 {source.capitalize()} instruction -> {instruction}")

        # Handle chat-mode toggles first
        if self._maybe_toggle_chat_mode(instruction):
            return

        if self._chat_mode:
            # Treat instruction as a chat message; do not call tiered planner.
            self._pause_listening()
            try:
                response = self._chat_respond(instruction)
            finally:
                self._resume_listening()
            if response:
                print(response)
                tts_text = response if self._speak_full else self._speakable_snippet(response, long_form=True)
                self._speak_safely(tts_text)
            return

        # Normal confirm → execute via tiered planner
        confirmed, final_instruction = self._confirm_instruction(instruction)
        if not confirmed:
            print("   ↳ Command cancelled.")
            return

        print(f"   ↳ Executing via `clai auto \"{final_instruction}\" --run`")
        self._pause_listening()
        try:
            output = self._run_auto_instruction(final_instruction)
        finally:
            self._resume_listening()
        cleaned = self._strip_ansi(output).strip()

        if cleaned:
            print(cleaned)
            tts_text = cleaned if self._speak_full else self._speakable_snippet(cleaned)
            self._speak_safely(tts_text)

    def _speakable_snippet(self, text: str, *, long_form: bool = False) -> str:
        """Pick a compact chunk to speak to avoid reading long logs verbatim."""
        if not text:
            return ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return text.strip()
        # Drop obvious CLI noise
        filtered = [
            ln for ln in lines
            if not ln.startswith(("System:", "🧠", "📊", "🚀", "▶", "📋", "🤖", "✓", "ℹ️", "❌", "✅"))
        ]
        if not filtered:
            filtered = lines
        candidate = " ".join(filtered) if long_form else filtered[0]
        max_len = 400 if long_form else 220
        if len(candidate) > max_len:
            candidate = candidate[: max_len - 1].rsplit(" ", 1)[0] + "…"
        return candidate

    # ---------------------------- Chat Mode ---------------------------- #
    def _maybe_toggle_chat_mode(self, instruction: str) -> bool:
        text = instruction.strip().lower()
        if not self._chat_mode and any(k in text for k in ["let's chat", "love to chat", "start chat", "chat mode", "let us chat", "i'd love to chat", "talk with me", "let's talk"]):
            self._chat_mode = True
            self._chat_history.clear()
            msg = "Chat mode enabled. I won't execute commands; say 'end chat' to exit."
            print(f"🤖 {msg}")
            self._speak_safely(msg)
            try:
                if self._speech_recognizer:
                    self._speech_recognizer.set_mode("dictation")
            except Exception:
                pass
            return True
        if self._chat_mode and any(k in text for k in ["end chat", "exit chat", "stop chatting", "finish chat", "stop chat", "done chatting"]):
            self._chat_mode = False
            msg = "Exiting chat mode."
            print(f"🤖 {msg}")
            self._speak_safely(msg)
            try:
                if self._speech_recognizer:
                    self._speech_recognizer.set_mode("balanced")
            except Exception:
                pass
            return True
        return False

    def _chat_respond(self, user_text: str) -> Optional[str]:
        # Maintain ring buffer of last 10 messages
        def push(role: str, content: str) -> None:
            self._chat_history.append((role, content))
            if len(self._chat_history) > self._chat_max_turns:
                # Drop the oldest two messages to preserve back-and-forth shape when possible
                # but ensure size <= max
                while len(self._chat_history) > self._chat_max_turns:
                    self._chat_history.pop(0)

        push("user", user_text)
        prompt = self._build_chat_prompt()
        # Use local deterministic profile (same as planner by default)
        response = run_ollama(prompt, profile=LOCAL_PLANNER)
        if not response:
            return "(No response from the local model)"
        push("assistant", response)
        return response

    def _build_chat_prompt(self) -> str:
        system = (
            "You are Nebula, a concise and friendly local assistant. "
            "Respond helpfully in English. Keep replies short unless asked to elaborate. "
            "Use plain text only: no emojis, no emoticons, no decorative symbols, and avoid Markdown. "
            "Prefer simple ASCII punctuation.\n\n"
        )
        lines: list[str] = [system]
        for role, content in self._chat_history[-self._chat_max_turns :]:
            prefix = "User" if role == "user" else "Assistant"
            lines.append(f"{prefix}: {content}")
        lines.append("Assistant:")
        return "\n".join(lines)

    def _confirm_instruction(self, instruction: str) -> Tuple[bool, str]:
        """Allow inline editing/confirmation before running the workflow."""
        current = instruction.strip()
        if not current:
            return False, current

        while True:
            edit_prompt = (
                "Edit instruction (press Enter to keep current):\n"
                f"   Current → {current}\n> "
            )
            edited = input(edit_prompt)
            if edited is not None:
                edited = edited.strip()
                if edited:
                    current = edited

            confirm = input(f"Execute this instruction? [Y/n]: ")
            if confirm is None:
                return False, current

            decision = confirm.strip().lower()
            if decision in {"", "y", "yes"}:
                return True, current
            if decision in {"n", "no", "cancel"}:
                return False, current
            # Any other input repeats loop for further editing

    def _pause_listening(self) -> None:
        self._listening_gate.clear()

    def _resume_listening(self) -> None:
        self._listening_gate.set()

    def _run_auto_instruction(self, instruction: str) -> str:
        """Execute the `clai auto` command and stream its output live."""
        command = [sys.executable, "-m", "agent.cli", "auto", instruction, "--run"]

        env = os.environ.copy()
        env["CLAI_VOICE_MODE"] = "1"

        try:
            process = subprocess.Popen(
                command,
                cwd=os.getcwd(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            return f"❌ Failed to invoke agent CLI: {exc}"

        assert process.stdout is not None
        output_lines: list[str] = []
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)

        return_code = process.wait()
        aggregated = "".join(output_lines)
        if return_code != 0:
            return aggregated or f"❌ Voice command failed (exit code {return_code})."
        return aggregated

    def _speak(self, text: str, force: bool = False) -> None:
        """Use text-to-speech if available."""
        self._speaker.speak(text, force=force)

    def _speak_safely(self, text: str, force: bool = False) -> None:
        """Speak while temporarily pausing the listener to avoid self-capture."""
        if not text:
            return
        was_listening = self._listening_gate.is_set()
        if was_listening:
            self._pause_listening()
        try:
            self._speaker.speak(text, force=force)
            # record last speech time for cooldown filtering
            import time as _t
            self._last_tts_at = _t.time()
        finally:
            if was_listening:
                # Optional post-speech delay to let audio drain from mic path
                try:
                    import time as _t
                    _delay = float(os.getenv("CLAI_TTS_POST_DELAY", "0.15"))
                    if _delay > 0:
                        _t.sleep(min(_delay, 1.0))
                except Exception:
                    pass
                self._resume_listening()

    @staticmethod
    def _strip_ansi(text: str) -> str:
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text)

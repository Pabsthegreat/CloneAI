"""Text-to-speech helper with cross-platform backends (Coqui, pyttsx3, macOS `say`)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import threading
import re
import unicodedata
from typing import Optional

import numpy as np

# Optional Coqui TTS import (supports both legacy `TTS` and new `coqui-tts` packages)
try:  # pragma: no cover - optional dependency
    from TTS.api import TTS as CoquiTTS
except Exception:  # pragma: no cover - fallback to new package name
    try:
        from coqui_tts.api import TTS as CoquiTTS  # type: ignore
    except Exception:
        CoquiTTS = None  # type: ignore

try:  # Optional sounddevice for playback
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency
    sd = None  # type: ignore


class TextToSpeechEngine:
    """Multi-backend TTS helper preferring Coqui for true cross-platform support."""

    def __init__(self, voice_preference: Optional[str] = None) -> None:
        self._engine = None
        self._lock = threading.Lock()
        self._voice_preference = voice_preference or os.getenv("CLAI_TTS_VOICE")
        self._status_reason: Optional[str] = None
        self._backend = "none"
        self._rate = int(os.getenv("CLAI_VOICE_RATE", "220"))
        self._coqui = None
        self._coqui_sample_rate = 22050
        self._coqui_speaker = os.getenv("CLAI_COQUI_TTS_SPEAKER")
        self._coqui_language = os.getenv("CLAI_COQUI_TTS_LANGUAGE")

        preferred_backend = os.getenv("CLAI_TTS_BACKEND", "auto").strip().lower()

        # Prefer Coqui for cross-platform voices unless explicitly disabled
        if preferred_backend in {"auto", "coqui"}:
            self._init_coqui_backend()

        # Try pyttsx3 unless explicitly overridden
        pyttsx3_init_ok = False
        if self._backend == "none" and preferred_backend in {"auto", "pyttsx3"}:
            try:
                import pyttsx3  # type: ignore
                self._pyttsx3 = pyttsx3
                try:
                    self._engine = pyttsx3.init()
                    pyttsx3_init_ok = True
                    self._backend = "pyttsx3"
                    if self._voice_preference:
                        self._configure_voice(self._voice_preference)
                    if isinstance(self._rate, int):
                        try:
                            self._engine.setProperty("rate", self._rate)
                        except Exception:
                            pass
                except Exception as exc:  # pragma: no cover - defensive
                    self._engine = None
                    self._status_reason = f"pyttsx3 init failed: {exc}"
            except ImportError:
                self._pyttsx3 = None  # type: ignore
                if preferred_backend == "pyttsx3":
                    self._status_reason = "pyttsx3 not installed"

        # Fallback to macOS 'say' if requested or pyttsx3 unavailable
        if (
            self._backend == "none"
            and preferred_backend in {"auto", "say"}
            and platform.system() == "Darwin"
        ):
            if shutil.which("say"):
                self._backend = "say"
                self._status_reason = None
            elif not pyttsx3_init_ok:
                self._status_reason = "No TTS backend available (Coqui/pyttsx3 missing and 'say' not found)"

    def _init_coqui_backend(self) -> None:
        """Attempt to initialize Coqui TTS backend."""

        if CoquiTTS is None or sd is None:
            missing = "Coqui TTS" if CoquiTTS is None else "sounddevice"
            self._status_reason = f"{missing} not installed"
            return

        model_name = os.getenv("CLAI_COQUI_TTS_MODEL", "tts_models/en/vctk/vits")
        try:
            self._coqui = CoquiTTS(model_name=model_name, progress_bar=False)
            self._backend = "coqui"
            self._status_reason = None
            # Some models expose synthesizer metadata
            self._coqui_sample_rate = getattr(
                getattr(self._coqui, "synthesizer", None),
                "output_sample_rate",
                22050,
            )
        except Exception as exc:  # pragma: no cover - heavy dependency
            self._coqui = None
            self._status_reason = f"Coqui init failed: {exc}"

    def speak(self, text: str, force: bool = False) -> None:
        """Speak the provided text if engine is available."""
        if not text:
            return
        prepared = self._prepare_text(text)

        if self._backend == "coqui" and self._coqui:
            if self._speak_with_coqui(prepared):
                return
            # If Coqui fails mid-session, fall back to other engines
            self._backend = "none"

        if self._backend == "pyttsx3" and self._engine:
            with self._lock:
                try:
                    self._engine.say(prepared)
                    self._engine.runAndWait()
                except Exception as exc:  # pragma: no cover - runtime guard
                    # Attempt fallback to 'say' if available
                    if platform.system() == "Darwin" and shutil.which("say"):
                        self._speak_via_say(prepared)
                    elif force:
                        print(f"(TTS failed) {prepared}  // {exc}")
            return

        if self._backend == "say":
            self._speak_via_say(prepared)
            return

        if force:
            print(f"(TTS missing) {prepared}")

    def _speak_via_say(self, text: str) -> None:
        args = ["say"]
        if self._voice_preference:
            args += ["-v", self._voice_preference]
        if isinstance(self._rate, int) and self._rate > 0:
            args += ["-r", str(self._rate)]
        try:
            subprocess.run(args + [text], check=False)
        except Exception:
            pass

    def _speak_with_coqui(self, text: str) -> bool:
        """Render speech using the Coqui TTS backend."""

        if not self._coqui or sd is None:
            return False

        try:
            audio = self._coqui.tts(
                text=text,
                speaker=self._coqui_speaker,
                language=self._coqui_language,
            )
            if isinstance(audio, list):
                audio = np.array(audio, dtype=np.float32)
            elif not isinstance(audio, np.ndarray):
                audio = np.asarray(audio, dtype=np.float32)

            if audio.ndim > 1:
                audio = np.squeeze(audio)

            if audio.size == 0:
                return False

            peak = float(np.max(np.abs(audio)))
            if peak > 0:
                audio = audio / peak

            sd.stop()
            sd.play(audio.astype(np.float32), samplerate=self._coqui_sample_rate)
            sd.wait()
            return True
        except Exception as exc:  # pragma: no cover - runtime guard
            self._status_reason = f"Coqui playback failed: {exc}"
            return False

    def _prepare_text(self, text: str) -> str:
        """Sanitize text for more reliable TTS (strip ANSI, emoji, odd control chars)."""
        sanitize = os.getenv("CLAI_TTS_SANITIZE", "true").lower() in {"1", "true", "yes", "on"}
        if not sanitize:
            return text

        # Remove ANSI escape codes
        ansi_re = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        s = ansi_re.sub("", text)

        # Replace common emojis with words (helps both pyttsx3 and say)
        replacements = {
            "🤖": "robot",
            "🧠": "brain",
            "📊": "chart",
            "🚀": "rocket",
            "▶": "play",
            "ℹ️": "info",
            "✅": "check",
            "❌": "error",
            "🔊": "speaker",
            "🎙️": "microphone",
            "🎧": "headphones",
            "🎤": "microphone",
            "🛑": "stop",
            "✓": "check",
        }
        for sym, word in replacements.items():
            s = s.replace(sym, f" {word} ")

        # Strip remaining emoji / pictographs (non-BMP and symbol categories)
        def _filter_char(ch: str) -> str:
            # Remove variation selectors and zero width joiners
            if ch in {"\u200d", "\ufe0f"}:
                return ""
            try:
                cat = unicodedata.category(ch)
            except Exception:
                return ""
            # Drop surrogate and control chars
            if cat.startswith("C"):
                return ""
            # Many emojis are Symbol, Other (So) and outside ASCII range
            if cat == "So" and ord(ch) > 127:
                return ""
            return ch

        s = "".join(_filter_char(c) for c in s)
        # Normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @property
    def available(self) -> bool:
        if self._backend == "coqui":
            return True
        if self._backend == "pyttsx3":
            return self._engine is not None
        if self._backend == "say":
            return True
        return False

    @property
    def status(self) -> str:
        backend_str = f"{self._backend}"
        return backend_str if self.available else (self._status_reason or "unavailable")

    def _configure_voice(self, preference: str) -> None:
        """Set a specific voice if available."""
        if not self._engine:
            return

        voices = self._engine.getProperty("voices")
        preference_lower = preference.lower()
        for voice in voices:
            voice_id = getattr(voice, "id", "").lower()
            voice_name = getattr(voice, "name", "").lower()
            if preference_lower in voice_id or preference_lower in voice_name:
                self._engine.setProperty("voice", voice.id)
                break

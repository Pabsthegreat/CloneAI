# Voice Mode (Nebula)

This document explains CloneAI's end‑to‑end Voice Mode: the components involved, how audio flows through the system, activation/usage patterns, configuration via environment variables, platform prerequisites, and future scope.


## Overview

- Hotword‑activated, hands‑free assistant with optional chat mode
- Accurate, fully local speech‑to‑text via Whisper (faster‑whisper)
- Text‑to‑speech via pyttsx3 or native macOS `say` fallback
- Inline edit + confirmation before executing commands
- Planner output streams live; mic is paused while speaking to avoid echo
- Auto‑tuning selects sensible defaults per OS (macOS/Windows/Linux)

Activation:
- Start: `clai auto "activate voice mode"`
- Stop:  `clai auto "shutdown voice mode"` or say "NEBULA shutdown"

Default hotword: `NEBULA` with fuzzy matching and aliases (configurable).


## Architecture

- `agent/cli.py`
  - Detects “activate/shutdown voice mode” in `auto` and delegates to the voice manager.
  - Calls `agent/config/autotune.apply_runtime_autotune()` at startup to set platform‑tuned defaults (only if the env var isn’t already set by the user).

- `agent/voice/manager.py`
  - Singleton orchestrator; starts a `VoiceModeSession` with the configured hotword and optional aliases.
  - Gracefully shuts down on Ctrl+C and joins listener threads to release the mic quickly.

- `agent/voice/session.py`
  - The main loop. Coordinates microphone listener, keyboard input (optional), TTS playback, chat mode, confirmation/edit prompts, and launch of `clai auto` for command execution.
  - Uses a “listening gate” to pause the mic whenever we speak or run a command.
  - Adds a short post‑speech delay and a cooldown window to avoid the recognizer hearing Nebula’s voice.

- `agent/voice/recognizer.py`
  - Wraps the `speech_recognition` library for audio capture from the microphone.
  - Default backend: Whisper via local `faster-whisper` (no network). Optional fallbacks (Sphinx/Google) exist but are not the default.
  - Tunable timeouts and thresholds; supports runtime profiles (responsive | balanced | dictation).

- `agent/voice/transcriber.py`
  - Loads a shared `faster-whisper` model and transcribes raw PCM audio to text.
  - Resamples audio to 16 kHz as needed, supports beam search, VAD, and language selection.

- `agent/voice/speaker.py`
  - TTS helper. Prefers `pyttsx3` when available; on macOS falls back to the native `say` command for reliability.
  - Sanitizes ANSI codes and emojis/pictographs to prevent engine stalls.
  - Supports voice selection and speaking rate.

- `agent/tools/ollama_client.py`
  - Direct, deterministic invocation of the local Ollama CLI for chat responses (no planner).

- `agent/config/autotune.py`
  - Applies safe, OS‑specific defaults for env vars (only when the user hasn’t set them).


## Audio Pipeline

1) Hotword + capture
- Mic is calibrated briefly for ambient noise at session start.
- Recognizer listens and transcribes using local Whisper.
- Fuzzy hotword matching (e.g., “nebula/neba/neb” and near misses like “bought/bot”) maps to the primary hotword.

2) Confirmation
- After an intent is recognized, the session prompts the user to edit the text and confirm execution.
- If confirmed, Voice Mode launches `clai auto "<instruction>" --run` as a subprocess and streams output live to the terminal.

3) TTS playback and anti‑echo
- Before speaking, the mic is paused (gate closed), then resumes afterward with a short post‑speech delay.
- A cooldown window ignores mic input for ~1.2s by default after any TTS playback to prevent self‑capture.

4) Chat Mode (no planner)
- Utterances are sent directly to the local Ollama model with a ring‑buffer history of the last 10 messages (5 user/5 assistant).
- The system prompt requests plain ASCII text (no emojis) and concise answers.
- Chat mode can optionally require the hotword to reduce ambient triggers.


## Usage Patterns

- Start voice mode: `clai auto "activate voice mode"`
- Say: “Nebula, <instruction>” (e.g., “Nebula, tell me about the Maratha Empire”).
- Edit/Confirm: keep or change the text, then confirm to run.
- Watch tiered‑planner logs stream live, then hear the spoken summary (or full content).
- Enter chat: “Nebula, let’s chat” (or “chat mode”); speak naturally; “end chat” to exit.
- Stop voice mode: “Nebula shutdown” or `Ctrl+C` or `clai auto "shutdown voice mode"`.


## Platform Requirements

Microphone capture
- Python package: `SpeechRecognition`
- System library: PortAudio
- Python binding: `pyaudio`

Install tips (macOS):
- `brew install portaudio`
- `pip install pyaudio`

If `pyaudio` fails to build, ensure Xcode command‑line tools are available and PortAudio is installed first, then reinstall `pyaudio`.

Speech‑to‑Text (local)
- `faster-whisper` (model downloads on first use). Choose model/device via env vars.

Text‑to‑Speech
- `pyttsx3` (cross‑platform) or macOS `say` fallback
- macOS voice example: `export CLAI_TTS_BACKEND=say` and `export CLAI_TTS_VOICE=Samantha`


## Configuration (Environment Variables)

General
- `CLAI_VOICE_HOTWORD` — Primary hotword string (default: `nebula`).
- `CLAI_VOICE_HOTWORD_ALIASES` — Comma‑separated aliases (e.g., `neba,neb`).
- `CLAI_VOICE_ENABLE_TYPING` — Enable keyboard input thread (default: `false`).
- `CLAI_VOICE_MODE` — Internal flag for subprocess context (informational).

Auto‑tune (applied only if unset)
- macOS defaults: `CLAI_TTS_BACKEND=say`, `CLAI_VOICE_RATE=240`, `CLAI_VOICE_TTS_COOLDOWN=1.8`, `CLAI_TTS_POST_DELAY=0.20`, `CLAI_SPEECH_TIMEOUT_SECONDS=1.0`, `CLAI_SPEECH_PHRASE_LIMIT=8.0`, `CLAI_SPEECH_PAUSE_THRESHOLD=1.1`, `CLAI_SPEECH_NON_SPEAKING=0.6`.
- Windows/Linux defaults: favor `pyttsx3`, set moderate rate/cooldown/limits.

Recognizer (SpeechRecognition)
- `CLAI_SPEECH_BACKEND` — `whisper` (default) | `sphinx` | `google`.
- `CLAI_SPEECH_TIMEOUT_SECONDS` — Max wait for start of speech (default: 1.0).
- `CLAI_SPEECH_PHRASE_LIMIT` — Max continuous capture window (default: 8.0s; chat dictation raises this to ~12s).
- `CLAI_SPEECH_PAUSE_THRESHOLD` — Seconds of silence signaling phrase end (default: ~1.1).
- `CLAI_SPEECH_ENERGY_THRESHOLD` — Energy cutoff for speech detection (default: 200).
- `CLAI_SPEECH_NON_SPEAKING` — Non‑speaking duration baseline (default: ~0.6).
- `CLAI_SPEECH_PHRASE_MIN` — Minimum speech duration (default: ~0.2).

Recognizer runtime profiles (via `recognizer.set_mode()`)
- `responsive` — lower latencies, shorter phrases.
- `balanced` — default values.
- `dictation` — longer phrases/pauses (used in chat mode).
- Dictation overrides: `CLAI_SPEECH_PHRASE_LIMIT_DICTATION`, `CLAI_SPEECH_PAUSE_THRESHOLD_DICTATION`, `CLAI_SPEECH_NON_SPEAKING_DICTATION`, `CLAI_SPEECH_TIMEOUT_SECONDS_DICTATION`.
- Responsive overrides: `CLAI_SPEECH_PHRASE_LIMIT_RESPONSIVE`, `CLAI_SPEECH_PAUSE_THRESHOLD_RESPONSIVE`, `CLAI_SPEECH_NON_SPEAKING_RESPONSIVE`, `CLAI_SPEECH_TIMEOUT_SECONDS_RESPONSIVE`.

Whisper (faster‑whisper)
- `CLAI_WHISPER_MODEL` — Model size (e.g., `tiny`, `base`, `small`, `medium`, `large`; default `small`).
- `CLAI_WHISPER_DEVICE` — `cpu` | `cuda` | `auto` (default: `cpu`).
- `CLAI_WHISPER_COMPUTE` — Quantization/precision (default: `int8` on CPU, `int8_float16` otherwise).
- `CLAI_WHISPER_BEAM_SIZE` — Beam search size (default: 5).
- `CLAI_WHISPER_VAD` — Enable internal VAD (default: true).
- `CLAI_WHISPER_VAD_MIN_SILENCE_MS` — VAD minimum silence (default: 300 ms).
- `CLAI_WHISPER_LANGUAGE` — `en` (default) or `auto` for multilingual.

Chat Mode
- `CLAI_CHAT_REQUIRE_HOTWORD` — If true, requires hotword in chat mode (default: true via autotune to reduce ambient pickup).
- History size is fixed at 10 messages (5 user / 5 assistant) with FIFO replacement.

TTS (pyttsx3 or macOS say)
- `CLAI_TTS_BACKEND` — `auto` | `pyttsx3` | `say` (default: `say` on macOS, `pyttsx3` elsewhere).
- `CLAI_TTS_VOICE` — Preferred voice name (e.g., `Samantha`).
- `CLAI_VOICE_RATE` — Speaking rate (wpm; default ~220–240 depending on OS).
- `CLAI_TTS_SANITIZE` — Strip ANSI and emojis, normalize text (default: true).
- `CLAI_VOICE_SPEAK_FULL` — Speak full output (true) or short summary (false).
- Anti‑echo: `CLAI_VOICE_TTS_COOLDOWN` (seconds; default: ~1.2–1.8), `CLAI_TTS_POST_DELAY` (~0.15–0.20s).


## Developer Notes

- Debug prints
  - Recognizer logs raw text ("🎤 Heard (raw): …") and parsed commands.
  - The listener prints when an utterance is ignored due to recent TTS playback.

- Confirmation
  - Inline edit prompt, then a `Y/n` confirmation before launching the planner.
  - Only after confirm do we start the subprocess; mic stays paused during execution.

- Safety
  - Voice Mode does not change planner safety/guardrails; it merely supplies the instruction. Chat mode bypasses the planner entirely and talks to a local model.

- Cross‑platform
  - macOS uses `say` if pyttsx3 is unavailable or fails. Linux/Windows default to pyttsx3.


## Troubleshooting

- PyAudio build errors (macOS):
  - `brew install portaudio`, then `pip install pyaudio`.

- Microphone still “on” after abort:
  - We now join listener threads; any lingering indicator should clear within ~1–2s.
  - You can reduce phrase limit or increase timeouts via envs if you need more aggressive teardown.

- Self‑listening (echo):
  - TTS is spoken with the mic gate closed, then post‑delay + cooldown before listening resumes.
  - Increase `CLAI_VOICE_TTS_COOLDOWN` to ~1.8–2.0 if needed.


## Future Scope

- Push‑to‑talk and ASR VAD barge‑in
- Streaming TTS with incremental playback
- Noise suppression / echo cancellation
- Custom wake‑word model (Porcupine/Snowboy‑style) for lower false positives
- Diarization and multi‑speaker handling
- Richer chat memory and topic summaries
- Automatic language detection + per‑segment language routing

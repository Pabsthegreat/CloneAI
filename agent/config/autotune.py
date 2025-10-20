from __future__ import annotations

import os
import platform
import shutil
from typing import Dict


def _set_default(env: str, value: str, changes: Dict[str, str]) -> None:
    if os.getenv(env) is None:
        os.environ[env] = value
        changes[env] = value


def apply_runtime_autotune() -> Dict[str, str]:
    """
    Set sensible default environment variables based on the host system.
    Only applies values that are not already explicitly set by the user.

    Returns a dict of env vars that were set by this function for visibility/testing.
    """
    changes: Dict[str, str] = {}
    system = platform.system()

    # General voice/chat safety defaults
    _set_default("CLAI_CHAT_REQUIRE_HOTWORD", "true", changes)
    _set_default("CLAI_VOICE_SPEAK_FULL", "true", changes)
    _set_default("CLAI_TTS_SANITIZE", "true", changes)
    _set_default("CLAI_WHISPER_LANGUAGE", "en", changes)

    if system == "Darwin":
        # Prefer native macOS speech for reliability and speed
        if shutil.which("say"):
            _set_default("CLAI_TTS_BACKEND", "say", changes)
            _set_default("CLAI_VOICE_RATE", "240", changes)
        else:
            _set_default("CLAI_TTS_BACKEND", "pyttsx3", changes)
            _set_default("CLAI_VOICE_RATE", "230", changes)
        _set_default("CLAI_VOICE_TTS_COOLDOWN", "1.8", changes)
        _set_default("CLAI_TTS_POST_DELAY", "0.20", changes)
        # Recognition responsiveness (balanced)
        _set_default("CLAI_SPEECH_TIMEOUT_SECONDS", "1.0", changes)
        _set_default("CLAI_SPEECH_PHRASE_LIMIT", "8.0", changes)
        _set_default("CLAI_SPEECH_PAUSE_THRESHOLD", "1.1", changes)
        _set_default("CLAI_SPEECH_NON_SPEAKING", "0.6", changes)
    elif system == "Windows":
        _set_default("CLAI_TTS_BACKEND", "pyttsx3", changes)
        _set_default("CLAI_VOICE_RATE", "210", changes)
        _set_default("CLAI_VOICE_TTS_COOLDOWN", "1.4", changes)
        _set_default("CLAI_TTS_POST_DELAY", "0.10", changes)
        _set_default("CLAI_SPEECH_TIMEOUT_SECONDS", "1.0", changes)
        _set_default("CLAI_SPEECH_PHRASE_LIMIT", "3.5", changes)
    else:
        # Linux or others
        _set_default("CLAI_TTS_BACKEND", "pyttsx3", changes)
        _set_default("CLAI_VOICE_RATE", "220", changes)
        _set_default("CLAI_VOICE_TTS_COOLDOWN", "1.6", changes)
        _set_default("CLAI_TTS_POST_DELAY", "0.12", changes)
        _set_default("CLAI_SPEECH_TIMEOUT_SECONDS", "1.0", changes)
        _set_default("CLAI_SPEECH_PHRASE_LIMIT", "3.5", changes)

    return changes


__all__ = ["apply_runtime_autotune"]

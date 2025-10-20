"""
Speech recognition utilities wrapping optional third-party libraries.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
import re
import sys
import types
from typing import Optional

from .transcriber import (
    WhisperTranscriber,
    WhisperTranscriberError,
    WhisperTranscriberUnavailable,
)


class SpeechRecognizerError(RuntimeError):
    """Base error for recognizer issues."""


class SpeechRecognizerUnavailable(SpeechRecognizerError):
    """Raised when speech recognition dependencies are missing."""


@dataclass
class RecognizerConfig:
    backend: str = "whisper"  # default to high-accuracy local backend
    timeout_seconds: float = 1.0
    phrase_time_limit: float = 8.0


class SpeechRecognizer:
    """Thin wrapper around the `speech_recognition` package."""

    def __init__(self, config: Optional[RecognizerConfig] = None) -> None:
        _ensure_distutils()
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError as exc:
            raise SpeechRecognizerUnavailable(
                "Install 'SpeechRecognition' (and optionally 'pocketsphinx') to enable voice input."
            ) from exc

        self._sr = sr
        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        pause_threshold = float(os.getenv("CLAI_SPEECH_PAUSE_THRESHOLD", "1.1"))
        energy_threshold = int(os.getenv("CLAI_SPEECH_ENERGY_THRESHOLD", "200"))
        non_speaking = float(os.getenv("CLAI_SPEECH_NON_SPEAKING", "0.6"))
        phrase_min = float(os.getenv("CLAI_SPEECH_PHRASE_MIN", "0.2"))
        self._recognizer.pause_threshold = pause_threshold
        self._recognizer.energy_threshold = energy_threshold
        try:
            self._recognizer.non_speaking_duration = non_speaking
        except Exception:
            pass
        try:
            self._recognizer.phrase_threshold = phrase_min
        except Exception:
            pass
        self.status_notice: Optional[str] = None
        self._calibration_duration = float(os.getenv("CLAI_SPEECH_CALIBRATION_DURATION", "1.5"))

        try:
            self._microphone = sr.Microphone()
        except OSError as exc:
            raise SpeechRecognizerError(f"Microphone not available: {exc}") from exc
        except AttributeError as exc:
            raise SpeechRecognizerError(
                "PyAudio (PortAudio bindings) not installed; install via 'pip install pyaudio' "
                "after installing PortAudio system libraries."
            ) from exc
        except ModuleNotFoundError as exc:
            missing = getattr(exc, "name", "distutils")
            raise SpeechRecognizerError(
                f"Missing Python module '{missing}'. Install the latest 'setuptools' package or "
                "upgrade SpeechRecognition to a version compatible with Python 3.12."
            ) from exc

        cfg = config or RecognizerConfig()
        # Allow environment overrides for responsiveness
        try:
            ts = os.getenv("CLAI_SPEECH_TIMEOUT_SECONDS")
            if ts is not None:
                cfg.timeout_seconds = float(ts)
        except Exception:
            pass
        try:
            ptl = os.getenv("CLAI_SPEECH_PHRASE_LIMIT")
            if ptl is not None:
                cfg.phrase_time_limit = float(ptl)
        except Exception:
            pass
        env_backend = os.getenv("CLAI_SPEECH_BACKEND")
        if env_backend:
            cfg.backend = env_backend

        self._config = cfg
        self._whisper_transcriber: Optional[WhisperTranscriber] = None
        self._normalise_backend()

    def set_mode(self, mode: str) -> None:
        """Adjust capture parameters at runtime (responsive|balanced|dictation)."""
        m = (mode or "").lower()
        if m == "dictation":
            try:
                self._recognizer.pause_threshold = float(os.getenv("CLAI_SPEECH_PAUSE_THRESHOLD_DICTATION", "1.3"))
            except Exception:
                pass
            try:
                self._recognizer.non_speaking_duration = float(os.getenv("CLAI_SPEECH_NON_SPEAKING_DICTATION", "0.7"))
            except Exception:
                pass
            self._config.phrase_time_limit = float(os.getenv("CLAI_SPEECH_PHRASE_LIMIT_DICTATION", "12.0"))
            self._config.timeout_seconds = float(os.getenv("CLAI_SPEECH_TIMEOUT_SECONDS_DICTATION", "1.2"))
            return
        if m == "responsive":
            try:
                self._recognizer.pause_threshold = float(os.getenv("CLAI_SPEECH_PAUSE_THRESHOLD_RESPONSIVE", "0.8"))
            except Exception:
                pass
            try:
                self._recognizer.non_speaking_duration = float(os.getenv("CLAI_SPEECH_NON_SPEAKING_RESPONSIVE", "0.5"))
            except Exception:
                pass
            self._config.phrase_time_limit = float(os.getenv("CLAI_SPEECH_PHRASE_LIMIT_RESPONSIVE", "3.0"))
            self._config.timeout_seconds = float(os.getenv("CLAI_SPEECH_TIMEOUT_SECONDS_RESPONSIVE", "0.8"))
            return
        # balanced/default
        try:
            self._recognizer.pause_threshold = float(os.getenv("CLAI_SPEECH_PAUSE_THRESHOLD", "1.1"))
        except Exception:
            pass
        try:
            self._recognizer.non_speaking_duration = float(os.getenv("CLAI_SPEECH_NON_SPEAKING", "0.6"))
        except Exception:
            pass
        self._config.phrase_time_limit = float(os.getenv("CLAI_SPEECH_PHRASE_LIMIT", "8.0"))
        self._config.timeout_seconds = float(os.getenv("CLAI_SPEECH_TIMEOUT_SECONDS", "1.0"))

    def calibrate(self) -> None:
        """Adjust for ambient noise."""
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=self._calibration_duration)

    def listen_phrase(self) -> Optional[str]:
        """Listen for a phrase and return recognized text."""
        with self._microphone as source:
            try:
                audio = self._recognizer.listen(
                    source,
                    timeout=self._config.timeout_seconds,
                    phrase_time_limit=self._config.phrase_time_limit,
                )
            except self._sr.WaitTimeoutError:
                return None

        try:
            backend = self._config.backend
            if backend == "whisper":
                if not self._whisper_transcriber:
                    raise SpeechRecognizerError("Whisper backend not initialised.")
                try:
                    return self._whisper_transcriber.transcribe(audio.frame_data, audio.sample_rate)
                except WhisperTranscriberError as exc:
                    raise SpeechRecognizerError(f"Whisper transcription failed: {exc}") from exc
            if backend == "sphinx":
                return self._recognizer.recognize_sphinx(audio)
            # Fall back to Google Web Speech API (requires internet)
            return self._recognizer.recognize_google(audio)
        except self._sr.UnknownValueError:
            return None
        except self._sr.RequestError as exc:
            raise SpeechRecognizerError(f"Speech recognition request failed: {exc}") from exc

    def _normalise_backend(self) -> None:
        """Ensure an operable backend is configured, falling back when necessary."""
        backend = (self._config.backend or "").lower()
        self._config.backend = backend or "whisper"

        if backend == "whisper":
            try:
                self._whisper_transcriber = WhisperTranscriber.instance()
                self.status_notice = self._whisper_transcriber.status_message
            except WhisperTranscriberUnavailable as exc:
                raise SpeechRecognizerError(str(exc)) from exc
            except WhisperTranscriberError as exc:
                raise SpeechRecognizerError(f"Failed to initialise Whisper backend: {exc}") from exc
            return

        if backend != "sphinx":
            return

        if not hasattr(self._recognizer, "recognize_sphinx"):
            self.status_notice = (
                "Sphinx backend unavailable in SpeechRecognition; using Google Web Speech API instead."
            )
            self._config.backend = "google"
            return

        try:
            import pocketsphinx  # type: ignore # noqa: F401
        except ImportError:
            self.status_notice = (
                "PocketSphinx not installed. Falling back to Google Web Speech API. "
                "Install via 'pip install pocketsphinx' for offline recognition."
            )
            self._config.backend = "google"


def _ensure_distutils() -> None:
    """
    Provide a minimal distutils.version.LooseVersion implementation for Python 3.12+.

    SpeechRecognition still imports distutils.version, which was removed from the standard
    library in Python 3.12. Creating a lightweight stub keeps compatibility without forcing
    users to install legacy packages.
    """
    if "distutils.version" in sys.modules:
        return

    try:
        import distutils  # type: ignore
    except ModuleNotFoundError:
        pass
    else:
        # If distutils exists but version submodule is missing, fall through to stub.
        if hasattr(distutils, "version"):
            sys.modules["distutils"] = distutils  # ensure canonical entry
            sys.modules["distutils.version"] = distutils.version  # type: ignore[attr-defined]
            return

    def _parse_version(value: str) -> tuple:
        parts = re.split(r"(\d+)", value)
        parsed = []
        for part in parts:
            if not part:
                continue
            parsed.append(int(part) if part.isdigit() else part)
        return tuple(parsed)

    class LooseVersion:
        def __init__(self, version: str) -> None:
            self.version = str(version)
            self._key = _parse_version(self.version)

        def __repr__(self) -> str:
            return f"LooseVersion('{self.version}')"

        def _coerce_other(self, other: object) -> tuple:
            if isinstance(other, LooseVersion):
                return other._key
            return _parse_version(str(other))

        def __lt__(self, other: object) -> bool:
            return self._key < self._coerce_other(other)

        def __le__(self, other: object) -> bool:
            return self._key <= self._coerce_other(other)

        def __eq__(self, other: object) -> bool:
            return self._key == self._coerce_other(other)

        def __ne__(self, other: object) -> bool:
            return self._key != self._coerce_other(other)

        def __gt__(self, other: object) -> bool:
            return self._key > self._coerce_other(other)

        def __ge__(self, other: object) -> bool:
            return self._key >= self._coerce_other(other)

    distutils_module = types.ModuleType("distutils")
    version_module = types.ModuleType("distutils.version")
    version_module.LooseVersion = LooseVersion  # type: ignore[attr-defined]

    distutils_module.version = version_module  # type: ignore[attr-defined]

    sys.modules["distutils"] = distutils_module
    sys.modules["distutils.version"] = version_module

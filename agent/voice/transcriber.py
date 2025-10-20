"""Utilities for high-accuracy local speech transcription using Whisper."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np


class WhisperTranscriberError(RuntimeError):
    """Generic error during Whisper transcription."""


class WhisperTranscriberUnavailable(WhisperTranscriberError):
    """Raised when required Whisper dependencies are missing."""


@dataclass(frozen=True)
class WhisperConfig:
    model_size: str
    device: str
    compute_type: str
    beam_size: int
    vad_filter: bool
    vad_min_silence_ms: int
    language: Optional[str]


class WhisperTranscriber:
    """Singleton-style loader for faster-whisper models."""

    _instance: Optional["WhisperTranscriber"] = None
    _instance_lock = threading.Lock()

    def __init__(self, config: WhisperConfig) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise WhisperTranscriberUnavailable(
                "Install 'faster-whisper' (and ensure compatible CTranslate2 binaries) to enable local transcription."
            ) from exc

        self._config = config
        self._model = WhisperModel(
            config.model_size,
            device=config.device,
            compute_type=config.compute_type,
        )
        self._status = (
            f"Whisper model '{config.model_size}' loaded locally on {config.device} ({config.compute_type})."
        )

    @classmethod
    def instance(cls) -> "WhisperTranscriber":
        with cls._instance_lock:
            if cls._instance is None:
                cfg = cls._build_config()
                cls._instance = cls(cfg)
        return cls._instance

    @classmethod
    def _build_config(cls) -> WhisperConfig:
        model = os.getenv("CLAI_WHISPER_MODEL", "small")
        device = os.getenv("CLAI_WHISPER_DEVICE", "cpu")
        compute = os.getenv("CLAI_WHISPER_COMPUTE", "int8_float16" if device != "cpu" else "int8")
        beam_size = int(os.getenv("CLAI_WHISPER_BEAM_SIZE", "5"))
        vad_filter = os.getenv("CLAI_WHISPER_VAD", "true").lower() in {"1", "true", "yes", "on"}
        vad_min_silence = int(os.getenv("CLAI_WHISPER_VAD_MIN_SILENCE_MS", "300"))
        language = os.getenv("CLAI_WHISPER_LANGUAGE", "en")
        if language:
            language = language.strip()
            if language.lower() in {"auto", "default"}:
                language = None
        else:
            language = "en"
        return WhisperConfig(
            model_size=model,
            device=device,
            compute_type=compute,
            beam_size=beam_size,
            vad_filter=vad_filter,
            vad_min_silence_ms=vad_min_silence,
            language=language,
        )

    @property
    def status_message(self) -> str:
        return self._status

    def transcribe(self, audio_frame_data: bytes, sample_rate: int) -> str:
        """Run Whisper on raw PCM audio captured by speech_recognition."""
        if not audio_frame_data:
            return ""

        audio_np = np.frombuffer(audio_frame_data, dtype=np.int16).astype(np.float32) / 32768.0

        target_sr = 16000
        if sample_rate and sample_rate != target_sr and len(audio_np) > 0:
            # Simple linear resample to match Whisper expectations.
            duration = len(audio_np) / sample_rate
            new_length = int(duration * target_sr)
            if new_length > 0:
                audio_np = np.interp(
                    np.linspace(0, len(audio_np), new_length, endpoint=False),
                    np.arange(len(audio_np)),
                    audio_np,
                ).astype(np.float32)

        segments, _ = self._model.transcribe(
            audio_np,
            beam_size=self._config.beam_size,
            vad_filter=self._config.vad_filter,
            vad_parameters={"min_silence_duration_ms": self._config.vad_min_silence_ms},
            language=self._config.language,
        )

        text_parts = [segment.text.strip() for segment in segments if segment.text]
        return " ".join(text_parts).strip()

"""
Voice mode manager responsible for orchestrating conversational sessions.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from .session import VoiceModeSession


class VoiceModeManager:
    """Singleton-style manager for activating conversational voice sessions."""

    _instance_lock = threading.Lock()
    _instance: Optional["VoiceModeManager"] = None

    def __init__(self) -> None:
        self._session: Optional[VoiceModeSession] = None
        self._session_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "VoiceModeManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def activate(self, hotword: str = "nebula") -> None:
        """
        Start a voice session if one is not already active.

        Blocks until the session completes (e.g. user says "CLAI shutdown").
        """
        configured_hotword = os.getenv("CLAI_VOICE_HOTWORD", hotword)
        aliases_env = os.getenv("CLAI_VOICE_HOTWORD_ALIASES", "")
        hotword_aliases = [alias.strip().lower() for alias in aliases_env.split(",") if alias.strip()]
        with self._session_lock:
            if self._session and self._session.is_active:
                # Session already running; surface info and return.
                self._session.notify_already_active()
                return

            self._session = VoiceModeSession(hotword=configured_hotword, aliases=hotword_aliases)

        try:
            self._session.run()
        except KeyboardInterrupt:
            # Gracefully stop session on Ctrl+C
            with self._session_lock:
                if self._session:
                    self._session.request_shutdown()
                    self._session.join_threads(timeout=2.0)
        finally:
            # Ensure threads are cleaned up and session released
            with self._session_lock:
                if self._session:
                    self._session.join_threads(timeout=1.0)
                self._session = None

    def deactivate(self) -> None:
        """Signal the current session (if any) to stop."""
        with self._session_lock:
            if self._session:
                self._session.request_shutdown()

    @property
    def is_active(self) -> bool:
        with self._session_lock:
            return bool(self._session and self._session.is_active)


def get_voice_manager() -> VoiceModeManager:
    """Convenience accessor for the shared voice mode manager."""
    return VoiceModeManager.instance()

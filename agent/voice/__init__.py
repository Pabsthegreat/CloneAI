"""
Voice mode package for CloneAI.

Exposes helpers to activate conversational voice sessions from the CLI.
"""

from .manager import VoiceModeManager, get_voice_manager

__all__ = ["VoiceModeManager", "get_voice_manager"]

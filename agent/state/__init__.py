"""
CloneAI State Management Package
Handles logging, history, and persistent state.
"""

from .logger import (
    CommandLogger,
    get_logger,
    log_command,
    get_history,
    search_history,
    format_history_list,
    clear_history,
    get_command_history
)

__all__ = [
    'CommandLogger',
    'get_logger',
    'log_command',
    'get_history',
    'search_history',
    'format_history_list',
    'clear_history',
    'get_command_history'
]

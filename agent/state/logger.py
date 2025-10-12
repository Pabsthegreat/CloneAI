"""
Command logging system for CloneAI
Stores last 100 commands and their outputs in a circular buffer.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque

from agent.system_info import get_history_path, ensure_config_dir


class CommandLogger:
    """Logs commands and outputs with circular buffer (max 100 entries)."""
    
    def __init__(self, log_path: Optional[str] = None, max_entries: int = 100):
        """
        Initialize command logger.
        
        Args:
            log_path: Path to log file (default: ~/.clai/command_history.json)
            max_entries: Maximum number of entries to keep (default: 100)
        """
        self.max_entries = max_entries
        self.log_path = log_path or str(get_history_path())
        self.log_dir = os.path.dirname(self.log_path)
        
        # Ensure directory exists
        ensure_config_dir()
        
        # Load existing history
        self.history = self._load_history()
    
    def _load_history(self) -> deque:
        """Load command history from file."""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert list to deque with max length
                    return deque(data, maxlen=self.max_entries)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Could not load history: {e}")
                return deque(maxlen=self.max_entries)
        return deque(maxlen=self.max_entries)
    
    def _save_history(self):
        """Save command history to file."""
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(list(self.history), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")
    
    def log_command(
        self,
        command: str,
        output: str,
        command_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a command and its output.
        
        Args:
            command: The command executed
            output: The output/result of the command
            command_type: Type of command (e.g., 'hi', 'chat', 'do', 'mail')
            metadata: Additional metadata (e.g., sender, count for email commands)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "command_type": command_type,
            "output": output,
            "metadata": metadata or {}
        }
        
        # Add to history (automatically removes oldest if > max_entries)
        self.history.append(entry)
        
        # Save to disk
        self._save_history()
    
    def get_history(
        self,
        limit: Optional[int] = None,
        command_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get command history.
        
        Args:
            limit: Maximum number of entries to return
            command_type: Filter by command type
            
        Returns:
            List of command history entries (most recent first)
        """
        # Convert deque to list (newest first)
        history_list = list(reversed(self.history))
        
        # Filter by command type if specified
        if command_type:
            history_list = [
                entry for entry in history_list
                if entry.get('command_type') == command_type
            ]
        
        # Apply limit
        if limit:
            history_list = history_list[:limit]
        
        return history_list
    
    def search_history(
        self,
        query: str,
        search_in: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Search command history.
        
        Args:
            query: Search query string
            search_in: Where to search ('command', 'output', or 'both')
            
        Returns:
            List of matching entries (most recent first)
        """
        query_lower = query.lower()
        results = []
        
        for entry in reversed(self.history):
            match = False
            
            if search_in in ("command", "both"):
                if query_lower in entry.get('command', '').lower():
                    match = True
            
            if search_in in ("output", "both"):
                if query_lower in entry.get('output', '').lower():
                    match = True
            
            if match:
                results.append(entry)
        
        return results
    
    def clear_history(self):
        """Clear all command history."""
        self.history.clear()
        self._save_history()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about command history."""
        if not self.history:
            return {
                "total_commands": 0,
                "command_types": {},
                "oldest_entry": None,
                "newest_entry": None,
            }
        
        # Count by command type
        command_types = {}
        for entry in self.history:
            cmd_type = entry.get('command_type', 'unknown')
            command_types[cmd_type] = command_types.get(cmd_type, 0) + 1
        
        return {
            "total_commands": len(self.history),
            "max_entries": self.max_entries,
            "command_types": command_types,
            "oldest_entry": self.history[0].get('timestamp') if self.history else None,
            "newest_entry": self.history[-1].get('timestamp') if self.history else None,
        }


def format_history_entry(entry: Dict[str, Any], index: int) -> str:
    """Format a single history entry for display."""
    timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    command = entry.get('command', 'N/A')
    command_type = entry.get('command_type', 'unknown')
    output = entry.get('output', '')
    
    # Truncate output if too long
    output_preview = output[:200] + "..." if len(output) > 200 else output
    
    lines = [
        f"\n{index}. [{timestamp}] {command_type.upper()}",
        f"   Command: {command}",
        f"   Output: {output_preview}",
        "-" * 80
    ]
    
    return "\n".join(lines)


def format_history_list(entries: List[Dict[str, Any]], title: str = "Command History") -> str:
    """Format multiple history entries for display."""
    if not entries:
        return "No history entries found."
    
    output = [f"\n📜 {title} ({len(entries)} entries)\n", "=" * 80]
    
    for i, entry in enumerate(entries, 1):
        output.append(format_history_entry(entry, i))
    
    return "\n".join(output)


# Global logger instance
_logger = None

def get_logger() -> CommandLogger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = CommandLogger()
    return _logger


def log_command(command: str, output: str, command_type: str = "general", metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to log a command."""
    logger = get_logger()
    logger.log_command(command, output, command_type, metadata)


def get_history(limit: Optional[int] = None, command_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function to get history."""
    logger = get_logger()
    return logger.get_history(limit, command_type)


def search_history(query: str, search_in: str = "both") -> List[Dict[str, Any]]:
    """Convenience function to search history."""
    logger = get_logger()
    return logger.search_history(query, search_in)

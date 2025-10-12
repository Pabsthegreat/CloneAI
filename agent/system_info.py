"""
Cross-platform system detection and configuration for CloneAI.
Handles path resolution and system-specific behavior.
"""

import os
import platform
import sys
from pathlib import Path
from typing import Tuple


def detect_system() -> Tuple[str, str]:
    """
    Detect the operating system and architecture.
    
    Returns:
        Tuple of (os_name, architecture) where:
        - os_name: 'Windows', 'macOS', 'Linux'
        - architecture: 'x86_64', 'arm64', 'aarch64', etc.
    """
    system = platform.system()
    machine = platform.machine().lower()
    
    # Normalize OS name
    if system == "Darwin":
        os_name = "macOS"
    elif system == "Windows":
        os_name = "Windows"
    elif system == "Linux":
        os_name = "Linux"
    else:
        os_name = system
    
    # Normalize architecture
    if machine in ['arm64', 'aarch64']:
        arch = 'ARM64'
    elif machine in ['x86_64', 'amd64']:
        arch = 'x86_64'
    elif machine in ['i386', 'i686', 'x86']:
        arch = 'x86'
    else:
        arch = machine.upper()
    
    return os_name, arch


def get_system_display_name() -> str:
    """
    Get a user-friendly system name for display.
    
    Returns:
        String like "macOS (ARM64)", "Windows (x86_64)", "Linux (x86_64)"
    """
    os_name, arch = detect_system()
    
    # Special case for Apple Silicon
    if os_name == "macOS" and arch == "ARM64":
        return "macOS Silicon"
    
    return f"{os_name} ({arch})"


def get_config_dir() -> Path:
    """
    Get the configuration directory for CloneAI.
    Cross-platform compatible.
    
    Returns:
        Path to ~/.clai directory
    """
    return Path.home() / '.clai'


def get_credentials_path() -> Path:
    """Get path to credentials.json"""
    return get_config_dir() / 'credentials.json'


def get_gmail_token_path() -> Path:
    """Get path to Gmail token"""
    return get_config_dir() / 'token.pickle'


def get_calendar_token_path() -> Path:
    """Get path to Calendar token"""
    return get_config_dir() / 'token_calendar.pickle'


def get_history_path() -> Path:
    """Get path to command history"""
    return get_config_dir() / 'command_history.json'


def ensure_config_dir() -> Path:
    """
    Ensure the config directory exists.
    Creates it if it doesn't exist.
    
    Returns:
        Path to config directory
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_shell_name() -> str:
    """
    Detect the current shell being used.
    
    Returns:
        Shell name: 'powershell', 'bash', 'zsh', 'fish', etc.
    """
    shell = os.environ.get('SHELL', '')
    
    if 'powershell' in shell.lower() or 'pwsh' in shell.lower():
        return 'PowerShell'
    elif 'bash' in shell:
        return 'Bash'
    elif 'zsh' in shell:
        return 'Zsh'
    elif 'fish' in shell:
        return 'Fish'
    elif sys.platform == 'win32':
        return 'PowerShell'  # Default on Windows
    else:
        return shell.split('/')[-1] if shell else 'Unknown'


def get_system_info() -> dict:
    """
    Get comprehensive system information.
    
    Returns:
        Dictionary with system details
    """
    os_name, arch = detect_system()
    
    return {
        'os': os_name,
        'architecture': arch,
        'display_name': get_system_display_name(),
        'shell': get_shell_name(),
        'python_version': platform.python_version(),
        'config_dir': str(get_config_dir()),
    }


def print_system_info():
    """Print system information in a user-friendly format."""
    info = get_system_info()
    print(f"System: {info['display_name']}")


# For backwards compatibility
def get_home_dir() -> str:
    """Get home directory as string. Deprecated - use Path.home() instead."""
    return str(Path.home())

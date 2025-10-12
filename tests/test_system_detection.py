"""
Test system detection functionality.
"""

import pytest
from agent.system_info import (
    detect_system,
    get_system_display_name,
    get_config_dir,
    get_credentials_path,
    get_gmail_token_path,
    get_calendar_token_path,
    get_history_path,
    get_system_info,
)
from pathlib import Path


def test_detect_system():
    """Test system detection returns valid values."""
    os_name, arch = detect_system()
    
    assert os_name in ['Windows', 'macOS', 'Linux'], f"Unknown OS: {os_name}"
    assert arch in ['ARM64', 'x86_64', 'x86'], f"Unknown architecture: {arch}"


def test_get_system_display_name():
    """Test system display name format."""
    display_name = get_system_display_name()
    
    assert isinstance(display_name, str)
    assert len(display_name) > 0
    # Should contain either "Windows", "macOS", or "Linux"
    assert any(os in display_name for os in ['Windows', 'macOS', 'Linux'])


def test_get_config_dir():
    """Test config directory path."""
    config_dir = get_config_dir()
    
    assert isinstance(config_dir, Path)
    assert config_dir.name == '.clai'
    assert config_dir.parent == Path.home()


def test_get_credentials_path():
    """Test credentials file path."""
    creds_path = get_credentials_path()
    
    assert isinstance(creds_path, Path)
    assert creds_path.name == 'credentials.json'
    assert creds_path.parent.name == '.clai'


def test_get_gmail_token_path():
    """Test Gmail token path."""
    token_path = get_gmail_token_path()
    
    assert isinstance(token_path, Path)
    assert token_path.name == 'token.pickle'
    assert token_path.parent.name == '.clai'


def test_get_calendar_token_path():
    """Test Calendar token path."""
    token_path = get_calendar_token_path()
    
    assert isinstance(token_path, Path)
    assert token_path.name == 'token_calendar.pickle'
    assert token_path.parent.name == '.clai'


def test_get_history_path():
    """Test command history path."""
    history_path = get_history_path()
    
    assert isinstance(history_path, Path)
    assert history_path.name == 'command_history.json'
    assert history_path.parent.name == '.clai'


def test_get_system_info():
    """Test comprehensive system info."""
    info = get_system_info()
    
    assert isinstance(info, dict)
    assert 'os' in info
    assert 'architecture' in info
    assert 'display_name' in info
    assert 'shell' in info
    assert 'python_version' in info
    assert 'config_dir' in info
    
    # Verify values are non-empty
    for key, value in info.items():
        assert value is not None
        assert str(value).strip() != ''


def test_config_dir_creation(tmp_path, monkeypatch):
    """Test config directory is created automatically."""
    # Mock home directory to tmp_path
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    
    from agent.system_info import ensure_config_dir
    
    config_dir = ensure_config_dir()
    
    assert config_dir.exists()
    assert config_dir.is_dir()
    assert config_dir.name == '.clai'

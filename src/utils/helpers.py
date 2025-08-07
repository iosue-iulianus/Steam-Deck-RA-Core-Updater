#!/usr/bin/env python3
"""Utility functions for the RetroArch Core Updater."""

import os
import shutil
from pathlib import Path
from typing import Optional


def format_bytes(bytes_count: int) -> str:
    """Format bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"


def check_dependencies() -> dict:
    """Check if required system dependencies are available."""
    dependencies = {
        'git': shutil.which('git') is not None,
        '7z': shutil.which('7z') is not None or shutil.which('7za') is not None,
        'wget': shutil.which('wget') is not None,
    }
    return dependencies


def get_free_space(path: str) -> int:
    """Get free space in bytes for the given path."""
    try:
        statvfs = os.statvfs(path)
        return statvfs.f_frsize * statvfs.f_bavail
    except (OSError, AttributeError):
        return 0


def validate_write_permissions(path: str) -> bool:
    """Check if we have write permissions to a path."""
    try:
        test_path = Path(path)
        if not test_path.exists():
            # Try to create the directory
            test_path.mkdir(parents=True, exist_ok=True)
        
        # Test write permission with a temporary file
        test_file = test_path / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
            
    except (OSError, PermissionError):
        return False


def is_steam_deck() -> bool:
    """Detect if running on Steam Deck."""
    try:
        # Check for Steam Deck specific files/directories
        steam_deck_indicators = [
            '/home/deck',  # Default Steam Deck user
            '/usr/bin/steamos-session-select',  # SteamOS specific command
        ]
        
        for indicator in steam_deck_indicators:
            if Path(indicator).exists():
                return True
        
        # Check environment variables
        if os.environ.get('SteamOS') or os.environ.get('STEAM_COMPAT_CLIENT_INSTALL_PATH'):
            return True
            
        return False
        
    except Exception:
        return False


def get_system_info() -> dict:
    """Get basic system information."""
    info = {
        'is_steam_deck': is_steam_deck(),
        'home_dir': str(Path.home()),
        'dependencies': check_dependencies(),
    }
    
    return info


def create_desktop_entry(app_name: str, exec_path: str, icon_path: str = None) -> bool:
    """Create a desktop entry for the application."""
    try:
        desktop_dir = Path.home() / '.local/share/applications'
        desktop_dir.mkdir(parents=True, exist_ok=True)
        
        desktop_file = desktop_dir / f'{app_name.lower().replace(" ", "-")}.desktop'
        
        content = f"""[Desktop Entry]
Name={app_name}
Comment=Update RetroArch cores on Steam Deck
Exec={exec_path}
Terminal=false
Type=Application
Categories=Game;Emulator;
StartupNotify=true"""

        if icon_path:
            content += f"\nIcon={icon_path}"
        
        desktop_file.write_text(content)
        desktop_file.chmod(0o755)
        
        return True
        
    except (OSError, PermissionError):
        return False


class SettingsManager:
    """Simple settings manager using a text file."""
    
    def __init__(self, app_name: str = "retroarch-core-updater"):
        self.config_dir = Path.home() / '.config' / app_name
        self.config_file = self.config_dir / 'settings.conf'
        self.settings = {}
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            self.settings[key.strip()] = value.strip()
            except (OSError, ValueError):
                pass
    
    def _save_settings(self):
        """Save settings to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                f.write("# RetroArch Core Updater Settings\n")
                for key, value in self.settings.items():
                    f.write(f"{key}={value}\n")
        except OSError:
            pass
    
    def get(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: str):
        """Set a setting value."""
        self.settings[key] = str(value)
        self._save_settings()
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting."""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def set_bool(self, key: str, value: bool):
        """Set a boolean setting."""
        self.set(key, 'true' if value else 'false')
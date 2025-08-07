#!/usr/bin/env python3
"""RetroArch installation detection for Steam Deck."""

import os
import glob
from pathlib import Path
from typing import List, Dict, Optional


class RetroArchDetector:
    """Detects RetroArch installations on Steam Deck."""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.detected_installations = []
    
    def detect_installations(self) -> List[Dict[str, str]]:
        """Detect all RetroArch installations on the system."""
        installations = []
        
        # Check internal storage
        internal_path = self._check_internal_storage()
        if internal_path:
            installations.append({
                'location': 'internal',
                'path': str(internal_path),
                'display_name': 'Internal Storage'
            })
        
        # Check SD card
        sd_paths = self._check_sd_card()
        for sd_path in sd_paths:
            installations.append({
                'location': 'sd',
                'path': str(sd_path),
                'display_name': f'SD Card ({sd_path.parent.name})'
            })
        
        self.detected_installations = installations
        return installations
    
    def _check_internal_storage(self) -> Optional[Path]:
        """Check for RetroArch on internal storage."""
        internal_path = self.home_dir / '.local/share/Steam/steamapps/common/RetroArch'
        
        if internal_path.exists() and internal_path.is_dir():
            cores_path = internal_path / 'cores'
            if cores_path.exists() or self._can_create_cores_dir(cores_path):
                return cores_path
        
        return None
    
    def _check_sd_card(self) -> List[Path]:
        """Check for RetroArch installations on SD cards."""
        sd_installations = []
        
        # Common SD card mount points on Steam Deck
        sd_mount_patterns = [
            '/run/media/mmcblk0p1/steamapps/common/RetroArch',
            '/run/media/*/steamapps/common/RetroArch',
            '/media/*/steamapps/common/RetroArch'
        ]
        
        for pattern in sd_mount_patterns:
            for retroarch_path in glob.glob(pattern):
                retroarch_path = Path(retroarch_path)
                if retroarch_path.exists() and retroarch_path.is_dir():
                    cores_path = retroarch_path / 'cores'
                    if cores_path.exists() or self._can_create_cores_dir(cores_path):
                        sd_installations.append(cores_path)
        
        return sd_installations
    
    def _can_create_cores_dir(self, cores_path: Path) -> bool:
        """Check if we can create the cores directory."""
        try:
            cores_path.mkdir(parents=True, exist_ok=True)
            return True
        except (PermissionError, OSError):
            return False
    
    def validate_installation_path(self, path: str) -> bool:
        """Validate that a given path is suitable for RetroArch cores."""
        try:
            cores_path = Path(path)
            parent_path = cores_path.parent
            
            # Check if parent directory exists and contains RetroArch files
            if not parent_path.exists():
                return False
            
            # Look for RetroArch executable or configuration files
            retroarch_indicators = [
                'retroarch',
                'retroarch.cfg',
                'RetroArch-Linux-x86_64.AppImage'
            ]
            
            for indicator in retroarch_indicators:
                if (parent_path / indicator).exists():
                    return True
            
            return False
            
        except (ValueError, OSError):
            return False
    
    def get_recommended_path(self) -> Optional[str]:
        """Get the recommended installation path."""
        installations = self.detect_installations()
        
        if not installations:
            return None
        
        # Prefer internal storage if available
        for install in installations:
            if install['location'] == 'internal':
                return install['path']
        
        # Otherwise return first SD card installation
        return installations[0]['path']
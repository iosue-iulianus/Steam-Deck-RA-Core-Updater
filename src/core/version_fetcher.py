#!/usr/bin/env python3
"""Fetch available RetroArch versions from Libretro buildbot."""

import re
import requests
from typing import List, Optional
from urllib.parse import urljoin


class VersionFetcher:
    """Fetches available RetroArch versions from Libretro buildbot."""
    
    BASE_URL = "https://buildbot.libretro.com/stable/"
    LINUX_ARCH = "linux/x86_64/"
    CORES_FILENAME = "RetroArch_cores.7z"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RetroArch-Core-Updater/1.0'
        })
    
    def fetch_available_versions(self) -> List[str]:
        """Fetch list of available RetroArch versions."""
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            
            # Parse HTML to find version directories
            version_pattern = r'href="/stable/(\d+\.\d+\.\d+)/"'
            versions = re.findall(version_pattern, response.text)
            
            # Sort versions in descending order (newest first)
            return sorted(set(versions), key=self._version_key, reverse=True)
            
        except requests.RequestException as e:
            print(f"Error fetching versions: {e}")
            return []
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest available version."""
        versions = self.fetch_available_versions()
        return versions[0] if versions else None
    
    def get_download_url(self, version: str) -> str:
        """Get download URL for a specific version."""
        return urljoin(
            self.BASE_URL,
            f"{version}/{self.LINUX_ARCH}{self.CORES_FILENAME}"
        )
    
    def validate_version(self, version: str) -> bool:
        """Validate that a version exists and is downloadable."""
        try:
            url = self.get_download_url(version)
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_version_info(self, version: str) -> dict:
        """Get detailed information about a version."""
        url = self.get_download_url(version)
        
        try:
            response = self.session.head(url, timeout=10)
            
            if response.status_code == 200:
                return {
                    'version': version,
                    'url': url,
                    'size': int(response.headers.get('content-length', 0)),
                    'available': True
                }
            else:
                return {
                    'version': version,
                    'url': url,
                    'available': False
                }
                
        except requests.RequestException as e:
            return {
                'version': version,
                'url': url,
                'available': False,
                'error': str(e)
            }
    
    def _version_key(self, version: str) -> tuple:
        """Convert version string to tuple for sorting."""
        try:
            return tuple(int(x) for x in version.split('.'))
        except ValueError:
            return (0, 0, 0)
    
    def get_core_info_repo_url(self) -> str:
        """Get URL for the core info repository."""
        return "https://github.com/libretro/libretro-core-info.git"
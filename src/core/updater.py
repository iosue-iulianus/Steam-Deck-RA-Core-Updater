#!/usr/bin/env python3
"""Core updater functionality for RetroArch."""

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Callable
import requests
from PySide6.QtCore import QObject, Signal, QThread


class UpdaterSignals(QObject):
    """Signals for the updater."""
    progress_changed = Signal(int)  # Progress percentage
    status_changed = Signal(str)    # Status message
    error_occurred = Signal(str)    # Error message
    finished = Signal(bool)         # Success/failure


class CoreUpdater(QThread):
    """Handles downloading and updating RetroArch cores."""
    
    def __init__(self, version: str, cores_path: str, core_info_url: str):
        super().__init__()
        self.version = version
        self.cores_path = Path(cores_path)
        self.core_info_url = core_info_url
        self.download_url = f"https://buildbot.libretro.com/stable/{version}/linux/x86_64/RetroArch_cores.7z"
        
        self.signals = UpdaterSignals()
        self.cancelled = False
        
    def run(self):
        """Run the update process."""
        try:
            self.signals.status_changed.emit("Preparing update...")
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                if self.cancelled:
                    return
                
                # Step 1: Backup existing cores
                self.signals.status_changed.emit("Backing up existing cores...")
                backup_path = self._backup_existing_cores()
                self.signals.progress_changed.emit(10)
                
                if self.cancelled:
                    return
                
                # Step 2: Clean cores directory
                self.signals.status_changed.emit("Cleaning cores directory...")
                self._clean_cores_directory()
                self.signals.progress_changed.emit(20)
                
                if self.cancelled:
                    self._restore_backup(backup_path)
                    return
                
                # Step 3: Clone core info files
                self.signals.status_changed.emit("Downloading core information...")
                success = self._clone_core_info()
                if not success:
                    self._restore_backup(backup_path)
                    self.signals.error_occurred.emit("Failed to download core information")
                    self.signals.finished.emit(False)
                    return
                self.signals.progress_changed.emit(40)
                
                if self.cancelled:
                    self._restore_backup(backup_path)
                    return
                
                # Step 4: Download cores archive
                self.signals.status_changed.emit("Downloading cores archive...")
                archive_path = temp_path / "RetroArch_cores.7z"
                success = self._download_cores_archive(archive_path)
                if not success:
                    self._restore_backup(backup_path)
                    self.signals.error_occurred.emit("Failed to download cores archive")
                    self.signals.finished.emit(False)
                    return
                
                if self.cancelled:
                    self._restore_backup(backup_path)
                    return
                
                # Step 5: Extract cores
                self.signals.status_changed.emit("Extracting cores...")
                success = self._extract_cores(archive_path)
                if not success:
                    self._restore_backup(backup_path)
                    self.signals.error_occurred.emit("Failed to extract cores")
                    self.signals.finished.emit(False)
                    return
                self.signals.progress_changed.emit(90)
                
                if self.cancelled:
                    self._restore_backup(backup_path)
                    return
                
                # Step 6: Cleanup
                self.signals.status_changed.emit("Finalizing installation...")
                self._cleanup_extracted_files()
                self.signals.progress_changed.emit(100)
                
                # Clean up backup if successful
                if backup_path and backup_path.exists():
                    shutil.rmtree(backup_path)
                
                self.signals.status_changed.emit("Update completed successfully!")
                self.signals.finished.emit(True)
                
        except Exception as e:
            self.signals.error_occurred.emit(f"Unexpected error: {str(e)}")
            self.signals.finished.emit(False)
    
    def cancel(self):
        """Cancel the update process."""
        self.cancelled = True
    
    def _backup_existing_cores(self) -> Optional[Path]:
        """Backup existing cores directory."""
        if not self.cores_path.exists():
            return None
        
        backup_path = self.cores_path.parent / f"cores_backup_{self.version}"
        
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(self.cores_path, backup_path)
            return backup_path
        except (OSError, shutil.Error) as e:
            print(f"Warning: Could not create backup: {e}")
            return None
    
    def _restore_backup(self, backup_path: Optional[Path]):
        """Restore from backup if it exists."""
        if backup_path and backup_path.exists():
            try:
                if self.cores_path.exists():
                    shutil.rmtree(self.cores_path)
                shutil.move(str(backup_path), str(self.cores_path))
            except (OSError, shutil.Error) as e:
                print(f"Error restoring backup: {e}")
    
    def _clean_cores_directory(self):
        """Clean the cores directory."""
        if self.cores_path.exists():
            shutil.rmtree(self.cores_path)
        self.cores_path.mkdir(parents=True, exist_ok=True)
    
    def _clone_core_info(self) -> bool:
        """Download core info files from GitHub as ZIP."""
        try:
            # Download core info as ZIP instead of git clone
            zip_url = "https://github.com/libretro/libretro-core-info/archive/refs/heads/master.zip"
            
            response = requests.get(zip_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save ZIP to temporary file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        return False
                    if chunk:
                        temp_file.write(chunk)
                temp_zip_path = temp_file.name
            
            # Extract ZIP to cores directory
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # Extract all files, but remove the top-level directory
                for member in zip_ref.namelist():
                    # Skip the root directory (libretro-core-info-master/)
                    if '/' in member:
                        # Remove the first directory component
                        relative_path = '/'.join(member.split('/')[1:])
                        if relative_path:  # Skip empty paths
                            member_path = self.cores_path / relative_path
                            member_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            if not member.endswith('/'):  # It's a file, not a directory
                                with zip_ref.open(member) as source, open(member_path, 'wb') as target:
                                    target.write(source.read())
            
            # Clean up temp file
            os.unlink(temp_zip_path)
            return True
            
        except (requests.RequestException, zipfile.BadZipFile, OSError) as e:
            print(f"Error downloading core info: {e}")
            return False
    
    def _download_cores_archive(self, output_path: Path) -> bool:
        """Download the cores archive."""
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = int(40 + (downloaded / total_size) * 30)
                            self.signals.progress_changed.emit(progress)
            
            return True
            
        except requests.RequestException:
            return False
    
    def _extract_cores(self, archive_path: Path) -> bool:
        """Extract cores from archive (supports both 7z and zip)."""
        try:
            # First try with 7z if available
            if shutil.which('7z'):
                cmd = ["7z", "e", str(archive_path), f"-o{self.cores_path}"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(self.cores_path)
                )
                if result.returncode == 0:
                    return True
            
            # Fallback to Python zipfile if 7z failed or not available
            # Note: This assumes the archive is actually a zip file
            # For true 7z files, we'd need python-lzma or py7zr
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.cores_path)
                return True
            except zipfile.BadZipFile:
                # If it's a real 7z file and 7z command failed, we can't extract it
                return False
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, Exception):
            return False
    
    def _cleanup_extracted_files(self):
        """Clean up unnecessary files from extraction."""
        cleanup_items = [
            "configure",
            "cores",
            "retroarch", 
            "RetroArch-Linux-x86_64",
            "RetroArch-Linux-x86_64.AppImage.home"
        ]
        
        for item in cleanup_items:
            item_path = self.cores_path / item
            if item_path.exists():
                if item_path.is_dir():
                    shutil.rmtree(item_path)
                else:
                    item_path.unlink()


class UpdateManager:
    """Manages the update process."""
    
    def __init__(self):
        self.current_updater = None
    
    def start_update(self, version: str, cores_path: str, 
                    progress_callback: Optional[Callable] = None,
                    status_callback: Optional[Callable] = None,
                    error_callback: Optional[Callable] = None,
                    finished_callback: Optional[Callable] = None) -> CoreUpdater:
        """Start an update process."""
        core_info_url = "https://github.com/libretro/libretro-core-info.git"
        
        self.current_updater = CoreUpdater(version, cores_path, core_info_url)
        
        # Connect callbacks
        if progress_callback:
            self.current_updater.signals.progress_changed.connect(progress_callback)
        if status_callback:
            self.current_updater.signals.status_changed.connect(status_callback)
        if error_callback:
            self.current_updater.signals.error_occurred.connect(error_callback)
        if finished_callback:
            self.current_updater.signals.finished.connect(finished_callback)
        
        self.current_updater.start()
        return self.current_updater
    
    def cancel_update(self):
        """Cancel the current update."""
        if self.current_updater and self.current_updater.isRunning():
            self.current_updater.cancel()
            self.current_updater.wait(5000)  # Wait up to 5 seconds
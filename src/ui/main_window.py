#!/usr/bin/env python3
"""Main window for RetroArch Core Updater."""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QPushButton, QGroupBox,
                              QTextEdit, QMessageBox, QSplitter, QFrame, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap

from core.detector import RetroArchDetector
from core.version_fetcher import VersionFetcher
from core.updater import UpdateManager
from utils.helpers import SettingsManager, format_bytes, get_free_space, get_system_info
# from .progress_dialog import ProgressDialog  # No longer needed


class VersionLoader(QThread):
    """Thread for loading available versions without blocking UI."""
    
    versions_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def run(self):
        """Load versions in background."""
        try:
            fetcher = VersionFetcher()
            versions = fetcher.fetch_available_versions()
            if versions:
                self.versions_loaded.emit(versions)
            else:
                self.error_occurred.emit("No versions found or network error")
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RetroArch Core Updater for SteamOS")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        
        # Initialize components
        self.detector = RetroArchDetector()
        self.version_fetcher = VersionFetcher()
        self.update_manager = UpdateManager()
        self.settings = SettingsManager()
        
        # UI state
        self.installations = []
        self.available_versions = []
        self.version_loader = None
        
        self._setup_ui()
        self._apply_steam_deck_styling()
        self._load_initial_data()
        
        # Load saved settings
        self._restore_settings()
    
    def _setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal splitter as primary container
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Content splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left column - Header + Configuration
        left_widget = self._create_left_column()
        splitter.addWidget(left_widget)
        
        # Right column - Status Log
        log_widget = self._create_log_panel()
        splitter.addWidget(log_widget)
        
        # Set splitter proportions (left column slightly smaller)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        
        # Footer
        self._create_footer(main_layout)
    
    def _create_left_column(self):
        """Create the left column with header and configuration."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # Header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(5)
        header_layout.setContentsMargins(0, 0, 0, 15)
        
        # Title
        title_label = QLabel("🎮 RetroArch Core Updater")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Download and install the latest RetroArch cores for SteamOS")
        subtitle_label.setStyleSheet("color: #aaa !important; font-size: 14px;")
        subtitle_label.setWordWrap(True)
        header_layout.addWidget(subtitle_label)
        
        left_layout.addWidget(header_widget)
        
        # Configuration panel (without groupbox)
        config_widget = self._create_config_content()
        left_layout.addWidget(config_widget)
        
        return left_widget
    
    def _create_config_content(self):
        """Create the configuration content without groupbox."""
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setSpacing(20)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # Version selection
        version_layout = QVBoxLayout()
        version_layout.setSpacing(8)
        version_label = QLabel("RetroArch Version:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        version_label.setFont(font)
        version_layout.addWidget(version_label)
        
        self.version_combo = QComboBox()
        self.version_combo.setMinimumHeight(40)
        self.version_combo.addItem("Loading versions...", None)
        self.version_combo.setEnabled(False)
        version_layout.addWidget(self.version_combo)
        
        config_layout.addLayout(version_layout)
        
        # Installation location
        location_layout = QVBoxLayout()
        location_layout.setSpacing(8)
        location_label = QLabel("Installation Location:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        location_label.setFont(font)
        location_layout.addWidget(location_label)
        
        self.location_combo = QComboBox()
        self.location_combo.setMinimumHeight(40)
        self.location_combo.currentTextChanged.connect(self._on_location_changed)
        location_layout.addWidget(self.location_combo)
        
        config_layout.addLayout(location_layout)
        
        # Update button
        self.update_button = QPushButton("🔄 Update Cores")
        self.update_button.setMinimumHeight(55)
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #2d5aa0;
                color: white !important;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e3f73;
            }
            QPushButton:pressed {
                background-color: #152d56;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999 !important;
            }
        """)
        self.update_button.clicked.connect(self._start_update)
        self.update_button.setEnabled(False)
        config_layout.addWidget(self.update_button)
        
        config_layout.addStretch()
        
        return config_widget
    
    def _create_config_panel(self):
        """Create the configuration panel."""
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(15)
        
        # Version selection
        version_layout = QVBoxLayout()
        version_label = QLabel("RetroArch Version:")
        font = QFont()
        font.setBold(True)
        version_label.setFont(font)
        version_layout.addWidget(version_label)
        
        self.version_combo = QComboBox()
        self.version_combo.setMinimumHeight(35)
        self.version_combo.addItem("Loading versions...", None)
        self.version_combo.setEnabled(False)
        version_layout.addWidget(self.version_combo)
        
        config_layout.addLayout(version_layout)
        
        # Installation location
        location_layout = QVBoxLayout()
        location_label = QLabel("Installation Location:")
        font = QFont()
        font.setBold(True)
        location_label.setFont(font)
        location_layout.addWidget(location_label)
        
        self.location_combo = QComboBox()
        self.location_combo.setMinimumHeight(35)
        self.location_combo.currentTextChanged.connect(self._on_location_changed)
        location_layout.addWidget(self.location_combo)
        
        config_layout.addLayout(location_layout)
        
        # Update button
        self.update_button = QPushButton("🔄 Update Cores")
        self.update_button.setMinimumHeight(50)
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #2d5aa0;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e3f73;
            }
            QPushButton:pressed {
                background-color: #152d56;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.update_button.clicked.connect(self._start_update)
        self.update_button.setEnabled(False)
        config_layout.addWidget(self.update_button)
        
        config_layout.addStretch()
        
        return config_group
    
    def _create_log_panel(self):
        """Create the unified status log panel."""
        log_group = QGroupBox("Status")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(10)
        
        # Progress section (initially hidden)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        
        # Progress status label
        self.progress_status_label = QLabel("Preparing update...")
        self.progress_status_label.setStyleSheet("color: #4a90e2; font-weight: bold; font-size: 13px;")
        progress_layout.addWidget(self.progress_status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #606060;
                border-radius: 8px;
                text-align: center;
                background-color: #2a2a2a;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 7px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # Progress buttons
        progress_buttons = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_update)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        progress_buttons.addStretch()
        progress_buttons.addWidget(self.cancel_button)
        progress_layout.addLayout(progress_buttons)
        
        log_layout.addWidget(self.progress_frame)
        
        # Status log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        return log_group
    
    def _create_footer(self, layout):
        """Create the footer section."""
        footer_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Refresh button
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self._refresh_data)
        footer_layout.addWidget(refresh_button)
        
        layout.addLayout(footer_layout)
    
    def _apply_steam_deck_styling(self):
        """Apply modern, Steam-compatible styling."""
        # Detect if running under Steam and apply more aggressive overrides
        import os
        is_steam_mode = os.environ.get('SteamAppId') is not None or os.environ.get('STEAM_COMPAT_DATA_PATH') is not None
        
        # Force Qt to use our styles regardless of system theme
        if is_steam_mode:
            os.environ['QT_QPA_PLATFORMTHEME'] = ''  # Disable system theme integration
        
        # Modern dark theme with explicit !important overrides for Steam compatibility
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2b2b2b, stop:1 #1e1e1e) !important;
                color: #ffffff !important;
            }
            QWidget {
                background-color: transparent;
                color: #ffffff !important;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #4a4a4a !important;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 15px;
                background: rgba(45, 45, 45, 0.6) !important;
                color: #ffffff !important;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ffffff !important;
                background: #2b2b2b !important;
                border-radius: 6px;
            }
            QComboBox {
                border: 2px solid #606060 !important;
                border-radius: 10px !important;
                padding: 10px 15px !important;
                background: #353535 !important;
                color: #ffffff !important;
                font-size: 13px !important;
                selection-background-color: #4a90e2 !important;
            }
            QComboBox:hover {
                border-color: #4a90e2 !important;
                background: #404040 !important;
            }
            QComboBox:focus {
                border-color: #4a90e2 !important;
                background: #404040 !important;
                outline: none;
            }
            QComboBox::drop-down {
                border: none !important;
                width: 25px;
                background: transparent !important;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 10px solid #ffffff;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #4a90e2 !important;
                background: #353535 !important;
                color: #ffffff !important;
                selection-background-color: #4a90e2 !important;
                selection-color: #ffffff !important;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px !important;
                color: #ffffff !important;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #4a90e2 !important;
                color: #ffffff !important;
            }
            QTextEdit {
                border: 2px solid #606060 !important;
                border-radius: 10px !important;
                background: #1a1a1a !important;
                color: #ffffff !important;
                padding: 12px !important;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
                font-size: 12px !important;
                line-height: 1.5;
                selection-background-color: #4a90e2 !important;
                selection-color: #ffffff !important;
            }
            QTextEdit:focus {
                border-color: #4a90e2 !important;
                outline: none;
            }
            QLabel {
                color: #ffffff !important;
                background: transparent !important;
            }
            QPushButton {
                border: 2px solid #606060 !important;
                border-radius: 10px !important;
                padding: 12px 18px !important;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #404040, stop:1 #353535) !important;
                color: #ffffff !important;
                font-size: 13px !important;
                font-weight: bold !important;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4a4a4a, stop:1 #3f3f3f) !important;
                border-color: #4a90e2 !important;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #353535, stop:1 #2a2a2a) !important;
            }
            QPushButton:disabled {
                background: #666 !important;
                color: #999 !important;
                border-color: #555 !important;
            }
            QFrame {
                background: rgba(40, 40, 40, 0.8) !important;
                border: 1px solid #4a4a4a !important;
                border-radius: 10px;
                color: #ffffff !important;
            }
            QScrollBar:vertical {
                background: #2a2a2a !important;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #606060 !important;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a90e2 !important;
            }
        """)
    
    def _load_initial_data(self):
        """Load initial data."""
        self._log_message("Starting RetroArch Core Updater...")
        
        # Load system information
        self._load_system_info()
        
        # Detect installations
        self._detect_installations()
        
        # Load versions in background
        self._load_versions()
    
    def _load_system_info(self):
        """Load and log basic system information."""
        info = get_system_info()
        
        # Log basic system info to status log
        os_name = "SteamOS" if info['is_steam_deck'] else "Linux"
        self._log_message(f"🖥️ Running on {os_name}")
        self._log_message(f"📁 Home directory: {info['home_dir']}")
    
    def _detect_installations(self):
        """Detect RetroArch installations."""
        self._log_message("Detecting RetroArch installations...")
        
        self.installations = self.detector.detect_installations()
        
        # Update location combo
        self.location_combo.clear()
        
        if not self.installations:
            self.location_combo.addItem("No RetroArch installations found", None)
            self._log_message("⚠️ No RetroArch installations detected")
        else:
            for install in self.installations:
                self.location_combo.addItem(install['display_name'], install)
                self._log_message(f"✅ Found: {install['display_name']} at {install['path']}")
        
        self._update_button_state()
    
    def _load_versions(self):
        """Load available versions in background."""
        self._log_message("Loading available RetroArch versions...")
        
        if self.version_loader and self.version_loader.isRunning():
            self.version_loader.quit()
            self.version_loader.wait()
        
        self.version_loader = VersionLoader()
        self.version_loader.versions_loaded.connect(self._on_versions_loaded)
        self.version_loader.error_occurred.connect(self._on_versions_error)
        self.version_loader.start()
    
    def _on_versions_loaded(self, versions):
        """Handle loaded versions."""
        self.available_versions = versions
        
        # Update version combo
        self.version_combo.clear()
        self.version_combo.setEnabled(True)
        
        for version in versions:
            self.version_combo.addItem(f"Version {version}", version)
        
        if versions:
            self._log_message(f"✅ Loaded {len(versions)} available versions")
            self._log_message(f"📦 Latest version: {versions[0]}")
        
        self._update_button_state()
    
    def _on_versions_error(self, error):
        """Handle version loading error."""
        self.version_combo.clear()
        self.version_combo.addItem("Failed to load versions", None)
        self._log_message(f"❌ Error loading versions: {error}")
    
    def _on_location_changed(self):
        """Handle location selection change."""
        current_data = self.location_combo.currentData()
        if current_data:
            path = current_data['path']
            free_space = get_free_space(path)
            self._log_message(f"📊 Free space at {path}: {format_bytes(free_space)}")
    
    def _update_button_state(self):
        """Update the state of the update button."""
        has_version = self.version_combo.currentData() is not None
        has_location = self.location_combo.currentData() is not None
        
        self.update_button.setEnabled(has_version and has_location)
        
        if has_version and has_location:
            self.status_label.setText("Ready to update")
        else:
            self.status_label.setText("Select version and location")
    
    def _start_update(self):
        """Start the update process."""
        version_data = self.version_combo.currentData()
        location_data = self.location_combo.currentData()
        
        if not version_data or not location_data:
            return
        
        version = version_data
        cores_path = location_data['path']
        
        self._log_message(f"🚀 Starting update to version {version}")
        self._log_message(f"📂 Target directory: {cores_path}")
        
        # Save settings
        self._save_settings()
        
        # Show progress panel and disable update button
        self._show_progress_panel()
        self.update_button.setEnabled(False)
        
        # Start update
        updater = self.update_manager.start_update(
            version=version,
            cores_path=cores_path,
            progress_callback=self._update_progress,
            status_callback=self._update_status,
            error_callback=self._log_error,
            finished_callback=self._on_update_finished
        )
    
    def _cancel_update(self):
        """Cancel the current update."""
        self.update_manager.cancel_update()
        self._log_message("❌ Update cancelled by user")
        self._hide_progress_panel()
        self.update_button.setEnabled(True)
    
    def _on_update_finished(self, success: bool):
        """Handle update completion."""
        # Hide progress panel and re-enable update button
        self._hide_progress_panel()
        self.update_button.setEnabled(True)
        
        if success:
            self._log_message("✅ Update completed successfully!")
            self._log_message("🎮 You can now launch RetroArch and enjoy the updated cores.")
        else:
            self._log_message("❌ Update failed! Please check the log for details.")
    
    def _refresh_data(self):
        """Refresh all data."""
        self._log_message("🔄 Refreshing data...")
        self._detect_installations()
        self._load_versions()
    
    def _show_progress_panel(self):
        """Show the integrated progress panel."""
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_status_label.setText("Preparing update...")
    
    def _hide_progress_panel(self):
        """Hide the integrated progress panel."""
        self.progress_frame.setVisible(False)
    
    def _update_progress(self, percentage: int):
        """Update the progress bar."""
        self.progress_bar.setValue(percentage)
    
    def _update_status(self, status: str):
        """Update the progress status label."""
        self.progress_status_label.setText(status)
        self._log_message(status)
    
    def _log_error(self, error: str):
        """Log an error message."""
        self._log_message(f"❌ {error}")

    def _log_message(self, message: str):
        """Add a message to the log."""
        self.log_text.append(message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _save_settings(self):
        """Save current settings."""
        version_data = self.version_combo.currentData()
        location_data = self.location_combo.currentData()
        
        if version_data:
            self.settings.set('last_version', version_data)
        
        if location_data:
            self.settings.set('last_location', location_data['path'])
    
    def _restore_settings(self):
        """Restore saved settings."""
        last_version = self.settings.get('last_version')
        last_location = self.settings.get('last_location')
        
        # Restore version selection
        if last_version:
            index = self.version_combo.findData(last_version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        
        # Restore location selection
        if last_location:
            for i in range(self.location_combo.count()):
                data = self.location_combo.itemData(i)
                if data and data.get('path') == last_location:
                    self.location_combo.setCurrentIndex(i)
                    break
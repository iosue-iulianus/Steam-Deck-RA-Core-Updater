#!/usr/bin/env python3
"""Main window for RetroArch Core Updater."""

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QPushButton, QGroupBox,
                              QTextEdit, QMessageBox, QSplitter, QFrame, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QEvent, QSize
from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap, QKeyEvent, QShortcut, QKeySequence, QMovie
from pathlib import Path

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
        
        # Enable keyboard focus for main window
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Initialize components
        self.detector = RetroArchDetector()
        self.version_fetcher = VersionFetcher()
        self.update_manager = UpdateManager()
        self.settings = SettingsManager()
        
        # Assets and animation placeholders
        self.assets_dir = Path(__file__).resolve().parents[2] / 'assets'
        self.sonic_label = None
        self.sonic_wait_movie = None
        self.sonic_run_movie = None
        
        # UI state
        self.installations = []
        self.available_versions = []
        self.version_loader = None
        
        # Gamepad focus management
        self.focusable_widgets = []
        self.current_focus_index = 0
        
        self._setup_ui()
        self._apply_steam_deck_styling()
        self._setup_focus_system()
        self._setup_shortcuts()
        self._setup_gamepad()
        self._load_initial_data()
        
        # Load saved settings
        self._restore_settings()
        
        # Ensure main window can receive keyboard input
        self.setFocus()
    
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
        title_label.setFrameStyle(QFrame.Shape.NoFrame)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Download and install the latest RetroArch cores for SteamOS")
        subtitle_label.setFrameStyle(QFrame.Shape.NoFrame)
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
        version_label.setFrameStyle(QFrame.Shape.NoFrame)
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
        location_label.setFrameStyle(QFrame.Shape.NoFrame)
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
            QPushButton:focus {
                border: 3px solid #ffffff !important;
            }
        """)
        self.update_button.clicked.connect(self._start_update)
        self.update_button.setEnabled(False)
        config_layout.addWidget(self.update_button)
        
        # Sonic animation area under the Update Cores button
        self.sonic_label = QLabel()
        self.sonic_label.setAlignment(Qt.AlignCenter)
        self.sonic_label.setMinimumHeight(140)
        config_layout.addWidget(self.sonic_label)
        
        # Initialize and show idle animation
        self._init_sonic_movies()
        self._set_idle_animation()
        
        config_layout.addStretch()
        
        return config_widget

    def _init_sonic_movies(self):
        """Initialize QMovie instances for idle and running animations and scale them similarly."""
        try:
            wait_path = self.assets_dir / 'sonic-wait.gif'
            run_path = self.assets_dir / 'sonic-run.gif'

            if wait_path.exists():
                self.sonic_wait_movie = QMovie(str(wait_path))
                self.sonic_wait_movie.setCacheMode(QMovie.CacheAll)
            if run_path.exists():
                self.sonic_run_movie = QMovie(str(run_path))
                self.sonic_run_movie.setCacheMode(QMovie.CacheAll)

            # Scale both to a common target height, preserving aspect ratio
            target_height = 140
            for movie in (self.sonic_wait_movie, self.sonic_run_movie):
                if movie:
                    movie.jumpToFrame(0)
                    frame_size = movie.frameRect().size()
                    orig_w = max(frame_size.width(), 1)
                    orig_h = max(frame_size.height(), 1)
                    scaled_w = int(orig_w * (target_height / orig_h))
                    movie.setScaledSize(QSize(scaled_w, target_height))

        except Exception:
            self.sonic_wait_movie = None
            self.sonic_run_movie = None

    def _set_idle_animation(self):
        """Show the idle (waiting) animation under the Update button."""
        if self.sonic_label is None:
            return
        if self.sonic_run_movie and self.sonic_label.movie() is self.sonic_run_movie:
            self.sonic_run_movie.stop()
        if self.sonic_wait_movie:
            self.sonic_label.setMovie(self.sonic_wait_movie)
            self.sonic_wait_movie.start()
        else:
            self.sonic_label.setText("")

    def _set_running_animation(self):
        """Show the running animation while an update is ongoing."""
        if self.sonic_label is None:
            return
        if self.sonic_wait_movie and self.sonic_label.movie() is self.sonic_wait_movie:
            self.sonic_wait_movie.stop()
        if self.sonic_run_movie:
            self.sonic_label.setMovie(self.sonic_run_movie)
            self.sonic_run_movie.start()
        else:
            self.sonic_label.setText("")
    
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
        self.progress_frame.setObjectName("progress_frame")
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
        
        footer_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self._refresh_data)
        footer_layout.addWidget(self.refresh_button)
        
        # Exit button
        self.exit_button = QPushButton("🛑 Exit")
        self.exit_button.setObjectName("exitButton")
        self.exit_button.clicked.connect(self._exit_application)
        footer_layout.addWidget(self.exit_button)
        
        layout.addLayout(footer_layout)
    
    def _setup_focus_system(self):
        """Set up gamepad focus management system."""
        # List of focusable widgets in tab order
        self.focusable_widgets = [
            self.version_combo,
            self.location_combo, 
            self.update_button,
            self.refresh_button,
            self.exit_button
        ]
        
        # Set focus policies on all widgets
        for widget in self.focusable_widgets:
            widget.setFocusPolicy(Qt.StrongFocus)
            
        # Set initial focus to first widget
        if self.focusable_widgets:
            self.current_focus_index = self._find_next_enabled_index(start_index=0, step=1)
            self._update_focus()
            print(f"Focus system initialized with {len(self.focusable_widgets)} widgets")

    def _find_next_enabled_index(self, start_index: int, step: int) -> int:
        """Find the next index in focusable_widgets that is enabled.

        step: 1 for forward/down, -1 for backward/up
        """
        if not self.focusable_widgets:
            return 0

        count = len(self.focusable_widgets)
        index = start_index % count
        for _ in range(count):
            widget = self.focusable_widgets[index]
            if widget.isEnabled():
                return index
            index = (index + step) % count
        return start_index % count
    
    def _update_focus(self):
        """Update the currently focused widget."""
        if not self.focusable_widgets:
            return
            
        # Clear focus from all widgets
        for widget in self.focusable_widgets:
            widget.clearFocus()
            
        # Set focus to current widget
        current_widget = self.focusable_widgets[self.current_focus_index]
        current_widget.setFocus(Qt.TabFocusReason)
        
        # Debug output
        print(f"Focus set to widget {self.current_focus_index}: {type(current_widget).__name__}")
    
    def _navigate_focus(self, direction):
        """Navigate focus up or down through focusable widgets."""
        if not self.focusable_widgets:
            return
        
        print(f"Navigating focus {direction} from index {self.current_focus_index}")
            
        step = -1 if direction == "up" else 1
        next_index = (self.current_focus_index + step) % len(self.focusable_widgets)
        self.current_focus_index = self._find_next_enabled_index(start_index=next_index, step=step)
        self._update_focus()

    def _has_active_popup(self) -> bool:
        """Return True if a popup (e.g., QComboBox dropdown) is open."""
        return QApplication.activePopupWidget() is not None

    def _get_open_combo(self) -> QComboBox | None:
        """Return the QComboBox whose popup is currently open, if any."""
        combos = [self.version_combo, self.location_combo]
        for combo in combos:
            try:
                view = combo.view()
                if view is not None and view.isVisible():
                    return combo
            except Exception:
                continue
        # Fallback: if focus widget is a combo and its popup is open
        fw = QApplication.focusWidget()
        if isinstance(fw, QComboBox):
            view = fw.view()
            if view is not None and view.isVisible():
                return fw
        return None

    def _send_key_to_active_popup(self, key: int):
        """Send a key press/release to the currently active popup widget."""
        popup = QApplication.activePopupWidget()
        if not popup:
            return
        press = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
        release = QKeyEvent(QEvent.KeyRelease, key, Qt.NoModifier)
        QApplication.sendEvent(popup, press)
        QApplication.sendEvent(popup, release)

    def _setup_shortcuts(self):
        """Set up application-wide keyboard shortcuts for navigation and activation."""
        self._shortcuts = []

        def add_shortcut(key_sequence, handler):
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

        # Up navigation: Arrow Up and W
        add_shortcut(Qt.Key_Up, self._shortcut_navigate_up)
        add_shortcut("W", self._shortcut_navigate_up)

        # Down navigation: Arrow Down and S
        add_shortcut(Qt.Key_Down, self._shortcut_navigate_down)
        add_shortcut("S", self._shortcut_navigate_down)

        # Activate: Enter / Return / Space
        add_shortcut(Qt.Key_Return, self._shortcut_activate)
        add_shortcut(Qt.Key_Enter, self._shortcut_activate)
        add_shortcut(Qt.Key_Space, self._shortcut_activate)

        # Exit: Escape
        add_shortcut(Qt.Key_Escape, self._shortcut_exit)

    def _shortcut_navigate_up(self):
        open_combo = self._get_open_combo()
        if open_combo is not None:
            # Move highlight/selection up within the combo
            count = open_combo.count()
            if count > 0:
                new_idx = (open_combo.currentIndex() - 1) % count
                open_combo.setCurrentIndex(new_idx)
            return
        self._navigate_focus("up")

    def _shortcut_navigate_down(self):
        open_combo = self._get_open_combo()
        if open_combo is not None:
            # Move highlight/selection down within the combo
            count = open_combo.count()
            if count > 0:
                new_idx = (open_combo.currentIndex() + 1) % count
                open_combo.setCurrentIndex(new_idx)
            return
        self._navigate_focus("down")

    def _shortcut_activate(self):
        # If a popup is open, let it handle activation/selection
        open_combo = self._get_open_combo()
        if open_combo is not None:
            # Commit current selection and close
            open_combo.hidePopup()
            return
        self._activate_current_widget()

    def _shortcut_exit(self):
        open_combo = self._get_open_combo()
        if open_combo is not None:
            # Close popup without further action
            open_combo.hidePopup()
            return
        self._exit_application()

    def _setup_gamepad(self):
        """Initialize optional Qt Gamepad navigation for Steam/Game Mode."""
        self.gamepad = None
        try:
            from PySide6.QtGamepad import QGamepad, QGamepadManager
        except Exception:
            return

        self._QGamepad = QGamepad
        self._QGamepadManager = QGamepadManager

        self._init_first_available_gamepad()

        # React to hotplug in Steam/Game Mode where the virtual controller may appear after launch
        mgr = QGamepadManager.instance()
        try:
            mgr.connectedGamepadsChanged.connect(self._on_gamepads_changed)
        except Exception:
            # Older bindings may use different signal names; ignore if unavailable
            pass

    def _init_first_available_gamepad(self):
        mgr = self._QGamepadManager.instance()
        devices = mgr.connectedGamepads()
        if not devices:
            return
        device_id = int(devices[0])
        self._bind_gamepad(device_id)

    def _bind_gamepad(self, device_id: int):
        # Clean up any previous instance
        if getattr(self, "gamepad", None) is not None:
            try:
                self.gamepad.deleteLater()
            except Exception:
                pass
        self.gamepad = self._QGamepad(device_id, self)

        # Debounce on-press actions
        def on_changed(pressed: bool, action):
            if pressed:
                action()

        # DPAD navigation
        self.gamepad.buttonUpChanged.connect(lambda v: on_changed(v, self._shortcut_navigate_up))
        self.gamepad.buttonDownChanged.connect(lambda v: on_changed(v, self._shortcut_navigate_down))

        # Left stick as navigation (use threshold)
        def on_axis_y_changed(value: float):
            if abs(value) < 0.6:
                return
            # Throttle repeats with a short timer
            if getattr(self, "_axis_nav_lock", False):
                return
            self._axis_nav_lock = True
            if value < 0:
                self._shortcut_navigate_up()
            else:
                self._shortcut_navigate_down()
            QTimer.singleShot(180, lambda: setattr(self, "_axis_nav_lock", False))

        self.gamepad.axisLeftYChanged.connect(on_axis_y_changed)

        # A/B buttons
        self.gamepad.buttonAChanged.connect(lambda v: on_changed(v, self._shortcut_activate))
        self.gamepad.buttonBChanged.connect(lambda v: on_changed(v, self._shortcut_exit))

        # No logging to status area for gamepad connection

    def _on_gamepads_changed(self):
        try:
            mgr = self._QGamepadManager.instance()
            devices = mgr.connectedGamepads()
        except Exception:
            return
        if devices and self.gamepad is None:
            self._bind_gamepad(int(devices[0]))
        elif not devices and self.gamepad is not None:
            try:
                self.gamepad.deleteLater()
            except Exception:
                pass
            self.gamepad = None
    
    def _activate_current_widget(self):
        """Activate the currently focused widget."""
        if not self.focusable_widgets:
            return
            
        current_widget = self.focusable_widgets[self.current_focus_index]
        print(f"Activating widget {self.current_focus_index}: {type(current_widget).__name__}")
        
        # Handle different widget types
        if isinstance(current_widget, QPushButton):
            current_widget.click()
        elif isinstance(current_widget, QComboBox):
            # Open combo box dropdown
            current_widget.showPopup()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle gamepad and keyboard input events."""
        key = event.key()
        
        # Debug output
        print(f"Key pressed: {key}, current focus index: {self.current_focus_index}")
        
        # D-pad and Left Stick navigation (Arrow keys, WASD)
        if key in [Qt.Key_Up, Qt.Key_W]:
            self._navigate_focus("up")
            event.accept()
            return
        elif key in [Qt.Key_Down, Qt.Key_S]:
            self._navigate_focus("down") 
            event.accept()
            return
        
        # A button - activate current widget (Enter, Space)
        elif key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space]:
            self._activate_current_widget()
            event.accept()
            return
            
        # B button - exit application (Escape)
        elif key == Qt.Key_Escape:
            self._exit_application()
            event.accept()
            return
            
        # Pass other events to parent
        super().keyPressEvent(event)
    
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
                border-width: 3px !important;
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
                border: none !important;
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
            QPushButton:focus {
                border-color: #4a90e2 !important;
                border-width: 3px !important;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4a4a4a, stop:1 #3f3f3f) !important;
                outline: none;
            }
            /* Exit button overrides: red background and red border when not focused; blue border on focus */
            QPushButton#exitButton {
                background: #b71c1c !important; /* deep red */
                border-color: #b71c1c !important;
            }
            QPushButton#exitButton:hover {
                background: #c62828 !important; /* brighter red */
                border-color: #c62828 !important;
            }
            QPushButton#exitButton:pressed {
                background: #8e0000 !important; /* darker red */
                border-color: #8e0000 !important;
            }
            QPushButton#exitButton:focus {
                background: #c62828 !important; /* keep red background when focused */
                border-color: #4a90e2 !important; /* blue border to indicate focus */
                border-width: 3px !important;
            }
            QPushButton:disabled {
                background: #666 !important;
                color: #999 !important;
                border-color: #555 !important;
            }
            QFrame#progress_frame {
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
        # Switch to running animation
        self._set_running_animation()
    
    def _cancel_update(self):
        """Cancel the current update."""
        self.update_manager.cancel_update()
        self._log_message("❌ Update cancelled by user")
        self._hide_progress_panel()
        self.update_button.setEnabled(True)
        self._set_idle_animation()
    
    def _exit_application(self):
        """Exit the application."""
        self.close()
    
    def _on_update_finished(self, success: bool):
        """Handle update completion."""
        # Hide progress panel and re-enable update button
        self._hide_progress_panel()
        self.update_button.setEnabled(True)
        self._set_idle_animation()
        
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
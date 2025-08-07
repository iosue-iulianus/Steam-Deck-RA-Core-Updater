#!/usr/bin/env python3
"""
RetroArch Core Updater for Steam Deck

A modern GUI application for downloading and updating RetroArch cores
specifically designed for Steam Deck users.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path for imports
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.main_window import MainWindow
from utils.helpers import get_system_info, check_dependencies


def check_requirements():
    """Check if all requirements are met."""
    missing_deps = []
    
    # Check system dependencies
    deps = check_dependencies()
    for dep, available in deps.items():
        if not available:
            missing_deps.append(dep)
    
    if missing_deps:
        return False, f"Missing system dependencies: {', '.join(missing_deps)}"
    
    return True, "All requirements met"


def setup_application():
    """Set up the QApplication with Steam Deck optimizations."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("RetroArch Core Updater")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Steam Deck Community")
    app.setApplicationDisplayName("RetroArch Core Updater for Steam Deck")
    
    # Steam Deck specific optimizations
    system_info = get_system_info()
    if system_info.get('is_steam_deck', False):
        # Optimize for Steam Deck screen
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    return app


def show_error_dialog(title, message):
    """Show an error dialog."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()


def main():
    """Main application entry point."""
    try:
        # Check requirements first
        req_ok, req_message = check_requirements()
        if not req_ok:
            show_error_dialog("Missing Dependencies", 
                            f"{req_message}\n\nPlease install the missing dependencies and try again.")
            return 1
        
        # Set up application
        app = setup_application()
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Handle system info display
        system_info = get_system_info()
        if not system_info.get('is_steam_deck', False):
            window._log_message("⚠️ This application is optimized for Steam Deck")
            window._log_message("   It should work on other Linux systems but may not be ideal")
        
        # Start event loop
        return app.exec()
        
    except ImportError as e:
        show_error_dialog("Import Error", 
                        f"Failed to import required modules: {e}\n\nPlease install PySide6 and try again.")
        return 1
    
    except Exception as e:
        show_error_dialog("Unexpected Error", 
                        f"An unexpected error occurred: {e}\n\nPlease check the console output for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
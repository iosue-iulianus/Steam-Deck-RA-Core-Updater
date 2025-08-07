#!/usr/bin/env python3
"""Progress dialog for update operations."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QProgressBar, QPushButton, QTextEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ProgressDialog(QDialog):
    """Dialog showing update progress with cancel capability."""
    
    cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating RetroArch Cores")
        self.setModal(True)
        self.setFixedSize(500, 300)
        
        # Make sure dialog stays on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Updating RetroArch Cores")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Status label
        self.status_label = QLabel("Preparing update...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Log text area (initially hidden)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setVisible(False)
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Show log button
        self.show_log_button = QPushButton("Show Details")
        self.show_log_button.clicked.connect(self._toggle_log)
        button_layout.addWidget(self.show_log_button)
        
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Store initial size
        self._compact_height = 300
        self._expanded_height = 450
    
    def update_progress(self, value: int):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
    
    def update_status(self, message: str):
        """Update the status message."""
        self.status_label.setText(message)
        self.log_text.append(f"[INFO] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def add_error(self, error_message: str):
        """Add an error message to the log."""
        self.log_text.append(f"[ERROR] {error_message}")
        
        # Auto-expand log on error
        if not self.log_text.isVisible():
            self._toggle_log()
    
    def set_finished(self, success: bool):
        """Mark the operation as finished."""
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Update completed successfully!")
            self.cancel_button.setText("Close")
        else:
            self.status_label.setText("Update failed!")
            self.cancel_button.setText("Close")
            
            # Show log on failure
            if not self.log_text.isVisible():
                self._toggle_log()
    
    def _toggle_log(self):
        """Toggle the visibility of the log text area."""
        if self.log_text.isVisible():
            self.log_text.setVisible(False)
            self.show_log_button.setText("Show Details")
            self.setFixedHeight(self._compact_height)
        else:
            self.log_text.setVisible(True)
            self.show_log_button.setText("Hide Details")
            self.setFixedHeight(self._expanded_height)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.cancel_button.text() == "Close":
            self.accept()
        else:
            # Confirm cancellation
            self.status_label.setText("Cancelling...")
            self.cancel_button.setEnabled(False)
            self.cancelled.emit()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.cancel_button.text() != "Close":
            # If operation is still running, emit cancel signal
            self.cancelled.emit()
        event.accept()
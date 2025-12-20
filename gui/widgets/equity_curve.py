"""Equity Curve Widget - Compact placeholder."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from core import AppState


class EquityCurve(QFrame):
    """Compact equity curve placeholder (minimized until data available)."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        self.setObjectName("equityCurve")
        self.setStyleSheet("""
            QFrame#equityCurve {
                background-color: #252930;
                border: 1px solid #3a3f4a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        # MINIMIZE HEIGHT - not a full chart placeholder
        self.setMaximumHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Minimal, informative message
        placeholder = QLabel("📊 Equity curve")
        placeholder.setStyleSheet("font-size: 10pt; color: #6b7280; font-weight: 500;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        
        status = QLabel("Available when system is running")
        status.setStyleSheet("font-size: 8pt; color: #4b5563;")
        status.setAlignment(Qt.AlignCenter)
        layout.addWidget(status)
        
        # Connect to state for future expansion
        app_state.status_changed.connect(self._update_status)
    
    def _update_status(self, status):
        """Update based on system status."""
        # Future: show live chart when running
        pass

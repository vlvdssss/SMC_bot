"""Logs Tab - Live log viewer."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt


class LogsTab(QWidget):
    """Logs viewer tab."""
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: 'Consolas', monospace;")
        layout.addWidget(self.log_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.log_text.clear)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def add_log(self, level: str, message: str):
        """Add log message."""
        color = {
            'INFO': '#e8e9ed',
            'WARNING': '#ffc107',
            'ERROR': '#ff5555'
        }.get(level, '#8b92a0')
        
        self.log_text.append(f'<span style="color: {color};">[{level}] {message}</span>')

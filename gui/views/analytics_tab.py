"""Analytics Tab - Performance analytics and charts."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core import AppState


class AnalyticsTab(QWidget):
    """Analytics tab with charts and metrics."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        layout = QVBoxLayout(self)
        label = QLabel("Analytics Tab - TODO: Implement charts")
        layout.addWidget(label)

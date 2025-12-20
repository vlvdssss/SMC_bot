"""Trades Tab - Trade history table."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget
from core import AppState


class TradesTab(QWidget):
    """Trades history tab."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Direction", "Entry", "P&L", "R", "Status"
        ])
        layout.addWidget(self.table)
        
        app_state.trade_closed.connect(self._add_trade)
    
    def _add_trade(self, trade):
        """Add trade to table."""
        # TODO: Implement
        pass

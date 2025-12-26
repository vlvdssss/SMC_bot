"""
Status Bar Widget - Top status bar showing system state

Displays:
    - System status (RUNNING/STOPPED/PAUSED)
    - Trading mode (DEMO/LIVE)
    - Uptime
    - Portfolio risk usage
    - Alerts indicator
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from datetime import timedelta

from core import AppState, SystemStatus, TradingMode


class StatusBarWidget(QWidget):
    """Status bar widget at top of main window."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        
        self.app_state = app_state
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        # Update timer (1 second)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_uptime)
        self.update_timer.start(1000)
        
        # Initial update
        self._update_display()
    
    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(20)
        
        # System status
        self.status_label = QLabel("● STOPPED")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.status_label.setToolTip("Current system execution status")
        layout.addWidget(self.status_label)
        
        # Mode indicator
        self.mode_label = QLabel("DEMO")
        self.mode_label.setStyleSheet("font-weight: bold;")
        self.mode_label.setToolTip("Trading mode: DEMO (paper) or LIVE (real money)")
        layout.addWidget(self.mode_label)
        
        # Separator
        layout.addWidget(QLabel("|"))
        
        # Uptime
        layout.addWidget(QLabel("Uptime:"))
        self.uptime_label = QLabel("--:--:--")
        self.uptime_label.setStyleSheet("font-family: 'Consolas', monospace;")
        self.uptime_label.setToolTip("System uptime since last start (HH:MM:SS)")
        layout.addWidget(self.uptime_label)
        
        # Separator
        layout.addWidget(QLabel("|"))
        
        # Risk usage
        layout.addWidget(QLabel("Portfolio Risk:"))
        self.risk_label = QLabel("0.0%")
        self.risk_label.setStyleSheet("font-family: 'Consolas', monospace; font-weight: bold;")
        self.risk_label.setToolTip("Current portfolio risk usage as percentage of maximum allowed")
        layout.addWidget(self.risk_label)
        
        # Separator
        layout.addWidget(QLabel("|"))
        
        # MT5 Connection status
        self.mt5_status_label = QLabel("🔌 MT5: Disconnected")
        self.mt5_status_label.setStyleSheet("color: #6b7280; font-size: 9pt;")
        self.mt5_status_label.setToolTip("MetaTrader 5 connection status")
        layout.addWidget(self.mt5_status_label)
        
        # Stretch
        layout.addStretch()
        
        # Alerts (placeholder)
        self.alerts_button = QPushButton("🔔 0")
        self.alerts_button.setFixedSize(60, 30)
        self.alerts_button.setToolTip("Number of active alerts/warnings")
        layout.addWidget(self.alerts_button)
        
        # Set frame style
        self.setStyleSheet("""
            StatusBarWidget {
                background-color: #252930;
                border-bottom: 1px solid #3a3f4a;
            }
        """)
    
    def _connect_signals(self) -> None:
        """Connect app state signals."""
        self.app_state.status_changed.connect(self._update_status)
        self.app_state.mode_changed.connect(self._update_mode)
        self.app_state.metrics_updated.connect(self._update_risk)
    
    def _update_display(self) -> None:
        """Update all display elements."""
        self._update_status(self.app_state.status)
        self._update_mode(self.app_state.mode)
        self._update_uptime()
    
    def _update_status(self, status: SystemStatus) -> None:
        """Update status display."""
        status_text = status.value
        
        # Color coding
        color_map = {
            SystemStatus.STOPPED: "#ff5555",
            SystemStatus.RUNNING: "#00c896",
            SystemStatus.PAUSED: "#ffc107",
            SystemStatus.ERROR: "#ff5555",
        }
        
        color = color_map.get(status, "#8b92a0")
        
        self.status_label.setText(f"● {status_text}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12pt;")
    
    def _update_mode(self, mode: TradingMode) -> None:
        """Update mode display."""
        mode_text = mode.value
        
        # Color coding
        if mode == TradingMode.DEMO:
            color = "#4a9eff"
        else:  # LIVE
            color = "#ffc107"
        
        self.mode_label.setText(mode_text)
        self.mode_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def _update_uptime(self) -> None:
        """Update uptime display."""
        uptime_seconds = self.app_state.uptime
        
        if uptime_seconds is None:
            self.uptime_label.setText("--:--:--")
        else:
            # Format as HH:MM:SS
            td = timedelta(seconds=int(uptime_seconds))
            hours = td.seconds // 3600
            minutes = (td.seconds % 3600) // 60
            seconds = td.seconds % 60
            
            self.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _update_risk(self, metrics) -> None:
        """Update risk display."""
        risk_pct = metrics.risk_used
        
        # Color based on risk level
        if risk_pct < 70:
            color = "#00c896"
        elif risk_pct < 90:
            color = "#ffc107"
        else:
            color = "#ff5555"
        
        self.risk_label.setText(f"{risk_pct:.1f}%")
        self.risk_label.setStyleSheet(
            f"color: {color}; font-family: 'Consolas', monospace; font-weight: bold;"
        )
    
    def update_mt5_status(self, connected: bool, account: str = "") -> None:
        """
        Update MT5 connection status display.
        
        Args:
            connected: Whether MT5 is connected
            account: Account number/name if connected
        """
        if connected:
            status_text = f"🔌 MT5: Connected"
            if account:
                status_text += f" ({account})"
            color = "#00c896"
        else:
            status_text = "🔌 MT5: Disconnected"
            color = "#6b7280"
        
        self.mt5_status_label.setText(status_text)
        self.mt5_status_label.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: 600;")

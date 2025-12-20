"""Portfolio Overview Widget - Instrument cards with visual elevation."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from core import AppState, InstrumentStatus


class InstrumentCard(QFrame):
    """Individual instrument card with ELEVATION and state indication."""
    
    def __init__(self, symbol: str, display_name: str):
        super().__init__()
        self.symbol = symbol
        self.display_name = display_name
        
        self.setObjectName("instrumentCard")
        self._apply_style(is_active=False, pnl=0)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header: Symbol + Icon
        header = QHBoxLayout()
        header.setSpacing(8)
        
        # Icon (minimal, symbolic)
        icon_map = {
            "XAUUSD": "🥇",
            "EURUSD": "💶",
            "GBPUSD": "💷",
            "US30": "📈",
        }
        icon = QLabel(icon_map.get(symbol, "📊"))
        icon.setStyleSheet("font-size: 18pt;")
        header.addWidget(icon)
        
        # Symbol name
        name_label = QLabel(display_name)
        name_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #e8e9ed; letter-spacing: 0.5px;")
        header.addWidget(name_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Tooltip for entire card
        self.setToolTip(f"{display_name} - Click for detailed instrument view")
        
        layout.addSpacing(4)
        
        # PnL - large, prominent
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setStyleSheet("font-size: 20pt; font-weight: 700; color: #8b92a0;")
        self.pnl_label.setToolTip("Current profit/loss for this instrument")
        layout.addWidget(self.pnl_label)
        
        # Status info row
        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        
        # Open positions
        positions_box = QVBoxLayout()
        positions_box.setSpacing(2)
        pos_title = QLabel("Positions")
        pos_title.setStyleSheet("font-size: 7pt; color: #6b7280; text-transform: uppercase;")
        self.positions_label = QLabel("0")
        self.positions_label.setStyleSheet("font-size: 12pt; font-weight: 600; color: #9ca3af;")
        self.positions_label.setToolTip("Number of open positions for this instrument")
        positions_box.addWidget(pos_title)
        positions_box.addWidget(self.positions_label)
        info_row.addLayout(positions_box)
        
        # Risk usage
        risk_box = QVBoxLayout()
        risk_box.setSpacing(2)
        risk_title = QLabel("Risk")
        risk_title.setStyleSheet("font-size: 7pt; color: #6b7280; text-transform: uppercase;")
        self.risk_label = QLabel("0%")
        self.risk_label.setStyleSheet("font-size: 12pt; font-weight: 600; color: #9ca3af;")
        self.risk_label.setToolTip("Risk usage percentage for this instrument")
        risk_box.addWidget(risk_title)
        risk_box.addWidget(self.risk_label)
        info_row.addLayout(risk_box)
        
        info_row.addStretch()
        layout.addLayout(info_row)
        
        layout.addStretch()
    
    def _apply_style(self, is_active: bool, pnl: float):
        """Apply styling with ELEVATION and glow based on state."""
        
        # Base style with shadow (elevation effect)
        base_bg = "#2a2f38"  # Slightly lighter than background
        border_color = "#3a3f4a"
        
        # Glow effect based on P&L and activity
        if is_active:
            if pnl > 0:
                # Green glow for winning positions
                border_color = "#00c896"
                glow = "0px 0px 12px rgba(0, 200, 150, 0.3)"
            elif pnl < 0:
                # Red glow for losing positions
                border_color = "#ff5555"
                glow = "0px 0px 12px rgba(255, 85, 85, 0.3)"
            else:
                # Neutral active glow
                border_color = "#4a9eff"
                glow = "0px 0px 8px rgba(74, 158, 255, 0.2)"
        else:
            # Inactive - subtle elevation only
            glow = "0px 2px 8px rgba(0, 0, 0, 0.3)"
        
        self.setStyleSheet(f"""
            QFrame#instrumentCard {{
                background-color: {base_bg};
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 0px;
            }}
            QFrame#instrumentCard:hover {{
                border-color: #4a9eff;
                background-color: #2f343e;
            }}
        """)
        
        # Note: Qt stylesheets don't support box-shadow,
        # but the border glow effect + lighter background creates elevation
    
    def update_status(self, status: InstrumentStatus):
        """Update card with instrument status."""
        
        # PnL
        pnl_text = f"${status.pnl:+,.2f}"
        pnl_color = "#00c896" if status.pnl > 0 else "#ff5555" if status.pnl < 0 else "#8b92a0"
        self.pnl_label.setText(pnl_text)
        self.pnl_label.setStyleSheet(f"font-size: 20pt; font-weight: 700; color: {pnl_color};")
        
        # Positions
        self.positions_label.setText(str(status.open_positions))
        pos_color = "#4a9eff" if status.open_positions > 0 else "#6b7280"
        self.positions_label.setStyleSheet(f"font-size: 12pt; font-weight: 600; color: {pos_color};")
        
        # Risk
        self.risk_label.setText(f"{status.risk_used:.1f}%")
        risk_color = "#00c896" if status.risk_used < 50 else "#ffc107" if status.risk_used < 80 else "#ff5555"
        self.risk_label.setStyleSheet(f"font-size: 12pt; font-weight: 600; color: {risk_color};")
        
        # Update card styling (elevation + glow)
        self._apply_style(status.is_active, status.pnl)


class PortfolioOverview(QFrame):
    """Portfolio overview with elevated instrument cards."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        self.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create cards for each instrument
        self.xauusd_card = InstrumentCard("XAUUSD", "GOLD")
        layout.addWidget(self.xauusd_card)
        
        self.eurusd_card = InstrumentCard("EURUSD", "EUR/USD")
        layout.addWidget(self.eurusd_card)
        
        layout.addStretch()
        
        # Connect to state
        app_state.instruments_updated.connect(self._update_instruments)
        
        # Initial update
        self._update_instruments(app_state.instruments)
    
    def _update_instruments(self, instruments: dict):
        """Update instrument cards."""
        
        # Update XAUUSD
        if "XAUUSD" in instruments:
            self.xauusd_card.update_status(instruments["XAUUSD"])
        
        # Update EURUSD
        if "EURUSD" in instruments:
            self.eurusd_card.update_status(instruments["EURUSD"])

"""Equity Card Widget - Account metrics with visual hierarchy."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from core import AppState, AccountMetrics


class AnimatedLabel(QLabel):
    """Label with smooth number animation."""
    
    def __init__(self, prefix="$", suffix=""):
        super().__init__()
        self._value = 0.0
        self._prefix = prefix
        self._suffix = suffix
        self._animation = None
        self.setText(f"{prefix}0.00{suffix}")
    
    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = value
        if self._suffix == "%":
            self.setText(f"{self._prefix}{value:.2f}{self._suffix}")
        else:
            self.setText(f"{self._prefix}{value:,.2f}{self._suffix}")
    
    value = Property(float, get_value, set_value)
    
    def animateTo(self, target_value, duration=300):
        """Animate to target value."""
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration)
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(target_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()


class EquityCard(QFrame):
    """Account metrics display with STRONG visual hierarchy."""
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        self.setObjectName("equityCard")
        self.setStyleSheet("""
            QFrame#equityCard {
                background-color: #252930;
                border: 1px solid #3a3f4a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title - small, muted
        title = QLabel("💰 ACCOUNT")
        title.setStyleSheet("font-size: 9pt; font-weight: 600; color: #6b7280; letter-spacing: 1px;")
        title.setToolTip("Account overview - main metrics")
        layout.addWidget(title)
        
        layout.addSpacing(8)
        
        # === HIERARCHY 1: EQUITY (ГЛАВНЫЙ ЭЛЕМЕНТ) ===
        # This is THE most important number - huge, bold, impossible to miss
        self.equity_label = AnimatedLabel("$", "")
        self.equity_label.setStyleSheet("""
            font-size: 32pt; 
            font-weight: 700; 
            color: #e8e9ed;
            letter-spacing: -1.2px;
            line-height: 1.0;
        """)
        self.equity_label.setAlignment(Qt.AlignLeft)
        self.equity_label.setToolTip("Current account equity (balance + unrealized P&L)")
        self.equity_label.setWordWrap(False)
        layout.addWidget(self.equity_label)
        
        # Equity change percentage - right below, smaller but still prominent
        self.equity_pct_label = QLabel("(+0.00%)")
        self.equity_pct_label.setStyleSheet("font-size: 14pt; font-weight: 600; color: #8b92a0;")
        self.equity_pct_label.setToolTip("Equity change percentage from initial balance")
        self.equity_pct_label.setWordWrap(False)
        layout.addWidget(self.equity_pct_label)
        
        layout.addSpacing(16)
        
        # Subtle separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3a3f4a; max-height: 1px;")
        layout.addWidget(sep)
        
        layout.addSpacing(12)
        
        # === HIERARCHY 2: PnL (ВТОРИЧНЫЙ, АКЦЕНТНЫЙ) ===
        # Two columns: Daily and Total PnL
        pnl_row = QHBoxLayout()
        pnl_row.setSpacing(24)
        
        # Daily PnL
        daily_box = QVBoxLayout()
        daily_box.setSpacing(4)
        daily_title = QLabel("DAILY")
        daily_title.setStyleSheet("font-size: 8pt; color: #6b7280; letter-spacing: 0.8px; font-weight: 600;")
        self.daily_pnl_label = AnimatedLabel("$", "")
        self.daily_pnl_label.setStyleSheet("font-size: 16pt; font-weight: 600; color: #e8e9ed;")
        self.daily_pnl_label.setToolTip("Today's profit/loss")
        self.daily_pnl_label.setWordWrap(False)
        daily_box.addWidget(daily_title)
        daily_box.addWidget(self.daily_pnl_label)
        pnl_row.addLayout(daily_box)
        
        # Total PnL
        total_box = QVBoxLayout()
        total_box.setSpacing(4)
        total_title = QLabel("TOTAL")
        total_title.setStyleSheet("font-size: 8pt; color: #6b7280; letter-spacing: 0.8px; font-weight: 600;")
        self.total_pnl_label = AnimatedLabel("$", "")
        self.total_pnl_label.setStyleSheet("font-size: 16pt; font-weight: 600; color: #e8e9ed;")
        self.total_pnl_label.setToolTip("Total profit/loss since start")
        self.total_pnl_label.setWordWrap(False)
        total_box.addWidget(total_title)
        total_box.addWidget(self.total_pnl_label)
        pnl_row.addLayout(total_box)
        
        pnl_row.addStretch()
        layout.addLayout(pnl_row)
        
        layout.addSpacing(16)
        
        # === HIERARCHY 3: SUPPORTING INFO (ВСПОМОГАТЕЛЬНЫЙ) ===
        # Balance and Max DD - small, less prominent
        supporting_row = QHBoxLayout()
        supporting_row.setSpacing(24)
        
        # Balance
        balance_box = QVBoxLayout()
        balance_box.setSpacing(3)
        balance_title = QLabel("Balance")
        balance_title.setStyleSheet("font-size: 10pt; color: #8b92a0; font-weight: 700;")
        self.balance_label = AnimatedLabel("$", "")
        self.balance_label.setStyleSheet("font-size: 15pt; color: #e8e9ed; font-weight: 700;")
        self.balance_label.setToolTip("Account balance (realized equity, without open positions)")
        self.balance_label.setWordWrap(False)
        balance_box.addWidget(balance_title)
        balance_box.addWidget(self.balance_label)
        supporting_row.addLayout(balance_box)
        
        # Max DD - always gets warning treatment
        dd_box = QVBoxLayout()
        dd_box.setSpacing(3)
        dd_title = QLabel("Max DD")
        dd_title.setStyleSheet("font-size: 10pt; color: #8b92a0; font-weight: 700;")
        self.max_dd_label = AnimatedLabel("", "%")
        self.max_dd_label.setStyleSheet("font-size: 15pt; color: #ffc107; font-weight: 700;")
        self.max_dd_label.setToolTip("Maximum drawdown - largest peak-to-trough decline")
        self.max_dd_label.setWordWrap(False)
        dd_box.addWidget(dd_title)
        dd_box.addWidget(self.max_dd_label)
        supporting_row.addLayout(dd_box)
        
        supporting_row.addStretch()
        layout.addLayout(supporting_row)
        
        layout.addStretch()
        
        # Connect to state
        app_state.metrics_updated.connect(self._update_metrics)
        
        # Initial update
        self._update_metrics(app_state.metrics)
    
    def _update_metrics(self, metrics: AccountMetrics):
        """Update metrics with STRONG visual hierarchy."""
        
        # === EQUITY (ГЛАВНЫЙ) - Largest, most prominent ===
        self.equity_label.animateTo(metrics.equity)
        equity_color = "#00c896" if metrics.equity >= metrics.balance else "#ff5555"
        self.equity_label.setStyleSheet(f"""
            font-size: 32pt; 
            font-weight: 700; 
            color: {equity_color};
            letter-spacing: -1.2px;
            line-height: 1.0;
        """)
        
        # Equity percentage
        equity_pct = metrics.equity_pct
        self.equity_pct_label.setText(f"({equity_pct:+.2f}%)")
        self.equity_pct_label.setStyleSheet(f"font-size: 14pt; font-weight: 600; color: {equity_color};")
        
        # === PNL (ВТОРИЧНЫЙ) - Medium, accented ===
        # Daily PnL
        self.daily_pnl_label.animateTo(metrics.daily_pnl)
        daily_color = "#00c896" if metrics.daily_pnl >= 0 else "#ff5555"
        self.daily_pnl_label.setStyleSheet(f"font-size: 16pt; font-weight: 600; color: {daily_color};")
        
        # Total PnL
        self.total_pnl_label.animateTo(metrics.total_pnl)
        total_color = "#00c896" if metrics.total_pnl >= 0 else "#ff5555"
        self.total_pnl_label.setStyleSheet(f"font-size: 16pt; font-weight: 600; color: {total_color};")
        
        # === SUPPORTING (ВСПОМОГАТЕЛЬНЫЙ) - Small, muted ===
        # Balance
        self.balance_label.animateTo(metrics.balance)
        
        # Max DD - always warning color
        self.max_dd_label.animateTo(metrics.max_drawdown)
        dd_color = "#00c896" if metrics.max_drawdown < 5 else "#ffc107" if metrics.max_drawdown < 10 else "#ff5555"
        self.max_dd_label.setStyleSheet(f"font-size: 11pt; color: {dd_color}; font-weight: 600;")

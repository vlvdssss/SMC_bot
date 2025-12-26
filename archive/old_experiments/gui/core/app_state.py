"""
Application State Manager

Maintains the current state of the trading system.
This is the single source of truth for all GUI components.

State includes:
    - System status (running, stopped, paused)
    - Trading mode (demo, live)
    - Account metrics (balance, equity, P&L, DD)
    - Portfolio positions
    - Recent trades
    - System health

The state manager receives updates from the DataBridge and
notifies all subscribed widgets when state changes.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal


class SystemStatus(Enum):
    """System execution status."""
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class TradingMode(Enum):
    """Trading mode."""
    DEMO = "DEMO"
    LIVE = "LIVE"


class SystemHealth(Enum):
    """System health indicator."""
    STABLE = "STABLE"
    CAUTION = "CAUTION"
    RISKY = "RISKY"


@dataclass
class AccountMetrics:
    """Account-level metrics."""
    balance: float = 0.0
    equity: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    risk_used: float = 0.0  # Percentage (0-100)
    
    @property
    def equity_pct(self) -> float:
        """Equity change percentage."""
        if self.balance == 0:
            return 0.0
        return ((self.equity - self.balance) / self.balance) * 100


@dataclass
class InstrumentStatus:
    """Per-instrument status."""
    symbol: str
    pnl: float = 0.0
    open_positions: int = 0
    risk_used: float = 0.0  # Percentage
    last_trade_time: Optional[datetime] = None
    win_rate: float = 0.0
    
    @property
    def is_active(self) -> bool:
        """Whether instrument has open positions."""
        return self.open_positions > 0


@dataclass
class Trade:
    """Individual trade record."""
    id: int
    symbol: str
    direction: str  # BUY or SELL
    entry_price: float
    tp: float
    sl: float
    lot_size: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    status: str = "OPEN"  # OPEN, WIN, LOSS, BE
    
    @property
    def duration(self) -> Optional[float]:
        """Trade duration in hours."""
        if self.exit_time is None:
            return None
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 3600


class AppState(QObject):
    """
    Central application state manager.
    
    Maintains current state and emits signals when state changes.
    All GUI widgets should subscribe to these signals to update their displays.
    """
    
    # Signals for state changes
    status_changed = Signal(SystemStatus)
    mode_changed = Signal(TradingMode)
    health_changed = Signal(SystemHealth)
    metrics_updated = Signal(AccountMetrics)
    instruments_updated = Signal(dict)  # {symbol: InstrumentStatus}
    trade_opened = Signal(Trade)
    trade_closed = Signal(Trade)
    alert_raised = Signal(str, str)  # (level, message)
    
    def __init__(self, mode: str = "demo", readonly: bool = False):
        """
        Initialize application state.
        
        Args:
            mode: Trading mode ("demo" or "live")
            readonly: Whether app is in read-only mode
        """
        super().__init__()
        
        # System settings
        self._status = SystemStatus.STOPPED
        self._mode = TradingMode.DEMO if mode == "demo" else TradingMode.LIVE
        self._readonly = readonly
        self._health = SystemHealth.STABLE
        
        # Metrics
        self._metrics = AccountMetrics()
        self._instruments: Dict[str, InstrumentStatus] = {}
        self._trades: List[Trade] = []
        
        # Statistics
        self._start_time: Optional[datetime] = None
        self._losing_streak = 0
        self._winning_streak = 0
        
    # === Properties ===
    
    @property
    def status(self) -> SystemStatus:
        """Current system status."""
        return self._status
    
    @property
    def mode(self) -> TradingMode:
        """Current trading mode."""
        return self._mode
    
    @property
    def is_readonly(self) -> bool:
        """Whether app is in read-only mode."""
        return self._readonly
    
    @property
    def health(self) -> SystemHealth:
        """Current system health."""
        return self._health
    
    @property
    def metrics(self) -> AccountMetrics:
        """Current account metrics."""
        return self._metrics
    
    @property
    def instruments(self) -> Dict[str, InstrumentStatus]:
        """Current instrument statuses."""
        return self._instruments.copy()
    
    @property
    def trades(self) -> List[Trade]:
        """All trades (sorted by time)."""
        return sorted(self._trades, key=lambda t: t.entry_time, reverse=True)
    
    @property
    def open_trades(self) -> List[Trade]:
        """Currently open trades."""
        return [t for t in self._trades if t.status == "OPEN"]
    
    @property
    def uptime(self) -> Optional[float]:
        """Uptime in seconds since start."""
        if self._start_time is None:
            return None
        return (datetime.now() - self._start_time).total_seconds()
    
    # === State Modifiers ===
    
    def set_status(self, status: SystemStatus) -> None:
        """Change system status."""
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)
            
            # Track start time
            if status == SystemStatus.RUNNING and self._start_time is None:
                self._start_time = datetime.now()
            elif status == SystemStatus.STOPPED:
                self._start_time = None
    
    def set_mode(self, mode: TradingMode) -> None:
        """Change trading mode."""
        if mode != self._mode:
            self._mode = mode
            self.mode_changed.emit(mode)
    
    def update_metrics(self, **kwargs) -> None:
        """
        Update account metrics.
        
        Args:
            **kwargs: Metric fields to update (balance, equity, etc.)
        """
        for key, value in kwargs.items():
            if hasattr(self._metrics, key):
                setattr(self._metrics, key, value)
        
        self.metrics_updated.emit(self._metrics)
        
        # Recalculate health
        self._update_health()
    
    def update_instrument(self, symbol: str, **kwargs) -> None:
        """
        Update instrument status.
        
        Args:
            symbol: Instrument symbol (e.g., "XAUUSD")
            **kwargs: Status fields to update
        """
        if symbol not in self._instruments:
            self._instruments[symbol] = InstrumentStatus(symbol=symbol)
        
        for key, value in kwargs.items():
            if hasattr(self._instruments[symbol], key):
                setattr(self._instruments[symbol], key, value)
        
        self.instruments_updated.emit(self._instruments)
    
    def add_trade(self, trade: Trade) -> None:
        """
        Add new trade to history.
        
        Args:
            trade: Trade object
        """
        self._trades.append(trade)
        self.trade_opened.emit(trade)
    
    def close_trade(self, trade_id: int, exit_price: float, pnl: float, 
                    r_multiple: float) -> None:
        """
        Close an open trade.
        
        Args:
            trade_id: Trade ID
            exit_price: Exit price
            pnl: Profit/Loss
            r_multiple: R-multiple result
        """
        for trade in self._trades:
            if trade.id == trade_id and trade.status == "OPEN":
                trade.exit_time = datetime.now()
                trade.exit_price = exit_price
                trade.pnl = pnl
                trade.r_multiple = r_multiple
                trade.status = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE"
                
                # Update streaks
                if trade.status == "WIN":
                    self._winning_streak += 1
                    self._losing_streak = 0
                elif trade.status == "LOSS":
                    self._losing_streak += 1
                    self._winning_streak = 0
                
                self.trade_closed.emit(trade)
                break
    
    def update_from_baza(self, data: dict) -> None:
        """
        Update state from BAZA system data.
        
        This is called by DataBridge when new data arrives.
        
        Args:
            data: Dictionary with BAZA system data
        """
        # Update metrics
        if 'balance' in data:
            self.update_metrics(balance=data['balance'])
        if 'equity' in data:
            self.update_metrics(equity=data['equity'])
        if 'daily_pnl' in data:
            self.update_metrics(daily_pnl=data['daily_pnl'])
        
        # Update instruments
        if 'instruments' in data:
            for symbol, inst_data in data['instruments'].items():
                self.update_instrument(symbol, **inst_data)
        
        # Update trades
        if 'new_trade' in data:
            self.add_trade(Trade(**data['new_trade']))
        
        if 'closed_trade' in data:
            self.close_trade(**data['closed_trade'])
    
    def raise_alert(self, level: str, message: str) -> None:
        """
        Raise an alert.
        
        Args:
            level: Alert level ("info", "warning", "error")
            message: Alert message
        """
        self.alert_raised.emit(level, message)
    
    # === Private Methods ===
    
    def _update_health(self) -> None:
        """Recalculate system health indicator."""
        score = 100
        
        # Drawdown penalty
        dd = self._metrics.current_drawdown
        if dd > 10:
            score -= (dd - 10) * 3
        
        # Losing streak penalty
        if self._losing_streak > 3:
            score -= (self._losing_streak - 3) * 5
        
        # Risk usage penalty
        risk_pct = self._metrics.risk_used / 100.0
        if risk_pct > 0.8:
            score -= (risk_pct - 0.8) * 50
        
        # Determine health level
        if score >= 80:
            new_health = SystemHealth.STABLE
        elif score >= 60:
            new_health = SystemHealth.CAUTION
        else:
            new_health = SystemHealth.RISKY
        
        # Emit if changed
        if new_health != self._health:
            self._health = new_health
            self.health_changed.emit(new_health)
            
            # Raise alert if degraded
            if new_health == SystemHealth.CAUTION:
                self.raise_alert("warning", "System health: CAUTION")
            elif new_health == SystemHealth.RISKY:
                self.raise_alert("error", "System health: RISKY")
    
    # === Utility Methods ===
    
    def get_stats(self) -> dict:
        """
        Get current statistics summary.
        
        Returns:
            Dictionary with key statistics
        """
        closed_trades = [t for t in self._trades if t.status != "OPEN"]
        wins = [t for t in closed_trades if t.status == "WIN"]
        
        return {
            'total_trades': len(closed_trades),
            'open_trades': len(self.open_trades),
            'win_rate': len(wins) / len(closed_trades) * 100 if closed_trades else 0,
            'losing_streak': self._losing_streak,
            'winning_streak': self._winning_streak,
            'uptime': self.uptime,
        }

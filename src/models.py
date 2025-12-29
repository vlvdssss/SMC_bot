"""
Trading Models

Модели данных для торговых операций.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeRequest:
    """Запрос на открытие сделки."""

    symbol: str
    direction: str  # 'buy' or 'sell'
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_amount: float
    risk_reward_ratio: float
    source: str  # 'manual', 'strategy', 'ai'
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Валидация после инициализации."""
        if self.direction not in ['buy', 'sell']:
            raise ValueError(f"Invalid direction: {self.direction}")

        if self.source not in ['manual', 'strategy', 'ai']:
            raise ValueError(f"Invalid source: {self.source}")

        if self.lot_size <= 0:
            raise ValueError("Lot size must be positive")

        if self.risk_amount <= 0:
            raise ValueError("Risk amount must be positive")


@dataclass
class TradeResult:
    """Результат выполнения сделки."""

    success: bool
    ticket: Optional[int] = None
    error_message: Optional[str] = None
    executed_price: Optional[float] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.success and not self.ticket:
            raise ValueError("Successful trade must have a ticket")


@dataclass
class AIPrediction:
    """AI-прогноз для ручной торговли."""

    market_bias: str  # 'bullish', 'bearish', 'range'
    trade_alignment: str  # 'aligned', 'neutral', 'risky'
    scenarios: Dict[str, str]
    invalidation_levels: list
    confidence: str  # 'low', 'medium', 'high'
    comment: str
    timestamp: datetime
    context: Dict[str, Any]

    def __post_init__(self):
        """Валидация."""
        if self.market_bias not in ['bullish', 'bearish', 'range']:
            raise ValueError(f"Invalid market_bias: {self.market_bias}")

        if self.trade_alignment not in ['aligned', 'neutral', 'risky']:
            raise ValueError(f"Invalid trade_alignment: {self.trade_alignment}")

        if self.confidence not in ['low', 'medium', 'high']:
            raise ValueError(f"Invalid confidence: {self.confidence}")
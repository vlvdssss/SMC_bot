"""
Manual Trade State - состояние ручной торговли.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ManualTradeState:
    """Состояние ручной торговли."""

    # Основные параметры
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    direction: str = "buy"

    # Ценовые уровни
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0

    # Риск менеджмент
    risk_amount: float = 1.0  # $ или %
    lot_size: float = 0.0
    risk_reward_ratio: float = 0.0

    # Market data
    bid_price: float = 0.0
    ask_price: float = 0.0
    spread: float = 0.0

    # Флаги
    auto_update_prices: bool = True
    prices_locked: bool = False

    # Метаданные
    last_update: datetime = field(default_factory=datetime.now)
    market_data_timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Инициализация."""
        self.last_update = datetime.now()

    def update_from_market_data(self, bid: float, ask: float, spread: float):
        """Обновление рыночных данных."""
        self.bid_price = bid
        self.ask_price = ask
        self.spread = spread
        self.market_data_timestamp = datetime.now()
        
        # Автоматически обновляем entry_price на основе direction
        if self.direction == "buy":
            self.entry_price = ask
        elif self.direction == "sell":
            self.entry_price = bid
        else:
            self.entry_price = bid

        # Автообновление entry price если включено
        if self.auto_update_prices and not self.prices_locked:
            if self.direction == "buy":
                self.entry_price = ask
            else:  # sell
                self.entry_price = bid

        self.last_update = datetime.now()

    def set_symbol(self, symbol: str):
        """Установка символа."""
        self.symbol = symbol
        self.last_update = datetime.now()

    def set_timeframe(self, timeframe: str):
        """Установка таймфрейма."""
        self.timeframe = timeframe
        self.last_update = datetime.now()

    def set_direction(self, direction: str):
        """Установка направления."""
        if direction in ["buy", "sell"]:
            self.direction = direction
            # Обновить entry price при смене направления
            if self.auto_update_prices and not self.prices_locked:
                if direction == "buy" and self.ask_price > 0:
                    self.entry_price = self.ask_price
                elif direction == "sell" and self.bid_price > 0:
                    self.entry_price = self.bid_price
            self.last_update = datetime.now()

    def set_entry_price(self, price: float):
        """Установка цены входа."""
        self.entry_price = price
        self.last_update = datetime.now()

    def set_stop_loss(self, price: float):
        """Установка стоп-лосса."""
        self.stop_loss = price
        self.last_update = datetime.now()

    def set_take_profit(self, price: float):
        """Установка тейк-профита."""
        self.take_profit = price
        self.last_update = datetime.now()

    def set_risk_amount(self, risk: float):
        """Установка риска."""
        self.risk_amount = risk
        self.last_update = datetime.now()

    def set_lot_size(self, lot: float):
        """Установка объема."""
        self.lot_size = lot
        self.last_update = datetime.now()

    def set_rr_ratio(self, rr: float):
        """Установка RR ratio."""
        self.risk_reward_ratio = rr
        self.last_update = datetime.now()

    def lock_prices(self, locked: bool = True):
        """Блокировка цен от автообновления."""
        self.prices_locked = locked
        self.last_update = datetime.now()

    def reset(self):
        """Сброс состояния."""
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.lot_size = 0.0
        self.risk_reward_ratio = 0.0
        self.prices_locked = False
        self.last_update = datetime.now()

    def is_valid(self) -> bool:
        """Проверка валидности состояния."""
        return (
            self.symbol and
            self.timeframe and
            self.direction in ["buy", "sell"] and
            self.entry_price > 0 and
            self.stop_loss > 0 and
            self.take_profit > 0 and
            self.risk_amount > 0
        )

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_amount': self.risk_amount,
            'lot_size': self.lot_size,
            'risk_reward_ratio': self.risk_reward_ratio,
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'spread': self.spread,
            'auto_update_prices': self.auto_update_prices,
            'prices_locked': self.prices_locked,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'market_data_timestamp': self.market_data_timestamp.isoformat() if self.market_data_timestamp else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ManualTradeState':
        """Десериализация из словаря."""
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                if key in ['last_update', 'market_data_timestamp'] and value:
                    setattr(state, key, datetime.fromisoformat(value))
                else:
                    setattr(state, key, value)
        return state
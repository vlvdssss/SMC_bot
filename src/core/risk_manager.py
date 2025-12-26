"""
Risk Manager - Управление рисками портфеля
"""

import logging
from typing import Dict, List
from datetime import datetime, time

class RiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('RiskManager')
        
        # Настройки рисков
        self.max_daily_loss_percent = config.get('max_daily_loss_percent', 5.0)
        self.max_open_positions = config.get('max_open_positions', 4)
        self.max_lot_size = config.get('max_lot_size', 1.0)
        self.max_daily_trades = config.get('max_daily_trades', 10)
        
        # Отслеживание
        self.daily_trades = {}
        self.daily_pnl = {}
        self.open_positions = 0
    
    def can_open_position(self, instrument: str, lot_size: float, account_balance: float) -> bool:
        """Проверка возможности открытия позиции"""
        
        # Проверка максимального количества открытых позиций
        if self.open_positions >= self.max_open_positions:
            self.logger.warning(f"Maximum open positions ({self.max_open_positions}) reached")
            return False
        
        # Проверка размера лота
        if lot_size > self.max_lot_size:
            self.logger.warning(f"Lot size {lot_size} exceeds maximum {self.max_lot_size}")
            return False
        
        # Проверка дневного лимита сделок
        today = datetime.now().date()
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
        
        if self.daily_trades[today] >= self.max_daily_trades:
            self.logger.warning(f"Daily trades limit ({self.max_daily_trades}) reached")
            return False
        
        # Проверка дневного убытка
        if today in self.daily_pnl and self.daily_pnl[today] < -account_balance * self.max_daily_loss_percent / 100:
            self.logger.warning(f"Daily loss limit ({self.max_daily_loss_percent}%) reached")
            return False
        
        return True
    
    def validate_signal(self, signal: Dict, current_price: float, account_balance: float) -> bool:
        """Валидация торгового сигнала"""
        
        # Проверка SL/TP расстояния
        if 'sl' not in signal or 'tp' not in signal:
            self.logger.error("Signal missing SL or TP")
            return False
        
        # Для BUY: SL < entry < TP
        if signal['direction'] == 'BUY':
            if not (signal['sl'] < current_price < signal['tp']):
                self.logger.warning("Invalid SL/TP levels for BUY signal")
                return False
        # Для SELL: TP < entry < SL
        elif signal['direction'] == 'SELL':
            if not (signal['tp'] < current_price < signal['sl']):
                self.logger.warning("Invalid SL/TP levels for SELL signal")
                return False
        
        # Расчет размера позиции
        risk_amount = account_balance * signal.get('risk_percent', 1.0) / 100
        stop_distance = abs(current_price - signal['sl'])
        
        if stop_distance == 0:
            self.logger.error("Stop distance cannot be zero")
            return False
        
        lot_size = risk_amount / (stop_distance * 100000)  # Для EURUSD, упрощено
        
        return self.can_open_position(signal.get('instrument', 'UNKNOWN'), lot_size, account_balance)
    
    def update_daily_stats(self, pnl: float):
        """Обновление дневной статистики"""
        today = datetime.now().date()
        
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
            self.daily_pnl[today] = 0
        
        self.daily_trades[today] += 1
        self.daily_pnl[today] += pnl
    
    def position_opened(self):
        """Уведомление об открытии позиции"""
        self.open_positions += 1
    
    def position_closed(self):
        """Уведомление о закрытии позиции"""
        self.open_positions = max(0, self.open_positions - 1)
    
    def get_risk_status(self) -> Dict:
        """Получение статуса рисков"""
        today = datetime.now().date()
        
        return {
            'open_positions': self.open_positions,
            'daily_trades': self.daily_trades.get(today, 0),
            'daily_pnl': self.daily_pnl.get(today, 0),
            'max_daily_loss_percent': self.max_daily_loss_percent,
            'max_open_positions': self.max_open_positions,
            'max_daily_trades': self.max_daily_trades
        }
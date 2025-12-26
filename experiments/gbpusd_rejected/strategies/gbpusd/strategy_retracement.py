"""
GBPUSD SMC Retracement Strategy - FINAL TEST

Классическая SMC Retracement логика для GBPUSD.
Аналогична EURUSD стратегии (без агрессии).

СТАТУС: FINAL TEST
ВЕРСИЯ: v1.0 (Final)
ДАТА: 20 декабря 2025

Это ПОСЛЕДНИЙ тест GBPUSD.
Если FAIL - GBPUSD полностью исключается из портфеля.
"""

import pandas as pd
import numpy as np


class StrategyGBPUSD_SMC_Retracement:
    """
    Классический SMC Retracement для GBPUSD.
    
    Логика:
    1. H1: BOS detection (direction filter)
    2. M15: Order Block identification
    3. M15: Entry на retracement в OB
    4. Premium/Discount зоны
    
    НИКАКИХ дополнительных фильтров.
    ПРОСТАЯ и ЧИСТАЯ логика.
    """
    
    def __init__(self):
        """Инициализация."""
        self.name = "GBPUSD SMC Retracement"
        self.version = "1.0 (Final Test)"
        
        # Data
        self.h1_data = None
        self.m15_data = None
        
        # H1 context
        self.h1_direction = None  # 'BULLISH' / 'BEARISH' / None
        self.bos_detected = False
        self.swing_high = None
        self.swing_low = None
        
        # M15 Order Blocks
        self.bullish_ob = None  # {'high': x, 'low': x}
        self.bearish_ob = None
        
        # Parameters
        self.swing_lookback = 10  # Для определения swing high/low
        self.ob_lookback = 20     # Lookback для поиска OB
        self.risk_reward = 2.0    # RR = 2:1
        
        # Point
        self.point = 0.00001  # 5 decimals
    
    def load_data(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame):
        """Загрузка данных."""
        self.h1_data = h1_data.copy()
        self.m15_data = m15_data.copy()
    
    def build_context(self, h1_idx: int):
        """
        H1 контекст - BOS detection.
        
        Args:
            h1_idx: Индекс H1 бара
        """
        if h1_idx < self.swing_lookback + 5:
            self.h1_direction = None
            return
        
        # Получаем недавние свинги
        lookback = self.swing_lookback
        start = max(0, h1_idx - lookback - 5)
        window = self.h1_data.iloc[start:h1_idx + 1]
        
        # Находим swing high/low
        recent = window.tail(lookback)
        self.swing_high = recent['high'].max()
        self.swing_low = recent['low'].min()
        
        # Текущий бар
        current = self.h1_data.iloc[h1_idx]
        
        # BOS detection
        # Bullish BOS: цена пробивает swing high
        if current['close'] > self.swing_high:
            self.h1_direction = 'BULLISH'
            self.bos_detected = True
        
        # Bearish BOS: цена пробивает swing low
        elif current['close'] < self.swing_low:
            self.h1_direction = 'BEARISH'
            self.bos_detected = True
        
        # Нет BOS - сохраняем предыдущее направление
        # (не сбрасываем direction после каждого бара)
    
    def _find_bullish_ob(self, m15_bars: pd.DataFrame) -> dict:
        """
        Поиск Bullish Order Block (МАКСИМАЛЬНО УПРОЩЁННО).
        
        OB = любая свеча перед большим движением вверх.
        """
        if len(m15_bars) < 3:
            return None
        
        # Берём последние 10 баров
        recent = m15_bars.tail(10)
        
        # Ищем импульс (любое движение > 15 pips)
        for i in range(len(recent) - 1, 1, -1):
            current = recent.iloc[i]
            prev = recent.iloc[i - 1]
            
            # Любое движение вверх
            move = current['high'] - prev['low']
            
            if move > 15 * self.point * 10:  # > 15 pips
                # OB = предыдущая свеча
                return {
                    'high': prev['high'],
                    'low': prev['low'],
                    'close': prev['close']
                }
        
        return None
    
    def _find_bearish_ob(self, m15_bars: pd.DataFrame) -> dict:
        """Поиск Bearish Order Block (МАКСИМАЛЬНО УПРОЩЁННО)."""
        if len(m15_bars) < 3:
            return None
        
        # Берём последние 10 баров
        recent = m15_bars.tail(10)
        
        # Ищем импульс (любое движение > 15 pips)
        for i in range(len(recent) - 1, 1, -1):
            current = recent.iloc[i]
            prev = recent.iloc[i - 1]
            
            # Любое движение вниз
            move = prev['high'] - current['low']
            
            if move > 15 * self.point * 10:  # > 15 pips
                # OB = предыдущая свеча
                return {
                    'high': prev['high'],
                    'low': prev['low'],
                    'close': prev['close']
                }
        
        return None
    
    def generate_signal(self, m15_idx: int, current_price: float, current_time) -> dict:
        """
        Генерация сигнала на M15.
        
        Args:
            m15_idx: Индекс M15 бара
            current_price: Текущая цена
            current_time: Время
            
        Returns:
            dict: Сигнал
        """
        signal = {'valid': False}
        
        # Проверка H1 направления
        if self.h1_direction is None:
            return signal
        
        if m15_idx < self.ob_lookback:
            return signal
        
        # Получаем недавние M15 бары
        start = max(0, m15_idx - self.ob_lookback)
        recent_m15 = self.m15_data.iloc[start:m15_idx + 1]
        
        # Ищем Order Blocks
        if self.h1_direction == 'BULLISH':
            self.bullish_ob = self._find_bullish_ob(recent_m15)
            
            if self.bullish_ob:
                # Проверка retracement в OB
                if (current_price <= self.bullish_ob['high'] and 
                    current_price >= self.bullish_ob['low']):
                    
                    # BUY signal
                    entry = current_price
                    sl = self.bullish_ob['low'] - (10 * self.point * 10)  # 10 pips buffer
                    
                    risk = entry - sl
                    if risk <= 0:
                        return signal
                    
                    tp = entry + (risk * self.risk_reward)
                    
                    return {
                        'valid': True,
                        'direction': 'BUY',
                        'entry_price': entry,
                        'sl': sl,
                        'tp': tp,
                        'risk_reward': self.risk_reward,
                        'reason': f'Bullish retracement to OB ({self.bullish_ob["low"]:.5f}-{self.bullish_ob["high"]:.5f})'
                    }
        
        elif self.h1_direction == 'BEARISH':
            self.bearish_ob = self._find_bearish_ob(recent_m15)
            
            if self.bearish_ob:
                # Проверка retracement в OB
                if (current_price >= self.bearish_ob['low'] and 
                    current_price <= self.bearish_ob['high']):
                    
                    # SELL signal
                    entry = current_price
                    sl = self.bearish_ob['high'] + (10 * self.point * 10)  # 10 pips buffer
                    
                    risk = sl - entry
                    if risk <= 0:
                        return signal
                    
                    tp = entry - (risk * self.risk_reward)
                    
                    return {
                        'valid': True,
                        'direction': 'SELL',
                        'entry_price': entry,
                        'sl': sl,
                        'tp': tp,
                        'risk_reward': self.risk_reward,
                        'reason': f'Bearish retracement to OB ({self.bearish_ob["low"]:.5f}-{self.bearish_ob["high"]:.5f})'
                    }
        
        return signal
    
    def execute_trade(self, signal: dict, balance: float, risk_pct: float = 0.5) -> dict:
        """
        Расчёт позиции.
        
        Args:
            signal: Сигнал
            balance: Баланс
            risk_pct: Риск (default 0.5%)
            
        Returns:
            dict: Параметры сделки
        """
        if not signal['valid']:
            return None
        
        # Risk amount
        risk_amount = balance * (risk_pct / 100)
        
        # SL distance
        if signal['direction'] == 'BUY':
            sl_distance = signal['entry_price'] - signal['sl']
        else:
            sl_distance = signal['sl'] - signal['entry_price']
        
        # SL в pips
        sl_pips = sl_distance / (self.point * 10)
        
        if sl_pips <= 0:
            return None
        
        # Lot size
        pip_value = 10.0  # GBPUSD: $10 per pip per lot
        lot_size = risk_amount / (sl_pips * pip_value)
        lot_size = round(lot_size, 2)
        lot_size = max(0.01, min(lot_size, 1.0))
        
        return {
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'sl': signal['sl'],
            'tp': signal['tp'],
            'lot_size': lot_size,
            'risk_amount': risk_amount,
            'risk_reward': signal['risk_reward'],
            'reason': signal['reason']
        }

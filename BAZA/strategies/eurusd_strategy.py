"""
EURUSD Trading Strategy - SMC Retracement Baseline

Стратегия для торговли валютной пары EUR/USD.

СТАТУС: BASELINE (R&D закрыт до результатов)
ВЕРСИЯ: v1.0
ДАТА СОЗДАНИЯ: 18 декабря 2025

Тип стратегии: SMC Retracement (pullback entries)
Отличается от XAUUSD тем, что EURUSD = более стабильная валютная пара с глубокими откатами.
"""

import pandas as pd
import numpy as np


class StrategyEURUSD_SMC_Retracement:
    """
    SMC Retracement стратегия для EURUSD.
    
    Концепция:
    - EURUSD = ликвидная валютная пара с четкой структурой
    - Глубокие откаты → entry на retracement в OB
    - Premium/Discount зоны работают отлично
    
    Логика:
    1. H1: BOS detection для определения направления тренда
    2. M15: Order Block identification
    3. M15: Premium/Discount зоны
    4. Entry: Retracement в OB + правильная зона
    5. Exit: 2:1 RR, SL = OB или ATR-based
    
    Отличия от XAUUSD:
    - НЕ используем FVG (фокус только на OB)
    - Более консервативные входы (pullback only)
    - Риск 0.5% (vs 1% для XAUUSD)
    """
    
    def __init__(self):
        """Инициализация стратегии для EURUSD"""
        self.instrument = "EURUSD"
        self.htf_timeframe = "H1"
        self.ltf_timeframe = "M15"
        
        # H1 State
        self.last_swing_high_h1 = None
        self.last_swing_low_h1 = None
        self.bos_direction = None  # 'BUY', 'SELL', or None
        self.h1_bos_valid = False
        
        # M15 State
        self.last_ob = None  # Order Block coordinates
        self.h1_high = None
        self.h1_low = None
        
        # Cache
        self._atr_cache = {}
        
        # Daily limits
        self.trades_today = 0
        self.current_date = None
        self.max_trades_per_day = 2
        
        # Data references (будут загружены через load_data)
        self.h1_data = None
        self.m15_data = None
    
    def load_data(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame) -> None:
        """Загрузка данных H1 и M15 в стратегию"""
        self.h1_data = h1_data.copy()
        self.m15_data = m15_data.copy()
    
    def build_context(self, current_h1_idx: int) -> None:
        """
        Построение контекста на основе H1 (HTF analysis).
        
        Обновляет:
        - self.bos_direction
        - self.h1_bos_valid
        - self.h1_high, self.h1_low
        """
        if self.h1_data is None:
            return
        self.analyze_h1(self.h1_data, current_h1_idx)
    
    def generate_signal(self, current_m15_idx: int, current_price: float, 
                       current_time: pd.Timestamp) -> dict:
        """
        Генерация торгового сигнала на M15.
        
        Returns:
            dict: {'direction': str, 'sl': float, 'tp': float, 'valid': bool, 'entry': float}
        """
        if self.m15_data is None:
            return {'valid': False}
        return self.get_signal(self.m15_data, current_m15_idx, current_price)
    
    def execute_trade(self, signal: dict, balance: float, risk_pct: float = 0.5) -> dict:
        """
        Расчет параметров сделки (lot size, P&L).
        
        Args:
            signal: Сигнал от generate_signal()
            balance: Текущий баланс
            risk_pct: Риск в процентах (0.5% для EURUSD)
            
        Returns:
            dict: Параметры сделки для executor
        """
        if not signal['valid']:
            return None
        
        risk_amount = balance * (risk_pct / 100.0)
        points_risk = abs(signal['entry'] - signal['sl'])
        
        lot_size = self._calculate_lot_size(balance, risk_amount, points_risk)
        
        if lot_size <= 0:
            return None
        
        return {
            'direction': signal['direction'],
            'entry': signal['entry'],
            'sl': signal['sl'],
            'tp': signal['tp'],
            'lot_size': lot_size
        }
    
    def get_trade(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame,
                  current_h1_idx: int, current_m15_idx: int,
                  current_price: float, current_time: pd.Timestamp,
                  balance: float) -> dict:
        """
        Главная функция - получение торгового сигнала.
        
        Args:
            h1_data: H1 DataFrame
            m15_data: M15 DataFrame
            current_h1_idx: Индекс в H1 данных
            current_m15_idx: Индекс в M15 данных
            current_price: Текущая цена
            current_time: Текущее время
            balance: Баланс счета
            
        Returns:
            dict: Параметры сделки или None
        """
        # Проверка daily limit
        current_date_only = current_time.date()
        if self.current_date != current_date_only:
            self.current_date = current_date_only
            self.trades_today = 0
        
        if self.trades_today >= self.max_trades_per_day:
            return None
        
        # Шаг 1: Анализ H1
        self.analyze_h1(h1_data, current_h1_idx)
        
        # Шаг 2: Генерация сигнала M15
        signal = self.get_signal(m15_data, current_m15_idx, current_price)
        
        # Шаг 3: Расчет сделки
        if signal['valid']:
            trade = self.execute_trade(signal, balance, risk_pct=0.5)
            if trade:
                self.trades_today += 1
            return trade
        
        return None
    
    # =========================================================================
    # EURUSD SMC RETRACEMENT LOGIC
    # =========================================================================
    
    def analyze_h1(self, h1_data: pd.DataFrame, current_idx: int) -> None:
        """
        Анализ H1 для определения BOS direction.
        
        EURUSD: используем стандартный BOS detection (100 баров lookback).
        """
        if current_idx < 2:
            return
        
        # Поиск swing highs и lows
        start_idx = max(1, current_idx - 100)
        end_idx = min(current_idx - 2, len(h1_data) - 2)
        
        if end_idx < start_idx:
            return
        
        for i in range(start_idx, end_idx + 1):
            # Swing High
            if (h1_data.iloc[i]['high'] > h1_data.iloc[i-1]['high'] and
                h1_data.iloc[i]['high'] > h1_data.iloc[i+1]['high']):
                self.last_swing_high_h1 = h1_data.iloc[i]['high']
            
            # Swing Low
            if (h1_data.iloc[i]['low'] < h1_data.iloc[i-1]['low'] and
                h1_data.iloc[i]['low'] < h1_data.iloc[i+1]['low']):
                self.last_swing_low_h1 = h1_data.iloc[i]['low']
        
        # Проверка BOS
        current_close = h1_data.iloc[current_idx]['close']
        
        if self.last_swing_high_h1 and current_close > self.last_swing_high_h1:
            self.bos_direction = 'BUY'
            self.h1_bos_valid = True
            self.h1_high = h1_data.iloc[current_idx - 10:current_idx]['high'].max()
            self.h1_low = h1_data.iloc[current_idx - 10:current_idx]['low'].min()
        elif self.last_swing_low_h1 and current_close < self.last_swing_low_h1:
            self.bos_direction = 'SELL'
            self.h1_bos_valid = True
            self.h1_high = h1_data.iloc[current_idx - 10:current_idx]['high'].max()
            self.h1_low = h1_data.iloc[current_idx - 10:current_idx]['low'].min()
        else:
            self.bos_direction = None
            self.h1_bos_valid = False
    
    def get_signal(self, m15_data: pd.DataFrame, current_idx: int, 
                   current_price: float) -> dict:
        """
        Получение торгового сигнала на M15 (RETRACEMENT LOGIC).
        
        EURUSD Retracement:
        - Ждем глубоких откатов (50-80% диапазона)
        - Entry в Order Block
        - Проверка Premium/Discount
        - SL = за OB или ATR-based
        - TP = 2:1 RR
        """
        signal = {
            'direction': None, 
            'sl': None, 
            'tp': None, 
            'valid': False,
            'entry': current_price
        }
        
        if not self.bos_direction or current_idx < 20:
            return signal
        
        # Расчет ATR(M15)
        atr = self._calculate_atr_cached(m15_data, current_idx, period=14)
        if atr == 0:
            return signal
        
        # Поиск Order Block (последняя свеча перед импульсом)
        lookback = min(20, current_idx)
        recent_bars = m15_data.iloc[current_idx - lookback:current_idx]
        
        if self.bos_direction == 'BUY':
            # Для BUY: ищем bullish OB (свечу перед движением вверх)
            # Проверяем откат к OB
            
            # OB = последняя down свеча перед up движением
            ob_found = False
            ob_low = None
            ob_high = None
            
            for i in range(len(recent_bars) - 1, 0, -1):
                bar = recent_bars.iloc[i]
                next_bar = recent_bars.iloc[i+1] if i+1 < len(recent_bars) else m15_data.iloc[current_idx]
                
                # Down свеча + следующая up свеча
                if bar['close'] < bar['open'] and next_bar['close'] > next_bar['open']:
                    ob_low = bar['low']
                    ob_high = bar['high']
                    ob_found = True
                    break
            
            if not ob_found:
                return signal
            
            # Проверяем что цена вернулась в OB
            if not (ob_low <= current_price <= ob_high):
                return signal
            
            # Проверяем Premium/Discount (должны быть в Discount для BUY)
            if not self.h1_low or not self.h1_high:
                return signal
            
            h1_range = self.h1_high - self.h1_low
            discount_level = self.h1_low + (h1_range * 0.5)
            
            if current_price > discount_level:
                # В Premium зоне - не входим
                return signal
            
            # Entry на текущей цене
            signal['direction'] = 'BUY'
            signal['sl'] = ob_low - (atr * 0.2)  # SL чуть ниже OB
            sl_distance = current_price - signal['sl']
            signal['tp'] = current_price + (sl_distance * 2.0)  # 2:1 RR
            signal['valid'] = True
            
        elif self.bos_direction == 'SELL':
            # Для SELL: ищем bearish OB
            ob_found = False
            ob_low = None
            ob_high = None
            
            for i in range(len(recent_bars) - 1, 0, -1):
                bar = recent_bars.iloc[i]
                next_bar = recent_bars.iloc[i+1] if i+1 < len(recent_bars) else m15_data.iloc[current_idx]
                
                # Up свеча + следующая down свеча
                if bar['close'] > bar['open'] and next_bar['close'] < next_bar['open']:
                    ob_low = bar['low']
                    ob_high = bar['high']
                    ob_found = True
                    break
            
            if not ob_found:
                return signal
            
            # Проверяем что цена вернулась в OB
            if not (ob_low <= current_price <= ob_high):
                return signal
            
            # Проверяем Premium/Discount (должны быть в Premium для SELL)
            if not self.h1_low or not self.h1_high:
                return signal
            
            h1_range = self.h1_high - self.h1_low
            premium_level = self.h1_low + (h1_range * 0.5)
            
            if current_price < premium_level:
                # В Discount зоне - не входим
                return signal
            
            # Entry на текущей цене
            signal['direction'] = 'SELL'
            signal['sl'] = ob_high + (atr * 0.2)  # SL чуть выше OB
            sl_distance = signal['sl'] - current_price
            signal['tp'] = current_price - (sl_distance * 2.0)  # 2:1 RR
            signal['valid'] = True
        
        return signal
    
    def _calculate_atr_cached(self, df: pd.DataFrame, current_idx: int, 
                              period: int = 14) -> float:
        """Расчет ATR с кэшированием."""
        cache_key = f"atr_{current_idx}_{period}"
        if cache_key in self._atr_cache:
            return self._atr_cache[cache_key]
        
        if current_idx < period:
            return 0.0
        
        recent = df.iloc[current_idx - period:current_idx]
        high_low = recent['high'] - recent['low']
        atr = high_low.mean()
        
        self._atr_cache[cache_key] = atr
        return atr if atr > 0 else 0.0
    
    def _calculate_lot_size(self, balance: float, risk_amount: float, 
                           sl_points: float) -> float:
        """
        Расчет lot size для EURUSD.
        
        EURUSD specs:
        - 1 lot = 100,000 units
        - 1 pip = 0.0001
        - Pip value = 10 USD для 1 лота
        """
        if sl_points <= 0:
            return 0.0
        
        # Для EURUSD: 1 pip = 0.0001 = $10 для 1 лота
        # sl_points уже в ценовых единицах (например, 0.0025)
        sl_pips = sl_points / 0.0001  # Конвертируем в pips
        
        # risk_amount = lot_size * sl_pips * pip_value
        # pip_value = $10 для 1 лота
        lot_size = risk_amount / (sl_pips * 10.0)
        
        # Округляем до 0.01 лота
        lot_size = round(lot_size, 2)
        
        # Минимум 0.01 лота
        return max(0.01, lot_size)

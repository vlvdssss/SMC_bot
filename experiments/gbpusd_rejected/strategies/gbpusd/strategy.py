"""
GBPUSD Trading Strategy - SMC Mean Reversion

Mean Reversion стратегия для торговли GBPUSD.

СТАТУС: CANDIDATE (Screening)
ВЕРСИЯ: v0.1
ДАТА СОЗДАНИЯ: 20 декабря 2025

Тип стратегии: Mean Reversion / Range
Отличается от XAUUSD/EURUSD - торгует ПРОТИВ импульса, на возвратах к среднему.
"""

import pandas as pd
import numpy as np


class StrategyGBPUSD_MeanReversion:
    """
    Mean Reversion стратегия для GBPUSD.
    
    Концепция:
    - GBPUSD = range-bound инструмент с частыми false breakouts
    - Торгуем liquidity sweeps (ложные пробои) и rejection
    - Entry ПРОТИВ импульса, возврат к mid-range
    
    Логика:
    1. H1: Range detection (EH/EL)
    2. M15: Liquidity sweep + rejection
    3. Entry: против sweep direction
    4. TP: mid-range или opposite range
    5. SL: за sweep + buffer
    """
    
    def __init__(self):
        """Инициализация стратегии."""
        self.name = "GBPUSD SMC Mean Reversion"
        self.version = "0.1 (Candidate)"
        self.status = "CANDIDATE"
        
        # Data
        self.h1_data = None
        self.m15_data = None
        
        # H1 context
        self.range_high = None
        self.range_low = None
        self.in_range = False
        self.has_trend = False
        
        # Parameters
        self.min_range_pips = 20          # Уменьшил с 30
        self.max_range_pips = 150         # Увеличил с 80
        self.sweep_buffer_pips = 3        # Уменьшил с 5 (легче триггерить)
        self.rejection_wick_pct = 40      # Уменьшил с 50 (легче rejection)
        self.sl_buffer_pips = 10
        self.risk_reward_min = 1.0        # Уменьшил с 1.2 (больше сигналов)
        
        # Point value for GBPUSD
        self.point = 0.00001  # 5 decimals
    
    def load_data(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame):
        """
        Загрузка H1 и M15 данных.
        
        Args:
            h1_data: H1 OHLC данные
            m15_data: M15 OHLC данные
        """
        self.h1_data = h1_data.copy()
        self.m15_data = m15_data.copy()
    
    def build_context(self, h1_idx: int):
        """
        Построение H1 контекста (упрощённо).
        
        Args:
            h1_idx: Индекс текущего H1 бара
        """
        if h1_idx < 10:
            return
        
        # МАКСИМАЛЬНО ПРОСТОЙ ПОДХОД:
        # Берём recent high/low как "range boundaries"
        lookback = 20
        start_idx = max(0, h1_idx - lookback)
        recent = self.h1_data.iloc[start_idx:h1_idx + 1]
        
        self.range_high = recent['high'].max()
        self.range_low = recent['low'].min()
        
        # Всегда in_range = True (убираем строгую проверку)
        self.in_range = True
        self.has_trend = False
    
    def _find_range_high(self, window: pd.DataFrame) -> float:
        """Найти range high (equal highs)."""
        highs = window['high'].values
        
        # Ищем зону с минимум 2 касаниями
        max_high = np.max(highs)
        tolerance = 10 * self.point  # 10 pips tolerance
        
        touches = np.sum(np.abs(highs - max_high) <= tolerance)
        
        if touches >= 2:
            return max_high
        
        return None
    
    def _find_range_low(self, window: pd.DataFrame) -> float:
        """Найти range low (equal lows)."""
        lows = window['low'].values
        
        # Ищем зону с минимум 2 касаниями
        min_low = np.min(lows)
        tolerance = 10 * self.point  # 10 pips tolerance
        
        touches = np.sum(np.abs(lows - min_low) <= tolerance)
        
        if touches >= 2:
            return min_low
        
        return None
    
    def _detect_trend(self, window: pd.DataFrame) -> bool:
        """Определить наличие тренда (series of breaks)."""
        closes = window['close'].values
        
        # Простая проверка: есть ли серия закрытий выше/ниже range
        if self.range_high is None or self.range_low is None:
            return False
        
        # Последние 5 баров
        recent = closes[-5:]
        
        # Bullish trend: большинство закрытий выше range_high
        above = np.sum(recent > self.range_high)
        if above >= 3:
            return True
        
        # Bearish trend: большинство закрытий ниже range_low
        below = np.sum(recent < self.range_low)
        if below >= 3:
            return True
        
        return False
    
    def generate_signal(self, m15_idx: int, current_price: float, current_time) -> dict:
        """
        Генерация торгового сигнала на M15.
        
        Args:
            m15_idx: Индекс текущего M15 бара
            current_price: Текущая цена
            current_time: Текущее время
            
        Returns:
            dict: Сигнал со всеми параметрами
        """
        # Default: no signal
        signal = {'valid': False}
        
        # Проверка H1 контекста
        if not self.in_range:
            return signal
        
        if m15_idx < 10:
            return signal
        
        # Проверка последних 5 M15 баров на liquidity sweep
        lookback = 5
        recent_bars = self.m15_data.iloc[m15_idx - lookback:m15_idx + 1]
        
        # Check for BULLISH setup (sweep LOW + rejection)
        bullish_signal = self._check_bullish_sweep(recent_bars, current_price)
        if bullish_signal['valid']:
            return bullish_signal
        
        # Check for BEARISH setup (sweep HIGH + rejection)
        bearish_signal = self._check_bearish_sweep(recent_bars, current_price)
        if bearish_signal['valid']:
            return bearish_signal
        
        return signal
    
    def _check_bullish_sweep(self, bars: pd.DataFrame, current_price: float) -> dict:
        """Проверка BULLISH setup (sweep below range_low + rejection)."""
        signal = {'valid': False}
        
        if self.range_low is None:
            return signal
        
        # 1. Проверка sweep (пробой ниже range_low)
        sweep_target = self.range_low - (self.sweep_buffer_pips * self.point * 10)
        has_sweep = np.any(bars['low'].values < sweep_target)
        
        if not has_sweep:
            return signal
        
        # 2. Проверка rejection (длинная нижняя тень + закрытие выше range_low)
        last_bar = bars.iloc[-1]
        
        # Rejection criteria
        bar_range = last_bar['high'] - last_bar['low']
        lower_wick = last_bar['close'] - last_bar['low']
        wick_pct = (lower_wick / bar_range) * 100 if bar_range > 0 else 0
        
        # Rejection = длинная тень + закрытие в range
        is_rejection = (
            wick_pct >= self.rejection_wick_pct and
            last_bar['close'] > self.range_low
        )
        
        if not is_rejection:
            return signal
        
        # 3. Calculate entry, SL, TP
        entry_price = current_price
        sl_price = last_bar['low'] - (self.sl_buffer_pips * self.point * 10)
        
        # TP = mid-range
        mid_range = (self.range_high + self.range_low) / 2
        tp_price = mid_range
        
        # Check RR
        risk = entry_price - sl_price
        reward = tp_price - entry_price
        
        if risk <= 0 or reward <= 0:
            return signal
        
        rr_ratio = reward / risk
        
        if rr_ratio < self.risk_reward_min:
            return signal
        
        # Valid BULLISH signal
        return {
            'valid': True,
            'direction': 'BUY',
            'entry_price': entry_price,
            'sl': sl_price,
            'tp': tp_price,
            'risk_reward': rr_ratio,
            'reason': f'Liquidity sweep below {self.range_low:.5f} + rejection'
        }
    
    def _check_bearish_sweep(self, bars: pd.DataFrame, current_price: float) -> dict:
        """Проверка BEARISH setup (sweep above range_high + rejection)."""
        signal = {'valid': False}
        
        if self.range_high is None:
            return signal
        
        # 1. Проверка sweep (пробой выше range_high)
        sweep_target = self.range_high + (self.sweep_buffer_pips * self.point * 10)
        has_sweep = np.any(bars['high'].values > sweep_target)
        
        if not has_sweep:
            return signal
        
        # 2. Проверка rejection (длинная верхняя тень + закрытие ниже range_high)
        last_bar = bars.iloc[-1]
        
        # Rejection criteria
        bar_range = last_bar['high'] - last_bar['low']
        upper_wick = last_bar['high'] - last_bar['close']
        wick_pct = (upper_wick / bar_range) * 100 if bar_range > 0 else 0
        
        # Rejection = длинная тень + закрытие в range
        is_rejection = (
            wick_pct >= self.rejection_wick_pct and
            last_bar['close'] < self.range_high
        )
        
        if not is_rejection:
            return signal
        
        # 3. Calculate entry, SL, TP
        entry_price = current_price
        sl_price = last_bar['high'] + (self.sl_buffer_pips * self.point * 10)
        
        # TP = mid-range
        mid_range = (self.range_high + self.range_low) / 2
        tp_price = mid_range
        
        # Check RR
        risk = sl_price - entry_price
        reward = entry_price - tp_price
        
        if risk <= 0 or reward <= 0:
            return signal
        
        rr_ratio = reward / risk
        
        if rr_ratio < self.risk_reward_min:
            return signal
        
        # Valid BEARISH signal
        return {
            'valid': True,
            'direction': 'SELL',
            'entry_price': entry_price,
            'sl': sl_price,
            'tp': tp_price,
            'risk_reward': rr_ratio,
            'reason': f'Liquidity sweep above {self.range_high:.5f} + rejection'
        }
    
    def execute_trade(self, signal: dict, balance: float, risk_pct: float = 0.4) -> dict:
        """
        Расчет размера позиции для сигнала.
        
        Args:
            signal: Торговый сигнал
            balance: Текущий баланс
            risk_pct: Процент риска (default 0.4%)
            
        Returns:
            dict: Параметры сделки с lot size
        """
        if not signal['valid']:
            return None
        
        # Risk amount
        risk_amount = balance * (risk_pct / 100)
        
        # SL distance in price
        if signal['direction'] == 'BUY':
            sl_distance = signal['entry_price'] - signal['sl']
        else:
            sl_distance = signal['sl'] - signal['entry_price']
        
        # SL distance in pips
        sl_pips = sl_distance / (self.point * 10)
        
        if sl_pips <= 0:
            return None
        
        # Lot size calculation
        # GBPUSD: 1 lot = 100,000 units, 1 pip = $10
        pip_value = 10.0
        lot_size = risk_amount / (sl_pips * pip_value)
        
        # Round to 0.01
        lot_size = round(lot_size, 2)
        
        # Min/max lot constraints
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

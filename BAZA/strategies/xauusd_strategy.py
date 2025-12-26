"""
XAUUSD Trading Strategy - Phase 2 Baseline (FIXED ENTRY LOGIC)

Стратегия для торговли золотом (XAUUSD) на основе Smart Money Concepts.

СТАТУС: STABLE - Phase 2 Baseline (исправлена логика входа)
ВЕРСИЯ: Final v1.1 (Fixed Entry)
ДАТА ОБНОВЛЕНИЯ: 22 декабря 2025

КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ:
- Сигнал формируется на close текущей свечи M15
- Вход происходит на open СЛЕДУЮЩЕЙ свечи M15
- Устранён look-ahead bias для соответствия live торговле

Торговая логика:
- HTF (H1): BOS detection для определения направления
- LTF (M15): Order Block entry в Premium/Discount зонах
- Risk: 1% per trade, 2:1 RR, 1.5x ATR SL
"""

import pandas as pd
import numpy as np


class StrategyXAUUSD:
    """
    Phase 2 Baseline стратегия для XAUUSD (Gold) с правильной логикой входа.
    
    Логика:
    1. H1: Поиск BOS (break of swing high/low) для направления тренда
    2. M15: Поиск Order Block (2-3 свечи перед импульсом > 1.2 ATR)
    3. M15: Проверка Premium/Discount (60%/40% зон) на close текущей свечи
    4. Entry: На OPEN СЛЕДУЮЩЕЙ свечи (если сигнал валиден)
    5. Exit: 2:1 RR, SL = 1.5x ATR
    
    FIXED: Теперь сигнал на close → вход на next open (как в live торговле)
    """
    
    def __init__(self):
        """Инициализация стратегии для XAUUSD"""
        self.instrument = "XAUUSD"
        self.name = "XAUUSD Phase 2 Baseline"
        self.version = "v1.1 (Fixed Entry)"
        self.htf_timeframe = "H1"
        self.ltf_timeframe = "M15"
        
        # H1 State
        self.last_swing_high_h1 = None
        self.last_swing_low_h1 = None
        self.bos_direction = None  # 'BUY', 'SELL', or None
        self.h1_bos_valid = False
        
        # Cache для оптимизации
        self._atr_cache = {}
        self._swing_cache = {}
    
    def load_data(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame):
        """
        Загрузка данных для стратегии.
        
        Args:
            h1_data: DataFrame с H1 барами
            m15_data: DataFrame с M15 барами
        """
        self.h1_data = h1_data
        self.m15_data = m15_data
    
    def build_context(self, current_h1_idx: int):
        """
        Построение контекста на H1 (HTF анализ).
        
        Определяет направление тренда через BOS.
        
        Args:
            current_h1_idx: Текущий индекс в H1 данных
        """
        self.analyze_h1(self.h1_data, current_h1_idx)
    
    def generate_signal(self, current_m15_idx: int, analysis_price: float, entry_price: float) -> dict:
        """
        Генерация торгового сигнала на M15.
        
        FIXED LOGIC: Анализ на close текущей свечи, вход на open следующей.
        
        Args:
            current_m15_idx: Текущий индекс в M15 данных (свеча которая закрылась)
            analysis_price: Цена для анализа (close текущей свечи)
            entry_price: Цена входа (open следующей свечи)
            
        Returns:
            dict: {
                'direction': 'BUY' | 'SELL' | None,
                'sl': float,
                'tp': float,
                'valid': bool,
                'entry': float (entry_price)
            }
        """
        return self.get_signal(self.m15_data, current_m15_idx, analysis_price, entry_price)
    
    def execute_trade(self, signal: dict, balance: float, risk_pct: float = 1.0) -> dict:
        """
        Расчет параметров сделки.
        
        Args:
            signal: Сигнал от generate_signal()
            balance: Текущий баланс
            risk_pct: Риск на сделку в % (default: 1%)
            
        Returns:
            dict: {
                'direction': str,
                'entry': float,
                'sl': float,
                'tp': float,
                'lot_size': float
            }
        """
        if not signal['valid']:
            return None
        
        # Расчет лот-сайза (XAUUSD contract size = 100 oz)
        entry_price = signal['entry']
        sl_price = signal['sl']
        
        risk_amount = balance * (risk_pct / 100.0)
        stop_loss_value = abs(entry_price - sl_price) * 100  # 100 oz
        
        if stop_loss_value == 0:
            lot_size = 0.0
        else:
            lot_size = risk_amount / stop_loss_value
            lot_size = round(lot_size, 2)
            lot_size = max(0.01, lot_size)
        
        return {
            'direction': signal['direction'],
            'entry': entry_price,
            'sl': signal['sl'],
            'tp': signal['tp'],
            'lot_size': lot_size
        }
    
    def run_cycle(self, current_h1_idx: int, current_m15_idx: int, 
                  analysis_price: float, entry_price: float, balance: float) -> dict:
        """
        Полный цикл: анализ H1 -> генерация сигнала M15 -> расчет сделки.
        
        FIXED: Разделены цены для анализа и входа.
        
        Args:
            current_h1_idx: Индекс в H1 данных
            current_m15_idx: Индекс в M15 данных
            analysis_price: Цена для анализа (close текущей свечи)
            entry_price: Цена входа (open следующей свечи)
            balance: Баланс счета
            
        Returns:
            dict: Параметры сделки или None
        """
        # Шаг 1: Анализ H1
        self.build_context(current_h1_idx)
        
        # Шаг 2: Генерация сигнала M15
        signal = self.generate_signal(current_m15_idx, analysis_price, entry_price)
        
        # Шаг 3: Расчет сделки
        if signal['valid']:
            trade = self.execute_trade(signal, balance)
            return trade
        
        return None
    
    # =========================================================================
    # BASELINE ЛОГИКА (FIXED ENTRY - v1.1)
    # =========================================================================
    
    def analyze_h1(self, h1_data: pd.DataFrame, current_idx: int) -> None:
        """
        Анализ H1 для определения BOS direction.
        
        BASELINE LOGIC - без изменений
        """
        if current_idx < 2:
            return
        
        # Поиск swing highs и lows (последние 100 баров)
        start_idx = max(1, current_idx - 100)
        end_idx = min(current_idx - 1, len(h1_data) - 2)  # -2 чтобы i+1 был валиден
        
        for i in range(start_idx, end_idx + 1):
            # Swing High: high[i] > high[i-1] and high[i] > high[i+1]
            if (h1_data.iloc[i]['high'] > h1_data.iloc[i-1]['high'] and
                h1_data.iloc[i]['high'] > h1_data.iloc[i+1]['high']):
                self.last_swing_high_h1 = h1_data.iloc[i]['high']
            
            # Swing Low: low[i] < low[i-1] and low[i] < low[i+1]
            if (h1_data.iloc[i]['low'] < h1_data.iloc[i-1]['low'] and
                h1_data.iloc[i]['low'] < h1_data.iloc[i+1]['low']):
                self.last_swing_low_h1 = h1_data.iloc[i]['low']
        
        # Проверка BOS на текущем close
        current_close = h1_data.iloc[current_idx]['close']
        
        if self.last_swing_high_h1 and current_close > self.last_swing_high_h1:
            self.bos_direction = 'BUY'
            self.h1_bos_valid = True
        elif self.last_swing_low_h1 and current_close < self.last_swing_low_h1:
            self.bos_direction = 'SELL'
            self.h1_bos_valid = True
        else:
            self.bos_direction = None
            self.h1_bos_valid = False
    
    def get_signal(self, m15_data: pd.DataFrame, current_idx: int, 
                   analysis_price: float, entry_price: float) -> dict:
        """
        Получение торгового сигнала на M15.
        
        FIXED LOGIC: Анализ на analysis_price, вход на entry_price.
        
        Args:
            current_idx: Индекс текущей свечи (которая закрылась)
            analysis_price: Close текущей свечи (для проверки условий)
            entry_price: Open следующей свечи (для входа)
        
        Returns:
            dict: {'direction': str, 'sl': float, 'tp': float, 'valid': bool, 'entry': float}
        """
        signal = {
            'direction': None, 
            'sl': None, 
            'tp': None, 
            'valid': False,
            'entry': entry_price  # ← КРИТИЧЕСКОЕ: вход на следующей свече
        }
        
        if not self.bos_direction or current_idx < 20:
            return signal
        
        # Расчет ATR(M15) за последние 14 баров (до текущей свечи включительно)
        atr = self._calculate_atr_cached(m15_data, current_idx, period=14)
        if atr == 0:
            return signal
        
        # Поиск Order Block (в исторических данных)
        ob_high, ob_low = self._find_order_block(m15_data, current_idx, atr)
        if ob_high is None or ob_low is None:
            return signal
        
        # Проверка что analysis_price (close) был в OB
        if not (ob_low <= analysis_price <= ob_high):
            return signal
        
        # Поиск swing high/low на M15 для Premium/Discount (cached)
        cache_key = f"swing_{current_idx}"
        if cache_key not in self._swing_cache:
            start_idx = max(0, current_idx - 50)
            swing_high_m15 = m15_data.iloc[start_idx:current_idx + 1]['high'].max()
            swing_low_m15 = m15_data.iloc[start_idx:current_idx + 1]['low'].min()
            self._swing_cache[cache_key] = (swing_high_m15, swing_low_m15)
            # Очистка кэша
            if len(self._swing_cache) > 100:
                self._swing_cache.clear()
        else:
            swing_high_m15, swing_low_m15 = self._swing_cache[cache_key]
        
        range_m15 = swing_high_m15 - swing_low_m15
        discount_threshold = swing_low_m15 + 0.6 * range_m15  # 60% зона
        premium_threshold = swing_low_m15 + 0.4 * range_m15   # 40% зона
        
        # Проверка Premium/Discount на analysis_price (close)
        if self.bos_direction == 'BUY':
            if analysis_price > discount_threshold:  # Не в discount (< 60%)
                return signal
            
            # Сигнал валиден, но входим на entry_price (next open)
            signal['direction'] = 'BUY'
            signal['sl'] = entry_price - (atr * 1.5)
            signal['tp'] = entry_price + ((entry_price - signal['sl']) * 2.0)
            signal['valid'] = True
        
        elif self.bos_direction == 'SELL':
            if analysis_price < premium_threshold:  # Не в premium (> 40%)
                return signal
            
            # Сигнал валиден, но входим на entry_price (next open)
            signal['direction'] = 'SELL'
            signal['sl'] = entry_price + (atr * 1.5)
            signal['tp'] = entry_price - ((signal['sl'] - entry_price) * 2.0)
            signal['valid'] = True
        
        return signal
    
    def _calculate_atr_cached(self, df: pd.DataFrame, current_idx: int, 
                              period: int = 14) -> float:
        """Расчет ATR с кэшированием."""
        cache_key = f"atr_{current_idx}_{period}"
        if cache_key in self._atr_cache:
            return self._atr_cache[cache_key]
        
        atr = self._calculate_atr(df, current_idx, period)
        self._atr_cache[cache_key] = atr
        
        # Контроль размера кэша
        if len(self._atr_cache) > 200:
            self._atr_cache.clear()
        
        return atr
    
    def _calculate_atr(self, df: pd.DataFrame, current_idx: int, 
                       period: int = 14) -> float:
        """Расчет ATR."""
        if current_idx < period:
            return 0.0
        
        tr_list = []
        for i in range(current_idx - period + 1, current_idx + 1):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_close = df.iloc[i-1]['close'] if i > 0 else df.iloc[i]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)
        
        return np.mean(tr_list)
    
    def _find_order_block(self, df: pd.DataFrame, current_idx: int, 
                         atr: float) -> tuple:
        """
        Поиск Order Block (2-3 противоположные свечи перед импульсом).
        
        BASELINE LOGIC - без изменений
        """
        if current_idx < 10:
            return None, None
        
        # Lookback максимум 50 баров
        lookback = min(50, current_idx)
        
        for i in range(current_idx - 1, current_idx - lookback, -1):
            if i < 0:
                break
            
            candle = df.iloc[i]
            body = abs(candle['close'] - candle['open'])
            
            # Проверка импульсной свечи
            if self.bos_direction == 'BUY':
                # Бычий импульс
                if candle['close'] > candle['open'] and body > 1.2 * atr:
                    # Поиск последних 2-3 медвежьих свечей перед импульсом
                    ob_candles = []
                    for j in range(i - 1, max(0, i - 10), -1):
                        ob_candle = df.iloc[j]
                        if ob_candle['close'] < ob_candle['open']:
                            ob_candles.append(ob_candle)
                            if len(ob_candles) >= 3:  # До 3 OB
                                break
                    
                    if ob_candles:
                        # Объединенный диапазон всех OB свечей
                        ob_high = max(c['high'] for c in ob_candles)
                        ob_low = min(c['low'] for c in ob_candles)
                        return ob_high, ob_low
            
            elif self.bos_direction == 'SELL':
                # Медвежий импульс
                if candle['close'] < candle['open'] and body > 1.2 * atr:
                    # Поиск последних 2-3 бычьих свечей перед импульсом
                    ob_candles = []
                    for j in range(i - 1, max(0, i - 10), -1):
                        ob_candle = df.iloc[j]
                        if ob_candle['close'] > ob_candle['open']:
                            ob_candles.append(ob_candle)
                            if len(ob_candles) >= 3:  # До 3 OB
                                break
                    
                    if ob_candles:
                        # Объединенный диапазон всех OB свечей
                        ob_high = max(c['high'] for c in ob_candles)
                        ob_low = min(c['low'] for c in ob_candles)
                        return ob_high, ob_low
        
        return None, None

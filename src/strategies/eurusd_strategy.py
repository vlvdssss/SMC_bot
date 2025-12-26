"""
EURUSD Trading Strategy - SMC Retracement Baseline (FIXED ENTRY LOGIC)

Стратегия для торговли валютной пары EUR/USD.

СТАТУС: BASELINE (исправлена логика входа)
ВЕРСИЯ: v1.1 (Fixed Entry)
ДАТА ОБНОВЛЕНИЯ: 22 декабря 2025

КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ:
- Сигнал формируется на close текущей свечи M15
- Вход происходит на open СЛЕДУЮЩЕЙ свечи M15
- Устранён look-ahead bias для соответствия live торговле

Тип стратегии: SMC Retracement (pullback entries)
"""

import pandas as pd
import numpy as np


class StrategyEURUSD_SMC_Retracement:
    """
    SMC Retracement стратегия для EURUSD с правильной логикой входа.
    
    Концепция:
    - EURUSD = ликвидная валютная пара с четкой структурой
    - Глубокие откаты → entry на retracement в OB
    - Premium/Discount зоны работают отлично
    
    Логика:
    1. H1: BOS detection для определения направления тренда
    2. M15: Order Block identification
    3. M15: Premium/Discount зоны (проверка на close текущей свечи)
    4. Entry: На OPEN СЛЕДУЮЩЕЙ свечи (если сигнал валиден)
    5. Exit: 2:1 RR, SL = OB или ATR-based
    
    FIXED: Теперь сигнал на close → вход на next open (как в live торговле)
    """
    
    def __init__(self):
        """Инициализация стратегии для EURUSD"""
        self.instrument = "EURUSD"
        self.name = "EURUSD SMC Retracement"
        self.version = "v1.1 (Fixed Entry)"
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
        
        # Стабилизационные фильтры
        self.min_atr_threshold = 0.7  # ATR > 70% от среднего
        self.max_atr_threshold = 1.5  # ATR < 150% от среднего
        self.max_daily_trades = 1     # Максимум 1 сделка в день
        self.max_daily_loss = 1.0     # Стоп на день при -1%
        
        # Daily tracking
        self.trades_today = 0
        self.daily_pnl_percent = 0.0
        self.current_date = None
        
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
    
    def generate_signal(self, current_m15_idx: int, analysis_price: float,
                       entry_price: float, current_time: pd.Timestamp, current_h1_idx: int = None) -> dict:
        """
        Генерация торгового сигнала на M15.
        
        FIXED LOGIC: Анализ на close текущей свечи, вход на open следующей.
        
        Args:
            current_m15_idx: Индекс текущей свечи (которая закрылась)
            analysis_price: Close текущей свечи (для анализа)
            entry_price: Open следующей свечи (для входа)
            current_time: Время текущей свечи
            current_h1_idx: Текущий индекс в H1 данных
        
        Returns:
            dict: {'direction': str, 'sl': float, 'tp': float, 'valid': bool, 'entry': float}
        """
        if self.m15_data is None:
            return {'valid': False}
        if current_h1_idx is not None:
            self.build_context(current_h1_idx)
        return self.get_signal(self.m15_data, current_m15_idx, analysis_price, entry_price)
    
    def execute_trade(self, signal: dict, balance: float, risk_pct: float = 0.5) -> dict:
        """
        Расчет параметров сделки с правильным лот-сайзом.
        
        Args:
            signal: Сигнал от generate_signal()
            balance: Текущий баланс
            risk_pct: Риск в процентах (0.5% для EURUSD)
            
        Returns:
            dict: Параметры сделки для executor
        """
        if not signal['valid']:
            return None
        
        # Расчет лот-сайза (EURUSD contract size = 100000 units)
        entry_price = signal['entry']
        sl_price = signal['sl']
        contract_size = 100000
        
        risk_amount = balance * (risk_pct / 100.0)  # Сколько $ рискуем
        sl_distance = abs(entry_price - sl_price)    # Расстояние до SL
        
        if sl_distance == 0:
            lot_size = 0.01  # Минимум
        else:
            # risk_amount = lot_size * contract_size * sl_distance
            lot_size = risk_amount / (contract_size * sl_distance)
            lot_size = max(0.01, lot_size)  # Минимум 0.01
            lot_size = min(1.0, lot_size)   # Максимум 1.0
            lot_size = round(lot_size, 2)   # Округление
        
        return {
            'direction': signal['direction'],
            'entry': entry_price,
            'sl': signal['sl'],
            'tp': signal['tp'],
            'lot_size': lot_size
        }
    
    def get_trade(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame,
                  current_h1_idx: int, current_m15_idx: int,
                  analysis_price: float, entry_price: float,
                  current_time: pd.Timestamp, balance: float) -> dict:
        """
        Главная функция - получение торгового сигнала.
        
        FIXED: Разделены цены для анализа и входа.
        
        Args:
            h1_data: H1 DataFrame
            m15_data: M15 DataFrame
            current_h1_idx: Индекс в H1 данных
            current_m15_idx: Индекс в M15 данных
            analysis_price: Close текущей свечи (для анализа)
            entry_price: Open следующей свечи (для входа)
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
        signal = self.get_signal(m15_data, current_m15_idx, analysis_price, entry_price)
        
        # Шаг 3: Расчет сделки
        if signal['valid']:
            trade = self.execute_trade(signal, balance, risk_pct=0.1)
            if trade:
                self.trades_today += 1
            return trade
        
        return None
    
    # =========================================================================
    # EURUSD SMC RETRACEMENT LOGIC (FIXED ENTRY - v1.1)
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
            # H1 диапазон ТОЛЬКО на прошлых данных!
            self.h1_high = h1_data.iloc[current_idx - 10:current_idx]['high'].max()
            self.h1_low = h1_data.iloc[current_idx - 10:current_idx]['low'].min()
        elif self.last_swing_low_h1 and current_close < self.last_swing_low_h1:
            self.bos_direction = 'SELL'
            self.h1_bos_valid = True
            # H1 диапазон ТОЛЬКО на прошлых данных!
            self.h1_high = h1_data.iloc[current_idx - 10:current_idx]['high'].max()
            self.h1_low = h1_data.iloc[current_idx - 10:current_idx]['low'].min()
        else:
            self.bos_direction = None
            self.h1_bos_valid = False
    
    def get_signal(self, m15_data: pd.DataFrame, current_idx: int,
                   analysis_price: float, entry_price: float) -> dict:
        """
        Получение торгового сигнала на M15 (RETRACEMENT LOGIC).
        
        FIXED LOGIC: Анализ на analysis_price, вход на entry_price.
        
        Args:
            current_idx: Индекс текущей свечи (которая закрылась)
            analysis_price: Close текущей свечи (для проверки условий)
            entry_price: Open следующей свечи (для входа)
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
        
        # Расчет ATR(M15)
        atr = self._calculate_atr_cached(m15_data, current_idx, period=14)
        if atr == 0:
            return signal
        
        # СТАБИЛИЗАЦИОННЫЕ ФИЛЬТРЫ
        # Фильтр 1: Волатильность в норме
        atr_avg = self._calculate_atr_sma(m15_data, current_idx, period=14, sma_period=100)
        if atr_avg > 0:
            if atr < atr_avg * self.min_atr_threshold:
                return signal  # Low volatility
            if atr > atr_avg * self.max_atr_threshold:
                return signal  # Too high volatility (news?)
        
        # Фильтр 2: Лимит сделок в день
        current_date = pd.to_datetime(m15_data.iloc[current_idx]['time']).date()
        if self.current_date != current_date:
            self.trades_today = 0
            self.daily_pnl_percent = 0.0
            self.current_date = current_date
        
        if self.trades_today >= self.max_daily_trades:
            return signal  # Daily trade limit
        
        # Фильтр 3: Стоп на день при большом убытке
        if self.daily_pnl_percent <= -self.max_daily_loss:
            return signal  # Daily loss limit
        
        # Поиск Order Block (ТОЛЬКО на данных ДО текущего момента)
        # current_idx - это свеча, которая только что закрылась
        # Order Block должен быть найден на предыдущих свечах
        lookback = min(20, current_idx)
        recent_bars = m15_data.iloc[current_idx - lookback:current_idx]  # НЕ включаем current_idx!
        
        if self.bos_direction == 'BUY':
            # Для BUY: ищем bullish OB (свечу перед движением вверх)
            ob_found = False
            ob_low = None
            ob_high = None
            
            for i in range(len(recent_bars) - 2, 0, -1):
                bar = recent_bars.iloc[i]
                next_bar = recent_bars.iloc[i+1]
                
                # Down свеча + следующая up свеча
                if bar['close'] < bar['open'] and next_bar['close'] > next_bar['open']:
                    ob_low = bar['low']
                    ob_high = bar['high']
                    ob_found = True
                    break
            
            if not ob_found:
                return signal
            
            # Проверяем что analysis_price (close) был в OB
            if not (ob_low <= analysis_price <= ob_high):
                return signal
            
            # Проверяем Premium/Discount (должны быть в Discount для BUY)
            if not self.h1_low or not self.h1_high:
                return signal
            
            h1_range = self.h1_high - self.h1_low
            discount_level = self.h1_low + (h1_range * 0.5)
            
            if analysis_price > discount_level:
                # В Premium зоне - не входим
                return signal
            
            # Entry на entry_price (следующий open)
            signal['direction'] = 'BUY'
            signal['sl'] = entry_price - (atr * 1.5)  # SL от entry
            sl_distance = entry_price - signal['sl']
            signal['tp'] = entry_price + (sl_distance * 2.0)  # 2:1 RR
            signal['valid'] = True
            
        elif self.bos_direction == 'SELL':
            # Для SELL: ищем bearish OB
            ob_found = False
            ob_low = None
            ob_high = None
            
            for i in range(len(recent_bars) - 2, 0, -1):
                bar = recent_bars.iloc[i]
                next_bar = recent_bars.iloc[i+1]
                
                # Up свеча + следующая down свеча
                if bar['close'] > bar['open'] and next_bar['close'] < next_bar['open']:
                    ob_low = bar['low']
                    ob_high = bar['high']
                    ob_found = True
                    break
            
            if not ob_found:
                return signal
            
            # Проверяем что analysis_price (close) был в OB
            if not (ob_low <= analysis_price <= ob_high):
                return signal
            
            # Проверяем Premium/Discount (должны быть в Premium для SELL)
            if not self.h1_low or not self.h1_high:
                return signal
            
            h1_range = self.h1_high - self.h1_low
            premium_level = self.h1_low + (h1_range * 0.5)
            
            if analysis_price < premium_level:
                # В Discount зоне - не входим
                return signal
            
            # Entry на entry_price (следующий open)
            signal['direction'] = 'SELL'
            signal['sl'] = entry_price + (atr * 1.5)  # SL от entry
            sl_distance = signal['sl'] - entry_price
            signal['tp'] = entry_price - (sl_distance * 2.0)  # 2:1 RR
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
        
        recent = df.iloc[current_idx - period + 1:current_idx + 1]
        high_low = recent['high'] - recent['low']
        atr = high_low.mean()
        
        self._atr_cache[cache_key] = atr
        return atr if atr > 0 else 0.0
    
    def _calculate_atr_sma(self, df: pd.DataFrame, current_idx: int, 
                          period: int = 14, sma_period: int = 100) -> float:
        """Расчет SMA ATR для фильтра волатильности."""
        if current_idx < sma_period:
            return 0.0
        
        atr_values = []
        for i in range(current_idx - sma_period + 1, current_idx + 1):
            atr = self._calculate_atr_cached(df, i, period)
            atr_values.append(atr)
        
        return np.mean(atr_values) if atr_values else 0.0
    
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

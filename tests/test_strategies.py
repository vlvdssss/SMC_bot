"""
Тесты для торговых стратегий - базовая функциональность.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestStrategyBasics:
    """Базовые тесты для торговых стратегий."""
    
    @pytest.fixture
    def sample_h1_data(self):
        """Создает тестовые H1 данные."""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='H')
        
        data = pd.DataFrame({
            'time': dates,
            'open': np.random.uniform(2000, 2100, 200),
            'high': np.random.uniform(2050, 2150, 200),
            'low': np.random.uniform(1950, 2050, 200),
            'close': np.random.uniform(2000, 2100, 200),
            'volume': np.random.randint(100, 1000, 200)
        })
        
        # Корректируем high/low
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    @pytest.fixture
    def sample_m15_data(self):
        """Создает тестовые M15 данные."""
        dates = pd.date_range(start='2024-01-01', periods=800, freq='15min')
        
        data = pd.DataFrame({
            'time': dates,
            'open': np.random.uniform(2000, 2100, 800),
            'high': np.random.uniform(2050, 2150, 800),
            'low': np.random.uniform(1950, 2050, 800),
            'close': np.random.uniform(2000, 2100, 800),
            'volume': np.random.randint(50, 500, 800)
        })
        
        # Корректируем high/low
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    def test_data_structure_h1(self, sample_h1_data):
        """Тест структуры H1 данных."""
        assert len(sample_h1_data) == 200
        assert all(col in sample_h1_data.columns for col in ['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Проверка что high >= open, close и low <= open, close
        assert all(sample_h1_data['high'] >= sample_h1_data['open'])
        assert all(sample_h1_data['high'] >= sample_h1_data['close'])
        assert all(sample_h1_data['low'] <= sample_h1_data['open'])
        assert all(sample_h1_data['low'] <= sample_h1_data['close'])
    
    def test_data_structure_m15(self, sample_m15_data):
        """Тест структуры M15 данных."""
        assert len(sample_m15_data) == 800
        assert all(col in sample_m15_data.columns for col in ['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Проверка валидности свечей
        assert all(sample_m15_data['high'] >= sample_m15_data['low'])
    
    def test_signal_structure(self):
        """Тест структуры торгового сигнала."""
        signal = {
            'valid': True,
            'direction': 'BUY',
            'entry': 2050.0,
            'sl': 2030.0,
            'tp': 2080.0,
            'lot_size': 0.1,
            'risk_reward': 1.5,
            'confidence': 'HIGH'
        }
        
        # Проверка обязательных полей
        assert 'valid' in signal
        assert 'direction' in signal
        assert signal['direction'] in ['BUY', 'SELL']
        
        if signal['valid']:
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            assert signal['sl'] != signal['entry']
            assert signal['tp'] != signal['entry']
    
    def test_buy_signal_levels(self):
        """Тест корректности уровней для BUY сигнала."""
        signal = {
            'valid': True,
            'direction': 'BUY',
            'entry': 2050.0,
            'sl': 2030.0,
            'tp': 2080.0
        }
        
        # Для BUY: SL < entry < TP
        assert signal['sl'] < signal['entry']
        assert signal['entry'] < signal['tp']
    
    def test_sell_signal_levels(self):
        """Тест корректности уровней для SELL сигнала."""
        signal = {
            'valid': True,
            'direction': 'SELL',
            'entry': 2050.0,
            'sl': 2070.0,
            'tp': 2020.0
        }
        
        # Для SELL: TP < entry < SL
        assert signal['tp'] < signal['entry']
        assert signal['entry'] < signal['sl']
    
    def test_risk_reward_calculation(self):
        """Тест расчета risk/reward."""
        # BUY сигнал
        entry = 2050.0
        sl = 2030.0
        tp = 2080.0
        
        risk = abs(entry - sl)  # 20
        reward = abs(tp - entry)  # 30
        rr = reward / risk  # 1.5
        
        assert abs(rr - 1.5) < 0.01
        
        # SELL сигнал
        entry = 2050.0
        sl = 2070.0
        tp = 2010.0
        
        risk = abs(sl - entry)  # 20
        reward = abs(entry - tp)  # 40
        rr = reward / risk  # 2.0
        
        assert abs(rr - 2.0) < 0.01
    
    def test_invalid_signal_structure(self):
        """Тест невалидных сигналов."""
        # Сигнал без SL
        signal1 = {
            'valid': True,
            'direction': 'BUY',
            'entry': 2050.0,
            'tp': 2080.0
        }
        assert 'sl' not in signal1
        
        # Сигнал с неверными уровнями для BUY
        signal2 = {
            'valid': True,
            'direction': 'BUY',
            'entry': 2050.0,
            'sl': 2070.0,  # SL > entry (неверно для BUY)
            'tp': 2080.0
        }
        assert not (signal2['sl'] < signal2['entry'] < signal2['tp'])
    
    def test_strategy_timeframe_alignment(self, sample_h1_data, sample_m15_data):
        """Тест выравнивания таймфреймов."""
        # H1 и M15 должны быть согласованы (4 свечи M15 = 1 свеча H1)
        h1_time = sample_h1_data.iloc[10]['time']
        
        # Находим соответствующие M15 свечи
        m15_subset = sample_m15_data[
            (sample_m15_data['time'] >= h1_time) &
            (sample_m15_data['time'] < h1_time + timedelta(hours=1))
        ]
        
        # Должно быть 4 M15 свечи на 1 H1
        assert len(m15_subset) == 4
    
    def test_minimum_data_requirements(self, sample_h1_data, sample_m15_data):
        """Тест минимальных требований к данным для стратегии."""
        # Стратегии обычно требуют минимум данных для анализа
        min_h1_bars = 50
        min_m15_bars = 200
        
        assert len(sample_h1_data) >= min_h1_bars
        assert len(sample_m15_data) >= min_m15_bars
    
    def test_data_continuity(self, sample_h1_data):
        """Тест непрерывности данных (нет пропусков)."""
        time_diffs = sample_h1_data['time'].diff().dropna()
        
        # Все интервалы должны быть 1 час
        expected_diff = timedelta(hours=1)
        assert all(time_diffs == expected_diff)
    
    def test_price_validity(self, sample_h1_data):
        """Тест валидности ценовых данных."""
        # Цены должны быть положительными
        assert all(sample_h1_data['open'] > 0)
        assert all(sample_h1_data['high'] > 0)
        assert all(sample_h1_data['low'] > 0)
        assert all(sample_h1_data['close'] > 0)
        
        # High >= Low всегда
        assert all(sample_h1_data['high'] >= sample_h1_data['low'])


class TestStrategyIndicators:
    """Тесты для индикаторов стратегии."""
    
    def test_ema_calculation(self):
        """Тест расчета EMA."""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108])
        
        # Расчет EMA (период 5)
        ema = prices.ewm(span=5, adjust=False).mean()
        
        assert len(ema) == len(prices)
        assert not ema.isna().any()
        assert all(ema > 0)
    
    def test_support_resistance_levels(self):
        """Тест определения уровней поддержки/сопротивления."""
        highs = [2100, 2105, 2098, 2110, 2095, 2108, 2112, 2103]
        lows = [2080, 2085, 2078, 2090, 2075, 2088, 2092, 2083]
        
        # Находим максимумы и минимумы
        resistance = max(highs)
        support = min(lows)
        
        assert resistance > support
        assert resistance == 2112
        assert support == 2075
    
    def test_trend_detection(self):
        """Тест определения тренда."""
        # Восходящий тренд
        uptrend_closes = [2000, 2010, 2020, 2030, 2040, 2050]
        ema_uptrend = pd.Series(uptrend_closes).ewm(span=3).mean()
        assert ema_uptrend.iloc[-1] > ema_uptrend.iloc[0]
        
        # Нисходящий тренд
        downtrend_closes = [2050, 2040, 2030, 2020, 2010, 2000]
        ema_downtrend = pd.Series(downtrend_closes).ewm(span=3).mean()
        assert ema_downtrend.iloc[-1] < ema_downtrend.iloc[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

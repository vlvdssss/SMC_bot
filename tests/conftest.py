"""
Pytest configuration and fixtures for BAZA Trading Bot tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_ohlc_data():
    """Генерирует тестовые OHLC данные."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    
    data = pd.DataFrame({
        'time': dates,
        'open': np.random.uniform(2000, 2100, 100),
        'high': np.random.uniform(2050, 2150, 100),
        'low': np.random.uniform(1950, 2050, 100),
        'close': np.random.uniform(2000, 2100, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    
    # Убедимся что high >= open, close и low <= open, close
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    return data


@pytest.fixture
def sample_signal():
    """Генерирует тестовый торговый сигнал."""
    return {
        'valid': True,
        'direction': 'BUY',
        'entry': 2050.0,
        'sl': 2030.0,
        'tp': 2080.0,
        'lot_size': 0.1,
        'risk_reward': 1.5,
        'confidence': 'HIGH'
    }


@pytest.fixture
def sample_account_info():
    """Генерирует тестовую информацию о счете."""
    return {
        'balance': 10000.0,
        'equity': 10000.0,
        'margin': 0.0,
        'free_margin': 10000.0,
        'margin_level': 0.0,
        'currency': 'USD'
    }


@pytest.fixture
def mock_mt5_price():
    """Мок для MT5 цены."""
    class MockPrice:
        def __init__(self):
            self.bid = 2050.0
            self.ask = 2051.0
            self.time = datetime.now()
    
    return MockPrice()

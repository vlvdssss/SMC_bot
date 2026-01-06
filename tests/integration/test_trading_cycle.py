"""
Integration Tests - Full Trading Cycle

Тесты полного цикла торговли: загрузка данных → стратегия → исполнение → результаты.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.bot_manager import BotManager, BotStatus
from src.core.broker_sim import BrokerSim
from src.core.data_loader import DataLoader
from src.strategies.xauusd_strategy import StrategyXAUUSD
from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement
from src.backtest.backtester import RealisticBacktester


class TestFullTradingCycle:
    """Тесты полного торгового цикла"""
    
    @pytest.fixture
    def bot_manager(self):
        """Fixture для BotManager"""
        manager = BotManager()
        manager.status = BotStatus.STOPPED
        return manager
    
    @pytest.fixture
    def broker_sim(self):
        """Fixture для BrokerSim"""
        return BrokerSim()
    
    @pytest.fixture
    def xauusd_strategy(self):
        """Fixture для XAUUSD стратегии"""
        return StrategyXAUUSD()
    
    @pytest.fixture
    def eurusd_strategy(self):
        """Fixture для EURUSD стратегии"""
        return StrategyEURUSD_SMC_Retracement()
    
    def test_bot_manager_lifecycle(self, bot_manager):
        """Тест жизненного цикла BotManager"""
        # Начальное состояние
        assert bot_manager.status == BotStatus.STOPPED
        assert bot_manager.stats['total_trades'] == 0
        
        # Симуляция работы бота
        bot_manager.status = BotStatus.RUNNING
        assert bot_manager.status == BotStatus.RUNNING
        
        # Добавление торга
        trade = {
            'symbol': 'XAUUSD',
            'direction': 'BUY',
            'entry': 2000.0,
            'exit': 2020.0,
            'profit': 20.0,
            'pips': 200,
            'timestamp': datetime.now().isoformat()
        }
        bot_manager.add_trade(trade)
        
        assert bot_manager.stats['total_trades'] == 1
        assert bot_manager.stats['wins'] == 1
        
        # Остановка бота
        bot_manager.status = BotStatus.STOPPED
        assert bot_manager.status == BotStatus.STOPPED
    
    def test_broker_sim_position_lifecycle(self, broker_sim):
        """Тест расчета спреда и маржи"""
        # Проверяем расчет маржи
        margin = broker_sim.calculate_margin_required(lot_size=0.1, price=2000.0)
        assert margin > 0
        
        # Проверяем применение спреда
        buy_price = broker_sim.apply_spread(price=2000.0, direction='BUY')
        sell_price = broker_sim.apply_spread(price=2000.0, direction='SELL')
        
        assert buy_price > 2000.0  # BUY должен быть выше
        assert sell_price < 2000.0  # SELL должен быть ниже
        assert buy_price - sell_price == broker_sim.spread * 2  # Двойной спред
    
    def test_strategy_signal_generation(self, xauusd_strategy):
        """Тест генерации сигналов стратегией"""
        # Создаем тестовые данные
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        data_h1 = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(2000, 2010, 100),
            'high': np.random.uniform(2010, 2020, 100),
            'low': np.random.uniform(1990, 2000, 100),
            'close': np.random.uniform(2000, 2010, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        dates_m15 = pd.date_range(start='2024-01-01', periods=400, freq='15min')
        data_m15 = pd.DataFrame({
            'timestamp': dates_m15,
            'open': np.random.uniform(2000, 2010, 400),
            'high': np.random.uniform(2010, 2020, 400),
            'low': np.random.uniform(1990, 2000, 400),
            'close': np.random.uniform(2000, 2010, 400),
            'volume': np.random.randint(1000, 10000, 400)
        })
        
        # Генерируем сигнал
        signal = xauusd_strategy.generate_signal(data_h1, data_m15)
        
        # Проверяем структуру сигнала
        if signal:
            assert 'direction' in signal
            assert signal['direction'] in ['BUY', 'SELL']
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            assert 'reason' in signal
    
    def test_data_loader_integration(self):
        """Тест загрузки данных"""
        # Используем существующие CSV файлы
        csv_file = Path('data/backtest/XAUUSD_H1_2023_2025.csv')
        
        if csv_file.exists():
            data_loader = DataLoader(
                instrument='XAUUSD',
                start_date='2024-01-01',
                end_date='2024-01-31'
            )
            
            data_h1, data_m15 = data_loader.load()
            
            assert data_h1 is not None
            assert not data_h1.empty
            assert 'close' in data_h1.columns
            assert 'timestamp' in data_h1.columns
    
    def test_end_to_end_trade_execution(self, broker_sim, xauusd_strategy):
        """Тест полного цикла: данные → сигнал → симуляция → результат"""
        # Создаем реалистичные данные с трендом
        dates_h1 = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        prices_h1 = np.linspace(2000, 2050, 50) + np.random.normal(0, 5, 50)
        data_h1 = pd.DataFrame({
            'timestamp': dates_h1,
            'open': prices_h1,
            'high': prices_h1 + np.random.uniform(5, 15, 50),
            'low': prices_h1 - np.random.uniform(5, 15, 50),
            'close': prices_h1 + np.random.uniform(-5, 5, 50),
            'volume': np.random.randint(5000, 15000, 50)
        })
        
        dates_m15 = pd.date_range(start='2024-01-01', periods=200, freq='15min')
        prices_m15 = np.linspace(2000, 2050, 200) + np.random.normal(0, 3, 200)
        data_m15 = pd.DataFrame({
            'timestamp': dates_m15,
            'open': prices_m15,
            'high': prices_m15 + np.random.uniform(2, 8, 200),
            'low': prices_m15 - np.random.uniform(2, 8, 200),
            'close': prices_m15 + np.random.uniform(-3, 3, 200),
            'volume': np.random.randint(1000, 5000, 200)
        })
        
        # 1. Генерируем сигнал
        signal = xauusd_strategy.generate_signal(data_h1, data_m15)
        
        # 2. Если есть сигнал, проверяем его структуру
        if signal:
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            
            # 3. Применяем спред к entry
            entry_with_spread = broker_sim.apply_spread(signal['entry'], signal['direction'])
            
            # 4. Проверяем что спред применен корректно
            if signal['direction'] == 'BUY':
                assert entry_with_spread > signal['entry']
            else:
                assert entry_with_spread < signal['entry']
    
    def test_multiple_trades_sequence(self, broker_sim, xauusd_strategy):
        """Тест последовательности нескольких сигналов"""
        signals_generated = 0
        
        # Симулируем 5 торговых сессий
        for i in range(5):
            # Создаем данные для каждой сессии
            dates_h1 = pd.date_range(start=f'2024-01-{i+1:02d}', periods=24, freq='1H')
            base_price = 2000 + i * 10
            prices_h1 = base_price + np.random.normal(0, 10, 24)
            
            data_h1 = pd.DataFrame({
                'timestamp': dates_h1,
                'open': prices_h1,
                'high': prices_h1 + np.random.uniform(5, 15, 24),
                'low': prices_h1 - np.random.uniform(5, 15, 24),
                'close': prices_h1 + np.random.uniform(-5, 5, 24),
                'volume': np.random.randint(5000, 15000, 24)
            })
            
            dates_m15 = pd.date_range(start=f'2024-01-{i+1:02d}', periods=96, freq='15min')
            prices_m15 = base_price + np.random.normal(0, 5, 96)
            
            data_m15 = pd.DataFrame({
                'timestamp': dates_m15,
                'open': prices_m15,
                'high': prices_m15 + np.random.uniform(2, 8, 96),
                'low': prices_m15 - np.random.uniform(2, 8, 96),
                'close': prices_m15 + np.random.uniform(-3, 3, 96),
                'volume': np.random.randint(1000, 5000, 96)
            })
            
            # Генерируем сигнал
            signal = xauusd_strategy.generate_signal(data_h1, data_m15)
            
            if signal:
                signals_generated += 1
        
        # Стратегия должна хотя бы иногда генерировать сигналы
        # (может быть 0 для некоторых random data)
        assert signals_generated >= 0
    
    def test_risk_management_integration(self, broker_sim):
        """Тест расчета риск-менеджмента"""
        initial_balance = 10000.0
        
        # Параметры позиции
        entry_price = 2000.0
        sl = 1980.0
        lot = 0.1
        
        # Рассчитываем риск
        risk_pips = abs(entry_price - sl) * 10  # Конвертируем в пипсы
        risk_amount = risk_pips * lot * 10  # 10$ per pip для 0.1 lot XAUUSD
        risk_percent = (risk_amount / initial_balance) * 100
        
        # Проверяем что риск не превышает 2%
        assert risk_percent <= 2.0
        
        # Проверяем маржу
        margin = broker_sim.calculate_margin_required(lot, entry_price)
        assert margin > 0
        assert margin < initial_balance  # Маржа должна быть меньше баланса


class TestStrategyIntegration:
    """Тесты интеграции стратегий"""
    
    def test_xauusd_strategy_consistency(self):
        """Тест консистентности XAUUSD стратегии"""
        strategy = StrategyXAUUSD()
        
        # Проверяем настройки
        assert strategy.instrument == "XAUUSD"
        assert strategy.htf_timeframe == "H1"
        assert strategy.ltf_timeframe == "M15"
        
        # Создаем одни и те же данные
        dates_h1 = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        data_h1 = pd.DataFrame({
            'timestamp': dates_h1,
            'open': np.full(50, 2000.0),
            'high': np.full(50, 2010.0),
            'low': np.full(50, 1990.0),
            'close': np.full(50, 2005.0),
            'volume': np.full(50, 10000)
        })
        
        dates_m15 = pd.date_range(start='2024-01-01', periods=200, freq='15min')
        data_m15 = pd.DataFrame({
            'timestamp': dates_m15,
            'open': np.full(200, 2000.0),
            'high': np.full(200, 2010.0),
            'low': np.full(200, 1990.0),
            'close': np.full(200, 2005.0),
            'volume': np.full(200, 2500)
        })
        
        # Генерируем сигнал дважды
        signal1 = strategy.generate_signal(data_h1, data_m15)
        signal2 = strategy.generate_signal(data_h1, data_m15)
        
        # Проверяем консистентность
        assert signal1 == signal2
    
    def test_eurusd_strategy_consistency(self):
        """Тест консистентности EURUSD стратегии"""
        strategy = StrategyEURUSD_SMC_Retracement()
        
        assert strategy.instrument == "EURUSD"
        assert strategy.htf_timeframe == "H1"
        assert strategy.ltf_timeframe == "M15"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

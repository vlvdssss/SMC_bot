"""
Integration Tests - Backtesting System

Тесты системы бэктестинга: загрузка данных → симуляция → метрики → результаты.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtest.backtester import RealisticBacktester
from src.backtest.portfolio_backtester import PortfolioBacktester
from src.backtest.metrics import MetricsCalculator
from src.core.broker_sim import BrokerSim
from src.strategies.xauusd_strategy import StrategyXAUUSD
from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement


class TestBacktestingSystem:
    """Тесты системы бэктестинга"""
    
    @pytest.fixture
    def sample_trades_df(self):
        """Fixture с примерными торгами"""
        trades = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(20):
            profit = np.random.choice([50, -30, 40, -20, 60, -25])
            trades.append({
                'symbol': 'XAUUSD',
                'direction': 'BUY' if i % 2 == 0 else 'SELL',
                'open_time': base_date + timedelta(days=i),
                'close_time': base_date + timedelta(days=i, hours=4),
                'entry': 2000 + i * 5,
                'exit': 2000 + i * 5 + profit / 10,
                'sl': 2000 + i * 5 - 20,
                'tp': 2000 + i * 5 + 40,
                'lot': 0.1,
                'profit': profit,
                'pips': profit * 10,
                'duration_hours': 4,
                'reason': 'Test trade'
            })
        
        return pd.DataFrame(trades)
    
    @pytest.fixture
    def sample_equity_df(self):
        """Fixture с примерной эквити"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Создаем реалистичную эквити с трендом и волатильностью
        base_equity = 10000
        trend = np.linspace(0, 2000, 100)  # Общий рост
        noise = np.random.normal(0, 100, 100).cumsum()  # Волатильность
        
        equity = base_equity + trend + noise
        
        return pd.DataFrame({
            'timestamp': dates,
            'equity': equity,
            'balance': equity,
            'margin': np.full(100, 0),
            'free_margin': equity
        })
    
    def test_backtest_metrics_calculation(self, sample_trades_df):
        """Тест расчета метрик бэктеста"""
        metrics = MetricsCalculator()
        results = metrics.calculate_portfolio_metrics(sample_trades_df)
        
        # Проверяем основные метрики
        assert 'total_trades' in results
        assert 'win_rate' in results
        assert 'profit_factor' in results
        assert 'total_profit' in results
        
        # Проверяем значения
        assert results['total_trades'] == len(sample_trades_df)
        assert 0 <= results['win_rate'] <= 100
        assert results['profit_factor'] >= 0
    
    def test_equity_curve_analysis(self, sample_equity_df):
        """Тест анализа эквити"""
        # Рассчитываем максимальную просадку вручную
        equity = sample_equity_df['equity']
        peak = equity.expanding(min_periods=1).max()
        drawdown = (equity - peak) / peak * 100
        max_dd = abs(drawdown.min())
        
        assert max_dd >= 0
        assert max_dd <= 100  # В процентах
    
    def test_realistic_backtester_initialization(self):
        """Тест инициализации RealisticBacktester"""
        strategies = {
            'XAUUSD': StrategyXAUUSD(),
            'EURUSD': StrategyEURUSD_SMC_Retracement()
        }
        broker = BrokerSim()
        
        # Note: DataLoader нужен, но может быть None для теста
        backtester = RealisticBacktester(
            strategies=strategies,
            broker=broker,
            data_loader=None
        )
        
        assert backtester is not None
        assert backtester.strategies == strategies
        assert backtester.broker == broker
    
    def test_backtest_with_sample_data(self):
        """Тест бэктеста с примерными данными"""
        # Создаем тестовые данные
        dates = pd.date_range(start='2024-01-01', periods=500, freq='1H')
        
        # Создаем тренд + шум
        trend = np.linspace(2000, 2100, 500)
        noise = np.random.normal(0, 5, 500)
        prices = trend + noise
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.uniform(2, 8, 500),
            'low': prices - np.random.uniform(2, 8, 500),
            'close': prices + np.random.uniform(-3, 3, 500),
            'volume': np.random.randint(5000, 15000, 500)
        })
        
        # Инициализируем компоненты
        strategy = StrategyXAUUSD()
        initial_balance = 10000.0
        open_positions = []
        balance = initial_balance
        
        # Симулируем простой бэктест
        trades = []
        equity_curve = [balance]
        
        # Проходим по данным с шагом 4 часа
        for i in range(50, len(data), 4):
            data_slice_h1 = data.iloc[max(0, i-50):i]
            data_slice_m15 = data.iloc[max(0, i-200):i]
            
            # Генерируем сигнал
            signal = strategy.generate_signal(data_slice_h1, data_slice_m15)
            
            if signal and len(open_positions) == 0:
                # Открываем позицию (симуляция)
                position = {
                    'id': len(trades),
                    'symbol': 'XAUUSD',
                    'direction': signal['direction'],
                    'lot': 0.1,
                    'entry': signal['entry'],
                    'sl': signal['sl'],
                    'tp': signal['tp']
                }
                open_positions.append(position)
                
                if position:
                    # Симулируем движение цены (берем следующие 10 свечей)
                    for j in range(i + 1, min(i + 10, len(data))):
                        current_price = data.iloc[j]['close']
                        
                        # Проверяем SL/TP
                        if signal['direction'] == 'BUY':
                            if current_price >= signal['tp']:
                                profit = (signal['tp'] - signal['entry']) * position['lot'] * 100
                                balance += profit
                                trades.append({'profit': profit, 'exit_price': signal['tp']})
                                open_positions.remove(position)
                                break
                            elif current_price <= signal['sl']:
                                profit = (signal['sl'] - signal['entry']) * position['lot'] * 100
                                balance += profit
                                trades.append({'profit': profit, 'exit_price': signal['sl']})
                                open_positions.remove(position)
                                break
                        else:  # SELL
                            if current_price <= signal['tp']:
                                profit = (signal['entry'] - signal['tp']) * position['lot'] * 100
                                balance += profit
                                trades.append({'profit': profit, 'exit_price': signal['tp']})
                                open_positions.remove(position)
                                break
                            elif current_price >= signal['sl']:
                                profit = (signal['entry'] - signal['sl']) * position['lot'] * 100
                                balance += profit
                                trades.append({'profit': profit, 'exit_price': signal['sl']})
                                open_positions.remove(position)
                                break
            
            equity_curve.append(balance)
        
        # Проверяем результаты
        assert len(trades) > 0, "Должны быть хотя бы некоторые сделки"
        assert len(equity_curve) > 1
        
        # Рассчитываем метрики
        if trades:
            trades_df = pd.DataFrame(trades)
            metrics = MetricsCalculator()
            results = metrics.calculate_portfolio_metrics(trades_df)
            
            assert 'total_trades' in results
            assert results['total_trades'] == len(trades)
    
    def test_portfolio_backtester_initialization(self):
        """Тест инициализации PortfolioBacktester"""
        strategies = {
            'XAUUSD': StrategyXAUUSD(),
            'EURUSD': StrategyEURUSD_SMC_Retracement()
        }
        
        backtester = PortfolioBacktester(
            strategies=strategies,
            initial_balance=10000.0
        )
        
        assert backtester is not None
        assert len(backtester.strategies) == 2
    
    def test_backtest_risk_management(self):
        """Тест риск-менеджмента в бэктесте"""
        initial_balance = 10000.0
        
        # Создаем позицию с заданным риском
        position = {
            'id': 1,
            'symbol': 'XAUUSD',
            'direction': 'BUY',
            'lot': 0.1,
            'entry': 2000.0,
            'sl': 1980.0,  # 20$ риск
            'tp': 2040.0   # 40$ цель
        }
        
        # Проверяем RR
        risk = abs(position['entry'] - position['sl'])
        reward = abs(position['tp'] - position['entry'])
        rr_ratio = reward / risk if risk > 0 else 0
        
        assert rr_ratio >= 2.0, "RR должно быть минимум 2:1"
        
        # Симулируем закрытие на SL
        profit = (position['sl'] - position['entry']) * position['lot'] * 100
        
        # Проверяем что потеря соответствует риску
        assert profit < 0
        assert abs(profit) <= initial_balance * 0.02  # Максимум 2% риск
    
    def test_backtest_statistical_significance(self, sample_trades_df):
        """Тест статистической значимости результатов"""
        metrics = MetricsCalculator()
        results = metrics.calculate_portfolio_metrics(sample_trades_df)
        
        # Проверяем минимальное количество сделок
        assert results['total_trades'] >= 10, "Нужно минимум 10 сделок для валидности"
        
        # Проверяем разумность метрик
        assert -100 <= results['total_profit'] <= 100000
        assert 0 <= results['win_rate'] <= 100
        assert 0 <= results['profit_factor'] <= 10
    
    def test_backtest_consistency(self):
        """Тест консистентности результатов бэктеста"""
        # Создаем детерминированные данные
        np.random.seed(42)
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        prices = np.linspace(2000, 2050, 100)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + 5,
            'low': prices - 5,
            'close': prices + 2,
            'volume': np.full(100, 10000)
        })
        
        strategy = StrategyXAUUSD()
        
        # Генерируем сигнал дважды
        signal1 = strategy.generate_signal(data, data)
        signal2 = strategy.generate_signal(data, data)
        
        # Результаты должны быть одинаковыми
        assert signal1 == signal2
    
    def test_backtest_edge_cases(self):
        """Тест граничных случаев"""
        initial_balance = 100.0  # Маленький баланс
        
        # Попытка открыть слишком большую позицию
        lot = 10.0  # Слишком большой лот
        entry_price = 2000.0
        
        # Проверяем требуемую маржу
        leverage = 100
        required_margin = (lot * 100 * entry_price) / leverage  # 100 oz для XAUUSD
        
        # Должна быть недостаточно средств
        assert required_margin > initial_balance


class TestBacktestMetrics:
    """Тесты метрик бэктестинга"""
    
    def test_win_rate_calculation(self):
        """Тест расчета винрейта"""
        trades = pd.DataFrame({
            'profit': [50, -30, 40, -20, 60, -25, 70, 30, -10, 45]
        })
        
        winning_trades = len(trades[trades['profit'] > 0])
        total_trades = len(trades)
        win_rate = (winning_trades / total_trades) * 100
        
        assert win_rate == 60.0  # 6 из 10
    
    def test_profit_factor_calculation(self):
        """Тест расчета profit factor"""
        trades = pd.DataFrame({
            'profit': [100, -50, 80, -30, 60, -40]
        })
        
        gross_profit = trades[trades['profit'] > 0]['profit'].sum()  # 240
        gross_loss = abs(trades[trades['profit'] < 0]['profit'].sum())  # 120
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        assert profit_factor == 2.0
    
    def test_max_drawdown_calculation(self):
        """Тест расчета максимальной просадки"""
        equity = pd.Series([10000, 10500, 10300, 9800, 10100, 11000, 10500, 10800])
        
        # Находим максимальную просадку
        peak = equity.expanding(min_periods=1).max()
        drawdown = (equity - peak) / peak * 100
        max_dd = abs(drawdown.min())
        
        # Максимальная просадка от 10500 до 9800
        expected_dd = abs((9800 - 10500) / 10500 * 100)
        
        assert abs(max_dd - expected_dd) < 0.1
    
    def test_sharpe_ratio_calculation(self):
        """Тест расчета коэффициента Шарпа"""
        # Дневные доходности
        returns = pd.Series([0.01, -0.005, 0.015, -0.01, 0.02, 0.005, -0.002, 0.012])
        
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Sharpe = (средняя доходность - безрисковая ставка) / стандартное отклонение
        # Для упрощения используем безрисковую ставку = 0
        sharpe = mean_return / std_return if std_return > 0 else 0
        
        assert sharpe > 0  # Положительная доходность


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

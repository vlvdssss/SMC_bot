"""
Strategy Parameter Optimizer для BAZA Trading Bot

Автоматический поиск оптимальных параметров стратегий через Grid Search.
"""

import pandas as pd
import numpy as np
from itertools import product
from typing import Dict, List, Tuple, Any
from datetime import datetime
import json
from pathlib import Path

from src.backtest.strategy_backtester import StrategyBacktester
try:
    from src.strategies.xauusd_strategy import StrategyXAUUSD
    # EURUSD strategy removed - only XAUUSD remains
except ImportError:
    from strategies.xauusd_strategy import StrategyXAUUSD
    # EURUSD strategy removed - only XAUUSD remains


class StrategyOptimizer:
    """
    Оптимизатор параметров торговых стратегий
    
    Методы оптимизации:
    - Grid Search: перебор всех комбинаций
    - Random Search: случайная выборка (быстрее)
    """
    
    def __init__(self, symbol: str, start_date: str, end_date: str, initial_balance: float = 100):
        """
        Args:
            symbol: 'XAUUSD' или 'EURUSD'
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата конца (YYYY-MM-DD)
            initial_balance: Начальный баланс для бектеста
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.results = []
        
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """
        Получить пространство параметров для оптимизации
        
        Returns:
            Dict с параметрами и их возможными значениями
        """
        if self.symbol == 'XAUUSD':
            return {
                'atr_period': [14, 20, 30],
                'atr_multiplier': [1.5, 2.0, 2.5, 3.0],
                'risk_percent': [0.01, 0.015, 0.02],
                'min_rr': [1.5, 2.0, 2.5],
                'ob_lookback': [10, 15, 20],
                'fvg_min_size': [0.5, 1.0, 1.5],
                'trend_ema_fast': [20, 50],
                'trend_ema_slow': [100, 200]
            }
        else:  # EURUSD
            return {
                'atr_period': [14, 20, 30],
                'atr_multiplier': [1.5, 2.0, 2.5],
                'risk_percent': [0.01, 0.015, 0.02],
                'min_rr': [1.5, 2.0, 2.5],
                'ob_lookback': [10, 15, 20],
                'fvg_threshold': [0.5, 1.0, 1.5]
            }
    
    def optimize_grid_search(self, 
                            param_space: Dict[str, List[Any]] = None,
                            metric: str = 'sharpe',
                            top_n: int = 10,
                            progress_callback=None) -> List[Dict]:
        """
        Grid Search оптимизация
        
        Args:
            param_space: Пространство параметров (если None - используется дефолтное)
            metric: Метрика для оптимизации ('sharpe', 'profit', 'winrate', 'drawdown')
            top_n: Количество лучших результатов
            progress_callback: Функция для обновления прогресса (current, total)
            
        Returns:
            List[Dict] с топ-N конфигурациями
        """
        if param_space is None:
            param_space = self.get_parameter_space()
        
        # Генерируем все комбинации
        param_names = list(param_space.keys())
        param_values = list(param_space.values())
        combinations = list(product(*param_values))
        
        total = len(combinations)
        print(f"🔍 Grid Search: {total} комбинаций для тестирования")
        
        self.results = []
        
        for idx, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            
            # Обновляем прогресс
            if progress_callback:
                progress_callback(idx + 1, total)
            
            # Запускаем бектест с этими параметрами
            try:
                metrics = self._run_backtest(params)
                
                result = {
                    'params': params,
                    'metrics': metrics,
                    'score': self._calculate_score(metrics, metric)
                }
                self.results.append(result)
                
            except Exception as e:
                print(f"⚠️ Ошибка для {params}: {e}")
                continue
        
        # Сортируем по score (от лучшего к худшему)
        self.results.sort(key=lambda x: x['score'], reverse=True)
        
        return self.results[:top_n]
    
    def optimize_random_search(self,
                               param_space: Dict[str, List[Any]] = None,
                               n_iterations: int = 100,
                               metric: str = 'sharpe',
                               top_n: int = 10,
                               progress_callback=None) -> List[Dict]:
        """
        Random Search оптимизация (быстрее Grid Search)
        
        Args:
            param_space: Пространство параметров
            n_iterations: Количество итераций
            metric: Метрика для оптимизации
            top_n: Количество лучших результатов
            progress_callback: Функция для обновления прогресса
            
        Returns:
            List[Dict] с топ-N конфигурациями
        """
        if param_space is None:
            param_space = self.get_parameter_space()
        
        print(f"🎲 Random Search: {n_iterations} случайных комбинаций")
        
        self.results = []
        
        for idx in range(n_iterations):
            # Генерируем случайную комбинацию
            params = {}
            for param_name, param_values in param_space.items():
                params[param_name] = np.random.choice(param_values)
            
            # Обновляем прогресс
            if progress_callback:
                progress_callback(idx + 1, n_iterations)
            
            # Запускаем бектест
            try:
                metrics = self._run_backtest(params)
                
                result = {
                    'params': params,
                    'metrics': metrics,
                    'score': self._calculate_score(metrics, metric)
                }
                self.results.append(result)
                
            except Exception as e:
                print(f"⚠️ Ошибка для {params}: {e}")
                continue
        
        # Сортируем по score
        self.results.sort(key=lambda x: x['score'], reverse=True)
        
        return self.results[:top_n]
    
    def _run_backtest(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Запустить бектест с заданными параметрами
        
        Args:
            params: Параметры стратегии
            
        Returns:
            Dict с метриками
        """
        # Создаем стратегию (только XAUUSD)
        strategy = StrategyXAUUSD(symbol=self.symbol)
        
        # Применяем параметры к стратегии
        for param_name, param_value in params.items():
            if hasattr(strategy, param_name):
                setattr(strategy, param_name, param_value)
        
        # Запускаем бектест с настоящей стратегией
        backtester = StrategyBacktester(strategy=strategy, initial_balance=self.initial_balance)
        result = backtester.run_backtest(start_date=self.start_date, end_date=self.end_date)
        
        # Преобразуем ключи в стандартные
        metrics = {
            'total_return': result.get('roi', 0),
            'win_rate': result.get('win_rate', 0),
            'sharpe_ratio': 0,
            'max_drawdown': result.get('max_dd', 0),
            'profit_factor': 0,
            'total_trades': result.get('trades', 0)
        }
        
        return metrics
    
    def _calculate_score(self, metrics: Dict[str, float], metric: str) -> float:
        """
        Вычислить score для ранжирования
        
        Args:
            metrics: Метрики бектеста
            metric: Метрика для оптимизации
            
        Returns:
            Score (чем выше, тем лучше)
        """
        if metric == 'sharpe':
            return metrics.get('sharpe_ratio', 0)
        
        elif metric == 'profit':
            return metrics.get('total_return', 0)
        
        elif metric == 'winrate':
            return metrics.get('win_rate', 0)
        
        elif metric == 'drawdown':
            # Для drawdown - чем меньше, тем лучше, поэтому инвертируем
            dd = metrics.get('max_drawdown', 100)
            return -dd if dd > 0 else 0
        
        elif metric == 'profit_factor':
            return metrics.get('profit_factor', 0)
        
        elif metric == 'combined':
            # Комбинированная метрика
            sharpe = metrics.get('sharpe_ratio', 0)
            winrate = metrics.get('win_rate', 0) / 100  # нормализуем
            dd = metrics.get('max_drawdown', 100)
            
            # Формула: Sharpe * Winrate * (1 - DD/100)
            score = sharpe * winrate * (1 - dd / 100)
            return max(0, score)
        
        else:
            return metrics.get('sharpe_ratio', 0)
    
    def save_results(self, filepath: str = None):
        """
        Сохранить результаты оптимизации
        
        Args:
            filepath: Путь к файлу (если None - auto-generate)
        """
        if not self.results:
            print("⚠️ Нет результатов для сохранения")
            return
        
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"results/{self.symbol.lower()}/optimization_{timestamp}.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Конвертируем results в JSON-friendly формат
        json_results = []
        for result in self.results:
            json_results.append({
                'params': result['params'],
                'metrics': result['metrics'],
                'score': result['score']
            })
        
        # Атомарное сохранение
        temp_file = filepath.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)
            temp_file.replace(filepath)
            print(f"✅ Результаты сохранены: {filepath}")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def print_top_results(self, top_n: int = 5):
        """
        Вывести топ-N результатов
        
        Args:
            top_n: Количество результатов
        """
        if not self.results:
            print("⚠️ Нет результатов")
            return
        
        print(f"\n{'='*80}")
        print(f"🏆 Топ-{top_n} конфигураций для {self.symbol}")
        print(f"{'='*80}\n")
        
        for idx, result in enumerate(self.results[:top_n], 1):
            params = result['params']
            metrics = result['metrics']
            score = result['score']
            
            print(f"#{idx} | Score: {score:.4f}")
            print(f"Parameters:")
            for param, value in params.items():
                print(f"  - {param}: {value}")
            
            print(f"Metrics:")
            print(f"  - Total Return: {metrics.get('total_return', 0):.2f}%")
            print(f"  - Win Rate: {metrics.get('win_rate', 0):.2f}%")
            print(f"  - Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  - Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"  - Profit Factor: {metrics.get('profit_factor', 0):.2f}")
            print(f"  - Total Trades: {metrics.get('total_trades', 0)}")
            print()


def run_optimization_example():
    """
    Пример использования оптимизатора
    """
    print("🚀 Запуск примера оптимизации...")
    
    # Загружаем данные
    data_path = "data/backtest/XAUUSD_H1_2023_2025.csv"
    data = pd.read_csv(data_path)
    data['time'] = pd.to_datetime(data['time'])
    
    # Фильтруем 2024 год для теста
    data_2024 = data[(data['time'] >= '2024-01-01') & (data['time'] < '2025-01-01')]
    
    print(f"📊 Данные загружены: {len(data_2024)} свечей")
    
    # Создаем оптимизатор
    optimizer = StrategyOptimizer(
        symbol='XAUUSD',
        data=data_2024,
        initial_balance=10000
    )
    
    # Уменьшенное пространство параметров для быстрого теста
    param_space = {
        'atr_period': [14, 20],
        'atr_multiplier': [1.5, 2.0, 2.5],
        'risk_percent': [0.01, 0.02],
        'min_rr': [1.5, 2.0]
    }
    
    def progress(current, total):
        percent = current / total * 100
        print(f"Прогресс: {current}/{total} ({percent:.1f}%)", end='\r')
    
    # Запускаем Grid Search
    top_configs = optimizer.optimize_grid_search(
        param_space=param_space,
        metric='combined',
        top_n=5,
        progress_callback=progress
    )
    
    # Выводим результаты
    optimizer.print_top_results(top_n=5)
    
    # Сохраняем результаты
    optimizer.save_results()
    
    print("\n✅ Оптимизация завершена!")


if __name__ == '__main__':
    run_optimization_example()

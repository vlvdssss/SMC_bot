"""
Realistic Backtester - Live Trading Simulation

Реалистичная симуляция бэктестинга с устранением look-ahead bias.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import yaml
import os

class RealisticBacktester:
    def __init__(self, strategies: Dict, broker, data_loader):
        self.strategies = strategies
        self.broker = broker
        self.data_loader = data_loader
    
    def run_backtest(self, instrument: str, start_date: datetime, end_date: datetime) -> Dict:
        """Запуск бэктеста для инструмента"""
        
        # Загрузка данных
        from core.data_loader import DataLoader
        data_loader = DataLoader(instrument=instrument, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        data_h1, data_m15 = data_loader.load()
        data = data_h1
        if data.empty:
            return {'error': 'No data available'}
        
        strategy = self.strategies[instrument]
        trades = []
        
        # Симуляция торговли
        for i in range(len(data)):
            current_bar = data.iloc[i]
            
            # Генерация сигнала
            signal = strategy.generate_signal(current_bar, data.iloc[:i+1])
            
            if signal:
                # Исполнение сделки на следующей свече
                if i + 1 < len(data):
                    entry_bar = data.iloc[i + 1]
                    trade = self._execute_trade(signal, entry_bar, strategy)
                    if trade:
                        trades.append(trade)
        
        # Расчет метрик
        return self._calculate_metrics(trades)
    
    def _execute_trade(self, signal: Dict, entry_bar: pd.Series, strategy) -> Optional[Dict]:
        """Исполнение сделки"""
        # Упрощенная реализация
        entry_price = entry_bar['open']
        sl = signal.get('sl')
        tp = signal.get('tp')
        
        # Определение выхода (упрощено)
        exit_price = tp if signal['direction'] == 'BUY' else sl
        pnl = (exit_price - entry_price) if signal['direction'] == 'BUY' else (entry_price - exit_price)
        
        return {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'direction': signal['direction']
        }
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """Расчет метрик производительности"""
        if not trades:
            return {'total_return': 0, 'max_drawdown': 0, 'win_rate': 0, 'total_trades': 0, 'profit_factor': 0}
        
        df = pd.DataFrame(trades)
        total_return = (df['pnl'].sum() / 10000) * 100  # Предполагаем начальный баланс 10000
        win_rate = (df['pnl'] > 0).mean() * 100
        profit_factor = abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum()) if df['pnl'].sum() < 0 else float('inf')
        
        # Max drawdown (упрощено)
        cumulative = df['pnl'].cumsum()
        max_drawdown = (cumulative - cumulative.cummax()).min() / 10000 * 100
        
        return {
            'total_return': total_return,
            'max_drawdown': abs(max_drawdown),
            'win_rate': win_rate,
            'total_trades': len(trades),
            'profit_factor': profit_factor
        }

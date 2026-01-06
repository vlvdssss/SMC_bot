"""
Strategy Backtester - Realistic backtest using actual strategy code

Бэктестер который использует настоящий код стратегий для реалистичных результатов.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.data_loader import DataLoader
from src.core.broker_sim import BrokerSim


class StrategyBacktester:
    """Бэктестер использующий реальный код стратегий."""

    def __init__(self, strategy, initial_balance: float = 100.0, risk_pct: float = 1.0):
        """
        Args:
            strategy: Экземпляр стратегии (StrategyXAUUSD или StrategyEURUSD_SMC_Retracement)
            initial_balance: Начальный баланс
            risk_pct: Риск на сделку в % (default: 1.0%)
        """
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.symbol = strategy.instrument

    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Запустить бэктест используя реальную стратегию.
        
        Args:
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата конца (YYYY-MM-DD)
            
        Returns:
            Dict с метриками
        """
        
        print(f"Loading data for {self.symbol} from {start_date} to {end_date}...")
        
        # Загрузка данных
        loader = DataLoader(self.symbol, start_date, end_date)
        h1_data, m15_data = loader.load()
        
        if h1_data.empty or m15_data.empty:
            print("❌ No data available")
            return self._empty_result()
        
        print(f"OK Loaded {len(h1_data)} H1 bars, {len(m15_data)} M15 bars")
        
        # Загружаем данные в стратегию
        self.strategy.load_data(h1_data, m15_data)
        
        # Ensure datetime index
        if 'time' in h1_data.columns:
            h1_data['time'] = pd.to_datetime(h1_data['time'])
            h1_data = h1_data.set_index('time')
        if 'time' in m15_data.columns:
            m15_data['time'] = pd.to_datetime(m15_data['time'])
            m15_data = m15_data.set_index('time')
        
        # Initialize broker simulator with symbol-specific parameters
        if 'EURUSD' in self.symbol.upper():
            # EURUSD настройки
            broker = BrokerSim(
                leverage=100,
                spread_points=1.5,  # 1.5 pips
                commission_per_lot=0.0,  # Нет комиссии
                contract_size=100000,  # Forex standard lot
                spread_multiplier=0.0001,  # 1 pip = 0.0001 для EURUSD
                slippage_min=0.00015,  # 1.5 pips
                slippage_max=0.00030   # 3 pips
            )
        else:
            # XAUUSD настройки (default)
            broker = BrokerSim(
                leverage=100,
                spread_points=0.25 * 100,  # XAUUSD spread
                commission_per_lot=7.0,
                contract_size=100,
                spread_multiplier=0.01,
                slippage_min=0.15,
                slippage_max=0.40
            )
        
        # Account state
        balance = self.initial_balance
        equity = balance
        open_positions = []
        trades_history = []
        equity_curve = [balance]
        
        # Main loop - iterate through M15 bars
        total_bars = len(m15_data) - 1
        print(f"\nProcessing {total_bars} M15 bars...")
        progress_step = max(1, total_bars // 20)
        
        for i in range(50, total_bars):  # Skip first 50 bars for indicators
            if i % progress_step == 0:
                pct = (i / total_bars) * 100
                print(f"  {pct:.0f}% | Trades: {len(trades_history)} | Balance: ${balance:.2f}")
            
            current_bar = m15_data.iloc[i]
            next_bar = m15_data.iloc[i + 1]
            current_time = m15_data.index[i]
            
            # Find corresponding H1 bar
            h1_idx = self._find_h1_index(h1_data, current_time)
            if h1_idx is None:
                continue
            
            # Step 1: Check open positions for SL/TP
            for pos in open_positions[:]:
                hit_sl = False
                hit_tp = False
                exit_price = None
                exit_reason = None
                
                if pos['direction'] == 'BUY':
                    if current_bar['low'] <= pos['sl']:
                        hit_sl = True
                        exit_price = pos['sl']
                        exit_reason = 'SL'
                    elif current_bar['high'] >= pos['tp']:
                        hit_tp = True
                        exit_price = pos['tp']
                        exit_reason = 'TP'
                else:  # SELL
                    if current_bar['high'] >= pos['sl']:
                        hit_sl = True
                        exit_price = pos['sl']
                        exit_reason = 'SL'
                    elif current_bar['low'] <= pos['tp']:
                        hit_tp = True
                        exit_price = pos['tp']
                        exit_reason = 'TP'
                
                if hit_sl or hit_tp:
                    # Close position
                    pnl = broker.calculate_pnl(
                        pos['entry_price'],
                        exit_price,
                        pos['direction'],
                        pos['lot_size']
                    )
                    
                    balance += pnl
                    
                    trades_history.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': current_time,
                        'direction': pos['direction'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'sl': pos['sl'],
                        'tp': pos['tp'],
                        'lot_size': pos['lot_size'],
                        'pnl': pnl,
                        'exit_reason': exit_reason,
                        'balance': balance
                    })
                    
                    open_positions.remove(pos)
                    equity_curve.append(balance)
            
            # Step 2: Check for new signals (if no open positions)
            if len(open_positions) == 0:
                # Generate signal using actual strategy
                # Analysis на close текущей свечи, entry на open следующей
                analysis_price = current_bar['close']
                entry_price = next_bar['open']
                
                # Check if strategy needs current_time parameter (EURUSD)
                try:
                    signal = self.strategy.generate_signal(
                        current_m15_idx=i,
                        analysis_price=analysis_price,
                        entry_price=entry_price,
                        current_time=current_time,
                        current_h1_idx=h1_idx
                    )
                except TypeError:
                    # XAUUSD doesn't need current_time
                    signal = self.strategy.generate_signal(
                        current_m15_idx=i,
                        analysis_price=analysis_price,
                        entry_price=entry_price,
                        current_h1_idx=h1_idx
                    )
                
                if signal and signal.get('valid') and signal.get('direction'):
                    # Execute trade using strategy's execute_trade method
                    trade_params = self.strategy.execute_trade(
                        signal=signal,
                        balance=balance,
                        risk_pct=self.risk_pct
                    )
                    
                    if trade_params:
                        # Increment daily trades counter
                        self.strategy.trades_today += 1
                        
                        # Apply spread and slippage to entry price
                        real_entry = broker.apply_spread(trade_params['entry'], trade_params['direction'])
                        real_entry = broker.apply_slippage(real_entry, trade_params['direction'])
                        
                        # Adjust SL and TP based on real entry (not simulated entry)
                        # Keep same distance from real entry as original
                        if trade_params['direction'] == 'BUY':
                            sl_distance = trade_params['entry'] - trade_params['sl']
                            tp_distance = trade_params['tp'] - trade_params['entry']
                            adjusted_sl = real_entry - sl_distance
                            adjusted_tp = real_entry + tp_distance
                        else:  # SELL
                            sl_distance = trade_params['sl'] - trade_params['entry']
                            tp_distance = trade_params['entry'] - trade_params['tp']
                            adjusted_sl = real_entry + sl_distance
                            adjusted_tp = real_entry - tp_distance
                        
                        # Open position on next bar with REAL entry price
                        open_positions.append({
                            'entry_time': m15_data.index[i + 1],
                            'direction': trade_params['direction'],
                            'entry_price': real_entry,  # ← REAL entry with spread+slippage
                            'sl': adjusted_sl,  # ← Adjusted SL
                            'tp': adjusted_tp,  # ← Adjusted TP
                            'lot_size': trade_params['lot_size']
                        })
        
        # Close any remaining open positions at final price
        if len(open_positions) > 0:
            final_price = m15_data.iloc[-1]['close']
            for pos in open_positions:
                pnl = broker.calculate_pnl(
                    pos['entry_price'],
                    final_price,
                    pos['direction'],
                    pos['lot_size']
                )
                balance += pnl
                
                trades_history.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': m15_data.index[-1],
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': final_price,
                    'sl': pos['sl'],
                    'tp': pos['tp'],
                    'lot_size': pos['lot_size'],
                    'pnl': pnl,
                    'exit_reason': 'END',
                    'balance': balance
                })
        
        print(f"  100% | Trades: {len(trades_history)} | Balance: ${balance:.2f}\n")
        print(f"OK Backtest complete!")
        
        # Calculate metrics
        return self._calculate_metrics(trades_history, balance)
    
    def _find_h1_index(self, h1_data: pd.DataFrame, m15_time: pd.Timestamp) -> int:
        """Find corresponding H1 bar index for M15 timestamp."""
        try:
            # Find H1 bar that contains this M15 time
            h1_idx = h1_data.index.get_indexer([m15_time], method='ffill')[0]
            if h1_idx >= 0:
                return h1_idx
        except:
            pass
        return None
    
    def _calculate_metrics(self, trades: List[Dict], final_balance: float) -> Dict[str, Any]:
        """Calculate backtest metrics."""
        if len(trades) == 0:
            return self._empty_result()
        
        df = pd.DataFrame(trades)
        
        # ROI
        roi = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        # Win Rate
        winning_trades = df[df['pnl'] > 0]
        win_rate = (len(winning_trades) / len(df)) * 100 if len(df) > 0 else 0
        
        # Max Drawdown
        equity_curve = [self.initial_balance]
        for trade in trades:
            equity_curve.append(trade['balance'])
        
        peak = self.initial_balance
        max_dd = 0
        max_dd_amount = 0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            dd_amount = peak - equity
            if dd > max_dd:
                max_dd = dd
                max_dd_amount = dd_amount
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_profit': final_balance - self.initial_balance,
            'roi': roi,
            'trades': len(trades),
            'win_rate': win_rate,
            'max_dd': max_dd,
            'max_dd_amount': max_dd_amount,
            'trades_list': trades  # Добавляем список сделок
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result."""
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.initial_balance,
            'total_profit': 0,
            'roi': 0,
            'trades': 0,
            'win_rate': 0,
            'max_dd': 0,
            'max_dd_amount': 0
        }

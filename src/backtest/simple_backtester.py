#!/usr/bin/env python3
"""
Simple Backtester - Fast H1-only backtest for validation

Simplified backtest using only H1 data for faster execution.
Still REALISTIC with proper spread, commission, slippage.
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


class SimpleBacktester:
    """Simple H1-based backtester for quick validation."""

    def __init__(self, initial_balance: float = 100.0):
        self.initial_balance = initial_balance

        # XAUUSD config
        self.config = {
            'contract_size': 100,
            'spread': 0.25,
            'commission': 7.0,
            'slippage_min': 0.15,
            'slippage_max': 0.40,
            'risk_pct': 0.75,
            'atr_period': 14,
            'swing_period': 20
        }

    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Run simple H1 backtest."""
        
        print(f"Loading H1 data for {start_date} to {end_date}...")
        
        # Load data
        loader = DataLoader('XAUUSD', start_date, end_date)
        h1_data, _ = loader.load()
        
        if h1_data.empty:
            print("❌ No data available")
            return self._empty_result()
        
        print(f"OK Loaded {len(h1_data)} H1 bars")
        
        # Ensure datetime index
        if 'time' in h1_data.columns:
            h1_data['time'] = pd.to_datetime(h1_data['time'])
            h1_data = h1_data.set_index('time')
        
        # Initialize broker
        broker = BrokerSim(
            leverage=100,
            spread_points=self.config['spread'] * 100,
            commission_per_lot=self.config['commission'],
            contract_size=self.config['contract_size'],
            spread_multiplier=0.01,
            slippage_min=self.config['slippage_min'],
            slippage_max=self.config['slippage_max']
        )
        
        # Account state
        balance = self.initial_balance
        equity = balance
        open_positions = []
        trades_history = []
        equity_curve = [balance]
        
        # Precompute indicators
        h1_data['atr'] = self._calculate_atr(h1_data, self.config['atr_period'])
        h1_data['swing_high'] = h1_data['high'].rolling(self.config['swing_period']).max()
        h1_data['swing_low'] = h1_data['low'].rolling(self.config['swing_period']).min()
        
        # BOS tracking
        last_swing_high = None
        last_swing_low = None
        bos_direction = None
        
        # CRITICAL FILTERS (like real strategy)
        trades_today = 0
        current_date = None
        max_trades_per_day = 1  # Limit overtrading!
        
        # Main loop
        total_bars = len(h1_data) - 1
        print(f"\nProcessing {total_bars} bars...")
        progress_step = max(1, total_bars // 20)
        
        for i in range(50, total_bars):
            if i % progress_step == 0:
                pct = (i / total_bars) * 100
                print(f"  {pct:.0f}% | Trades: {len(trades_history)} | Balance: ${balance:.2f}")
            
            current_bar = h1_data.iloc[i]
            next_bar = h1_data.iloc[i + 1]
            current_time = h1_data.index[i]
            
            # Step 1: Check open positions for SL/TP
            for pos in open_positions[:]:
                hit_sl = False
                hit_tp = False
                exit_price = None
                
                if pos['direction'] == 'BUY':
                    if current_bar['low'] <= pos['sl']:
                        hit_sl = True
                        exit_price = pos['sl']
                    elif current_bar['high'] >= pos['tp']:
                        hit_tp = True
                        exit_price = pos['tp']
                else:  # SELL
                    if current_bar['high'] >= pos['sl']:
                        hit_sl = True
                        exit_price = pos['sl']
                    elif current_bar['low'] <= pos['tp']:
                        hit_tp = True
                        exit_price = pos['tp']
                
                if hit_sl or hit_tp:
                    pnl = self._calculate_pnl(pos, exit_price, broker)
                    balance += pnl
                    
                    trades_history.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': current_time,
                        'direction': pos['direction'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'lot_size': pos['lot_size'],
                        'pnl': pnl,
                        'reason': 'SL' if hit_sl else 'TP',
                        'balance': balance
                    })
                    
                    open_positions.remove(pos)
            
            # Update equity
            current_price = current_bar['close']
            equity = balance
            for pos in open_positions:
                unrealized_pnl = self._calculate_unrealized_pnl(pos, current_price, broker)
                equity += unrealized_pnl
            
            equity_curve.append(equity)
            
            # Step 2: Check for new signals
            if len(open_positions) == 0:  # One position at a time
                # Reset daily counter
                bar_date = h1_data.index[i].date()
                if current_date != bar_date:
                    trades_today = 0
                    current_date = bar_date
                
                # FILTER 1: Max 1 trade per day
                if trades_today >= max_trades_per_day:
                    continue
                
                # Update BOS
                if last_swing_high is None or i >= 50:
                    last_swing_high = h1_data.iloc[max(0, i-20):i]['high'].max()
                    last_swing_low = h1_data.iloc[max(0, i-20):i]['low'].min()
                
                if current_bar['close'] > last_swing_high:
                    bos_direction = 'BUY'
                elif current_bar['close'] < last_swing_low:
                    bos_direction = 'SELL'
                
                # Simple signal generation
                if bos_direction and current_bar['atr'] > 0:
                    atr = current_bar['atr']
                    
                    # FILTER 2: ATR in normal range (0.7x - 1.5x average)
                    atr_avg = h1_data.iloc[max(0, i-100):i]['atr'].mean()
                    if atr < atr_avg * 0.7 or atr > atr_avg * 1.5:
                        continue  # Skip low or high volatility
                    
                    # Entry conditions - MORE STRICT
                    signal_valid = False
                    direction = None
                    entry_price = next_bar['open']
                    
                    if bos_direction == 'BUY':
                        # Buy ONLY on pullback (not just red candle)
                        pullback_depth = (current_bar['open'] - current_bar['close']) / atr
                        if current_bar['close'] < current_bar['open'] and pullback_depth > 0.3:
                            signal_valid = True
                            direction = 'BUY'
                            sl = entry_price - (atr * 1.5)
                            tp = entry_price + (atr * 3.0)
                    
                    elif bos_direction == 'SELL':
                        # Sell ONLY on pullback
                        pullback_depth = (current_bar['close'] - current_bar['open']) / atr
                        if current_bar['close'] > current_bar['open'] and pullback_depth > 0.3:
                            signal_valid = True
                            direction = 'SELL'
                            sl = entry_price + (atr * 1.5)
                            tp = entry_price - (atr * 3.0)
                    
                    if signal_valid:
                        # Calculate lot size
                        lot_size = self._calculate_position_size(balance, entry_price, sl, broker)
                        
                        if lot_size > 0:
                            # 
                            
                            trades_today += 1  # Increment daily counterApply spread/slippage
                            entry_price_final = broker.apply_spread(entry_price, direction)
                            entry_price_final = broker.apply_slippage(entry_price_final, direction)
                            
                            # Commission
                            commission = broker.calculate_commission(lot_size)
                            balance -= commission
                            
                            # Open position
                            open_positions.append({
                                'direction': direction,
                                'entry_time': h1_data.index[i+1],
                                'entry_price': entry_price_final,
                                'sl': sl,
                                'tp': tp,
                                'lot_size': lot_size,
                                'commission': commission
                            })
        
        # Close remaining positions
        if open_positions:
            final_price = h1_data.iloc[-1]['close']
            for pos in open_positions:
                pnl = self._calculate_pnl(pos, final_price, broker)
                balance += pnl
                trades_history.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': h1_data.index[-1],
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': final_price,
                    'lot_size': pos['lot_size'],
                    'pnl': pnl,
                    'reason': 'EOD',
                    'balance': balance
                })
        
        print(f"\nOK Backtest complete!")
        return self._calculate_metrics(balance, equity_curve, trades_history)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR."""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def _calculate_position_size(self, balance: float, entry_price: float, 
                                  sl_price: float, broker: BrokerSim) -> float:
        """Calculate position size."""
        risk_amount = balance * (self.config['risk_pct'] / 100.0)
        price_risk = abs(entry_price - sl_price)
        
        if price_risk == 0:
            return 0.0
        
        lot_size = risk_amount / (broker.contract_size * price_risk)
        lot_size = round(lot_size, 2)
        
        return max(0.01, min(1.0, lot_size))
    
    def _calculate_pnl(self, position: Dict, exit_price: float, broker: BrokerSim) -> float:
        """Calculate PnL."""
        if position['direction'] == 'BUY':
            price_diff = exit_price - position['entry_price']
        else:
            price_diff = position['entry_price'] - exit_price
        
        return price_diff * position['lot_size'] * broker.contract_size
    
    def _calculate_unrealized_pnl(self, position: Dict, current_price: float, 
                                   broker: BrokerSim) -> float:
        """Calculate unrealized PnL."""
        if position['direction'] == 'BUY':
            price_diff = current_price - position['entry_price']
        else:
            price_diff = position['entry_price'] - current_price
        
        return price_diff * position['lot_size'] * broker.contract_size
    
    def _calculate_metrics(self, final_balance: float, equity_curve: List[float], 
                           trades: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics."""
        if not trades:
            return self._empty_result()
        
        df_trades = pd.DataFrame(trades)
        
        # ROI
        roi = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        # Win Rate
        winning_trades = df_trades[df_trades['pnl'] > 0]
        win_rate = (len(winning_trades) / len(df_trades)) * 100 if len(df_trades) > 0 else 0
        
        # Max Drawdown
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_dd = abs(drawdown.min())
        max_dd_amount = abs((equity_series - running_max).min())
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_profit': final_balance - self.initial_balance,
            'roi': roi,
            'trades': len(df_trades),
            'win_rate': win_rate,
            'max_dd': max_dd,
            'max_dd_amount': max_dd_amount
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Empty result."""
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


def run_simple_backtest(year: int):
    """Run simple backtest."""
    backtester = SimpleBacktester()
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    print(f"\n{'='*60}")
    print(f"SIMPLE XAUUSD Backtest for {year}")
    print(f"{'='*60}\n")
    
    result = backtester.run_backtest(start_date, end_date)
    
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS FOR {year}")
    print(f"{'='*60}")
    print(f"Initial Balance: ${result['initial_balance']:.2f}")
    print(f"Final Balance: ${result['final_balance']:.2f}")
    print(f"Total Profit: ${result['total_profit']:.2f}")
    print(f"ROI: {result['roi']:.2f}%")
    print(f"Total Trades: {result['trades']}")
    print(f"Win Rate: {result['win_rate']:.2f}%")
    print(f"Max Drawdown: {result['max_dd']:.2f}% (${result['max_dd_amount']:.2f})")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    run_simple_backtest(year)

"""
Run backtest for trading strategies.

Usage:
    python run_backtest.py --instrument xauusd --start 2023-01-01 --end 2023-12-31
    python run_backtest.py --instrument us30 --start 2024-01-01 --end 2024-12-31
    python run_backtest.py --instrument xauusd --start 2025-01-01 --end 2025-12-15 --balance 100
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from strategies.xauusd.strategy import StrategyXAUUSD
from strategies.eurusd.strategy import StrategyEURUSD_SMC_Retracement
from BAZA.core.data_loader import DataLoader
from BAZA.core.broker_sim import BrokerSim
from BAZA.core.executor import Executor


def run_backtest(instrument: str, start_date: str, end_date: str, initial_balance: float = 100.0):
    """Run backtest for specified period."""
    
    instrument = instrument.lower()
    
    # Strategy configuration
    if instrument == 'xauusd':
        strategy_name = "XAUUSD Trend Following Baseline"
        strategy_class = StrategyXAUUSD
        risk_pct = 1.0  # Phase 2 Baseline: 1% risk per trade
        contract_size = 100  # XAUUSD: 100 oz per lot
        spread_points = 20.0
        spread_multiplier = 0.01  # 20 points = 0.20 USD
        commission_per_lot = 7.0
        price_decimals = 2  # XAUUSD: 2 знака (2150.45)
    elif instrument == 'eurusd':
        strategy_name = "EURUSD SMC Retracement Baseline"
        strategy_class = StrategyEURUSD_SMC_Retracement
        risk_pct = 0.5
        contract_size = 100000  # EURUSD: 100,000 units per lot
        spread_points = 1.5
        spread_multiplier = 0.0001  # 1.5 pips = 0.00015 USD
        commission_per_lot = 0.0  # No commission on forex usually
        price_decimals = 5  # EURUSD: 5 знаков (1.17220)
    else:
        raise ValueError(f"Unknown instrument: {instrument}. Supported: xauusd, eurusd")
    
    print("=" * 80)
    print(f"SMC-framework - {strategy_name} Backtest")
    print("=" * 80)
    print(f"Instrument: {instrument.upper()}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print(f"Risk per trade: {risk_pct}%")
    print("=" * 80)
    print()
    
    # Load data
    print("[*] Loading data...")
    loader = DataLoader(instrument=instrument, start_date=start_date, end_date=end_date)
    h1_data, m15_data = loader.load()
    print(f"  H1 bars: {len(h1_data)}")
    print(f"  M15 bars: {len(m15_data)}")
    print()
    
    # Initialize components
    strategy = strategy_class()
    strategy.load_data(h1_data, m15_data)
    
    broker = BrokerSim(
        leverage=100,
        spread_points=spread_points,
        spread_multiplier=spread_multiplier,
        commission_per_lot=commission_per_lot,
        contract_size=contract_size
    )
    
    executor = Executor(broker, contract_size=contract_size)
    
    # Backtest state
    balance = initial_balance
    equity = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0.0
    
    trades = []
    equity_curve = []
    
    # Align H1 and M15
    h1_idx = 0
    
    print("[*] Running backtest...")
    print()
    
    total_bars = len(m15_data)
    progress_step = max(1, total_bars // 20)  # Update every 5%
    
    for m15_idx in range(len(m15_data)):
        current_time = m15_data.iloc[m15_idx]['time']
        current_price = m15_data.iloc[m15_idx]['close']
        
        # Progress update every 5%
        if (m15_idx + 1) % progress_step == 0:
            progress = ((m15_idx + 1) / total_bars) * 100
            total_trades = len(trades)
            print(f"[>] Progress: {progress:.0f}% | Trades: {total_trades} | Balance: ${balance:,.2f} | Equity: ${equity:,.2f}")
        
        # Update H1 index
        while h1_idx < len(h1_data) - 1 and h1_data.iloc[h1_idx + 1]['time'] <= current_time:
            h1_idx += 1
        
        # Skip if not enough H1 data
        if h1_idx < 2:
            continue
        
        # Update H1 context
        strategy.build_context(h1_idx)
        
        # Check if position exists
        if executor.has_position():
            # Update position
            used_margin = executor.get_used_margin(current_price)
            floating_pnl = executor.get_floating_pnl(current_price)
            equity = balance + floating_pnl
            
            result = executor.update_position(current_price, current_time)
            
            if result['closed']:
                # Position closed
                balance += result['pnl']
                equity = balance
                
                # Track max DD
                if balance > peak_balance:
                    peak_balance = balance
                
                dd = ((peak_balance - balance) / peak_balance) * 100
                if dd > max_drawdown:
                    max_drawdown = dd
                
                # Record trade
                pos = executor.last_closed_position
                trades.append({
                    'entry_time': pos.entry_time,
                    'exit_time': pos.exit_time,
                    'direction': pos.direction,
                    'entry_price': pos.entry_price,
                    'exit_price': pos.exit_price,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'lot_size': pos.lot_size,
                    'pnl': pos.pnl,
                    'exit_reason': pos.exit_reason,
                    'balance': balance
                })
                
                # Log every 5th trade
                if len(trades) % 5 == 0:
                    print(f"[$] Trade #{len(trades)} closed | {pos.direction} | {pos.exit_reason} | PnL: ${pos.pnl:+.2f} | Balance: ${balance:,.2f}")
        else:
            # No position - check for signal
            if m15_idx < 20:
                continue
            
            signal = strategy.generate_signal(m15_idx, current_price)
            
            if signal['valid']:
                # Calculate lot size
                trade_params = strategy.execute_trade(signal, balance, risk_pct=risk_pct)
                
                if trade_params:
                    # Try to open position
                    used_margin = executor.get_used_margin(current_price) if executor.has_position() else 0.0
                    
                    opened = executor.open_position(
                        signal=signal,
                        lot_size=trade_params['lot_size'],
                        current_price=current_price,
                        current_time=current_time,
                        balance=balance,
                        equity=equity,
                        used_margin=used_margin
                    )
                    
                    if opened:
                        # Log every 5th trade opened
                        if (len(trades) + 1) % 5 == 1:
                            print(f"[+] Trade #{len(trades)+1} opened | {signal['direction']} | Entry: {current_price:.{price_decimals}f} | SL: {signal['sl']:.{price_decimals}f} | TP: {signal['tp']:.{price_decimals}f}")
        
        # Record equity
        if len(equity_curve) == 0 or equity_curve[-1]['time'] != current_time:
            equity_curve.append({
                'time': current_time,
                'balance': balance,
                'equity': equity
            })
    
    # Close any remaining position
    if executor.has_position():
        final_price = m15_data.iloc[-1]['close']
        final_time = m15_data.iloc[-1]['time']
        result = executor.update_position(final_price, final_time)
        if result['closed']:
            balance += result['pnl']
    
    # Calculate statistics
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if len(trades) == 0:
        print("WARNING: No trades executed")
        return
    
    df_trades = pd.DataFrame(trades)
    
    # Basic stats
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['pnl'] > 0])
    losing_trades = len(df_trades[df_trades['pnl'] < 0])
    win_rate = (winning_trades / total_trades) * 100
    
    total_pnl = df_trades['pnl'].sum()
    final_balance = balance
    roi = ((final_balance - initial_balance) / initial_balance) * 100
    
    avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    
    print(f"\n[=] Performance:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Wins: {winning_trades} | Losses: {losing_trades}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"\n[=] P&L:")
    print(f"  Initial Balance: ${initial_balance:,.2f}")
    print(f"  Final Balance: ${final_balance:,.2f}")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  ROI: {roi:,.2f}%")
    print(f"\n[=] Trade Quality:")
    print(f"  Avg Win: ${avg_win:.2f}")
    print(f"  Avg Loss: ${avg_loss:.2f}")
    if avg_loss != 0:
        print(f"  Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}")
    print(f"\n[=] Risk:")
    print(f"  Max Drawdown: {max_drawdown:.2f}%")
    
    print()
    print("=" * 80)
    
    # Save results
    year = start_date[:4]
    output_dir = Path(f"results/{instrument}/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    trades_file = output_dir / f"backtest_{start_date}_{end_date}_trades.csv"
    equity_file = output_dir / f"backtest_{start_date}_{end_date}_equity.csv"
    
    df_trades.to_csv(trades_file, index=False)
    pd.DataFrame(equity_curve).to_csv(equity_file, index=False)
    
    print(f"[OK] Results saved:")
    print(f"  {trades_file}")
    print(f"  {equity_file}")
    print()
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'max_dd': max_drawdown,
        'roi': roi,
        'final_balance': final_balance
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run backtest for trading strategies')
    parser.add_argument('--instrument', type=str, required=True, choices=['xauusd', 'eurusd', 'gbpusd'], help='Instrument to backtest')
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    
    args = parser.parse_args()
    
    run_backtest(args.instrument, args.start, args.end, args.balance)

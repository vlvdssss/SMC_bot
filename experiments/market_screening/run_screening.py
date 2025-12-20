"""
Market Screening Runner

НАЗНАЧЕНИЕ:
Запуск backtest для всех screening инструментов с единой логикой.

INSTRUMENTS:
1) USDCHF
2) EURGBP
3) NZDUSD
4) USDJPY
5) AUDCAD
6) XAGUSD

PARAMETERS (unified):
- Risk: 0.5%
- RR: 2:1
- Max trades/day: 1
- Period: 2023-2025
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
from screening_strategy import ScreeningStrategy


class SimpleBrokerSimulator:
    """Simple broker simulator for screening backtests"""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = []
        self.closed_trades = []
        
    def calculate_position_size(self, risk_percent: float, stop_distance: float, price: float):
        """Calculate position size based on risk"""
        risk_amount = self.balance * (risk_percent / 100.0)
        
        # For Forex: position size in lots
        # 1 lot = 100,000 units
        # Risk per pip = position_size * pip_value
        # pip_value ≈ 10 for standard lot (simplified)
        
        stop_distance_pips = stop_distance * 10000  # Convert to pips
        
        if stop_distance_pips == 0:
            return 0
            
        # Simplified: risk_amount = position_lots * stop_distance_pips * 10
        position_lots = risk_amount / (stop_distance_pips * 10)
        
        return max(0.01, round(position_lots, 2))  # Minimum 0.01 lot
        
    def open_position(self, signal: dict, entry_time):
        """Open new position"""
        direction = signal['direction']
        entry = signal['entry']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        risk_percent = signal['risk_percent']
        
        stop_distance = abs(entry - stop_loss)
        position_size = self.calculate_position_size(risk_percent, stop_distance, entry)
        
        if position_size == 0:
            return None
            
        position = {
            'direction': direction,
            'entry_price': entry,
            'entry_time': entry_time,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'risk_percent': risk_percent,
            'reason': signal.get('reason', 'Unknown')
        }
        
        self.positions.append(position)
        return position
        
    def update_positions(self, current_bar):
        """Update positions and close if hit SL/TP"""
        current_time = current_bar.name
        high = current_bar['High']
        low = current_bar['Low']
        close = current_bar['Close']
        
        positions_to_close = []
        
        for position in self.positions:
            hit_sl = False
            hit_tp = False
            exit_price = None
            
            if position['direction'] == 'long':
                # Check SL
                if low <= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                # Check TP
                elif high >= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
                    
            elif position['direction'] == 'short':
                # Check SL
                if high >= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                # Check TP
                elif low <= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
            
            if hit_sl or hit_tp:
                # Close position
                pnl_pips = 0
                if position['direction'] == 'long':
                    pnl_pips = (exit_price - position['entry_price']) * 10000
                else:
                    pnl_pips = (position['entry_price'] - exit_price) * 10000
                    
                pnl_money = pnl_pips * position['position_size'] * 10
                
                self.balance += pnl_money
                
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': current_time,
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'position_size': position['position_size'],
                    'pnl_pips': pnl_pips,
                    'pnl_money': pnl_money,
                    'outcome': 'TP' if hit_tp else 'SL',
                    'reason': position['reason']
                }
                
                self.closed_trades.append(trade)
                positions_to_close.append(position)
        
        # Remove closed positions
        for position in positions_to_close:
            self.positions.remove(position)
            
        # Update equity
        self.equity = self.balance
        
    def get_stats(self) -> dict:
        """Calculate statistics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'final_balance': self.balance,
                'roi': 0
            }
            
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t['pnl_money'] > 0]
        losing_trades = [t for t in self.closed_trades if t['pnl_money'] < 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl_money'] for t in self.closed_trades)
        
        # Calculate drawdown
        equity_curve = [self.initial_balance]
        running_balance = self.initial_balance
        for trade in self.closed_trades:
            running_balance += trade['pnl_money']
            equity_curve.append(running_balance)
            
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown_series = (equity_series - running_max) / running_max * 100
        max_drawdown = abs(drawdown_series.min())
        
        # Profit factor
        total_profit = sum(t['pnl_money'] for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t['pnl_money'] for t in losing_trades)) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        avg_win = np.mean([t['pnl_money'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_money'] for t in losing_trades]) if losing_trades else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'final_balance': self.balance,
            'roi': (self.balance - self.initial_balance) / self.initial_balance * 100
        }


def load_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load data from CSV"""
    filename = f"data/backtest/{symbol}_{timeframe}_2023_2025.csv"
    
    if not os.path.exists(filename):
        print(f"ERROR: File not found: {filename}")
        return None
        
    df = pd.read_csv(filename, index_col=0, parse_dates=True)
    return df


def run_backtest(symbol: str, start_date: str, end_date: str, initial_balance: float = 10000):
    """Run backtest for one instrument"""
    print(f"\n{'=' * 60}")
    print(f"BACKTESTING: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'=' * 60}")
    
    # Load data
    data_h1 = load_data(symbol, 'H1')
    data_m15 = load_data(symbol, 'M15')
    
    if data_h1 is None or data_m15 is None:
        print(f"ERROR: Failed to load data for {symbol}")
        return None
        
    # Filter by date range
    data_h1 = data_h1[start_date:end_date]
    data_m15 = data_m15[start_date:end_date]
    
    print(f"H1 bars: {len(data_h1)}")
    print(f"M15 bars: {len(data_m15)}")
    
    # Initialize strategy and broker
    strategy = ScreeningStrategy(symbol)
    broker = SimpleBrokerSimulator(initial_balance)
    
    # Run backtest
    total_bars = len(data_m15)
    progress_step = total_bars // 20  # 5% steps
    
    for i in range(len(data_m15)):
        current_bar = data_m15.iloc[i]
        
        # Update existing positions
        broker.update_positions(current_bar)
        
        # Check for new signals (only if no open positions)
        if len(broker.positions) == 0:
            signal = strategy.analyze(data_h1, data_m15, i)
            
            if signal:
                broker.open_position(signal, current_bar.name)
        
        # Progress
        if i % progress_step == 0 or i == total_bars - 1:
            progress = int((i / total_bars) * 100)
            print(f"Progress: {progress}% | Balance: ${broker.balance:.2f} | Trades: {len(broker.closed_trades)}")
    
    # Get statistics
    stats = broker.get_stats()
    
    # Get debug stats from strategy
    debug_stats = strategy.get_debug_stats()
    
    print(f"\n{'=' * 60}")
    print(f"DEBUG STATS: {symbol}")
    print(f"{'=' * 60}")
    print(f"Total bars analyzed: {debug_stats['total_bars']}")
    print(f"H1 direction found: {debug_stats['h1_direction_found']} ({debug_stats['h1_direction_found']/debug_stats['total_bars']*100:.1f}%)")
    print(f"OB found: {debug_stats['ob_found']} ({debug_stats['ob_found']/debug_stats['total_bars']*100:.2f}%)")
    print(f"Price in OB: {debug_stats['price_in_ob']} ({debug_stats['price_in_ob']/debug_stats['total_bars']*100:.3f}%)")
    print(f"Premium/Discount OK: {debug_stats['premium_discount_ok']} ({debug_stats['premium_discount_ok']/debug_stats['total_bars']*100:.3f}%)")
    print(f"Signals generated: {debug_stats['signals_generated']}")
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {symbol}")
    print(f"{'=' * 60}")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Total PnL: ${stats['total_pnl']:.2f}")
    print(f"ROI: {stats['roi']:.1f}%")
    print(f"Max Drawdown: {stats['max_drawdown']:.1f}%")
    print(f"Profit Factor: {stats['profit_factor']:.2f}")
    print(f"Final Balance: ${stats['final_balance']:.2f}")
    print(f"{'=' * 60}\n")
    
    # Save results
    results_dir = f"results/screening/{symbol}"
    os.makedirs(results_dir, exist_ok=True)
    
    # Save stats
    with open(f"{results_dir}/stats_{start_date}_{end_date}.json", 'w') as f:
        json.dump(stats, f, indent=2)
        
    # Save trades
    if broker.closed_trades:
        trades_df = pd.DataFrame(broker.closed_trades)
        trades_df.to_csv(f"{results_dir}/trades_{start_date}_{end_date}.csv", index=False)
    
    return stats


def main():
    """Main screening function"""
    instruments = [
        'USDCHF',
        'EURGBP',
        'NZDUSD',
        'USDJPY',
        'AUDCAD',
        'XAGUSD'
    ]
    
    # Quick screening: 2023 only (1 year)
    start_date = '2023-01-01'
    end_date = '2023-12-31'
    
    print("=" * 60)
    print("MARKET SCREENING - SMC FRAMEWORK")
    print("=" * 60)
    print(f"Instruments: {len(instruments)}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Strategy: Unified SMC Retracement")
    print(f"Risk: 0.5% per trade")
    print(f"RR: 2:1")
    print("=" * 60)
    
    # Run backtests for all instruments
    all_results = {}
    
    for symbol in instruments:
        stats = run_backtest(symbol, start_date, end_date)
        if stats:
            all_results[symbol] = stats
    
    # Generate summary table
    print("\n" + "=" * 80)
    print("SCREENING SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Instrument':<12} {'Trades':<8} {'WR%':<8} {'MaxDD%':<10} {'PF':<8} {'ROI%':<10} {'Verdict':<10}")
    print("-" * 80)
    
    for symbol in instruments:
        if symbol in all_results:
            stats = all_results[symbol]
            
            # Calculate verdict
            equity_up = stats['roi'] > 0
            dd_ok = stats['max_drawdown'] <= 15
            pf_ok = stats['profit_factor'] >= 1.3
            
            if equity_up and dd_ok and pf_ok:
                verdict = "WIN"
            else:
                verdict = "FAIL"
            
            # Handle zero trades case
            trades_per_year = stats['total_trades']  # Already 1 year
            
            print(f"{symbol:<12} {trades_per_year:<8.0f} {stats['win_rate']:<8.1f} "
                  f"{stats['max_drawdown']:<10.1f} {stats['profit_factor']:<8.2f} "
                  f"{stats['roi']:<10.1f} {verdict:<10}")
        else:
            print(f"{symbol:<12} {'ERROR':<8} {'-':<8} {'-':<10} {'-':<8} {'-':<10} {'ERROR':<10}")
    
    print("=" * 80)
    print("\nWIN Criteria:")
    print("- Equity UP (ROI > 0)")
    print("- Max DD <= 15%")
    print("- PF >= 1.3")
    print("=" * 80)
    
    # Save summary
    summary_file = "results/screening/SUMMARY.txt"
    os.makedirs("results/screening", exist_ok=True)
    
    with open(summary_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("MARKET SCREENING SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Period: {start_date} to {end_date}\n")
        f.write(f"Strategy: Unified SMC Retracement\n")
        f.write(f"Risk: 0.5% per trade, RR: 2:1\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"{'Instrument':<12} {'Trades/Yr':<12} {'WR%':<8} {'MaxDD%':<10} {'PF':<8} {'ROI%':<10} {'Verdict':<10}\n")
        f.write("-" * 80 + "\n")
        
        for symbol in instruments:
            if symbol in all_results:
                stats = all_results[symbol]
                
                equity_up = stats['roi'] > 0
                dd_ok = stats['max_drawdown'] <= 15
                pf_ok = stats['profit_factor'] >= 1.3
                
                if equity_up and dd_ok and pf_ok:
                    verdict = "WIN"
                else:
                    verdict = "FAIL"
                
                trades_per_year = stats['total_trades']  # Already 1 year
                
                f.write(f"{symbol:<12} {trades_per_year:<12.0f} {stats['win_rate']:<8.1f} "
                       f"{stats['max_drawdown']:<10.1f} {stats['profit_factor']:<8.2f} "
                       f"{stats['roi']:<10.1f} {verdict:<10}\n")
            else:
                f.write(f"{symbol:<12} {'ERROR':<12} {'-':<8} {'-':<10} {'-':<8} {'-':<10} {'ERROR':<10}\n")
        
        f.write("=" * 80 + "\n")
    
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()

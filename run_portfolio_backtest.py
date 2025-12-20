"""
Portfolio Backtest Runner - Simple parallel execution of two FROZEN baselines.

This script runs XAUUSD and EURUSD strategies in parallel with independent
signal generation and position management, but shared balance and equity.

CRITICAL RULES:
- NO CHANGES to baseline strategy logic
- NO optimization of weights or parameters  
- NO correlation filters or complex risk models
- Simple risk allocation: XAUUSD 0.75%, EURUSD 0.5%, max total 1.25%

Usage:
    python run_portfolio_backtest.py --start 2024-01-01 --end 2024-12-31 --balance 100
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


class PortfolioBacktest:
    """Simple portfolio backtest for two frozen baseline strategies."""
    
    def __init__(self, initial_balance: float = 100.0):
        self.initial_balance = initial_balance
        
        # Shared portfolio state
        self.balance = initial_balance
        self.equity = initial_balance
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        
        # Risk allocation (SIMPLE MODEL)
        self.risk_xauusd = 1.0   # % per trade (Phase 2 Baseline)
        self.risk_eurusd = 0.5   # % per trade
        self.max_total_risk = 1.5  # % maximum exposure
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        
        # Instruments configuration
        self.instruments = {
            'xauusd': {
                'name': 'XAUUSD Phase 2 Baseline',
                'strategy_class': StrategyXAUUSD,
                'contract_size': 100,
                'spread_points': 20.0,
                'spread_multiplier': 0.01,
                'commission_per_lot': 7.0,
                'price_decimals': 2,
                'risk_pct': self.risk_xauusd
            },
            'eurusd': {
                'name': 'EURUSD SMC Retracement Baseline',
                'strategy_class': StrategyEURUSD_SMC_Retracement,
                'contract_size': 100000,
                'spread_points': 1.5,
                'spread_multiplier': 0.0001,
                'commission_per_lot': 0.0,
                'price_decimals': 5,
                'risk_pct': self.risk_eurusd
            }
        }
        
        # Strategy instances
        self.strategies = {}
        self.executors = {}
        self.data = {}
        
    def load_data(self, start_date: str, end_date: str):
        """Load historical data for both instruments."""
        print("[*] Loading data...")
        
        for instrument in ['xauusd', 'eurusd']:
            loader = DataLoader(instrument=instrument, start_date=start_date, end_date=end_date)
            h1_data, m15_data = loader.load()
            
            self.data[instrument] = {
                'h1': h1_data,
                'm15': m15_data,
                'h1_idx': 0
            }
            
            print(f"  {instrument.upper()}: H1={len(h1_data)}, M15={len(m15_data)}")
        
        print()
    
    def initialize_strategies(self):
        """Initialize strategy instances and executors."""
        print("[*] Initializing strategies...")
        
        for instrument, config in self.instruments.items():
            # Create strategy instance
            strategy = config['strategy_class']()
            strategy.load_data(self.data[instrument]['h1'], self.data[instrument]['m15'])
            self.strategies[instrument] = strategy
            
            # Create broker simulator
            broker = BrokerSim(
                leverage=100,
                spread_points=config['spread_points'],
                spread_multiplier=config['spread_multiplier'],
                commission_per_lot=config['commission_per_lot'],
                contract_size=config['contract_size']
            )
            
            # Create executor
            executor = Executor(broker, contract_size=config['contract_size'])
            self.executors[instrument] = executor
            
            print(f"  {instrument.upper()}: {config['name']} - READY")
        
        print()
    
    def get_current_risk_exposure(self):
        """Calculate current total risk exposure from open positions."""
        total_exposure = 0.0
        
        for instrument in ['xauusd', 'eurusd']:
            if self.executors[instrument].has_position():
                # Approximate exposure as risk_pct used for this position
                total_exposure += self.instruments[instrument]['risk_pct']
        
        return total_exposure
    
    def can_open_position(self, instrument: str):
        """Check if we can open a new position given current exposure."""
        current_exposure = self.get_current_risk_exposure()
        new_risk = self.instruments[instrument]['risk_pct']
        
        # Would this exceed max total risk?
        return (current_exposure + new_risk) <= self.max_total_risk
    
    def update_positions(self, instrument: str, current_price: float, current_time):
        """Update position for given instrument."""
        executor = self.executors[instrument]
        
        if not executor.has_position():
            return
        
        # Update floating P&L
        floating_pnl = executor.get_floating_pnl(current_price)
        
        # Check if position closes
        result = executor.update_position(current_price, current_time)
        
        if result['closed']:
            # Position closed - update portfolio balance
            self.balance += result['pnl']
            self.equity = self.balance
            
            # Track drawdown
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            dd = ((self.peak_balance - self.balance) / self.peak_balance) * 100
            if dd > self.max_drawdown:
                self.max_drawdown = dd
            
            # Record trade
            pos = executor.last_closed_position
            self.trades.append({
                'instrument': instrument.upper(),
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
                'balance': self.balance
            })
            
            # Log trade
            if len(self.trades) % 5 == 0:
                print(f"[$] Trade #{len(self.trades)} | {instrument.upper()} {pos.direction} | {pos.exit_reason} | PnL: ${pos.pnl:+.2f} | Balance: ${self.balance:,.2f}")
    
    def check_signal(self, instrument: str, m15_idx: int, current_price: float, current_time):
        """Check for signal and potentially open position."""
        executor = self.executors[instrument]
        strategy = self.strategies[instrument]
        config = self.instruments[instrument]
        
        # Skip if already has position
        if executor.has_position():
            return
        
        # Check if we can open new position (risk limit)
        if not self.can_open_position(instrument):
            return
        
        # Get signal from strategy (different signatures for different strategies)
        if instrument == 'xauusd':
            signal = strategy.generate_signal(m15_idx, current_price)
        elif instrument == 'eurusd':
            signal = strategy.generate_signal(m15_idx, current_price, current_time)
        else:
            return
        
        if not signal['valid']:
            return
        
        # Calculate lot size using strategy logic
        trade_params = strategy.execute_trade(signal, self.balance, risk_pct=config['risk_pct'])
        
        if not trade_params:
            return
        
        # Open position
        opened = executor.open_position(
            signal=signal,
            lot_size=trade_params['lot_size'],
            current_price=current_price,
            current_time=current_time,
            balance=self.balance,
            equity=self.equity,
            used_margin=0.0
        )
        
        if opened and (len(self.trades) + 1) % 5 == 1:
            print(f"[+] Trade #{len(self.trades)+1} | {instrument.upper()} {signal['direction']} | Entry: {current_price:.{config['price_decimals']}f}")
    
    def run(self, start_date: str, end_date: str):
        """Run portfolio backtest."""
        print("=" * 80)
        print("SMC-framework - PORTFOLIO BACKTEST (XAUUSD + EURUSD)")
        print("=" * 80)
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Risk Model: XAUUSD {self.risk_xauusd}% + EURUSD {self.risk_eurusd}% (Max {self.max_total_risk}%)")
        print("=" * 80)
        print()
        
        # Load data
        self.load_data(start_date, end_date)
        
        # Initialize strategies
        self.initialize_strategies()
        
        # Find common M15 timeline (use XAUUSD as reference)
        m15_ref = self.data['xauusd']['m15']
        total_bars = len(m15_ref)
        progress_step = max(1, total_bars // 20)
        
        print("[*] Running portfolio backtest...")
        print()
        
        for m15_idx in range(total_bars):
            current_time = m15_ref.iloc[m15_idx]['time']
            
            # Progress update
            if (m15_idx + 1) % progress_step == 0:
                progress = ((m15_idx + 1) / total_bars) * 100
                print(f"[>] Progress: {progress:.0f}% | Trades: {len(self.trades)} | Balance: ${self.balance:,.2f} | Equity: ${self.equity:,.2f}")
            
            # Calculate total equity (balance + floating P&L)
            total_floating_pnl = 0.0
            
            # Process each instrument
            for instrument in ['xauusd', 'eurusd']:
                # Find corresponding M15 bar
                m15_data = self.data[instrument]['m15']
                
                # Simple time alignment - find closest bar
                time_diff = abs(m15_data['time'] - current_time)
                closest_idx = time_diff.idxmin()
                
                if time_diff.iloc[closest_idx].total_seconds() > 900:  # More than 15 min difference
                    continue
                
                current_price = m15_data.iloc[closest_idx]['close']
                
                # Update H1 index for this instrument
                h1_data = self.data[instrument]['h1']
                h1_idx = self.data[instrument]['h1_idx']
                
                while h1_idx < len(h1_data) - 1 and h1_data.iloc[h1_idx + 1]['time'] <= current_time:
                    h1_idx += 1
                
                self.data[instrument]['h1_idx'] = h1_idx
                
                # Skip if not enough H1 data
                if h1_idx < 2:
                    continue
                
                # Update H1 context for strategy
                self.strategies[instrument].build_context(h1_idx)
                
                # Update existing positions
                self.update_positions(instrument, current_price, current_time)
                
                # Check for new signals
                if closest_idx >= 20:  # Need minimum bars
                    self.check_signal(instrument, closest_idx, current_price, current_time)
                
                # Add floating P&L to equity
                if self.executors[instrument].has_position():
                    total_floating_pnl += self.executors[instrument].get_floating_pnl(current_price)
            
            # Update equity with floating P&L
            self.equity = self.balance + total_floating_pnl
            
            # Record equity curve
            if len(self.equity_curve) == 0 or self.equity_curve[-1]['time'] != current_time:
                self.equity_curve.append({
                    'time': current_time,
                    'balance': self.balance,
                    'equity': self.equity
                })
        
        # Close any remaining positions
        for instrument in ['xauusd', 'eurusd']:
            if self.executors[instrument].has_position():
                m15_data = self.data[instrument]['m15']
                final_price = m15_data.iloc[-1]['close']
                final_time = m15_data.iloc[-1]['time']
                result = self.executors[instrument].update_position(final_price, final_time)
                if result['closed']:
                    self.balance += result['pnl']
        
        # Generate report
        self.generate_report(start_date, end_date)
    
    def generate_report(self, start_date: str, end_date: str):
        """Generate portfolio backtest report."""
        print()
        print("=" * 80)
        print("PORTFOLIO RESULTS")
        print("=" * 80)
        
        if len(self.trades) == 0:
            print("⚠️  No trades executed")
            return
        
        df_trades = pd.DataFrame(self.trades)
        
        # Overall stats
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df_trades['pnl'].sum()
        final_balance = self.balance
        roi = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        # Per-instrument breakdown
        xauusd_trades = df_trades[df_trades['instrument'] == 'XAUUSD']
        eurusd_trades = df_trades[df_trades['instrument'] == 'EURUSD']
        
        xauusd_pnl = xauusd_trades['pnl'].sum() if len(xauusd_trades) > 0 else 0
        eurusd_pnl = eurusd_trades['pnl'].sum() if len(eurusd_trades) > 0 else 0
        
        xauusd_count = len(xauusd_trades)
        eurusd_count = len(eurusd_trades)
        
        # Profit contribution
        total_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        xauusd_profit = xauusd_trades[xauusd_trades['pnl'] > 0]['pnl'].sum() if len(xauusd_trades) > 0 else 0
        eurusd_profit = eurusd_trades[eurusd_trades['pnl'] > 0]['pnl'].sum() if len(eurusd_trades) > 0 else 0
        
        xauusd_contribution = (xauusd_profit / total_profit * 100) if total_profit > 0 else 0
        eurusd_contribution = (eurusd_profit / total_profit * 100) if total_profit > 0 else 0
        
        print(f"\n[=] Portfolio Performance:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Wins: {winning_trades} | Losses: {losing_trades}")
        print(f"  Win Rate: {win_rate:.2f}%")
        
        print(f"\n[=] Portfolio P&L:")
        print(f"  Initial Balance: ${self.initial_balance:,.2f}")
        print(f"  Final Balance: ${final_balance:,.2f}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  ROI: {roi:,.2f}%")
        
        print(f"\n[=] Risk:")
        print(f"  Max Drawdown: {self.max_drawdown:.2f}%")
        
        print(f"\n[=] Per-Instrument Breakdown:")
        print(f"  XAUUSD: {xauusd_count} trades | P&L: ${xauusd_pnl:+,.2f}")
        print(f"  EURUSD: {eurusd_count} trades | P&L: ${eurusd_pnl:+,.2f}")
        
        print(f"\n[=] Profit Contribution:")
        print(f"  XAUUSD: {xauusd_contribution:.1f}%")
        print(f"  EURUSD: {eurusd_contribution:.1f}%")
        
        print()
        print("=" * 80)
        
        # Save results
        year = start_date[:4]
        output_dir = Path(f"results/portfolio/{year}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        trades_file = output_dir / f"portfolio_{start_date}_{end_date}_trades.csv"
        equity_file = output_dir / f"portfolio_{start_date}_{end_date}_equity.csv"
        
        df_trades.to_csv(trades_file, index=False)
        pd.DataFrame(self.equity_curve).to_csv(equity_file, index=False)
        
        print(f"[OK] Results saved:")
        print(f"  {trades_file}")
        print(f"  {equity_file}")
        print()
        
        # Generate verdict
        self.generate_verdict(roi, win_rate)
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'max_dd': self.max_drawdown,
            'roi': roi,
            'final_balance': final_balance,
            'xauusd_trades': xauusd_count,
            'eurusd_trades': eurusd_count
        }
    
    def generate_verdict(self, roi: float, win_rate: float):
        """Generate portfolio verdict."""
        print("=" * 80)
        print("PORTFOLIO VERDICT")
        print("=" * 80)
        
        # Compare with individual baselines
        xauusd_baseline = {'dd': 11.5, 'roi': 952, 'wr': 60.8}  # 3-year avg
        eurusd_baseline = {'dd': 5.4, 'roi': 324, 'wr': 70.7}   # 3-year avg
        
        # Expected weighted performance (naive)
        expected_dd = (xauusd_baseline['dd'] * 0.6 + eurusd_baseline['dd'] * 0.4)  # Rough weight
        
        print(f"\n[=] Portfolio Equity:")
        if roi > 0:
            print(f"  ✅ UP (+{roi:.2f}%)")
        elif roi == 0:
            print(f"  ⚠️  FLAT (0.00%)")
        else:
            print(f"  ❌ DOWN ({roi:.2f}%)")
        
        print(f"\n[=] Portfolio DD vs Individual:")
        print(f"  Portfolio DD: {self.max_drawdown:.2f}%")
        print(f"  XAUUSD Baseline DD: {xauusd_baseline['dd']:.2f}%")
        print(f"  EURUSD Baseline DD: {eurusd_baseline['dd']:.2f}%")
        
        if self.max_drawdown < xauusd_baseline['dd'] and self.max_drawdown < eurusd_baseline['dd']:
            print(f"  ✅ Portfolio DD is LOWER than both individual strategies")
        elif self.max_drawdown < xauusd_baseline['dd']:
            print(f"  ✅ Portfolio DD is LOWER than XAUUSD (more aggressive)")
        else:
            print(f"  ⚠️  Portfolio DD is similar or higher")
        
        print(f"\n[=] Stability Improvement:")
        if self.max_drawdown < expected_dd:
            print(f"  ✅ YES - Portfolio provides better risk-adjusted returns")
        else:
            print(f"  ⚠️  NEUTRAL - Portfolio DD within expected range")
        
        print(f"\n[=] Portfolio Approach Verdict:")
        if roi > 0 and self.max_drawdown < xauusd_baseline['dd'] and win_rate > 60:
            print(f"  ✅ PORTFOLIO MAKES SENSE - Better stability than XAUUSD alone")
            print(f"  Recommendation: Continue with portfolio approach for demo")
        elif roi > 0:
            print(f"  ⚠️  PORTFOLIO ACCEPTABLE - Positive returns but review risk metrics")
            print(f"  Recommendation: Consider adjusting allocation weights")
        else:
            print(f"  ⚠️  PORTFOLIO NEEDS REVIEW - Performance below expectations")
            print(f"  Recommendation: Analyze individual strategy timing conflicts")
        
        print()
        print("=" * 80)
        print()
        print("NOTE: This is a COMPATIBILITY TEST, not an optimization.")
        print("Baseline strategies remain FROZEN. No further changes until demo results.")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run portfolio backtest for two frozen baselines')
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    
    args = parser.parse_args()
    
    portfolio = PortfolioBacktest(initial_balance=args.balance)
    portfolio.run(args.start, args.end)

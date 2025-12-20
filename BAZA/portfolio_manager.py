"""Portfolio Manager - Multi-instrument portfolio execution with risk management."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import yaml

from .core import BrokerSim, Executor, DataLoader
from .strategies import StrategyXAUUSD, StrategyEURUSD_SMC_Retracement


class PortfolioManager:
    """
    Manages multiple instruments in a portfolio with unified risk management.
    
    FROZEN LOGIC from portfolio backtests (2023-2025 validated).
    """
    
    def __init__(self, initial_balance: float = 100.0):
        """
        Initialize portfolio manager.
        
        Args:
            initial_balance: Starting capital
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        
        # Load configurations
        self.instruments_config = self._load_config('config/instruments.yaml')
        self.portfolio_config = self._load_config('config/portfolio.yaml')
        
        # Active instruments
        self.active_instruments = self._get_active_instruments()
        
        # Portfolio state
        self.strategies = {}
        self.executors = {}
        self.data = {}
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        
        print(f"[*] Portfolio Manager initialized")
        print(f"    Balance: ${self.balance:,.2f}")
        print(f"    Active instruments: {', '.join(self.active_instruments)}")
    
    def _load_config(self, config_file: str) -> dict:
        """Load YAML configuration."""
        config_path = Path(__file__).parent / config_file
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_active_instruments(self) -> List[str]:
        """Get list of enabled instruments from config."""
        portfolio_instruments = self.portfolio_config['portfolio']['instruments']
        
        active = []
        for instrument in portfolio_instruments:
            if self.instruments_config['instruments'][instrument]['enabled']:
                active.append(instrument)
        
        return active
    
    def load_data(self, start_date: str, end_date: str):
        """
        Load historical data for all active instruments.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        """
        print(f"[*] Loading data for {len(self.active_instruments)} instruments...")
        
        for instrument in self.active_instruments:
            loader = DataLoader(
                instrument=instrument.lower(),
                start_date=start_date,
                end_date=end_date
            )
            h1_data, m15_data = loader.load()
            
            self.data[instrument] = {
                'h1': h1_data,
                'm15': m15_data,
                'h1_idx': 0
            }
            
            print(f"    {instrument}: H1={len(h1_data)}, M15={len(m15_data)}")
        
        print()
    
    def initialize_strategies(self):
        """Initialize strategy instances and executors for all instruments."""
        print(f"[*] Initializing strategies...")
        
        for instrument in self.active_instruments:
            config = self.instruments_config['instruments'][instrument]
            
            # Create strategy instance
            strategy_class_name = config['strategy_class']
            if strategy_class_name == 'StrategyXAUUSD':
                strategy = StrategyXAUUSD()
            elif strategy_class_name == 'StrategyEURUSD_SMC_Retracement':
                strategy = StrategyEURUSD_SMC_Retracement()
            else:
                raise ValueError(f"Unknown strategy class: {strategy_class_name}")
            
            strategy.load_data(self.data[instrument]['h1'], self.data[instrument]['m15'])
            self.strategies[instrument] = strategy
            
            # Create broker simulator
            broker = BrokerSim(
                leverage=self.instruments_config['global_settings']['leverage'],
                spread_points=config['spread_points'],
                spread_multiplier=config['spread_multiplier'],
                commission_per_lot=config['commission_per_lot'],
                contract_size=config['contract_size']
            )
            
            # Create executor
            executor = Executor(broker, contract_size=config['contract_size'])
            self.executors[instrument] = executor
            
            print(f"    {instrument}: {config['strategy_version']} - READY")
        
        print()
    
    def get_current_risk_exposure(self) -> float:
        """Calculate current total risk exposure from open positions."""
        total_exposure = 0.0
        
        for instrument in self.active_instruments:
            if self.executors[instrument].has_position():
                config = self.instruments_config['instruments'][instrument]
                total_exposure += config['risk_per_trade']
        
        return total_exposure
    
    def can_open_position(self, instrument: str) -> bool:
        """
        Check if we can open a new position given current exposure.
        
        Args:
            instrument: Instrument to check
            
        Returns:
            True if position can be opened
        """
        current_exposure = self.get_current_risk_exposure()
        new_risk = self.instruments_config['instruments'][instrument]['risk_per_trade']
        max_exposure = self.portfolio_config['portfolio']['risk_model']['max_total_exposure']
        
        return (current_exposure + new_risk) <= max_exposure
    
    def update_positions(self, instrument: str, current_price: float, current_time):
        """
        Update position for given instrument.
        
        Args:
            instrument: Instrument to update
            current_price: Current price
            current_time: Current timestamp
        """
        executor = self.executors[instrument]
        
        if not executor.has_position():
            return
        
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
                'instrument': instrument,
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
    
    def check_signal(self, instrument: str, m15_idx: int, current_price: float, current_time):
        """
        Check for signal and potentially open position.
        
        Args:
            instrument: Instrument to check
            m15_idx: Current M15 index
            current_price: Current price
            current_time: Current timestamp
        """
        executor = self.executors[instrument]
        strategy = self.strategies[instrument]
        config = self.instruments_config['instruments'][instrument]
        
        # Skip if already has position
        if executor.has_position():
            return
        
        # Check if we can open new position (risk limit)
        if not self.can_open_position(instrument):
            return
        
        # Get signal from strategy (handle different signatures)
        if instrument == 'XAUUSD':
            signal = strategy.generate_signal(m15_idx, current_price)
        elif instrument == 'EURUSD':
            signal = strategy.generate_signal(m15_idx, current_price, current_time)
        else:
            return
        
        if not signal['valid']:
            return
        
        # Calculate lot size using strategy logic
        trade_params = strategy.execute_trade(signal, self.balance, risk_pct=config['risk_per_trade'])
        
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
    
    def run_backtest(self, start_date: str, end_date: str) -> dict:
        """
        Run portfolio backtest.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary with results
        """
        print("=" * 80)
        print(f"PORTFOLIO BACKTEST: {self.portfolio_config['portfolio']['name']}")
        print("=" * 80)
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        
        risk_model = self.portfolio_config['portfolio']['risk_model']
        print(f"Risk Model: Max {risk_model['max_total_exposure']}% total exposure")
        print("=" * 80)
        print()
        
        # Load data
        self.load_data(start_date, end_date)
        
        # Initialize strategies
        self.initialize_strategies()
        
        # Use first instrument as reference timeline
        ref_instrument = self.active_instruments[0]
        m15_ref = self.data[ref_instrument]['m15']
        total_bars = len(m15_ref)
        progress_step = max(1, total_bars // 100)  # 100 updates instead of 20
        
        print(f"[*] Running backtest ({total_bars:,} bars)...")
        print(f"    Progress updates every {progress_step:,} bars (~1%)")
        print()
        
        for m15_idx in range(total_bars):
            current_time = m15_ref.iloc[m15_idx]['time']
            
            # Progress update (every 1%)
            if (m15_idx + 1) % progress_step == 0:
                progress = ((m15_idx + 1) / total_bars) * 100
                elapsed = current_time.strftime('%Y-%m-%d')
                print(f"[>] {progress:3.0f}% | {elapsed} | Trades: {len(self.trades):3d} | Balance: ${self.balance:,.2f}")
            
            # Calculate total equity (balance + floating P&L)
            total_floating_pnl = 0.0
            
            # Process each instrument
            for instrument in self.active_instruments:
                # Find corresponding M15 bar
                m15_data = self.data[instrument]['m15']
                
                # Simple time alignment
                time_diff = abs(m15_data['time'] - current_time)
                closest_idx = time_diff.idxmin()
                
                if time_diff.iloc[closest_idx].total_seconds() > 900:
                    continue
                
                current_price = m15_data.iloc[closest_idx]['close']
                
                # Update H1 index
                h1_data = self.data[instrument]['h1']
                h1_idx = self.data[instrument]['h1_idx']
                
                while h1_idx < len(h1_data) - 1 and h1_data.iloc[h1_idx + 1]['time'] <= current_time:
                    h1_idx += 1
                
                self.data[instrument]['h1_idx'] = h1_idx
                
                if h1_idx < 2:
                    continue
                
                # Update H1 context for strategy
                self.strategies[instrument].build_context(h1_idx)
                
                # Update existing positions
                self.update_positions(instrument, current_price, current_time)
                
                # Check for new signals
                if closest_idx >= 20:
                    self.check_signal(instrument, closest_idx, current_price, current_time)
                
                # Add floating P&L
                if self.executors[instrument].has_position():
                    total_floating_pnl += self.executors[instrument].get_floating_pnl(current_price)
            
            # Update equity
            self.equity = self.balance + total_floating_pnl
            
            # Record equity curve
            if len(self.equity_curve) == 0 or self.equity_curve[-1]['time'] != current_time:
                self.equity_curve.append({
                    'time': current_time,
                    'balance': self.balance,
                    'equity': self.equity
                })
        
        # Close remaining positions
        for instrument in self.active_instruments:
            if self.executors[instrument].has_position():
                m15_data = self.data[instrument]['m15']
                final_price = m15_data.iloc[-1]['close']
                final_time = m15_data.iloc[-1]['time']
                result = self.executors[instrument].update_position(final_price, final_time)
                if result['closed']:
                    self.balance += result['pnl']
        
        # Generate report
        return self._generate_report(start_date, end_date)
    
    def _generate_report(self, start_date: str, end_date: str) -> dict:
        """Generate portfolio backtest report."""
        print()
        print("=" * 80)
        print("PORTFOLIO RESULTS")
        print("=" * 80)
        
        if len(self.trades) == 0:
            print("⚠️  No trades executed")
            return {}
        
        df_trades = pd.DataFrame(self.trades)
        
        # Overall stats
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df_trades['pnl'].sum()
        final_balance = self.balance
        roi = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        # Per-instrument breakdown
        print(f"\n[=] Portfolio Performance:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  ROI: {roi:,.2f}%")
        print(f"  Max DD: {self.max_drawdown:.2f}%")
        print(f"  Final Balance: ${final_balance:,.2f}")
        
        print(f"\n[=] Per-Instrument:")
        for instrument in self.active_instruments:
            inst_trades = df_trades[df_trades['instrument'] == instrument]
            inst_pnl = inst_trades['pnl'].sum() if len(inst_trades) > 0 else 0
            print(f"  {instrument}: {len(inst_trades)} trades | P&L: ${inst_pnl:+,.2f}")
        
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
        
        print(f"[OK] Results saved to results/portfolio/{year}/")
        print()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'max_dd': self.max_drawdown,
            'roi': roi,
            'final_balance': final_balance
        }

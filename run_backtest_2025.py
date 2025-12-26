#!/usr/bin/env python3
"""
Backtest Runner for 2025 - Final Strategies

Runs backtests for XAUUSD, EURUSD, and Portfolio with realistic conditions.
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from strategies.xauusd_strategy import StrategyXAUUSD
from strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement
from core.data_loader import DataLoader
from core.broker_sim import BrokerSim
from core.executor import Executor


class BacktestRunner:
    """Backtest runner for individual instruments and portfolio."""

    def __init__(self, initial_balance: float = 100.0):
        self.initial_balance = initial_balance

    def run_single_instrument(self, instrument: str, start_date: str, end_date: str,
                            risk_pct: float, slippage_min: float, slippage_max: float,
                            spread: float, commission: float) -> dict:
        """Run backtest for single instrument."""

        print(f"[*] Running {instrument.upper()} backtest: {start_date} to {end_date}")
        print(f"[*] Risk: {risk_pct}%, Slippage: {slippage_min}-{slippage_max}, Spread: {spread}, Commission: {commission}")

        # Configure instrument
        if instrument.lower() == 'xauusd':
            strategy_class = StrategyXAUUSD
            contract_size = 100
            spread_points = spread / 0.01  # Convert to points
            spread_multiplier = 0.01
            price_decimals = 2
        elif instrument.lower() == 'eurusd':
            strategy_class = StrategyEURUSD_SMC_Retracement
            contract_size = 100000
            spread_points = spread / 0.0001  # Convert to points
            spread_multiplier = 0.0001
            price_decimals = 5
        else:
            raise ValueError(f"Unknown instrument: {instrument}")

        # Load data
        loader = DataLoader(instrument=instrument.lower(), start_date=start_date, end_date=end_date)
        h1_data, m15_data = loader.load()

        if h1_data.empty or m15_data.empty:
            return {'error': 'No data available'}

        # Initialize strategy
        strategy = strategy_class()
        strategy.load_data(h1_data, m15_data)

        # Initialize broker with slippage
        broker = BrokerSim(
            leverage=100,
            spread_points=spread_points,
            spread_multiplier=spread_multiplier,
            commission_per_lot=commission,
            contract_size=contract_size,
            slippage_min=slippage_min,
            slippage_max=slippage_max
        )

        # Initialize executor
        executor = Executor(broker, contract_size=contract_size)

        # Backtest variables
        balance = self.initial_balance
        equity = self.initial_balance
        peak_balance = self.initial_balance
        max_drawdown = 0.0
        trades = []
        equity_curve = []

        # H1 index tracking
        h1_idx = 0

        # Run backtest
        print(f"Starting backtest with {len(m15_data)} M15 bars...")
        for i in range(len(m15_data)):
            if i % 1000 == 0:
                print(f"Processed {i}/{len(m15_data)} bars...")
            current_bar = m15_data.iloc[i]
            current_price = current_bar['close']
            current_time = current_bar['time']

            # Update H1 index
            while h1_idx < len(h1_data) - 1 and h1_data.iloc[h1_idx + 1]['time'] <= current_time:
                h1_idx += 1

            # Update positions
            if executor.has_position():
                floating_pnl = executor.get_floating_pnl(current_price)
                equity = balance + floating_pnl

                result = executor.update_position(current_price, current_time)
                if result['closed']:
                    balance += result['pnl']
                    equity = balance

                    # Track drawdown
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
                        'entry_price': round(pos.entry_price, price_decimals),
                        'exit_price': round(pos.exit_price, price_decimals),
                        'sl': round(pos.sl, price_decimals),
                        'tp': round(pos.tp, price_decimals),
                        'lot_size': pos.lot_size,
                        'pnl': round(pos.pnl, 2),
                        'exit_reason': pos.exit_reason,
                        'balance': round(balance, 2)
                    })

            # Check for signals
            if not executor.has_position():
                # Need next bar for entry
                if i >= len(m15_data) - 1:
                    continue

                analysis_price = current_bar['close']
                entry_price = m15_data.iloc[i + 1]['open']
                entry_time = m15_data.iloc[i + 1]['time']

                # Get signal
                if instrument.lower() == 'xauusd':
                    signal = strategy.generate_signal(i, analysis_price, entry_price, h1_idx)
                else:
                    signal = strategy.generate_signal(i, analysis_price, entry_price, entry_time, h1_idx)

                if signal.get('valid', False):
                    # Calculate lot size
                    trade_params = strategy.execute_trade(signal, balance, risk_pct=risk_pct)
                    if trade_params:
                        lot_size = trade_params['lot_size']

                        # Open position
                        opened = executor.open_position(
                            signal=signal,
                            lot_size=lot_size,
                            current_price=entry_price,
                            current_time=entry_time,
                            balance=balance,
                            equity=equity,
                            used_margin=executor.get_used_margin(entry_price)
                        )

                        if opened:
                            # Deduct commission from balance
                            commission_cost = broker.calculate_commission(lot_size)
                            balance -= commission_cost

            # Record equity
            equity_curve.append({
                'time': current_time,
                'balance': round(balance, 2),
                'equity': round(equity, 2)
            })

        # Calculate metrics
        if trades:
            df_trades = pd.DataFrame(trades)
            total_trades = len(df_trades)
            winning_trades = (df_trades['pnl'] > 0).sum()
            win_rate = (winning_trades / total_trades) * 100

            total_pnl = df_trades['pnl'].sum()
            roi = (total_pnl / self.initial_balance) * 100

            gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            # Sharpe ratio (simplified, assuming daily returns)
            if len(equity_curve) > 1:
                returns = pd.DataFrame(equity_curve)['equity'].pct_change().dropna()
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0

            # Average RR achieved
            contract_size = 100 if instrument.lower() == 'xauusd' else 100000
            df_trades['risk_dollar'] = abs(df_trades['entry_price'] - df_trades['sl']) * contract_size * df_trades['lot_size']
            df_trades['rr_achieved'] = np.where(df_trades['risk_dollar'] > 0,
                                                np.where(df_trades['pnl'] > 0,
                                                         df_trades['pnl'] / df_trades['risk_dollar'],
                                                         -df_trades['pnl'] / df_trades['risk_dollar']),
                                                0)
            avg_rr = df_trades['rr_achieved'].mean()

            # Max consecutive losses
            consecutive_losses = 0
            max_consecutive_losses = 0
            for pnl in df_trades['pnl']:
                if pnl < 0:
                    consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                else:
                    consecutive_losses = 0
        else:
            total_trades = 0
            win_rate = 0
            roi = 0
            profit_factor = 0
            sharpe_ratio = 0
            avg_rr = 0
            max_consecutive_losses = 0

        # Monthly breakdown
        monthly_data = {}
        if trades:
            df_trades['month'] = pd.to_datetime(df_trades['entry_time']).dt.strftime('%Y-%m')
            monthly = df_trades.groupby('month').agg({
                'pnl': 'sum',
                'balance': 'last',
                'entry_time': 'count'
            }).rename(columns={'entry_time': 'trades'})
            monthly = monthly.sort_index()

            running_balance = self.initial_balance
            for month, row in monthly.iterrows():
                monthly_data[month] = {
                    'trades': int(row['trades']),
                    'pnl': round(row['pnl'], 2),
                    'balance': round(running_balance + row['pnl'], 2)
                }
                running_balance += row['pnl']

        return {
            'instrument': instrument.upper(),
            'period': f"{start_date} — {end_date}",
            'initial_balance': self.initial_balance,
            'final_balance': round(balance, 2),
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'roi': round(roi, 2),
            'max_drawdown': round(max_drawdown, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
            'sharpe_ratio': round(sharpe_ratio, 2),
            'avg_rr_achieved': round(avg_rr, 2),
            'max_consecutive_losses': max_consecutive_losses,
            'monthly_data': monthly_data,
            'trades': trades
        }

    def run_portfolio(self, start_date: str, end_date: str,
                     xauusd_risk: float, eurusd_risk: float, max_exposure: float) -> dict:
        """Run portfolio backtest."""

        print(f"[*] Running PORTFOLIO backtest: {start_date} to {end_date}")
        print(f"[*] XAUUSD risk: {xauusd_risk}%, EURUSD risk: {eurusd_risk}%, Max exposure: {max_exposure}%")

        # Load data for both instruments
        instruments_config = {
            'xauusd': {
                'strategy_class': StrategyXAUUSD,
                'contract_size': 100,
                'spread': 0.25,
                'commission': 7.0,
                'slippage_min': 0.15,
                'slippage_max': 0.40,
                'risk_pct': xauusd_risk,
                'price_decimals': 2
            },
            'eurusd': {
                'strategy_class': StrategyEURUSD_SMC_Retracement,
                'contract_size': 100000,
                'spread': 0.00015,
                'commission': 0.0,
                'slippage_min': 0.00015,
                'slippage_max': 0.00030,
                'risk_pct': eurusd_risk,
                'price_decimals': 5
            }
        }

        data = {}
        strategies = {}
        brokers = {}
        executors = {}
        h1_indices = {}

        for instr, config in instruments_config.items():
            # Load data
            loader = DataLoader(instrument=instr, start_date=start_date, end_date=end_date)
            h1_data, m15_data = loader.load()
            data[instr] = {'h1': h1_data, 'm15': m15_data}
            h1_indices[instr] = 0

            # Initialize strategy
            strategy = config['strategy_class']()
            strategy.load_data(h1_data, m15_data)
            strategies[instr] = strategy

            # Initialize broker
            spread_points = config['spread'] / (0.01 if instr == 'xauusd' else 0.0001)
            spread_multiplier = 0.01 if instr == 'xauusd' else 0.0001
            broker = BrokerSim(
                leverage=100,
                spread_points=spread_points,
                spread_multiplier=spread_multiplier,
                commission_per_lot=config['commission'],
                contract_size=config['contract_size'],
                slippage_min=config['slippage_min'],
                slippage_max=config['slippage_max']
            )
            brokers[instr] = broker

            # Initialize executor
            executor = Executor(broker, contract_size=config['contract_size'])
            executors[instr] = executor

        # Portfolio variables
        balance = self.initial_balance
        equity = self.initial_balance
        peak_balance = self.initial_balance
        max_drawdown = 0.0
        all_trades = []
        equity_curve = []

        # Get max length
        max_len = max(len(data['xauusd']['m15']), len(data['eurusd']['m15']))

        # Run portfolio backtest
        print(f"Starting portfolio backtest with {max_len} bars...")
        for i in range(max_len):
            if i % 1000 == 0:
                print(f"Processed {i}/{max_len} bars...")
            current_time = None
            total_floating_pnl = 0.0

            # Update positions for both instruments
            for instr in ['xauusd', 'eurusd']:
                if i < len(data[instr]['m15']):
                    current_bar = data[instr]['m15'].iloc[i]
                    current_price = current_bar['close']
                    current_time = current_bar['time']

                    # Update H1 index
                    while h1_indices[instr] < len(data[instr]['h1']) - 1 and data[instr]['h1'].iloc[h1_indices[instr] + 1]['time'] <= current_time:
                        h1_indices[instr] += 1

                    executor = executors[instr]
                    if executor.has_position():
                        floating_pnl = executor.get_floating_pnl(current_price)
                        total_floating_pnl += floating_pnl

                        result = executor.update_position(current_price, current_time)
                        if result['closed']:
                            balance += result['pnl']

                            # Record trade
                            pos = executor.last_closed_position
                            all_trades.append({
                                'instrument': instr.upper(),
                                'entry_time': pos.entry_time,
                                'exit_time': pos.exit_time,
                                'direction': pos.direction,
                                'entry_price': round(pos.entry_price, instruments_config[instr]['price_decimals']),
                                'exit_price': round(pos.exit_price, instruments_config[instr]['price_decimals']),
                                'lot_size': pos.lot_size,
                                'pnl': round(pos.pnl, 2),
                                'exit_reason': pos.exit_reason
                            })

            # Update equity and drawdown
            equity = balance + total_floating_pnl
            if equity > peak_balance:
                peak_balance = equity
            dd = ((peak_balance - equity) / peak_balance) * 100
            if dd > max_drawdown:
                max_drawdown = dd

            # Check for signals
            current_exposure = 0.0
            for instr in ['xauusd', 'eurusd']:
                if executors[instr].has_position():
                    current_exposure += instruments_config[instr]['risk_pct']

            for instr in ['xauusd', 'eurusd']:
                if i < len(data[instr]['m15']) - 1 and not executors[instr].has_position():
                    if current_exposure + instruments_config[instr]['risk_pct'] > max_exposure:
                        continue

                    current_bar = data[instr]['m15'].iloc[i]
                    analysis_price = current_bar['close']
                    entry_price = data[instr]['m15'].iloc[i + 1]['open']
                    entry_time = data[instr]['m15'].iloc[i + 1]['time']

                    # Get signal
                    h1_idx = h1_indices[instr]
                    if instr == 'xauusd':
                        signal = strategies[instr].generate_signal(i, analysis_price, entry_price, h1_idx)
                    else:
                        signal = strategies[instr].generate_signal(i, analysis_price, entry_price, entry_time, h1_idx)

                    if signal.get('valid', False):
                        # Calculate lot size
                        trade_params = strategies[instr].execute_trade(signal, balance, risk_pct=instruments_config[instr]['risk_pct'])
                        if trade_params:
                            lot_size = trade_params['lot_size']

                            # Open position
                            opened = executors[instr].open_position(
                                signal=signal,
                                lot_size=lot_size,
                                current_price=entry_price,
                                current_time=entry_time,
                                balance=balance,
                                equity=equity,
                                used_margin=executors[instr].get_used_margin(entry_price)
                            )

                            if opened:
                                # Deduct commission
                                commission_cost = brokers[instr].calculate_commission(lot_size)
                                balance -= commission_cost
                                current_exposure += instruments_config[instr]['risk_pct']

            # Record equity
            if current_time:
                equity_curve.append({
                    'time': current_time,
                    'balance': round(balance, 2),
                    'equity': round(equity, 2)
                })

        # Calculate portfolio metrics
        df_trades = pd.DataFrame(all_trades)
        if not df_trades.empty:
            total_trades = len(df_trades)
            winning_trades = (df_trades['pnl'] > 0).sum()
            win_rate = (winning_trades / total_trades) * 100

            total_pnl = df_trades['pnl'].sum()
            roi = (total_pnl / self.initial_balance) * 100

            gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            # Sharpe ratio
            if len(equity_curve) > 1:
                returns = pd.DataFrame(equity_curve)['equity'].pct_change().dropna()
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0

            # By instrument
            by_instrument = df_trades.groupby('instrument').agg({
                'pnl': ['count', 'sum', lambda x: (x > 0).sum()],
                'lot_size': 'sum'
            })
            by_instrument.columns = ['trades', 'total_pnl', 'wins', 'total_lots']
            by_instrument['win_rate'] = (by_instrument['wins'] / by_instrument['trades']) * 100
            by_instrument['contribution'] = (by_instrument['total_pnl'] / total_pnl) * 100 if total_pnl != 0 else 0

            # Monthly breakdown
            monthly_data = {}
            df_trades['month'] = pd.to_datetime(df_trades['entry_time']).dt.strftime('%Y-%m')
            monthly = df_trades.groupby('month').agg({
                'pnl': 'sum',
                'instrument': 'count'
            }).rename(columns={'instrument': 'trades'})
            monthly = monthly.sort_index()

            running_balance = self.initial_balance
            for month, row in monthly.iterrows():
                monthly_data[month] = {
                    'trades': int(row['trades']),
                    'pnl': round(row['pnl'], 2),
                    'balance': round(running_balance + row['pnl'], 2)
                }
                running_balance += row['pnl']
        else:
            total_trades = 0
            win_rate = 0
            roi = 0
            profit_factor = 0
            sharpe_ratio = 0
            by_instrument = pd.DataFrame()
            monthly_data = {}

        return {
            'period': f"{start_date} — {end_date}",
            'initial_balance': self.initial_balance,
            'final_balance': round(balance, 2),
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'roi': round(roi, 2),
            'max_drawdown': round(max_drawdown, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
            'sharpe_ratio': round(sharpe_ratio, 2),
            'by_instrument': by_instrument.to_dict('index') if not by_instrument.empty else {},
            'monthly_data': monthly_data,
            'trades': all_trades
        }


def print_single_results(results):
    """Print results for single instrument."""
    print(f"\n{results['instrument']} BACKTEST {results['period'].split(' — ')[0].split('-')[0]}")
    print(f"Период: {results['period']}")
    print(f"Начальный баланс: ${results['initial_balance']:.2f}")
    print(f"Финальный баланс: ${results['final_balance']:.2f}")
    print("Метрика\tЗначение")
    print(f"Всего сделок\t{results['total_trades']}")
    print(f"Win Rate\t{results['win_rate']}%")
    print(f"ROI\t{results['roi']}%")
    print(f"Max Drawdown\t{results['max_drawdown']}%")
    print(f"Profit Factor\t{results['profit_factor']}")
    print(f"Sharpe Ratio\t{results['sharpe_ratio']}")
    print(f"Avg RR Achieved\t{results['avg_rr_achieved']}")
    print(f"Max Consecutive Loss\t{results['max_consecutive_losses']}")

    print("\nПомесячная разбивка:")
    print("Месяц\tTrades\tP&L\tБаланс")
    for month, data in results['monthly_data'].items():
        month_name = datetime.strptime(month, '%Y-%m').strftime('%b')
        print(f"{month_name}\t{data['trades']}\t${data['pnl']:+.2f}\t${data['balance']:.2f}")

    # Первые 10 сделок
    if results['trades']:
        print("\nПервые 10 сделок:")
        print("#\tEntry\tSL\tTP\tLot Size\tRisk $\tExit\tP&L")
        contract_size = 100 if results['instrument'] == 'XAUUSD' else 100000
        for idx, trade in enumerate(results['trades'][:10]):
            risk_dollar = abs(trade['entry_price'] - trade['sl']) * contract_size * trade['lot_size']
            print(f"{idx+1}\t{trade['entry_price']}\t{trade['sl']}\t{trade['tp']}\t{trade['lot_size']}\t{risk_dollar:.2f}\t{trade['exit_price']}\t{trade['pnl']}")

    print("============================================================\n")


def print_portfolio_results(results):
    """Print results for portfolio."""
    print(f"\nPORTFOLIO BACKTEST {results['period'].split(' — ')[0].split('-')[0]} (XAUUSD + EURUSD)")
    print(f"Период: {results['period']}")
    print(f"Начальный баланс: ${results['initial_balance']:.2f}")
    print(f"Финальный баланс: ${results['final_balance']:.2f}")

    print("\nОБЩИЕ МЕТРИКИ:")
    print("Метрика\tЗначение")
    print(f"Всего сделок\t{results['total_trades']}")
    print(f"Win Rate\t{results['win_rate']}%")
    print(f"ROI\t{results['roi']}%")
    print(f"Max Drawdown\t{results['max_drawdown']}%")
    print(f"Profit Factor\t{results['profit_factor']}")
    print(f"Sharpe Ratio\t{results['sharpe_ratio']}")

    print("\nПО ИНСТРУМЕНТАМ:")
    print("Инструмент\tTrades\tWin%\tP&L\tContribution")
    total_trades = 0
    for instr, data in results['by_instrument'].items():
        print(f"{instr}\t{data['trades']}\t{data['win_rate']:.1f}%\t${data['total_pnl']:+.2f}\t{data['contribution']:+.1f}%")
        total_trades += data['trades']
    print(f"TOTAL\t{total_trades}\t\t\t100%")

    print("\nПОМЕСЯЧНАЯ РАЗБИВКА ПОРТФЕЛЯ:")
    print("Месяц\tXAUUSD P&L\tEURUSD P&L\tTotal P&L\tБаланс")
    for month, data in results['monthly_data'].items():
        month_name = datetime.strptime(month, '%Y-%m').strftime('%b')
        # Calculate P&L by instrument
        xau_pnl = sum(trade['pnl'] for trade in results['trades'] 
                     if pd.to_datetime(trade['entry_time']).strftime('%Y-%m') == month and trade['instrument'] == 'XAUUSD')
        eur_pnl = sum(trade['pnl'] for trade in results['trades'] 
                     if pd.to_datetime(trade['entry_time']).strftime('%Y-%m') == month and trade['instrument'] == 'EURUSD')
        print(f"{month_name}\t${xau_pnl:+.2f}\t${eur_pnl:+.2f}\t${data['pnl']:+.2f}\t${data['balance']:.2f}")
    print("============================================================\n")


def main():
    parser = argparse.ArgumentParser(description='BAZA 2025 Backtest Runner')
    parser.add_argument('--task', type=str, required=True,
                        choices=['xauusd', 'eurusd', 'portfolio', 'all'],
                        help='Task to run')
    args = parser.parse_args()

    runner = BacktestRunner(initial_balance=100.0)

    if args.task in ['xauusd', 'all']:
        # ЗАДАЧА 1: XAUUSD
        results_xau = runner.run_single_instrument(
            instrument='xauusd',
            start_date='2025-01-01',
            end_date='2025-12-26',
            risk_pct=0.75,
            slippage_min=0.15,
            slippage_max=0.40,
            spread=0.25,
            commission=7.0
        )
        print_single_results(results_xau)

    if args.task in ['eurusd', 'all']:
        # ЗАДАЧА 2: EURUSD
        results_eur = runner.run_single_instrument(
            instrument='eurusd',
            start_date='2025-01-01',
            end_date='2025-12-26',
            risk_pct=0.5,
            slippage_min=0.00015,
            slippage_max=0.00030,
            spread=0.00015,
            commission=0.0
        )
        print_single_results(results_eur)

    if args.task in ['portfolio', 'all']:
        # ЗАДАЧА 3: PORTFOLIO
        results_port = runner.run_portfolio(
            start_date='2025-01-01',
            end_date='2025-12-26',
            xauusd_risk=0.75,
            eurusd_risk=0.5,
            max_exposure=1.25
        )
        print_portfolio_results(results_port)

    # ЗАДАЧА 4: Сравнение с 2024
    if args.task == 'all':
        print("СРАВНЕНИЕ 2024 vs 2025")
        print("XAUUSD:")
        print("Метрика20242025Разница")
        print("ROI45.86%???")
        print("Max DD16.27%???")
        print("Win Rate~45%???")
        print("Trades315???")
        print("EURUSD:")
        print("Метрика20242025Разница")
        print("ROI340.75%???")
        print("Max DD5.32%???")
        print("Win Rate71.96%???")
        print("Trades189???")
        print("PORTFOLIO:")
        print("Метрика20242025Разница")
        print("ROI???")
        print("Max DD???")
        print("ВЫВОД:")
        print("Стратегия стабильна/нестабильна между годами")
        print("Рекомендация: готово к демо / нужна доработка")
        print("============================================================")


if __name__ == '__main__':
    main()
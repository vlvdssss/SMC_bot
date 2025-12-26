#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    BAZA TRADING BOT v1.0                     ║
║                                                              ║
║  Автоматическая торговля на основе Smart Money Concepts      ║
║                                                              ║
║  Результаты бэктеста 2024:                                   ║
║  • XAUUSD: +45.86% ROI, 16% Max DD                          ║
║  • EURUSD: +340.75% ROI, 5.32% Max DD                       ║
║                                                              ║
║  Запуск:                                                     ║
║    python main.py --mode demo                                ║
║    python main.py --mode live                                ║
║    python main.py --mode backtest --year 2024                ║
╚══════════════════════════════════════════════════════════════╝
"""

import argparse
import sys
import os
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from strategies.xauusd_strategy import StrategyXAUUSD
from strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement
from mt5.connector import MT5Connector
from live.live_trader import LiveTrader
from backtest.backtester import RealisticBacktester
from core.broker_sim import BrokerSim
from core.data_loader import DataLoader


def main():
    parser = argparse.ArgumentParser(
        description='BAZA Trading Bot - SMC автоматическая торговля',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--mode', type=str, required=True,
                        choices=['demo', 'live', 'backtest'],
                        help='Режим работы: demo, live, backtest')
    
    parser.add_argument('--year', type=int, default=2024,
                        help='Год для бэктеста (по умолчанию 2024)')
    
    parser.add_argument('--instrument', type=str, default='all',
                        choices=['all', 'xauusd', 'eurusd'],
                        help='Инструмент (по умолчанию all)')
    
    parser.add_argument('--interval', type=int, default=60,
                        help='Интервал проверки в секундах (по умолчанию 60)')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.mode == 'demo':
        run_demo(args)
    elif args.mode == 'live':
        run_live(args)
    elif args.mode == 'backtest':
        run_backtest(args)


def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    BAZA TRADING BOT v1.0                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def run_demo(args):
    """Запуск в демо режиме (мониторинг без торговли)"""
    print("[*] Режим: DEMO (мониторинг без торговли)")
    print(f"[*] Интервал проверки: {args.interval} сек")
    print("-" * 60)
    
    trader = LiveTrader(config_dir='config', enable_trading=False)
    trader.run()


def run_live(args):
    """Запуск реальной торговли"""
    print("[!] ВНИМАНИЕ: Режим LIVE торговли!")
    print("[!] Будут открываться реальные сделки!")
    
    confirm = input("\nВведите 'CONFIRM' для подтверждения: ")
    if confirm != 'CONFIRM':
        print("Отменено.")
        return
    
    trader = LiveTrader(config_dir='config', enable_trading=True)
    trader.run()


def run_backtest(args):
    """Запуск бэктеста"""
    print(f"[*] Режим: BACKTEST")
    print(f"[*] Год: {args.year}")
    print(f"[*] Инструмент: {args.instrument}")
    print("-" * 60)
    
    # Create strategies
    strategies = {
        'XAUUSD': StrategyXAUUSD(),
        'EURUSD': StrategyEURUSD_SMC_Retracement()
    }
    
    # Create broker and data loader
    broker = BrokerSim()
    data_loader = DataLoader()
    
    backtester = RealisticBacktester(strategies, broker, data_loader)()
    
    if args.instrument in ['all', 'xauusd']:
        print("\n[XAUUSD]")
        backtester.run_backtest('XAUUSD', datetime(args.year, 1, 1), datetime(args.year, 12, 31))
    
    if args.instrument in ['all', 'eurusd']:
        print("\n[EURUSD]")
        backtester.run_backtest('EURUSD', datetime(args.year, 1, 1), datetime(args.year, 12, 31))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Остановлено пользователем (Ctrl+C)")
        sys.exit(0)

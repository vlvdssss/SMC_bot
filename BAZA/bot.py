"""
BAZA - Production Trading Bot

Main entry point for the trading bot. Supports:
- Backtest mode (historical data)
- Demo mode (MT5 demo account) - TODO
- Live mode (MT5 live account) - TODO

Usage:
    # Backtest portfolio
    python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31
    
    # Backtest single instrument
    python BAZA/bot.py --mode backtest --instrument xauusd --start 2024-01-01 --end 2024-12-31
    
    # Demo trading (future)
    python BAZA/bot.py --mode demo --mt5-config config/mt5_demo.ini
    
    # Live trading (future)
    python BAZA/bot.py --mode live --mt5-config config/mt5_live.ini
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from BAZA.portfolio_manager import PortfolioManager
from BAZA.core import DataLoader
from BAZA.strategies import StrategyXAUUSD, StrategyEURUSD_SMC_Retracement


def run_single_backtest(instrument: str, start_date: str, end_date: str, initial_balance: float = 100.0):
    """
    Run backtest for single instrument.
    
    This is a simplified wrapper around the original run_backtest.py logic.
    For full single-instrument backtesting, use run_backtest.py from root.
    
    Args:
        instrument: Instrument to backtest (xauusd, eurusd)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_balance: Initial balance
    """
    print("=" * 80)
    print(f"SINGLE INSTRUMENT BACKTEST: {instrument.upper()}")
    print("=" * 80)
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print()
    print("⚠️  For full single-instrument backtesting, use:")
    print(f"    python run_backtest.py --instrument {instrument} --start {start_date} --end {end_date}")
    print()
    print("=" * 80)
    

def run_portfolio_backtest(start_date: str, end_date: str, initial_balance: float = 100.0):
    """
    Run portfolio backtest with multiple instruments.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_balance: Initial balance
    """
    portfolio = PortfolioManager(initial_balance=initial_balance)
    results = portfolio.run_backtest(start_date, end_date)
    
    return results


def run_demo_trading(mt5_config: str = None, check_interval: int = 60):
    """
    Run bot in demo trading mode.
    
    Args:
        mt5_config: Path to MT5 config file (optional)
        check_interval: LOG interval in seconds (market checked every 1 sec)
    """
    from BAZA.live_trader import LiveTrader
    
    print("=" * 80)
    print("DEMO TRADING MODE")
    print("=" * 80)
    print()
    
    # Создаём live трейдер
    config_dir = 'BAZA/config'
    trader = LiveTrader(config_dir=config_dir)
    
    # Подключаемся к MT5
    if not trader.connect_mt5():
        print("[!] Failed to connect to MT5")
        return
    
    # Инициализируем стратегии
    trader.initialize_strategies()
    
    # Запускаем мониторинг (рынок проверяется каждую секунду, логи каждые N сек)
    trader.run_monitoring(log_interval=check_interval)


def run_live_trading(mt5_config: str):
    """
    Run bot in live trading mode.
    
    TODO: Implement MT5 integration with safety checks
    
    Args:
        mt5_config: Path to MT5 config file
    """
    print("=" * 80)
    print("LIVE TRADING MODE")
    print("=" * 80)
    print()
    print("⚠️  Live trading not yet implemented")
    print("    Required: MT5 integration + demo validation")
    print()
    print("=" * 80)


def validate_date_format(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='BAZA Trading Bot - Multi-instrument portfolio trading system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Portfolio backtest (2024)
  python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31
  
  # Portfolio backtest (3 years)
  python BAZA/bot.py --mode backtest --portfolio --start 2023-01-01 --end 2025-12-17
  
  # Single instrument backtest
  python BAZA/bot.py --mode backtest --instrument xauusd --start 2024-01-01 --end 2024-12-31
  
  # Demo trading (future)
  python BAZA/bot.py --mode demo --mt5-config config/mt5_demo.ini
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['backtest', 'demo', 'live'],
        help='Trading mode: backtest, demo, or live'
    )
    
    # Backtest parameters
    parser.add_argument(
        '--portfolio',
        action='store_true',
        help='Run portfolio backtest (multiple instruments)'
    )
    
    parser.add_argument(
        '--instrument',
        type=str,
        choices=['xauusd', 'eurusd'],
        help='Single instrument to backtest (if not portfolio)'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='Start date for backtest (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date for backtest (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--balance',
        type=float,
        default=100.0,
        help='Initial balance (default: 100)'
    )
    
    # MT5 parameters
    parser.add_argument(
        '--mt5-config',
        type=str,
        help='Path to MT5 configuration file'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='LOG interval in seconds for demo/live mode (market checked every 1s, default: 60s logs)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.mode == 'backtest':
        if not args.portfolio and not args.instrument:
            parser.error("Backtest mode requires --portfolio or --instrument")
        
        if not args.start or not args.end:
            parser.error("Backtest mode requires --start and --end dates")
        
        if not validate_date_format(args.start) or not validate_date_format(args.end):
            parser.error("Dates must be in YYYY-MM-DD format")
        
        # Run backtest
        if args.portfolio:
            run_portfolio_backtest(args.start, args.end, args.balance)
        else:
            run_single_backtest(args.instrument, args.start, args.end, args.balance)
    
    elif args.mode == 'demo':
        # Demo mode работает с конфигом из BAZA/config/mt5.yaml
        run_demo_trading(check_interval=args.interval)
    
    elif args.mode == 'live':
        if not args.mt5_config:
            parser.error("Live mode requires --mt5-config")
        
        # Safety confirmation
        print("⚠️  WARNING: You are about to start LIVE TRADING")
        print("    This will use real money!")
        print()
        confirmation = input("Type 'CONFIRM LIVE TRADING' to proceed: ")
        
        if confirmation == "CONFIRM LIVE TRADING":
            run_live_trading(args.mt5_config)
        else:
            print("Live trading cancelled.")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Bot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERROR] Bot crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

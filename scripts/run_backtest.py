"""
Quick Portfolio Backtest Runner

Запуск бэктеста портфолио для проверки стратегий.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.portfolio_backtester import PortfolioBacktester

def main():
    print("\n" + "="*60)
    print("🚀 PORTFOLIO BACKTEST")
    print("="*60 + "\n")
    
    # Параметры
    initial_balance = 100  # $100 starting balance
    start_date = '2024-01-01'
    end_date = '2025-01-01'
    
    print(f"💰 Initial Balance: ${initial_balance}")
    print(f"📅 Period: {start_date} → {end_date}")
    print(f"📊 Instruments: XAUUSD + EURUSD")
    print(f"⚙️ Max Exposure: 20%\n")
    
    # Создаем портфолио бэктестер
    backtester = PortfolioBacktester(
        initial_balance=initial_balance,
        max_exposure=0.20  # 20% max exposure
    )
    
    print("⏳ Running backtest...\n")
    
    # Запускаем бэктест
    try:
        results = backtester.run_backtest(start_date=start_date, end_date=end_date)
        
        print("\n" + "="*60)
        print("📊 RESULTS")
        print("="*60 + "\n")
        
        print(f"Initial Balance:   ${results['initial_balance']:.2f}")
        print(f"Final Balance:     ${results['final_balance']:.2f}")
        print(f"Total Profit:      ${results['total_profit']:.2f}")
        print(f"ROI:               {results['roi']:.2f}%")
        print(f"Total Trades:      {results['trades']}")
        print(f"Win Rate:          {results['win_rate']:.2f}%")
        print(f"Max Drawdown:      {results['max_dd']:.2f}%")
        print(f"Max DD Amount:     ${results['max_dd_amount']:.2f}")
        
        print("\n" + "="*60)
        print("✅ Backtest completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

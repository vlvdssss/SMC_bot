"""Простая проверка MT5 истории напрямую"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta

print("Подключение к MT5...")
if not mt5.initialize():
    print(f"❌ Ошибка initialize(): {mt5.last_error()}")
    quit()

print("✅ MT5 подключен")

# Account info
account_info = mt5.account_info()
if account_info:
    print(f"Логин: {account_info.login}")
    print(f"Баланс: ${account_info.balance:.2f}")
    print(f"Equity: ${account_info.equity:.2f}")

# Get history for last 7 days
from_date = datetime.now() - timedelta(days=7)
to_date = datetime.now()

print(f"\nПолучение истории с {from_date.strftime('%Y-%m-%d')} по {to_date.strftime('%Y-%m-%d')}...")

deals = mt5.history_deals_get(from_date, to_date)

if deals is None:
    print(f"❌ Нет сделок. Ошибка: {mt5.last_error()}")
else:
    print(f"✅ Найдено {len(deals)} deals")
    
    # Filter closed trades
    closed_trades = []
    for deal in deals:
        if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
            # entry=0 - открытие, entry=1 - закрытие
            if hasattr(deal, 'entry') and deal.entry == 1:
                closed_trades.append(deal)
    
    print(f"📊 Закрытых сделок: {len(closed_trades)}")
    
    # Show last 10
    print("\nПоследние 10 закрытых сделок:")
    for i, deal in enumerate(closed_trades[-10:], 1):
        dt = datetime.fromtimestamp(deal.time)
        action = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
        print(f"{i:2d}. {dt.strftime('%Y-%m-%d %H:%M:%S')} | {deal.symbol:6s} | {action:4s} | "
              f"{deal.volume:.2f} lot | Profit: ${deal.profit:+.2f}")

mt5.shutdown()
print("\n✅ Завершено")

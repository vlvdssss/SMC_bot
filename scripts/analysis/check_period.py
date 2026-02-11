import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

# Период со скриншота: 13:59:32 до 18:31:05
today = datetime(2026, 2, 9)
start = today.replace(hour=13, minute=59, second=0)
end = today.replace(hour=18, minute=32, second=0)

print("=" * 100)
print(f"ПРОВЕРКА ПЕРИОДА: {start.strftime('%H:%M:%S')} - {end.strftime('%H:%M:%S')}")
print("=" * 100)

# Получаем историю
deals = mt5.history_deals_get(start, end)

if deals is None or len(deals) == 0:
    print("❌ Нет сделок")
    mt5.shutdown()
    exit()

print(f"\nВсего deals: {len(deals)}")

# Фильтруем только торговые операции
buy_count = 0
sell_count = 0
trades = []

for deal in deals:
    if deal.type not in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
        continue
    
    # Только закрытые позиции (entry=1)
    is_closed = deal.entry == 1 if hasattr(deal, 'entry') else False
    if not is_closed:
        continue
    
    deal_time = datetime.fromtimestamp(deal.time)
    direction = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
    
    trades.append({
        'time': deal_time.strftime('%Y.%m.%d %H:%M:%S'),
        'ticket': deal.ticket,
        'direction': direction,
        'volume': deal.volume,
        'price': deal.price,
        'sl': getattr(deal, 'sl', 0),
        'tp': getattr(deal, 'tp', 0),
        'profit': deal.profit
    })
    
    if deal.type == mt5.DEAL_TYPE_BUY:
        buy_count += 1
    else:
        sell_count += 1

print(f"\n📊 СТАТИСТИКА:")
print(f"   BUY:  {buy_count}")
print(f"   SELL: {sell_count}")
print(f"   ИТОГО: {buy_count + sell_count}")

print(f"\n📋 ДЕТАЛИ ВСЕХ СДЕЛОК:")
print(f"{'Время':<20} {'Ticket':<15} {'Тип':<6} {'Объем':<8} {'Цена':<10} {'S/L':<10} {'T/P':<10} {'Прибыль':<10}")
print("=" * 100)

for t in trades:
    emoji = "✅" if t['profit'] > 0 else "❌"
    print(f"{t['time']:<20} {t['ticket']:<15} {t['direction']:<6} {t['volume']:<8.2f} {t['price']:<10.2f} "
          f"{t['sl']:<10.2f} {t['tp']:<10.2f} {emoji} ${t['profit']:+7.2f}")

total_pnl = sum(t['profit'] for t in trades)
print("=" * 100)
print(f"💰 ИТОГО PnL: ${total_pnl:.2f}")

mt5.shutdown()

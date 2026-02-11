import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

# Период со скриншота
today = datetime(2026, 2, 9)
start = today.replace(hour=13, minute=59, second=0)
end = today.replace(hour=18, minute=32, second=0)

print("=" * 100)
print(f"ВСЕ ОПЕРАЦИИ (ОТКРЫТИЕ И ЗАКРЫТИЕ): {start.strftime('%H:%M:%S')} - {end.strftime('%H:%M:%S')}")
print("=" * 100)

deals = mt5.history_deals_get(start, end)

if deals is None or len(deals) == 0:
    print("❌ Нет сделок")
    mt5.shutdown()
    exit()

print(f"\nВсего deals: {len(deals)}")

# Группируем по entry (0=открытие, 1=закрытие)
opened = []  # entry=0
closed = []  # entry=1

for deal in deals:
    if deal.type not in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
        continue
    
    deal_time = datetime.fromtimestamp(deal.time)
    direction = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
    entry_type = getattr(deal, 'entry', -1)
    
    trade = {
        'time': deal_time.strftime('%Y.%m.%d %H:%M:%S'),
        'ticket': deal.ticket,
        'direction': direction,
        'entry': entry_type,
        'volume': deal.volume,
        'price': deal.price,
        'profit': deal.profit
    }
    
    if entry_type == 0:
        opened.append(trade)
    elif entry_type == 1:
        closed.append(trade)

print(f"\n{'='*100}")
print(f"📈 ОТКРЫТИЕ ПОЗИЦИЙ (entry=0) - ЭТО ПОКАЗАНО НА ТВОЁМ СКРИНШОТЕ:")
print(f"{'='*100}")
print(f"BUY открытий:  {sum(1 for t in opened if t['direction'] == 'BUY')}")
print(f"SELL открытий: {sum(1 for t in opened if t['direction'] == 'SELL')}")
print(f"\nДетали:")
for t in opened:
    print(f"{t['time']} | Ticket: {t['ticket']} | {t['direction']:4s} | {t['volume']} lots | ${t['price']:.2f}")

print(f"\n{'='*100}")
print(f"📉 ЗАКРЫТИЕ ПОЗИЦИЙ (entry=1) - ЭТО Я АНАЛИЗИРОВАЛ:")
print(f"{'='*100}")
print(f"BUY закрытий:  {sum(1 for t in closed if t['direction'] == 'BUY')}")
print(f"SELL закрытий: {sum(1 for t in closed if t['direction'] == 'SELL')}")
print(f"\nДетали:")
for t in closed:
    emoji = "✅" if t['profit'] > 0 else "❌"
    print(f"{t['time']} | Ticket: {t['ticket']} | {t['direction']:4s} | {t['volume']} lots | ${t['price']:.2f} | {emoji} ${t['profit']:+7.2f}")

mt5.shutdown()

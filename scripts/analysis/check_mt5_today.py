import MetaTrader5 as mt5
from datetime import datetime, timedelta

mt5.initialize()

# Сегодняшний день
today = datetime(2026, 2, 9)
start = today.replace(hour=0, minute=0, second=0)
end = today.replace(hour=23, minute=59, second=59)

print("=" * 100)
print(f"ПРОВЕРКА РЕАЛЬНЫХ СДЕЛОК В MT5 ЗА {today.strftime('%Y-%m-%d')}")
print("=" * 100)

# Получаем историю сделок
deals = mt5.history_deals_get(start, end)

if deals is None or len(deals) == 0:
    print("❌ Нет сделок")
    mt5.shutdown()
    exit()

print(f"\nВсего deals в MT5: {len(deals)}")

# Фильтруем только закрытые позиции (entry=1)
buy_deals = []
sell_deals = []

for deal in deals:
    # Пропускаем deposit/credit/balance операции
    if deal.type not in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
        continue
    
    # Берём только ЗАКРЫТЫЕ позиции (entry=1)
    is_closed = deal.entry == 1 if hasattr(deal, 'entry') else False
    
    if is_closed:
        deal_time = datetime.fromtimestamp(deal.time)
        hour = deal_time.hour
        
        if deal.type == mt5.DEAL_TYPE_BUY:
            buy_deals.append({
                'time': deal_time.strftime('%H:%M:%S'),
                'hour': hour,
                'profit': deal.profit,
                'volume': deal.volume,
                'price': deal.price
            })
        elif deal.type == mt5.DEAL_TYPE_SELL:
            sell_deals.append({
                'time': deal_time.strftime('%H:%M:%S'),
                'hour': hour,
                'profit': deal.profit,
                'volume': deal.volume,
                'price': deal.price
            })

print(f"\n📊 СТАТИСТИКА ПО НАПРАВЛЕНИЯМ (только закрытые):")
print(f"   BUY сделок:  {len(buy_deals)}")
print(f"   SELL сделок: {len(sell_deals)}")
print(f"   ИТОГО:       {len(buy_deals) + len(sell_deals)}")

# BUY сделки
if buy_deals:
    buy_pnl = sum(d['profit'] for d in buy_deals)
    print(f"\n📈 BUY СДЕЛКИ ({len(buy_deals)}) | PnL: ${buy_pnl:.2f}")
    for d in buy_deals:
        emoji = "✅" if d['profit'] > 0 else "❌"
        print(f"   {emoji} {d['time']} | Vol: {d['volume']} | ${d['profit']:+7.2f}")

# SELL сделки
if sell_deals:
    sell_pnl = sum(d['profit'] for d in sell_deals)
    print(f"\n📉 SELL СДЕЛКИ ({len(sell_deals)}) | PnL: ${sell_pnl:.2f}")
    for d in sell_deals:
        emoji = "✅" if d['profit'] > 0 else "❌"
        print(f"   {emoji} {d['time']} | Vol: {d['volume']} | ${d['profit']:+7.2f}")

# Почасовая статистика
print(f"\n📅 ПОЧАСОВАЯ РАЗБИВКА:")
from collections import defaultdict
hourly = defaultdict(lambda: {'buy': 0, 'sell': 0})

for d in buy_deals:
    hourly[d['hour']]['buy'] += 1
for d in sell_deals:
    hourly[d['hour']]['sell'] += 1

for hour in sorted(hourly.keys()):
    b = hourly[hour]['buy']
    s = hourly[hour]['sell']
    print(f"   {hour:02d}:00 | BUY: {b:2d} | SELL: {s:2d}")

total_pnl = sum(d['profit'] for d in buy_deals) + sum(d['profit'] for d in sell_deals)
print(f"\n💰 ИТОГО PnL: ${total_pnl:.2f}")

mt5.shutdown()

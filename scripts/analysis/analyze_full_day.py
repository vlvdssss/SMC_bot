import MetaTrader5 as mt5
from datetime import datetime
from collections import defaultdict

mt5.initialize()

# Весь день
today = datetime(2026, 2, 9)
start = today.replace(hour=0, minute=0, second=0)
end = today.replace(hour=23, minute=59, second=59)

print("=" * 100)
print("ПОЛНЫЙ АНАЛИЗ СЕГОДНЯШНЕГО ДНЯ - ТОЛЬКО ОТКРЫТИЯ ПОЗИЦИЙ (entry=0)")
print("=" * 100)

deals = mt5.history_deals_get(start, end)

if not deals:
    print("❌ Нет сделок")
    mt5.shutdown()
    exit()

# Собираем только ОТКРЫТИЯ позиций
buy_opens = []
sell_opens = []

for deal in deals:
    if deal.type not in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
        continue
    
    # Только ОТКРЫТИЯ (entry=0)
    entry_type = getattr(deal, 'entry', -1)
    if entry_type != 0:
        continue
    
    deal_time = datetime.fromtimestamp(deal.time)
    
    trade = {
        'time': deal_time.strftime('%H:%M:%S'),
        'hour': deal_time.hour,
        'ticket': deal.ticket,
        'price': deal.price,
        'volume': deal.volume
    }
    
    if deal.type == mt5.DEAL_TYPE_BUY:
        buy_opens.append(trade)
    else:
        sell_opens.append(trade)

print(f"\n📊 ОТКРЫТО ПОЗИЦИЙ ЗА ВЕСЬ ДЕНЬ:")
print(f"   BUY:  {len(buy_opens)}")
print(f"   SELL: {len(sell_opens)}")
print(f"   ИТОГО: {len(buy_opens) + len(sell_opens)}")

# Почасовая статистика
hourly = defaultdict(lambda: {'buy': 0, 'sell': 0})
for t in buy_opens:
    hourly[t['hour']]['buy'] += 1
for t in sell_opens:
    hourly[t['hour']]['sell'] += 1

print(f"\n📅 ПОЧАСОВОЕ ОТКРЫТИЕ ПОЗИЦИЙ:")
print(f"{'Час':<6} {'BUY':<6} {'SELL':<6} {'Итого':<6}")
print("-" * 30)
for hour in sorted(hourly.keys()):
    b = hourly[hour]['buy']
    s = hourly[hour]['sell']
    print(f"{hour:02d}:00  {b:<6} {s:<6} {b+s:<6}")

print(f"\n📋 ВСЕ BUY ОТКРЫТИЯ:")
if buy_opens:
    for t in buy_opens:
        print(f"   {t['time']} | Ticket: {t['ticket']} | ${t['price']:.2f}")
else:
    print("   ✅ НЕТ BUY ОТКРЫТИЙ")

print(f"\n📋 ВСЕ SELL ОТКРЫТИЯ:")
if sell_opens:
    for t in sell_opens[:20]:  # Первые 20
        print(f"   {t['time']} | Ticket: {t['ticket']} | ${t['price']:.2f}")
    if len(sell_opens) > 20:
        print(f"   ... и ещё {len(sell_opens) - 20} SELL открытий")
else:
    print("   ❌ НЕТ SELL ОТКРЫТИЙ")

print(f"\n{'='*100}")
print(f"ВЫВОД:")
print(f"{'='*100}")

if len(buy_opens) > len(sell_opens):
    print("⚠️ БОТ ОТКРЫВАЛ БОЛЬШЕ BUY - возможна проблема с AI логикой")
elif len(sell_opens) > len(buy_opens):
    print("✅ БОТ ОТКРЫВАЛ БОЛЬШЕ SELL - AI работал правильно (downtrend)")
else:
    print("⚖️ Равное количество BUY и SELL")

mt5.shutdown()

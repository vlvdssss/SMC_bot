"""Quick check today's trades"""
import json
from collections import defaultdict
from datetime import datetime

# Load trades
with open('data/trades_history.json', encoding='utf-8') as f:
    trades = json.load(f)

# Filter today
today = [t for t in trades if t.get('date') == '2026-02-10']

print("="*80)
print(f"📊 СЕГОДНЯ (2026-02-10): {len(today)} сделок")
print("="*80)

wins = [t for t in today if float(t.get('pnl', 0)) > 0]
losses = [t for t in today if float(t.get('pnl', 0)) < 0]
total_pnl = sum(float(t.get('pnl', 0)) for t in today)

print(f"✅ Прибыльных: {len(wins)}")
print(f"❌ Убыточных: {len(losses)}")
print(f"📈 Winrate: {len(wins)/len(today)*100 if today else 0:.1f}%")
print(f"💰 Total PnL: ${total_pnl:.2f}")
print()

# By hour
by_hour = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0})
for t in today:
    hour = t['time'][:2]
    by_hour[hour]['count'] += 1
    by_hour[hour]['pnl'] += float(t.get('pnl', 0))
    if float(t.get('pnl', 0)) > 0:
        by_hour[hour]['wins'] += 1
    else:
        by_hour[hour]['losses'] += 1

print("🕐 ПОЧАСОВАЯ РАЗБИВКА:")
print("-"*80)
for h in sorted(by_hour.keys()):
    d = by_hour[h]
    wr = d['wins']/d['count']*100 if d['count'] else 0
    print(f"{h}:00 - {d['count']:2d} сделок | W:{d['wins']:2d} L:{d['losses']:2d} | WR:{wr:5.1f}% | PnL: ${d['pnl']:7.2f}")

print()
print("="*80)
print("❌ ХУДШИЕ УБЫТКИ:")
print("="*80)
worst = sorted([t for t in today if float(t.get('pnl', 0)) < 0], key=lambda x: float(x.get('pnl', 0)))[:10]
for t in worst:
    print(f"{t['time']} | {t['direction']:4s} | {t['instrument']} | ${float(t.get('pnl', 0)):7.2f}")

print()
print("="*80)
print("🔥 СЕРИИ УБЫТКОВ:")
print("="*80)

# Find consecutive loss series
sorted_today = sorted(today, key=lambda x: f"{x['date']} {x['time']}")
consecutive = 0
max_consecutive = 0
current_series = []
worst_series = []

for t in sorted_today:
    if float(t.get('pnl', 0)) < 0:
        consecutive += 1
        current_series.append(t)
        if consecutive > max_consecutive:
            max_consecutive = consecutive
            worst_series = current_series.copy()
    else:
        consecutive = 0
        current_series = []

print(f"Максимальная серия: {max_consecutive} убытков подряд")
if worst_series:
    series_pnl = sum(float(t.get('pnl', 0)) for t in worst_series)
    print(f"Убыток от серии: ${series_pnl:.2f}")
    print("Сделки:")
    for t in worst_series:
        print(f"  {t['time']} | {t['direction']:4s} | ${float(t.get('pnl', 0)):7.2f}")

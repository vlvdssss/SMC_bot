import json
from datetime import datetime
from collections import defaultdict

# Загружаем сделки
with open('data/trades_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

# Новые сделки (с 27.01)
new_trades = [t for t in trades if datetime.strptime(t.get('date', '2000-01-01'), '%Y-%m-%d') >= datetime(2026, 1, 27)]

# Группируем по дням
by_date = defaultdict(list)
for t in new_trades:
    by_date[t['date']].append(t)

print(f"{'='*70}")
print(f"СТАТИСТИКА ПО ДНЯМ (с 27 января)")
print(f"{'='*70}")

total_pnl = 0
for date in sorted(by_date.keys()):
    day_trades = by_date[date]
    day_pnl = sum(t.get('pnl', 0) for t in day_trades)
    day_wins = sum(1 for t in day_trades if t.get('pnl', 0) > 0)
    day_losses = len(day_trades) - day_wins
    winrate = day_wins / len(day_trades) * 100 if day_trades else 0
    
    total_pnl += day_pnl
    
    emoji = "+" if day_pnl > 0 else "-"
    print(f"{emoji} {date}: {len(day_trades):2} сделок | "
          f"PnL: ${day_pnl:+7.2f} | "
          f"W/L: {day_wins}/{day_losses} ({winrate:.0f}%)")

print(f"{'='*70}")
print(f"ИТОГО: ${total_pnl:.2f}")
print(f"{'='*70}")

# Смотрим что с балансом
print(f"\n{'='*70}")
print(f"БАЛАНС")
print(f"{'='*70}")
with open('data/bot_stats.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)

print(f"Текущий баланс:     ${stats['balance']:.2f}")
print(f"Total PnL (файл):   ${stats['total_pnl']:.2f}")
print(f"Starting (файл):    ${stats['starting_balance']:.2f}")
print(f"\nPnL новых сделок:   ${total_pnl:.2f}")
print(f"Правильный старт:   ${stats['balance'] - total_pnl:.2f}")
print(f"\nРАЗНИЦА: ${stats['starting_balance'] - (stats['balance'] - total_pnl):.2f}")

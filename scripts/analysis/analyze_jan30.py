import json

with open('data/trades_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

jan30 = [t for t in trades if t.get('date') == '2026-01-30']

print(f"{'='*70}")
print(f"ДЕТАЛЬНЫЙ АНАЛИЗ 30 ЯНВАРЯ (178 сделок!)")
print(f"{'='*70}\n")

wins = [t for t in jan30 if t.get('pnl', 0) > 0]
losses = [t for t in jan30 if t.get('pnl', 0) < 0]
breakevens = [t for t in jan30 if t.get('pnl', 0) == 0]

total_pnl = sum(t.get('pnl', 0) for t in jan30)
avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0

print(f"Всего сделок: {len(jan30)}")
print(f"  + Прибыльных: {len(wins)} (средняя: ${avg_win:.2f})")
print(f"  - Убыточных: {len(losses)} (средняя: ${avg_loss:.2f})")
print(f"  = Breakeven: {len(breakevens)}")
print(f"\nИтоговый PnL: ${total_pnl:.2f}")
print(f"Winrate: {len(wins)/len(jan30)*100:.1f}%")

# Проверяем распределение
print(f"\n{'─'*70}")
print(f"РАСПРЕДЕЛЕНИЕ УБЫТКОВ:")
print(f"{'─'*70}")

loss_ranges = {
    'Мелкие (-$0.01 до -$2)': 0,
    'Средние (-$2 до -$5)': 0,
    'Крупные (-$5 и больше)': 0,
}

for t in losses:
    pnl = abs(t.get('pnl', 0))
    if pnl < 2:
        loss_ranges['Мелкие (-$0.01 до -$2)'] += 1
    elif pnl < 5:
        loss_ranges['Средние (-$2 до -$5)'] += 1
    else:
        loss_ranges['Крупные (-$5 и больше)'] += 1

for range_name, count in loss_ranges.items():
    print(f"  {range_name}: {count}")

print(f"\n{'─'*70}")
print(f"ВЫВОД:")
print(f"{'─'*70}")
print(f"Проблема: СЛИШКОМ МНОГО СДЕЛОК за день ({len(jan30)})")
print(f"Низкий винрейт: {len(wins)/len(jan30)*100:.1f}%")
print(f"Возможно, бот переторговывает!")

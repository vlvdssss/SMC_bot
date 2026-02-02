import json
from datetime import datetime

# Загружаем сделки
with open('data/trades_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

# Анализируем
cutoff = datetime(2026, 1, 27)
old_trades = []
new_trades = []

for t in trades:
    try:
        trade_date = datetime.strptime(t.get('date', '2000-01-01'), '%Y-%m-%d')
        if trade_date < cutoff:
            old_trades.append(t)
        else:
            new_trades.append(t)
    except:
        old_trades.append(t)

print(f"{'='*60}")
print(f"АНАЛИЗ СДЕЛОК")
print(f"{'='*60}")
print(f"\nВсего сделок в истории: {len(trades)}")
print(f"Старые (до 27.01.2026): {len(old_trades)}")
print(f"Новые (с 27.01.2026):   {len(new_trades)}")

# Старые сделки
old_pnl = sum(t.get('pnl', 0) for t in old_trades)
old_wins = sum(1 for t in old_trades if t.get('pnl', 0) > 0)
old_losses = len(old_trades) - old_wins

print(f"\n{'─'*60}")
print(f"СТАРЫЕ СДЕЛКИ (мусор):")
print(f"{'─'*60}")
print(f"  💰 PnL: ${old_pnl:.2f}")
print(f"  ✅ Прибыльных: {old_wins}")
print(f"  ❌ Убыточных: {old_losses}")
if old_trades:
    print(f"  📊 Winrate: {old_wins/len(old_trades)*100:.1f}%")

# Новые сделки
if new_trades:
    new_pnl = sum(t.get('pnl', 0) for t in new_trades)
    new_wins = sum(1 for t in new_trades if t.get('pnl', 0) > 0)
    new_losses = len(new_trades) - new_wins
    
    print(f"\n{'─'*60}")
    print(f"НОВЫЕ СДЕЛКИ (с 27.01 - хороший бот):")
    print(f"{'─'*60}")
    print(f"  💰 PnL: ${new_pnl:.2f}")
    print(f"  ✅ Прибыльных: {new_wins}")
    print(f"  ❌ Убыточных: {new_losses}")
    print(f"  📊 Winrate: {new_wins/len(new_trades)*100:.1f}%")
else:
    print(f"\n❌ Новых сделок НЕТ!")

print(f"\n{'='*60}")
print(f"ВЫВОД: Надо УДАЛИТЬ {len(old_trades)} старых сделок!")
print(f"{'='*60}")

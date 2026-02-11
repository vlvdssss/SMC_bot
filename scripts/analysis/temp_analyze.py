import json
from datetime import datetime

trades = json.load(open('data/trades_history.json', 'r', encoding='utf-8'))
today = '2026-02-09'
today_trades = [t for t in trades if t.get('date') == today]

print(f'Сделок за сегодня: {len(today_trades)}')
total_pnl = sum(t.get('pnl', 0) for t in today_trades)
print(f'Total PnL: ${total_pnl:.2f}')

wins = [t for t in today_trades if t.get('pnl', 0) > 0]
losses = [t for t in today_trades if t.get('pnl', 0) < 0]
print(f'Wins: {len(wins)}, Losses: {len(losses)}')

# Группировка по направлению
buys = [t for t in today_trades if t.get('direction') == 'BUY']
sells = [t for t in today_trades if t.get('direction') == 'SELL']

buy_pnl = sum(t.get('pnl', 0) for t in buys)
sell_pnl = sum(t.get('pnl', 0) for t in sells)

print(f'\nBUY: {len(buys)} сделок, PnL: ${buy_pnl:.2f}')
print(f'SELL: {len(sells)} сделок, PnL: ${sell_pnl:.2f}')

print(f'\nВСЕ сделки за сегодня:')
for i, t in enumerate(today_trades, 1):
    print(f"{i}. {t.get('time', 'N/A'):5} {t.get('instrument', 'N/A'):6} {t.get('direction', 'N/A'):4} PnL: ${t.get('pnl', 0):7.2f}")

# Находим максимальную просадку
running_pnl = 0
max_drawdown = 0
for t in today_trades:
    running_pnl += t.get('pnl', 0)
    if running_pnl < max_drawdown:
        max_drawdown = running_pnl

print(f'\nМаксимальная просадка: ${max_drawdown:.2f}')
print(f'Текущий PnL: ${total_pnl:.2f}')

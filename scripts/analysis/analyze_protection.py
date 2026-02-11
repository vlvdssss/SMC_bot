"""Анализ работы защиты и сделок"""
import json
from datetime import datetime
from pathlib import Path

# Загружаем историю сделок
trades_file = Path('data/trades_history.json')
trades = json.load(open(trades_file, 'r', encoding='utf-8'))

# Анализируем последние 100 сделок
recent_trades = trades[-100:]

print("="*80)
print("АНАЛИЗ ПОСЛЕДНИХ 100 СДЕЛОК")
print("="*80)

# Подсчёт статистики
wins = [t for t in recent_trades if t.get('pnl', 0) > 0]
losses = [t for t in recent_trades if t.get('pnl', 0) < 0]
total_pnl = sum(t.get('pnl', 0) for t in recent_trades)

print(f"\nОбщая статистика:")
print(f"  Всего сделок: {len(recent_trades)}")
print(f"  Побед: {len(wins)} ({len(wins)/len(recent_trades)*100:.1f}%)")
print(f"  Убытков: {len(losses)} ({len(losses)/len(recent_trades)*100:.1f}%)")
print(f"  Total PnL: ${total_pnl:.2f}")
print(f"  Средняя победа: ${sum(t['pnl'] for t in wins)/len(wins):.2f}" if wins else "N/A")
print(f"  Средний убыток: ${sum(t['pnl'] for t in losses)/len(losses):.2f}" if losses else "N/A")

# Анализ серий убытков
print(f"\n{'='*80}")
print("АНАЛИЗ СЕРИЙ УБЫТКОВ (должна была сработать защита после 2 подряд)")
print("="*80)

consecutive_losses = 0
max_consecutive_losses = 0
series = []
current_series = []

for trade in recent_trades:
    pnl = trade.get('pnl', 0)
    
    if pnl < 0:
        consecutive_losses += 1
        current_series.append(trade)
        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
    else:
        if consecutive_losses >= 2:
            series.append({
                'count': consecutive_losses,
                'trades': current_series.copy(),
                'total_loss': sum(t.get('pnl', 0) for t in current_series)
            })
        consecutive_losses = 0
        current_series = []

# Последняя серия
if consecutive_losses >= 2:
    series.append({
        'count': consecutive_losses,
        'trades': current_series.copy(),
        'total_loss': sum(t.get('pnl', 0) for t in current_series)
    })

print(f"\n⚠️  НАЙДЕНО СЕРИЙ ПОДРЯД УБЫТКОВ (≥2): {len(series)}")
print(f"⚠️  МАКСИМАЛЬНАЯ СЕРИЯ: {max_consecutive_losses} убытков подряд")

if series:
    print(f"\n📉 ТОП-5 ХУДШИХ СЕРИЙ:")
    sorted_series = sorted(series, key=lambda x: x['total_loss'])[:5]
    
    for i, s in enumerate(sorted_series, 1):
        print(f"\n  {i}. Серия из {s['count']} убытков подряд (${s['total_loss']:.2f}):")
        for t in s['trades']:
            print(f"     → {t.get('date')} {t.get('time')} {t.get('direction'):4} PnL: ${t.get('pnl'):.2f}")

# Анализ по направлениям
print(f"\n{'='*80}")
print("АНАЛИЗ ПО НАПРАВЛЕНИЯМ")
print("="*80)

buys = [t for t in recent_trades if t.get('direction') == 'BUY']
sells = [t for t in recent_trades if t.get('direction') == 'SELL']

buy_wins = [t for t in buys if t.get('pnl', 0) > 0]
buy_losses = [t for t in buys if t.get('pnl', 0) < 0]
sell_wins = [t for t in sells if t.get('pnl', 0) > 0]
sell_losses = [t for t in sells if t.get('pnl', 0) < 0]

if buys:
    buy_pnl = sum(t.get('pnl', 0) for t in buys)
    print(f"\n  BUY сделки:")
    print(f"    Всего: {len(buys)}")
    print(f"    Побед: {len(buy_wins)} ({len(buy_wins)/len(buys)*100:.1f}%)")
    print(f"    Убытков: {len(buy_losses)} ({len(buy_losses)/len(buys)*100:.1f}%)")
    print(f"    Total PnL: ${buy_pnl:.2f}")

if sells:
    sell_pnl = sum(t.get('pnl', 0) for t in sells)
    print(f"\n  SELL сделки:")
    print(f"    Всего: {len(sells)}")
    print(f"    Побед: {len(sell_wins)} ({len(sell_wins)/len(sells)*100:.1f}%)")
    print(f"    Убытков: {len(sell_losses)} ({len(sell_losses)/len(sells)*100:.1f}%)")
    print(f"    Total PnL: ${sell_pnl:.2f}")

# Проверка настроек защиты
print(f"\n{'='*80}")
print("ПРОВЕРКА НАСТРОЕК ЗАЩИТЫ")
print("="*80)

import yaml
trading_config = yaml.safe_load(open('config/trading.yaml', 'r', encoding='utf-8'))

stop_loss_protection = trading_config.get('trading', {}).get('stop_loss_protection', {})
profit_protection = trading_config.get('trading', {}).get('profit_protection', {})

print(f"\nStop Loss Protection:")
print(f"  Enabled: {stop_loss_protection.get('enabled', False)}")
print(f"  Consecutive stops: {stop_loss_protection.get('consecutive_stops', 'N/A')}")
print(f"  Cooldown (min): {stop_loss_protection.get('cooldown_minutes', 'N/A')}")

print(f"\nProfit Protection:")
print(f"  Enabled: {profit_protection.get('enabled', False)}")
print(f"  Consecutive wins: {profit_protection.get('consecutive_wins', 'N/A')}")
print(f"  Cooldown (min): {profit_protection.get('cooldown_minutes', 'N/A')}")

print(f"\n{'='*80}")
print("ВЫВОД:")
print("="*80)

if len(series) > 0:
    print(f"\n⚠️  КРИТИЧЕСКАЯ ПРОБЛЕМА: Найдено {len(series)} серий из 2+ убытков подряд!")
    print(f"⚠️  Защита НЕ СРАБОТАЛА или не включена!")
    print(f"⚠️  Win Rate: {len(wins)/len(recent_trades)*100:.1f}% (должно быть >50%)")
    
    if not stop_loss_protection.get('enabled'):
        print(f"\n❌  Stop Loss Protection ВЫКЛЮЧЕНА в trading.yaml!")
    else:
        print(f"\n❓  Stop Loss Protection включена, но НЕ РАБОТАЕТ!")
        print(f"    Нужно проверить код в src/live/live_trader.py")
else:
    print(f"\n✅  Серий из 2+ убытков не найдено")

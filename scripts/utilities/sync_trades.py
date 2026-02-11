"""Принудительная синхронизация сделок из MT5"""
import sys
import os
from pathlib import Path

# Устанавливаем рабочую директорию
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from src.core.mt5_manager import MT5Manager
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("="*80)
print("ПРИНУДИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ СДЕЛОК ИЗ MT5")
print("="*80)

# Создаём manager
manager = MT5Manager()

# Инициализируем и подключаемся
if not manager.initialize():
    print("❌ Не удалось инициализировать MT5!")
    sys.exit(1)

# Загружаем конфиг MT5
import yaml
mt5_config = yaml.safe_load(open('config/mt5.yaml', 'r', encoding='utf-8'))
credentials = mt5_config.get('mt5', {}).get('connection', {})

login = credentials.get('login', 0)
password = credentials.get('password', '')
server = credentials.get('server', '')

if not login or not password:
    print("❌ Не найденыданные для подключения в config/mt5.yaml!")
    sys.exit(1)

success, msg = manager.connect(login, password, server)
if not success:
    print(f"❌ Не удалось подключиться к MT5: {msg}")
    sys.exit(1)

print(f"✅ Подключен к MT5")

# Получаем историю за последние 7 дней
print(f"\n📊 Получаю историю сделок за последние 7 дней...")
trades = manager.get_trade_history(days=7)

if not trades:
    print(f"❌ Нет сделок в истории MT5")
    sys.exit(0)

print(f"✅ Найдено {len(trades)} сделок в MT5")

# Загружаем существующие сделки
trades_file = Path('data/trades_history.json')
existing_trades = []
existing_ids = set()

if trades_file.exists():
    with open(trades_file, 'r', encoding='utf-8') as f:
        existing_trades = json.load(f)
        existing_ids = {int(t.get('id', 0)) for t in existing_trades if t.get('id')}

print(f"📁 В файле уже есть {len(existing_trades)} сделок")

# Находим новые сделки
new_trades = []
today = datetime.now().strftime('%Y-%m-%d')
today_new = []

for trade in trades:
    trade_id = int(trade.get('id', 0))
    if trade_id and trade_id not in existing_ids:
        new_trades.append(trade)
        if trade.get('date') == today:
            today_new.append(trade)

if not new_trades:
    print(f"\n✅ Все сделки уже синхронизированы!")
    sys.exit(0)

print(f"\n🆕 Найдено {len(new_trades)} НОВЫХ сделок")
print(f"🆕 Из них сегодняшних: {len(today_new)}")

# Показываем сегодняшние сделки подробно
if today_new:
    print(f"\n{'='*80}")
    print(f"СЕГОДНЯШНИЕ СДЕЛКИ ({today}):")
    print("="*80)
    
    total_today_pnl = 0
    for i, trade in enumerate(sorted(today_new, key=lambda x: x.get('time', '')), 1):
        pnl = trade.get('pnl', 0)
        total_today_pnl += pnl
        symbol = '✅' if pnl > 0 else '❌'
        print(f"{i:2}. {trade.get('time', 'N/A'):5} {trade.get('instrument', 'N/A'):6} "
              f"{trade.get('direction', 'N/A'):4} {symbol} PnL: ${pnl:7.2f}")
    
    print(f"\n📊 ИТОГО за сегодня: ${total_today_pnl:.2f}")

# Добавляем новые сделки в файл
print(f"\n💾 Добавляю {len(new_trades)} новых сделок в файл...")

all_trades = existing_trades + new_trades

# Атомарное сохранение
temp_file = trades_file.with_suffix('.tmp')
try:
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False, default=str)
    temp_file.replace(trades_file)
    print(f"✅ Файл обновлён! Теперь {len(all_trades)} сделок в истории")
except Exception as e:
    print(f"❌ Ошибка сохранения: {e}")
    if temp_file.exists():
        temp_file.unlink()
    sys.exit(1)

# Пересчитываем статистику
print(f"\n📊 Пересчитываю статистику...")
wins = len([t for t in all_trades if t.get('pnl', 0) > 0])
losses = len([t for t in all_trades if t.get('pnl', 0) < 0])
total_pnl = sum(t.get('pnl', 0) for t in all_trades)
today_pnl = sum(t.get('pnl', 0) for t in all_trades if t.get('date') == today)

print(f"  Всего сделок: {len(all_trades)}")
print(f"  Побед: {wins} ({wins/len(all_trades)*100:.1f}%)")
print(f"  Убытков: {losses} ({losses/len(all_trades)*100:.1f}%)")
print(f"  Total PnL: ${total_pnl:.2f}")
print(f"  Today PnL: ${today_pnl:.2f}")

print(f"\n{'='*80}")
print(f"✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!")
print("="*80)

manager.disconnect()

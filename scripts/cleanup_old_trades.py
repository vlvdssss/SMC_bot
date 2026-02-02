#!/usr/bin/env python3
"""
Скрипт очистки старых сделок до указанной даты
Обновляет статистику и баланс с учетом MT5
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import logger
import MetaTrader5 as mt5


def cleanup_trades_before_date(cutoff_date: str = "2026-01-27"):
    """
    Очистить все сделки до указанной даты.
    
    Args:
        cutoff_date: Дата в формате YYYY-MM-DD (сделки до этой даты будут удалены)
    """
    # Пути к файлам
    trades_file = Path('data/trades_history.json')
    stats_file = Path('data/bot_stats.json')
    
    if not trades_file.exists():
        logger.error(f"Файл {trades_file} не найден!")
        return False
    
    # Читаем текущие сделки
    with open(trades_file, 'r', encoding='utf-8') as f:
        all_trades = json.load(f)
    
    logger.info(f"Всего сделок в истории: {len(all_trades)}")
    
    # Фильтруем сделки - оставляем только после cutoff_date
    cutoff_dt = datetime.strptime(cutoff_date, "%Y-%m-%d")
    filtered_trades = []
    
    for trade in all_trades:
        trade_date_str = trade.get('date', '')
        try:
            trade_dt = datetime.strptime(trade_date_str, "%Y-%m-%d")
            if trade_dt >= cutoff_dt:
                filtered_trades.append(trade)
        except ValueError:
            # Если дата не распарсилась, пропускаем
            logger.warning(f"Не удалось распарсить дату сделки: {trade_date_str}")
            continue
    
    logger.info(f"Сделок после {cutoff_date}: {len(filtered_trades)}")
    logger.info(f"Удалено сделок: {len(all_trades) - len(filtered_trades)}")
    
    # Сохраняем отфильтрованные сделки
    with open(trades_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_trades, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Сделки обновлены в {trades_file}")
    
    # Получаем текущий баланс из MT5
    if not mt5.initialize():
        logger.error("❌ Не удалось подключиться к MT5!")
        logger.error("⚠️ Статистика не будет обновлена с балансом MT5")
        mt5_balance = None
    else:
        account_info = mt5.account_info()
        if account_info:
            mt5_balance = account_info.balance
            logger.info(f"💰 Баланс из MT5: ${mt5_balance:.2f}")
        else:
            logger.warning("⚠️ Не удалось получить баланс из MT5")
            mt5_balance = None
        mt5.shutdown()
    
    # Пересчитываем статистику на основе отфильтрованных сделок
    total_trades = len(filtered_trades)
    wins = sum(1 for t in filtered_trades if t.get('pnl', 0) > 0)
    losses = sum(1 for t in filtered_trades if t.get('pnl', 0) < 0)
    total_pnl = sum(t.get('pnl', 0) for t in filtered_trades)
    
    # Читаем текущую статистику
    if stats_file.exists():
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    else:
        stats = {}
    
    # Обновляем статистику
    if mt5_balance is not None:
        stats['balance'] = mt5_balance
        stats['equity'] = mt5_balance
        # Баланс на начало = текущий баланс - профит
        stats['starting_balance'] = mt5_balance - total_pnl
    
    stats['total_pnl'] = total_pnl
    stats['total_trades'] = total_trades
    stats['trades'] = total_trades
    stats['wins'] = wins
    stats['losses'] = losses
    stats['winning_trades'] = wins
    stats['losing_trades'] = losses
    stats['last_date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Сохраняем обновленную статистику
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Статистика обновлена в {stats_file}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("📊 ИТОГОВАЯ СТАТИСТИКА:")
    logger.info(f"   💰 Баланс: ${stats.get('balance', 0):.2f}")
    logger.info(f"   📈 Профит: ${total_pnl:.2f}")
    logger.info(f"   📊 Сделок: {total_trades}")
    logger.info(f"   ✅ Успешных: {wins}")
    logger.info(f"   ❌ Убыточных: {losses}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return True


if __name__ == "__main__":
    logger.info("🧹 Запуск очистки старых сделок...")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Можно передать дату как аргумент
    cutoff_date = "2026-01-27"
    if len(sys.argv) > 1:
        cutoff_date = sys.argv[1]
    
    logger.info(f"🗓️  Удаление сделок до: {cutoff_date}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    success = cleanup_trades_before_date(cutoff_date)
    
    if success:
        logger.info("✅ Очистка завершена успешно!")
    else:
        logger.error("❌ Ошибка при очистке")
        sys.exit(1)

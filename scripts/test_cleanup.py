"""
Тест системы автоочистки
"""

import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.cleanup_service import CleanupService
from src.core.logger import logger


def create_test_signals():
    """Создаём тестовые сигналы разного возраста"""
    signals_dir = Path('data/ai_signals')
    signals_dir.mkdir(parents=True, exist_ok=True)
    
    active_file = signals_dir / 'active_signals.json'
    
    # Создаём сигналы:
    # - 2 свежих (< 36 часов)
    # - 3 старых (> 36 часов) - должны удалиться
    now = datetime.now()
    
    signals = [
        # Свежие сигналы (останутся)
        {
            'id': 'signal_fresh_1',
            'created_at': (now - timedelta(hours=12)).isoformat(),
            'symbol': 'XAUUSD',
            'direction': 'BUY'
        },
        {
            'id': 'signal_fresh_2',
            'created_at': (now - timedelta(hours=24)).isoformat(),
            'symbol': 'EURUSD',
            'direction': 'SELL'
        },
        # Старые сигналы (должны удалиться)
        {
            'id': 'signal_old_1',
            'created_at': (now - timedelta(hours=48)).isoformat(),
            'symbol': 'XAUUSD',
            'direction': 'BUY'
        },
        {
            'id': 'signal_old_2',
            'created_at': (now - timedelta(hours=72)).isoformat(),
            'symbol': 'GBPUSD',
            'direction': 'SELL'
        },
        {
            'id': 'signal_old_3',
            'created_at': (now - timedelta(days=5)).isoformat(),
            'symbol': 'XAUUSD',
            'direction': 'BUY'
        }
    ]
    
    with open(active_file, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Created {len(signals)} test signals")
    logger.info("   - 2 fresh (< 36h)")
    logger.info("   - 3 old (> 36h)")
    
    return active_file


def create_test_logs():
    """Создаём тестовые логи разного возраста"""
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    
    # Создаём файлы:
    # - 2 свежих (< 7д 20ч)
    # - 2 старых (> 7д 20ч) - должны удалиться
    files = []
    
    # Свежие логи
    for i in range(2):
        file_path = logs_dir / f'test_fresh_{i}.log'
        file_path.write_text(f"Fresh log {i}\n")
        
        # Устанавливаем время модификации (5 дней назад)
        mtime = (now - timedelta(days=5)).timestamp()
        import os
        os.utime(file_path, (mtime, mtime))
        files.append(('fresh', file_path))
    
    # Старые логи
    for i in range(2):
        file_path = logs_dir / f'test_old_{i}.log'
        file_path.write_text(f"Old log {i}\n")
        
        # Устанавливаем время модификации (10 дней назад)
        mtime = (now - timedelta(days=10)).timestamp()
        import os
        os.utime(file_path, (mtime, mtime))
        files.append(('old', file_path))
    
    logger.info(f"✅ Created {len(files)} test log files")
    logger.info("   - 2 fresh (< 7d 20h)")
    logger.info("   - 2 old (> 7d 20h)")
    
    return files


def test_signals_cleanup():
    """Тест очистки сигналов"""
    logger.info("\n" + "="*80)
    logger.info("🧪 TEST: Signals Cleanup")
    logger.info("="*80)
    
    # Создаём тестовые данные
    active_file = create_test_signals()
    
    # Читаем количество до очистки
    with open(active_file, 'r', encoding='utf-8') as f:
        before = json.load(f)
    logger.info(f"\n📊 Before cleanup: {len(before)} signals")
    
    # Запускаем очистку
    cleanup = CleanupService()
    stats = cleanup.cleanup_old_signals()
    
    # Читаем количество после очистки
    with open(active_file, 'r', encoding='utf-8') as f:
        after = json.load(f)
    logger.info(f"📊 After cleanup: {len(after)} signals")
    
    # Проверяем результат
    logger.info(f"\n✅ Cleanup stats:")
    logger.info(f"   Deleted: {stats['deleted_active']}")
    logger.info(f"   Remaining: {len(after)}")
    logger.info(f"   Expected: 2 remaining, 3 deleted")
    
    if len(after) == 2 and stats['deleted_active'] == 3:
        logger.info("\n🎉 TEST PASSED: Signals cleanup works correctly!")
        return True
    else:
        logger.error(f"\n❌ TEST FAILED: Expected 2 remaining and 3 deleted, got {len(after)} remaining and {stats['deleted_active']} deleted")
        return False


def test_logs_cleanup():
    """Тест очистки логов"""
    logger.info("\n" + "="*80)
    logger.info("🧪 TEST: Logs Cleanup")
    logger.info("="*80)
    
    # Создаём тестовые данные
    files = create_test_logs()
    logs_dir = Path('logs')
    
    # Считаем файлы до очистки
    before_count = len(list(logs_dir.glob('test_*.log')))
    logger.info(f"\n📊 Before cleanup: {before_count} log files")
    
    # Запускаем очистку
    cleanup = CleanupService()
    stats = cleanup.cleanup_old_logs()
    
    # Считаем файлы после очистки
    after_count = len(list(logs_dir.glob('test_*.log')))
    logger.info(f"📊 After cleanup: {after_count} log files")
    
    # Проверяем результат
    logger.info(f"\n✅ Cleanup stats:")
    logger.info(f"   Deleted files: {stats['deleted_files']}")
    logger.info(f"   Freed space: {stats['deleted_size_mb']:.4f} MB")
    logger.info(f"   Remaining: {after_count}")
    logger.info(f"   Expected: 2 remaining, 2 deleted")
    
    if after_count == 2 and stats['deleted_files'] == 2:
        logger.info("\n🎉 TEST PASSED: Logs cleanup works correctly!")
        
        # Удаляем оставшиеся тестовые файлы
        for f in logs_dir.glob('test_*.log'):
            f.unlink()
        logger.info("🧹 Cleaned up test files")
        
        return True
    else:
        logger.error(f"\n❌ TEST FAILED: Expected 2 remaining and 2 deleted, got {after_count} remaining and {stats['deleted_files']} deleted")
        return False


def main():
    """Запуск всех тестов"""
    logger.info("\n" + "="*80)
    logger.info("🧪 CLEANUP SERVICE TEST SUITE")
    logger.info("="*80)
    
    results = []
    
    # Тест 1: Очистка сигналов
    results.append(('Signals Cleanup', test_signals_cleanup()))
    
    # Тест 2: Очистка логов
    results.append(('Logs Cleanup', test_logs_cleanup()))
    
    # Итоги
    logger.info("\n" + "="*80)
    logger.info("📊 TEST RESULTS")
    logger.info("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\n🎯 Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED!")
    else:
        logger.error("❌ SOME TESTS FAILED")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

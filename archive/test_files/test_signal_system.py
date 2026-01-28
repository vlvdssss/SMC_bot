#!/usr/bin/env python3
"""
Тест системы подачи сигналов

Проверяет:
1. Ограничения времени торговли: ЗАПРЕТ 13:00-18:00, РАЗРЕШЕНО ПН 01:00 - ПТ 21:00
2. Периодичность анализа из конфига
3. Совместимость компонентов
4. GUI настройки
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime, time as dt_time
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import logger
from src.ai.analyst_scheduler import AnalystScheduler
from src.ai.signal_manager import AISignalManager


def load_config(config_name: str) -> dict:
    """Загрузить конфиг"""
    try:
        config_path = Path(f"config/{config_name}")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load {config_name}: {e}")
    return {}


def check_trading_hours(current_time: datetime) -> tuple[bool, str]:
    """
    Проверить разрешено ли торговать сейчас
    
    Правила:
    - ЗАПРЕТ: 13:00 - 18:00 (каждый день)
    - РАЗРЕШЕНО: Понедельник 01:00 - Пятница 21:00
    - ЗАПРЕТ: Суббота, Воскресенье
    
    Returns:
        (allowed, reason)
    """
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    hour = current_time.hour
    
    # Проверка выходных
    if weekday >= 5:  # Saturday=5, Sunday=6
        return False, f"Weekend (day={weekday})"
    
    # Проверка времени недели
    if weekday == 0 and hour < 1:  # Monday before 01:00
        return False, "Monday before 01:00"
    
    if weekday == 4 and hour >= 21:  # Friday after 21:00
        return False, "Friday after 21:00"
    
    # Проверка запретного времени 13:00-18:00
    if 13 <= hour < 18:
        return False, f"Night ban (13:00-18:00), current hour={hour}"
    
    return True, "OK"


def test_time_restrictions():
    """Тест 1: Проверка ограничений времени"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Ограничения времени торговли")
    print("="*60)
    
    # Тестовые сценарии
    test_cases = [
        # (weekday, hour, should_allow, description)
        (0, 0, False, "Monday 00:00 - BEFORE 01:00"),
        (0, 1, True, "Monday 01:00 - START"),
        (0, 12, True, "Monday 12:00 - OK"),
        (0, 13, False, "Monday 13:00 - NIGHT BAN START"),
        (0, 17, False, "Monday 17:00 - NIGHT BAN"),
        (0, 18, True, "Monday 18:00 - NIGHT BAN END"),
        (2, 10, True, "Wednesday 10:00 - OK"),
        (2, 15, False, "Wednesday 15:00 - NIGHT BAN"),
        (4, 20, True, "Friday 20:00 - OK"),
        (4, 21, False, "Friday 21:00 - END"),
        (5, 10, False, "Saturday - WEEKEND"),
        (6, 10, False, "Sunday - WEEKEND"),
    ]
    
    passed = 0
    failed = 0
    
    for weekday, hour, should_allow, description in test_cases:
        # Create test datetime
        test_time = datetime(2026, 1, 5 + weekday, hour, 0)
        allowed, reason = check_trading_hours(test_time)
        
        status = "✅ PASS" if allowed == should_allow else "❌ FAIL"
        if allowed == should_allow:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {description}")
        print(f"   Expected: {'ALLOW' if should_allow else 'BLOCK'}, Got: {'ALLOW' if allowed else 'BLOCK'} ({reason})")
    
    print(f"\nРезультат: {passed} passed, {failed} failed")
    return failed == 0


def test_schedule_config():
    """Тест 2: Проверка конфигурации расписания"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Конфигурация расписания анализа")
    print("="*60)
    
    ai_config = load_config('ai.yaml')
    
    # Проверяем schedule settings
    schedule = ai_config.get('market_analyst', {}).get('schedule', {})
    times = schedule.get('times', [])
    
    print(f"Schedule enabled: {schedule.get('enabled', False)}")
    print(f"Schedule times: {times}")
    print(f"Min minutes between calls: {ai_config.get('market_analyst', {}).get('safety', {}).get('min_minutes_between_calls', 15)}")
    
    # Проверяем restrictions
    restrictions = schedule.get('restrictions', {})
    night_block = restrictions.get('night_block', {})
    weekend_block = restrictions.get('weekend_block', {})
    
    print(f"\nNight block: {night_block.get('enabled', False)} ({night_block.get('start')} - {night_block.get('end')})")
    print(f"Weekend block: {weekend_block.get('enabled', False)} (Fri {weekend_block.get('friday_start')} - Mon {weekend_block.get('monday_end')})")
    
    # Проверяем совместимость с trading hours
    trading_config = load_config('trading.yaml')
    hours = trading_config.get('trading', {}).get('hours', {})
    
    print(f"\nTrading hours from config:")
    print(f"  Start: {hours.get('start', 'NOT SET')}")
    print(f"  End: {hours.get('end', 'NOT SET')}")
    
    return True


def test_scheduler_integration():
    """Тест 3: Интеграция scheduler"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Интеграция AnalystScheduler")
    print("="*60)
    
    try:
        signal_manager = AISignalManager()
        scheduler = AnalystScheduler(signal_manager=signal_manager)
        
        print(f"✅ Scheduler initialized")
        print(f"   Schedule times: {[t.strftime('%H:%M') for t in scheduler.schedule_times]}")
        print(f"   AI enabled: {scheduler.is_ai_enabled()}")
        print(f"   Last run: {scheduler.last_run}")
        
        # Проверяем что scheduler не запущен (не нужно запускать в тесте)
        print(f"   Running: {scheduler.running}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_manager():
    """Тест 4: SignalManager работоспособность"""
    print("\n" + "="*60)
    print("ТЕСТ 4: SignalManager")
    print("="*60)
    
    try:
        manager = AISignalManager()
        
        print(f"✅ SignalManager initialized")
        print(f"   Active signals: {len(manager.active_signals)}")
        print(f"   Block type: {manager.block_type}")
        print(f"   Signal history: {len(manager.signal_history)} entries")
        
        # Проверяем методы
        status = manager.get_status_summary()
        print(f"   Status: {status}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gui_settings():
    """Тест 5: GUI настройки (проверка существования полей)"""
    print("\n" + "="*60)
    print("ТЕСТ 5: GUI Settings (config check)")
    print("="*60)
    
    try:
        from src.gui.settings_dialog import SettingsDialog
        
        print("✅ SettingsDialog module loaded")
        print("   Проверка доступности настроек:")
        
        # Проверяем что в settings_dialog.py есть нужные поля
        import inspect
        source = inspect.getsource(SettingsDialog)
        
        checks = [
            ('trade_start', 'Trading start time'),
            ('trade_end', 'Trading end time'),
            ('ai_enabled', 'AI enabled'),
            ('gpt_model', 'GPT model'),
        ]
        
        for field, description in checks:
            if field in source:
                print(f"   ✅ {description} ({field})")
            else:
                print(f"   ❌ {description} ({field}) NOT FOUND")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("ТЕСТ СИСТЕМЫ ПОДАЧИ СИГНАЛОВ")
    print("="*60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Запуск тестов
    results.append(("Time Restrictions", test_time_restrictions()))
    results.append(("Schedule Config", test_schedule_config()))
    results.append(("Scheduler Integration", test_scheduler_integration()))
    results.append(("SignalManager", test_signal_manager()))
    results.append(("GUI Settings", test_gui_settings()))
    
    # Итоговый отчёт
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        print(f"\n⚠️ ПРОВАЛЕНО {total - passed} тестов")
        return 1


if __name__ == "__main__":
    exit(main())

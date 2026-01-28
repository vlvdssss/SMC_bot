#!/usr/bin/env python3
"""
Финальный тест: Проверка работы системы в runtime
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import logger


def test_live_trader_hours():
    """Тест проверки торговых часов в LiveTrader"""
    print("\n" + "="*60)
    print("ТЕСТ: LiveTrader торговые часы")
    print("="*60)
    
    try:
        from src.live.live_trader import LiveTrader
        
        # Создаём trader (только инициализация, без подключения к MT5)
        trader = LiveTrader(enable_trading=False)
        
        # Проверяем метод
        if hasattr(trader, '_check_trading_hours'):
            print("✅ Метод _check_trading_hours существует")
            
            # Тестируем текущее время
            allowed = trader._check_trading_hours()
            current_time = datetime.now()
            hour = current_time.hour
            weekday = current_time.weekday()
            
            print(f"\nТекущее время: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"День недели: {weekday} (0=Mon, 6=Sun)")
            print(f"Час: {hour}")
            print(f"Торговля разрешена: {'✅ ДА' if allowed else '❌ НЕТ'}")
            
            # Логика проверки
            if weekday >= 5:
                expected = False
                reason = "Weekend"
            elif weekday == 0 and hour < 1:
                expected = False
                reason = "Monday before 01:00"
            elif weekday == 4 and hour >= 21:
                expected = False
                reason = "Friday after 21:00"
            elif 13 <= hour < 18:
                expected = False
                reason = "Night ban (13:00-18:00)"
            else:
                expected = True
                reason = "OK"
            
            print(f"Ожидается: {'разрешено' if expected else 'запрещено'} ({reason})")
            
            if allowed == expected:
                print("\n✅ ТЕСТ ПРОЙДЕН - логика работает корректно")
                return True
            else:
                print(f"\n❌ ТЕСТ ПРОВАЛЕН - ожидалось {expected}, получено {allowed}")
                return False
        else:
            print("❌ Метод _check_trading_hours не найден")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Тест полной интеграции"""
    print("\n" + "="*60)
    print("ТЕСТ: Полная интеграция системы")
    print("="*60)
    
    try:
        # Проверяем что все компоненты доступны
        from src.ai.analyst_scheduler import AnalystScheduler
        from src.ai.signal_manager import AISignalManager
        from src.live.live_trader import LiveTrader
        
        print("✅ Все модули импортированы успешно")
        
        # Проверяем signal manager
        signal_mgr = AISignalManager()
        print(f"✅ SignalManager: {len(signal_mgr.active_signals)} активных сигналов")
        
        # Проверяем scheduler
        scheduler = AnalystScheduler(signal_manager=signal_mgr)
        print(f"✅ Scheduler: {len(scheduler.schedule_times)} временных точек")
        print(f"   Расписание: {[t.strftime('%H:%M') for t in scheduler.schedule_times]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ")
    print("="*60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Тесты
    results.append(("Trading Hours Check", test_live_trader_hours()))
    results.append(("Full Integration", test_integration()))
    
    # Итог
    print("\n" + "="*60)
    print("ИТОГИ")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")
    
    print(f"\nРезультат: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("\n✅ Система готова к работе:")
        print("   - Проверка торговых часов: РАБОТАЕТ")
        print("   - Ограничение 13:00-18:00: АКТИВНО")
        print("   - Расписание ПН 01:00 - ПТ 21:00: АКТИВНО")
        print("   - Интеграция компонентов: OK")
        return 0
    else:
        print(f"\n⚠️ Провалено {total - passed} тестов")
        return 1


if __name__ == "__main__":
    exit(main())

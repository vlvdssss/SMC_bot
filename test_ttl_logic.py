"""
Тест TTL логики сигналов
Проверяет правильность работы signal_ttl настроек
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.ai.signal_manager import AISignalManager, AISignal

def load_config(filename):
    """Загрузить конфиг файл"""
    config_path = Path(__file__).parent / "config" / filename
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_ttl_expire():
    print("\n" + "="*80)
    print("🔍 ТЕСТ TTL ЛОГИКИ СИГНАЛОВ")
    print("="*80 + "\n")
    
    # Загружаем конфиг
    trading_config = load_config('trading.yaml')
    ai_config = load_config('ai.yaml')
    
    configs = {
        'trading.yaml': trading_config,
        'ai.yaml': ai_config
    }
    
    ttl_config = trading_config.get('trading', {}).get('signal_ttl', {})
    
    print("📋 КОНФИГУРАЦИЯ TTL:")
    print(f"   • Enabled: {ttl_config.get('enabled', False)}")
    print(f"   • TTL Minutes: {ttl_config.get('ttl_minutes', 60)}")
    print(f"   • Auto-requery on expire: {ttl_config.get('auto_requery_on_expire', False)}")
    print(f"   • Auto-requery on close: {ttl_config.get('auto_requery_on_close', False)}")
    print()
    
    # Создаем AISignalManager
    signal_manager = AISignalManager()
    
    # Создаем тестовый сигнал
    print("✅ Создаем тестовый сигнал (BUY XAUUSD)...")
    
    created_time = datetime.now() - timedelta(minutes=65)
    expires_time = created_time + timedelta(minutes=60)
    
    test_signal = AISignal(
        id=f"XAUUSD_BUY_{int(time.time())}",
        symbol="XAUUSD",
        type="BUY",
        entry_price=2650.00,
        stop_loss=2640.00,
        take_profit=2670.00,
        trigger_time=created_time.isoformat(),
        reasoning="Test signal for TTL check",
        confidence=85,
        risk_reward=2.0,
        created_at=created_time.isoformat(),
        expires_at=expires_time.isoformat(),  # Истек 5 минут назад!
        priority=1,
        status="pending"
    )
    
    signal_manager.active_signals.append(test_signal)
    print(f"   Signal ID: {test_signal.id}")
    print(f"   Created: 65 minutes ago (EXPIRED!)")
    print(f"   Status: {test_signal.status}")
    print()
    
    # Проверяем сигнал
    print("🔍 Проверка is_expired():")
    is_expired = test_signal.is_expired()
    print(f"   Result: {is_expired}")
    print(f"   Expected: True (expires_at in the past)")
    print()
    
    # Запускаем cleanup
    print("🧹 Запускаем _cleanup_expired_signals()...")
    signal_manager._cleanup_expired_signals()
    
    remaining = len([s for s in signal_manager.active_signals if s.status == "pending"])
    print(f"   Remaining pending signals: {remaining}")
    print(f"   Expected: 0 (expired signal should be removed)")
    print()
    
    # Тест 2: Свежий сигнал
    print("="*80)
    print("✅ Создаем СВЕЖИЙ сигнал (5 минут назад)...")
    
    created_time_fresh = datetime.now() - timedelta(minutes=5)
    expires_time_fresh = created_time_fresh + timedelta(minutes=60)
    
    fresh_signal = AISignal(
        id=f"EURUSD_SELL_{int(time.time())}",
        symbol="EURUSD",
        type="SELL",
        entry_price=1.0500,
        stop_loss=1.0550,
        take_profit=1.0450,
        trigger_time=created_time_fresh.isoformat(),
        reasoning="Fresh test signal",
        confidence=90,
        risk_reward=1.5,
        created_at=created_time_fresh.isoformat(),
        expires_at=expires_time_fresh.isoformat(),  # Еще 55 минут
        priority=2,
        status="pending"
    )
    
    signal_manager.active_signals.append(fresh_signal)
    print(f"   Signal ID: {fresh_signal.id}")
    print(f"   Created: 5 minutes ago (VALID)")
    print(f"   Status: {fresh_signal.status}")
    print()
    
    # Проверяем
    print("🔍 Проверка is_expired():")
    is_expired_fresh = fresh_signal.is_expired()
    print(f"   Result: {is_expired_fresh}")
    print(f"   Expected: False (expires_at in the future)")
    print()
    
    # Cleanup
    print("🧹 Запускаем _cleanup_expired_signals()...")
    signal_manager._cleanup_expired_signals()
    
    remaining_after = len([s for s in signal_manager.active_signals if s.status == "pending"])
    print(f"   Remaining pending signals: {remaining_after}")
    print(f"   Expected: 1 (fresh signal should remain)")
    print()
    
    # Итоги
    print("="*80)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТА:")
    print("="*80)
    
    tests_passed = 0
    tests_total = 4
    
    # Test 1: Expired signal detected
    if is_expired:
        print("✅ Test 1: Expired signal detected correctly")
        tests_passed += 1
    else:
        print("❌ Test 1: FAILED - Expired signal not detected")
    
    # Test 2: Expired signal removed
    if remaining == 0:
        print("✅ Test 2: Expired signal removed from active_signals")
        tests_passed += 1
    else:
        print(f"❌ Test 2: FAILED - {remaining} expired signals still present")
    
    # Test 3: Fresh signal not expired
    if not is_expired_fresh:
        print("✅ Test 3: Fresh signal not marked as expired")
        tests_passed += 1
    else:
        print("❌ Test 3: FAILED - Fresh signal incorrectly expired")
    
    # Test 4: Fresh signal remains
    if remaining_after == 1:
        print("✅ Test 4: Fresh signal remains in active_signals")
        tests_passed += 1
    else:
        print(f"❌ Test 4: FAILED - Expected 1 signal, got {remaining_after}")
    
    print()
    print(f"🎯 SCORE: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED! TTL Logic working correctly!")
    else:
        print(f"⚠️  {tests_total - tests_passed} test(s) failed")
    
    print("="*80 + "\n")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = test_ttl_expire()
    sys.exit(0 if success else 1)

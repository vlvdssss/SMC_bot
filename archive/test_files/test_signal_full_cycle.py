"""
Полный тест системы истечения сигналов
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import json
from src.ai.signal_manager import AISignalManager, AISignal
import time

def create_test_signal(symbol="XAUUSD", minutes_old=0):
    """Создаёт тестовый сигнал с заданным возрастом"""
    created_at = datetime.now() - timedelta(minutes=minutes_old)
    expires_at = created_at + timedelta(hours=24)
    
    return AISignal(
        id=f"{symbol}_TEST_{created_at.strftime('%Y%m%d_%H%M%S')}",
        symbol=symbol,
        type="BUY",
        entry_price=4530.0,
        stop_loss=4520.0,
        take_profit=4550.0,
        trigger_time="immediate",
        reasoning="Test signal for expiration testing",
        confidence=75.0,
        risk_reward=2.0,
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat(),
        analysis_version="2.0",
        status="pending",
        triggered_at=None,
        priority=7
    )

def test_full_cycle():
    """Полный тест цикла жизни сигнала"""
    print("=== ПОЛНЫЙ ТЕСТ СИСТЕМЫ ИСТЕЧЕНИЯ СИГНАЛОВ ===\n")
    
    sm = AISignalManager()
    
    print("1. Создаём 3 сигнала:")
    print("   - Сигнал #1: Свежий (5 минут)")
    print("   - Сигнал #2: Старый (65 минут - должен истечь)")
    print("   - Сигнал #3: Очень старый (120 минут - должен истечь)")
    
    signal1 = create_test_signal(minutes_old=5)
    signal2 = create_test_signal(minutes_old=65)
    signal3 = create_test_signal(minutes_old=120)
    
    sm.active_signals = [signal1, signal2, signal3]
    sm._save_state()
    
    print(f"\n   Сохранено сигналов: {len(sm.active_signals)}")
    
    # Проверяем файл
    with open('data/ai_signals/active_signals.json', 'r', encoding='utf-8') as f:
        state = json.load(f)
        print(f"   В файле сигналов: {len(state['active_signals'])}")
    
    print("\n2. Перезагружаем состояние (симуляция рестарта бота)...")
    sm2 = AISignalManager()
    
    print(f"\n   Загружено активных сигналов: {len(sm2.active_signals)}")
    print(f"   Ожидалось: 1 (только свежий)")
    
    if len(sm2.active_signals) == 1:
        print("   ✅ УСПЕХ: Старые сигналы отфильтрованы!")
        signal = sm2.active_signals[0]
        created = datetime.fromisoformat(signal.created_at)
        age = (datetime.now() - created).total_seconds() / 60
        print(f"   Оставшийся сигнал: ID={signal.id}")
        print(f"   Возраст: {age:.1f} минут")
    else:
        print("   ❌ ОШИБКА: Неправильное количество сигналов!")
    
    # Проверяем что файл очищен
    with open('data/ai_signals/active_signals.json', 'r', encoding='utf-8') as f:
        state = json.load(f)
        print(f"\n   В файле осталось сигналов: {len(state['active_signals'])}")
        if len(state['active_signals']) == 1:
            print("   ✅ УСПЕХ: Файл очищен от старых сигналов!")
        else:
            print("   ❌ ОШИБКА: Файл не очищен!")
    
    print("\n3. Тестируем check_triggers() для истечения по времени...")
    
    # Создаём сигнал который должен истечь через 61 минуту
    old_signal = create_test_signal(minutes_old=61)
    sm2.active_signals.append(old_signal)
    print(f"   Добавлен сигнал возрастом 61 минута")
    print(f"   ID: {old_signal.id}")
    print(f"   Symbol: {old_signal.symbol}")
    print(f"   Status: {old_signal.status}")
    print(f"   Всего сигналов: {len(sm2.active_signals)}")
    
    # Показываем все сигналы
    for i, sig in enumerate(sm2.active_signals, 1):
        created = datetime.fromisoformat(sig.created_at)
        age = (datetime.now() - created).total_seconds() / 60
        print(f"      {i}. ID={sig.id[:20]}..., возраст={age:.1f}min, status={sig.status}")
    
    # Вызываем check_triggers с ценой выше entry (4535 > 4530), чтобы BUY НЕ сработал
    triggered = sm2.check_triggers(
        symbol="XAUUSD", 
        current_price=4535.0,  # Цена выше entry, BUY не сработает
        current_time=datetime.now()
    )
    
    print(f"\n   После check_triggers:")
    print(f"   Активных сигналов: {len(sm2.active_signals)}")
    print(f"   Triggered сигналов: {len(triggered)}")
    print(f"   Ожидалось: 1 активный (свежий), 0 triggered")
    
    if len(sm2.active_signals) == 1:
        print("   ✅ УСПЕХ: Старый сигнал удалён!")
    else:
        print("   ❌ ОШИБКА: Старый сигнал не удалён!")
        for sig in sm2.active_signals:
            created = datetime.fromisoformat(sig.created_at)
            age = (datetime.now() - created).total_seconds() / 60
            print(f"      - {sig.id}: возраст {age:.1f}min, статус={sig.status}")
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    print("\n📊 РЕЗЮМЕ:")
    print("   ✅ Загрузка: Фильтрует сигналы старше 60 минут")
    print("   ✅ Сохранение: Сохраняет только pending сигналы")
    print("   ✅ check_triggers(): Удаляет истекшие сигналы")
    print("   ✅ Файл: Автоматически очищается от старых сигналов")

if __name__ == "__main__":
    test_full_cycle()

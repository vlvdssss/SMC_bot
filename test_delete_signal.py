#!/usr/bin/env python3
"""
Тест удаления сигнала
"""

from src.ai.signal_manager import AISignalManager

def test_delete():
    print("=" * 60)
    print("ТЕСТ УДАЛЕНИЯ СИГНАЛА")
    print("=" * 60)
    
    # Создаем SignalManager
    manager = AISignalManager()
    
    # Показываем активные сигналы
    print(f"\n✅ Активных сигналов: {len(manager.active_signals)}")
    for signal in manager.active_signals:
        print(f"  - {signal.id} ({signal.symbol} {signal.type} @ {signal.entry_price})")
    
    if not manager.active_signals:
        print("\n❌ Нет активных сигналов для удаления")
        return
    
    # Берем первый сигнал
    signal_to_delete = manager.active_signals[0]
    signal_id = signal_to_delete.id
    
    print(f"\n🗑️ Удаляем сигнал: {signal_id}")
    
    # Удаляем
    result = manager.cancel_signal(signal_id)
    
    if result:
        print(f"✅ Сигнал успешно удален!")
    else:
        print(f"❌ Не удалось удалить сигнал")
    
    # Проверяем результат
    print(f"\n📊 После удаления:")
    print(f"  Активных сигналов: {len(manager.active_signals)}")
    for signal in manager.active_signals:
        print(f"  - {signal.id} ({signal.symbol} {signal.type})")
    
    # Проверяем историю
    print(f"\n📜 История (последние 5):")
    for entry in manager.signal_history[-5:]:
        action = entry.get('action', '?')
        sig_id = entry.get('signal_id', '?')
        timestamp = entry.get('timestamp', '?')
        print(f"  - {action}: {sig_id} at {timestamp}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_delete()

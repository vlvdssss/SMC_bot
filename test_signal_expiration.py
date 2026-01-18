"""
Тестирование системы истечения сигналов
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import json
from src.ai.signal_manager import AISignalManager
import yaml

def test_signal_expiration():
    print("=== Тест системы истечения сигналов ===\n")
    
    # Создаём signal manager (config загружается внутри)
    sm = AISignalManager()
    
    # Проверяем текущее состояние
    print(f"1. Активных сигналов сейчас: {len(sm.active_signals)}")
    
    # Показываем каждый сигнал
    for i, signal in enumerate(sm.active_signals, 1):
        created = datetime.fromisoformat(signal.created_at)
        now = datetime.now()
        age_minutes = (now - created).total_seconds() / 60
        
        print(f"\n   Сигнал #{i}:")
        print(f"   - ID: {signal.id}")
        print(f"   - Символ: {signal.symbol}")
        print(f"   - Тип: {signal.type}")
        print(f"   - Статус: {signal.status}")
        print(f"   - Создан: {signal.created_at[11:19]}")
        print(f"   - Возраст: {age_minutes:.1f} минут")
        print(f"   - Истёк (24h): {signal.is_expired()}")
        print(f"   - Цена входа: {signal.entry_price}")
        print(f"   - Истекает: {signal.expires_at[11:19]}")
    
    # Проверяем файл состояния
    signals_file = Path('data/ai_signals/active_signals.json')
    if signals_file.exists():
        with open(signals_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
            file_signals = state.get('active_signals', [])
            print(f"\n2. Сигналов в файле: {len(file_signals)}")
            
            for i, sig in enumerate(file_signals, 1):
                print(f"\n   Файл сигнал #{i}:")
                print(f"   - ID: {sig.get('id')}")
                print(f"   - Статус: {sig.get('status')}")
                print(f"   - Создан: {sig.get('created_at', 'N/A')[11:19]}")
    
    print("\n3. Настройки:")
    validity = sm.config.get('market_analyst', {}).get('signals', {}).get('validity_minutes', 60)
    print(f"   - Signal validity: {validity} минут")
    
    print("\n=== Тест завершён ===")

if __name__ == "__main__":
    test_signal_expiration()

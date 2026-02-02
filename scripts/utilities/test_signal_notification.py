#!/usr/bin/env python3
"""
Тестирование отправки сигнала в Telegram с кнопкой удаления
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from src.monitoring.telegram_notifier import TelegramNotifier
from src.core.bot_manager import BotManager


def test_send_signal():
    """Тест отправки сигнала с кнопкой удаления"""
    print("=" * 60)
    print("ТЕСТ: Отправка сигнала в Telegram")
    print("=" * 60)
    
    # Получаем Telegram notifier из BotManager
    bot_manager = BotManager()
    
    if not bot_manager.telegram or not bot_manager.telegram.enabled:
        print("❌ Telegram не настроен или отключен")
        return False
    
    telegram = bot_manager.telegram
    
    # Тестовые данные сигнала
    print("\n📤 Отправка тестового сигнала...")
    result = telegram.send_signal(
        symbol="XAUUSD",
        direction="SELL",
        entry=2776.50000,
        sl=2781.00000,
        tp=2766.00000,
        confidence=80.0,
        quality="VERY_HIGH",
        accuracy="HIGH",
        lot_multiplier=1.00,
        signal_id="test_signal_001"
    )
    
    if result:
        print("✅ Сигнал успешно отправлен!")
        print("\n📱 Проверьте Telegram:")
        print("   - Сообщение должно содержать информацию о сигнале")
        print("   - Должна быть кнопка '🗑️ Удалить'")
        print("   - При нажатии кнопка должна удалить сообщение")
    else:
        print("❌ Не удалось отправить сигнал")
        print("   Проверьте логи для деталей")
    
    return result


if __name__ == "__main__":
    success = test_send_signal()
    sys.exit(0 if success else 1)

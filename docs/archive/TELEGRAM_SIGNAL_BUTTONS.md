# Telegram Signal Notifications with Delete Button

## Что изменилось

Добавлена функциональность отправки AI сигналов в Telegram с интерактивной кнопкой удаления.

## Изменения в коде

### 1. `src/monitoring/telegram_notifier.py`
- **Добавлен импорт `json`** для работы с InlineKeyboard
- **Новый метод `send_signal()`** - отправка сигнала с кнопкой удаления
  - Параметры: symbol, direction, entry, sl, tp, confidence, quality, accuracy, lot_multiplier, signal_id
  - Форматирует сигнал как HTML сообщение
  - Добавляет InlineKeyboard с кнопкой "🗑️ Удалить"
  - Callback data: `delete_signal_{signal_id}`

### 2. `src/ai/signal_manager_v3.py`
- **Добавлена отправка Telegram уведомления** после создания сигнала
- Вызывает `telegram.send_signal()` с параметрами из SignalDecision
- Передаёт: quality, accuracy, lot_multiplier из GPT V3 оценки

### 3. `src/monitoring/telegram_bot.py`
- **Добавлен импорт `CallbackQueryHandler`**
- **Новый метод `handle_callback()`** - обработчик inline кнопок
  - Обрабатывает callback `delete_signal_*`
  - Удаляет сообщение при нажатии кнопки "Удалить"
- **Обновлен `start_polling()`** - зарегистрирован CallbackQueryHandler

### 4. `config/telegram.yaml`
- **Добавлен ключ `ai_signal: true`** в секцию notify
- Управляет отправкой уведомлений о новых AI сигналах

## Формат уведомления

```
🤖 SELL XAUUSD 💎 VERY_HIGH

💵 Entry: 2776.50000
🛑 Stop Loss: 2781.00000
🎯 Take Profit: 2766.00000

🧠 Confidence: 80.0%
📊 GPT V3: HIGH accuracy, VERY_HIGH quality, lot 1.00x

⏰ 2026-02-02 01:32:37

[🗑️ Удалить] <- Inline кнопка
```

## Эмодзи для качества

- **LOW**: ⚠️
- **NORMAL**: ✅
- **HIGH**: 🔥
- **VERY_HIGH**: 💎

## Использование

### Автоматическая отправка
При создании сигнала через `SignalManagerV3.process_decision_v3()` уведомление отправляется автоматически, если:
- Telegram включен (`telegram.enabled: true`)
- Уведомления сигналов включены (`notify.ai_signal: true`)

### Ручная отправка
```python
from src.core.bot_manager import BotManager

bot_manager = BotManager()
bot_manager.telegram.send_signal(
    symbol="XAUUSD",
    direction="BUY",
    entry=2775.50,
    sl=2770.00,
    tp=2785.00,
    confidence=85.0,
    quality="HIGH",
    accuracy="VERY_HIGH",
    lot_multiplier=1.5,
    signal_id="signal_001"
)
```

### Кнопка "Удалить"
- При нажатии на кнопку "🗑️ Удалить" сообщение удаляется из чата
- Callback обрабатывается в `telegram_bot.py`
- Логируется в лог: `[Telegram] Signal message deleted: {signal_id}`

## Тестирование

Запустите тест:
```bash
python test_signal_notification.py
```

Проверьте в Telegram:
1. Должно прийти сообщение с сигналом SELL XAUUSD
2. Под сообщением кнопка "🗑️ Удалить"
3. При нажатии кнопки сообщение удаляется

## Troubleshooting

### Сигнал не отправляется
- Проверьте `config/telegram.yaml`: `notify.ai_signal: true`
- Проверьте логи: `[Telegram] Signal notification sent for {symbol}`
- Проверьте наличие bot_token и chat_id

### Кнопка не работает
- Убедитесь, что Telegram бот запущен (`enable_bot: true`)
- Проверьте, что `CallbackQueryHandler` зарегистрирован в `start_polling()`
- Проверьте логи при нажатии кнопки

### Сообщение не удаляется
- Проверьте права бота в Telegram
- Проверьте callback_data в логах
- Убедитесь, что signal_id передан корректно

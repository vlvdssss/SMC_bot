# Delete Signal Feature - Documentation

## Что изменилось

Добавлена полная интеграция кнопки "Delete Signal" как в GUI программе, так и в Telegram с синхронизацией между ними.

## Изменения

### 1. GUI - Кнопка Delete Signal
**Файл:** [src/gui/app.py](../src/gui/app.py#L775-L810)

#### Что добавлено:
- **Кнопка "🗑️ Delete Signal"** в карточке каждого активного сигнала
- **Красный цвет** (#e74c3c) с hover эффектом (#c0392b)
- **Метод `_delete_signal(signal_id)`** для обработки удаления:
  - Вызывает `signal_manager.cancel_signal(signal_id)`
  - Отправляет уведомление в Telegram
  - Обновляет GUI (`refresh_summary()`)
  - Показывает messagebox с подтверждением

#### Код кнопки:
```python
delete_btn = tk.Button(card_content,
                      text="🗑️ Delete Signal",
                      font=('Arial', 10, 'bold'),
                      bg=Colors.ERROR,
                      fg='white',
                      activebackground='#c0392b',
                      activeforeground='white',
                      cursor='hand2',
                      relief='flat',
                      padx=15,
                      pady=8,
                      command=lambda sid=signal.id: self._delete_signal(sid))
```

### 2. Telegram - Синхронизация удаления
**Файл:** [src/monitoring/telegram_bot.py](../src/monitoring/telegram_bot.py#L70-L97)

#### Что изменено:
Обработчик `handle_callback()` теперь:
1. **Удаляет сигнал** из SignalManager через `cancel_signal()`
2. **Удаляет сообщение** из Telegram чата
3. **Логирует действие**
4. **Показывает ошибку** если сигнал не найден

#### Код обработчика:
```python
if bot_manager.signal_manager.cancel_signal(signal_id):
    logger.info(f"[Telegram] Signal {signal_id} cancelled from SignalManager")
    await query.message.delete()
    logger.info(f"[Telegram] Signal message deleted: {signal_id}")
else:
    logger.warning(f"[Telegram] Signal {signal_id} not found")
    await query.message.edit_text("⚠️ Сигнал не найден или уже удалён")
```

## Как это работает

### Сценарий 1: Удаление через GUI
1. Пользователь нажимает "🗑️ Delete Signal" в программе
2. Вызывается `_delete_signal(signal_id)`
3. Сигнал удаляется из `signal_manager.active_signals`
4. Статус сигнала меняется на "cancelled"
5. Отправляется уведомление в Telegram: "🗑️ Signal Deleted"
6. GUI обновляется - сигнал исчезает из ACTIVE SIGNALS
7. Сигнал добавляется в RECENT HISTORY с действием "cancelled"

### Сценарий 2: Удаление через Telegram
1. Пользователь нажимает "🗑️ Удалить" в Telegram
2. Telegram callback вызывает `cancel_signal(signal_id)`
3. Сигнал удаляется из `signal_manager.active_signals`
4. Статус сигнала меняется на "cancelled"
5. Сообщение удаляется из Telegram чата
6. **GUI автоматически обновится** при следующем refresh (каждые 2-3 секунды)

## Синхронизация

### GUI → Telegram
- При удалении через GUI отправляется сообщение в Telegram
- Пользователь видит уведомление о том, что сигнал удалён

### Telegram → GUI
- При удалении через Telegram сигнал удаляется из SignalManager
- GUI обновляется автоматически при следующем цикле refresh
- Сигнал исчезает из ACTIVE SIGNALS

## Логирование

### Удаление через GUI:
```
[GUI] Signal XAUUSD_20260202_013000 cancelled successfully
[Telegram] 📤 Sending to chat_id=543258309...
[Telegram] ✅ Message sent successfully: 🗑️ Signal Deleted...
```

### Удаление через Telegram:
```
[Telegram] Signal XAUUSD_20260202_013000 cancelled from SignalManager
[Telegram] Signal message deleted: XAUUSD_20260202_013000
[AI-Signal] Cancelled: XAUUSD_20260202_013000
```

## История сигнала

После удаления сигнал добавляется в историю:
```json
{
  "action": "cancelled",
  "signal_id": "XAUUSD_20260202_013000",
  "timestamp": "2026-02-02T01:30:00"
}
```

## Визуальный вид

### GUI - До:
```
┌─────────────────────────────────────┐
│ SELL  XAUUSD              LOW       │
│─────────────────────────────────────│
│ ENTRY      STOP LOSS   TAKE PROFIT  │
│ 4735.00000 4740.00000  4725.00000   │
│                                     │
│ Confidence: 80%                     │
│ ████████████████░░░░                │
│                                     │
│ 💡 GPT V3: VERY_HIGH accuracy...   │
└─────────────────────────────────────┘
```

### GUI - После изменений:
```
┌─────────────────────────────────────┐
│ SELL  XAUUSD              LOW       │
│─────────────────────────────────────│
│ ENTRY      STOP LOSS   TAKE PROFIT  │
│ 4735.00000 4740.00000  4725.00000   │
│                                     │
│ Confidence: 80%                     │
│ ████████████████░░░░                │
│                                     │
│ 💡 GPT V3: VERY_HIGH accuracy...   │
│─────────────────────────────────────│
│     🗑️ Delete Signal               │  ← НОВАЯ КНОПКА
└─────────────────────────────────────┘
```

### Telegram - Сигнал с кнопкой:
```
🤖 SELL XAUUSD 💎 VERY_HIGH

💵 Entry: 4735.00000
🛑 Stop Loss: 4740.00000
🎯 Take Profit: 4725.00000

🧠 Confidence: 80.0%
📊 GPT V3: HIGH accuracy, VERY_HIGH quality, lot 1.00x

⏰ 2026-02-02 01:30:00

┌───────────────┐
│ 🗑️ Удалить   │  ← INLINE КНОПКА
└───────────────┘
```

## Troubleshooting

### Кнопка в GUI не работает
- Проверьте, что `bot_manager.signal_manager` инициализирован
- Проверьте логи: `[GUI] Signal {id} cancelled successfully`
- Убедитесь, что `refresh_summary()` вызывается после удаления

### Кнопка в Telegram не удаляет сигнал из программы
- Проверьте, что Telegram бот запущен (`enable_bot: true`)
- Проверьте логи: `[Telegram] Signal {id} cancelled from SignalManager`
- Убедитесь, что `CallbackQueryHandler` зарегистрирован

### Сигнал удалён, но всё ещё виден в GUI
- GUI обновляется каждые 2-3 секунды
- Подождите 1 цикл refresh или нажмите "Refresh" вручную
- Проверьте статус сигнала в `data/ai_signals/` - должен быть "cancelled"

## Тестирование

1. Запустите программу: `python main.py`
2. Дождитесь создания сигнала (или создайте тестовый)
3. **Тест GUI:** Нажмите "🗑️ Delete Signal" → Должно появиться messagebox
4. **Тест Telegram:** Нажмите "🗑️ Удалить" → Сообщение должно исчезнуть
5. Проверьте RECENT HISTORY - сигнал должен быть там с action="cancelled"

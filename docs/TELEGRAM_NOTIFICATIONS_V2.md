# Telegram Notifications v2.0 - Mode-Specific Messages

## 📋 Обзор

Обновленная система уведомлений в Telegram с отдельными форматами для каждого режима торговли:
- **Strategy + AI**: Стандартные уведомления о торговле
- **Pure AI Trading**: Детальные сообщения с объяснениями от GPT

## 🔄 Обновленные методы

### 1. `send_trade_opened()` ✅
Уведомление об открытии сделки

**Pure AI режим:**
- 🤖 Префикс "PURE AI: Сделка открыта"
- 💡 Конфиденс GPT в процентах (с эмодзи)
- 💭 Детальное объяснение от GPT (reasoning)
- 📊 Расчет Risk:Reward
- 🎯 Все уровни: Entry, TP, SL

**Strategy режим:**
- 📈 Стандартное "Сделка открыта"
- Символ, направление, лот
- Entry, TP, SL
- Время открытия

### 2. `send_trade_closed()` ✅
Уведомление о закрытии сделки

**Pure AI режим:**
- ✅/❌ Результат с эмодзи
- 💰 Профит с огнем при успехе
- 🎯 Причина закрытия (TP/SL/Manual)
- 📏 Пипсы и длительность

**Strategy режим:**
- Стандартный формат
- Профит, пипсы, длительность
- Без детального анализа

### 3. `send_startup()` ✅
Уведомление о запуске бота

**Pure AI режим:**
- 🤖 "Pure AI Trading запущен"
- ⏰ Интервал анализа (2 часа)
- 📊 Таймфрейм (15 минут)
- 🎯 Минимальный конфиденс
- 📉 Лимит сделок в день
- 🔒 Кулдаун между сделками

**Strategy режим:**
- 📈 "Strategy + AI"
- 🎯 Название стратегии
- 📊 Список инструментов

### 4. `send_shutdown()` ✅
Уведомление об остановке

**Pure AI режим:**
- 🤖 Итоговая статистика Pure AI
- 🔬 Количество GPT анализов
- 📡 Количество сигналов
- 🎯 Винрейт
- Детальная статистика сделок

**Strategy режим:**
- Стандартная итоговая статистика
- Баланс, профит, сделки

### 5. `send_daily_report()` ✅
Ежедневный отчет

**Pure AI режим:**
- 🤖 "Pure AI: Дневной отчет"
- 🔬 Количество GPT анализов
- 📡 Количество сигналов
- 💡 Средний конфиденс
- Полная статистика торговли

**Strategy режим:**
- Стандартный дневной отчет
- Баланс, профит, winrate, ROI

### 6. `send_periodic_report()` ✨ NEW
Периодический отчет (каждые 3 часа)

**Pure AI режим:**
- ⏰ Статус системы
- 📊 Сделки сегодня / лимит
- 🔬 AI активность (анализы, сигналы)
- ⏱️ Время следующего анализа
- 💡 Средний конфиденс

**Strategy режим:**
- 📈 Статус торговли
- 💰 Баланс и P&L
- ✅ Открытые позиции
- 🎯 Winrate

**Особенности:**
- Автоматическая защита от спама (не чаще раза в 3 часа)
- Использует `self.last_report_time` для отслеживания

### 7. `send_ai_analysis_update()` ✨ NEW
Уведомление об анализе GPT (только Pure AI)

**Формат:**
- 🔬 "Pure AI: Анализ завершен"
- 📊 Символ
- 📈/📉 Решение (BUY/SELL/HOLD)
- 🔥/✅/⚠️ Конфиденс с эмодзи (80%+/70%+/<70%)
- 💭 Объяснение GPT (до 300 символов)
- 🔄 Время следующего анализа

**Использование:**
```python
notifier.send_ai_analysis_update(
    symbol="XAUUSD",
    confidence=85.5,
    direction="BUY",
    reasoning="Сильный восходящий тренд на 15M, RSI показывает...",
    next_analysis_time="14:00"
)
```

## 📝 Примеры использования

### Открытие сделки - Pure AI
```python
notifier.send_trade_opened(
    symbol="XAUUSD",
    direction="BUY",
    lot=0.1,
    entry=2650.50,
    sl=2645.00,
    tp=2665.00,
    mode="pure_ai",
    reasoning="Технический анализ показывает сильный восходящий импульс...",
    confidence=85.5
)
```

### Запуск бота - Pure AI
```python
notifier.send_startup(
    mode="pure_ai",
    instruments=["XAUUSD", "EURUSD"],
    config={
        "min_confidence": 70,
        "max_trades_per_day": 5,
        "symbol_cooldown_hours": 2
    }
)
```

### Периодический отчет
```python
notifier.send_periodic_report(
    mode="pure_ai",
    stats={
        "balance": 10500.00,
        "daily_profit": 150.00,
        "trades_today": 2,
        "max_trades": 5,
        "analyses_today": 6,
        "signals_today": 3,
        "next_analysis": "14:00",
        "avg_confidence": 78.5
    }
)
```

## 🔧 Технические детали

### Новые параметры класса
```python
class TelegramNotifier:
    def __init__(self, ...):
        self.last_report_time: Optional[datetime] = None  # Для периодических отчетов
```

### Эмодзи система

**Pure AI:**
- 🤖 Автономная торговля
- 🔬 GPT анализ
- 💡 Конфиденс/сигнал
- 🔥 Высокий конфиденс (≥80%)
- ✅ Хороший конфиденс (≥70%)
- ⚠️ Низкий конфиденс (<70%)

**Общие:**
- 📊 Данные/статистика
- 💰 Баланс/профит
- 📈 Рост/BUY
- 📉 Падение/SELL
- ✅ Успех
- ❌ Ошибка

## 🚀 Интеграция

### В PureAITrader
```python
# При анализе
self.notifier.send_ai_analysis_update(
    symbol=symbol,
    confidence=analysis.confidence,
    direction=analysis.direction,
    reasoning=analysis.reasoning,
    next_analysis_time=self._get_next_analysis_time()
)

# При открытии сделки
self.notifier.send_trade_opened(
    symbol=signal.symbol,
    direction=signal.direction,
    lot=lot_size,
    entry=signal.entry_price,
    sl=signal.stop_loss,
    tp=signal.take_profit,
    mode="pure_ai",
    reasoning=signal.reasoning,
    confidence=signal.confidence
)

# Периодический отчет (каждые 3 часа)
self.notifier.send_periodic_report(
    mode="pure_ai",
    stats=self._get_current_stats()
)
```

### В LiveTrader (Strategy режим)
```python
# При открытии сделки
self.notifier.send_trade_opened(
    symbol=position.symbol,
    direction=position.direction,
    lot=position.lot,
    entry=position.entry,
    sl=position.sl,
    tp=position.tp,
    mode="strategy"
)

# Периодический отчет
self.notifier.send_periodic_report(
    mode="strategy",
    stats=self._get_current_stats()
)
```

## 📊 Частота уведомлений

### Pure AI режим
- **Запуск/остановка**: При старте/стопе бота
- **Анализ**: Каждые 2 часа (12 раз/день)
- **Открытие сделки**: При каждом открытии (макс 5/день)
- **Закрытие сделки**: При каждом закрытии
- **Периодический отчет**: Каждые 3 часа (8 раз/день)
- **Дневной отчет**: 1 раз в день

### Strategy режим
- **Запуск/остановка**: При старте/стопе бота
- **Открытие/закрытие**: При каждой сделке
- **Периодический отчет**: Каждые 3 часа
- **Дневной отчет**: 1 раз в день

## ✅ Преимущества новой системы

1. **Прозрачность Pure AI**: Видны рассуждения GPT и конфиденс
2. **Раздельная статистика**: Четкое разделение метрик по режимам
3. **Регулярные обновления**: Отчеты каждые 3 часа
4. **Защита от спама**: Автоматическое ограничение частоты
5. **Детальная информация**: R:R, пипсы, длительность
6. **Эмодзи система**: Быстрая визуальная оценка

## 🔜 Следующие шаги

1. ✅ Обновить PureAITrader для вызова новых методов
2. ✅ Добавить периодические отчеты в основной цикл
3. ✅ Пересобрать EXE с новыми уведомлениями
4. 🔄 Протестировать на демо-счете
5. 📊 Собрать статистику использования

## 📖 См. также

- [PURE_AI_TRADING_MODE.md](PURE_AI_TRADING_MODE.md) - Описание Pure AI режима
- [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) - Настройка Telegram бота
- [MONITORING.md](MONITORING.md) - Система мониторинга

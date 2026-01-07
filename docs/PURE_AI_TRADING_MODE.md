# 🤖 Pure AI Trading Mode - Документация

## 📋 Обзор

**Pure AI Trading Mode** - новый режим работы бота, где все торговые решения принимает ChatGPT.

### Ключевые особенности:
- ✅ **Автоматический анализ каждые 2 часа** (00:00, 02:00, 04:00... 22:00)
- ✅ **Анализ скриншотов** графиков 5M, 15M, 1H
- ✅ **Учет новостей** с внешних источников
- ✅ **Готовые торговые сигналы** с entry/SL/TP от GPT
- ✅ **Дедупликация сигналов** (±0.1% от entry price)
- ✅ **Таймфрейм исполнения: 15M**
- ✅ **Символы: XAUUSD, EURUSD**

---

## 🎯 Два режима работы

### 1️⃣ Strategy + AI (классический)
```
Стратегия → Анализ 5M/15M/1H
    ↓
GPT → Валидация сигнала (фильтр новостей)
    ↓
Risk Manager → Контроль размера позиции
    ↓
Executor → Исполнение сделки
```

### 2️⃣ Pure AI Trading (новый)
```
Каждые 2 часа:
    ↓
GPT → Анализ скриншотов + новости + метрики
    ↓
Генерация готовых сигналов (entry/SL/TP)
    ↓
Signal Manager → Дедупликация + TTL
    ↓
LiveTrader → Мониторинг триггеров
    ↓
Executor → Исполнение при достижении цены
```

---

## 🚀 Как использовать

### Запуск через GUI

1. Открой приложение: `python main.py`
2. В панели управления найди **"🎯 Режим торговли"**
3. Выбери режим:
   - **⚡ Strategy + AI** - стратегия + GPT фильтр
   - **🤖 Pure AI Trading** - только GPT сигналы
4. Нажми **▶ СТАРТ**

### Переключение режимов

Можно переключать режимы **БЕЗ остановки бота**:
- Выбери другой режим → автоматически переключится
- Логи покажут текущий активный режим
- При переключении на Pure AI → автоматически запускается 2-часовой цикл

---

## ⚙️ Конфигурация

### Настройки Pure AI Trader

В файле `src/ai/pure_ai_trader.py`:

```python
class PureAITrader:
    SYMBOLS = ["XAUUSD", "EURUSD"]          # Торгуемые символы
    ANALYSIS_INTERVAL = 2 * 60 * 60         # 2 часа
    MIN_CONFIDENCE = 70                      # Минимум 70% уверенности
    MAX_TRADES_PER_DAY = 5                   # Максимум 5 сделок в день
    COOLDOWN_HOURS = 2                       # 2 часа пауза между сделками
```

### Требования

1. **OpenAI API Key** - обязателен
   - Установи в `.env`: `OPENAI_API_KEY=sk-...`
   - Или через GUI: **⚙ Настройки** → OpenAI API Key

2. **MetaTrader 5** - запущен и подключен

3. **Интернет** - для GPT и загрузки новостей

---

## 📊 Логика работы

### Цикл анализа (каждые 2 часа)

```python
1. Захват скриншотов:
   - XAUUSD: 5M, 15M, 1H
   - EURUSD: 5M, 15M, 1H

2. Расчет метрик:
   - ATR (волатильность)
   - Тренд (EMA 20/50/200)
   - Premium/Discount зоны
   - Ближайшие S/R уровни

3. Загрузка новостей:
   - Экономический календарь
   - Высокоимпактные события
   - Фильтрация по символам

4. Отправка GPT:
   Prompt: "Analyze XAUUSD on 5M/15M/1H timeframes.
            Consider: trend, structure, news impact.
            Provide: entry, SL, TP, confidence, reasoning."

5. Обработка ответа:
   {
     "signal": {
       "type": "BUY",
       "entry": 2665.50,
       "stop_loss": 2662.00,
       "take_profit": 2672.00,
       "confidence": 78,
       "reasoning": "Strong bullish structure..."
     },
     "trading_blocks": {
       "block_trading": false,
       "reason": null
     }
   }

6. Создание сигнала:
   - Проверка дубликатов (±0.1%)
   - Проверка confidence >= 70%
   - Установка TTL (24 часа)
   - Сохранение в Signal Manager

7. Мониторинг:
   - LiveTrader проверяет триггеры каждую минуту
   - При достижении entry price → исполнение
   - Или по времени (если указан trigger_time)
```

---

## 🛡️ Защитные механизмы

### 1. Дедупликация сигналов
```python
# Не создаем новый сигнал если:
- Symbol тот же
- Type (BUY/SELL) тот же
- Entry price ±0.1% от существующего
- Предыдущий сигнал активен

# Обновляем если:
- Новый confidence выше
- TP/SL улучшились
```

### 2. Лимиты торговли
```python
- MAX_TRADES_PER_DAY = 5
- COOLDOWN_HOURS = 2 (между сделками одного символа)
- MIN_CONFIDENCE = 70%
```

### 3. TTL сигналов
```python
- Каждый сигнал живет 24 часа
- Confidence decay со временем
- Автоочистка expired сигналов
```

### 4. Блокировки торговли
```python
# GPT может установить block:
- HARD_BLOCK: полный запрет (risk 0.0x)
- SOFT_BLOCK: только high confidence >70% (risk 0.3x)
- WARNING: снижение риска (risk 0.5x)
- BIAS: легкое предупреждение (risk 0.8x)
```

---

## 📈 Ожидаемая производительность

### Pure AI Mode (прогноз)
```
Анализов в день: 12 (каждые 2 часа)
Сигналов в день: 2-5 (с учетом фильтров)
Винрейт: 60-70% (GPT видит больше контекста)
R:R: 1:1.5 (быстрые сделки на 15M)
Затраты на GPT: ~$0.50/день (~$15/месяц)
```

### Strategy + AI Mode (текущий)
```
Сигналов в день: 2-5
Винрейт: 55-65%
R:R: 1:2
Затраты на GPT: $0-5/месяц (только фильтр)
```

---

## 🔧 Troubleshooting

### Pure AI Trader не запускается

**Ошибка:** "Pure AI Trader не инициализирован"

**Решение:**
1. Проверь `OPENAI_API_KEY` в `.env`
2. Перезапусти приложение
3. Проверь логи: `logs/test_log.txt`

### Сигналы не создаются

**Возможные причины:**
1. **Confidence < 70%** - GPT не уверен
2. **Дубликат** - похожий сигнал уже активен
3. **Лимит достигнут** - 5 сделок за день
4. **Cooldown** - 2 часа после последней сделки

**Решение:**
- Смотри логи: `[PureAI]` метки
- Проверь активные сигналы в GUI
- Дождись следующего цикла (2 часа)

### Высокие затраты на GPT

**Проблема:** >$1/день на GPT API

**Решение:**
1. Уменьши частоту: `ANALYSIS_INTERVAL = 3 * 60 * 60` (3 часа)
2. Используй `gpt-4o-mini` вместо `gpt-4o`
3. Ограничь символы: только `XAUUSD`

---

## 📝 Логи и мониторинг

### Ключевые логи

```log
[PureAI] Pure AI Trader initialized
[PureAI] Symbols: XAUUSD, EURUSD
[PureAI] Analysis every 2 hours

[PureAI] 🧠 Starting analysis cycle at 2026-01-07 10:00:00
[PureAI] 📊 Analyzing XAUUSD...
[PureAI] XAUUSD → Sentiment: BULLISH, Confidence: 78%
[PureAI] ✅ XAUUSD BUY signal created
         Entry: 2665.50, SL: 2662.00, TP: 2672.00
         Confidence: 78%, R:R: 2.14
         Reason: Strong bullish structure + discount zone

[AI-Signal] Triggered: XAUUSD_20260107_100015
[Trade] XAUUSD BUY 0.05 lots @ 2665.50
```

### Telegram уведомления

При включенном Telegram получишь:
- 🚀 Новый AI сигнал создан
- ✅ Сигнал сработал → сделка открыта
- 🚫 Блокировка торговли GPT
- ⚠️ Лимит сделок достигнут

---

## 🎨 GUI индикаторы

### Переключатель режима
```
🎯 Режим торговли:
 ⚡ Strategy + AI  (Стратегия + GPT фильтр) [выбрано]
 🤖 Pure AI Trading  (Только GPT сигналы)
                                          [Активен] ✅
```

### Статус Pure AI
```
Pure AI Status:
- Running: Yes
- Trades Today: 2 / 5
- Last Analysis: XAUUSD @ 10:00, EURUSD @ 10:01
- Cooldowns: XAUUSD (45 min), EURUSD (-)
- Next Cycle: 12:00:00
```

---

## 💡 Советы по использованию

### 1. Тестируй на демо
```
- Первую неделю: только наблюдай
- Записывай все сигналы в Excel
- Сравнивай с Strategy mode
- Переходи на лайв только после проверки
```

### 2. Настрой под себя
```python
# Консервативный режим
MIN_CONFIDENCE = 80           # Только очень уверенные сигналы
MAX_TRADES_PER_DAY = 3        # Мало сделок
COOLDOWN_HOURS = 4            # Больше пауза

# Агрессивный режим
MIN_CONFIDENCE = 65           # Больше сигналов
MAX_TRADES_PER_DAY = 8        # Активная торговля
COOLDOWN_HOURS = 1            # Короткая пауза
```

### 3. Комбинируй режимы
```
Утро (06:00-12:00):  Strategy + AI (активная сессия)
День (12:00-18:00):  Pure AI (GPT анализ)
Вечер (18:00-22:00): Strategy + AI (NY закрытие)
Ночь (22:00-06:00):  Pure AI (низкая активность)
```

---

## 🔮 Будущие улучшения

- [ ] Адаптивный интервал (чаще в активные сессии)
- [ ] Multi-timeframe confirmation (сигнал на 3+ TF)
- [ ] Sentiment analysis новостей
- [ ] Backtesting Pure AI на истории
- [ ] A/B testing Strategy vs Pure AI
- [ ] Portfolio diversification (крипта, акции)

---

## 📞 Поддержка

Проблемы? Вопросы?

1. Проверь логи: `logs/test_log.txt`
2. Проверь ошибки: Ctrl+Shift+I (Developer Tools)
3. Telegram: @your_support_bot
4. GitHub Issues: [your-repo]/issues

---

**Версия:** 1.0  
**Дата:** 07.01.2026  
**Автор:** BAZA Trading Bot Team

🚀 **Удачной торговли!**

# StateCore Integration - Документация

## Обзор

**StateCore** - минимальный state manager без полной перестройки архитектуры. Решает 3 критические проблемы:

1. **UI десинхронизация** - статус показывает WAITING, но бот торгует
2. **Дубли входов** - несколько ордеров на один сигнал
3. **Нет прозрачности** - непонятно почему вошли/отказались

## Архитектура

```
StateCore (singleton)
├── BotStatus (enum): IDLE/WAITING/ANALYZING/BLOCKED/ORDERING/TRADING/ERROR
├── ActiveSignal (dataclass): текущий активный сигнал
├── LastAnalysis (dataclass): последний GPT анализ
├── DecisionLog (dataclass): structured logging каждого решения
├── Locks: order_lock, analysis_lock (защита от дублей)
├── Cooldown tracking: cooldown_until, last_order_ts
└── Signal deduplication: processed_signal_ids (set)
```

## Основные компоненты

### 1. StateCore (`src/core/state_core.py`)

**Singleton** - единый источник правды для всего бота.

**Основные методы:**
- `set_status(status, reason)` - установить статус бота
- `set_active_signal(signal)` - установить активный сигнал (с дедупликацией)
- `clear_active_signal(reason)` - очистить после закрытия позиции
- `acquire_order_lock() / release_order_lock()` - защита от двойных ордеров
- `acquire_analysis_lock() / release_analysis_lock()` - защита от двойных GPT запросов
- `log_decision(decision)` - structured logging в JSONL
- `get_state_snapshot()` - полный снимок состояния для UI

### 2. Signal ID Generator (`src/core/signal_id_generator.py`)

Генерирует уникальные ID для дедупликации:

**Формат:** `{symbol}_{timeframe}_{timestamp}_{hash}`
**Пример:** `XAUUSD_M5_20260221_142530_a3f9b2`

**Функции:**
- `generate_signal_id(symbol, timeframe, action, entry, sl, tp)` - создать ID
- `generate_signal_id_from_dict(data)` - из словаря сигнала
- `parse_signal_id(signal_id)` - разобрать компоненты

### 3. Decision Logging (`data/decision_logs.jsonl`)

**Формат:** 1 строка JSON на каждую попытку сигнала

**Структура:**
```json
{
  "signal_id": "XAUUSD_M5_20260221_142530_a3f9b2",
  "timestamp": "2026-02-21T14:25:30",
  "symbol": "XAUUSD",
  "raw_signal": "BUY",
  "gpt_confidence": 82,
  "gpt_reasoning": "Strong bullish momentum...",
  "filters": {
    "htf_gate": "PASS (TREND_UP aligned)",
    "rr_gate": "PASS (1.5 RR)",
    "spread_gate": "PASS (2.1 pips)",
    "cooldown_gate": "PASS (120 min since last)",
    "daily_limit_gate": "PASS (3/6 trades)"
  },
  "setup_score": 78,
  "final_decision": "ENTER",
  "block_reason": null
}
```

**Типы решений:**
- `ENTER` - вошли в сделку
- `HOLD` - GPT выбрал HOLD
- `BLOCK` - фильтры заблокировали
- `DUPLICATE` - дубликат signal_id
- `INVALID` - не прошел базовую валидацию
- `ERROR` - ошибка обработки

## Интеграции

### Signal Manager (`src/ai/signal_manager.py`)

**Изменения:**
1. Импортирован StateCore и signal_id_generator
2. В `__init__`: инициализация `self.state_core = get_state_core()`
3. В `create_signal_from_analysis()`:
   - Генерация signal_id с хешем от entry/sl/tp
   - Проверка дедупликации через `state_core.processed_signal_ids`
   - Structured logging всех решений (ENTER/BLOCK/HOLD)
   - Установка ActiveSignal через `state_core.set_active_signal()`
4. В обработке HOLD:
   - Logging HOLD решений
   - Установка статуса WAITING

### LiveTrader (`src/live/live_trader.py`)

**Изменения:**
1. Импортирован StateCore и BotStatus
2. В `__init__`: инициализация `self.state_core = get_state_core()`
3. В цикле выставления ордера:
   - `acquire_order_lock()` перед executor.execute_signal
   - Статус ORDERING → TRADING
   - `release_order_lock()` в finally
4. При закрытии позиции:
   - `clear_active_signal(reason="Position closed")`
   - Статус TRADING → WAITING

### Analyst Scheduler (`src/ai/analyst_scheduler.py`)

**Изменения:**
1. Импортирован StateCore и BotStatus
2. В `__init__`: инициализация `self.state_core = get_state_core()`
3. В `_run_analysis()`:
   - `acquire_analysis_lock()` в начале (защита от двойных GPT запросов)
   - Статус ANALYZING во время GPT анализа
   - Статус WAITING/BLOCKED/ERROR после завершения
   - `release_analysis_lock()` в finally

## Workflow - Полный цикл

### 1. Анализ запущен

```
[Scheduler] acquire_analysis_lock() ✓
[StateCore] Status: WAITING → ANALYZING
[Scheduler] GPT запрос...
```

### 2. GPT ответ получен

```python
# А) HOLD
[SignalManager] Action: HOLD
[StateCore] log_decision(HOLD)
[StateCore] Status: ANALYZING → WAITING

# Б) BUY/SELL
[SignalManager] Generate signal_id: XAUUSD_M5_20260221_142530_a3f9b2
[SignalManager] Check filters...
```

### 3. Фильтры пройдены

```
[SignalManager] HTF Gate: PASS ✓
[SignalManager] RR Gate: PASS ✓
[SignalManager] Spread Gate: PASS ✓
[SignalManager] Cooldown Gate: PASS ✓
[SignalManager] Daily Limit Gate: PASS (3/6) ✓
[SignalManager] Setup Score: 78 ✓
[StateCore] log_decision(ENTER, score=78)
[StateCore] set_active_signal(signal) ✓
```

### 4. Ордер выставляется

```
[LiveTrader] acquire_order_lock() ✓
[StateCore] Status: WAITING → ORDERING
[Executor] order_send() → ticket=12345678
[StateCore] Status: ORDERING → TRADING
[LiveTrader] release_order_lock() ✓
```

### 5. Позиция закрыта

```
[LiveTrader] Position closed: P&L +$15.50
[StateCore] clear_active_signal(reason="Position closed (WIN, P&L: $15.50)")
[StateCore] Status: TRADING → WAITING
[TradeFilters] record_trade_result(XAUUSD, +15.50)
[TradeFilters] Set cooldown: 15 min (after win)
```

## Дедупликация - Защита от дублей

### Signal ID уровень

**Проблема:** Два одинаковых сигнала в одну минуту

**Решение:**
```python
signal_id = f"{symbol}_{tf}_{timestamp}_{hash(entry+sl+tp)}"
# XAUUSD_M5_20260221_142530_a3f9b2

if signal_id in state_core.processed_signal_ids:
    log_decision(DUPLICATE)
    return None

state_core.processed_signal_ids.add(signal_id)
```

### Order Lock уровень

**Проблема:** Два потока пытаются выставить ордер одновременно

**Решение:**
```python
if not state_core.acquire_order_lock():
    logger.warning("Order lock already held - skipping")
    return None

try:
    executor.execute_signal()
finally:
    state_core.release_order_lock()
```

### Analysis Lock уровень

**Проблема:** Два GPT запроса запускаются параллельно

**Решение:**
```python
if not state_core.acquire_analysis_lock():
    logger.warning("Analysis lock already held - skipping")
    return {"error": "analysis_locked"}

try:
    analyst.analyze_market()
finally:
    state_core.release_analysis_lock()
```

## UI Integration (будущее)

**Без рефакторинга app_v2.py:**

```python
# В любом месте UI можно прочитать состояние:
snapshot = state_core.get_state_snapshot()

# Статус
status_label.config(text=snapshot['bot_status'])

# Активный сигнал
if snapshot['active_signal']:
    signal = snapshot['active_signal']
    signal_label.config(text=f"{signal['action']} @ {signal['entry']}")

# Cooldown
if snapshot['cooldown']['active']:
    remaining = snapshot['cooldown']['remaining_minutes']
    cooldown_label.config(text=f"Cooldown: {remaining} min")

# Блокировка
if snapshot['block_reason']:
    block_label.config(text=snapshot['block_reason'])
```

## Логи - Где смотреть

### 1. Real-time logs
```
logs/bot.log
```

**StateCore маркеры:**
```
[StateCore] Status: WAITING → ANALYZING
[StateCore] Active signal set: BUY XAUUSD (ID: XAUUSD_M5...)
[StateCore] Clearing active signal: XAUUSD_M5... (Position closed)
[StateCore] 🔒 Order lock acquired
[StateCore] 🔓 Order lock released
```

### 2. Decision logs
```
data/decision_logs.jsonl
```

**Каждая строка = одна попытка:**
```bash
# Фильтруем только входы
cat decision_logs.jsonl | jq 'select(.final_decision=="ENTER")'

# Фильтруем блокировки по cooldown
cat decision_logs.jsonl | jq 'select(.block_reason | contains("cooldown"))'

# Статистика решений за день
cat decision_logs.jsonl | grep "2026-02-21" | jq '.final_decision' | sort | uniq -c
```

### 3. State snapshots (debug)
```python
from src.core.state_core import get_state_core
state = get_state_core()

# Вывести полное состояние
import json
print(json.dumps(state.get_state_snapshot(), indent=2))
```

## Преимущества

### ✅ Решенные проблемы

1. **UI десинхронизация**
   - Единый источник статуса
   - UI читает напрямую из StateCore
   - Гарантия: что видишь = что есть

2. **Дубли входов**
   - Signal ID дедупликация
   - Order lock защита
   - Analysis lock защита

3. **Нет прозрачности**
   - Каждое решение в decision_logs.jsonl
   - Все фильтры видны
   - Setup score + причина блокировки

### 📊 Новые возможности

1. **Structured logging**
   - JSON формат для анализа
   - Фильтрация по типам решений
   - Статистика фильтров

2. **Signal tracking**
   - Полная история signal_id
   - От создания до закрытия
   - P&L привязан к signal_id

3. **Lock visibility**
   - Видно когда бот заблокирован
   - Причина блокировки
   - Оставшееся время cooldown

## Минимальность

**НЕ требует:**
- ❌ Полной перестройки app_v2.py
- ❌ Изменения архитектуры executor
- ❌ Рефакторинга bot_manager
- ❌ Миграции данных

**Требует только:**
- ✅ Импорт StateCore
- ✅ Вызовы set_status/locks
- ✅ UI читает snapshot (опционально)

## Совместимость

- Работает со старым кодом
- Постепенная миграция UI
- Нет breaking changes
- Singleton не конфликтует

## Дальнейшее развитие

**После успешного тестирования:**

1. UI Dashboard для StateCore
2. Web API для мониторинга
3. Alerts на критические статусы
4. Графики decision logs
5. Real-time snapshot streaming

## Troubleshooting

### Проблема: "Order lock already held"

**Причина:** Предыдущий ордер не отпустил lock (exception в finally?)

**Решение:**
```python
state_core.release_order_lock()  # Manual release
```

### Проблема: "Analysis lock already held"

**Причина:** GPT запрос завис, lock не освободился

**Решение:**
```python
state_core.release_analysis_lock()  # Manual release
```

### Проблема: Дубликаты signal_id

**Причина:** Hash коллизия (маловероятно) или одинаковые параметры

**Решение:**
Нормально - это защита работает! Дубли отсеиваются, decision_log покажет DUPLICATE.

---

**v1.0 - Minimal StateCore без полной перестройки**

Дата: 2026-02-21

# StateCore Integration - Changelog

## 2026-02-21 - v1.0 Initial Release

### 🎯 Цель
Минимальный state manager без полной перестройки архитектуры для решения 3 проблем:
1. UI десинхронизация (статус не совпадает с реальностью)
2. Дубли входов (несколько ордеров на один сигнал)
3. Нет прозрачности (почему вошли/отказались)

---

## 📦 Новые файлы

### Core Components

1. **`src/core/state_core.py`** (400 строк)
   - `BotStatus` enum (IDLE/WAITING/ANALYZING/BLOCKED/ORDERING/TRADING/ERROR)
   - `StateCore` singleton class
   - `ActiveSignal` dataclass - текущий активный сигнал
   - `LastAnalysis` dataclass - последний GPT анализ
   - `DecisionLog` dataclass - structured logging
   - Thread-safe locks (order_lock, analysis_lock)
   - Signal deduplication (processed_signal_ids set)
   - Cooldown tracking (cooldown_until, last_order_ts)
   - Decision logging в JSONL формат

2. **`src/core/signal_id_generator.py`** (120 строк)
   - `generate_signal_id()` - создание уникальных ID с хешем
   - Формат: `{symbol}_{tf}_{timestamp}_{hash(entry+sl+tp)}`
   - Пример: `XAUUSD_M5_20260221_142530_a3f9b2`
   - `parse_signal_id()` - разбор компонентов
   - `is_valid_signal_id()` - валидация формата

### Documentation

3. **`docs/STATE_CORE_INTEGRATION.md`** (500 строк)
   - Полная документация архитектуры
   - Workflow диаграммы
   - Примеры использования
   - Troubleshooting guide

---

## 🔧 Измененные файлы

### src/ai/signal_manager.py

**Добавлено:**
- Импорт: `StateCore`, `BotStatus`, `ActiveSignal`, `LastAnalysis`, `DecisionLog`
- Импорт: `generate_signal_id_from_dict`
- `self.state_core = get_state_core()` в __init__

**Изменено: `create_signal_from_analysis()`**
```python
# 1. Генерация signal_id (hash от entry/sl/tp)
signal_id = generate_signal_id_from_dict(signal_data)

# 2. Проверка дедупликации
if signal_id in self.state_core.processed_signal_ids:
    decision = DecisionLog(..., final_decision="DUPLICATE")
    self.state_core.log_decision(decision)
    return None

# 3. Валидация + фильтры
gates_passed, reason, score = self.trade_filters.check_all_gates(...)

# 4. Decision logging
decision = DecisionLog(
    signal_id=signal_id,
    filters={...},
    setup_score=score,
    final_decision="ENTER" | "BLOCK",
    block_reason=reason
)
self.state_core.log_decision(decision)

# 5. Если заблокировано - обновить статус
if not gates_passed:
    self.state_core.set_status(BotStatus.BLOCKED, reason=reason)
    return None

# 6. Создать ActiveSignal
active_signal = ActiveSignal(
    signal_id=signal_id,
    symbol=symbol,
    action=action,
    confidence=confidence,
    ...
)
self.state_core.set_active_signal(active_signal)

# 7. Сохранить LastAnalysis
last_analysis = LastAnalysis(...)
self.state_core.set_last_analysis(last_analysis)
```

**Изменено: обработка HOLD**
```python
if action == "HOLD":
    # Decision logging
    decision = DecisionLog(..., final_decision="HOLD")
    self.state_core.log_decision(decision)
    
    # Update status
    self.state_core.set_status(BotStatus.WAITING)
```

**Добавлено: `_create_signal_with_id()`**
- Принимает signal_id как параметр
- Старый `_create_signal()` теперь вызывает этот метод

---

### src/live/live_trader.py

**Добавлено:**
- Импорт: `StateCore`, `BotStatus`
- `self.state_core = get_state_core()` в __init__
- `self.state_core.set_status(BotStatus.IDLE)` при старте

**Изменено: выставление ордера**
```python
# Перед executor.execute_signal():
if not self.state_core.acquire_order_lock():
    logger.warning("Order lock already held - skipping")
    return None

try:
    # Update status
    self.state_core.set_status(BotStatus.ORDERING)
    self.state_core.last_order_ts = datetime.now()
    
    result = self.executor.execute_signal(symbol, signal)
    
    if result:
        # Position opened
        self.state_core.set_status(BotStatus.TRADING)
finally:
    self.state_core.release_order_lock()
```

**Изменено: закрытие позиции**
```python
for trade in new_trades:
    pnl = trade.get('pnl', 0)
    symbol = trade.get('symbol')
    
    # Clear active signal if matches
    if self.state_core.active_signal and \
       self.state_core.active_signal.symbol == symbol:
        result_str = "WIN" if pnl > 0 else "LOSS"
        self.state_core.clear_active_signal(
            reason=f"Position closed ({result_str}, P&L: ${pnl:.2f})"
        )
        
        # Update status to WAITING
        self.state_core.set_status(BotStatus.WAITING)
```

---

### src/ai/analyst_scheduler.py

**Добавлено:**
- Импорт: `StateCore`, `BotStatus`
- `self.state_core = get_state_core()` в __init__

**Изменено: `_run_analysis()`**
```python
# В начале метода:
if not self.state_core.acquire_analysis_lock():
    logger.warning("Analysis lock already held - skipping")
    return {"error": "analysis_locked"}

try:
    # Update status
    self.state_core.set_status(BotStatus.ANALYZING)
    
    # Duplicate check
    if time_since_last < 60:
        self.state_core.set_status(BotStatus.WAITING)
        return {"error": "duplicate_blocked"}
    
    # Kill-switch check
    if not self.is_ai_enabled():
        self.state_core.set_status(BotStatus.WAITING)
        return fallback
    
    # Position check
    if has_position:
        self.state_core.set_status(BotStatus.BLOCKED, 
                                   reason="Position open")
        return {"error": "position_open"}
    
    # Time restriction check
    if not time_allowed:
        self.state_core.set_status(BotStatus.BLOCKED, 
                                   reason=time_reason)
        return {"error": "time_restriction"}
    
    # Volatility check
    if not vol_passed:
        self.state_core.set_status(BotStatus.BLOCKED,
                                   reason=vol_reason)
        return {"error": "volatility_filter"}
    
    # Run GPT analysis
    try:
        analysis = self.analyst.analyze_market(symbol)
    except Exception as e:
        self.state_core.set_status(BotStatus.ERROR, reason=str(e))
        return fallback
    
    # Process signals
    signal_summary = self.signal_manager.process_analysis(analysis)
    
    # Success - back to WAITING (unless signal created)
    if not self.state_core.active_signal:
        self.state_core.set_status(BotStatus.WAITING)
    
    return analysis

finally:
    self.state_core.release_analysis_lock()
```

---

## 📊 Новые возможности

### 1. Structured Decision Logging

**Файл:** `data/decision_logs.jsonl`

**Формат:**
```json
{
  "signal_id": "XAUUSD_M5_20260221_142530_a3f9b2",
  "timestamp": "2026-02-21T14:25:30",
  "symbol": "XAUUSD",
  "raw_signal": "BUY",
  "gpt_confidence": 82,
  "gpt_reasoning": "Strong bullish momentum, EMA alignment",
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
- `ENTER` - вошли в сделку (все фильтры PASS)
- `HOLD` - GPT выбрал HOLD (smart trading)
- `BLOCK` - фильтры заблокировали (htf/rr/spread/cooldown/daily_limit)
- `DUPLICATE` - дубликат signal_id (защита работает)
- `INVALID` - не прошел базовую валидацию (entry==sl и т.д.)
- `ERROR` - ошибка обработки

### 2. Signal ID Deduplication

**Защита от дублей на 3 уровнях:**

1. **Signal ID level**
   - Hash от entry/sl/tp/timestamp
   - Проверка `signal_id in processed_signal_ids`
   - Log: DUPLICATE decision

2. **Order lock level**
   - `state_core.order_lock` флаг
   - Защищает executor.execute_signal()
   - Только один ордер одновременно

3. **Analysis lock level**
   - `state_core.analysis_lock` флаг
   - Защищает GPT запросы
   - Только один анализ одновременно

### 3. BotStatus Tracking

**Жизненный цикл статуса:**
```
IDLE → WAITING → ANALYZING → [ORDERING → TRADING] → WAITING
                       ↓
                   BLOCKED / ERROR
```

**События:**
- `IDLE` - бот запущен, но еще не начал работу
- `WAITING` - ожидание следующего цикла/события
- `ANALYZING` - GPT анализ в процессе
- `BLOCKED` - заблокирован (cooldown/filters/position open)
- `ORDERING` - выставление ордера в MT5
- `TRADING` - позиция открыта
- `ERROR` - ошибка (config/API/network)

### 4. Active Signal Tracking

**StateCore.active_signal:**
- Хранит текущий активный сигнал
- Очищается при закрытии позиции
- Связывает signal_id → P&L
- Проверяется при блокировке анализа

**StateCore.last_analysis:**
- Хранит последний GPT ответ
- Даже если сигнал заблокирован фильтрами
- Для debug и UI отображения

---

## 🔒 Thread Safety

### Locks

1. **StateCore._state_lock** (threading.Lock)
   - Защищает доступ к внутреннему состоянию
   - Используется во всех методах set/get
   - Предотвращает race conditions

2. **order_lock** (bool flag)
   - Защищает выставление ордеров
   - acquire → execute → release (finally)
   - Предотвращает двойные ордера

3. **analysis_lock** (bool flag)
   - Защищает GPT запросы
   - acquire → analyze → release (finally)
   - Предотвращает двойные API вызовы

### Singleton Pattern

```python
class StateCore:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**Гарантии:**
- Только один экземпляр StateCore
- Thread-safe инициализация
- Доступ из любого модуля

---

## 📈 Метрики (добавляются в логи)

### StateCore Events

**Маркеры в logs/bot.log:**
```
[StateCore] Status: WAITING → ANALYZING
[StateCore] Active signal set: BUY XAUUSD (ID: XAUUSD_M5_20260221...)
[StateCore] Decision: ENTER | BUY XAUUSD (82%) | Score: 78 | Reason: OK
[StateCore] Clearing active signal: XAUUSD_M5... (Position closed (WIN, P&L: $15.50))
[StateCore] 🔒 Order lock acquired
[StateCore] 🔓 Order lock released
[StateCore] 🔒 Analysis lock acquired
[StateCore] 🔓 Analysis lock released
```

### Decision Log Events

**data/decision_logs.jsonl:**
- Каждая строка = одна попытка сигнала
- JSON формат для парсинга
- Фильтрация, статистика, анализ

---

## ⚠️ Breaking Changes

**НЕТ** - полная обратная совместимость!

**Старый код работает:**
- AI Signal Manager продолжает работу
- LiveTrader выставляет ордера
- Analyst Scheduler запускает анализы

**Новое добавлено:**
- StateCore - опциональный слой
- Decision logging - дополнительный вывод
- Signal ID - расширенная валидация

---

## 🧪 Тестирование

### Проверить signal_id генерацию

```python
from src.core.signal_id_generator import generate_signal_id

signal_id = generate_signal_id(
    symbol="XAUUSD",
    timeframe="M5",
    action="BUY",
    entry=2650.5,
    sl=2645.0,
    tp=2660.0
)
print(signal_id)
# XAUUSD_M5_20260221_142530_a3f9b2
```

### Проверить StateCore

```python
from src.core.state_core import get_state_core, BotStatus

state = get_state_core()

# Set status
state.set_status(BotStatus.ANALYZING)

# Get snapshot
import json
print(json.dumps(state.get_state_snapshot(), indent=2))
```

### Проверить decision logs

```bash
# Показать последние 5 решений
tail -5 data/decision_logs.jsonl | jq '.'

# Фильтр по типу
cat data/decision_logs.jsonl | jq 'select(.final_decision=="ENTER")'

# Статистика за день
cat data/decision_logs.jsonl | grep "2026-02-21" | jq '.final_decision' | sort | uniq -c
```

---

## 🚀 Следующие шаги

### Мгновенные (уже работает)

1. ✅ Decision logging - каждая попытка видна
2. ✅ Signal deduplication - дубли отсеиваются
3. ✅ Lock protection - двойные ордера невозможны

### Короткие (опционально)

1. UI чтение `state_core.get_state_snapshot()` для отображения статуса
2. Real-time log viewer для decision_logs.jsonl
3. Grafana dashboard на базе JSONL логов

### Долгие (будущее)

1. Web API для мониторинга StateCore
2. Alerts на критические статусы (ERROR/BLOCKED)
3. A/B тестирование фильтров через decision logs
4. ML анализ причин блокировок

---

## 📚 Документация

- **Полная документация:** `docs/STATE_CORE_INTEGRATION.md`
- **API Reference:** См. docstrings в `src/core/state_core.py`
- **Examples:** См. раздел "Workflow" в документации

---

**v1.0 - Minimal StateCore Integration**

Автор: GitHub Copilot (Claude Sonnet 4.5)
Дата: 2026-02-21

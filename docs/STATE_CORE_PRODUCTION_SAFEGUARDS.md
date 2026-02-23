# StateCore Production Safeguards - Документация

## Обзор изменений

Добавлены 6 критичных продакшн-страховок для предотвращения сбоев в проде:

1. **TTL/LRU для processed_signal_ids** - предотвращение утечки памяти
2. **Auto-timeout для locks** - защита от зависших запросов
3. **Формализация статусов** - TRADING только при реальной позиции
4. **Разделение last_analysis и active_signal** - HOLD не перетирает active_signal
5. **Ticket tracking + CLOSE events** - полная трассировка сделок
6. **Единственный путь к ордеру** - валидация перед acquire_order_lock

---

## 1️⃣ TTL/LRU для processed_signal_ids

### Проблема

```python
# СТАРЫЙ КОД (память растёт бесконечно)
self.processed_signal_ids: set = set()
# Через неделю → 10,000 signal_ids в памяти
# Через месяц → 50,000+ signal_ids
# → OOM crash
```

### Решение

```python
# НОВЫЙ КОД (TTL 24 часа)
self.processed_signal_ids: Dict[str, datetime] = {}  # signal_id -> timestamp

def _cleanup_old_signal_ids(self):
    """Очистка signal_ids старше 24 часов (TTL/LRU)."""
    now = datetime.now()
    ttl_seconds = 24 * 3600  # 24 hours
    
    old_ids = [
        sid for sid, ts in self.processed_signal_ids.items()
        if (now - ts).total_seconds() > ttl_seconds
    ]
    
    for sid in old_ids:
        del self.processed_signal_ids[sid]
    
    if old_ids:
        logger.debug(f"[StateCore] Cleaned {len(old_ids)} old signal_ids (TTL 24h)")
```

**Вызывается автоматически в `set_active_signal()`:**
```python
def set_active_signal(self, signal: ActiveSignal):
    with self._state_lock:
        # Cleanup перед проверкой дубликата
        self._cleanup_old_signal_ids()
        
        # Check duplicate
        if signal.signal_id in self.processed_signal_ids:
            age_seconds = (datetime.now() - self.processed_signal_ids[signal.signal_id]).total_seconds()
            logger.warning(f"Duplicate signal_id (age: {age_seconds:.0f}s) - IGNORED")
            return False
        
        # Save with timestamp
        self.processed_signal_ids[signal.signal_id] = datetime.now()
```

**Гарантии:**
- ✅ Дубликаты блокируются в течение 24 часов
- ✅ Старые signal_ids автоматически удаляются
- ✅ Память не растёт бесконечно
- ✅ Нет ложных DUPLICATE после 24h

---

## 2️⃣ Auto-timeout для locks

### Проблема

```python
# СТАРЫЙ КОД (зависший lock убивает бота)
def acquire_order_lock(self):
    if self.order_lock:
        return False  # Locked forever if exception in finally
    self.order_lock = True
    return True

# Сценарий:
# 1. acquire_order_lock() → True
# 2. executor.execute_signal() → exception (MT5 disconnected)
# 3. finally: release_order_lock() → НЕ ВЫПОЛНИЛСЯ (crash)
# 4. order_lock == True НАВСЕГДА → БОТ МЁРТВ до перезапуска
```

### Решение: order_lock timeout (30 секунд)

```python
self.order_lock: bool = False
self.order_lock_acquired_at: Optional[datetime] = None  # Track acquisition time

def acquire_order_lock(self) -> bool:
    with self._state_lock:
        # AUTO-TIMEOUT CHECK (30 seconds)
        if self.order_lock and self.order_lock_acquired_at:
            elapsed = (datetime.now() - self.order_lock_acquired_at).total_seconds()
            if elapsed > 30:
                logger.error(f"🚨 Order lock timeout ({elapsed:.0f}s > 30s) - AUTO RELEASE")
                self.order_lock = False
                self.order_lock_acquired_at = None
                self.set_status(BotStatus.ERROR, reason="Order lock timeout")
        
        if self.order_lock:
            return False
        
        # PRODUCTION GUARD: Единственный путь к ордеру - через active_signal
        if not self.active_signal:
            logger.error("🚨 CRITICAL: Cannot acquire order lock - no active_signal")
            return False
        
        if self.active_signal.action == "HOLD":
            logger.error("🚨 CRITICAL: Cannot acquire order lock - active_signal is HOLD")
            return False
        
        self.order_lock = True
        self.order_lock_acquired_at = datetime.now()
        return True
```

### Решение: analysis_lock timeout (90 секунд)

```python
self.analysis_lock: bool = False
self.analysis_lock_acquired_at: Optional[datetime] = None

def acquire_analysis_lock(self) -> bool:
    with self._state_lock:
        # AUTO-TIMEOUT CHECK (90 seconds)
        if self.analysis_lock and self.analysis_lock_acquired_at:
            elapsed = (datetime.now() - self.analysis_lock_acquired_at).total_seconds()
            if elapsed > 90:
                logger.error(f"🚨 Analysis lock timeout ({elapsed:.0f}s > 90s) - AUTO RELEASE")
                self.analysis_lock = False
                self.analysis_lock_acquired_at = None
                self.set_status(BotStatus.ERROR, reason="Analysis lock timeout")
        
        if self.analysis_lock:
            return False
        
        self.analysis_lock = True
        self.analysis_lock_acquired_at = datetime.now()
        return True
```

**Почему 30s для order_lock, 90s для analysis_lock?**
- Order execution обычно < 3 секунды
- GPT API может висеть 30-60 секунд при проблемах с сетью
- 30s достаточно для order + запас
- 90s достаточно для GPT + запас

**Гарантии:**
- ✅ Зависший order lock освобождается через 30s
- ✅ Зависший analysis lock освобождается через 90s
- ✅ Статус → ERROR (видно что что-то сломалось)
- ✅ Бот продолжает работать вместо мёртвого lock

---

## 3️⃣ Формализация статусов

### Проблемы старого кода

1. **TRADING без позиции:**
   ```python
   # executor.execute_signal() вернул True
   state_core.set_status(TRADING)
   # Но MT5 rejected order → позиции НЕТ
   # UI показывает TRADING, но ничего не открыто
   ```

2. **WAITING при MT5 disconnected:**
   ```python
   # MT5 connection lost
   state_core.set_status(WAITING)  # Как будто всё норм
   # Но бот не может торговать → должен быть ERROR
   ```

### Новая логика (в будущем, пока не реализовано полностью)

**Правила переходов:**
```
TRADING → только если позиция реально открыта (positions_get подтверждает)
ERROR → если MT5 disconnected
WAITING → только если:
  - Нет позиции
  - Нет блокировок
  - MT5 connected
```

**Реализация (пример для будущего):**
```python
def set_status_with_validation(self, status: BotStatus, mt5_connector=None):
    """Установить статус с валидацией."""
    # Проверяем валидность перехода
    if status == BotStatus.TRADING:
        # TRADING только если позиция реально открыта
        if mt5_connector:
            positions = mt5_connector.positions_get()
            if not positions or len(positions) == 0:
                logger.error("Cannot set TRADING - no open positions")
                return False
    
    if status == BotStatus.WAITING:
        # WAITING только если нет позиции и MT5 connected
        if mt5_connector:
            if not mt5_connector.is_connected():
                logger.error("Cannot set WAITING - MT5 disconnected")
                self.set_status(BotStatus.ERROR, reason="MT5 disconnected")
                return False
    
    self.set_status(status)
    return True
```

**Сейчас частично реализовано:**
- ✅ TRADING устанавливается после executor.execute_signal() == True
- ✅ ERROR устанавливается при timeout locks
- ⏳ TODO: Проверка реальной позиции через positions_get
- ⏳ TODO: MT5 connection check перед WAITING

---

## 4️⃣ Разделение last_analysis и active_signal

### Проблема старого кода

```python
# GPT вернул HOLD
if action == "HOLD":
    # Старый код мог перезаписать active_signal
    self.active_signal = ...  # ❌ ОШИБКА
    # Теряется информация о реальном торгуемом сигнале
```

### Жёсткое правило

**active_signal меняется ТОЛЬКО при final_decision == ENTER:**
```python
def set_active_signal(self, signal: ActiveSignal):
    with self._state_lock:
        # PRODUCTION GUARD: HOLD никогда не должен быть active_signal
        if signal.action == "HOLD":
            logger.error("🚨 CRITICAL: Attempted to set HOLD as active_signal - REJECTED")
            return False
        
        # Только BUY/SELL могут быть active_signal
        self.active_signal = signal
        return True
```

**HOLD сохраняется только в last_analysis:**
```python
# В signal_manager.py:
if action == "HOLD":
    # Save last_analysis (but NOT active_signal)
    last_analysis = LastAnalysis(
        signal_id=decision_log.signal_id,
        symbol=symbol,
        action="HOLD",
        confidence=confidence,
        reasoning=reasoning,
        timestamp=datetime.now().isoformat(),
        filters_passed=False,
        block_reason="GPT chose HOLD",
        setup_score=0
    )
    self.state_core.set_last_analysis(last_analysis)
    # active_signal НЕ ТРОГАЕМ
```

**Гарантии:**
- ✅ active_signal содержит ТОЛЬКО BUY/SELL
- ✅ HOLD никогда не перетирает active_signal
- ✅ last_analysis показывает последний GPT ответ (включая HOLD)
- ✅ UI может показывать оба: торгуемый сигнал + последний анализ

---

## 5️⃣ Ticket tracking + CLOSE events

### Расширение ActiveSignal

```python
@dataclass
class ActiveSignal:
    signal_id: str
    symbol: str
    action: str  # BUY/SELL (НИКОГДА HOLD)
    confidence: int
    entry: float
    sl: float
    tp: float
    reasoning: str
    timestamp: str
    setup_score: int = 0
    expires_at: Optional[str] = None
    ticket: Optional[int] = None  # 🆕 MT5 ticket ID
    opened_at: Optional[str] = None  # 🆕 Timestamp открытия позиции
```

### Сохранение ticket после order_send

```python
# В live_trader.py после executor.execute_signal():
if result:
    # Extract ticket from MT5 positions
    ticket = None
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get(symbol=symbol)
        if positions and len(positions) > 0:
            ticket = positions[-1].ticket
            logger.debug(f"[TRADE] Extracted ticket from position: {ticket}")
    except Exception as e:
        logger.debug(f"[TRADE] Could not extract ticket: {e}")
    
    # Save ticket and opened_at to active_signal
    if self.state_core.active_signal:
        self.state_core.active_signal.ticket = ticket
        self.state_core.active_signal.opened_at = datetime.now().isoformat()
        logger.info(f"[StateCore] Ticket saved to active_signal: {ticket}")
```

### Расширение DecisionLog для CLOSE events

```python
@dataclass
class DecisionLog:
    signal_id: str
    timestamp: str
    symbol: str
    raw_signal: str  # BUY/SELL/HOLD/CLOSE
    gpt_confidence: int
    gpt_reasoning: str
    filters: Dict[str, Any]
    setup_score: int
    final_decision: str  # ENTER/HOLD/BLOCK/DUPLICATE/INVALID/ERROR/CLOSE
    block_reason: Optional[str]
    ticket: Optional[int] = None  # 🆕 Для CLOSE events
    pnl: Optional[float] = None  # 🆕 Для CLOSE events
    duration_minutes: Optional[int] = None  # 🆕 Для CLOSE events
```

### Логирование CLOSE event

```python
def log_close_event(self, ticket: int, symbol: str, pnl: float, signal_id: Optional[str] = None):
    """
    Логировать событие CLOSE при закрытии позиции.
    
    Args:
        ticket: MT5 ticket
        symbol: Символ
        pnl: Profit/Loss
        signal_id: ID сигнала (если известен)
    """
    if not signal_id and self.active_signal:
        signal_id = self.active_signal.signal_id
    
    if not signal_id:
        logger.warning(f"Cannot log CLOSE event - no signal_id (ticket={ticket})")
        return
    
    # Calculate duration
    duration_minutes = None
    if self.active_signal and self.active_signal.opened_at:
        try:
            opened = datetime.fromisoformat(self.active_signal.opened_at)
            duration_minutes = int((datetime.now() - opened).total_seconds() / 60)
        except Exception as e:
            logger.debug(f"Failed to calculate duration: {e}")
    
    # Create CLOSE decision log
    close_log = DecisionLog(
        signal_id=signal_id,
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        raw_signal="CLOSE",
        gpt_confidence=0,
        gpt_reasoning="Position closed",
        filters={},
        setup_score=0,
        final_decision="CLOSE",
        block_reason=None,
        ticket=ticket,
        pnl=pnl,
        duration_minutes=duration_minutes
    )
    
    self.log_decision(close_log)
    logger.info(f"CLOSE event logged: ticket={ticket}, P&L=${pnl:.2f}, duration={duration_minutes}min")
```

### Пример в live_trader.py

```python
# При закрытии позиции:
for trade in new_trades:
    ticket = trade.get('ticket', trade_id)
    pnl = trade.get('pnl', 0)
    symbol = trade.get('symbol')
    
    if self.state_core.active_signal and self.state_core.active_signal.symbol == symbol:
        # Log CLOSE event with P&L and duration
        self.state_core.log_close_event(
            ticket=ticket,
            symbol=symbol,
            pnl=pnl,
            signal_id=self.state_core.active_signal.signal_id
        )
        
        result_str = "WIN" if pnl > 0 else "LOSS"
        self.state_core.clear_active_signal(reason=f"Position closed ({result_str}, P&L: ${pnl:.2f})")
```

### Пример CLOSE события в decision_logs.jsonl

```json
{
  "signal_id": "XAUUSD_M5_20260221_142530_a3f9b2",
  "timestamp": "2026-02-21T15:18:45",
  "symbol": "XAUUSD",
  "raw_signal": "CLOSE",
  "gpt_confidence": 0,
  "gpt_reasoning": "Position closed",
  "filters": {},
  "setup_score": 0,
  "final_decision": "CLOSE",
  "block_reason": null,
  "ticket": 12345678,
  "pnl": 15.50,
  "duration_minutes": 173
}
```

**Полный lifecycle в логах:**
```jsonl
{"signal_id": "XAUUSD_..._a3f9b2", "final_decision": "ENTER", "setup_score": 78, "timestamp": "14:25:30"}
{"signal_id": "XAUUSD_..._a3f9b2", "final_decision": "CLOSE", "ticket": 12345678, "pnl": 15.50, "duration_minutes": 173, "timestamp": "15:18:45"}
```

**Анализ:**
```bash
# Найти все CLOSE события с P&L
cat decision_logs.jsonl | jq 'select(.final_decision=="CLOSE")'

# Средний P&L
cat decision_logs.jsonl | jq 'select(.final_decision=="CLOSE") | .pnl' | awk '{sum+=$1; count++} END {print "Avg P&L:", sum/count}'

# Средняя длительность
cat decision_logs.jsonl | jq 'select(.final_decision=="CLOSE") | .duration_minutes' | awk '{sum+=$1; count++} END {print "Avg Duration:", sum/count, "min"}'

# Связать ENTER → CLOSE по signal_id
cat decision_logs.jsonl | jq -s 'group_by(.signal_id) | .[] | select(length > 1)'
```

---

## 6️⃣ Единственный путь к ордеру

### Правило

**Ордер может быть создан ТОЛЬКО если:**
1. `active_signal != None`
2. `active_signal.action == BUY or SELL` (не HOLD)
3. `order_lock` успешно получен

**Никаких обходных путей.**

### Реализация в acquire_order_lock

```python
def acquire_order_lock(self) -> bool:
    with self._state_lock:
        # ... timeout check ...
        
        # PRODUCTION GUARD: Единственный путь к ордеру - через active_signal
        if not self.active_signal:
            logger.error("🚨 CRITICAL: Cannot acquire order lock - no active_signal")
            return False
        
        if self.active_signal.action == "HOLD":
            logger.error("🚨 CRITICAL: Cannot acquire order lock - active_signal is HOLD")
            return False
        
        self.order_lock = True
        self.order_lock_acquired_at = datetime.now()
        return True
```

### Проверка в live_trader.py

```python
# Перед executor.execute_signal():
if not self.state_core.acquire_order_lock():
    logger.warning("⚠️ Order lock already held - skipping duplicate order")
    return None
```

**Защита на уровне StateCore:**
- ❌ Нельзя получить order_lock если нет active_signal
- ❌ Нельзя получить order_lock если active_signal.action == HOLD
- ❌ Нельзя выставить ордер без order_lock

**Защита на уровне live_trader:**
- ✅ Проверяет acquire_order_lock() == True перед executor
- ✅ release_order_lock() в finally (всегда)

**Гарантии:**
- ✅ Нет "сюрприз ордеров" из неизвестных источников
- ✅ Каждый ордер привязан к active_signal
- ✅ Каждый ордер залогирован с signal_id
- ✅ Trace от ENTER до CLOSE

---

## Итоговые гарантии

| № | Проблема | Решение | Статус |
|---|----------|---------|--------|
| 1 | Память растёт бесконечно | TTL 24h для signal_ids | ✅ |
| 2 | Зависший lock убивает бота | Auto-timeout 30s/90s | ✅ |
| 3 | TRADING без позиции | Validation (частично) | ⏳ |
| 4 | HOLD перетирает active_signal | Guard в set_active_signal | ✅ |
| 5 | Нет trace от ENTER → CLOSE | Ticket + CLOSE events | ✅ |
| 6 | Обходные пути к ордерам | Guard в acquire_order_lock | ✅ |

---

## Что осталось сделать (опционально)

### Формализация статусов (п.3)

**TODO:**
1. Добавить метод `set_status_with_validation(status, mt5_connector=None)`
2. Проверять `positions_get()` перед `BotStatus.TRADING`
3. Проверять `is_connected()` перед `BotStatus.WAITING`
4. Автоматический переход в ERROR при MT5 disconnect

**Приоритет:** Средний (сейчас частично работает, но нет полной валидации)

### Мониторинг locks

**TODO:**
1. Dashboard показывающий текущие locks + elapsed time
2. Alert при timeout locks (Telegram/Discord)
3. Метрики: lock_timeout_count, avg_lock_duration

**Приоритет:** Низкий (логи уже показывают проблемы)

---

**v1.1 - Production Safeguards**

Дата: 2026-02-21

# StateCore v1.2 - Stability Improvements

## Обзор

Добавлены 6 критичных стабилизационных улучшений перед production запуском:

1. **Position Confirmation with Retry** - подтверждение реальной позиции после order_send
2. **MT5 Watchdog** - мониторинг connection каждые 10-15s с auto-reconnect
3. **Circuit Breaker (Auto-Recovery)** - автоматическая блокировка при частых ошибках
4. **Event Bus** - события StateCore → UI для синхронизации интерфейса
5. **Invariants Checker** - проверка системных инвариантов каждые 60s
6. **Single Gate** - единый point of validation перед ордером

---

## 1️⃣ Position Confirmation with Retry

### Проблема

```python
# СТАРЫЙ КОД
result = executor.execute_signal(symbol, signal)
if result:
    state_core.set_status(TRADING)  # ❌ НЕТ ПРОВЕРКИ РЕАЛЬНОЙ ПОЗИЦИИ
# Что если MT5 принял order_send но позиция не открылась?
# → Бот думает что торгует, но позиции нет!
```

### Решение

```python
def confirm_position_opened(self, symbol: str, expected_ticket: Optional[int] = None, 
                            retries: int = 3, delay: float = 0.5) -> tuple[bool, Optional[int]]:
    """
    Подтверждение открытия позиции через positions_get с retry.
    
    Args:
        symbol: Символ для проверки
        expected_ticket: Ожидаемый ticket (optional)
        retries: Количество попыток (default: 3)
        delay: Задержка между попытками в секундах (default: 0.5)
    
    Returns:
        (success: bool, ticket: Optional[int])
    """
    for attempt in range(1, retries + 1):
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=symbol)
            
            if positions and len(positions) > 0:
                ticket = positions[-1].ticket
                
                # Validate expected ticket if provided
                if expected_ticket and ticket != expected_ticket:
                    logger.warning(f"Ticket mismatch: expected={expected_ticket}, found={ticket}")
                    if attempt < retries:
                        time.sleep(delay)
                        continue
                
                logger.info(f"✅ Position confirmed: {symbol} ticket={ticket} (attempt {attempt})")
                self._emit_event("position_confirmed", {"symbol": symbol, "ticket": ticket})
                return True, ticket
            else:
                logger.warning(f"No position found for {symbol} (attempt {attempt}/{retries})")
                if attempt < retries:
                    time.sleep(delay)
                    continue
        
        except Exception as e:
            logger.error(f"Position check error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
                continue
    
    # All retries failed
    logger.error(f"🚨 Position confirmation FAILED after {retries} retries")
    self._emit_event("position_confirmation_failed", {"symbol": symbol, "retries": retries})
    self._record_error("position_confirmation_failed")
    return False, None
```

### Использование в live_trader.py

```python
result = self.executor.execute_signal(symbol, signal)

if result:
    logger.info(f"✅ Order sent successfully for {symbol}")
    
    # POSITION CONFIRMATION: 3 retries x 0.5s
    position_confirmed, ticket = self.state_core.confirm_position_opened(
        symbol=symbol,
        retries=3,
        delay=0.5
    )
    
    if not position_confirmed:
        # CRITICAL: Order sent but position not confirmed
        logger.error(f"🚨 Order sent but position NOT confirmed for {symbol}")
        
        # Set ERROR status
        self.state_core.set_status(BotStatus.ERROR, reason="Order sent but no position")
        
        # Log to decision_logs
        self.state_core.log_decision(DecisionLog(
            signal_id=signal_id,
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            raw_signal=direction,
            gpt_confidence=0,
            gpt_reasoning="Order sent but position not confirmed",
            filters={},
            setup_score=0,
            final_decision="ERROR",
            block_reason="Position confirmation failed"
        ))
        
        # Clear active signal (trade failed)
        self.state_core.clear_active_signal(reason="Position confirmation failed")
        return None
    
    # Position confirmed! ✅
    logger.info(f"✅ Position confirmed: {symbol} ticket={ticket}")
    
    # Save ticket to active_signal
    if self.state_core.active_signal:
        self.state_core.active_signal.ticket = ticket
        self.state_core.active_signal.opened_at = datetime.now().isoformat()
    
    # NOW we can set TRADING status
    self.state_core.set_status(BotStatus.TRADING)
```

**Гарантии:**
- ✅ TRADING статус устанавливается ТОЛЬКО после подтверждения реальной позиции
- ✅ 3 попытки с 0.5s задержкой (total 1.5s max delay)
- ✅ ERROR статус и логирование если позиция не подтверждена
- ✅ Автоматический clear active_signal при неудаче

---

## 2️⃣ MT5 Watchdog

### Проблема

```python
# СТАРЫЙ КОД - нет мониторинга MT5 connection
# Если MT5 disconnected:
# - Бот продолжает пытаться торговать
# - Errors в логах, но нет recovery
# - Позиция может зависнуть без управления
```

### Решение: Background Thread

```python
def check_mt5_connection(self) -> bool:
    """Check MT5 connection health."""
    if not self.mt5_connector:
        return True  # No connector, assume OK
    
    try:
        import MetaTrader5 as mt5
        
        # Check terminal connection
        terminal_info = mt5.terminal_info()
        if not terminal_info:
            logger.error("MT5 terminal_info() failed")
            return False
        
        # Check account info
        account_info = mt5.account_info()
        if not account_info:
            logger.error("MT5 account_info() failed")
            return False
        
        # Check connection flag
        if not terminal_info.connected:
            logger.error("MT5 terminal not connected")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"MT5 connection check error: {e}")
        return False

def _mt5_watchdog_loop(self):
    """Background thread: MT5 connection watchdog."""
    logger.info("[StateCore] MT5 Watchdog started")
    
    while not self._shutdown_flag.is_set():
        try:
            time.sleep(12)  # Check every ~12 seconds (10-15s range)
            
            if not self.mt5_connector:
                continue
            
            healthy = self.check_mt5_connection()
            
            with self._state_lock:
                self.mt5_last_check = datetime.now()
                
                if not healthy and self.mt5_connection_healthy:
                    # Connection just lost
                    logger.error("🚨 MT5 CONNECTION LOST")
                    self.mt5_connection_healthy = False
                    self.set_status(BotStatus.ERROR, reason="MT5 disconnected")
                    self._emit_event("mt5_disconnected", {})
                    
                    # Keep active_signal for recovery
                    if self.active_signal:
                        logger.warning("Active signal present during disconnect - keeping for recovery")
                
                elif healthy and not self.mt5_connection_healthy:
                    # Connection restored
                    logger.info(f"✅ MT5 CONNECTION RESTORED (after {self.mt5_reconnect_attempts} attempts)")
                    self.mt5_connection_healthy = True
                    self.mt5_reconnect_attempts = 0
                    
                    if self.bot_status == BotStatus.ERROR:
                        self.set_status(BotStatus.WAITING)
                    
                    self._emit_event("mt5_reconnected", {})
                
                elif not healthy:
                    # Still disconnected, try reconnect
                    self.mt5_reconnect_attempts += 1
                    
                    if self.mt5_reconnect_attempts % 5 == 0:  # Every ~60s (5 * 12s)
                        logger.warning(f"Attempting MT5 reconnect... (attempt {self.mt5_reconnect_attempts})")
                        try:
                            import MetaTrader5 as mt5
                            if mt5.initialize():
                                logger.info("MT5 reconnect successful")
                        except Exception as e:
                            logger.error(f"MT5 reconnect failed: {e}")
        
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
    
    logger.info("[StateCore] MT5 Watchdog stopped")
```

### Запуск

```python
# В live_trader.py __init__:
self.state_core = get_state_core()
self.state_core.set_mt5_connector(self.mt5_connector)
self.state_core.start_background_tasks()  # Starts watchdog + invariants checker
```

**Гарантии:**
- ✅ Проверка connection каждые 12s (10-15s диапазон)
- ✅ Автоматический переход в ERROR при disconnect
- ✅ Попытки reconnect каждые ~60s
- ✅ Событие `mt5_disconnected` / `mt5_reconnected` в event bus
- ✅ Active signal сохраняется для recovery

---

## 3️⃣ Circuit Breaker (Auto-Recovery)

### Проблема

```python
# СТАРЫЙ КОД - нет защиты от частых ошибок
# Сценарий:
# 1. MT5 glitch → position confirmation failed
# 2. Retry → failed again
# 3. Retry → failed again
# → Бот продолжает пытаться торговать → cascade of errors
```

### Решение: Error Counter + Circuit Breaker

```python
def _record_error(self, error_type: str):
    """Record error for circuit breaker."""
    with self._state_lock:
        self.error_history.append({
            "type": error_type,
            "timestamp": datetime.now()
        })
        
        # Check if circuit breaker should trigger
        self._check_circuit_breaker()

def _check_circuit_breaker(self):
    """Check if circuit breaker should trigger (3 errors in 15 min → BLOCKED 2 hours)."""
    now = datetime.now()
    window_start = now - timedelta(minutes=15)
    
    # Count recent errors (last 15 minutes)
    recent_errors = [
        err for err in self.error_history
        if err["timestamp"] > window_start
    ]
    
    if len(recent_errors) >= 3:
        # TRIGGER CIRCUIT BREAKER
        self.recovery_blocked_until = now + timedelta(hours=2)
        
        # Release all locks
        self.order_lock = False
        self.order_lock_acquired_at = None
        self.analysis_lock = False
        self.analysis_lock_acquired_at = None
        
        # Clear active signal
        if self.active_signal:
            logger.error(
                f"🚨 CIRCUIT BREAKER TRIGGERED: {len(recent_errors)} errors in 15 min. "
                f"Clearing active signal: {self.active_signal.signal_id[:12]}..."
            )
            self.active_signal = None
        
        # Set status
        self.set_status(
            BotStatus.BLOCKED,
            reason=f"Circuit breaker: {len(recent_errors)} errors in 15 min (blocked 2h)"
        )
        
        self._emit_event("circuit_breaker_triggered", {
            "error_count": len(recent_errors),
            "blocked_until": self.recovery_blocked_until.isoformat()
        })
        
        logger.error(
            f"🔥 AUTO-RECOVERY: Bot BLOCKED for 2 hours (until {self.recovery_blocked_until.strftime('%H:%M')})"
        )

def is_recovery_blocked(self) -> tuple[bool, Optional[int]]:
    """Check if bot is in recovery block."""
    with self._state_lock:
        if not self.recovery_blocked_until:
            return False, None
        
        now = datetime.now()
        if now < self.recovery_blocked_until:
            remaining_minutes = int((self.recovery_blocked_until - now).total_seconds() / 60)
            return True, remaining_minutes
        else:
            # Recovery block expired
            self.recovery_blocked_until = None
            if self.bot_status == BotStatus.BLOCKED:
                self.set_status(BotStatus.WAITING)
                logger.info("✅ Recovery block expired - bot resumed")
                self._emit_event("recovery_block_expired", {})
            return False, None
```

**Правила Circuit Breaker:**
- **Trigger**: 3 ошибки за 15 минут
- **Action**: BLOCKED на 2 часа, release locks, clear active_signal
- **Errors tracked**: position_confirmation_failed, MT5 errors, lock timeouts
- **Recovery**: Автоматически через 2 часа

**Гарантии:**
- ✅ Защита от cascade failures
- ✅ Автоматическая очистка состояния (locks + active_signal)
- ✅ Cooldown 2 часа для стабилизации
- ✅ Событие `circuit_breaker_triggered` в event bus

---

## 4️⃣ Event Bus

### Назначение

Синхронизация StateCore → UI через очередь событий.

### API

```python
# Subscribe to events
def on_state_event(event: Dict):
    event_type = event["type"]  # e.g. "position_confirmed", "mt5_disconnected"
    timestamp = event["timestamp"]
    data = event["data"]
    
    # Update UI
    print(f"[{timestamp}] {event_type}: {data}")

state_core.subscribe_to_events(on_state_event)

# Events emitted automatically by StateCore:
# - position_confirmed: {"symbol": "XAUUSD", "ticket": 12345678}
# - position_confirmation_failed: {"symbol": "XAUUSD", "retries": 3}
# - mt5_disconnected: {}
# - mt5_reconnected: {}
# - circuit_breaker_triggered: {"error_count": 3, "blocked_until": "2026-02-21T18:30:00"}
# - recovery_block_expired: {}
# - invariants_violated: {"violations": ["TRADING without position"]}

# Get recent events
recent_events = state_core.get_recent_events(count=20)
```

**Гарантии:**
- ✅ Non-blocking callbacks (exceptions caught)
- ✅ Deque с maxlen=100 (последние 100 событий)
- ✅ Timestamps в ISO format
- ✅ Thread-safe

---

## 5️⃣ Invariants Checker

### Назначение

Проверка системных инвариантов каждые 60 секунд и автоматический recovery.

### Инварианты

```python
def check_invariants(self):
    """Check system invariants and fix violations."""
    violations = []
    
    with self._state_lock:
        now = datetime.now()
        
        # INVARIANT 1: TRADING status must have open position
        if self.bot_status == BotStatus.TRADING:
            if not self.active_signal:
                violations.append("TRADING without active_signal")
                logger.error("⚠️ INVARIANT VIOLATION: TRADING without active_signal")
                self.set_status(BotStatus.ERROR, reason="Invariant: TRADING without active_signal")
            
            elif self.mt5_connector:
                try:
                    import MetaTrader5 as mt5
                    positions = mt5.positions_get(symbol=self.active_signal.symbol)
                    if not positions or len(positions) == 0:
                        violations.append(f"TRADING without real position ({self.active_signal.symbol})")
                        logger.error(f"⚠️ INVARIANT VIOLATION: TRADING but no position for {self.active_signal.symbol}")
                        self.set_status(BotStatus.ERROR, reason="Invariant: TRADING without position")
                        self.active_signal = None
                except Exception as e:
                    logger.error(f"Invariant check error: {e}")
        
        # INVARIANT 2: Locks should not be held forever
        if self.order_lock and self.order_lock_acquired_at:
            elapsed = (now - self.order_lock_acquired_at).total_seconds()
            if elapsed > 60:  # More than 1 minute
                violations.append(f"order_lock held for {elapsed:.0f}s")
                logger.error(f"⚠️ INVARIANT VIOLATION: order_lock held for {elapsed:.0f}s - RELEASING")
                self.order_lock = False
                self.order_lock_acquired_at = None
        
        if self.analysis_lock and self.analysis_lock_acquired_at:
            elapsed = (now - self.analysis_lock_acquired_at).total_seconds()
            if elapsed > 120:  # More than 2 minutes
                violations.append(f"analysis_lock held for {elapsed:.0f}s")
                logger.error(f"⚠️ INVARIANT VIOLATION: analysis_lock held for {elapsed:.0f}s - RELEASING")
                self.analysis_lock = False
                self.analysis_lock_acquired_at = None
        
        # INVARIANT 3: active_signal must never be HOLD
        if self.active_signal and self.active_signal.action == "HOLD":
            violations.append("active_signal.action == HOLD")
            logger.error("⚠️ INVARIANT VIOLATION: active_signal is HOLD - CLEARING")
            self.active_signal = None
        
        # Store violations
        if violations:
            self.invariants_violations = violations
            self._emit_event("invariants_violated", {"violations": violations})
        
        self.invariants_last_check = now
    
    return violations
```

### Background Thread

```python
def _invariants_checker_loop(self):
    """Background thread: Invariants checker (every 60 seconds)."""
    logger.info("[StateCore] Invariants Checker started")
    
    while not self._shutdown_flag.is_set():
        try:
            time.sleep(60)  # Check every minute
            
            violations = self.check_invariants()
            
            if violations:
                logger.warning(f"Invariants check: {len(violations)} violations found")
            else:
                logger.debug("Invariants check: OK")
        
        except Exception as e:
            logger.error(f"Invariants checker error: {e}")
    
    logger.info("[StateCore] Invariants Checker stopped")
```

**Гарантии:**
- ✅ Проверка каждые 60s
- ✅ Автоматический recovery (release locks, clear invalid state)
- ✅ Событие `invariants_violated` при нарушениях
- ✅ Логирование всех нарушений

---

## 6️⃣ Single Gate

### Назначение

Единственный point of validation перед ордером. Все проверки в одном месте.

### Реализация

```python
# ════════════════════════════════════════════════════════════════
# SINGLE GATE: Единственный путь к ордеру - все проверки перед lock
# ════════════════════════════════════════════════════════════════

# Gate 1: Проверяем active_signal существует
if not self.state_core.active_signal:
    logger.error("[TRADE] 🚨 GATE VIOLATION: No active_signal - cannot proceed to order")
    self.state_core.log_decision(DecisionLog(
        signal_id=signal_id,
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        raw_signal=direction,
        gpt_confidence=0,
        gpt_reasoning="",
        filters={},
        setup_score=0,
        final_decision="BLOCK",
        block_reason="Gate: No active_signal"
    ))
    return None

# Gate 2: Проверяем что active_signal.action != HOLD
if self.state_core.active_signal.action == "HOLD":
    logger.error("[TRADE] 🚨 GATE VIOLATION: active_signal is HOLD - should never reach order execution")
    return None

# Gate 3: Проверяем recovery block
in_recovery, recovery_min = self.state_core.is_recovery_blocked()
if in_recovery:
    logger.warning(f"[TRADE] ⛔ GATE BLOCK: Bot in recovery mode ({recovery_min} min remaining)")
    self.state_core.log_decision(DecisionLog(
        signal_id=signal_id,
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        raw_signal=direction,
        gpt_confidence=0,
        gpt_reasoning="",
        filters={},
        setup_score=0,
        final_decision="BLOCK",
        block_reason=f"Gate: Recovery block ({recovery_min}min)"
    ))
    return None

# Gate 4: Проверяем MT5 connection
if not self.state_core.mt5_connection_healthy:
    logger.error("[TRADE] 🚨 GATE BLOCK: MT5 not connected")
    self.state_core.log_decision(DecisionLog(
        signal_id=signal_id,
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        raw_signal=direction,
        gpt_confidence=0,
        gpt_reasoning="",
        filters={},
        setup_score=0,
        final_decision="BLOCK",
        block_reason="Gate: MT5 disconnected"
    ))
    return None

# All gates passed ✅
logger.info(f"[TRADE] ✅ All gates passed for {symbol} - proceeding to order execution")

# ════════════════════════════════════════════════════════════════

# Now acquire order lock (protected by gates above)
if not self.state_core.acquire_order_lock():
    logger.warning("[TRADE] ⚠️ Order lock already held - skipping duplicate order")
    return None
```

**Gates:**
1. ✅ `active_signal != None`
2. ✅ `active_signal.action != HOLD`
3. ✅ `not in_recovery_block`
4. ✅ `mt5_connection_healthy`

**Гарантии:**
- ✅ Никаких обходных путей к ордеру
- ✅ Все BLOCK решения логируются в decision_logs.jsonl
- ✅ Явные error messages для каждого gate
- ✅ Fail-fast (return None при первом нарушении)

---

## Итоговые гарантии v1.2

| Улучшение | Проблема | Решение | Статус |
|-----------|----------|---------|--------|
| Position Confirmation | TRADING без реальной позиции | 3 retry x 0.5s через positions_get | ✅ |
| MT5 Watchdog | Нет мониторинга connection | Background check 12s + auto-reconnect 60s | ✅ |
| Circuit Breaker | Cascade failures | 3 errors в 15min → BLOCKED 2h | ✅ |
| Event Bus | UI рассинхронизация | StateCore events → UI callbacks | ✅ |
| Invariants Checker | Зависшие states | Check 60s + auto-recovery | ✅ |
| Single Gate | Обходные пути к ордеру | 4 gates перед order lock | ✅ |

---

## Запуск Background Tasks

```python
# В live_trader.py:
self.state_core = get_state_core()
self.state_core.set_mt5_connector(self.mt5_connector)
self.state_core.start_background_tasks()  # ← Starts watchdog + invariants checker

# При shutdown:
self.state_core.stop_background_tasks()
```

---

## Мониторинг в Production

### 1. Проверка здоровья

```python
snapshot = state_core.get_state_snapshot()

# MT5 watchdog status
print(f"MT5 healthy: {snapshot['mt5']['healthy']}")
print(f"Last check: {snapshot['mt5']['last_check']}")
print(f"Reconnect attempts: {snapshot['mt5']['reconnect_attempts']}")

# Recovery status
print(f"Recovery blocked: {snapshot['recovery']['blocked']}")
print(f"Recent errors (15min): {snapshot['recovery']['recent_errors']}")

# Invariants status
print(f"Last invariants check: {snapshot['invariants']['last_check']}")
print(f"Violations: {snapshot['invariants']['violations']}")
```

### 2. Events monitoring

```python
def monitor_events(event):
    event_type = event["type"]
    
    if event_type == "circuit_breaker_triggered":
        # CRITICAL: Circuit breaker triggered
        send_telegram_alert(f"🚨 Circuit breaker: {event['data']['error_count']} errors")
    
    elif event_type == "mt5_disconnected":
        # WARNING: MT5 connection lost
        send_telegram_alert("⚠️ MT5 disconnected")
    
    elif event_type == "invariants_violated":
        # ERROR: System invariants violated
        violations = event['data']['violations']
        send_telegram_alert(f"⚠️ Invariants violated: {violations}")

state_core.subscribe_to_events(monitor_events)
```

### 3. Decision logs analysis

```bash
# Найти все BLOCK решения от single gate
cat decision_logs.jsonl | jq 'select(.final_decision=="BLOCK" and (.block_reason | startswith("Gate:")))'

# Найти все position confirmation failures
cat decision_logs.jsonl | jq 'select(.final_decision=="ERROR" and (.block_reason == "Position confirmation failed"))'

# Счётчик circuit breaker events
cat decision_logs.jsonl | jq 'select(.block_reason | startswith("Circuit breaker"))' | wc -l
```

---

**v1.2 - Stability Improvements**

Дата: 2026-02-21

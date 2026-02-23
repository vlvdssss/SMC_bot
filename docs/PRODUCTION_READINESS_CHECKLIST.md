# Production Readiness Checklist - StateCore v1.2

## Перед запуском

### 1. Проверить конфигурацию

```yaml
# ai.yaml - trade_filters должны быть активны
trade_filters:
  enabled: true
  htf_gate:
    enabled: true
    timeframe: "M15"
  rr_gate:
    enabled: true
    min_rr: 1.2
  spread_gate:
    enabled: true
    max_pips: 3.0
  dynamic_cooldown:
    enabled: true
    win_cooldown_minutes: 15
    loss_cooldown_minutes: 90
    no_trade_cooldown_minutes: 240
  daily_limit:
    enabled: true
    max_trades_per_day: 6
  setup_score:
    enabled: true
    min_score: 70
```

### 2. Убедиться что background tasks запущены

```python
# В live_trader.py должно быть:
self.state_core = get_state_core()
self.state_core.set_mt5_connector(self.mt5_connector)
self.state_core.start_background_tasks()  # ← КРИТИЧНО

# При shutdown (если есть):
self.state_core.stop_background_tasks()
```

### 3. Проверить логи при старте

```
[StateCore] Initialized (singleton)
[StateCore] MT5 connector registered for watchdog
[StateCore] Background tasks started (watchdog, invariants)
[StateCore] MT5 Watchdog started
[StateCore] Invariants Checker started
```

---

## Monitoring в реальном времени

### StateCore Status

```python
snapshot = state_core.get_state_snapshot()

# Проверить статус
assert snapshot['bot_status'] in ['WAITING', 'ANALYZING', 'TRADING']
assert snapshot['mt5']['healthy'] == True
assert snapshot['recovery']['blocked'] == False

print(f"Status: {snapshot['bot_status']}")
print(f"MT5: {'✅' if snapshot['mt5']['healthy'] else '🚨'}")
print(f"Recovery: {'🔥 BLOCKED' if snapshot['recovery']['blocked'] else '✅ OK'}")
print(f"Errors (15min): {snapshot['recovery']['recent_errors']}")
```

### Event Monitoring

```python
def prod_event_monitor(event):
    event_type = event["type"]
    timestamp = event["timestamp"]
    
    if event_type == "position_confirmed":
        # OK: Position opened successfully
        print(f"[{timestamp}] ✅ Position confirmed: {event['data']}")
    
    elif event_type == "position_confirmation_failed":
        # CRITICAL: Position not confirmed after 3 retries
        print(f"[{timestamp}] 🚨 Position confirmation FAILED: {event['data']}")
        send_telegram_alert("🚨 Position confirmation failed")
    
    elif event_type == "mt5_disconnected":
        # WARNING: MT5 connection lost
        print(f"[{timestamp}] ⚠️ MT5 disconnected")
        send_telegram_alert("⚠️ MT5 connection lost")
    
    elif event_type == "mt5_reconnected":
        # OK: MT5 connection restored
        print(f"[{timestamp}] ✅ MT5 reconnected")
        send_telegram_alert("✅ MT5 connection restored")
    
    elif event_type == "circuit_breaker_triggered":
        # CRITICAL: Circuit breaker triggered
        data = event['data']
        print(f"[{timestamp}] 🔥 CIRCUIT BREAKER: {data['error_count']} errors")
        send_telegram_alert(f"🔥 Circuit breaker triggered: {data['error_count']} errors in 15min. Blocked until {data['blocked_until']}")
    
    elif event_type == "recovery_block_expired":
        # OK: Recovery block expired
        print(f"[{timestamp}] ✅ Recovery block expired - bot resumed")
        send_telegram_alert("✅ Recovery block expired")
    
    elif event_type == "invariants_violated":
        # ERROR: System invariants violated
        violations = event['data']['violations']
        print(f"[{timestamp}] ⚠️ Invariants violated: {violations}")
        send_telegram_alert(f"⚠️ Invariants violated: {violations}")

state_core.subscribe_to_events(prod_event_monitor)
```

---

## Decision Logs Analysis

### 1. Проверить что логи пишутся

```bash
# Последние 10 решений
tail -n 10 data/decision_logs.jsonl | jq '.'

# Должны быть:
# - final_decision: ENTER / HOLD / BLOCK / CLOSE
# - Для CLOSE: ticket, pnl, duration_minutes
```

### 2. Статистика за день

```bash
# Всего решений
cat data/decision_logs.jsonl | jq -s '. | length'

# По типам решений
cat data/decision_logs.jsonl | jq -s 'group_by(.final_decision) | .[] | {decision: .[0].final_decision, count: length}'

# Примерный вывод:
# {"decision": "ENTER", "count": 5}
# {"decision": "HOLD", "count": 12}
# {"decision": "BLOCK", "count": 8}
# {"decision": "CLOSE", "count": 4}
# {"decision": "ERROR", "count": 1}
```

### 3. Gate violations

```bash
# Все BLOCK от single gate
cat data/decision_logs.jsonl | jq 'select(.final_decision=="BLOCK" and (.block_reason | startswith("Gate:")))'

# Пример:
# {"block_reason": "Gate: No active_signal"}
# {"block_reason": "Gate: Recovery block (45min)"}
# {"block_reason": "Gate: MT5 disconnected"}
```

### 4. Position confirmation failures

```bash
# Все ERROR от position confirmation
cat data/decision_logs.jsonl | jq 'select(.final_decision=="ERROR" and (.block_reason == "Position confirmation failed"))'

# Если есть => КРИТИЧЕСКАЯ ПРОБЛЕМА с MT5
# Должно быть 0 в норме
```

### 5. CLOSE events с P&L

```bash
# Все закрытые сделки с P&L
cat data/decision_logs.jsonl | jq 'select(.final_decision=="CLOSE")'

# Средний P&L
cat data/decision_logs.jsonl | jq 'select(.final_decision=="CLOSE") | .pnl' | awk '{sum+=$1; count++} END {print "Avg P&L:", sum/count}'

# Средняя длительность
cat data/decision_logs.jsonl | jq 'select(.final_decision=="CLOSE") | .duration_minutes' | awk '{sum+=$1; count++} END {print "Avg Duration:", sum/count, "min"}'
```

---

## Alerting Rules

### CRITICAL (немедленная реакция)

1. **Circuit breaker triggered**
   - Что: Бот заблокирован на 2 часа из-за частых ошибок
   - Действие: Проверить логи, найти причину ошибок
   - Event: `circuit_breaker_triggered`

2. **Position confirmation failed**
   - Что: Order sent, но позиция не подтвердилась через 1.5s
   - Действие: Проверить MT5 connection, market conditions
   - Decision log: `final_decision=ERROR, block_reason=Position confirmation failed`

### WARNING (мониторить)

3. **MT5 disconnected**
   - Что: MT5 connection lost
   - Действие: Watchdog будет пытаться reconnect каждые 60s
   - Event: `mt5_disconnected`

4. **Invariants violated**
   - Что: Системные инварианты нарушены (напр. TRADING без позиции)
   - Действие: Checker автоматически исправит, но нужно изучить причину
   - Event: `invariants_violated`

5. **Gate blocks**
   - Что: Single gate заблокировал ордер (recovery mode, MT5 disconnect)
   - Действие: Норма если recovery mode активен, проверить если много gate blocks
   - Decision log: `final_decision=BLOCK, block_reason starts with "Gate:"`

### INFO (логировать)

6. **MT5 reconnected**
   - Что: Connection восстановлен после disconnect
   - Event: `mt5_reconnected`

7. **Recovery block expired**
   - Что: 2 часа circuit breaker истекли, бот возобновил работу
   - Event: `recovery_block_expired`

---

## Health Check Script

```python
#!/usr/bin/env python3
"""
Production health check for StateCore bot.
Run every 5 minutes via cron.
"""

import json
from datetime import datetime, timedelta
from src.core.state_core import get_state_core

def health_check():
    state_core = get_state_core()
    snapshot = state_core.get_state_snapshot()
    
    issues = []
    
    # Check 1: Bot status
    if snapshot['bot_status'] == 'ERROR':
        issues.append(f"🚨 Bot in ERROR state: {snapshot['block_reason']}")
    
    # Check 2: MT5 connection
    if not snapshot['mt5']['healthy']:
        issues.append(f"🚨 MT5 disconnected (reconnect attempts: {snapshot['mt5']['reconnect_attempts']})")
    
    # Check 3: Recovery block
    if snapshot['recovery']['blocked']:
        remaining = snapshot['recovery']['remaining_minutes']
        issues.append(f"⚠️ Bot in recovery block ({remaining} min remaining)")
    
    # Check 4: Recent errors
    recent_errors = snapshot['recovery']['recent_errors']
    if recent_errors >= 2:
        issues.append(f"⚠️ {recent_errors} errors in last 15 min (limit: 3)")
    
    # Check 5: Invariants violations
    violations = snapshot['invariants'].get('violations', [])
    if violations:
        issues.append(f"⚠️ Invariants violations: {violations}")
    
    # Check 6: MT5 watchdog last check
    mt5_last_check = snapshot['mt5']['last_check']
    if mt5_last_check:
        last_check_dt = datetime.fromisoformat(mt5_last_check)
        age_seconds = (datetime.now() - last_check_dt).total_seconds()
        if age_seconds > 60:  # More than 1 minute
            issues.append(f"⚠️ MT5 watchdog not running (last check: {age_seconds:.0f}s ago)")
    
    # Report
    if issues:
        print("=" * 60)
        print(f"HEALTH CHECK FAILED [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print("=" * 60)
        for issue in issues:
            print(issue)
        print("=" * 60)
        
        # Send alert
        alert_text = "\n".join(issues)
        send_telegram_alert(f"⚠️ Health check failed:\n{alert_text}")
        
        return False
    else:
        print(f"✅ Health check OK [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"Status: {snapshot['bot_status']}")
        print(f"MT5: OK")
        print(f"Recent errors: {recent_errors}/3")
        return True

def send_telegram_alert(text):
    """Send Telegram alert (implement based on your bot)."""
    # TODO: Implement Telegram bot API call
    pass

if __name__ == "__main__":
    health_check()
```

**Cron setup:**

```bash
# Run health check every 5 minutes
*/5 * * * * cd /path/to/bot && python health_check.py
```

---

## Expected Production Behavior

### Normal Operation

```
[StateCore] Status: WAITING
[StateCore] MT5 Watchdog: ✅ (last check: 12s ago)
[StateCore] Invariants: ✅ (last check: 45s ago)
[StateCore] Recovery: ✅ (no blocks)
[StateCore] Recent errors: 0/3

[TRADE] ✅ All gates passed for XAUUSD - proceeding to order execution
[TRADE] ✅ Order sent successfully for XAUUSD
[StateCore] ✅ Position confirmed: XAUUSD ticket=12345678 (attempt 1)
[StateCore] Position tracking: ticket=12345678, opened_at=2026-02-21T15:30:00
[StateCore] Status: WAITING → TRADING
```

### Position Confirmation Failure (Rare)

```
[TRADE] ✅ Order sent successfully for XAUUSD
[StateCore] No position found for XAUUSD (attempt 1/3)
[StateCore] No position found for XAUUSD (attempt 2/3)
[StateCore] No position found for XAUUSD (attempt 3/3)
[StateCore] 🚨 Position confirmation FAILED after 3 retries
[TRADE] 🚨 CRITICAL: Order sent but position NOT confirmed for XAUUSD
[StateCore] Status: ORDERING → ERROR (Order sent but no position)
[StateCore] Decision logged: ERROR - Position confirmation failed
[StateCore] Clearing active signal: Position confirmation failed
[StateCore] Error recorded: position_confirmation_failed (1/3 in 15min)
```

### MT5 Disconnect → Reconnect

```
[StateCore] 🚨 MT5 CONNECTION LOST
[StateCore] Status: WAITING → ERROR (MT5 disconnected)
[StateCore] Event: mt5_disconnected
[StateCore] Active signal present during disconnect - keeping for recovery

[StateCore] Attempting MT5 reconnect... (attempt 5)
[StateCore] MT5 reconnect successful

[StateCore] ✅ MT5 CONNECTION RESTORED (after 5 attempts)
[StateCore] Status: ERROR → WAITING
[StateCore] Event: mt5_reconnected
```

### Circuit Breaker (3 errors in 15 min)

```
[StateCore] Error recorded: position_confirmation_failed (1/3)
[StateCore] Error recorded: mt5_order_failed (2/3)
[StateCore] Error recorded: position_confirmation_failed (3/3)

[StateCore] 🚨 CIRCUIT BREAKER TRIGGERED: 3 errors in 15 min
[StateCore] Clearing active signal: XAUUSD_M5_...
[StateCore] Releasing all locks
[StateCore] Status: WAITING → BLOCKED (Circuit breaker: 3 errors in 15 min, blocked 2h)
[StateCore] Event: circuit_breaker_triggered
[StateCore] 🔥 AUTO-RECOVERY: Bot BLOCKED for 2 hours (until 17:30)

... 2 hours later ...

[StateCore] ✅ Recovery block expired - bot resumed
[StateCore] Status: BLOCKED → WAITING
[StateCore] Event: recovery_block_expired
```

### Invariants Violation → Auto-fix

```
[StateCore] Invariants check started
[StateCore] ⚠️ INVARIANT VIOLATION: TRADING but no position for XAUUSD
[StateCore] Status: TRADING → ERROR (Invariant: TRADING without position)
[StateCore] Clearing active signal
[StateCore] Event: invariants_violated (violations: ["TRADING without real position (XAUUSD)"])
[StateCore] Invariants check: 1 violations found
```

---

## Shutdown Procedure

```python
# Graceful shutdown
logger.info("Shutting down bot...")

# Stop background tasks
state_core.stop_background_tasks()

# Wait for tasks to finish (max 5s)
time.sleep(5)

# Close MT5 connection
mt5_connector.shutdown()

logger.info("Bot shut down successfully")
```

---

## FAQ

### Q: Как часто watchdog проверяет MT5?

**A:** Каждые ~12 секунд (10-15s диапазон).

### Q: Сколько времени дается на position confirmation?

**A:** 3 попытки x 0.5s = максимум 1.5 секунды.

### Q: Что происходит при circuit breaker?

**A:** Бот блокируется на 2 часа, release locks, clear active_signal, статус → BLOCKED.

### Q: Можно ли вручную снять circuit breaker block?

**A:** Да, через `state_core.recovery_blocked_until = None` или рестарт бота.

### Q: Как watchdog влияет на активную позицию?

**A:** Не влияет. При disconnect активный сигнал сохраняется для recovery. Но новые ордера блокируются (single gate).

### Q: Что если invariants checker найдет TRADING без позиции?

**A:** Автоматически: статус → ERROR, active_signal cleared. Логируется событие.

---

**Production Readiness: ✅ READY**

StateCore v1.2 готов к production с полной защитой от:
- Несуществующих позиций (position confirmation + invariants)
- MT5 disconnects (watchdog + auto-reconnect)
- Cascade failures (circuit breaker)
- Invalid states (invariants checker)
- Обходных путей (single gate)

Дата: 2026-02-21

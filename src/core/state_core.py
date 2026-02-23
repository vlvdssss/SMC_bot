"""
StateCore - Единый источник правды для состояния бота
Минимальный state manager без рефакторинга всей архитектуры
"""

import threading
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from collections import deque

from src.core.logger import logger


class BotStatus(Enum):
    """Единая enum для статусов бота."""
    IDLE = "IDLE"                    # Начальное состояние
    WAITING = "WAITING"              # Ожидание следующего цикла
    ANALYZING = "ANALYZING"          # GPT анализ в процессе
    BLOCKED = "BLOCKED"              # Заблокирован (cooldown/filters/risk)
    ORDERING = "ORDERING"            # Выставление ордера
    TRADING = "TRADING"              # Позиция открыта
    ERROR = "ERROR"                  # Ошибка


@dataclass
class ActiveSignal:
    """Активный сигнал (тот по которому торгуем)."""
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
    ticket: Optional[int] = None  # MT5 ticket ID (устанавливается после order_send)
    opened_at: Optional[str] = None  # Timestamp открытия позиции
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LastAnalysis:
    """Последний GPT анализ (может отличаться от active_signal)."""
    signal_id: str
    symbol: str
    action: str
    confidence: int
    reasoning: str
    timestamp: str
    filters_passed: bool = False
    block_reason: Optional[str] = None
    setup_score: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DecisionLog:
    """Structured log для каждой попытки сигнала."""
    signal_id: str
    timestamp: str
    symbol: str
    raw_signal: str  # BUY/SELL/HOLD
    gpt_confidence: int
    gpt_reasoning: str
    filters: Dict[str, Any]  # htf/rr/spread/cooldown/daily_limit
    setup_score: int
    final_decision: str  # ENTER/HOLD/BLOCK/DUPLICATE/INVALID/ERROR/CLOSE
    block_reason: Optional[str]
    ticket: Optional[int] = None  # Для CLOSE events
    pnl: Optional[float] = None  # Для CLOSE events
    duration_minutes: Optional[int] = None  # Для CLOSE events
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON строка для логов."""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class StateCore:
    """
    Легковесный state manager - единый источник правды.
    
    Без рефакторинга архитектуры, просто централизует состояние.
    UI/LiveTrader/SignalManager читают/пишут через StateCore.
    """
    
    # Singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Защита от повторной инициализации singleton
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._state_lock = threading.Lock()
        
        # === CORE STATE ===
        self.bot_status: BotStatus = BotStatus.IDLE
        self.active_signal: Optional[ActiveSignal] = None
        self.last_analysis: Optional[LastAnalysis] = None
        
        # === BLOCKS & COOLDOWNS ===
        self.block_reason: Optional[str] = None
        self.cooldown_until: Optional[datetime] = None
        
        # === LOCKS (защита от дублей) ===
        self.order_lock: bool = False
        self.order_lock_acquired_at: Optional[datetime] = None  # Auto-timeout tracking
        self.analysis_lock: bool = False
        self.analysis_lock_acquired_at: Optional[datetime] = None  # Auto-timeout tracking
        
        # === TIMESTAMPS ===
        self.last_run_ts: Optional[datetime] = None
        self.last_order_ts: Optional[datetime] = None
        self.last_ui_update_ts: Optional[datetime] = None
        
        # === SIGNAL TRACKING (дедупликация с TTL) ===
        self.last_traded_signal_id: Optional[str] = None
        self.processed_signal_ids: Dict[str, datetime] = {}  # signal_id -> timestamp (TTL 24h)
        
        # === DECISION LOGS ===
        self.decision_logs: list = []
        self.decision_log_file = Path("data/decision_logs.jsonl")
        self.decision_log_file.parent.mkdir(exist_ok=True)
        
        # === PIPELINE INDICATORS ===
        self.pipeline = {
            "data": "IDLE",
            "signal": "IDLE",
            "gpt": "IDLE",
            "risk": "IDLE",
            "order": "IDLE"
        }
        
        # === AUTO-RECOVERY (circuit breaker) ===
        self.error_history: deque = deque(maxlen=10)  # Last 10 errors with timestamps
        self.recovery_blocked_until: Optional[datetime] = None
        
        # === EVENT BUS (StateCore → UI) ===
        self.event_queue: deque = deque(maxlen=100)  # Last 100 events
        self.event_subscribers: list[Callable] = []  # Callback functions
        
        # === MT5 WATCHDOG ===
        self.mt5_connector = None  # Set externally
        self.mt5_last_check: Optional[datetime] = None
        self.mt5_connection_healthy: bool = True
        self.mt5_reconnect_attempts: int = 0
        
        # === INVARIANTS CHECKER ===
        self.invariants_last_check: Optional[datetime] = None
        self.invariants_violations: list = []
        
        # === BACKGROUND TASKS ===
        self._watchdog_thread: Optional[threading.Thread] = None
        self._invariants_thread: Optional[threading.Thread] = None
        self._shutdown_flag = threading.Event()
        
        logger.info("[StateCore] Initialized (singleton)")
    
    # ==================== STATUS MANAGEMENT ====================
    
    def set_status(self, status: BotStatus, reason: Optional[str] = None):
        """
        Установить статус бота.
        
        Args:
            status: Новый статус
            reason: Причина смены статуса (для BLOCKED/ERROR)
        """
        with self._state_lock:
            old_status = self.bot_status
            self.bot_status = status
            
            if status == BotStatus.BLOCKED and reason:
                self.block_reason = reason
            elif status != BotStatus.BLOCKED:
                self.block_reason = None
            
            self.last_ui_update_ts = datetime.now()
            
            if old_status != status:
                logger.info(f"[StateCore] Status: {old_status.value} → {status.value}" + 
                          (f" ({reason})" if reason else ""))
    
    def get_status(self) -> tuple[BotStatus, Optional[str]]:
        """Получить текущий статус и причину блокировки."""
        with self._state_lock:
            return self.bot_status, self.block_reason
    
    # ==================== SIGNAL MANAGEMENT ====================
    
    def set_active_signal(self, signal: ActiveSignal):
        """
        Установить активный сигнал (тот по которому торгуем).
        
        КРИТИЧНО: Только для ENTER решений (action = BUY/SELL).
        HOLD НИКОГДА не должен попадать сюда.
        
        Автоматически:
        - Проверяет дедупликацию (TTL)
        - Обновляет статус
        - Записывает signal_id с timestamp
        """
        with self._state_lock:
            # PRODUCTION GUARD: HOLD никогда не должен быть active_signal
            if signal.action == "HOLD":
                logger.error(f"[StateCore] 🚨 CRITICAL: Attempted to set HOLD as active_signal - REJECTED")
                return False
            
            # Cleanup old signal_ids (TTL)
            self._cleanup_old_signal_ids()
            
            # Защита от дублей
            if signal.signal_id in self.processed_signal_ids:
                age_seconds = (datetime.now() - self.processed_signal_ids[signal.signal_id]).total_seconds()
                logger.warning(f"[StateCore] ⚠️ Duplicate signal_id: {signal.signal_id} (age: {age_seconds:.0f}s) - IGNORED")
                return False
            
            self.active_signal = signal
            self.processed_signal_ids[signal.signal_id] = datetime.now()
            self.last_ui_update_ts = datetime.now()
            
            logger.info(f"[StateCore] Active signal set: {signal.action} {signal.symbol} (ID: {signal.signal_id[:12]}...)")
            return True
    
    def clear_active_signal(self, reason: str = "Position closed"):
        """Очистить активный сигнал."""
        with self._state_lock:
            if self.active_signal:
                logger.info(f"[StateCore] Clearing active signal: {self.active_signal.signal_id[:12]}... ({reason})")
                
                # Сохраняем signal_id как последний торгованный
                self.last_traded_signal_id = self.active_signal.signal_id
                
                self.active_signal = None
                self.last_ui_update_ts = datetime.now()
    
    def set_last_analysis(self, analysis: LastAnalysis):
        """Установить последний GPT анализ (может не стать активным сигналом)."""
        with self._state_lock:
            self.last_analysis = analysis
            self.last_ui_update_ts = datetime.now()
            
            logger.debug(f"[StateCore] Last analysis updated: {analysis.action} ({analysis.confidence}%)")
    
    # ==================== LOCKS ====================
    
    def acquire_order_lock(self) -> bool:
        """
        Попытка получить order lock (защита от двойных ордеров).
        
        PRODUCTION GUARD: Проверяет наличие active_signal перед выдачей lock.
        """
        with self._state_lock:
            # Check auto-timeout (30 seconds)
            if self.order_lock and self.order_lock_acquired_at:
                elapsed = (datetime.now() - self.order_lock_acquired_at).total_seconds()
                if elapsed > 30:
                    logger.error(f"[StateCore] 🚨 Order lock timeout ({elapsed:.0f}s > 30s) - AUTO RELEASE")
                    self.order_lock = False
                    self.order_lock_acquired_at = None
                    self.set_status(BotStatus.ERROR, reason="Order lock timeout")
            
            if self.order_lock:
                logger.warning("[StateCore] ⚠️ Order lock already held!")
                return False
            
            # PRODUCTION GUARD: Единственный путь к ордеру - через active_signal
            if not self.active_signal:
                logger.error("[StateCore] 🚨 CRITICAL: Cannot acquire order lock - no active_signal")
                return False
            
            if self.active_signal.action == "HOLD":
                logger.error("[StateCore] 🚨 CRITICAL: Cannot acquire order lock - active_signal is HOLD")
                return False
            
            self.order_lock = True
            self.order_lock_acquired_at = datetime.now()
            logger.debug("[StateCore] 🔒 Order lock acquired")
            return True
    
    def release_order_lock(self):
        """Освободить order lock."""
        with self._state_lock:
            self.order_lock = False
            self.order_lock_acquired_at = None
            logger.debug("[StateCore] 🔓 Order lock released")
    
    def acquire_analysis_lock(self) -> bool:
        """Попытка получить analysis lock (защита от двойных GPT запросов)."""
        with self._state_lock:
            # Check auto-timeout (90 seconds)
            if self.analysis_lock and self.analysis_lock_acquired_at:
                elapsed = (datetime.now() - self.analysis_lock_acquired_at).total_seconds()
                if elapsed > 90:
                    logger.error(f"[StateCore] 🚨 Analysis lock timeout ({elapsed:.0f}s > 90s) - AUTO RELEASE")
                    self.analysis_lock = False
                    self.analysis_lock_acquired_at = None
                    self.set_status(BotStatus.ERROR, reason="Analysis lock timeout")
            
            if self.analysis_lock:
                logger.warning("[StateCore] ⚠️ Analysis lock already held!")
                return False
            
            self.analysis_lock = True
            self.analysis_lock_acquired_at = datetime.now()
            logger.debug("[StateCore] 🔒 Analysis lock acquired")
            return True
    
    def release_analysis_lock(self):
        """Освободить analysis lock."""
        with self._state_lock:
            self.analysis_lock = False
            self.analysis_lock_acquired_at = None
            logger.debug("[StateCore] 🔓 Analysis lock released")
    
    # ==================== COOLDOWN ====================
    
    def set_cooldown(self, minutes: int, reason: str):
        """Установить cooldown."""
        with self._state_lock:
            self.cooldown_until = datetime.now() + timedelta(minutes=minutes)
            self.set_status(BotStatus.BLOCKED, reason=f"{reason} (cooldown {minutes} min)")
            
            logger.warning(f"[StateCore] 🕐 Cooldown set: {minutes} min ({reason})")
    
    def is_in_cooldown(self) -> tuple[bool, Optional[int]]:
        """
        Проверить активен ли cooldown.
        
        Returns:
            (in_cooldown: bool, remaining_minutes: Optional[int])
        """
        with self._state_lock:
            if not self.cooldown_until:
                return False, None
            
            now = datetime.now()
            if now < self.cooldown_until:
                remaining = int((self.cooldown_until - now).total_seconds() / 60)
                return True, remaining
            else:
                # Cooldown истёк
                self.cooldown_until = None
                if self.bot_status == BotStatus.BLOCKED:
                    self.set_status(BotStatus.WAITING)
                return False, None
    
    # ==================== DECISION LOGGING ====================
    
    def log_decision(self, decision: DecisionLog):
        """
        Записать решение (почему вошли/почему отказались).
        
        Формат: 1 строка JSON на каждую попытку.
        """
        try:
            # Add to memory
            self.decision_logs.append(decision)
            
            # Keep last 100 in memory
            if len(self.decision_logs) > 100:
                self.decision_logs = self.decision_logs[-100:]
            
            # Append to file (JSONL format)
            with open(self.decision_log_file, 'a', encoding='utf-8') as f:
                f.write(decision.to_json() + '\n')
            
            # Log summary
            logger.info(
                f"[StateCore] Decision: {decision.final_decision} | "
                f"{decision.raw_signal} {decision.symbol} ({decision.gpt_confidence}%) | "
                f"Score: {decision.setup_score} | "
                f"Reason: {decision.block_reason or 'OK'}"
            )
            
        except Exception as e:
            logger.error(f"[StateCore] Failed to log decision: {e}")
    
    def get_recent_decisions(self, count: int = 10) -> list[Dict]:
        """Получить последние N решений."""
        with self._state_lock:
            return [d.to_dict() for d in self.decision_logs[-count:]]
    
    # ==================== PIPELINE INDICATORS ====================
    
    def set_pipeline_step(self, step: str, state: str):
        """
        Установить состояние шага pipeline.
        
        Args:
            step: data/signal/gpt/risk/order
            state: IDLE/ACTIVE/SUCCESS/FAIL
        """
        with self._state_lock:
            if step in self.pipeline:
                self.pipeline[step] = state
                logger.debug(f"[StateCore] Pipeline: {step} → {state}")
    
    # ==================== SNAPSHOTS ====================
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Получить полный snapshot состояния (для UI/debug)."""
        with self._state_lock:
            in_cooldown, cooldown_min = self.is_in_cooldown()
            in_recovery, recovery_min = self.is_recovery_blocked()
            
            return {
                "bot_status": self.bot_status.value,
                "active_signal": self.active_signal.to_dict() if self.active_signal else None,
                "last_analysis": self.last_analysis.to_dict() if self.last_analysis else None,
                "block_reason": self.block_reason,
                "cooldown": {
                    "active": in_cooldown,
                    "remaining_minutes": cooldown_min,
                    "until": self.cooldown_until.isoformat() if self.cooldown_until else None
                },
                "recovery": {
                    "blocked": in_recovery,
                    "remaining_minutes": recovery_min,
                    "until": self.recovery_blocked_until.isoformat() if self.recovery_blocked_until else None,
                    "recent_errors": len([e for e in self.error_history if (datetime.now() - e["timestamp"]).total_seconds() < 900])
                },
                "locks": {
                    "order": self.order_lock,
                    "analysis": self.analysis_lock
                },
                "mt5": {
                    "healthy": self.mt5_connection_healthy,
                    "last_check": self.mt5_last_check.isoformat() if self.mt5_last_check else None,
                    "reconnect_attempts": self.mt5_reconnect_attempts
                },
                "invariants": {
                    "last_check": self.invariants_last_check.isoformat() if self.invariants_last_check else None,
                    "violations": self.invariants_violations
                },
                "timestamps": {
                    "last_run": self.last_run_ts.isoformat() if self.last_run_ts else None,
                    "last_order": self.last_order_ts.isoformat() if self.last_order_ts else None,
                    "last_ui_update": self.last_ui_update_ts.isoformat() if self.last_ui_update_ts else None
                },
                "pipeline": self.pipeline,
                "recent_signals": len(self.processed_signal_ids),
                "event_queue_size": len(self.event_queue)
            }
    
    # ==================== UTILITIES ====================
    
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
            logger.warning(f"[StateCore] Cannot log CLOSE event - no signal_id (ticket={ticket})")
            return
        
        # Calculate duration
        duration_minutes = None
        if self.active_signal and self.active_signal.opened_at:
            try:
                opened = datetime.fromisoformat(self.active_signal.opened_at)
                duration_minutes = int((datetime.now() - opened).total_seconds() / 60)
            except Exception as e:
                logger.debug(f"[StateCore] Failed to calculate duration: {e}")
        
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
        logger.info(f"[StateCore] CLOSE event logged: ticket={ticket}, P&L=${pnl:.2f}, duration={duration_minutes}min")
    
    # ==================== POSITION CONFIRMATION ====================
    
    def confirm_position_opened(self, symbol: str, expected_ticket: Optional[int] = None, 
                                retries: int = 3, delay: float = 0.5) -> tuple[bool, Optional[int]]:
        """
        Подтверждение открытия позиции через positions_get с retry.
        
        Args:
            symbol: Символ для проверки
            expected_ticket: Ожидаемый ticket (optional)
            retries: Количество попыток
            delay: Задержка между попытками (секунды)
        
        Returns:
            (success: bool, ticket: Optional[int])
        """
        if not self.mt5_connector:
            logger.error("[StateCore] Cannot confirm position - mt5_connector not set")
            return False, None
        
        for attempt in range(1, retries + 1):
            try:
                import MetaTrader5 as mt5
                
                # Check for open position
                positions = mt5.positions_get(symbol=symbol)
                
                if positions and len(positions) > 0:
                    # Position found
                    ticket = positions[-1].ticket
                    
                    # If expected_ticket provided, validate it
                    if expected_ticket and ticket != expected_ticket:
                        logger.warning(
                            f"[StateCore] Position ticket mismatch: expected={expected_ticket}, found={ticket} "
                            f"(attempt {attempt}/{retries})"
                        )
                        if attempt < retries:
                            time.sleep(delay)
                            continue
                    
                    logger.info(f"[StateCore] ✅ Position confirmed: {symbol} ticket={ticket} (attempt {attempt})")
                    self._emit_event("position_confirmed", {"symbol": symbol, "ticket": ticket})
                    return True, ticket
                else:
                    # No position found
                    logger.warning(
                        f"[StateCore] No position found for {symbol} (attempt {attempt}/{retries})"
                    )
                    
                    if attempt < retries:
                        time.sleep(delay)
                        continue
            
            except Exception as e:
                logger.error(f"[StateCore] Position check error (attempt {attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(delay)
                    continue
        
        # All retries failed
        logger.error(f"[StateCore] 🚨 Position confirmation FAILED after {retries} retries")
        self._emit_event("position_confirmation_failed", {"symbol": symbol, "retries": retries})
        self._record_error("position_confirmation_failed")
        return False, None
    
    # ==================== AUTO-RECOVERY (Circuit Breaker) ====================
    
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
        
        # Count recent errors
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
                    f"[StateCore] 🚨 CIRCUIT BREAKER TRIGGERED: {len(recent_errors)} errors in 15 min. "
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
                f"[StateCore] 🔥 AUTO-RECOVERY: Bot BLOCKED for 2 hours (until {self.recovery_blocked_until.strftime('%H:%M')})"
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
                    logger.info("[StateCore] ✅ Recovery block expired - bot resumed")
                    self._emit_event("recovery_block_expired", {})
                return False, None
    
    # ==================== EVENT BUS ====================
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to queue and notify subscribers."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        self.event_queue.append(event)
        
        # Notify subscribers (non-blocking)
        for callback in self.event_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"[StateCore] Event subscriber error: {e}")
    
    def subscribe_to_events(self, callback: Callable):
        """Subscribe to StateCore events."""
        if callback not in self.event_subscribers:
            self.event_subscribers.append(callback)
            logger.info(f"[StateCore] Event subscriber added: {callback.__name__}")
    
    def get_recent_events(self, count: int = 20) -> list[Dict]:
        """Get recent events from queue."""
        return list(self.event_queue)[-count:]
    
    # ==================== INVARIANTS CHECKER ====================
    
    def check_invariants(self):
        """Check system invariants and fix violations."""
        violations = []
        
        with self._state_lock:
            now = datetime.now()
            
            # INVARIANT 1: TRADING status must have open position
            if self.bot_status == BotStatus.TRADING:
                if not self.active_signal:
                    violations.append("TRADING without active_signal")
                    logger.error("[StateCore] ⚠️ INVARIANT VIOLATION: TRADING without active_signal")
                    self.set_status(BotStatus.ERROR, reason="Invariant: TRADING without active_signal")
                
                elif self.mt5_connector:
                    try:
                        import MetaTrader5 as mt5
                        positions = mt5.positions_get(symbol=self.active_signal.symbol)
                        if not positions or len(positions) == 0:
                            violations.append(f"TRADING without real position ({self.active_signal.symbol})")
                            logger.error(
                                f"[StateCore] ⚠️ INVARIANT VIOLATION: TRADING but no position for {self.active_signal.symbol}"
                            )
                            self.set_status(BotStatus.ERROR, reason="Invariant: TRADING without position")
                            self.active_signal = None
                    except Exception as e:
                        logger.error(f"[StateCore] Invariant check error: {e}")
            
            # INVARIANT 2: Locks should not be held forever
            if self.order_lock and self.order_lock_acquired_at:
                elapsed = (now - self.order_lock_acquired_at).total_seconds()
                if elapsed > 60:  # More than 1 minute
                    violations.append(f"order_lock held for {elapsed:.0f}s")
                    logger.error(f"[StateCore] ⚠️ INVARIANT VIOLATION: order_lock held for {elapsed:.0f}s - RELEASING")
                    self.order_lock = False
                    self.order_lock_acquired_at = None
            
            if self.analysis_lock and self.analysis_lock_acquired_at:
                elapsed = (now - self.analysis_lock_acquired_at).total_seconds()
                if elapsed > 120:  # More than 2 minutes
                    violations.append(f"analysis_lock held for {elapsed:.0f}s")
                    logger.error(f"[StateCore] ⚠️ INVARIANT VIOLATION: analysis_lock held for {elapsed:.0f}s - RELEASING")
                    self.analysis_lock = False
                    self.analysis_lock_acquired_at = None
            
            # INVARIANT 3: active_signal must never be HOLD
            if self.active_signal and self.active_signal.action == "HOLD":
                violations.append("active_signal.action == HOLD")
                logger.error("[StateCore] ⚠️ INVARIANT VIOLATION: active_signal is HOLD - CLEARING")
                self.active_signal = None
            
            # Store violations
            if violations:
                self.invariants_violations = violations
                self._emit_event("invariants_violated", {"violations": violations})
            
            self.invariants_last_check = now
        
        return violations
    
    # ==================== MT5 WATCHDOG ====================
    
    def set_mt5_connector(self, connector):
        """Set MT5 connector reference for watchdog."""
        self.mt5_connector = connector
        logger.info("[StateCore] MT5 connector registered for watchdog")
    
    def check_mt5_connection(self) -> bool:
        """Check MT5 connection health."""
        if not self.mt5_connector:
            return True  # No connector, assume OK
        
        try:
            import MetaTrader5 as mt5
            
            # Check terminal connection
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                logger.error("[StateCore] MT5 terminal_info() failed")
                return False
            
            # Check account info
            account_info = mt5.account_info()
            if not account_info:
                logger.error("[StateCore] MT5 account_info() failed")
                return False
            
            # Check connection flag
            if not terminal_info.connected:
                logger.error("[StateCore] MT5 terminal not connected")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"[StateCore] MT5 connection check error: {e}")
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
                        logger.error("[StateCore] 🚨 MT5 CONNECTION LOST")
                        self.mt5_connection_healthy = False
                        self.set_status(BotStatus.ERROR, reason="MT5 disconnected")
                        self._emit_event("mt5_disconnected", {})
                        
                        # Stop trading if position active
                        if self.active_signal:
                            logger.warning("[StateCore] Active signal present during disconnect - keeping for recovery")
                    
                    elif healthy and not self.mt5_connection_healthy:
                        # Connection restored
                        logger.info(f"[StateCore] ✅ MT5 CONNECTION RESTORED (after {self.mt5_reconnect_attempts} attempts)")
                        self.mt5_connection_healthy = True
                        self.mt5_reconnect_attempts = 0
                        
                        if self.bot_status == BotStatus.ERROR:
                            self.set_status(BotStatus.WAITING)
                        
                        self._emit_event("mt5_reconnected", {})
                    
                    elif not healthy:
                        # Still disconnected, try reconnect
                        self.mt5_reconnect_attempts += 1
                        
                        if self.mt5_reconnect_attempts % 5 == 0:  # Every ~60s (5 * 12s)
                            logger.warning(
                                f"[StateCore] Attempting MT5 reconnect... (attempt {self.mt5_reconnect_attempts})"
                            )
                            try:
                                import MetaTrader5 as mt5
                                if mt5.initialize():
                                    logger.info("[StateCore] MT5 reconnect successful")
                            except Exception as e:
                                logger.error(f"[StateCore] MT5 reconnect failed: {e}")
            
            except Exception as e:
                logger.error(f"[StateCore] Watchdog error: {e}")
        
        logger.info("[StateCore] MT5 Watchdog stopped")
    
    def _invariants_checker_loop(self):
        """Background thread: Invariants checker (every 60 seconds)."""
        logger.info("[StateCore] Invariants Checker started")
        
        while not self._shutdown_flag.is_set():
            try:
                time.sleep(60)  # Check every minute
                
                violations = self.check_invariants()
                
                if violations:
                    logger.warning(f"[StateCore] Invariants check: {len(violations)} violations found")
                else:
                    logger.debug("[StateCore] Invariants check: OK")
            
            except Exception as e:
                logger.error(f"[StateCore] Invariants checker error: {e}")
        
        logger.info("[StateCore] Invariants Checker stopped")
    
    def start_background_tasks(self):
        """Start background tasks (watchdog, invariants checker)."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            logger.warning("[StateCore] Background tasks already running")
            return
        
        self._shutdown_flag.clear()
        
        # Start MT5 watchdog
        self._watchdog_thread = threading.Thread(
            target=self._mt5_watchdog_loop,
            name="StateCore-MT5Watchdog",
            daemon=True
        )
        self._watchdog_thread.start()
        
        # Start invariants checker
        self._invariants_thread = threading.Thread(
            target=self._invariants_checker_loop,
            name="StateCore-InvariantsChecker",
            daemon=True
        )
        self._invariants_thread.start()
        
        logger.info("[StateCore] Background tasks started (watchdog, invariants)")
    
    def stop_background_tasks(self):
        """Stop background tasks."""
        self._shutdown_flag.set()
        
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=5)
        
        if self._invariants_thread:
            self._invariants_thread.join(timeout=5)
        
        logger.info("[StateCore] Background tasks stopped")
    
    def reset(self):
        """Сброс состояния (для тестов или рестарта)."""
        with self._state_lock:
            self.bot_status = BotStatus.IDLE
            self.active_signal = None
            self.last_analysis = None
            self.block_reason = None
            self.cooldown_until = None
            self.order_lock = False
            self.order_lock_acquired_at = None
            self.analysis_lock = False
            self.analysis_lock_acquired_at = None
            self.processed_signal_ids.clear()
            self.error_history.clear()
            self.recovery_blocked_until = None
            
            logger.info("[StateCore] State reset")


# ==================== GLOBAL INSTANCE ====================

# Singleton instance
_state_core = None

def get_state_core() -> StateCore:
    """Get singleton instance of StateCore."""
    global _state_core
    if _state_core is None:
        _state_core = StateCore()
    return _state_core

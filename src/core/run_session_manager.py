"""
Run Session Manager - управление прогоном и мониторинг событий
Хранит состояние, события, метрики для вкладки RUN/MONITOR
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import defaultdict, deque
from dataclasses import dataclass, asdict

from src.core.logger import logger


@dataclass
class RunState:
    """Состояние текущего прогона"""
    run_id: str  # YYYYMMDD_HHMM
    start_time: str  # ISO datetime
    status: str  # ACTIVE/PAUSED/STOPPED
    current_day: int  # 1-5
    total_days: int  # 5 по умолчанию
    elapsed_seconds: int
    
    # Counters Today
    today_mt5_disconnected: int = 0
    today_reconnect: int = 0
    today_invariants: int = 0
    today_order_lock_timeout: int = 0
    today_analysis_lock_timeout: int = 0
    today_circuit_breaker: int = 0
    today_orders_sent: int = 0
    today_positions_opened: int = 0
    today_positions_closed: int = 0
    today_enters: int = 0
    today_holds: int = 0
    today_blocks: int = 0
    
    # Counters Total
    total_mt5_disconnected: int = 0
    total_reconnect: int = 0
    total_invariants: int = 0
    total_order_lock_timeout: int = 0
    total_analysis_lock_timeout: int = 0
    total_circuit_breaker: int = 0
    total_orders_sent: int = 0
    total_positions_opened: int = 0
    total_positions_closed: int = 0
    total_enters: int = 0
    total_holds: int = 0
    total_blocks: int = 0
    
    # Last reset time для today counters
    last_day_reset: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'RunState':
        return RunState(**data)


class RunSessionManager:
    """
    Управление прогоном бота:
    - Создание/загрузка/сохранение run sessions
    - Подписка на StateCore events
    - Автосохранение каждые 60s
    - JSONL логирование событий
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Run state
        self.current_run: Optional[RunState] = None
        self.run_dir: Optional[Path] = None
        
        # Event queue (для GUI)
        self.event_queue: deque = deque(maxlen=1000)
        
        # Event buffer для батчинга записи в файл (flush каждые 2s)
        self.event_buffer: List[Dict[str, Any]] = []
        self.event_buffer_lock = threading.Lock()
        
        # Auto-save thread
        self._shutdown_flag = threading.Event()
        self._autosave_thread: Optional[threading.Thread] = None
        self._flush_thread: Optional[threading.Thread] = None
        
        # Suggestions
        self.suggestions: List[Dict[str, str]] = []
        
        # Base dir
        self.runs_dir = Path("data/runs")
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("[RunSessionManager] Initialized")
    
    # ==================== RUN CONTROL ====================
    
    def start_new_run(self, days: int = 5) -> bool:
        """Начать новый прогон"""
        with self.lock:
            if self.current_run and self.current_run.status == "ACTIVE":
                logger.warning("[RunSessionManager] Run already active")
                return False
            
            # Create run ID
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create run directory
            self.run_dir = self.runs_dir / f"run_{run_id}"
            self.run_dir.mkdir(exist_ok=True)
            
            # Initialize state
            self.current_run = RunState(
                run_id=run_id,
                start_time=datetime.now().isoformat(),
                status="ACTIVE",
                current_day=1,
                total_days=days,
                elapsed_seconds=0,
                last_day_reset=datetime.now().isoformat()
            )
            
            # Clear queues
            self.event_queue.clear()
            self.suggestions.clear()
            
            # Save initial state
            self._save_state()
            
            # Start autosave and flush threads
            self._start_autosave()
            self._start_flush_thread()
            
            logger.info(f"[RunSessionManager] Started new {days}-day run: {run_id}")
            self._log_event("run_started", {"run_id": run_id, "days": days})
            
            return True
    
    def save_run_config(self, effective_config: Dict[str, Any], preflight_report: Dict[str, Any]) -> bool:
        """
        Сохранить эффективную конфигурацию и pre-flight report в папку прогона
        
        Args:
            effective_config: эффективная конфигурация из ConfigManager
            preflight_report: результаты pre-flight checks
            
        Returns:
            bool: успех операции
        """
        if not self.run_dir:
            logger.error("[RunSessionManager] No active run directory")
            return False
        
        try:
            # Save effective config
            config_file = self.run_dir / "run_effective_config_start.yaml"
            import yaml
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'timestamp': datetime.now().isoformat(),
                    'purpose': '5-day production run baseline',
                    'config': effective_config
                }, f, default_flow_style=False, allow_unicode=True)
            
            # Save preflight report
            preflight_file = self.run_dir / "preflight_report.json"
            with open(preflight_file, 'w', encoding='utf-8') as f:
                json.dump(preflight_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[RunSessionManager] ✅ Saved config to {config_file}")
            logger.info(f"[RunSessionManager] ✅ Saved preflight report to {preflight_file}")
            return True
            
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to save run config: {e}")
            return False
    
    def pause_run(self):
        """Пауза прогона"""
        with self.lock:
            if not self.current_run:
                return
            
            if self.current_run.status == "ACTIVE":
                self.current_run.status = "PAUSED"
                self._save_state()
                logger.info("[RunSessionManager] Run paused")
                self._log_event("run_paused", {})
    
    def resume_run(self):
        """Возобновить прогон"""
        with self.lock:
            if not self.current_run:
                return
            
            if self.current_run.status == "PAUSED":
                self.current_run.status = "ACTIVE"
                self._save_state()
                logger.info("[RunSessionManager] Run resumed")
                self._log_event("run_resumed", {})
    
    def stop_run(self):
        """Остановить прогон"""
        with self.lock:
            if not self.current_run:
                return
            
            self.current_run.status = "STOPPED"
            
            # Flush events перед остановкой
            self._flush_event_buffer()
            
            self._save_state()
            
            # Stop autosave and flush threads
            self._shutdown_flag.set()
            if self._autosave_thread:
                self._autosave_thread.join(timeout=2)
            if self._flush_thread:
                self._flush_thread.join(timeout=2)
            
            logger.info("[RunSessionManager] Run stopped")
            self._log_event("run_stopped", {"elapsed": self.current_run.elapsed_seconds})
    
    def reset_run(self):
        """Сброс прогона"""
        with self.lock:
            if self.current_run:
                self.stop_run()
            
            self.current_run = None
            self.run_dir = None
            self.event_queue.clear()
            self.suggestions.clear()
            
            logger.info("[RunSessionManager] Run reset")
    
    # ==================== STATE PERSISTENCE ====================
    
    def _save_state(self):
        """Сохранить состояние в файл"""
        if not self.current_run or not self.run_dir:
            return
        
        try:
            state_file = self.run_dir / "run_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_run.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.debug(f"[RunSessionManager] State saved to {state_file}")
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to save state: {e}")
    
    def load_run(self, run_id: str) -> bool:
        """Загрузить прогон из файла"""
        with self.lock:
            run_dir = self.runs_dir / f"run_{run_id}"
            state_file = run_dir / "run_state.json"
            
            if not state_file.exists():
                logger.error(f"[RunSessionManager] Run state not found: {run_id}")
                return False
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.current_run = RunState.from_dict(data)
                self.run_dir = run_dir
                
                # Load events
                self._load_events()
                
                # Resume autosave if active
                if self.current_run.status == "ACTIVE":
                    self._start_autosave()
                
                logger.info(f"[RunSessionManager] Loaded run: {run_id}")
                return True
            
            except Exception as e:
                logger.error(f"[RunSessionManager] Failed to load run: {e}")
                return False
    
    def list_runs(self) -> List[Dict[str, Any]]:
        """Список доступных прогонов"""
        runs = []
        for run_dir in sorted(self.runs_dir.glob("run_*"), reverse=True):
            state_file = run_dir / "run_state.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    runs.append({
                        "run_id": data["run_id"],
                        "start_time": data["start_time"],
                        "status": data["status"],
                        "days": data["total_days"]
                    })
                except:
                    pass
        return runs
    
    # ==================== EVENT HANDLING ====================
    
    def handle_statecore_event(self, event: Dict[str, Any]):
        """Обработчик событий от StateCore"""
        if not self.current_run or self.current_run.status != "ACTIVE":
            return
        
        event_type = event.get("type")
        timestamp = event.get("timestamp")
        data = event.get("data", {})
        
        # Log event
        self._log_event(event_type, data)
        
        # Update counters
        with self.lock:
            if event_type == "mt5_disconnected":
                self.current_run.today_mt5_disconnected += 1
                self.current_run.total_mt5_disconnected += 1
                self._add_suggestion("warning", f"MT5 disconnected at {timestamp}")
            
            elif event_type == "mt5_reconnected":
                self.current_run.today_reconnect += 1
                self.current_run.total_reconnect += 1
            
            elif event_type == "circuit_breaker_triggered":
                self.current_run.today_circuit_breaker += 1
                self.current_run.total_circuit_breaker += 1
                self._add_suggestion("critical", f"Circuit breaker triggered: {data}")
            
            elif event_type == "invariants_violated":
                self.current_run.today_invariants += 1
                self.current_run.total_invariants += 1
                self._add_suggestion("critical", f"Invariants violated: {data.get('violations')}")
            
            elif event_type == "order_lock_timeout":
                self.current_run.today_order_lock_timeout += 1
                self.current_run.total_order_lock_timeout += 1
                self._add_suggestion("warning", "Order lock timeout detected")
            
            elif event_type == "analysis_lock_timeout":
                self.current_run.today_analysis_lock_timeout += 1
                self.current_run.total_analysis_lock_timeout += 1
                self._add_suggestion("warning", "Analysis lock timeout detected")
            
            elif event_type == "position_confirmed":
                self.current_run.today_orders_sent += 1
                self.current_run.total_orders_sent += 1
                self.current_run.today_positions_opened += 1
                self.current_run.total_positions_opened += 1
            
            # Add to event queue for GUI
            self.event_queue.append({
                "timestamp": timestamp,
                "type": event_type,
                "data": data
            })
    
    def handle_decision_log(self, decision: Dict[str, Any]):
        """Обработчик decision logs (ENTER/HOLD/BLOCK/CLOSE)"""
        if not self.current_run or self.current_run.status != "ACTIVE":
            return
        
        final_decision = decision.get("final_decision")
        
        with self.lock:
            if final_decision == "ENTER":
                self.current_run.today_enters += 1
                self.current_run.total_enters += 1
            elif final_decision == "HOLD":
                self.current_run.today_holds += 1
                self.current_run.total_holds += 1
            elif final_decision == "BLOCK":
                self.current_run.today_blocks += 1
                self.current_run.total_blocks += 1
            elif final_decision == "CLOSE":
                self.current_run.today_positions_closed += 1
                self.current_run.total_positions_closed += 1
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Записать событие в буфер (батчинг для производительности)"""
        if not self.run_dir:
            return
        
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "data": data
            }
            
            # Добавить в буфер вместо немедленной записи
            with self.event_buffer_lock:
                self.event_buffer.append(event)
        
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to buffer event: {e}")
    
    def _load_events(self):
        """Загрузить события из файла"""
        if not self.run_dir:
            return
        
        events_file = self.run_dir / "run_events.jsonl"
        if not events_file.exists():
            return
        
        try:
            self.event_queue.clear()
            with open(events_file, 'r', encoding='utf-8') as f:
                for line in f:
                    event = json.loads(line.strip())
                    self.event_queue.append(event)
            
            logger.debug(f"[RunSessionManager] Loaded {len(self.event_queue)} events")
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to load events: {e}")
    
    # ==================== PROGRESS & METRICS ====================
    
    def update_elapsed(self):
        """Обновить elapsed time (вызывается из GUI каждые ~1s)"""
        if not self.current_run or self.current_run.status != "ACTIVE":
            return
        
        with self.lock:
            start = datetime.fromisoformat(self.current_run.start_time)
            elapsed = int((datetime.now() - start).total_seconds())
            self.current_run.elapsed_seconds = elapsed
            
            # Check day rollover (каждые 24 часа)
            last_reset = datetime.fromisoformat(self.current_run.last_day_reset)
            if (datetime.now() - last_reset).total_seconds() >= 86400:  # 24 hours
                self._rollover_day()
    
    def _rollover_day(self):
        """Переход на следующий день + сохранение daily summary"""
        # Save daily summary
        self._save_daily_summary()
        
        # Reset today counters
        self.current_run.today_mt5_disconnected = 0
        self.current_run.today_reconnect = 0
        self.current_run.today_invariants = 0
        self.current_run.today_order_lock_timeout = 0
        self.current_run.today_analysis_lock_timeout = 0
        self.current_run.today_circuit_breaker = 0
        self.current_run.today_orders_sent = 0
        self.current_run.today_positions_opened = 0
        self.current_run.today_positions_closed = 0
        self.current_run.today_enters = 0
        self.current_run.today_holds = 0
        self.current_run.today_blocks = 0
        
        # Increment day
        self.current_run.current_day += 1
        self.current_run.last_day_reset = datetime.now().isoformat()
        
        logger.info(f"[RunSessionManager] Day rollover: now day {self.current_run.current_day}")
        self._log_event("day_rollover", {"new_day": self.current_run.current_day})
        
        # Check if run complete
        if self.current_run.current_day > self.current_run.total_days:
            logger.info("[RunSessionManager] Run completed!")
            self.stop_run()
    
    def _save_daily_summary(self):
        """Сохранить итоги дня"""
        if not self.run_dir or not self.current_run:
            return
        
        try:
            summary_file = self.run_dir / f"daily_summary_day{self.current_run.current_day}.json"
            summary = {
                "day": self.current_run.current_day,
                "timestamp": datetime.now().isoformat(),
                "counters": {
                    "mt5_disconnected": self.current_run.today_mt5_disconnected,
                    "reconnect": self.current_run.today_reconnect,
                    "invariants": self.current_run.today_invariants,
                    "order_lock_timeout": self.current_run.today_order_lock_timeout,
                    "analysis_lock_timeout": self.current_run.today_analysis_lock_timeout,
                    "circuit_breaker": self.current_run.today_circuit_breaker,
                    "orders_sent": self.current_run.today_orders_sent,
                    "positions_opened": self.current_run.today_positions_opened,
                    "positions_closed": self.current_run.today_positions_closed,
                    "enters": self.current_run.today_enters,
                    "holds": self.current_run.today_holds,
                    "blocks": self.current_run.today_blocks
                }
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[RunSessionManager] Daily summary saved: {summary_file}")
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to save daily summary: {e}")
    
    def get_progress(self) -> Dict[str, Any]:
        """Получить прогресс для UI"""
        if not self.current_run:
            return {"active": False}
        
        with self.lock:
            start = datetime.fromisoformat(self.current_run.start_time)
            elapsed = int((datetime.now() - start).total_seconds())
            total_duration = self.current_run.total_days * 86400  # days in seconds
            
            # Today progress
            last_reset = datetime.fromisoformat(self.current_run.last_day_reset)
            today_elapsed = int((datetime.now() - last_reset).total_seconds())
            today_remaining = max(0, 86400 - today_elapsed)
            
            # Total progress
            total_remaining = max(0, total_duration - elapsed)
            
            # ETA
            eta = datetime.now() + timedelta(seconds=total_remaining)
            
            # Format time strings (HH:MM:SS)
            def format_time(seconds: int) -> str:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
            
            return {
                "active": True,
                "status": self.current_run.status,
                "run_id": self.current_run.run_id,
                "start_time": self.current_run.start_time,
                "current_day": self.current_run.current_day,
                "total_days": self.current_run.total_days,
                "elapsed_seconds": elapsed,
                "today_elapsed": today_elapsed,
                "today_remaining": today_remaining,
                "total_remaining": total_remaining,
                "eta": eta.isoformat(),
                "eta_end": eta.strftime("%Y-%m-%d %H:%M:%S"),
                "today_progress": min(100, (today_elapsed / 86400) * 100),
                "total_progress": min(100, (elapsed / total_duration) * 100) if total_duration > 0 else 0,
                "today_elapsed_str": format_time(today_elapsed),
                "today_remaining_str": format_time(today_remaining),
                "total_elapsed_str": format_time(elapsed),
                "total_remaining_str": format_time(total_remaining)
            }
    
    def get_counters(self) -> Dict[str, Dict[str, int]]:
        """Получить счётчики для UI"""
        if not self.current_run:
            return {
                'today': {},
                'total': {}
            }
        
        with self.lock:
            return {
                'today': {
                    'mt5_disconnected': self.current_run.today_mt5_disconnected,
                    'reconnect': self.current_run.today_reconnect,
                    'invariants': self.current_run.today_invariants,
                    'order_lock_timeout': self.current_run.today_order_lock_timeout,
                    'analysis_lock_timeout': self.current_run.today_analysis_lock_timeout,
                    'circuit_breaker': self.current_run.today_circuit_breaker,
                    'orders_sent': self.current_run.today_orders_sent,
                    'positions_opened': self.current_run.today_positions_opened,
                    'positions_closed': self.current_run.today_positions_closed,
                    'enters': self.current_run.today_enters,
                    'holds': self.current_run.today_holds,
                    'blocks': self.current_run.today_blocks,
                },
                'total': {
                    'mt5_disconnected': self.current_run.total_mt5_disconnected,
                    'reconnect': self.current_run.total_reconnect,
                    'invariants': self.current_run.total_invariants,
                    'order_lock_timeout': self.current_run.total_order_lock_timeout,
                    'analysis_lock_timeout': self.current_run.total_analysis_lock_timeout,
                    'circuit_breaker': self.current_run.total_circuit_breaker,
                    'orders_sent': self.current_run.total_orders_sent,
                    'positions_opened': self.current_run.total_positions_opened,
                    'positions_closed': self.current_run.total_positions_closed,
                    'enters': self.current_run.total_enters,
                    'holds': self.current_run.total_holds,
                    'blocks': self.current_run.total_blocks,
                }
            }
    
    # ==================== SUGGESTIONS ====================
    
    def _add_suggestion(self, level: str, message: str):
        """Добавить suggestion (warning/critical)"""
        suggestion = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.suggestions.append(suggestion)
        
        # Keep last 10
        if len(self.suggestions) > 10:
            self.suggestions = self.suggestions[-10:]
    
    def get_suggestions(self) -> List[Dict[str, str]]:
        """Получить текущие suggestions"""
        with self.lock:
            # Auto-generate suggestions based on counters
            suggestions = list(self.suggestions)
            
            if self.current_run:
                # MT5 disconnects
                if self.current_run.today_mt5_disconnected >= 3:
                    suggestions.append({
                        "level": "WARNING",
                        "message": f"MT5 disconnected {self.current_run.today_mt5_disconnected} times today",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Lock timeouts
                if self.current_run.today_order_lock_timeout >= 1:
                    suggestions.append({
                        "level": "WARNING",
                        "message": f"Order lock timeout detected ({self.current_run.today_order_lock_timeout} times)",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Circuit breaker
                if self.current_run.today_circuit_breaker >= 1:
                    suggestions.append({
                        "level": "CRITICAL",
                        "message": f"Circuit breaker triggered {self.current_run.today_circuit_breaker} times today",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Invariants
                if self.current_run.today_invariants >= 1:
                    suggestions.append({
                        "level": "CRITICAL",
                        "message": f"System invariants violated {self.current_run.today_invariants} times",
                        "timestamp": datetime.now().isoformat()
                    })
            
            return suggestions[-10:]  # Last 10
    
    # ==================== EXPORT ====================
    
    def export_report(self) -> Optional[Path]:
        """Экспорт итогового отчёта в JSON"""
        if not self.current_run or not self.run_dir:
            return None
        
        try:
            report_file = self.run_dir / f"report_{self.current_run.run_id}.json"
            
            # Загрузить daily summaries
            daily_summaries = []
            for i in range(1, self.current_run.current_day + 1):
                summary_file = self.run_dir / f"daily_summary_day{i}.json"
                if summary_file.exists():
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        daily_summaries.append(json.load(f))
            
            # Анализ decision_logs.jsonl (если есть)
            decision_logs_path = Path("data/logs/decision_logs.jsonl")
            block_reasons_analysis = {}
            if decision_logs_path.exists():
                try:
                    from collections import Counter
                    with open(decision_logs_path, 'r', encoding='utf-8') as f:
                        logs = [json.loads(line) for line in f if line.strip()]
                    
                    # Фильтруем только события из текущего прогона
                    run_start = datetime.fromisoformat(self.current_run.start_time)
                    run_logs = [
                        log for log in logs
                        if datetime.fromisoformat(log['timestamp']) >= run_start
                    ]
                    
                    # Считаем block reasons
                    block_reasons = [log.get('block_reason') for log in run_logs if log.get('block_reason')]
                    block_reasons_analysis = dict(Counter(block_reasons).most_common(10))
                
                except Exception as e:
                    logger.debug(f"[RunSessionManager] Decision logs analysis failed: {e}")
            
            report = {
                "run_id": self.current_run.run_id,
                "start_time": self.current_run.start_time,
                "status": self.current_run.status,
                "duration_seconds": self.current_run.elapsed_seconds,
                "duration_hours": round(self.current_run.elapsed_seconds / 3600, 2),
                "days_completed": self.current_run.current_day,
                "total_days": self.current_run.total_days,
                "counters": self.get_counters(),
                "daily_summaries": daily_summaries,
                "top_block_reasons": block_reasons_analysis,
                "suggestions": self.get_suggestions(),
                "files": {
                    "run_state": "run_state.json",
                    "run_events": "run_events.jsonl",
                    "decision_logs": str(decision_logs_path.resolve())
                },
                "generated_at": datetime.now().isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[RunSessionManager] Report exported: {report_file}")
            return report_file
        
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to export report: {e}")
            return None
    
    # ==================== AUTOSAVE ====================
    
    def _start_autosave(self):
        """Запустить autosave thread (каждые 60s)"""
        if self._autosave_thread and self._autosave_thread.is_alive():
            return
        
        self._shutdown_flag.clear()
        self._autosave_thread = threading.Thread(
            target=self._autosave_loop,
            name="RunSessionAutosave",
            daemon=True
        )
        self._autosave_thread.start()
        logger.debug("[RunSessionManager] Autosave thread started")
    
    def _start_flush_thread(self):
        """Запустить flush thread для event buffer (каждые 2s)"""
        if self._flush_thread and self._flush_thread.is_alive():
            return
        
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="RunSessionFlush",
            daemon=True
        )
        self._flush_thread.start()
        logger.debug("[RunSessionManager] Flush thread started")
    
    def _autosave_loop(self):
        """Background thread: autosave каждые 60s"""
        while not self._shutdown_flag.is_set():
            try:
                self._shutdown_flag.wait(timeout=60)
                if not self._shutdown_flag.is_set():
                    self._save_state()
            except Exception as e:
                logger.error(f"[RunSessionManager] Autosave error: {e}")
    
    def _flush_loop(self):
        """Background thread: flush event buffer каждые 2s"""
        while not self._shutdown_flag.is_set():
            try:
                self._shutdown_flag.wait(timeout=2)
                if not self._shutdown_flag.is_set():
                    self._flush_event_buffer()
            except Exception as e:
                logger.error(f"[RunSessionManager] Flush error: {e}")
    
    def _flush_event_buffer(self):
        """Записать буфер событий в файл"""
        if not self.run_dir:
            return
        
        with self.event_buffer_lock:
            if not self.event_buffer:
                return
            
            events_to_write = self.event_buffer[:]
            self.event_buffer.clear()
        
        try:
            events_file = self.run_dir / "run_events.jsonl"
            with open(events_file, 'a', encoding='utf-8') as f:
                for event in events_to_write:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
            
            logger.debug(f"[RunSessionManager] Flushed {len(events_to_write)} events to disk")
        
        except Exception as e:
            logger.error(f"[RunSessionManager] Failed to flush events: {e}")
    
    def shutdown(self):
        """Shutdown manager"""
        # Flush events перед shutdown
        self._flush_event_buffer()
        
        self._shutdown_flag.set()
        if self._autosave_thread:
            self._autosave_thread.join(timeout=5)
        if self._flush_thread:
            self._flush_thread.join(timeout=2)
        
        # Final save
        if self.current_run:
            self._save_state()
        
        logger.info("[RunSessionManager] Shutdown complete")


# ==================== GLOBAL INSTANCE ====================

_run_session_manager = None

def get_run_session_manager() -> RunSessionManager:
    """Get singleton instance"""
    global _run_session_manager
    if _run_session_manager is None:
        _run_session_manager = RunSessionManager()
    return _run_session_manager

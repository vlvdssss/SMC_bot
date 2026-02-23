#!/usr/bin/env python3
"""
AI Analyst Scheduler v2.0 - Автоматический запуск анализа

Запускает market analyst в 06:00 и 18:00 каждый день.
Поддерживает kill-switch из конфига.

VERSION 2.0 Features:
- Kill-switch (AI_ENABLED check)
- Graceful degradation (stale analysis fallback)
- Save analysis history
- Rate limiting
"""

import threading
import time
import yaml
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Callable, Optional
import json

from src.core.logger import logger
from src.core.state_core import get_state_core, BotStatus
from src.ai.market_analyst import MarketAnalystService
from src.ai.signal_manager import AISignalManager


class AnalystScheduler:
    """
    Scheduler for automated AI market analysis v2.0.
    
    Features:
    - Runs analysis at 06:00 and 18:00 daily
    - Manual trigger support
    - Kill-switch support
    - Graceful degradation
    - Analysis history saving
    """
    
    def __init__(
        self, 
        analyst: Optional[MarketAnalystService] = None,
        signal_manager: Optional[AISignalManager] = None,
        callback: Optional[Callable] = None,
        executor: Optional[object] = None,
        rejected_logger: Optional[object] = None
    ):
        """Initialize scheduler v2.0."""
        self.analyst = analyst or MarketAnalystService()
        self.signal_manager = signal_manager or AISignalManager()
        self.callback = callback
        self.executor = executor  # For position checking
        self.rejected_logger = rejected_logger  # For logging rejected signals
        
        # StateCore integration
        self.state_core = get_state_core()
        
        # Load config
        self.config = self._load_config()
        
        # Режим работы: interval (каждые N минут) или schedule (по расписанию)
        schedule_config = self.config.get('market_analyst', {}).get('schedule', {})
        self.schedule_enabled = schedule_config.get('enabled', False)  # Включен ли автоматический анализ
        self.mode = schedule_config.get('mode', 'interval')  # 'interval' or 'schedule'
        self.interval_minutes = schedule_config.get('interval_minutes', 60)  # Default: 1 hour
        
        # Schedule times from config (для режима 'schedule')
        config_times = schedule_config.get('times', [])
        self.schedule_times = [self._parse_time(t) for t in config_times] if config_times else []
        
        self.running = False
        self.thread = None
        self.last_run = None
        self.last_analysis = None  # Cache for fallback
        
        # Analysis history directory
        self.history_dir = Path("data/ai_analysis")
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # Analysis lock to prevent duplicate runs
        self._analysis_lock = threading.Lock()
        self._last_analysis_time = {}  # symbol -> timestamp
        
        if self.schedule_enabled:
            if self.mode == 'interval':
                logger.info(f"[AI-Scheduler] v2.0 initialized in INTERVAL mode: every {self.interval_minutes} minutes")
            else:
                logger.info(f"[AI-Scheduler] v2.0 initialized in SCHEDULE mode: {config_times}")
        else:
            logger.info(f"[AI-Scheduler] v2.0 initialized in EVENT-DRIVEN mode: analysis only on triggers (TTL, position close)")
            logger.info(f"[AI-Scheduler] v2.0 initialized in SCHEDULE mode: {config_times}")
    
    def _load_config(self) -> dict:
        """Load AI config."""
        try:
            config_path = Path("config/ai.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"[AI-Scheduler] Failed to load config: {e}")
        return {}
    
    def _parse_time(self, time_str: str) -> dt_time:
        """Parse time string to dt_time."""
        try:
            # Remove quotes if present
            time_str = str(time_str).strip().strip("'\"")
            hour, minute = map(int, time_str.split(':'))
            return dt_time(hour, minute)
        except Exception as e:
            logger.warning(f"[AI-Scheduler] Invalid time format '{time_str}': {e}")
            return dt_time(6, 0)
    
    def is_ai_enabled(self) -> bool:
        """Check if AI is enabled (kill-switch)."""
        # Reload config to get fresh value
        self.config = self._load_config()
        ai_enabled = self.config.get('ai_enabled', True)
        analyst_enabled = self.config.get('market_analyst', {}).get('enabled', True)
        # В event-driven режиме schedule.enabled не влияет - AI запускается по событиям (TTL, position close)
        return ai_enabled and analyst_enabled
    
    def _is_instrument_analysis_enabled(self, symbol: str) -> bool:
        """Проверить включен ли анализ для инструмента."""
        try:
            instruments_path = Path("config/instruments.yaml")
            if instruments_path.exists():
                with open(instruments_path, 'r', encoding='utf-8') as f:
                    instruments_config = yaml.safe_load(f) or {}
                    instrument = instruments_config.get('instruments', {}).get(symbol, {})
                    # Проверяем оба флага: enabled (общий) и analysis_enabled (анализ)
                    return instrument.get('enabled', False) and instrument.get('analysis_enabled', True)
        except Exception as e:
            logger.warning(f"[AI-Scheduler] Failed to check instrument config for {symbol}: {e}")
        return True  # По умолчанию включено
    
    def start(self):
        """Start the scheduler thread."""
        if self.running:
            logger.warning("[AI-Scheduler] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("[AI-Scheduler] Started")
    
    def stop(self):
        """Stop the scheduler thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[AI-Scheduler] Stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop - supports interval and schedule modes."""
        while self.running:
            try:
                # Check kill-switch first
                if not self.is_ai_enabled():
                    logger.debug("[AI-Scheduler] AI disabled, skipping (kill-switch active)")
                    time.sleep(60)
                    continue
                
                # Если schedule отключен - только спим, анализ только по событиям
                if not self.schedule_enabled:
                    logger.debug("[AI-Scheduler] Schedule disabled, waiting for event triggers (TTL/position close)")
                    time.sleep(60)
                    continue
                
                now = datetime.now()
                
                # INTERVAL MODE: каждые N минут с момента запуска или последнего анализа
                if self.mode == 'interval':
                    should_run = False
                    
                    if self.last_run is None:
                        # Первый запуск - запускаем сразу
                        should_run = True
                        logger.info(f"[AI-Scheduler] ⏰ First run (interval mode: {self.interval_minutes}min)")
                    else:
                        # Проверяем прошло ли нужное время
                        time_since_last = (now - self.last_run).total_seconds() / 60  # в минутах
                        if time_since_last >= self.interval_minutes:
                            should_run = True
                            logger.info(f"[AI-Scheduler] ⏰ Interval trigger: {int(time_since_last)}min passed (target: {self.interval_minutes}min)")
                    
                    if should_run:
                        # КРИТИЧНО: Обновляем last_run СРАЗУ чтобы избежать петли
                        self.last_run = now
                        
                        # Анализируем все активные инструменты
                        analysis_ran = False
                        
                        # XAUUSD
                        if self._is_instrument_analysis_enabled("XAUUSD"):
                            result = self._run_analysis("XAUUSD")
                            # Проверяем что анализ прошел успешно (не был заблокирован)
                            if result and "error" not in result:
                                analysis_ran = True
                            else:
                                error_type = result.get("error", "unknown") if result else "unknown"
                                logger.debug(f"[AI-Scheduler] XAUUSD analysis returned error: {error_type}")
                        else:
                            logger.info("[AI-Scheduler] XAUUSD analysis disabled in config")
                        
                        # EURUSD
                        if self._is_instrument_analysis_enabled("EURUSD"):
                            result = self._run_analysis("EURUSD")
                            if result and "error" not in result:
                                analysis_ran = True
                            else:
                                error_type = result.get("error", "unknown") if result else "unknown"
                                logger.debug(f"[AI-Scheduler] EURUSD analysis returned error: {error_type}")
                        else:
                            logger.info("[AI-Scheduler] EURUSD analysis disabled in config")
                        
                        if analysis_ran:
                            logger.info(f"[AI-Scheduler] ✅ Analysis completed, next run in {self.interval_minutes} minutes")
                        else:
                            logger.info(f"[AI-Scheduler] ⚠️ Analysis blocked/failed, but timer reset - next run in {self.interval_minutes} minutes")
                
                # SCHEDULE MODE: по фиксированному расписанию
                elif self.mode == 'schedule' and self.schedule_times:
                    current_time = now.time()
                    for schedule_time in self.schedule_times:
                        if self._should_run(current_time, schedule_time):
                            logger.info(f"[AI-Scheduler] ⏰ Schedule trigger: {current_time.strftime('%H:%M')}")
                            
                            # Анализируем все активные инструменты
                            analysis_ran = False
                            
                            if self._is_instrument_analysis_enabled("XAUUSD"):
                                self._run_analysis("XAUUSD")
                                analysis_ran = True
                            
                            if self._is_instrument_analysis_enabled("EURUSD"):
                                self._run_analysis("EURUSD")
                                analysis_ran = True
                            
                            if analysis_ran:
                                self.last_run = now
                            
                            break  # Only run once per minute
                
                # Sleep 60 seconds
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"[AI-Scheduler] Error in loop: {e}")
                time.sleep(60)
    
    def _should_run(self, current_time: dt_time, schedule_time: dt_time) -> bool:
        """Check if analysis should run now."""
        # Check if within 1-minute window of schedule time
        hour_match = current_time.hour == schedule_time.hour
        minute_match = abs(current_time.minute - schedule_time.minute) <= 1
        
        # Сброс last_run если прошло более 1 часа (защита от застревания)
        if self.last_run:
            time_since_last = (datetime.now() - self.last_run).total_seconds()
            if time_since_last > 3600:  # 1 час
                logger.info(f"[AI-Scheduler] Resetting last_run (>1h ago: {int(time_since_last)}s)")
                self.last_run = None
            elif time_since_last <= 290:  # 4.8 минут cooldown (чуть меньше 5 для надёжности)
                # Более детальное логирование для диагностики
                logger.debug(
                    f"[AI-Scheduler] Skipping {schedule_time.strftime('%H:%M')} - "
                    f"last run {int(time_since_last)}s ago (< 290s cooldown)"
                )
                return False
        
        if hour_match and minute_match:
            logger.info(f"[AI-Scheduler] Time match: {current_time.strftime('%H:%M')} ≈ {schedule_time.strftime('%H:%M')}")
            return True
        
        return False
    
    def run_now(self, symbol: str = "XAUUSD") -> dict:
        """
        Trigger analysis manually.
        
        Args:
            symbol: Trading symbol to analyze (XAUUSD or EURUSD)
        
        Returns:
            Analysis result dict
        """
        logger.info(f"[AI-Scheduler] Manual trigger for {symbol}")
        return self._run_analysis(symbol)
    
    def _run_analysis(self, symbol: str) -> dict:
        """
        Execute full analysis pipeline.
        
        Steps:
        1. Check kill-switch
        2. Check open position (БЛОКИРОВКА - v2.0)
        3. Check time restrictions
        4. Run market analysis (GPT + charts) with fallback
        5. Process signals through SignalManager
        6. Save history
        7. Execute callback
        8. Return results
        """
        # STATECORE: Acquire analysis lock (защита от двойного GPT вызова)
        if not self.state_core.acquire_analysis_lock():
            logger.warning("[AI-Scheduler] ⚠️ Analysis lock already held - skipping duplicate analysis")
            return {
                "error": "analysis_locked",
                "reason": "Another analysis already in progress",
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # STATECORE: Update status to ANALYZING
            self.state_core.set_status(BotStatus.ANALYZING)
            
            # ЗАЩИТА ОТ ДУБЛИРОВАНИЯ с использованием internal lock
            with self._analysis_lock:
                now = datetime.now()
                last_time = self._last_analysis_time.get(symbol)
                
                if last_time:
                    time_since_last = (now - last_time).total_seconds()
                    MIN_INTERVAL_SECONDS = 60  # Минимум 60 секунд между анализами
                    
                    if time_since_last < MIN_INTERVAL_SECONDS:
                        logger.warning(
                            f"[AI-Scheduler] ⏸️ Duplicate analysis blocked: last run was "
                            f"{time_since_last:.1f}s ago (min interval: {MIN_INTERVAL_SECONDS}s)"
                        )
                        # STATECORE: Set back to WAITING
                        self.state_core.set_status(BotStatus.WAITING)
                        return {
                            "error": "duplicate_blocked",
                            "reason": f"Analysis ran {time_since_last:.1f}s ago (< {MIN_INTERVAL_SECONDS}s)",
                            "symbol": symbol,
                            "timestamp": now.isoformat()
                        }
                
                # Обновляем время ВНУТРИ lock - защита от race condition
                self._last_analysis_time[symbol] = now
                logger.debug(f"[AI-Scheduler] Analysis timestamp set for {symbol}: {now.isoformat()}")
            
            # Quick checks BEFORE acquiring lock for actual analysis
            # Check kill-switch
            if not self.is_ai_enabled():
                logger.warning("[AI-Scheduler] AI disabled, using fallback")
                self.state_core.set_status(BotStatus.WAITING)
                return self._get_fallback_analysis(symbol)
            
            # Check if position already open FOR THIS SYMBOL - BLOCK AI analysis to save API calls
            if self.executor and hasattr(self.executor, 'has_position'):
                has_pos = self.executor.has_position(symbol=symbol)
                logger.debug(f"[AI-Scheduler] Position check for {symbol}: {has_pos}")
                
                if has_pos:
                    logger.info(f"[AI-Scheduler] 🚫 Position open for {symbol} - BLOCKING AI analysis (save API calls)")
                    self.state_core.set_status(BotStatus.BLOCKED, reason=f"Position open for {symbol}")
                    return {
                        "error": "position_open",
                        "reason": f"Position open for {symbol} - AI analysis blocked until close",
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.debug(f"[AI-Scheduler] ✅ No position for {symbol} - analysis allowed")
            
            # Check time restrictions
            time_allowed, time_reason = self.signal_manager._is_trading_time_allowed()
            if not time_allowed:
                logger.warning(f"[AI-Scheduler] ⏸️ Analysis blocked: {time_reason}")
                
                # Log rejection for time restriction (for analytics)
                if hasattr(self, 'rejected_logger') and self.rejected_logger:
                    self.rejected_logger.log_rejection(
                        symbol=symbol,
                        direction='N/A',
                        confidence=0.0,
                        entry=0.0,
                        sl=0.0,
                        tp=0.0,
                        reason=time_reason,
                        filter_type='time_restriction'
                    )
                
                self.state_core.set_status(BotStatus.BLOCKED, reason=time_reason)
                return {
                    "error": "time_restriction",
                    "reason": time_reason,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Check volatility pre-filter (skip GPT if market too quiet)
            vol_passed, vol_reason = self.signal_manager.check_volatility_filter(symbol)
            if not vol_passed:
                logger.warning(f"[AI-Scheduler] Analysis skipped: {vol_reason}")
                self.state_core.set_status(BotStatus.BLOCKED, reason=vol_reason)
                return {
                    "error": "volatility_filter",
                    "reason": vol_reason,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat()
                }
            
            # NOW run actual GPT analysis
            logger.ai(f"Starting analysis for {symbol} ({vol_reason})")
            
            # Step 1: Run analysis with fallback on error
            try:
                analysis = self.analyst.analyze_market(symbol)
            except ValueError as e:
                # Configuration errors (invalid API key, missing config)
                logger.error(f"[AI-Scheduler] ❌ CONFIGURATION ERROR: {e}")
                logger.error("[AI-Scheduler] 💡 Исправь конфигурацию и перезапусти бота")
                analysis = self._get_fallback_analysis(symbol, error=f"Config error: {e}")
                self.state_core.set_status(BotStatus.ERROR, reason=f"Config error: {e}")
            except Exception as e:
                # All other errors (API errors, network, etc.)
                error_type = type(e).__name__
                logger.error(f"[AI-Scheduler] ❌ ANALYSIS FAILED: {error_type}")
                logger.error(f"[AI-Scheduler] Детали: {e}")
                logger.error("[AI-Scheduler] 💡 Используется fallback анализ (безопасный режим)")
                analysis = self._get_fallback_analysis(symbol, error=f"{error_type}: {e}")
                self.state_core.set_status(BotStatus.ERROR, reason=f"{error_type}")
            
            # Step 2: Process signals
            if "error" not in analysis:
                signal_summary = self.signal_manager.process_analysis(analysis)
                analysis["signal_processing"] = signal_summary
                
                # Save history
                self._save_analysis_history(analysis)
                self.last_analysis = analysis
                
                # STATECORE: Analysis success - back to WAITING (SignalManager will update status if signal created)
                if not self.state_core.active_signal:
                    self.state_core.set_status(BotStatus.WAITING)
            
            # Step 3: Callback
            if self.callback:
                try:
                    self.callback(analysis)
                except Exception as e:
                    logger.error(f"[AI-Scheduler] Callback failed: {e}")
            
            # Log summary
            self._log_analysis_summary(analysis)
            
            return analysis
        
        except Exception as e:
            logger.error(f"[AI-Scheduler] Analysis failed: {e}")
            self.state_core.set_status(BotStatus.ERROR, reason=str(e))
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
        
        finally:
            # STATECORE: Always release analysis lock
            self.state_core.release_analysis_lock()
    
    def _log_analysis_summary(self, analysis: dict):
        """Log human-readable summary."""
        try:
            # Get summary from signal_processing (V5 format)
            summary = analysis.get("signal_processing", analysis.get("summary", {}))
            
            # DEBUG: Log what we got
            logger.debug(f"[AI-Scheduler] Summary for logging: {summary}")
            
            signals = analysis.get("signals", [])
            blocks = analysis.get("trading_blocks", {})
            
            # Чистый вывод результата
            sentiment = summary.get('sentiment', 'N/A')
            confidence = summary.get('confidence', 0)
            sig_count = len(signals)
            
            logger.ai(f"Analysis complete - {sentiment.upper()} (Confidence: {confidence}%)")
            
            # Log signals с категорией SIGNAL
            for signal in signals:
                logger.signal(
                    f"{signal['type']} @ {signal['entry_price']} "
                    f"(SL: {signal['stop_loss']}, TP: {signal['take_profit']}, Conf: {signal['confidence']}%)"
                )
            
        except Exception as e:
            logger.debug(f"Failed to log summary: {e}")
    
    def _save_analysis_history(self, analysis: dict):
        """Save analysis to timestamped file for history with atomic write."""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.history_dir / f"analysis_{timestamp}.json"
            
            # Атомарное сохранение
            temp_file = filename.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
                temp_file.replace(filename)
                logger.info(f"[AI-Scheduler] Saved history: {filename.name}")
            except Exception as e:
                logger.error(f"[AI-Scheduler] Error saving history: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise
        except Exception as e:
            logger.error(f"[AI-Scheduler] Failed to save history: {e}")
    
    def _get_fallback_analysis(self, symbol: str, error: str = None) -> dict:
        """Get fallback analysis (from last good analysis or safe default)."""
        try:
            # Try to use last cached analysis
            if self.last_analysis and "error" not in self.last_analysis:
                age_minutes = (datetime.now() - datetime.fromisoformat(
                    self.last_analysis.get("timestamp")
                )).total_seconds() / 60
                
                max_age = self.config.get('market_analyst', {}).get('fallback', {}).get('max_stale_minutes', 1440)
                
                if age_minutes < max_age:
                    logger.info(f"[AI-Scheduler] Using cached analysis (age: {age_minutes:.0f}min)")
                    fallback = self.last_analysis.copy()
                    fallback["is_fallback"] = True
                    fallback["fallback_reason"] = f"Using cached analysis (age: {age_minutes:.0f}min)"
                    if error:
                        fallback["original_error"] = error
                    return fallback
            
            # Safe default: no signals, warning block
            logger.warning("[AI-Scheduler] No valid cache, using safe default")
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "is_fallback": True,
                "fallback_reason": "No recent analysis available",
                "original_error": error or "Unknown error",
                "summary": {
                    "sentiment": "neutral",
                    "confidence": 0,
                    "key_levels": {}
                },
                "signals": [],
                "trading_blocks": {
                    "block_type": "warning",
                    "reason": "AI service unavailable - using safe fallback"
                }
            }
            
        except Exception as e:
            logger.error(f"[AI-Scheduler] Fallback failed: {e}")
            return {
                "error": "Fallback generation failed",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "schedule": [t.strftime("%H:%M") for t in self.schedule_times],
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self._get_next_run_time()
        }
    
    def get_next_analysis_time(self) -> Optional[str]:
        """Get human-readable next analysis time for telegram messages."""
        try:
            if self.mode == 'interval':
                # Interval mode - calculate based on last_run
                if self.last_run:
                    from datetime import timedelta
                    next_time = self.last_run + timedelta(minutes=self.interval_minutes)
                    now = datetime.now()
                    
                    if next_time > now:
                        # Future time
                        delta_minutes = int((next_time - now).total_seconds() / 60)
                        if delta_minutes < 60:
                            return f"через {delta_minutes} мин"
                        else:
                            hours = delta_minutes // 60
                            minutes = delta_minutes % 60
                            return f"через {hours}ч {minutes}мин"
                    else:
                        return "сейчас"
                else:
                    return f"каждые {self.interval_minutes} мин"
            
            elif self.mode == 'schedule':
                # Schedule mode - find next scheduled time
                next_run = self._get_next_run_time()
                if next_run:
                    next_dt = datetime.fromisoformat(next_run)
                    return next_dt.strftime('%H:%M')
                return "не запланирован"
            
            return "не определено"
            
        except Exception as e:
            logger.error(f"[AI-Scheduler] Failed to get next analysis time: {e}")
            return "не определено"
    
    def _get_next_run_time(self) -> Optional[str]:
        """Calculate next scheduled run time."""
        try:
            now = datetime.now()
            today = now.date()
            
            # Find next schedule time today
            for schedule_time in sorted(self.schedule_times):
                next_run = datetime.combine(today, schedule_time)
                if next_run > now:
                    return next_run.isoformat()
            
            # If no more today, return first time tomorrow
            if self.schedule_times:
                first_time = min(self.schedule_times)
                from datetime import timedelta
                tomorrow = today + timedelta(days=1)
                next_run = datetime.combine(tomorrow, first_time)
                return next_run.isoformat()
            
            return None
            
        except Exception as e:
            logger.error(f"[AI-Scheduler] Failed to calc next run: {e}")
            return None
    
    def trigger_immediate_analysis(self, symbol: str = "XAUUSD", reason: str = "manual", cooldown_minutes: int = 0):
        """
        Trigger immediate analysis (for position close or TTL expiration).
        
        Args:
            symbol: Trading symbol
            reason: Reason for trigger (position_closed, ttl_expired, manual)
            cooldown_minutes: Wait N minutes before analysis (0 = immediate)
        """
        if cooldown_minutes > 0:
            logger.info(f"[AI-Scheduler] Analysis scheduled in {cooldown_minutes} minutes: {reason}")
        else:
            logger.info(f"[AI-Scheduler] Immediate analysis triggered: {reason}")
        
        # Run async to not block
        def _async_run():
            # Wait cooldown period if specified
            if cooldown_minutes > 0:
                logger.info(f"[AI-Scheduler] ⏳ Waiting {cooldown_minutes} minutes before analysis...")
                # Sleep in small intervals to check running flag
                total_seconds = cooldown_minutes * 60
                sleep_interval = 10  # Check every 10 seconds
                elapsed = 0
                while elapsed < total_seconds:
                    if not self.running:
                        logger.info("[AI-Scheduler] ⏸️ Cooldown interrupted - scheduler stopped")
                        return
                    time.sleep(min(sleep_interval, total_seconds - elapsed))
                    elapsed += sleep_interval
                logger.info(f"[AI-Scheduler] ⏰ Cooldown finished - starting analysis")
            
            # Check if scheduler is still running before analysis
            if not self.running:
                logger.info("[AI-Scheduler] ⏸️ Analysis skipped - scheduler stopped")
                return
            
            # После cooldown сразу запускаем анализ
            # (защита от дублирования есть внутри _run_analysis)
            self._run_analysis(symbol)
        
        thread = threading.Thread(target=_async_run, daemon=True)
        thread.start()


# Global scheduler instance (initialized in app)
_scheduler_instance: Optional[AnalystScheduler] = None


def get_scheduler() -> AnalystScheduler:
    """Get global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AnalystScheduler()
    return _scheduler_instance


def init_scheduler(
    callback: Optional[Callable] = None, 
    executor: Optional[object] = None,
    signal_manager: Optional['AISignalManager'] = None,
    rejected_logger: Optional[object] = None
) -> AnalystScheduler:
    """Initialize and start global scheduler."""
    global _scheduler_instance
    _scheduler_instance = AnalystScheduler(
        callback=callback, 
        executor=executor,
        signal_manager=signal_manager,
        rejected_logger=rejected_logger
    )
    _scheduler_instance.start()
    return _scheduler_instance


if __name__ == "__main__":
    # Test run
    def test_callback(analysis):
        print(f"\n{'='*60}")
        print("ANALYSIS CALLBACK")
        print(f"{'='*60}")
        print(f"Sentiment: {analysis.get('summary', {}).get('sentiment')}")
        print(f"Signals: {len(analysis.get('signals', []))}")
        print(f"{'='*60}\n")
    
    scheduler = AnalystScheduler(callback=test_callback)
    print(f"Status: {scheduler.get_status()}")
    
    # Manual trigger
    print("\nTriggering manual analysis...")
    result = scheduler.run_now()
    print(f"\nResult summary: {result.get('summary', {})}")

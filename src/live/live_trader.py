"""
Live Trader - Live and Demo Trading Module
"""

import logging
import time
from datetime import datetime, time as datetime_time, timedelta
from typing import Dict, Tuple
import threading
import json
from pathlib import Path
import sys
from src.core.logger import logger
from src.core.risk_manager import RiskManager
from src.core.state_core import get_state_core, BotStatus

# Helper для работы с путями в EXE
def get_data_path(filename):
    """Получить абсолютный путь к файлу в data директории (работает в EXE и python)"""
    if getattr(sys, 'frozen', False):
        # Если запущен как EXE, используем директорию где находится EXE
        base_path = Path(sys.executable).parent
    else:
        # Если запущен как python скрипт, используем корневую директорию проекта
        base_path = Path(__file__).parent.parent.parent
    return base_path / 'data' / filename

# Добавить импорт
try:
    from src.ai.news_filter import GPTNewsFilter
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False

try:
    from src.ai.signal_manager import AISignalManager
    AI_SIGNAL_MANAGER_AVAILABLE = True
except ImportError:
    AI_SIGNAL_MANAGER_AVAILABLE = False

try:
    from src.ml.predictor import TradePredictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    from src.ml import MLDataCollector
    ML_DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    ML_DATA_COLLECTOR_AVAILABLE = False

try:
    from src.monitoring import TelegramNotifier, AlertManager
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# V5 Improvements
try:
    from src.ai.technical_filter import TechnicalConfirmation
    TECHNICAL_FILTER_AVAILABLE = True
except ImportError:
    TECHNICAL_FILTER_AVAILABLE = False
    logger.warning("[V5] Technical Filter not available")

try:
    from src.ai.session_adapter import SessionAdapter
    SESSION_ADAPTER_AVAILABLE = True
except ImportError:
    SESSION_ADAPTER_AVAILABLE = False
    logger.warning("[V5] Session Adapter not available")

try:
    from src.ai.adaptive_lot import AdaptiveLotSizing
    ADAPTIVE_LOT_AVAILABLE = True
except ImportError:
    ADAPTIVE_LOT_AVAILABLE = False
    logger.warning("[V5] Adaptive Lot not available")

try:
    from src.ai.rejected_logger import RejectedSignalsLogger
    REJECTED_LOGGER_AVAILABLE = True
except ImportError:
    REJECTED_LOGGER_AVAILABLE = False
    logger.warning("[V5] Rejected Logger not available")

class LiveTrader:
    def __init__(self, config_dir: str = 'config', enable_trading: bool = False, enable_gpt: bool = True, bot_queue=None) -> None:
        """
        Args:
            config_dir: Путь к папке с конфигами
            enable_trading: True = реальная торговля, False = только мониторинг
            enable_gpt: True = использовать GPT фильтр, False = отключить
        """
        # Check if already initialized (prevent duplicate logs)
        if hasattr(self, '_initialized') and self._initialized:
            logger.debug("[LiveTrader] Already initialized, skipping duplicate init...")
            return
        
        logger.info("="*80)
        logger.info("[LiveTrader] Initializing LiveTrader...")
        logger.info(f"[LiveTrader] Mode: {'REAL TRADING' if enable_trading else 'MONITORING ONLY'}")
        logger.info(f"[LiveTrader] GPT filter: {'ENABLED' if enable_gpt else 'DISABLED'}")
        self._initialized = False
        
        self.config_dir: str = config_dir
        self.enable_trading: bool = enable_trading
        self.enable_gpt: bool = enable_gpt
        self.connected: bool = False
        
        # Bot queue for event-driven UI updates
        self.bot_queue = bot_queue
        
        # Флаг для отслеживания блокировки торговли (чтобы не спамить логи)
        self._last_block_reason: str = None
        
        # Stop Loss Protection - защита от серии стопов
        self._consecutive_stops_count: int = 0  # Счетчик последовательных стопов
        self._stop_protection_until: datetime = None  # Время до которого заблокирована торговля
        self._last_stop_protection_log: datetime = None  # Время последнего лога о защите
        
        # Profit Protection - защита от жадности (фиксация прибыли)
        self._consecutive_wins_count: int = 0  # Счетчик последовательных прибыльных сделок
        self._profit_protection_until: datetime = None  # Время до которого заблокирована торговля после профитов
        self._last_profit_protection_log: datetime = None  # Время последнего лога о profit защите
        
        # Отслеживание последней обработанной сделки для синхронизации защиты
        self._last_processed_trade_id: int = 0  # ID последней обработанной сделки
        
        # Загрузка конфигов
        logger.info("[LiveTrader] Loading configuration files...")
        self.load_configs()
        
        # Подключение к MT5
        logger.info("[LiveTrader] Connecting to MetaTrader 5...")
        self.connect_mt5()
        
        # Инициализация стратегий
        logger.info("[LiveTrader] Initializing trading strategies...")
        self.init_strategies()
        
        # Инициализация фильтров
        logger.info("[LiveTrader] Initializing filters (GPT, ML)...")
        self.init_filters()
        
        # Инициализация executor
        logger.info("[LiveTrader] Initializing Executor...")
        from src.core.executor import Executor
        magic_number = self.mt5_config.get('mt5', {}).get('settings', {}).get('magic_number', 123456)
        self.executor = Executor(
            mt5_connector=self.mt5_connector,
            magic_number=magic_number,
            bot_queue=getattr(self, 'bot_queue', None)  # Pass bot_queue for events
        )
        logger.info(f"[LiveTrader] Executor ready (Magic: {magic_number})")
        
        # Инициализация RiskManager для trailing расчётов
        logger.info("[LiveTrader] Initializing RiskManager...")
        risk_config = self.config.get('trading', {}).get('risk', {})
        self.risk_manager = RiskManager(config=risk_config)
        logger.info("[LiveTrader] RiskManager ready")
        
        # Инициализация V4 Trailing Stop Handler
        trailing_config = self.config.get('trading', {}).get('trailing_stop', {})
        trailing_enabled = trailing_config.get('enabled', False)
        
        if trailing_enabled:
            logger.info("[LiveTrader] Initializing V4 Trailing Stop...")
            from src.live.trailing_stop_v4 import TrailingStopV4
            self.trailing_v4 = TrailingStopV4(mt5_connector=self.mt5_connector)
            logger.info("[V4-Trailing] ✅ ENABLED (30% activation, 50% stop distance)")
        else:
            logger.info("[V4-Trailing] ⛔ DISABLED in settings")
            from src.live.trailing_stop_v4 import TrailingStopV4
            self.trailing_v4 = TrailingStopV4(mt5_connector=self.mt5_connector)
        
        # Инициализация NewsFetcher (для V3)
        self.news_fetcher = None
        try:
            from src.ai.news_fetcher import RealTimeNewsFetcher
            self.news_fetcher = RealTimeNewsFetcher()
            logger.info("[LiveTrader] NewsFetcher initialized")
        except Exception as e:
            logger.warning(f"[LiveTrader] NewsFetcher not available: {e}")
        
        # Инициализация AI Signal Manager
        self.ai_signal_manager = None
        if AI_SIGNAL_MANAGER_AVAILABLE:
            try:
                logger.info("[LiveTrader] Initializing AI Signal Manager...")
                # Передаем telegram_notifier если он уже инициализирован
                telegram_for_signals = getattr(self, 'telegram', None)
                self.ai_signal_manager = AISignalManager(
                    telegram_notifier=telegram_for_signals,
                    bot_queue=getattr(self, 'bot_queue', None),  # Pass bot_queue for events
                    mt5_connector=self.mt5_connector  # 🔥 Pass MT5 connector for Trade Filters
                )
                # Set executor reference for position checks
                self.ai_signal_manager.set_executor(self.executor)
                
                # 🚀 АКТИВАЦИЯ SIGNAL QUALITY V3.0
                try:
                    from src.ai.activate_v3 import activate_v3, ENABLE_SIGNAL_QUALITY_V3
                    if ENABLE_SIGNAL_QUALITY_V3 and self.news_fetcher:
                        self.ai_signal_manager = activate_v3(
                            self.ai_signal_manager,
                            self.news_fetcher,
                            enable=True
                        )
                    elif ENABLE_SIGNAL_QUALITY_V3:
                        logger.warning("[LiveTrader] V3 enabled but news_fetcher not available - using V2")
                except ImportError as e:
                    logger.info(f"[LiveTrader] V3 module not found ({e}) - using V2 logic")
                
                logger.info("[LiveTrader] AI Signal Manager initialized with executor reference")
            except Exception as e:
                logger.error(f"[LiveTrader] Failed to init AI Signal Manager: {e}")
        else:
            logger.warning("[LiveTrader] AI Signal Manager unavailable")
        
        # StateCore - единый источник правды
        logger.info("[LiveTrader] Initializing StateCore...")
        self.state_core = get_state_core()
        self.state_core.set_status(BotStatus.IDLE)
        
        # Register MT5 connector for watchdog
        self.state_core.set_mt5_connector(self.mt5_connector)
        
        # Start background tasks (MT5 watchdog, invariants checker)
        self.state_core.start_background_tasks()
        
        logger.info("[LiveTrader] StateCore integrated with watchdog enabled")
        
        # Инициализация ML Data Collector для сбора данных для обучения
        self.ml_collector = None
        if ML_DATA_COLLECTOR_AVAILABLE:
            try:
                logger.info("[LiveTrader] Initializing ML Data Collector...")
                self.ml_collector = MLDataCollector()
                logger.info("[LiveTrader] ML Data Collector ready - collecting training data")
            except Exception as e:
                logger.error(f"[LiveTrader] Failed to init ML Data Collector: {e}")
        else:
            logger.debug("[LiveTrader] ML Data Collector unavailable")
        
        # ✅ V5: Инициализация новых модулей
        logger.info("[LiveTrader] Initializing V5 improvements...")
        
        # Загружаем V5 конфиг из trading.yaml
        v5_config = self.config.get('trading', {}).get('v5_improvements', {})
        
        # Technical Filter (гибридная стратегия GPT + Technical)
        self.tech_filter = None
        tech_config = v5_config.get('technical_filter', {})
        tech_enabled = tech_config.get('enabled', True)
        tech_strict = tech_config.get('strict_mode', False)
        
        if TECHNICAL_FILTER_AVAILABLE and tech_enabled:
            try:
                self.tech_filter = TechnicalConfirmation(strict_mode=tech_strict)
                mode_text = "STRICT" if tech_strict else "BALANCED"
                logger.info(f"[V5] ✅ Technical Confirmation Filter enabled ({mode_text} mode)")
            except Exception as e:
                logger.error(f"[V5] Failed to init Technical Filter: {e}")
        else:
            reason = "disabled in config" if not tech_enabled else "module not available"
            logger.warning(f"[V5] ⚠️ Technical Filter disabled ({reason})")
        
        # Session Adapter (адаптация под торговые сессии)
        self.session_adapter = None
        session_config = v5_config.get('session_adapter', {})
        session_enabled = session_config.get('enabled', True)
        
        if SESSION_ADAPTER_AVAILABLE and session_enabled:
            try:
                self.session_adapter = SessionAdapter()
                logger.info("[V5] ✅ Session Adapter enabled (Asian/European/US adaptation)")
            except Exception as e:
                logger.error(f"[V5] Failed to init Session Adapter: {e}")
        else:
            reason = "disabled in config" if not session_enabled else "module not available"
            logger.warning(f"[V5] ⚠️ Session Adapter disabled ({reason})")
        
        # Adaptive Lot Sizing (умный расчет лота)
        self.lot_sizer = None
        lot_config = v5_config.get('adaptive_lot', {})
        lot_enabled = lot_config.get('enabled', True)
        
        if ADAPTIVE_LOT_AVAILABLE and lot_enabled:
            try:
                base_lot = lot_config.get('base_lot', risk_config.get('fixed_lot_size', 0.01))
                max_lot = lot_config.get('max_lot', 0.05)
                lookback = lot_config.get('lookback_trades', 10)
                
                self.lot_sizer = AdaptiveLotSizing(
                    base_lot=base_lot,
                    min_lot=0.01,
                    max_lot=max_lot,
                    lookback_trades=lookback
                )
                logger.info(f"[V5] ✅ Adaptive Lot Sizing enabled (base={base_lot}, max={max_lot}, lookback={lookback})")
            except Exception as e:
                logger.error(f"[V5] Failed to init Adaptive Lot: {e}")
        else:
            reason = "disabled in config" if not lot_enabled else "module not available"
            logger.warning(f"[V5] ⚠️ Adaptive Lot disabled ({reason})")
        
        # Rejected Signals Logger (логирование отклоненных сигналов)
        self.rejected_logger = None
        logger_config = v5_config.get('rejected_logger', {})
        logger_enabled = logger_config.get('enabled', True)
        
        if REJECTED_LOGGER_AVAILABLE and logger_enabled:
            try:
                self.rejected_logger = RejectedSignalsLogger()
                logger.info("[V5] ✅ Rejected Signals Logger enabled")
            except Exception as e:
                logger.error(f"[V5] Failed to init Rejected Logger: {e}")
        else:
            reason = "disabled in config" if not logger_enabled else "module not available"
            logger.warning(f"[V5] ⚠️ Rejected Logger disabled ({reason})")
        
        logger.info("[LiveTrader] V5 improvements initialized")
        
        # Инициализация мониторинга
        logger.info("[LiveTrader] Initializing monitoring (Telegram)...")
        self.telegram = None
        self.alert_manager = None
        self.notify_config = {}
        if MONITORING_AVAILABLE:
            self._init_monitoring()
        else:
            logger.warning("[LiveTrader] Monitoring modules unavailable")
        
        # Отслеживание открытых позиций для Telegram уведомлений
        self.tracked_positions = {}  # {ticket: {symbol, direction, entry_time, ...}}
        
        # Устанавливаем Telegram в TrailingStopV4 после инициализации
        if hasattr(self, 'trailing_v4') and self.telegram:
            self.trailing_v4.telegram = self.telegram
            logger.info("[LiveTrader] Telegram notifier set to V4 Trailing Stop")
        
        logger.info("[LiveTrader] LiveTrader fully initialized")
        logger.info("="*80)
    
    def start(self) -> None:
        """Запуск трейдера (для совместимости)."""
        pass
    
    def load_configs(self) -> None:
        """Загрузка конфигурационных файлов."""
        import yaml
        config_path = Path(self.config_dir)
        
        # Загружаем MT5 конфиг
        mt5_config_path = config_path / 'mt5.yaml'
        if mt5_config_path.exists():
            with open(mt5_config_path, 'r', encoding='utf-8') as f:
                self.mt5_config = yaml.safe_load(f)
        else:
            self.mt5_config = {}
        
        # Загружаем конфиг инструментов
        instruments_config_path = config_path / 'instruments.yaml'
        if instruments_config_path.exists():
            with open(instruments_config_path, 'r', encoding='utf-8') as f:
                self.instruments_config = yaml.safe_load(f)
        else:
            self.instruments_config = {}
        
        # Загружаем конфиг портфеля
        portfolio_config_path = config_path / 'portfolio.yaml'
        if portfolio_config_path.exists():
            with open(portfolio_config_path, 'r', encoding='utf-8') as f:
                self.portfolio_config = yaml.safe_load(f)
        else:
            self.portfolio_config = {}
        
        # Загружаем trading.yaml (для RiskManager и других настроек)
        trading_config_path = config_path / 'trading.yaml'
        if trading_config_path.exists():
            with open(trading_config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
    
    def get_check_interval(self) -> float:
        """Получить интервал проверки сигналов из конфига (в секундах)."""
        try:
            return float(self.config.get('trading', {}).get('check_interval_seconds', 3))
        except (ValueError, TypeError):
            return 3.0  # По умолчанию 3 секунды
    
    def _is_trading_enabled_for_instrument(self, symbol: str) -> bool:
        """Проверить включена ли торговля для инструмента."""
        try:
            instrument_config = self.instruments_config.get('instruments', {}).get(symbol, {})
            # Проверяем оба флага: enabled (общий) и trading_enabled (торговля)
            is_enabled = instrument_config.get('enabled', False)
            is_trading = instrument_config.get('trading_enabled', True)
            
            if not is_enabled:
                logger.debug(f"[TRADE] {symbol} instrument disabled")
                return False
            
            if not is_trading:
                logger.debug(f"[TRADE] {symbol} trading disabled (analysis only)")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"[TRADE] Failed to check trading config for {symbol}: {e}")
            return True  # По умолчанию разрешаем если не смогли проверить
    
    def _can_trade_now(self) -> bool:
        """
        Check if trading is allowed at current time (hardcoded restrictions).
        
        HARDCODED RESTRICTIONS (removed from GUI):
        - No trading on weekends (Saturday=5, Sunday=6)
        - No trading during night hours: 23:30 UTC - 01:10 UTC
        
        Returns:
            bool: True if trading allowed, False if blocked
        """
        now = datetime.now()
        block_reason = None
        
        # Block weekends (Saturday and Sunday)
        if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
            block_reason = f"weekend_{now.strftime('%A')}"
            # Логируем только при первом входе в блокировку
            if self._last_block_reason != block_reason:
                logger.info(f"[TRADE] ⛔ Weekend block: No trading on {now.strftime('%A')}")
                self._last_block_reason = block_reason
            return False
        
        # Block night hours: 23:30 - 01:10 UTC
        current_time = now.time()
        night_start = datetime_time(23, 30)
        night_end = datetime_time(1, 10)
        
        # Night block spans across midnight (23:30 → 00:00 → 01:10)
        if current_time >= night_start or current_time <= night_end:
            block_reason = f"night_{current_time.strftime('%H:%M')}"
            # Логируем только при первом входе в блокировку
            if self._last_block_reason != block_reason:
                logger.info(f"[TRADE] ⛔ Night block: No trading from 23:30 to 01:10 UTC (current: {current_time.strftime('%H:%M')})")
                self._last_block_reason = block_reason
            return False
        
        # Сбросить флаг если блокировка снята
        if self._last_block_reason is not None:
            logger.info("[TRADE] ✅ Trading restrictions lifted - trading allowed")
            self._last_block_reason = None
        
        return True
    
    def _check_stop_loss_protection(self) -> bool:
        """
        Проверка защиты от серии стопов.
        
        Блокирует торговлю на N минут после серии убыточных сделок.
        Считаются только обычные стопы (минусовые сделки), не трейлинг стопы.
        
        Returns:
            bool: True если торговля разрешена, False если заблокирована
        """
        # Проверяем включена ли защита
        protection_config = self.config.get('trading', {}).get('stop_loss_protection', {})
        if not protection_config.get('enabled', False):
            return True
        
        now = datetime.now()
        
        # Проверяем активна ли блокировка
        if self._stop_protection_until and now < self._stop_protection_until:
            # Логируем только раз в минуту чтобы не спамить
            if not self._last_stop_protection_log or (now - self._last_stop_protection_log).seconds >= 60:
                remaining = (self._stop_protection_until - now).seconds // 60
                logger.warning(f"[PROTECTION] 🛡️ Stop loss protection ACTIVE: {remaining} min remaining (consecutive stops: {self._consecutive_stops_count})")
                self._last_stop_protection_log = now
            return False
        
        # Блокировка истекла - сбрасываем счетчик
        if self._stop_protection_until and now >= self._stop_protection_until:
            logger.info(f"[PROTECTION] ✅ Stop loss protection LIFTED - trading resumed")
            self._consecutive_stops_count = 0
            self._stop_protection_until = None
            self._last_stop_protection_log = None
        
        return True
    
    def _check_profit_protection(self) -> bool:
        """
        Проверка защиты от жадности (фиксация прибыли).
        
        Блокирует торговлю на N минут после серии прибыльных сделок
        для фиксации заработанной прибыли.
        
        Returns:
            bool: True если торговля разрешена, False если заблокирована
        """
        # Проверяем включена ли защита
        protection_config = self.config.get('trading', {}).get('profit_protection', {})
        if not protection_config.get('enabled', False):
            return True
        
        now = datetime.now()
        
        # Проверяем активна ли блокировка
        if self._profit_protection_until and now < self._profit_protection_until:
            # Логируем только раз в минуту чтобы не спамить
            if not self._last_profit_protection_log or (now - self._last_profit_protection_log).seconds >= 60:
                remaining = (self._profit_protection_until - now).seconds // 60
                logger.info(f"[PROTECTION] 💎 Profit protection ACTIVE: {remaining} min remaining (consecutive wins: {self._consecutive_wins_count})")
                self._last_profit_protection_log = now
            return False
        
        # Блокировка истекла - сбрасываем счетчик
        if self._profit_protection_until and now >= self._profit_protection_until:
            logger.info(f"[PROTECTION] ✅ Profit protection LIFTED - trading resumed")
            self._consecutive_wins_count = 0
            self._profit_protection_until = None
            self._last_profit_protection_log = None
        
        return True
    
    def _register_trade_result(self, pnl: float, is_trailing_stop: bool = False):
        """
        Регистрация результата сделки для защиты от стопов и фиксации прибыли.
        
        Args:
            pnl: Прибыль/убыток сделки
            is_trailing_stop: True если сделка закрыта трейлинг стопом (учитывается как профит)
        """
        # === STOP LOSS PROTECTION ===
        stop_protection_config = self.config.get('trading', {}).get('stop_loss_protection', {})
        stop_protection_enabled = stop_protection_config.get('enabled', False)
        
        # === PROFIT PROTECTION ===
        profit_protection_config = self.config.get('trading', {}).get('profit_protection', {})
        profit_protection_enabled = profit_protection_config.get('enabled', False)
        
        # Прибыльная сделка (включая трейлинг стоп)
        if pnl > 0:
            # Сбрасываем счетчик стопов
            if stop_protection_enabled and self._consecutive_stops_count > 0:
                logger.info(f"[PROTECTION] ✅ Winning trade - reset stop counter (was {self._consecutive_stops_count})")
                self._consecutive_stops_count = 0
            
            # Считаем прибыльные сделки для profit protection
            if profit_protection_enabled:
                self._consecutive_wins_count += 1
                consecutive_wins_limit = profit_protection_config.get('consecutive_wins', 3)
                
                logger.info(f"[PROTECTION] 💰 Profitable trade - consecutive wins: {self._consecutive_wins_count}/{consecutive_wins_limit}")
                
                # Проверяем достигнут ли лимит прибыльных
                if self._consecutive_wins_count >= consecutive_wins_limit:
                    cooldown_minutes = profit_protection_config.get('cooldown_minutes', 10)
                    self._profit_protection_until = datetime.now() + timedelta(minutes=cooldown_minutes)
                    
                    logger.warning("="*80)
                    logger.warning(f"[PROTECTION] 💎 PROFIT PROTECTION ACTIVATED!")
                    logger.warning(f"[PROTECTION] Reason: {consecutive_wins_limit} consecutive winning trades")
                    logger.warning(f"[PROTECTION] Trading PAUSED to lock profits for: {cooldown_minutes} minutes")
                    logger.warning(f"[PROTECTION] Resume at: {self._profit_protection_until.strftime('%H:%M:%S')}")
                    logger.warning("="*80)
            return
        
        # Убыточная сделка (обычный стоп) - только если не трейлинг
        if pnl < 0 and not is_trailing_stop:
            # Сбрасываем счетчик прибыльных сделок
            if profit_protection_enabled and self._consecutive_wins_count > 0:
                logger.info(f"[PROTECTION] ❌ Losing trade - reset win counter (was {self._consecutive_wins_count})")
                self._consecutive_wins_count = 0
            
            # Считаем стопы для stop protection
            if stop_protection_enabled:
                self._consecutive_stops_count += 1
                consecutive_stops_limit = stop_protection_config.get('consecutive_stops', 2)
                
                logger.warning(f"[PROTECTION] ⚠️ Stop loss hit - consecutive stops: {self._consecutive_stops_count}/{consecutive_stops_limit}")
                
                # Проверяем достигнут ли лимит
                if self._consecutive_stops_count >= consecutive_stops_limit:
                    # Stop protection cooldown (15 minutes default)
                    cooldown_minutes = stop_protection_config.get('cooldown_minutes', 15)
                    self._stop_protection_until = datetime.now() + timedelta(minutes=cooldown_minutes)
                    
                    logger.warning("="*80)
                    logger.warning(f"[PROTECTION] 🛡️ STOP LOSS PROTECTION ACTIVATED!")
                    logger.warning(f"[PROTECTION] Reason: {consecutive_stops_limit} consecutive stop losses")
                    logger.warning(f"[PROTECTION] Trading blocked for: {cooldown_minutes} minutes")
                    logger.warning(f"[PROTECTION] Resume at: {self._stop_protection_until.strftime('%H:%M:%S')}")
                    logger.warning("="*80)
    
    def reset_protection(self):
        """Сброс всех защитных блокировок (вызывается из GUI)."""
        self._consecutive_stops_count = 0
        self._consecutive_wins_count = 0
        self._stop_protection_until = None
        self._profit_protection_until = None
        self._last_stop_protection_log = None
        self._last_profit_protection_log = None
        
        logger.info("="*80)
        logger.info("[PROTECTION] 🔓 PROTECTION RESET BY USER")
        logger.info("[PROTECTION] All counters and blocks cleared")
        logger.info("[PROTECTION] Trading resumed")
        logger.info("="*80)
        
        return True
    
    def _sync_protection_from_history(self):
        """Синхронизация защиты с историей сделок из файла.
        
        Вызывается каждый цикл для обработки новых закрытых сделок,
        которые появились в trades_history.json (через синхронизацию с MT5).
        Обрабатывает ТОЛЬКО СЕГОДНЯШНИЕ сделки.
        """
        try:
            from datetime import datetime
            
            trades_file = get_data_path('trades_history.json')
            if not trades_file.exists():
                return
            
            with open(trades_file, 'r', encoding='utf-8') as f:
                all_trades = json.load(f)
            
            if not all_trades:
                return
            
            # КРИТИЧНО: Берём только СЕГОДНЯШНИЕ сделки
            today = datetime.now().strftime('%Y-%m-%d')
            today_trades = [t for t in all_trades if t.get('date') == today]
            
            # Фильтруем новые сделки (которые еще не обработали)
            new_trades = [t for t in today_trades if int(t.get('id', 0)) > self._last_processed_trade_id]
            
            if not new_trades:
                return
            
            # Сортируем по ID (чтобы обрабатывать в правильном порядке)
            new_trades.sort(key=lambda x: int(x.get('id', 0)))
            
            logger.debug(f"[PROTECTION] Syncing {len(new_trades)} new trades from today")
            
            # Обрабатываем каждую новую сделку
            for trade in new_trades:
                trade_id = int(trade.get('id', 0))
                pnl = trade.get('pnl', 0)
                symbol = trade.get('instrument', trade.get('symbol', 'UNKNOWN'))
                ticket = trade.get('ticket', trade_id)  # Ticket может быть в 'ticket' или использовать trade_id
                
                # Для Pure AI все закрытия через SL/TP, не трейлинг
                is_trailing = False
                
                # Регистрируем результат для защиты
                self._register_trade_result(pnl=pnl, is_trailing_stop=is_trailing)
                
                # 🔥 Record trade result for Trade Filters (cooldown management)
                if self.ai_signal_manager and hasattr(self.ai_signal_manager, 'trade_filters'):
                    try:
                        self.ai_signal_manager.trade_filters.record_trade_result(symbol, pnl)
                    except Exception as e:
                        logger.debug(f"[Trade Filters] Failed to record result: {e}")
                
                # STATECORE: Log CLOSE event and clear active signal when position closed
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
                    
                    # Update status to WAITING
                    self.state_core.set_status(BotStatus.WAITING)
                
                # Обновляем ID последней обработанной сделки
                self._last_processed_trade_id = trade_id
                
        except Exception as e:
            logger.error(f"[PROTECTION] Failed to sync from history: {e}")
    
    def connect_mt5(self) -> bool:
        """Подключение к MetaTrader 5."""
        import MetaTrader5 as mt5
        
        # Загружаем данные из конфига
        mt5_config = self.mt5_config.get('mt5', {}).get('connection', {})
        
        login = mt5_config.get('login')
        password = mt5_config.get('password')
        server = mt5_config.get('server')
        path = mt5_config.get('path')
        
        # Инициализация MT5
        if not mt5.initialize(path=path):
            error = mt5.last_error()
            raise ConnectionError(f"MT5 initialize failed: {error}")
        
        # Авторизация
        if login and password and server:
            authorized = mt5.login(login=int(login), password=password, server=server)
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                raise ConnectionError(f"MT5 login failed: {error}")
        
        # Проверяем подключение
        account_info = mt5.account_info()
        if account_info is None:
            raise ConnectionError("Failed to get account info")
        
        self.connected = True
        self.account_info = account_info
        self.mt5_connector = mt5  # Для executor
        
        return True
    
    def get_connection_status(self) -> dict:
        """Возвращает статус подключения."""
        if not self.connected:
            return {'connected': False, 'message': 'Не подключено'}
        
        import MetaTrader5 as mt5
        info = mt5.account_info()
        
        if info:
            return {
                'connected': True,
                'message': 'Подключено',
                'broker': info.company,
                'account': info.login,
                'balance': info.balance,
                'equity': info.equity
            }
        return {'connected': False, 'message': 'Соединение потеряно'}
    
    def init_strategies(self):
        """Инициализация стратегий."""
        # Загружаем стратегии из конфига
        self.strategies = {}
        
        # КРИТИЧНО: В Pure AI mode стратегии НЕ используются
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            if bot_manager.trading_mode == 'pure_ai':
                logger.info("[Strategies] 🤖 Pure AI mode detected - strategy initialization SKIPPED")
                logger.info("[Strategies] All trading decisions will come from GPT-4 AI only")
                return
        except Exception as e:
            logger.warning(f"[Strategies] Could not check trading mode: {e}")
        
        instruments = self.instruments_config.get('instruments', {})
        
        for symbol, config in instruments.items():
            if config.get('enabled', False):
                # Получаем имя класса стратегии из конфига
                strategy_class = config.get('strategy_class', 'StrategyXAUUSD')
                
                try:
                    # Only XAUUSD strategy remains (EURUSD removed)
                    if strategy_class == 'StrategyXAUUSD' or symbol == 'XAUUSD':
                        from src.strategies.xauusd_strategy import StrategyXAUUSD
                        strategy = StrategyXAUUSD()
                        
                        # Применяем пользовательские настройки из config.json
                        try:
                            config_file = get_data_path('config.json')
                            if config_file.exists():
                                import json
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    user_config = json.load(f)
                                    strategy_settings = user_config.get('strategy', {})
                                    if strategy_settings:
                                        strategy.max_daily_trades = strategy_settings.get('max_daily_trades', strategy.max_daily_trades)
                                        strategy.max_daily_loss = strategy_settings.get('max_daily_loss', strategy.max_daily_loss)
                                        strategy.min_atr_threshold = strategy_settings.get('min_atr_threshold', strategy.min_atr_threshold)
                                        strategy.max_atr_threshold = strategy_settings.get('max_atr_threshold', strategy.max_atr_threshold)
                                        logger.info(f"[Strategy] ⚙️ Применены кастомные настройки для {symbol}: "
                                                  f"trades={strategy.max_daily_trades}, loss={strategy.max_daily_loss}%, "
                                                  f"ATR=[{strategy.min_atr_threshold}-{strategy.max_atr_threshold}]")
                        except Exception as e:
                            logger.warning(f"[Strategy] Failed to load custom settings: {e}")
                        
                        self.strategies[symbol] = strategy
                    else:
                        logger.warning(f"Unknown strategy class: {strategy_class} for {symbol}")
                        continue
                    
                    logger.info(f"Strategy loaded: {symbol} -> {strategy_class}")
                    
                except Exception as e:
                    logger.error(f"Failed to load strategy for {symbol}: {e}")
                    # Алерт об ошибке стратегии
                    if self.alert_manager:
                        self.alert_manager.alert_strategy_error(strategy_class, str(e))
    
    def _init_monitoring(self):
        """Инициализация системы мониторинга."""
        try:
            import yaml
            config_path = Path('config/telegram.yaml')
            
            if not config_path.exists():
                logger.warning("📱 [TELEGRAM] Config not found at config/telegram.yaml")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            tg_config = config.get('telegram', {})
            enabled = tg_config.get('enabled', False)
            bot_token = tg_config.get('bot_token', '').strip()
            chat_id = tg_config.get('chat_id', '').strip()
            
            logger.info(f"📱 [TELEGRAM] Config loaded: enabled={enabled}, token_len={len(bot_token)}, chat_id={chat_id}")
            
            if not enabled:
                logger.info("📱 [TELEGRAM] Notifications DISABLED in config (enabled: false)")
                return
            
            if not bot_token or not chat_id:
                logger.error(f"📱 [TELEGRAM] ❌ Cannot initialize: Missing credentials!")
                logger.error(f"📱 [TELEGRAM]    bot_token: {'EMPTY' if not bot_token else f'{len(bot_token)} chars'}")
                logger.error(f"📱 [TELEGRAM]    chat_id: {'EMPTY' if not chat_id else chat_id}")
                logger.error(f"📱 [TELEGRAM]    Please configure in Settings -> Telegram tab")
                return
            
            # Create TelegramNotifier
            timeout = tg_config.get('timeout', 30)
            retry_attempts = tg_config.get('retry_attempts', 3)
            retry_delay = tg_config.get('retry_delay', 2)
            
            self.telegram = TelegramNotifier(
                token=bot_token,
                chat_id=chat_id,
                timeout=timeout,
                retry_attempts=retry_attempts,
                retry_delay=retry_delay
            )
            self.notify_config = tg_config.get('notify', {})
            
            if self.telegram.enabled:
                logger.info("📱 [TELEGRAM] ✅ Notifications ENABLED and ready!")
                logger.info(f"📱 [TELEGRAM]    Notify on trade_opened: {self.notify_config.get('trade_opened', True)}")
                logger.info(f"📱 [TELEGRAM]    Notify on trade_closed: {self.notify_config.get('trade_closed', True)}")
                logger.info(f"📱 [TELEGRAM]    Notify on startup: {self.notify_config.get('startup', True)}")
            else:
                logger.error("📱 [TELEGRAM] ❌ Notifier created but NOT enabled (check token/chat_id)")
            
            # AlertManager
            self.alert_manager = AlertManager()
            
            # Обновляем telegram в AI Signal Manager если он был создан ранее
            if self.ai_signal_manager and self.telegram:
                self.ai_signal_manager.telegram = self.telegram
                logger.info("[LiveTrader] Telegram notifier set to AI Signal Manager")
            
            # Связываем с Telegram
            def telegram_alert_handler(alert):
                if self.telegram and self.notify_config.get('alerts', True):
                    if alert.level.value in ['WARNING', 'ERROR', 'CRITICAL']:
                        self.telegram.send_alert(
                            alert_type=alert.type.value,
                            message=alert.message,
                            level=alert.level.value
                        )
            
            self.alert_manager.add_handler(telegram_alert_handler)
                
        except Exception as e:
            logger.error(f"📱 [TELEGRAM] Failed to init monitoring: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def init_filters(self):
        """Инициализация фильтров."""
        # Инициализация GPT фильтра
        self.gpt_filter = None
        
        # Проверяем конфиг на enabled флаг
        try:
            import yaml
            with open('config/ai.yaml', 'r', encoding='utf-8') as f:
                ai_config = yaml.safe_load(f)
                news_filter_enabled = ai_config.get('news_filter', {}).get('enabled', False)
        except Exception as e:
            logger.warning(f"Failed to load news_filter config: {e}")
            news_filter_enabled = False
        
        if not news_filter_enabled:
            logger.info("📰 [NEWS FILTER] DISABLED by config (news_filter.enabled=false)")
        elif self.enable_gpt and GPT_AVAILABLE and news_filter_enabled:
            try:
                self.gpt_filter = GPTNewsFilter()
                logger.info("📰 [NEWS FILTER] ENABLED")
            except Exception as e:
                logger.warning(f"GPT Filter disabled: {e}")
        elif not self.enable_gpt:
            logger.info("GPT Filter disabled by user setting")
        else:
            logger.warning("GPT Filter not available (missing dependencies)")
        
        # Инициализация ML предиктора
        self.ml_predictor = None
        if ML_AVAILABLE:
            try:
                self.ml_predictor = TradePredictor()
                if self.ml_predictor.is_trained:
                    logger.info("ML Predictor loaded")
                else:
                    logger.warning("ML Predictor not trained yet")
            except Exception as e:
                logger.warning(f"ML Predictor disabled: {e}")
                # Алерт об ошибке ML
                if self.alert_manager:
                    self.alert_manager.alert_ml_error(str(e))
        else:
            logger.warning("ML Predictor not available (missing dependencies)")
    
    def _check_trading_hours(self) -> bool:
        """
        Проверить разрешено ли торговать сейчас
        
        Правила:
        - ЗАПРЕТ: 23:30 - 01:00 (каждый день) - Strict night ban
        - РАЗРЕШЕНО: Понедельник 01:00 - Пятница 21:00
        - ЗАПРЕТ: Суббота, Воскресенье
        
        Returns:
            True если торговля разрешена
        """
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        minute = now.minute
        
        # Проверка выходных
        if weekday >= 5:  # Saturday=5, Sunday=6
            if weekday == 5:
                logger.debug(f"[Trading Hours] Saturday - trading blocked")
            else:
                logger.debug(f"[Trading Hours] Sunday - trading blocked")
            return False
        
        # Проверка времени недели
        if weekday == 0 and hour < 1:  # Monday before 01:00
            logger.debug(f"[Trading Hours] Monday before 01:00 - trading blocked")
            return False
        
        if weekday == 4 and hour >= 21:  # Friday after 21:00
            logger.debug(f"[Trading Hours] Friday after 21:00 - trading blocked")
            return False
        
        # Проверка строгого запрета 23:30-01:10 (Strict night ban)
        if hour == 23 and minute >= 30:
            logger.debug(f"[Trading Hours] Night ban (23:30-01:10) - trading blocked")
            return False
        if hour == 0:  # 00:00-00:59
            logger.debug(f"[Trading Hours] Night ban (00:00-01:10) - trading blocked")
            return False
        if hour == 1 and minute < 10:  # 01:00-01:09
            logger.debug(f"[Trading Hours] Night ban (01:00-01:10) - trading blocked")
            return False
        
        return True
    
    def check_signals(self):
        """Проверка сигналов для всех стратегий."""
        # NOTE: Sync отключен - protection будет работать только с НОВЫМИ сделками
        # Чтобы избежать спама при старте (когда уже есть много закрытых сделок)
        # self._sync_protection_from_history()
        
        # Проверка времени торговли
        if not self._check_trading_hours():
            logger.debug("[LiveTrader] Trading blocked by schedule")
            return []
        
        # Проверка защиты от стопов
        if not self._check_stop_loss_protection():
            logger.debug("[LiveTrader] Trading blocked by stop loss protection")
            return []
        
        # Проверка защиты от жадности (фиксация прибыли)
        if not self._check_profit_protection():
            logger.debug("[LiveTrader] Trading blocked by profit protection")
            return []
        
        signals = []
        
        # Проверяем AI сигналы ПЕРЕД проверкой позиций (AI сигналы сохраняются и ждут)
        if self.ai_signal_manager:
            logger.debug("[LiveTrader] Checking AI signals...")
            ai_signals = self._check_ai_signals()
            if ai_signals:
                logger.info(f"[LiveTrader] Found {len(ai_signals)} AI signals")
                signals.extend(ai_signals)
                
                # КРИТИЧНО: Проверяем доступность GPT перед торговлей
                if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                    analyst = getattr(self.analyst_scheduler, 'analyst', None)
                    if analyst and not analyst.is_gpt_available():
                        logger.error("[LiveTrader] 🚫 GPT connection DISABLED - AI trading blocked")
                        logger.warning("[LiveTrader] Recovery in progress... waiting for GPT reconnection")
                        return signals  # Не торгуем пока GPT недоступен
                
                # Исполняем AI сигналы (multi-symbol: по 1 позиции на символ)
                if self.enable_trading:
                    for ai_signal in ai_signals:
                        symbol = ai_signal.get('symbol')
                        
                        # Проверяем позицию по конкретному символу
                        if self.executor and self.executor.has_position(symbol=symbol):
                            logger.debug(f"[LiveTrader] Position already open for {symbol} - skipping")
                            continue
                        
                        logger.info(f"[LiveTrader] Executing AI signal for {symbol}")
                        self.execute_trade(symbol, ai_signal)
                        # No break - allow multiple symbols to trade simultaneously
            else:
                logger.debug("[LiveTrader] No triggered AI signals found")
        else:
            logger.debug("[LiveTrader] AI signal manager not available")
        
        # Проверка обычных стратегий: SKIP если есть позиция ИЛИ если Pure AI mode активен
        if self.executor and self.executor.has_position():
            logger.debug("[LiveTrader] Position already open - skipping strategy signal checks")
            return signals
        
        # КРИТИЧНО: В Pure AI mode НЕ используем обычные стратегии
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            trading_mode = bot_manager.trading_mode
            
            if trading_mode == 'pure_ai' and self.ai_signal_manager:
                logger.debug("[LiveTrader] Pure AI mode active - skipping strategy signals")
                return signals
        except Exception as e:
            logger.debug(f"[LiveTrader] Could not check trading mode: {e}")
        
        for symbol, strategy in self.strategies.items():
            try:
                # Check AI permission first
                if not self._should_trade_allowed(symbol):
                    logger.info(f"[LiveTrader] Trading blocked by AI for {symbol}")
                    continue
                
                # Получаем данные
                h1_data, m15_data = self.load_market_data(symbol)
                
                if h1_data is None or m15_data is None:
                    logger.debug(f"[LiveTrader] No market data for {symbol}")
                    continue
                
                # Проверяем сигналы стратегии
                logger.debug(f"[LiveTrader] Checking strategy signals for {symbol}...")
                signal = strategy.check_signal(h1_data, m15_data)
                
                if signal and signal.get('valid', False):
                    logger.info(f"[LiveTrader] ✅ Valid signal from strategy: {signal.get('direction')} @ {signal.get('entry')}")
                    # Применяем фильтры
                    filtered_signal = self.process_signal(symbol, signal, h1_data, m15_data, len(m15_data)-1)
                    
                    if filtered_signal:
                        # Add fixed lot size from config (removed % risk calculation)
                        fixed_lot_size = self.config.get('trading', {}).get('risk', {}).get('fixed_lot_size', 0.01)
                        filtered_signal['lot_size'] = fixed_lot_size
                        filtered_signal['volume'] = fixed_lot_size  # Duplicate for compatibility
                        
                        # Apply AI risk multiplier (may reduce lot_size)
                        filtered_signal = self._apply_ai_risk_multiplier(symbol, filtered_signal)
                        
                        direction = "BUY" if filtered_signal.get('direction') == 'long' else "SELL"
                        signals.append(f"{symbol}: {direction} @ {filtered_signal.get('entry_price', 0):.5f}")
                        
                        # Если разрешена торговля, открываем сделку
                        if self.enable_trading:
                            self.execute_trade(symbol, filtered_signal)
                # Removed: NOT valid signal logging - too spammy in logs
            
            except Exception as e:
                logger.error(f"Error checking {symbol}: {e}")
        
        return signals
    
    def load_market_data(self, symbol: str):
        """Загрузка рыночных данных."""
        try:
            from src.core.data_loader import DataLoader
            
            data_loader = DataLoader(instrument=symbol.lower())
            h1_data, m15_data = data_loader.load()
            
            return h1_data, m15_data
            
        except Exception as e:
            # Только в файл лог, не спамить консоль
            logger.debug(f"Failed to load data for {symbol}: {e}")
            logger.debug("Backtest data file not found - normal for live trading")
            return None, None
    
    def process_signal(self, instrument: str, signal: dict, h1_data=None, m15_data=None, m15_idx=None):
        """Обработка сигнала с ML и GPT фильтрами."""
        
        if not signal.get('valid', False):
            logger.debug(f"[LiveTrader] Signal not valid, skipping")
            return None
        
        # 1. ML проверка (если есть данные)
        if h1_data is not None and m15_data is not None and m15_idx is not None:
            ml_ok, ml_prob = self.check_ml_filter(h1_data, m15_data, m15_idx, signal)
            if not ml_ok:
                logger.info(f"[LiveTrader] Signal filtered by ML (prob: {ml_prob:.1%})")
                return None
        
        # 2. GPT проверка
        gpt_ok, gpt_reason = self.check_gpt_filter(instrument)
        if not gpt_ok:
            logger.info(f"[LiveTrader] Signal filtered by GPT: {gpt_reason}")
            return None
        
        # Сигнал прошел все фильтры - возвращаем обработанный dict
        direction = "BUY" if signal.get('direction') == 'long' else "SELL"
        entry_price = signal.get('entry_price', signal.get('entry', 0))
        sl = signal.get('sl', signal.get('stop_loss', 0))
        tp = signal.get('tp', signal.get('take_profit', 0))
        
        processed_signal = {
            'symbol': instrument,
            'direction': signal.get('direction'),
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'valid': True
        }
        
        # Копируем дополнительные поля если есть
        for key in ['confidence', 'reasoning', 'source', 'ai_signal_id', 'timestamp']:
            if key in signal:
                processed_signal[key] = signal[key]
        
        logger.info(f"[LiveTrader] ✅ Signal passed all filters: {direction} @ {entry_price:.5f} (SL: {sl:.5f}, TP: {tp:.5f})")
        return processed_signal
    
    def check_ml_filter(self, h1_data, m15_data, m15_idx, signal):
        """ML фильтр сигнала."""
        if not self.ml_predictor:
            return True, 0.5
        
        try:
            # Получаем признаки для ML
            features = self.ml_predictor.extract_features(h1_data, m15_data, m15_idx)
            prediction = self.ml_predictor.predict(features)
            
            # Если предсказание не совпадает с сигналом, фильтруем
            signal_direction = 1 if signal.get('direction') == 'long' else 0
            if prediction != signal_direction:
                return False, prediction
            
            return True, prediction
        except Exception as e:
            logger.error(f"ML filter error: {e}")
            return True, 0.5
    
    def check_gpt_filter(self, instrument: str) -> Tuple[bool, str]:
        """GPT фильтр сигнала."""
        if not self.gpt_filter:
            return True, "GPT filter disabled"
        
        try:
            safe, risk_level, reason = self.gpt_filter.check_trading_safety(instrument)
            
            if not safe:
                return False, reason
            
            return True, reason
        except Exception as e:
            logger.error(f"GPT filter error: {e}")
            return True, "GPT filter error"
    
    def execute_trade(self, symbol: str, signal: dict):
        """Исполнение сделки."""
        try:
            # HARDCODED TRADING HOURS CHECK (removed from GUI)
            if not self._can_trade_now():
                logger.warning(f"[TRADE] Trading blocked by hardcoded hours/weekend restriction")
                return None
            
            # КРИТИЧНО: Проверяем статус сигнала - prevent duplicate trades
            signal_id = signal.get('ai_signal_id')
            if signal_id and self.ai_signal_manager:
                # Проверяем что сигнал ready для исполнения (pending или triggered)
                # 'pending' = ждет триггера, 'triggered' = цена достигла entry
                # 'filled' = уже исполнен (БЛОКИРУЕМ)
                active_signals = self.ai_signal_manager.get_active_signals(symbol=symbol)
                signal_found = False
                for s in active_signals:
                    if s.get('id') == signal_id:
                        status = s.get('status')
                        if status == 'filled':
                            logger.warning(f"[TRADE] Signal {signal_id} already filled - ignoring")
                            return None
                        if status not in ['pending', 'triggered']:
                            logger.warning(f"[TRADE] Signal {signal_id} has status {status} - ignoring")
                            return None
                        signal_found = True
                        break
                
                if not signal_found:
                    logger.warning(f"[TRADE] Signal {signal_id} not found in active signals - ignoring")
                    return None
            
            # Safety: Check GPT availability before trading
            if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                analyst = getattr(self.analyst_scheduler, 'analyst', None)
                if analyst and not analyst.is_gpt_available():
                    logger.error(f"[TRADE] 🚫 Cannot execute {symbol} trade - GPT connection disabled")
                    logger.warning("[TRADE] Trading blocked until GPT recovery completes")
                    return None
            
            # КРИТИЧНО: Проверяем нет ли уже открытой позиции ДЛЯ ЭТОГО СИМВОЛА (max 1 per symbol)
            try:
                positions = self.mt5_connector.positions_get(symbol=symbol)
                if positions and len(positions) > 0:
                    logger.warning(f"[TRADE] Position already open for {symbol} - ignoring new signal (max 1 per symbol)")
                    return None
            except Exception as e:
                logger.error(f"[TRADE] Failed to check positions for {symbol}: {e}")
                return None
            
            # Проверяем включена ли торговля для этого инструмента
            if not self._is_trading_enabled_for_instrument(symbol):
                logger.info(f"[TRADE] Trading disabled for {symbol} in config - signal ignored")
                return None
            
            # ✅ V5: ПРИМЕНЯЕМ НОВЫЕ ФИЛЬТРЫ ПЕРЕД ИСПОЛНЕНИЕМ
            direction = signal.get('direction', '').upper()
            if direction.lower() == 'long':
                direction = 'BUY'
            elif direction.lower() == 'short':
                direction = 'SELL'
            
            entry = signal.get('entry_price', signal.get('entry', 0))
            sl = signal.get('sl', signal.get('stop_loss', 0))
            tp = signal.get('tp', signal.get('take_profit', 0))
            
            # FIXED: Handle decimal confidence from signals (0-1 format)
            raw_confidence = signal.get('confidence', 75)
            if isinstance(raw_confidence, str):
                try:
                    raw_confidence = float(raw_confidence)
                except (ValueError, TypeError):
                    raw_confidence = 75
            
            # Convert decimal (0-1) to percentage (0-100)
            if isinstance(raw_confidence, (int, float)) and raw_confidence <= 1.0:
                confidence = int(raw_confidence * 100)  # Convert 0.85 → 85%
                logger.info(f"[LiveTrader] Converted decimal confidence {raw_confidence} → {confidence}%")
            else:
                confidence = int(raw_confidence) if raw_confidence > 1 else 75
            
            lot_size = signal.get('lot_size', signal.get('volume', 0.01))
            
            # 1️⃣ TECHNICAL CONFIRMATION FILTER
            if self.tech_filter and confidence < 80:
                try:
                    confirmed, reason, tech_data = self.tech_filter.confirm_signal(
                        symbol=symbol,
                        direction=direction,
                        confidence=confidence,
                        entry_price=entry
                    )
                    
                    if not confirmed:
                        logger.warning(f"[V5-TechFilter] ❌ Signal REJECTED: {reason}")
                        
                        # Emit risk_blocked event to GUI
                        if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                            try:
                                signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                                self.bot_queue.put({
                                    'type': 'risk_blocked',
                                    'signal_id': signal_id,
                                    'signal_id_short': signal_id_short,
                                    'reason': f"Technical Filter: {reason}",
                                    'filter_type': 'technical',
                                    'symbol': symbol
                                })
                                logger.debug(f"[TRADE] Event emitted: risk_blocked (TechFilter)")
                            except Exception as e:
                                logger.error(f"[TRADE] Failed to emit risk_blocked event: {e}")
                        
                        # Логируем отклонение
                        if self.rejected_logger:
                            self.rejected_logger.log_rejection(
                                symbol=symbol, direction=direction, confidence=confidence,
                                entry=entry, sl=sl, tp=tp,
                                reason=reason, filter_type='technical',
                                tech_data=tech_data
                            )
                        return None
                    
                    logger.info(f"[V5-TechFilter] ✅ Signal CONFIRMED: {reason}")
                except Exception as e:
                    logger.error(f"[V5-TechFilter] Filter error: {e}")
            
            # 2️⃣ SESSION ADAPTER
            if self.session_adapter:
                try:
                    new_sl, new_tp, new_lot, allowed, reason = self.session_adapter.adapt_signal_parameters(
                        entry=entry,
                        sl=sl,
                        tp=tp,
                        confidence=confidence,
                        lot=lot_size
                    )
                    
                    if not allowed:
                        logger.warning(f"[V5-SessionAdapter] ❌ Signal REJECTED: {reason}")
                        
                        # Emit risk_blocked event to GUI
                        if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                            try:
                                signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                                self.bot_queue.put({
                                    'type': 'risk_blocked',
                                    'signal_id': signal_id,
                                    'signal_id_short': signal_id_short,
                                    'reason': f"Session Adapter: {reason}",
                                    'filter_type': 'session',
                                    'symbol': symbol
                                })
                                logger.debug(f"[TRADE] Event emitted: risk_blocked (SessionAdapter)")
                            except Exception as e:
                                logger.error(f"[TRADE] Failed to emit risk_blocked event: {e}")
                        
                        # Логируем отклонение
                        if self.rejected_logger:
                            session_info = self.session_adapter.get_session_info()
                            self.rejected_logger.log_rejection(
                                symbol=symbol, direction=direction, confidence=confidence,
                                entry=entry, sl=sl, tp=tp,
                                reason=reason, filter_type='session',
                                session_info=session_info
                            )
                        return None
                    
                    # Применяем адаптированные параметры
                    signal['sl'] = new_sl
                    signal['stop_loss'] = new_sl
                    signal['tp'] = new_tp
                    signal['take_profit'] = new_tp
                    lot_size = new_lot
                    logger.info(f"[V5-SessionAdapter] ✅ Parameters adapted: {reason}")
                    
                except Exception as e:
                    logger.error(f"[V5-SessionAdapter] Adapter error: {e}")
            
            # 3️⃣ ADAPTIVE LOT SIZING
            if self.lot_sizer:
                try:
                    # Получаем последние сделки для ЭТОГО символа
                    recent_trades = self._get_recent_trades_for_lot_sizing(symbol=symbol)
                    
                    # Получаем базовый лот для этого инструмента
                    instrument_config = self.instruments_config.get('instruments', {}).get(symbol, {})
                    instrument_base_lot = instrument_config.get('base_lot', None)
                    instrument_max_lot = instrument_config.get('max_lot', None)
                    
                    # Рассчитываем адаптивный лот
                    signal_quality_mult = signal.get('quality_multiplier', 1.0)
                    session_mult = signal.get('session_multiplier', 1.0)
                    
                    adaptive_lot = self.lot_sizer.calculate_lot(
                        recent_trades=recent_trades,
                        current_confidence=confidence,
                        signal_quality_multiplier=signal_quality_mult,
                        session_multiplier=session_mult,
                        instrument_base_lot=instrument_base_lot,
                        instrument_max_lot=instrument_max_lot
                    )
                    
                    lot_size = adaptive_lot
                    logger.info(f"[V5-AdaptiveLot] ✅ Calculated adaptive lot for {symbol}: {lot_size:.2f} (base: {instrument_base_lot or 'default'})")
                    
                except Exception as e:
                    logger.error(f"[V5-AdaptiveLot] Calculation error: {e}")
            
            # Применяем финальный лот к сигналу
            signal['lot_size'] = lot_size
            signal['volume'] = lot_size
            
            # Добавляем max_spread_pips для spread filter в executor
            max_spread = self.config.get('trading', {}).get('risk', {}).get('max_spread_pips', 3.0)
            signal['max_spread_pips'] = max_spread
            
            # ✅ All risk checks passed - emit risk_ok event
            if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                try:
                    signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                    self.bot_queue.put({
                        'type': 'risk_ok',
                        'signal_id': signal_id,
                        'signal_id_short': signal_id_short,
                        'symbol': symbol,
                        'direction': direction,
                        'lot_size': lot_size
                    })
                    logger.debug(f"[TRADE] Event emitted: risk_ok (ID: {signal_id_short})")
                except Exception as e:
                    logger.error(f"[TRADE] Failed to emit risk_ok event: {e}")
            
            # ════════════════════════════════════════════════════════════════
            # SINGLE GATE: Единственный путь к ордеру - все проверки перед lock
            # ════════════════════════════════════════════════════════════════
            
            # Gate 1: Проверяем active_signal существует
            if not self.state_core.active_signal:
                logger.error("[TRADE] 🚨 GATE VIOLATION: No active_signal - cannot proceed to order")
                if signal_id:
                    from src.core.state_core import DecisionLog
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
                if signal_id:
                    from src.core.state_core import DecisionLog
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
                if signal_id:
                    from src.core.state_core import DecisionLog
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
            
            # STATECORE: Acquire order lock (защита от дублей)
            if not self.state_core.acquire_order_lock():
                logger.warning("[TRADE] ⚠️ Order lock already held - skipping duplicate order")
                return None
            
            try:
                # STATECORE: Update status to ORDERING
                self.state_core.set_status(BotStatus.ORDERING)
                self.state_core.last_order_ts = datetime.now()
                
                # ═══════════════════════════════════════════════════════════════
                # DRY_RUN MODE: Simulate order without real execution
                # ═══════════════════════════════════════════════════════════════
                dry_run = self.config.get('trading', {}).get('dry_run', False)
                
                if dry_run:
                    logger.warning(f"[DRY_RUN] 🧪 SIMULATING ORDER for {symbol} (no real execution)")
                    logger.info(f"[DRY_RUN] WOULD_SEND_ORDER: {direction} {lot_size} lots @ {entry}")
                    logger.info(f"[DRY_RUN] SL: {sl}, TP: {tp}, Confidence: {confidence}%")
                    
                    # Log simulated order to decision_logs
                    if signal_id:
                        from src.core.state_core import DecisionLog
                        self.state_core.log_decision(DecisionLog(
                            signal_id=signal_id,
                            timestamp=datetime.now().isoformat(),
                            symbol=symbol,
                            raw_signal=direction,
                            gpt_confidence=confidence,
                            gpt_reasoning=signal.get('reasoning', 'DRY_RUN test'),
                            filters={'dry_run': {'passed': True, 'reason': 'Simulated in DRY_RUN mode'}},
                            setup_score=confidence,
                            final_decision="SIMULATED",
                            block_reason=f"DRY_RUN: Would send {direction} order"
                        ))
                    
                    # Emit simulated event to UI
                    if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                        try:
                            signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                            self.bot_queue.put({
                                'type': 'dry_run_simulated',
                                'signal_id': signal_id,
                                'signal_id_short': signal_id_short,
                                'symbol': symbol,
                                'direction': direction,
                                'lot_size': lot_size,
                                'entry': entry,
                                'sl': sl,
                                'tp': tp
                            })
                            logger.debug(f"[DRY_RUN] Event emitted: dry_run_simulated")
                        except Exception as e:
                            logger.error(f"[DRY_RUN] Failed to emit event: {e}")
                    
                    # Clear active signal in DRY_RUN mode
                    self.state_core.clear_active_signal(reason="DRY_RUN simulation completed")
                    
                    # Set status back to MONITORING
                    self.state_core.set_status(BotStatus.MONITORING)
                    
                    logger.info(f"[DRY_RUN] ✅ Simulation completed for {symbol}")
                    return {'simulated': True, 'symbol': symbol, 'direction': direction}
                
                # ═══════════════════════════════════════════════════════════════
                # REAL EXECUTION (dry_run = False)
                # ═══════════════════════════════════════════════════════════════
                
                result = self.executor.execute_signal(symbol, signal)
                
                if result:
                    logger.info(f"[TRADE] ✅ Order sent successfully for {symbol}")
                    
                    # ═══════════════════════════════════════════════════════════════
                    # POSITION CONFIRMATION: Verify position opened with 3 retries
                    # ═══════════════════════════════════════════════════════════════
                    
                    position_confirmed, ticket = self.state_core.confirm_position_opened(
                        symbol=symbol,
                        retries=3,
                        delay=0.5
                    )
                    
                    if not position_confirmed:
                        # Position not confirmed after retries
                        logger.error(f"[TRADE] 🚨 CRITICAL: Order sent but position NOT confirmed for {symbol}")
                        
                        # Set ERROR status
                        self.state_core.set_status(BotStatus.ERROR, reason="Order sent but no position")
                        
                        # Log to decision_logs
                        if signal_id:
                            from src.core.state_core import DecisionLog
                            self.state_core.log_decision(DecisionLog(
                                signal_id=signal_id,
                                timestamp=datetime.now().isoformat(),
                                symbol=symbol,
                                raw_signal=direction if 'direction' in locals() else "UNKNOWN",
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
                    logger.info(f"[TRADE] ✅ Position confirmed: {symbol} ticket={ticket}")
                    
                    # STATECORE: Save ticket and opened_at to active_signal
                    if self.state_core.active_signal:
                        self.state_core.active_signal.ticket = ticket
                        self.state_core.active_signal.opened_at = datetime.now().isoformat()
                        logger.info(f"[StateCore] Position tracking: ticket={ticket}, opened_at={self.state_core.active_signal.opened_at}")
                    
                    # STATECORE: Update status to TRADING (position confirmed)
                    self.state_core.set_status(BotStatus.TRADING)
                else:
                    # Order execution returned False/None
                    logger.warning(f"[TRADE] ⚠️ Order execution returned {result} for {symbol}")
                    self.state_core.set_status(BotStatus.WAITING)
                    
            finally:
                # STATECORE: Always release order lock
                self.state_core.release_order_lock()
            
            if result:
                logger.info(f"Trade executed for {symbol}: {result}")
                
                # Извлекаем данные из сигнала (используется в нескольких местах)
                direction = signal.get('direction', '').upper()
                if direction.lower() == 'long':
                    direction = 'BUY'
                elif direction.lower() == 'short':
                    direction = 'SELL'
                
                entry = signal.get('entry_price', 0)
                sl = signal.get('sl', signal.get('stop_loss', 0))
                tp = signal.get('tp', signal.get('take_profit', 0))
                lot_size = signal.get('lot_size', signal.get('volume', 0.01))
                
                # Отмечаем AI сигнал как исполненный (если есть)
                if self.ai_signal_manager and signal.get('ai_signal_id'):
                    try:
                        filled_price = signal.get('entry_price', 0)
                        self.ai_signal_manager.mark_signal_filled(
                            signal_id=signal['ai_signal_id'],
                            filled_price=filled_price
                        )
                    except Exception as e:
                        logger.error(f"[TRADE] Failed to mark AI signal as filled: {e}")
                
                # Отправка Telegram уведомления
                if self.telegram:
                    try:
                        # Определяем режим торговли
                        from src.core.bot_manager import BotManager
                        bot_manager = BotManager()
                        trading_mode = bot_manager.trading_mode
                        
                        reasoning = signal.get('reasoning', '')
                        
                        # FIXED: Handle confidence format (decimal or percentage)
                        raw_conf = signal.get('confidence', 0)
                        if isinstance(raw_conf, (int, float)) and raw_conf <= 1.0:
                            confidence = raw_conf * 100  # Convert decimal to %
                        else:
                            confidence = raw_conf  # Already in %
                        
                        # Отправляем уведомление
                        self.telegram.send_trade_opened(
                            symbol=symbol,
                            direction=direction,
                            lot=lot_size,
                            entry=entry,
                            sl=sl,
                            tp=tp,
                            mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                            reasoning=reasoning,
                            confidence=confidence
                        )
                        logger.info(f"[Telegram] Trade opened notification sent for {symbol}")
                    except Exception as tg_error:
                        logger.error(f"[Telegram] Failed to send trade opened notification: {tg_error}")
                
                # Запоминаем позицию для отслеживания закрытия и трейлинга
                try:
                    # Получаем последнюю открытую позицию из MT5
                    positions = self.mt5_connector.positions_get(symbol=symbol)
                    if positions and len(positions) > 0:
                        pos = positions[-1]  # Последняя открытая позиция
                        
                        # Вычисляем расстояние до ТП для трейлинга
                        tp_distance = abs(tp - entry)
                        
                        self.tracked_positions[pos.ticket] = {
                            'symbol': symbol,
                            'direction': direction,
                            'entry_price': entry,
                            'sl': sl,
                            'current_sl': sl,  # Инициализируем текущий SL
                            'tp': tp,
                            'tp_distance': tp_distance,  # NEW: for trailing calculations
                            'entry_time': datetime.now(),
                            'volume': lot_size,
                            'sl_moved': False,  # Флаг что SL еще не перемещен
                            'breakeven_moved': False  # Флаг что breakeven еще не выполнен
                        }
                        
                        # Логирование параметров позиции
                        logger.info(f"[Position] ✅ Tracking #{pos.ticket} ({symbol} {direction})")
                        logger.info(f"[Position]    Entry: ${entry:.2f}, SL: ${sl:.2f}, TP: ${tp:.2f}")
                        logger.info(f"[Position]    TP Distance: ${tp_distance:.2f} (used for trailing calculation)")
                        logger.info(f"[Position]    🎯 Trailing activates at: +${tp_distance * 0.30:.2f} (30% of TP)")
                        
                except Exception as track_error:
                    logger.error(f"[Position] Failed to track position: {track_error}")
                
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {e}")
    
    def check_trailing_stop(self):
        """
        V4 Trailing Stop - Fixed parameters for M5 scalping.
        
        Uses TrailingStopV4 module with fixed activation/stop levels.
        """
        # Check if trailing stop enabled in config
        trailing_config = self.config.get('trading', {}).get('trailing_stop', {})
        if not trailing_config.get('enabled', False):
            # Log once that trailing is disabled (avoid spam)
            if not hasattr(self, '_trailing_disabled_logged'):
                logger.info("[V4-Trailing] ⛔ Trailing stop DISABLED in settings")
                self._trailing_disabled_logged = True
            return
        
        # Reset flag when enabled (for next disable)
        if hasattr(self, '_trailing_disabled_logged'):
            logger.info("[V4-Trailing] ✅ Trailing stop ENABLED (30% activation, 50% stop)")
            delattr(self, '_trailing_disabled_logged')
        
        if not self.tracked_positions:
            # Log periodically that no positions tracked (every 60 seconds)
            if not hasattr(self, '_last_no_positions_log') or (datetime.now() - self._last_no_positions_log).total_seconds() > 60:
                logger.debug("[V4-Trailing] No positions to track")
                self._last_no_positions_log = datetime.now()
            return
        
        try:
            # V4: Use new simplified trailing stop handler
            if hasattr(self, 'trailing_v4'):
                self.trailing_v4.check_and_apply(self.tracked_positions)
            else:
                logger.warning("[LiveTrader] V4 trailing stop handler not initialized")
        
        except Exception as e:
            logger.error(f"[V4-Trailing] Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _modify_position_sl(self, ticket: int, new_sl: float, symbol: str = None) -> bool:
        """Изменяет Stop Loss открытой позиции."""
        try:
            # Получаем текущую позицию
            positions = self.mt5_connector.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                logger.warning(f"[TrailingSL] Position #{ticket} not found")
                return False
            
            position = positions[0]
            symbol = symbol or position.symbol
            
            # Нормализуем SL по digit symbol
            symbol_info = self.mt5_connector.symbol_info(symbol)
            if symbol_info:
                new_sl = round(new_sl, symbol_info.digits)
            
            # Формируем запрос на модификацию
            request = {
                "action": self.mt5_connector.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": new_sl,
                "tp": position.tp,
                "magic": 123456,
                "comment": "Trailing SL",
            }
            
            # Отправляем запрос
            result = self.mt5_connector.order_send(request)
            
            if result and result.retcode == self.mt5_connector.TRADE_RETCODE_DONE:
                logger.info(f"[TrailingSL] ✅ MT5 confirmed SL modification for #{ticket}")
                return True
            else:
                error_code = result.retcode if result else "No result"
                error_msg = result.comment if result else "No response from MT5"
                logger.error(f"[TrailingSL] ❌ Failed to modify SL for #{ticket}: [{error_code}] {error_msg}")
                return False
        
        except Exception as e:
            logger.error(f"[TrailingSL] Error modifying SL: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def check_closed_positions(self):
        """Проверяет закрытые позиции и отправляет Telegram уведомления."""
        # FIXED: Works WITHOUT Telegram - logging always active
        
        # Import datetime at function start to avoid UnboundLocalError
        from datetime import datetime, timedelta
        import time
        
        try:
            # Проходим по отслеживаемым позициям (если они есть)
            for ticket in list(self.tracked_positions.keys()):
                pos_info = self.tracked_positions[ticket]
                
                # Пропускаем если уже обработали закрытие
                if pos_info.get('notification_sent', False):
                    continue
                
                # Проверяем есть ли позиция в открытых
                position = self.mt5_connector.positions_get(ticket=ticket)
                
                if not position or len(position) == 0:
                    # Позиция закрыта - проверяем историю
                    logger.info(f"[Closed] Position #{ticket} CLOSED - fetching history...")
                    
                    # Даём MT5 время записать в историю (500ms)
                    time.sleep(0.5)
                    
                    # Ищем в истории сделок (расширенный диапазон - 24 часа)
                    history = self.mt5_connector.history_deals_get(
                        datetime.now() - timedelta(hours=24),
                        datetime.now()
                    )
                    
                    deal_found = False
                    closing_deal = None
                    
                    if history:
                        for deal in history:
                            if deal.position_id == ticket and deal.entry == 1:  # 1 = OUT
                                deal_found = True
                                closing_deal = deal
                                logger.info(f"[Closed] Found closing deal for #{ticket}, profit=${deal.profit:.2f}")
                                break
                    
                    if deal_found and closing_deal:
                        # Нашли сделку закрытия - отправляем полный отчёт
                        pos_info = self.tracked_positions[ticket]
                        
                        # Вычисляем profit напрямую из MT5
                        profit = closing_deal.profit if hasattr(closing_deal, 'profit') else 0.0
                        
                        # Вычисляем длительность
                        duration = datetime.now() - pos_info['entry_time']
                        hours = int(duration.total_seconds() // 3600)
                        minutes = int((duration.total_seconds() % 3600) // 60)
                        duration_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
                        
                        # Вычисляем пипсы
                        price_diff = abs(closing_deal.price - pos_info['entry_price'])
                        pips = price_diff * 10000  # для forex
                        if pos_info['symbol'] == 'XAUUSD':
                            pips = price_diff * 100  # для золота
                        
                        # Определяем причину закрытия ПРАВИЛЬНО
                        # Сравниваем цену закрытия с TP и SL
                        close_price = closing_deal.price
                        entry_price = pos_info['entry_price']
                        sl_price = pos_info.get('sl', 0)
                        tp_price = pos_info.get('tp', 0)
                        
                        # Определяем насколько близко к TP/SL закрылась сделка
                        tp_distance = abs(close_price - tp_price) if tp_price else 999999
                        sl_distance = abs(close_price - sl_price) if sl_price else 999999
                        
                        # Если закрылась ближе к TP - значит взяла TP
                        # Если ближе к SL - значит взяла SL
                        # Порог - 0.5$ для XAUUSD
                        CLOSE_THRESHOLD = 0.5
                        
                        if profit > 1.0:  # Прибыльная сделка
                            if tp_distance < CLOSE_THRESHOLD:
                                result_reason = "Take Profit"
                            else:
                                result_reason = "Trailing Stop"
                        elif profit < -1.0:  # Убыточная сделка
                            if sl_distance < CLOSE_THRESHOLD:
                                result_reason = "Stop Loss"
                            else:
                                result_reason = "Manual Close"
                        else:  # Около нуля
                            result_reason = "Breakeven"
                        
                        # Получаем режим торговли
                        from src.core.bot_manager import BotManager
                        bot_manager = BotManager()
                        trading_mode = bot_manager.trading_mode
                        
                        # 🔥 CRITICAL: ALWAYS log closure (even without Telegram)
                        logger.info("=" * 70)
                        logger.info(f"[Closed] 🏁 POSITION CLOSED: #{ticket}")
                        logger.info(f"[Closed]    Symbol: {pos_info['symbol']} {pos_info['direction']}")
                        logger.info(f"[Closed]    Entry: ${pos_info['entry_price']:.2f} → Close: ${close_price:.2f}")
                        logger.info(f"[Closed]    SL: ${sl_price:.2f}, TP: ${tp_price:.2f}")
                        logger.info(f"[Closed]    💰 Profit: ${profit:.2f} ({pips:.1f} pips)")
                        logger.info(f"[Closed]    ⏱️ Duration: {duration_str}")
                        logger.info(f"[Closed]    🎯 Reason: {result_reason}")
                        logger.info(f"[Closed]    TP distance: ${tp_distance:.2f}, SL distance: ${sl_distance:.2f}")
                        logger.info("=" * 70)
                        
                        # Отправляем уведомление (только если Telegram настроен)
                        if self.telegram:
                            try:
                                self.telegram.send_trade_closed(
                                    symbol=pos_info['symbol'],
                                    direction=pos_info['direction'],
                                    profit=profit,
                                    pips=pips,
                                    duration=duration_str,
                                    mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                                    result_reason=result_reason
                                )
                                logger.info(f"[Telegram] Trade closed notification sent for #{ticket}")
                            except Exception as tg_error:
                                logger.error(f"[Telegram] Failed to send closure notification: {tg_error}")
                        
                        # Логируем результат в ML систему
                        if self.ml_collector:
                            try:
                                # Безопасно получаем время открытия
                                opened_at = pos_info.get('entry_time') or pos_info.get('opened_at') or datetime.now()
                                if isinstance(opened_at, datetime):
                                    open_time_str = opened_at.isoformat()
                                else:
                                    open_time_str = str(opened_at)
                                
                                trade_data = {
                                    'id': ticket,
                                    'open_time': open_time_str,
                                    'close_time': datetime.now().isoformat(),
                                    'instrument': pos_info['symbol'],
                                    'direction': pos_info['direction'],
                                    'volume': pos_info.get('volume', 0.01),
                                    'entry_price': pos_info.get('entry_price', 0),
                                    'exit_price': current_price,
                                    'sl': pos_info.get('sl', 0),
                                    'tp': pos_info.get('tp', 0),
                                    'pnl': profit,
                                    'close_reason': result_reason,
                                    'session': self._get_session(datetime.now().hour),
                                    'open_atr': 0,  # TODO: сохранять при открытии
                                    'open_rsi': 0,
                                    'open_ema_trend': ''
                                }
                                # Пытаемся найти AI данные для этой сделки
                                ai_data = pos_info.get('ai_data')  # Если сохранили при открытии
                                
                                logger.info(f"[ML] Logging trade outcome: #{ticket} {pos_info['direction']} ${profit:.2f}")
                                self.ml_collector.log_trade_outcome(trade_data, ai_data)
                            except Exception as e:
                                logger.warning(f"[ML] ⚠️ Failed to log trade outcome for #{ticket}: {e}")
                                import traceback
                                logger.warning(f"[ML] Traceback: {traceback.format_exc()}")
                        
                        # Регистрируем результат сделки для защиты от стопов
                        is_trailing = (result_reason == "Trailing Stop")
                        self._register_trade_result(pnl=profit, is_trailing_stop=is_trailing)
                        
                        # Удаляем из отслеживаемых
                        del self.tracked_positions[ticket]
                    
                    else:
                        # Не нашли в истории - отправляем уведомление с примерными данными
                        pos_info = self.tracked_positions[ticket]
                        logger.warning(f"[Closed] Deal for #{ticket} not found in history - sending notification with estimated data")
                        
                        # Пытаемся рассчитать profit по текущей цене
                        estimated_profit = 0.0
                        estimated_pips = 0.0
                        duration_str = "N/A"
                        try:
                            # Получаем текущую цену
                            tick = self.mt5_connector.symbol_info_tick(pos_info['symbol'])
                            if tick:
                                current_price = tick.bid if pos_info['direction'] == 'BUY' else tick.ask
                                entry_price = pos_info.get('entry_price', 0)
                                volume = pos_info.get('volume', 0.01)
                                open_time = pos_info.get('entry_time')
                                
                                # Рассчитываем длительность
                                if open_time:
                                    from datetime import datetime, timedelta
                                    # open_time уже является datetime объектом из tracked_positions
                                    if isinstance(open_time, str):
                                        open_dt = datetime.fromisoformat(open_time)
                                    elif isinstance(open_time, datetime):
                                        open_dt = open_time
                                    else:
                                        # Если это timestamp (int/float)
                                        open_dt = datetime.fromtimestamp(open_time)
                                    
                                    duration = datetime.now() - open_dt
                                    minutes = int(duration.total_seconds() / 60)
                                    seconds = int(duration.total_seconds() % 60)
                                    duration_str = f"{minutes}m {seconds}s"
                                
                                if entry_price > 0:
                                    # Рассчитываем profit
                                    if pos_info['direction'] == 'BUY':
                                        price_diff = current_price - entry_price
                                    else:  # SELL
                                        price_diff = entry_price - current_price
                                    
                                    # ИСПРАВЛЕНО: Правильный расчет для XAUUSD
                                    # Contract size = 100 унций, но формула должна быть:
                                    # profit = price_diff * volume * contract_size / 100
                                    # Для volume=0.01: price_diff * 0.01 * 100 = price_diff * 1.0
                                    # Например: price_diff = -2.43, volume = 0.01 → profit = -2.43
                                    contract_size = 100  # XAUUSD = 100 унций на лот
                                    lot_to_oz = volume * contract_size  # 0.01 lot = 1 oz
                                    estimated_profit = price_diff * lot_to_oz
                                    estimated_pips = price_diff * 100  # 1 pip = $0.01
                                    logger.info(f"[Closed] Estimated profit: ${estimated_profit:.2f} ({estimated_pips:.1f} pips), duration: {duration_str}")
                        except Exception as e:
                            logger.error(f"[Closed] Failed to calculate estimated profit: {e}")
                        
                        # 🔥 CRITICAL: ALWAYS log closure (even without Telegram)
                        logger.info("=" * 70)
                        logger.info(f"[Closed] 🏁 POSITION CLOSED (NOT IN HISTORY): #{ticket}")
                        logger.info(f"[Closed]    Symbol: {pos_info['symbol']} {pos_info['direction']}")
                        logger.info(f"[Closed]    Entry: ${pos_info.get('entry_price', 0):.2f}")
                        logger.info(f"[Closed]    💰 Estimated Profit: ${estimated_profit:.2f} ({estimated_pips:.1f} pips)")
                        logger.info(f"[Closed]    ⏱️ Duration: {duration_str}")
                        logger.info(f"[Closed]    🎯 Reason: Manual Close or Trailing Stop")
                        logger.info(f"[Closed]    ⚠️ Deal not found in MT5 history - using estimated data")
                        logger.info("=" * 70)
                        
                        # Отправляем уведомление (только если Telegram настроен)
                        if self.telegram and self.notify_config.get('trade_closed', True):
                            try:
                                from src.core.bot_manager import BotManager
                                bot_manager = BotManager()
                                trading_mode = bot_manager.trading_mode
                                
                                self.telegram.send_trade_closed(
                                    symbol=pos_info['symbol'],
                                    direction=pos_info['direction'],
                                    profit=estimated_profit,
                                    pips=estimated_pips,
                                    duration=duration_str,
                                    mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                                    result_reason="Trailing Stop"
                                )
                                logger.info(f"[Telegram] Trade closed notification sent for #{ticket} (estimated data)")
                            except Exception as tg_error:
                                logger.error(f"[Telegram] Failed to send closure notification: {tg_error}")
                        
                        # NOTE: Trade history is now managed by bot_manager._sync_with_mt5()
                        # This prevents duplicate entries in trades_history.json
                        # The sync happens periodically and pulls accurate data from MT5
                        
                        try:
                            # Just update bot_manager stats (no manual file write)
                            from src.core.bot_manager import BotManager
                            bot_manager = BotManager()
                            bot_manager.load_stats()  # Reload from file
                            
                        except Exception as e:
                            logger.error(f"[History] Failed to save trade: {e}")
                        
                        # Удаляем из tracked
                        del self.tracked_positions[ticket]
                    
                    # AUTO-REQUERY: Trigger GPT analysis after position close (configurable cooldown)
                    if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                        cooldown = self.config.get('trading', {}).get('signal_ttl', {}).get('requery_cooldown_minutes', 5)
                        logger.info(f"[LiveTrader] 🔄 Position closed - triggering GPT analysis in {cooldown} minutes")
                        self.analyst_scheduler.trigger_immediate_analysis(
                            symbol=pos_info['symbol'],
                            reason="position_closed",
                            cooldown_minutes=cooldown
                        )
                        # Mark that analysis was triggered to prevent FALLBACK duplicate
                        self._last_fallback_analysis_time = datetime.now()
            
            # FALLBACK: Если нет tracked позиций, но есть закрытые сделки в MT5
            # Проверяем последние сделки и запускаем анализ если нужно
            # NOTE: Skip if position_closed already triggered above (prevents duplicate analysis)
            if not self.tracked_positions:
                # Нет отслеживаемых позиций - проверяем MT5 напрямую
                current_positions = self.mt5_connector.positions_get()
                if not current_positions or len(current_positions) == 0:
                    # Нет открытых позиций в MT5
                    # Проверяем есть ли активные сигналы
                    has_active_signals = False
                    if self.ai_signal_manager:
                        active_signals = self.ai_signal_manager.get_active_signals()
                        has_active_signals = len(active_signals) > 0
                    
                    # Если нет позиций и нет сигналов - запускаем анализ через 5 минут
                    if not has_active_signals:
                        # БЛОКИРОВКА: Не запускать fallback анализ ночью или в выходные
                        if not self._can_trade_now():
                            logger.debug("[LiveTrader] FALLBACK blocked - outside trading hours")
                        elif hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                            # Проверяем когда был последний анализ
                            last_analysis_time = getattr(self, '_last_fallback_analysis_time', None)
                            current_time = datetime.now()
                            
                            cooldown = self.config.get('trading', {}).get('signal_ttl', {}).get('requery_cooldown_minutes', 5)
                            cooldown_seconds = cooldown * 60
                            
                            if last_analysis_time is None or (current_time - last_analysis_time).total_seconds() > cooldown_seconds:
                                logger.info(f"[LiveTrader] 🔄 FALLBACK: No positions and no signals - triggering analysis in {cooldown} min")
                                self.analyst_scheduler.trigger_immediate_analysis(
                                    symbol='XAUUSD',
                                    reason="fallback_no_positions",
                                    cooldown_minutes=cooldown
                                )
                                self._last_fallback_analysis_time = current_time
        
        except Exception as e:
            logger.error(f"[Telegram] Failed to check closed positions: {e}")
    
    def save_trade(self, trade: dict):
        """
        DEPRECATED: Trade saving is now handled by bot_manager._sync_with_mt5()
        This function is kept for backwards compatibility but does nothing.
        All trades are synced from MT5 automatically to prevent duplicates.
        """
        logger.debug(f"[save_trade] DEPRECATED - trades are synced from MT5 automatically")
        pass
    
    def _get_recent_trades_for_lot_sizing(self, symbol: str = None, lookback_trades: int = 10) -> list:
        """
        📊 V5: Получить последние закрытые сделки для расчета адаптивного лота.
        
        Args:
            symbol: Символ инструмента (если None, берет все сделки)
            lookback_trades: Количество последних сделок (по умолчанию 10)
        
        Returns:
            Список словарей с информацией о сделках:
            [{'profit': float, 'success': bool, 'timestamp': datetime}, ...]
        """
        recent_trades = []
        
        try:
            import MetaTrader5 as mt5
            
            # Получаем историю сделок за последние 30 дней
            history = self.mt5_connector.history_deals_get(
                datetime.now() - timedelta(days=30),
                datetime.now()
            )
            
            if not history:
                logger.debug(f"[V5-AdaptiveLot] No trade history found for {symbol or 'all symbols'}")
                return []
            
            # Фильтруем только закрывающие сделки (entry=1 означает OUT)
            closing_deals = [deal for deal in history if deal.entry == 1]
            
            # Фильтруем по символу, если указан
            if symbol:
                closing_deals = [deal for deal in closing_deals if deal.symbol == symbol]
            
            # Берем последние N сделок
            for deal in closing_deals[-lookback_trades:]:
                trade_info = {
                    'profit': deal.profit,
                    'success': deal.profit > 0,
                    'timestamp': datetime.fromtimestamp(deal.time),
                    'symbol': deal.symbol,
                    'volume': deal.volume
                }
                recent_trades.append(trade_info)
            
            symbol_info = f" for {symbol}" if symbol else " (all symbols)"
            logger.debug(f"[V5-AdaptiveLot] Loaded {len(recent_trades)} recent trades{symbol_info} for lot calculation")
            return recent_trades
            
        except Exception as e:
            logger.error(f"[V5-AdaptiveLot] Failed to get trade history: {e}")
            return []
    
    # ========== AI Integration Methods ==========
    
    def _check_ai_signals(self) -> list:
        """
        Проверка и исполнение AI сигналов.
        
        Returns:
            List of triggered AI signals ready for execution
        """
        if not self.ai_signal_manager:
            logger.debug("[AI] Signal manager not available")
            return []
        
        triggered_signals = []
        
        try:
            import MetaTrader5 as mt5
            current_time = datetime.now()
            
            logger.debug(f"[AI] Checking signals at {current_time.strftime('%H:%M:%S')}")
            
            # Проверяем каждый символ
            for symbol in ['XAUUSD', 'EURUSD']:
                # Получаем текущую цену
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    logger.debug(f"[AI] No tick data for {symbol}")
                    continue
                
                current_price = (tick.bid + tick.ask) / 2
                logger.debug(f"[AI] {symbol} current price: {current_price}")
                
                # Проверяем триггеры
                signals = self.ai_signal_manager.check_triggers(
                    current_price=current_price,
                    symbol=symbol,
                    current_time=current_time
                )
                
                logger.debug(f"[AI] {symbol} found {len(signals) if signals else 0} triggered signals")
                
                if signals:
                    for ai_signal in signals:
                        # Конвертируем AI сигнал в формат стратегии
                        strategy_signal = self._convert_ai_signal_to_strategy(ai_signal)
                        
                        logger.info(
                            f"[AI-Signal] Triggered: {symbol} {ai_signal.type} "
                            f"@ {ai_signal.entry_price} (conf: {ai_signal.confidence}%)"
                        )
                        
                        # Логируем AI решение в ML систему
                        if self.ml_collector:
                            try:
                                # Пропускаем NONE actions (это ошибки валидации, не реальные сигналы)
                                if ai_signal.type in ['BUY', 'SELL']:
                                    ai_data = {
                                        'action': ai_signal.type,
                                        'confidence': ai_signal.confidence,
                                        'entry_price': ai_signal.entry_price,
                                        'sl_price': ai_signal.stop_loss,
                                        'tp_price': ai_signal.take_profit,
                                        'reasoning': ai_signal.reasoning,
                                        'market_context': getattr(ai_signal, 'market_context', 'N/A')
                                    }
                                    # Market данные для ML - расширенная версия
                                    market_data = {
                                        'timestamp': datetime.now(),
                                        'symbol': symbol,
                                        'price': current_price,
                                        'bid': tick.bid,
                                        'ask': tick.ask,
                                        'spread': round((tick.ask - tick.bid) * 10, 1),  # В пипсах для золота
                                        # TODO: Добавить индикаторы из MarketAnalyst когда будет доступно
                                        'atr_14': 0,  # Пока заполняем нулями
                                        'rsi_14': 0,
                                        'ema_20': 0,
                                        'ema_50': 0,
                                        'ema_200': 0,
                                        'ema_trend': 'unknown'
                                    }
                                    self.ml_collector.log_ai_decision(ai_data, market_data, triggered=True, executed=False)
                                else:
                                    logger.debug(f"[ML] Skipping NONE action (validation error or invalid signal)")
                            except Exception as e:
                                logger.debug(f"[ML] Failed to log AI decision: {e}")
                        
                        # НЕ исполняем здесь - будет исполнено в основном цикле check_signals
                        # Это предотвращает двойной вход в сделку
                        
                        triggered_signals.append(strategy_signal)
        
        except Exception as e:
            logger.error(f"[AI] Signal check failed: {e}", exc_info=True)
        
        return triggered_signals
    
    def _convert_ai_signal_to_strategy(self, ai_signal) -> dict:
        """
        Конвертация AI сигнала в формат стратегии.
        
        Args:
            ai_signal: AISignal объект
        
        Returns:
            Dict в формате стратегии
            
        Note: Uses AI-calculated SL/TP values which are already properly adapted
        for instrument type, volatility, and session.
        """
        # Get fixed lot size from config (removed % risk calculation)
        fixed_lot_size = self.config.get('trading', {}).get('risk', {}).get('fixed_lot_size', 0.01)
        
        # ✅ USE AI-CALCULATED SL/TP (already adapted for volatility/session)
        symbol = ai_signal.symbol
        entry_price = ai_signal.entry_price
        direction = 'long' if ai_signal.type.upper() == 'BUY' else 'short'
        
        # Use SL/TP from AI signal (already calculated by market_analyst with proper adaptation)
        sl_price = ai_signal.stop_loss
        tp_price = ai_signal.take_profit
        
        # Log what we're using
        if 'XAU' in symbol or 'GOLD' in symbol:
            sl_distance_dollars = abs(entry_price - sl_price)
            tp_distance_dollars = abs(entry_price - tp_price)
            logger.info(f"[AI-Convert] {symbol} {direction.upper()}: Using AI-calculated SL/TP")
            logger.info(f"[AI-Convert]    Entry: ${entry_price:.2f}, SL: ${sl_price:.2f} (${sl_distance_dollars:.2f}), TP: ${tp_price:.2f} (${tp_distance_dollars:.2f})")
        else:
            sl_distance_pips = abs(entry_price - sl_price) * 10000
            tp_distance_pips = abs(entry_price - tp_price) * 10000
            logger.info(f"[AI-Convert] {symbol} {direction.upper()}: Using AI-calculated SL/TP")
            logger.info(f"[AI-Convert]    Entry: {entry_price:.5f}, SL: {sl_price:.5f} ({sl_distance_pips:.1f} pips), TP: {tp_price:.5f} ({tp_distance_pips:.1f} pips)")
        
        return {
            'symbol': ai_signal.symbol,
            'direction': direction,
            'entry_price': entry_price,
            'sl': sl_price,  # ✅ From AI (market_analyst adaptive calculation)
            'tp': tp_price,  # ✅ From AI (market_analyst adaptive calculation)
            'stop_loss': sl_price,  # Дублируем для совместимости
            'take_profit': tp_price,
            'confidence': ai_signal.confidence,  # Keep as percentage (0-100), not decimal
            'reasoning': ai_signal.reasoning,
            'source': 'AI-GPT',
            'ai_signal_id': ai_signal.id,
            'valid': True,  # AI сигналы всегда валидны после проверки
            'timestamp': datetime.now().isoformat(),
            'lot_size': fixed_lot_size,  # Fixed lot from config (but will be overridden by adaptive_lot in execute flow)
            'volume': fixed_lot_size  # Duplicate for compatibility
        }
    
    def _should_trade_allowed(self, symbol: str) -> bool:
        """Check if AI allows trading for symbol."""
        if not self.ai_signal_manager:
            return True  # AI not available, allow trading
        
        try:
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission(symbol)
            
            if not allowed:
                logger.warning(f"[AI] Trading blocked for {symbol}: {reason}")
            
            return allowed
        except Exception as e:
            logger.error(f"[AI] Permission check failed: {e}")
            return True  # Fail-safe: allow trading on error
    
    def _apply_ai_risk_multiplier(self, symbol: str, signal: dict) -> dict:
        """Apply AI risk multiplier to signal position size."""
        if not self.ai_signal_manager:
            return signal
        
        try:
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission(symbol)
            
            if multiplier != 1.0:
                logger.info(f"[AI] Applying risk multiplier {multiplier:.2f}x for {symbol}: {reason}")
                
                # Reduce position size
                if 'volume' in signal:
                    signal['volume'] = signal['volume'] * multiplier
                
                # Store original and modified for logging
                signal['ai_risk_multiplier'] = multiplier
                signal['ai_risk_reason'] = reason
            
            return signal
        except Exception as e:
            logger.error(f"[AI] Risk multiplier failed: {e}")
            return signal  # Fail-safe: return original signal
    
    def _get_session(self, hour: int) -> str:
        """Определяет торговую сессию по часу."""
        if 2 <= hour < 10:
            return 'ASIA'
        elif 10 <= hour < 16:
            return 'EUROPE'
        elif 16 <= hour < 22:
            return 'US'
        else:
            return 'OFF_HOURS'
"""
Bot Manager - управление состоянием бота

Синглтон для управления ботом из веб-интерфейса.
"""

import threading
import queue
from enum import Enum
from datetime import datetime
from typing import Optional, Callable
import json
import csv
from pathlib import Path
import sys
from src.core.logger import logger
from src.core.config_manager import get_config_manager

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

# Мониторинг
try:
    from src.monitoring import TelegramNotifier, AlertManager
    from src.monitoring.telegram_bot import TelegramBotWithButtons
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring modules not available")

# Cleanup Service
try:
    from src.core.cleanup_service import CleanupService
    CLEANUP_AVAILABLE = True
except ImportError:
    CLEANUP_AVAILABLE = False
    logger.warning("Cleanup service not available")

# ML Data Collector
try:
    from src.ml import MLDataCollector
    ML_DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    ML_DATA_COLLECTOR_AVAILABLE = False
    logger.debug("ML Data Collector not available")


class BotStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"       # Bot idle, waiting for next analysis
    ANALYZING = "analyzing"   # GPT analysis in progress
    BLOCKED = "blocked"       # Trade blocked by filters
    ORDERING = "ordering"     # Placing order to MT5
    ERROR = "error"           # Error state


class BotManager:
    """Менеджер состояния бота."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.status = BotStatus.STOPPED
        self.is_running = False  # Для Telegram бота
        self.mode = 'demo'  # Режим работы: demo, backtest, live
        
        # Load trading_mode from config
        self.config_manager = get_config_manager()
        self.trading_mode = self.config_manager.get('trading.yaml', 'trading', 'mode', 'manual')
        logger.info(f"[BotManager] Trading mode loaded from config: {self.trading_mode}")
        
        # Register config reload callback
        self.config_manager.register_reload_callback(self._on_config_reload)
        
        self.bot_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # MT5 Manager (устанавливается извне)
        self.mt5_manager = None
        
        # LiveTrader instance (устанавливается при запуске)
        self.live_trader = None
        
        # Signal Manager для управления AI сигналами
        self.signal_manager = None
        
        # Логи для веб-интерфейса
        self.logs: list = []
        self.max_logs = 100
        
        # Статистика
        self.stats = {
            'balance': 100.0,
            'total_pnl': 0.0,
            'today_pnl': 0.0,
            'total_trades': 0,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'open_positions': [],
            'last_date': datetime.now().strftime('%Y-%m-%d')  # Для отслеживания смены дня
        }
        
        # Callback для обновления UI
        self.on_update: Optional[Callable] = None
        
        # Система мониторинга
        self.telegram = None
        self.telegram_bot = None  # Бот с кнопками
        self.telegram_bot_thread = None
        self.alert_manager = None
        if MONITORING_AVAILABLE:
            self._init_monitoring()
        
        # Система автоочистки
        self.cleanup_service = None
        if CLEANUP_AVAILABLE:
            self._init_cleanup()
        
        # ML Data Collector для сбора данных для обучения
        self.ml_collector = None
        if ML_DATA_COLLECTOR_AVAILABLE:
            try:
                self.ml_collector = MLDataCollector()
                logger.debug("[BotManager] ML Data Collector initialized")
            except Exception as e:
                logger.error(f"[BotManager] Failed to init ML Data Collector: {e}")
        
        # Загружаем историю
        self.load_stats()
    
    def set_mt5_manager(self, mt5_manager):
        """Установка MT5 Manager для получения реальной статистики."""
        self.mt5_manager = mt5_manager
        logger.info("MT5 Manager connected to BotManager")
        
        # Синхронизация с MT5 после подключения
        self._sync_with_mt5()
    
    def _on_config_reload(self):
        """Callback вызываемый при перезагрузке конфигурации."""
        try:
            old_mode = self.trading_mode
            new_mode = self.config_manager.get('trading.yaml', 'trading', 'mode', 'manual')
            
            if old_mode != new_mode:
                self.trading_mode = new_mode
                logger.info(f"[BotManager] Trading mode updated: {old_mode} → {new_mode}")
            else:
                logger.debug(f"[BotManager] Trading mode unchanged: {new_mode}")
                
        except Exception as e:
            logger.error(f"[BotManager] Failed to reload config: {e}")
    
    def _update_stats_from_mt5(self):
        """Обновление статистики из MT5."""
        if self.mt5_manager and self.mt5_manager.is_connected():
            try:
                account_info = self.mt5_manager.get_account_info()
                if account_info:
                    # Получаем текущий баланс из MT5 (единственный источник правды)
                    current_balance = account_info.get('balance', self.stats['balance'])
                    self.stats['balance'] = current_balance
                    self.stats['equity'] = account_info.get('equity', account_info.get('balance', 0))
                    
                    # Рассчитываем total_pnl как: текущий баланс - начальный баланс
                    starting_balance = self.stats.get('starting_balance', current_balance)
                    self.stats['total_pnl'] = round(current_balance - starting_balance, 2)
                    
                    logger.debug(f"Stats updated from MT5: balance=${current_balance:.2f}, total_pnl=${self.stats['total_pnl']:.2f}")
                    return True
            except Exception as e:
                logger.error(f"Failed to update stats from MT5: {e}")
        return False
    
    def _init_monitoring(self):
        """Инициализация системы мониторинга."""
        try:
            import yaml
            from src.core.credentials import CredentialsLoader
            
            # Загружаем credentials из внешнего файла
            creds = CredentialsLoader.load()
            bot_token = creds.get('TELEGRAM_BOT_TOKEN')
            chat_id = creds.get('TELEGRAM_CHAT_ID')
            
            # Если нет в credentials, пробуем из telegram.yaml (fallback)
            if not bot_token or not chat_id:
                config_path = Path('config/telegram.yaml')
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    tg_config = config.get('telegram', {})
                    bot_token = bot_token or tg_config.get('bot_token')
                    chat_id = chat_id or tg_config.get('chat_id')
                else:
                    logger.info("Telegram config not found, notifications disabled")
                    return
            
            # Загружаем остальные настройки из yaml (не credentials)
            config_path = Path('config/telegram.yaml')
            tg_config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                tg_config = config.get('telegram', {})
            
            if bot_token and chat_id:
                timeout = tg_config.get('timeout', 30)
                timeout = tg_config.get('timeout', 30)
                retry_attempts = tg_config.get('retry_attempts', 3)
                retry_delay = tg_config.get('retry_delay', 2)
                logger.info(f"[BotManager] Initializing Telegram: token={'***' + bot_token[-4:] if bot_token else 'NONE'}, chat_id={chat_id}")
                
                self.telegram = TelegramNotifier(
                    token=bot_token,
                    chat_id=chat_id,
                    timeout=timeout,
                    retry_attempts=retry_attempts,
                    retry_delay=retry_delay
                )
                self.notify_config = tg_config.get('notify', {})
                logger.info(f"[BotManager] Telegram notifications enabled: {self.telegram.enabled}")
                logger.info(f"[BotManager] Notify config: {self.notify_config}")
                
                # Запускаем Telegram бот с кнопками
                if bot_token and tg_config.get('enable_bot', True):
                    self.telegram_bot = TelegramBotWithButtons(bot_token, bot_manager=self)
                    # Запускаем бот в отдельном потоке
                    self.telegram_bot_thread = threading.Thread(
                        target=self.telegram_bot.start_polling,
                        daemon=True,
                        name="TelegramBotThread"
                    )
                    self.telegram_bot_thread.start()
                    logger.info("🤖 Telegram бот с кнопками запущен")
                
                # Инициализация AlertManager
                self.alert_manager = AlertManager()
                
                # Инициализируем Signal Manager с Telegram
                if not self.signal_manager:
                    try:
                        from src.ai.signal_manager import AISignalManager
                        self.signal_manager = AISignalManager(
                            telegram_notifier=self.telegram,
                            bot_queue=getattr(self, 'bot_queue', None)  # Pass bot_queue for events
                        )
                        logger.info("[BotManager] Signal Manager initialized with Telegram notifications")
                    except Exception as e:
                        logger.warning(f"[BotManager] Failed to init Signal Manager: {e}")
                
                # Связываем AlertManager с Telegram
                def telegram_alert_handler(alert):
                    if self.telegram and self.notify_config.get('alerts', True):
                        min_level = tg_config.get('alert_min_level', 'WARNING')
                        if alert.level.value in ['WARNING', 'ERROR', 'CRITICAL']:
                            self.telegram.send_alert(
                                alert_type=alert.type.value,
                                message=alert.message,
                                level=alert.level.value
                            )
                
                self.alert_manager.add_handler(telegram_alert_handler)
                logger.info("AlertManager linked to Telegram")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
    
    def _init_cleanup(self):
        """Инициализация системы автоочистки."""
        try:
            # Cleanup Service загрузит конфиг сам из config/cleanup.yaml
            self.cleanup_service = CleanupService()
            self.cleanup_service.start()  # Запускаем фоновый поток
            logger.info("🧹 Cleanup service initialized and started")
            
        except Exception as e:
            logger.error(f"Failed to initialize cleanup service: {e}")
    
    def reload_config(self):
        """
        Перезагрузка настроек без перезапуска бота.
        Применяет изменения из конфигурационных файлов.
        """
        try:
            import yaml
            logger.info("="*80)
            logger.info("[BotManager] 🔄 Перезагрузка конфигурации...")
            
            # Перезагрузка Telegram настроек
            config_path = Path('config/telegram.yaml')
            if config_path.exists() and MONITORING_AVAILABLE:
                logger.info("[BotManager] 📱 Перезагрузка Telegram настроек...")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                tg_config = config.get('telegram', {})
                if tg_config.get('enabled', False):
                    bot_token = tg_config.get('bot_token')
                    chat_id = tg_config.get('chat_id')
                    
                    # Переинициализация Telegram notifier
                    if self.telegram:
                        self.telegram.token = bot_token
                        self.telegram.chat_id = chat_id
                        logger.info(f"[BotManager] ✅ Telegram обновлён (chat_id: {chat_id})")
                    else:
                        self.telegram = TelegramNotifier(token=bot_token, chat_id=chat_id)
                        logger.info(f"[BotManager] ✅ Telegram инициализирован (chat_id: {chat_id})")
                    
                    self.notify_config = tg_config.get('notify', {})
                    notify_list = [k for k, v in self.notify_config.items() if v]
                    logger.info(f"[BotManager] 📬 Уведомления включены: {', '.join(notify_list) if notify_list else 'нет'}")
                else:
                    self.telegram = None
                    logger.info("[BotManager] ❌ Telegram отключен")
            else:
                logger.info("[BotManager] ⚠️ Telegram config не найден или модуль недоступен")
            
            # Перезагрузка MT5 (если менеджер установлен)
            mt5_config_path = Path('config/mt5.yaml')
            if mt5_config_path.exists() and self.mt5_manager:
                logger.info("[BotManager] 🔌 MT5 настройки будут применены при следующем подключении")
            
            # Перезагрузка Risk настроек
            portfolio_path = Path('config/portfolio.yaml')
            if portfolio_path.exists():
                logger.info("[BotManager] 💰 Перезагрузка risk настроек...")
                with open(portfolio_path, 'r', encoding='utf-8') as f:
                    portfolio = yaml.safe_load(f)
                    risk = portfolio.get('risk_per_trade_percent', 1.0)
                    logger.info(f"[BotManager] ✅ Risk per trade: {risk}%")
            
            # Перезагрузка AI настроек
            ai_path = Path('config/ai.yaml')
            if ai_path.exists():
                logger.info("[BotManager] 🤖 Перезагрузка AI настроек...")
                with open(ai_path, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f)
                    enabled = ai_config.get('market_analyst', {}).get('enabled', True)
                    model = ai_config.get('market_analyst', {}).get('gpt', {}).get('model', 'gpt-4o')
                    validity = ai_config.get('market_analyst', {}).get('signals', {}).get('validity_minutes', 60)
                    logger.info(f"[BotManager] ✅ AI Analysis: {'Включён' if enabled else 'Отключён'} (model: {model}, validity: {validity}min)")
            
            # Перезагрузка Trailing Stop настроек
            trading_path = Path('config/trading.yaml')
            if trading_path.exists():
                with open(trading_path, 'r', encoding='utf-8') as f:
                    trading_config = yaml.safe_load(f)
                    trailing_enabled = trading_config.get('trading', {}).get('trailing_stop', {}).get('enabled', False)
                    if trailing_enabled:
                        activation = trading_config.get('trading', {}).get('trailing_stop', {}).get('activation_profit_percent', 30)
                        stop_dist = trading_config.get('trading', {}).get('trailing_stop', {}).get('stop_distance_percent', 50)
                        logger.info(f"[BotManager] 🔒 Trailing Stop: ✅ ВКЛЮЧЁН (активация: {activation}%, стоп: {stop_dist}%)")
                    else:
                        logger.info("[BotManager] 🔒 Trailing Stop: ⛔ ОТКЛЮЧЁН")
            
            # Другие настройки (strategy, etc.) применяются автоматически
            # при следующей проверке сигналов
            
            logger.info("[BotManager] ✅ Все настройки успешно перезагружены!")
            logger.info("="*80)
            return True
            
        except Exception as e:
            logger.error(f"[BotManager] ❌ Ошибка перезагрузки настроек: {e}")
            return False
    
    def get_current_settings(self):
        """Получить текущие активные настройки."""
        try:
            import yaml
            settings = {
                'trading_mode': self.trading_mode,
                'status': self.status.value,
                'mt5_connected': self.mt5_manager.is_connected() if self.mt5_manager else False,
                'telegram_enabled': bool(self.telegram),
            }
            
            # Загружаем настройки риска
            portfolio_path = Path('config/portfolio.yaml')
            if portfolio_path.exists():
                with open(portfolio_path, 'r', encoding='utf-8') as f:
                    portfolio = yaml.safe_load(f)
                    settings['risk_percent'] = portfolio.get('risk_per_trade_percent', 1.0)
            
            # Загружаем настройки AI
            ai_path = Path('config/ai.yaml')
            if ai_path.exists():
                with open(ai_path, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f)
                    settings['ai_enabled'] = ai_config.get('enabled', True)
                    settings['ai_model'] = ai_config.get('model', 'gpt-4o')
            
            return settings
        except Exception as e:
            logger.error(f"[BotManager] Ошибка получения настроек: {e}")
            return {}
    
    def start(self, mode: str = 'demo', trading_mode: str = 'strategy', bot_queue=None):
        """
        Запуск бота.
        
        Args:
            mode: Режим счета ('demo' или 'live')
            trading_mode: Режим торговли ('strategy' или 'pure_ai')
            bot_queue: Queue for event-driven UI updates
        """
        if self.status == BotStatus.RUNNING:
            self.log("Warning: Bot already running")
            return False
        
        self.stop_event.clear()
        self.pause_event.clear()
        self.trading_mode = trading_mode  # Сохраняем режим торговли
        self.bot_queue = bot_queue  # Store bot_queue for passing to components
        self.status = BotStatus.RUNNING
        self.is_running = True  # Для Telegram бота
        
        # Запускаем в отдельном потоке
        self.bot_thread = threading.Thread(
            target=self._run_bot,
            args=(mode,),
            daemon=True
        )
        self.bot_thread.start()
        
        self.log(f"Bot started in {mode.upper()} mode | Trading: {trading_mode.upper()}")
        
        # Обновляем статистику из MT5 перед отправкой уведомления
        self._update_stats_from_mt5()
        
        # Сохраняем статистику для Telegram бота
        self.save_stats()
        
        # Telegram уведомление
        logger.info(f"[BotManager] Checking Telegram notification: telegram={self.telegram}, notify_startup={self.notify_config.get('startup', True) if hasattr(self, 'notify_config') else 'NO_CONFIG'}")
        if self.telegram and self.notify_config.get('startup', True):
            instruments = list(self.stats.get('instruments', ['XAUUSD', 'EURUSD']))
            logger.info(f"[BotManager] Sending startup notification for {trading_mode} mode with {instruments}")
            result = self.telegram.send_startup(
                mode=trading_mode,  # Передаем режим торговли (strategy/pure_ai)
                instruments=instruments
            )
            logger.info(f"[BotManager] Startup notification result: {result}")
        else:
            logger.warning(f"[BotManager] Startup notification skipped: telegram={bool(self.telegram)}, config={hasattr(self, 'notify_config')}")
        
        return True
    
    def stop(self):
        """Остановка бота."""
        if self.status == BotStatus.STOPPED:
            self.log("Warning: Bot already stopped")
            return False
        
        self.stop_event.set()
        self.status = BotStatus.STOPPED
        self.is_running = False  # Для Telegram бота
        
        # Уменьшен таймаут для быстрой остановки
        if self.bot_thread:
            self.bot_thread.join(timeout=1)  # Было 5, теперь 1 секунда
        
        # Останавливаем cleanup service
        if self.cleanup_service:
            self.cleanup_service.stop()
            logger.info("🧹 Cleanup service stopped")
        
        self.log("Bot stopped")
        
        # Все операции с файлами и сетью делаем асинхронно
        # чтобы не блокировать вызывающий поток
        import threading
        def _async_cleanup():
            try:
                # Обновляем статистику из MT5 перед отправкой уведомления
                self._update_stats_from_mt5()
                
                # Сохраняем статистику для Telegram бота
                self.save_stats()
                
                # Telegram уведомление
                if self.telegram and self.notify_config.get('shutdown', True):
                    self.telegram.send_shutdown(
                        mode=self.trading_mode,  # Передаем режим торговли
                        stats=self.stats
                    )
            except Exception as e:
                logger.error(f"[BotManager] Error in async cleanup: {e}")
        
        # Запускаем cleanup в фоне
        threading.Thread(target=_async_cleanup, daemon=True, name="CleanupThread").start()
        
        return True
    
    def pause(self):
        """Пауза бота."""
        if self.status != BotStatus.RUNNING:
            self.log("Warning: Bot not running")
            return False
        
        self.pause_event.set()
        self.status = BotStatus.PAUSED
        self.log("Bot paused (no new trades will be opened)")
        return True
    
    def resume(self):
        """Возобновление бота."""
        if self.status != BotStatus.PAUSED:
            return False
        
        self.pause_event.clear()
        self.status = BotStatus.RUNNING
        self.log("Bot resumed")
        return True
    
    def set_mode(self, mode: str):
        """Установка режима работы."""
        if mode not in ['demo', 'backtest', 'live']:
            self.log(f"Warning: Invalid mode: {mode}")
            return False
        
        self.mode = mode
        self.log(f"[CHANGE] Mode changed to {mode.upper()}")
        return True
    
    def _run_bot(self, mode: str):
        """
        Инициализация LiveTrader (БЕЗ собственного цикла).
        
        ВАЖНО: Основной trading loop работает в app.py (_run_trading_loop).
        BotManager только создаёт и хранит LiveTrader для использования GUI.
        
        Собственный цикл ОТКЛЮЧЁН для предотвращения race conditions.
        """
        try:
            # Импортируем необходимые компоненты
            from src.live.live_trader import LiveTrader
            import yaml
            from pathlib import Path
            
            # Читаем режим торговли из конфига (а не из mode!)
            enable_trading = False  # Default
            trading_config_path = Path('config/trading.yaml')
            if trading_config_path.exists():
                with open(trading_config_path, 'r', encoding='utf-8') as f:
                    trading_config = yaml.safe_load(f)
                    enable_trading = trading_config.get('trading', {}).get('enabled', False)
            
            logger.info(f"[BotManager] Account mode: {mode.upper()}, Trading from config: {'ON' if enable_trading else 'OFF'}")
            
            # Инициализация LiveTrader
            # LiveTrader сам загружает конфиги, подключается к MT5, 
            # инициализирует стратегии и создает executor
            self.live_trader = LiveTrader(
                config_dir='config',
                enable_trading=enable_trading,
                enable_gpt=True,  # GPT фильтр включен
                bot_queue=getattr(self, 'bot_queue', None)  # Pass bot_queue for event-driven UI
            )
            
            self.log(f"LiveTrader initialized (trading={'ON' if enable_trading else 'OFF'})")
            self.log("BotManager: LiveTrader ready - GUI loop will handle trading")
            
            # ЦИКЛ ОТКЛЮЧЁН - app.py делает всю работу
            # Просто ждём команды остановки
            while not self.stop_event.is_set():
                self.stop_event.wait(5)  # Просто спим, проверяя stop_event
            
            self.log("BotManager: Stop signal received")
                
        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.status = BotStatus.STOPPED
    
    def log(self, message: str) -> None:
        """Добавление сообщения в лог с автоматической очисткой старых записей."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            'time': timestamp,
            'message': message
        }
        
        # Добавляем запись
        self.logs.append(log_entry)
        
        # Обрезаем лог СРАЗУ при превышении лимита (исправление memory leak)
        if len(self.logs) > self.max_logs:
            # Удаляем старые записи, оставляем только последние max_logs
            excess = len(self.logs) - self.max_logs
            self.logs = self.logs[excess:]
        
        # Выводим в лог через logger
        logger.info(message)
    
    def add_trade(self, trade: dict):
        """Добавление сделки."""
        # Проверяем смену даты и сбрасываем today_pnl если наступил новый день
        today = datetime.now().strftime('%Y-%m-%d')
        last_date = self.stats.get('last_date', today)
        
        if today != last_date:
            logger.info(f"[STATS] New day detected: {last_date} -> {today}. Resetting today_pnl from ${self.stats.get('today_pnl', 0):.2f} to $0")
            self.stats['today_pnl'] = 0.0
            self.stats['last_date'] = today
        
        # Обновляем статистику
        pnl = trade.get('pnl', 0)
        # УДАЛЕНО: Не добавляем к total_pnl и balance - они берутся из MT5!
        # total_pnl будет пересчитан как: текущий balance - starting_balance
        
        # Обновляем счётчики сделок (синхронизируем оба ключа для совместимости)
        self.stats['total_trades'] += 1
        self.stats['trades'] = self.stats.get('trades', 0) + 1
        
        if pnl > 0:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        
        # Проверяем сегодняшняя ли сделка
        if trade.get('date') == today:
            self.stats['today_pnl'] += pnl
        
        # Проверки алертов (если включены)
        if self.alert_manager:
            # Проверка дневного убытка
            if self.stats.get('today_pnl', 0) < 0:
                starting_balance = self.stats.get('starting_balance', self.stats.get('balance', 10000))
                self.alert_manager.check_daily_loss(self.stats['today_pnl'], starting_balance)
            
            # Проверка винрейта
            total = self.stats.get('total_trades', 0)
            if total >= 20:  # Минимум 20 сделок для статистики
                wins = self.stats.get('wins', 0)
                winrate = (wins / total) * 100 if total > 0 else 0
                self.alert_manager.check_winrate_drop(winrate, min_trades=total)
        
        # Сохраняем в файл
        self.save_trade(trade)
        self.save_stats()
        # Вызов callback для обновления UI / внешних обработчиков
        try:
            if self.on_update and callable(self.on_update):
                try:
                    self.on_update()
                except Exception:
                    pass
        except Exception:
            pass
    
    def save_trade(self, trade: dict):
        """Сохранение сделки в файл (JSON + CSV) с атомарной записью."""
        trades_file = get_data_path('trades_history.json')
        trades_file.parent.mkdir(exist_ok=True)
        
        trades = []
        if trades_file.exists():
            try:
                with open(trades_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
            except Exception:
                trades = []

        # Защита от дубликатов по ticket/id
        existing_ids = set()
        for t in trades:
            try:
                if t.get('id') is not None:
                    existing_ids.add(int(t.get('id')))
            except Exception:
                continue

        try:
            if trade.get('id') is not None and int(trade.get('id')) in existing_ids:
                return
        except Exception:
            pass

        # Конвертируем datetime объекты в строки для JSON сериализации
        trade_copy = trade.copy()
        for key, value in trade_copy.items():
            if isinstance(value, datetime):
                trade_copy[key] = value.isoformat()
        
        trades.append(trade_copy)

        # Атомарное сохранение: пишем во временный файл, потом переименовываем
        temp_file = trades_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(trades, f, indent=2, ensure_ascii=False, default=str)
            # Атомарная замена - если бот упадёт ВО ВРЕМЯ записи, основной файл не пострадает
            temp_file.replace(trades_file)
            
            # Экспортируем в CSV после успешного сохранения JSON
            self._export_trades_to_csv(trades)
            
            # Логируем в ML систему для анализа
            if self.ml_collector:
                try:
                    self.ml_collector.log_trade_outcome(trade, ai_data=None)
                except Exception as e:
                    logger.debug(f"[ML] Failed to log trade outcome: {e}")
            
        except Exception as e:
            logger.error(f"[SAVE TRADE] Ошибка атомарного сохранения: {e}")
            # Удаляем временный файл если он остался
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def _export_trades_to_csv(self, trades: list):
        """Экспорт всех сделок в CSV файл для удобного анализа."""
        try:
            csv_file = get_data_path('trades_history.csv')
            
            # Если нет сделок, не создаём пустой файл
            if not trades:
                return
            
            # Определяем колонки CSV
            fieldnames = [
                'id', 'date', 'time', 'instrument', 'direction', 
                'volume', 'entry_price', 'exit_price', 'sl', 'tp',
                'pnl', 'commission', 'swap', 'duration_minutes',
                'close_reason', 'strategy', 'confidence'
            ]
            
            # Пишем в CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for trade in trades:
                    # Подготавливаем строку с данными
                    row = {
                        'id': trade.get('id', ''),
                        'date': trade.get('date', ''),
                        'time': trade.get('time', ''),
                        'instrument': trade.get('instrument', ''),
                        'direction': trade.get('direction', ''),
                        'volume': trade.get('volume', 0),
                        'entry_price': trade.get('entry_price', 0),
                        'exit_price': trade.get('exit_price', 0),
                        'sl': trade.get('sl', 0),
                        'tp': trade.get('tp', 0),
                        'pnl': trade.get('pnl', 0),
                        'commission': trade.get('commission', 0),
                        'swap': trade.get('swap', 0),
                        'duration_minutes': trade.get('duration_minutes', 0),
                        'close_reason': trade.get('close_reason', ''),
                        'strategy': trade.get('strategy', 'AI'),
                        'confidence': trade.get('confidence', 0)
                    }
                    writer.writerow(row)
            
            logger.debug(f"[CSV] Exported {len(trades)} trades to trades_history.csv")
            
        except Exception as e:
            logger.error(f"[CSV] Failed to export to CSV: {e}")
    
    def save_stats(self):
        """Сохранение статистики с атомарной записью."""
        stats_file = get_data_path('bot_stats.json')
        stats_file.parent.mkdir(exist_ok=True)
        
        # Добавляем дополнительные поля для Telegram бота
        stats_to_save = self.stats.copy()
        stats_to_save['mode'] = self.trading_mode
        stats_to_save['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stats_to_save['is_running'] = self.status == BotStatus.RUNNING
        
        # Атомарное сохранение
        temp_file = stats_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(stats_to_save, f, indent=2, ensure_ascii=False)
            temp_file.replace(stats_file)
        except Exception as e:
            logger.error(f"[SAVE STATS] Ошибка атомарного сохранения: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def load_stats(self):
        """Загрузка статистики."""
        stats_file = get_data_path('bot_stats.json')
        
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                saved_stats = json.load(f)
                # Обновим базовые значения из сохранённого файла
                self.stats.update(saved_stats)

        # Попробуем загрузить историю сделок и пересчитать агрегаты (если файл есть)
        
        trades_file = get_data_path('trades_history.json')
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)

            # Пересчитываем ONLY: trades count, wins/losses, today_pnl
            # total_pnl = берем из MT5 balance - starting_balance!
            total_trades = len(trades)
            wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
            losses = sum(1 for t in trades if t.get('pnl', 0) <= 0)

            today = datetime.now().strftime('%Y-%m-%d')
            today_pnl = sum(t.get('pnl', 0) for t in trades if t.get('date') == today)

            # Обновляем статистику (НЕ total_pnl - он рассчитывается из balance!)
            self.stats['today_pnl'] = round(float(today_pnl), 2)
            # Сохраняем обе вариации ключей для совместимости с GUI и API
            self.stats['total_trades'] = total_trades
            self.stats['trades'] = total_trades
            self.stats['wins'] = wins
            self.stats['losses'] = losses
            self.stats['winning_trades'] = wins
            self.stats['losing_trades'] = losses
            
            # Проверяем наличие starting_balance
            if 'starting_balance' not in self.stats:
                # Вычисляем starting_balance как: текущий баланс - сумма PnL всех сделок
                total_pnl_from_trades = sum(t.get('pnl', 0) for t in trades)
                current_balance = self.stats.get('balance', 0)
                self.stats['starting_balance'] = round(current_balance - total_pnl_from_trades, 2)
                logger.info(f"[Stats] Calculated starting_balance: ${self.stats['starting_balance']:.2f} (balance={current_balance:.2f} - trades_pnl={total_pnl_from_trades:.2f})")
            
            # Сохраняем обновленную статистику в файл
            self.save_stats()
            
            # total_pnl будет вычислен из MT5 в _update_stats_from_mt5()
            logger.info(f"[STATS] Loaded: Today PnL=${today_pnl:.2f}, Trades={total_trades} (Total PnL will be calculated from MT5 balance)")
        else:
            # Нет файла с историей - это первый запуск
            # starting_balance = текущий баланс
            if 'starting_balance' not in self.stats:
                current_balance = self.stats.get('balance', 10000.0)
                self.stats['starting_balance'] = current_balance
                logger.info(f"[Stats] First run - setting starting_balance to current balance: ${current_balance:.2f}")
        
        # Синхронизация с MT5: проверяем новые закрытые сделки
        self._sync_with_mt5()
    
    def _sync_with_mt5(self):
        """Синхронизация с MT5: загружаем сделки которых нет в trades_history.json"""
        if not self.mt5_manager or not self.mt5_manager.is_connected():
            logger.debug("[SYNC] MT5 not connected, skipping sync")
            return
        
        try:
            # Получаем историю сделок за последние 7 дней
            from datetime import datetime, timedelta
            
            trade_history = self.mt5_manager.get_trade_history(days=7)
            if not trade_history:
                logger.debug("[SYNC] No trade history from MT5")
                return
            
            # Загружаем существующие ID сделок
            trades_file = get_data_path('trades_history.json')
            existing_trades = []
            existing_ids = set()
            
            if trades_file.exists():
                with open(trades_file, 'r', encoding='utf-8') as f:
                    existing_trades = json.load(f)
                    existing_ids = {int(t.get('id', 0)) for t in existing_trades if t.get('id')}
            
            # Находим новые сделки
            new_trades = []
            for trade in trade_history:
                trade_id = int(trade.get('id', 0))
                if trade_id and trade_id not in existing_ids:
                    new_trades.append(trade)
            
            if new_trades:
                logger.info(f"[SYNC] Found {len(new_trades)} new trades from MT5")
                
                # Добавляем новые сделки
                for trade in new_trades:
                    self.add_trade(trade)
                
                logger.info(f"[SYNC] ✅ Synced {len(new_trades)} trades from MT5")
            else:
                logger.debug("[SYNC] No new trades to sync")
                
        except Exception as e:
            logger.error(f"[SYNC] Failed to sync with MT5: {e}")
    
    def get_stats(self) -> dict:
        """Получение текущей статистики."""
        # Рассчитываем win rate
        total_trades = self.stats.get('total_trades', 0)
        winning_trades = self.stats.get('wins', 0)
        losing_trades = self.stats.get('losses', 0)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': self.stats.get('total_pnl', 0.0),
            'today_pnl': self.stats.get('today_pnl', 0.0),
            'open_positions': self.stats.get('open_positions', [])
        }
    
    def get_status_info(self) -> dict:
        """Информация о статусе для API."""
        return {
            'status': self.status.value,
            'mode': self.mode,
            'stats': self.stats,
            'logs': self.logs[-20:],  # Последние 20 логов
            'open_positions': self.stats.get('open_positions', [])
        }


# Глобальный инстанс
bot_manager = BotManager()
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
from pathlib import Path
import sys
from src.core.logger import logger

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


class BotStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


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
        self.trading_mode = 'pure_ai'  # Pure AI режим (фиксированный)
        self.bot_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # MT5 Manager (устанавливается извне)
        self.mt5_manager = None
        
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
        
        # Загружаем историю
        self.load_stats()
    
    def set_mt5_manager(self, mt5_manager):
        """Установка MT5 Manager для получения реальной статистики."""
        self.mt5_manager = mt5_manager
        logger.info("MT5 Manager connected to BotManager")
        
        # Синхронизация с MT5 после подключения
        self._sync_with_mt5()
    
    def _update_stats_from_mt5(self):
        """Обновление статистики из MT5."""
        if self.mt5_manager and self.mt5_manager.is_connected():
            try:
                account_info = self.mt5_manager.get_account_info()
                if account_info:
                    self.stats['balance'] = account_info.get('balance', self.stats['balance'])
                    self.stats['equity'] = account_info.get('equity', account_info.get('balance', 0))
                    logger.info(f"Stats updated from MT5: balance=${self.stats['balance']:.2f}")
                    return True
            except Exception as e:
                logger.error(f"Failed to update stats from MT5: {e}")
        return False
    
    def _init_monitoring(self):
        """Инициализация системы мониторинга."""
        try:
            import yaml
            config_path = Path('config/telegram.yaml')
            
            if not config_path.exists():
                logger.info("Telegram config not found, notifications disabled")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            tg_config = config.get('telegram', {})
            if tg_config.get('enabled', False):
                bot_token = tg_config.get('bot_token')
                chat_id = tg_config.get('chat_id')
                logger.info(f"[BotManager] Initializing Telegram: token={'***' + bot_token[-4:] if bot_token else 'NONE'}, chat_id={chat_id}")
                
                self.telegram = TelegramNotifier(
                    token=bot_token,
                    chat_id=chat_id
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
                        self.signal_manager = AISignalManager(telegram_notifier=self.telegram)
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
    
    def start(self, mode: str = 'demo', trading_mode: str = 'strategy'):
        """
        Запуск бота.
        
        Args:
            mode: Режим счета ('demo' или 'live')
            trading_mode: Режим торговли ('strategy' или 'pure_ai')
        """
        if self.status == BotStatus.RUNNING:
            self.log("Warning: Bot already running")
            return False
        
        self.stop_event.clear()
        self.pause_event.clear()
        self.trading_mode = trading_mode  # Сохраняем режим торговли
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
        
        if self.bot_thread:
            self.bot_thread.join(timeout=5)
        
        # Останавливаем cleanup service
        if self.cleanup_service:
            self.cleanup_service.stop()
            logger.info("🧹 Cleanup service stopped")
        
        self.log("Bot stopped")
        
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
            
            # Определяем режим торговли
            enable_trading = (mode == 'live')
            
            # Инициализация LiveTrader
            # LiveTrader сам загружает конфиги, подключается к MT5, 
            # инициализирует стратегии и создает executor
            self.live_trader = LiveTrader(
                config_dir='config',
                enable_trading=enable_trading,
                enable_gpt=True  # GPT фильтр включен
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
        self.stats['total_pnl'] += pnl
        self.stats['balance'] += pnl
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
        """Сохранение сделки в файл."""
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

        trades.append(trade)

        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
    
    def save_stats(self):
        """Сохранение статистики."""
        stats_file = get_data_path('bot_stats.json')
        stats_file.parent.mkdir(exist_ok=True)
        
        # Добавляем дополнительные поля для Telegram бота
        stats_to_save = self.stats.copy()
        stats_to_save['mode'] = self.trading_mode
        stats_to_save['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stats_to_save['is_running'] = self.status == BotStatus.RUNNING
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_to_save, f, indent=2)
    
    def load_stats(self):
        """Загрузка статистики."""
        stats_file = get_data_path('bot_stats.json')
        
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                saved_stats = json.load(f)
                # Обновим базовые значения из сохранённого файла
                self.stats.update(saved_stats)
                
                # Проверяем наличие starting_balance
                if 'starting_balance' not in self.stats:
                    # Если нет starting_balance, вычисляем его
                    current_balance = self.stats.get('balance', 0)
                    total_pnl = self.stats.get('total_pnl', 0)
                    self.stats['starting_balance'] = current_balance - total_pnl
                    logger.info(f"[Stats] Calculated starting_balance: ${self.stats['starting_balance']:.2f}")

        # Попробуем загрузить историю сделок и пересчитать агрегаты (если файл есть)
        
        trades_file = get_data_path('trades_history.json')
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)

            # Пересчитываем суммарный PnL, число сделок, wins/losses и PnL за сегодня
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            total_trades = len(trades)
            wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
            losses = sum(1 for t in trades if t.get('pnl', 0) <= 0)

            today = datetime.now().strftime('%Y-%m-%d')
            today_pnl = sum(t.get('pnl', 0) for t in trades if t.get('date') == today)

            # Обновляем статистику
            self.stats['total_pnl'] = round(float(total_pnl), 2)
            self.stats['today_pnl'] = round(float(today_pnl), 2)
            # Сохраняем обе вариации ключей для совместимости с GUI и API
            self.stats['total_trades'] = total_trades
            self.stats['trades'] = total_trades
            self.stats['wins'] = wins
            self.stats['losses'] = losses
            self.stats['winning_trades'] = wins
            self.stats['losing_trades'] = losses
            
            # Сохраняем обновленную статистику в файл
            self.save_stats()
            logger.info(f"[STATS] Loaded: Total PnL=${total_pnl:.2f}, Today PnL=${today_pnl:.2f}, Trades={total_trades}")
        
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
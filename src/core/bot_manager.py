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
from src.core.logger import logger

# Мониторинг
try:
    from src.monitoring import TelegramNotifier, AlertManager
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring modules not available")


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
        self.mode = 'demo'  # Режим работы: demo, backtest, live
        self.bot_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # MT5 Manager (устанавливается извне)
        self.mt5_manager = None
        
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
            'open_positions': []
        }
        
        # Callback для обновления UI
        self.on_update: Optional[Callable] = None
        
        # Система мониторинга
        self.telegram = None
        self.alert_manager = None
        if MONITORING_AVAILABLE:
            self._init_monitoring()
        
        # Загружаем историю
        self.load_stats()
    
    def set_mt5_manager(self, mt5_manager):
        """Установка MT5 Manager для получения реальной статистики."""
        self.mt5_manager = mt5_manager
        logger.info("MT5 Manager connected to BotManager")
    
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
                self.telegram = TelegramNotifier(
                    token=tg_config.get('bot_token'),
                    chat_id=tg_config.get('chat_id')
                )
                self.notify_config = tg_config.get('notify', {})
                logger.info("Telegram notifications enabled")
                
                # Инициализация AlertManager
                self.alert_manager = AlertManager()
                
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
    
    def start(self, mode: str = 'demo'):
        """Запуск бота."""
        if self.status == BotStatus.RUNNING:
            self.log("Warning: Bot already running")
            return False
        
        self.stop_event.clear()
        self.pause_event.clear()
        self.status = BotStatus.RUNNING
        
        # Запускаем в отдельном потоке
        self.bot_thread = threading.Thread(
            target=self._run_bot,
            args=(mode,),
            daemon=True
        )
        self.bot_thread.start()
        
        self.log(f"Bot started in {mode.upper()} mode")
        
        # Обновляем статистику из MT5 перед отправкой уведомления
        self._update_stats_from_mt5()
        
        # Telegram уведомление
        if self.telegram and self.notify_config.get('startup', True):
            instruments = list(self.stats.get('instruments', ['XAUUSD', 'EURUSD']))
            self.telegram.send_startup(mode=mode.upper(), instruments=instruments)
        
        return True
    
    def stop(self):
        """Остановка бота."""
        if self.status == BotStatus.STOPPED:
            self.log("Warning: Bot already stopped")
            return False
        
        self.stop_event.set()
        self.status = BotStatus.STOPPED
        
        if self.bot_thread:
            self.bot_thread.join(timeout=5)
        
        self.log("Bot stopped")
        
        # Обновляем статистику из MT5 перед отправкой уведомления
        self._update_stats_from_mt5()
        
        # Telegram уведомление
        if self.telegram and self.notify_config.get('shutdown', True):
            self.telegram.send_shutdown(stats=self.stats)
        
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
        """Основной цикл бота."""
        try:
            # Импортируем необходимые компоненты
            from src.live.live_trader import LiveTrader
            
            # Определяем режим торговли
            enable_trading = (mode == 'live')
            
            # Инициализация LiveTrader
            # LiveTrader сам загружает конфиги, подключается к MT5, 
            # инициализирует стратегии и создает executor
            trader = LiveTrader(
                config_dir='config',
                enable_trading=enable_trading,
                enable_gpt=True  # GPT фильтр включен
            )
            
            self.log(f"LiveTrader initialized (trading={'ON' if enable_trading else 'OFF'})")
            
            while not self.stop_event.is_set():
                # Проверяем паузу
                if self.pause_event.is_set():
                    self.stop_event.wait(1)
                    continue
                
                # Один цикл проверки сигналов
                try:
                    signals = trader.check_signals()
                    if signals:
                        for signal_msg in signals:
                            self.log(f"Signal: {signal_msg}")
                except Exception as e:
                    self.log(f"Error checking signals: {e}")
                
                # Ждём перед следующей проверкой
                self.stop_event.wait(60)  # 60 секунд
                
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
        today = datetime.now().strftime('%Y-%m-%d')
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
        trades_file = Path('data/trades_history.json')
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
        stats_file = Path('data/bot_stats.json')
        stats_file.parent.mkdir(exist_ok=True)
        
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def load_stats(self):
        """Загрузка статистики."""
        stats_file = Path('data/bot_stats.json')
        
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                saved_stats = json.load(f)
                # Обновим базовые значения из сохранённого файла
                self.stats.update(saved_stats)

        # Попробуем загрузить историю сделок и пересчитать агрегаты (если файл есть)
        
        trades_file = Path('data/trades_history.json')
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
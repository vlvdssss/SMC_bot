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
        
        # Логи для веб-интерфейса
        self.logs: list = []
        self.max_logs = 100
        
        # Статистика
        self.stats = {
            'balance': 100.0,
            'total_pnl': 0.0,
            'today_pnl': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'open_positions': []
        }
        
        # Callback для обновления UI
        self.on_update: Optional[Callable] = None
        
        # Загружаем историю
        self.load_stats()
    
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
            from src.mt5.connector import MT5Connector
            from src.strategies.xauusd_strategy import StrategyXAUUSD
            from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement
            from src.core.broker_sim import BrokerSim
            import yaml
            
            enable_trading = (mode == 'live')
            
            # Загрузка конфига MT5
            try:
                with open('config/mt5.yaml', 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                mt5_config = config['mt5']
            except Exception as e:
                self.log(f"Error loading MT5 config: {e}")
                self.status = BotStatus.STOPPED
                return
            
            # Инициализация стратегий
            strategies = {
                'XAUUSD': StrategyXAUUSD(),
                'EURUSD': StrategyEURUSD_SMC_Retracement()
            }
            
            # Инициализация компонентов
            mt5_connector = MT5Connector(mt5_config)
            executor = BrokerSim()  # Пока используем симулятор
            
            # Инициализация LiveTrader с правильными аргументами
            trader = LiveTrader(strategies, executor, mt5_connector)
            
            while not self.stop_event.is_set():
                # Проверяем паузу
                if self.pause_event.is_set():
                    self.stop_event.wait(1)
                    continue
                
                # Один цикл проверки
                trader.check_signals()
                
                # Ждём перед следующей проверкой
                self.stop_event.wait(60)  # 60 секунд
                
        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.status = BotStatus.STOPPED
    
    def log(self, message: str):
        """Добавление лога."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            'time': timestamp,
            'message': message
        }
        
        self.logs.append(log_entry)
        
        # Ограничиваем количество логов
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        # Выводим в консоль тоже
        print(f"[{timestamp}] {message}")
    
    def add_trade(self, trade: dict):
        """Добавление сделки."""
        # Обновляем статистику
        pnl = trade.get('pnl', 0)
        self.stats['total_pnl'] += pnl
        self.stats['balance'] += pnl
        self.stats['total_trades'] += 1
        
        if pnl > 0:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        
        # Проверяем сегодняшняя ли сделка
        today = datetime.now().strftime('%Y-%m-%d')
        if trade.get('date') == today:
            self.stats['today_pnl'] += pnl
        
        # Сохраняем в файл
        self.save_trade(trade)
        self.save_stats()
    
    def save_trade(self, trade: dict):
        """Сохранение сделки в файл."""
        trades_file = Path('data/trades_history.json')
        trades_file.parent.mkdir(exist_ok=True)
        
        trades = []
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        
        trades.append(trade)
        
        with open(trades_file, 'w') as f:
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
                self.stats.update(saved_stats)
        
        # Сбрасываем today_pnl если новый день
        trades_file = Path('data/trades_history.json')
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            today_pnl = sum(t['pnl'] for t in trades if t.get('date') == today)
            self.stats['today_pnl'] = today_pnl
    
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
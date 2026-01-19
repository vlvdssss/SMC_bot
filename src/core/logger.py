"""
Centralized Logger v2.0 - двухуровневое логирование.
Консоль - только важные события
Файл - всё подробно
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Set
import yaml


# Категории логов
class LogCategory:
    STARTUP = "STARTUP"
    AI = "AI"
    SIGNAL = "SIGNAL"
    TRADE = "TRADE"
    PROFIT = "PROFIT"
    SCHEDULER = "SCHEDULER"
    ERROR = "ERROR"
    WARNING = "WARNING"
    DEBUG = "DEBUG"


# Спам фильтр - игнорируемые сообщения в консоли
SPAM_FILTERS = [
    "Failed to load data for",
    "Backtest data file not found",
    "Backtest mode requires CSV",
    "For live trading, this error can be ignored"
]


class Logger:
    """Централизованный логгер приложения."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_logger()
            self._initialized = True
            # GUI callback для вывода логов
            self.gui_callback = None
            # Загрузка конфига
            self.config = self._load_config()
            # Счетчик для спам фильтра
            self._spam_count = {}

    def _load_config(self) -> dict:
        """Загрузить конфиг логирования."""
        try:
            config_path = Path("config/logging.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception:
            pass
        # Дефолтные настройки
        return {
            "console": {
                "level": "INFO",
                "show_categories": ["STARTUP", "AI", "SIGNAL", "TRADE", "PROFIT", "ERROR"]
            },
            "file": {
                "level": "DEBUG",
                "max_size_mb": 10,
                "backup_count": 7
            }
        }

    def _is_spam(self, message: str) -> bool:
        """Проверить, является ли сообщение спамом."""
        for spam_pattern in SPAM_FILTERS:
            if spam_pattern in message:
                # Подсчет спама для отчета
                self._spam_count[spam_pattern] = self._spam_count.get(spam_pattern, 0) + 1
                return True
        return False

    def _setup_logger(self):
        """Настройка логгера с двумя хендлерами."""
        # Устанавливаем UTF-8 для stdout
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

        self.logger = logging.getLogger('BAZA')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # === ФАЙЛОВЫЙ ХЕНДЛЕР - ВСЁ ПОДРОБНО (DEBUG) ===
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"baza_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] BAZA: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=7, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # ВСЁ в файл
        file_handler.setFormatter(file_formatter)

        # === КОНСОЛЬНЫЙ ХЕНДЛЕР - ТОЛЬКО ВАЖНОЕ (INFO+) ===
        console_formatter = logging.Formatter(
            '%(asctime)s %(message)s',
            datefmt='%H:%M:%S'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Только INFO+ в консоль
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("✅ Logger v2.0 initialized")

    def set_gui_callback(self, callback: callable):
        """Установить callback для вывода в GUI."""
        self.gui_callback = callback

    def _log_to_gui(self, message: str, level: str = "INFO"):
        """Внутренний метод для вывода в GUI через callback."""
        if self.gui_callback:
            try:
                # Вызов callback для вставки в GUI (timestamp добавляется в GUI)
                self.gui_callback(message, level)
            except Exception as e:
                # Ошибка GUI - логируем только в debug
                self.logger.debug(f"GUI logging error: {e}")
        # НЕ печатаем в консоль - это делает console_handler!

    def debug(self, message: str, *args, **kwargs):
        """Debug сообщение (только в файл)."""
        self.logger.debug(message, *args, **kwargs)
        # НЕ выводим в GUI для debug

    def info(self, message: str, *args, **kwargs):
        """Info сообщение."""
        # Фильтр спама для консоли
        if not self._is_spam(message):
            self.logger.info(message, *args, **kwargs)
            self._log_to_gui(message, "INFO")
        else:
            # Спам идет только в файл
            self.logger.debug(f"[FILTERED] {message}", *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Warning сообщение."""
        # Фильтр спама для консоли
        if not self._is_spam(message):
            self.logger.warning(message, *args, **kwargs)
            self._log_to_gui(message, "WARNING")
        else:
            # Спам идет только в файл
            self.logger.debug(f"[FILTERED] {message}", *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Error сообщение (всегда показывать)."""
        # Фильтр спама даже для ошибок
        if not self._is_spam(message):
            self.logger.error(message, *args, **kwargs)
            self._log_to_gui(message, "ERROR")
        else:
            # Спам идет только в файл
            self.logger.debug(f"[FILTERED ERROR] {message}", *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Critical сообщение (всегда показывать)."""
        self.logger.critical(message, *args, **kwargs)
        self._log_to_gui(message, "CRITICAL")
    
    # === КАТЕГОРИЙНЫЕ МЕТОДЫ ===
    
    def startup(self, message: str):
        """Стартап сообщение."""
        self.info(f"✅ [STARTUP] {message}")
    
    def ai(self, message: str):
        """AI анализ."""
        self.info(f"🔍 [AI] {message}")
    
    def signal(self, message: str):
        """Сигнал."""
        self.info(f"📊 [SIGNAL] {message}")
    
    def trade(self, message: str):
        """Торговая операция."""
        self.info(f"📈 [TRADE] {message}")
    
    def profit(self, message: str, amount: float = None):
        """Результат сделки."""
        if amount is not None:
            sign = "+" if amount >= 0 else ""
            self.info(f"💰 [PROFIT] {message} → {sign}{amount:.2f} USD")
        else:
            self.info(f"💰 [PROFIT] {message}")
    
    def scheduler(self, message: str):
        """Расписание."""
        self.info(f"⏰ [SCHEDULER] {message}")
    
    def get_spam_stats(self) -> dict:
        """Получить статистику отфильтрованного спама."""
        return self._spam_count.copy()

    def log_to_gui(self, message: str, level: str = "INFO"):
        """Устаревший метод для совместимости."""
        self._log_to_gui(message, level)
        return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"


# Глобальный экземпляр логгера
logger = Logger()
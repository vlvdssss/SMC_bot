"""
Centralized Logger - централизованная система логирования.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


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

    def _setup_logger(self):
        """Настройка логгера с UTF-8."""
        # Устанавливаем UTF-8 для stdout
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Для старых версий Python
            pass

        self.logger = logging.getLogger('BAZA')
        self.logger.setLevel(logging.DEBUG)

        # Убираем существующие хендлеры
        self.logger.handlers.clear()

        # Форматтер без эмодзи
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] BAZA: %(message)s',
            datefmt='%H:%M:%S'
        )

        # Файловый хендлер с UTF-8
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"baza_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Консольный хендлер с UTF-8 (добавляем обратно для видимости)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Добавляем оба хендлера
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("Logger initialized")

    def set_gui_callback(self, callback: callable):
        """Установить callback для вывода в GUI."""
        self.gui_callback = callback

    def _log_to_gui(self, message: str, level: str = "INFO"):
        """Внутренний метод для вывода в GUI через callback."""
        if self.gui_callback:
            try:
                # Форматирование сообщения с timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted = f"[{timestamp}] {message}"
                
                # Вызов callback для вставки в GUI
                self.gui_callback(formatted, level)
            except Exception as e:
                # Fallback в консоль при ошибке GUI
                print(f"GUI logging error: {e}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        else:
            # Если callback не установлен, выводим в консоль
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def debug(self, message: str, *args, **kwargs):
        """Debug сообщение."""
        self.logger.debug(message, *args, **kwargs)
        self._log_to_gui(message, "DEBUG")

    def info(self, message: str, *args, **kwargs):
        """Info сообщение."""
        self.logger.info(message, *args, **kwargs)
        self._log_to_gui(message, "INFO")

    def warning(self, message: str, *args, **kwargs):
        """Warning сообщение."""
        self.logger.warning(message, *args, **kwargs)
        self._log_to_gui(message, "WARNING")

    def error(self, message: str, *args, **kwargs):
        """Error сообщение."""
        self.logger.error(message, *args, **kwargs)
        self._log_to_gui(message, "ERROR")

    def critical(self, message: str, *args, **kwargs):
        """Critical сообщение."""
        self.logger.critical(message, *args, **kwargs)
        self._log_to_gui(message, "CRITICAL")

    def log_to_gui(self, message: str, level: str = "INFO"):
        """Устаревший метод для совместимости."""
        self._log_to_gui(message, level)
        return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"


# Глобальный экземпляр логгера
logger = Logger()
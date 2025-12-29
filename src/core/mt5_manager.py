"""
MT5 Manager - централизованное управление MT5 подключением.
"""

import logging
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MT5Manager:
    """Менеджер MT5 подключения."""

    def __init__(self):
        self.mt5 = None
        self.connected = False
        self.account_info = {}
        self.last_connect_attempt = 0
        self.connect_cooldown = 5  # секунды

        # Импортируем MT5
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            logger.info("MT5 library imported successfully")
        except ImportError:
            logger.error("MetaTrader5 library not found")
            raise ImportError("MetaTrader5 library is required")

    def initialize(self, terminal_path: str = None) -> bool:
        """Инициализация MT5."""
        try:
            if terminal_path and Path(terminal_path).exists():
                if not self.mt5.initialize(terminal_path):
                    logger.error(f"Failed to initialize MT5 with path: {terminal_path}")
                    return False
            else:
                if not self.mt5.initialize():
                    logger.error("Failed to initialize MT5")
                    return False

            logger.info("MT5 initialized successfully")
            return True

        except Exception as e:
            logger.error(f"MT5 initialization error: {e}")
            return False

    def connect(self, login: int, password: str, server: str) -> Tuple[bool, str]:
        """Подключение к торговому счету."""
        current_time = time.time()

        # Проверка cooldown
        if current_time - self.last_connect_attempt < self.connect_cooldown:
            return False, "Подождите перед следующей попыткой подключения"

        self.last_connect_attempt = current_time

        try:
            # Проверяем инициализацию
            if not self.mt5:
                return False, "MT5 не инициализирован"

            # Подключаемся
            authorized = self.mt5.login(login, password, server)

            if authorized:
                self.connected = True

                # Получаем информацию о счете
                account = self.mt5.account_info()
                if account:
                    self.account_info = {
                        'login': account.login,
                        'balance': account.balance,
                        'equity': account.equity,
                        'margin': account.margin,
                        'margin_free': account.margin_free,
                        'server': server
                    }
                    logger.info(f"MT5 connected: {account.login}@{server}")
                    return True, f"Подключено: {account.login}"
                else:
                    return False, "Не удалось получить информацию о счете"
            else:
                error = self.mt5.last_error()
                error_msg = f"Ошибка авторизации: {error}" if error else "Ошибка авторизации"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False, f"Ошибка подключения: {str(e)}"

    def disconnect(self) -> bool:
        """Отключение от MT5."""
        try:
            if self.mt5:
                self.mt5.shutdown()
                self.connected = False
                self.account_info = {}
                logger.info("MT5 disconnected")
                return True
        except Exception as e:
            logger.error(f"MT5 disconnect error: {e}")

        return False

    def is_connected(self) -> bool:
        """Проверка подключения."""
        if not self.mt5 or not self.connected:
            return False

        try:
            # Проверяем соединение через ping
            terminal_info = self.mt5.terminal_info()
            return terminal_info is not None
        except:
            self.connected = False
            return False

    def get_account_info(self) -> dict:
        """Получение информации о счете."""
        if self.is_connected():
            try:
                account = self.mt5.account_info()
                if account:
                    return {
                        'login': account.login,
                        'balance': account.balance,
                        'equity': account.equity,
                        'margin': account.margin,
                        'margin_free': account.margin_free,
                        'server': self.account_info.get('server', '')
                    }
            except Exception as e:
                logger.error(f"Error getting account info: {e}")

        return {}

    def get_terminal_info(self) -> dict:
        """Получение информации о терминале."""
        if self.is_connected():
            try:
                terminal = self.mt5.terminal_info()
                if terminal:
                    return {
                        'name': terminal.name,
                        'company': terminal.company,
                        'path': terminal.path
                    }
            except Exception as e:
                logger.error(f"Error getting terminal info: {e}")

        return {}

    def get_connection_status(self) -> Dict[str, Any]:
        """Получение полного статуса подключения."""
        if not self.is_connected():
            return {
                'connected': False,
                'message': 'Не подключено',
                'account': None,
                'terminal': None
            }

        account_info = self.get_account_info()
        terminal_info = self.get_terminal_info()

        return {
            'connected': True,
            'message': f"Подключено: {account_info.get('login', 'N/A')}",
            'account': account_info,
            'terminal': terminal_info
        }

    def __del__(self):
        """Деструктор - корректное отключение."""
        self.disconnect()
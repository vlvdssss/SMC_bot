"""
App State - централизованное состояние приложения.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AppState:
    """Централизованное состояние приложения."""

    def __init__(self):
        # MT5 Manager
        self.mt5_manager = None

        # Статус MT5
        self.mt5_connected = False
        self.mt5_account_info = {}

        # Executor
        self.executor = None

        # Bot state
        self.bot_running = False
        self.bot_paused = False

        # Manual trading
        self.manual_trading_enabled = False
        self.manual_trade_state = None  # ManualTradeState
        self.market_data_updater = None  # MarketDataUpdater

        # Statistics
        self.stats = {
            'balance': 100.0,
            'total_pnl': 0.0,
            'today_pnl': 0.0,
            'trades': 0,
            'wins': 0,
            'losses': 0
        }

        # Settings
        self.settings = {
            'enable_gpt': True,
            'mt5': {
                'login': '',
                'password': '',
                'server': '',
                'terminal_path': ''
            }
        }

        logger.info("AppState initialized")

    def update_mt5_status(self, connected: bool, account_info: Optional[Dict[str, Any]] = None) -> None:
        """Обновление статуса MT5."""
        self.mt5_connected = connected
        
        # Безопасная обработка account_info с различными типами входных данных
        if account_info is None:
            self.mt5_account_info = {}
        elif isinstance(account_info, dict):
            self.mt5_account_info = account_info.copy()  # Создаём копию для безопасности
            # Безопасно получаем и обновляем баланс
            try:
                balance = account_info.get('balance')
                if balance is not None:
                    self.stats['balance'] = float(balance)
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid balance value in account_info: {e}")
        elif isinstance(account_info, (int, str)):
            # Если пришёл простой идентификатор (login), создаём словарь
            try:
                self.mt5_account_info = {'login': int(account_info)}
            except (TypeError, ValueError) as e:
                logger.warning(f"Cannot convert account_info to login: {e}")
                self.mt5_account_info = {'info': str(account_info)}
        else:
            logger.error(f"Invalid account_info type: {type(account_info)}")
            self.mt5_account_info = {}

        logger.info(f"MT5 status updated: connected={connected}, account={self.mt5_account_info.get('login', 'N/A')}")

    def is_mt5_ready(self) -> bool:
        """Проверка готовности MT5."""
        return self.mt5_connected and self.mt5_manager is not None

    def can_execute_trades(self) -> bool:
        """Проверка возможности выполнения сделок."""
        return self.is_mt5_ready() and not self.bot_running

    def get_mt5_config(self) -> dict:
        """Получение конфига MT5."""
        return self.settings.get('mt5', {})

    def set_mt5_config(self, config: dict):
        """Установка конфига MT5."""
        self.settings['mt5'] = config
        logger.info("MT5 config updated")
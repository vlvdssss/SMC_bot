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

    def update_mt5_status(self, connected: bool, account_info: dict = None):
        """Обновление статуса MT5."""
        self.mt5_connected = connected
        # account_info может быть dict с деталями или иногда простым login (int)
        if account_info:
            if isinstance(account_info, dict):
                self.mt5_account_info = account_info
                # безопасно получить баланс
                try:
                    self.stats['balance'] = float(account_info.get('balance', self.stats.get('balance', 100.0)))
                except Exception:
                    # если balance некорректен — не перезаписываем
                    pass
            else:
                # если пришёл простой идентификатор (login), положим его в account_info как словарь
                try:
                    self.mt5_account_info = {'login': int(account_info)}
                except Exception:
                    self.mt5_account_info = {'info': str(account_info)}
        else:
            self.mt5_account_info = {}

        logger.info(f"MT5 status updated: connected={connected}")

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
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

    def get_trade_history(self, days: int = 30) -> list:
        """Получение истории сделок из терминала за последние `days` дней.

        Возвращает список словарей с полями: id, date, time, instrument, direction, pnl, volume, price
        """
        result = []
        try:
            if not self.is_connected():
                return result

            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            deals = self.mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return result

            for deal in deals:
                # Учтём только торговые сделки (buy/sell)
                if deal.type in [self.mt5.DEAL_TYPE_BUY, self.mt5.DEAL_TYPE_SELL]:
                    pnl = float(deal.profit) if deal.profit is not None else 0.0

                    # deal.time can be datetime or int timestamp depending on MT5 bindings
                    try:
                        t = deal.time
                        if isinstance(t, int) or isinstance(t, float):
                            from datetime import datetime
                            dt = datetime.fromtimestamp(int(t))
                        else:
                            dt = t
                    except Exception:
                        from datetime import datetime
                        dt = datetime.now()

                    result.append({
                        'id': int(deal.ticket),
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M'),
                        'instrument': deal.symbol,
                        'direction': 'BUY' if deal.type == self.mt5.DEAL_TYPE_BUY else 'SELL',
                        'pnl': round(pnl, 2),
                        'volume': float(deal.volume),
                        'price': float(deal.price)
                    })

        except Exception as e:
            logger.error(f"Error getting trade history from MT5: {e}")

        return result

    def start_trade_sync(self, poll_interval: float = 5.0, lookback_days: int = 365):
        """Start background thread to poll MT5 for new deals and push them to bot_manager.

        This will read existing `data/trades_history.json` to determine the last seen ticket
        and then periodically call `get_trade_history` and add new trades via `bot_manager.add_trade()`.
        """
        # If already started, skip
        if hasattr(self, '_trade_sync_thread') and self._trade_sync_thread is not None:
            return

        def sync_loop():
            try:
                from time import sleep
                from src.core.bot_manager import bot_manager

                # Determine last seen ticket from local file
                last_ticket = 0
                try:
                    import json
                    from pathlib import Path
                    tf = Path('data/trades_history.json')
                    if tf.exists():
                        with open(tf, 'r', encoding='utf-8') as f:
                            trades = json.load(f)
                        tickets = [int(t.get('id')) for t in trades if t.get('id') is not None]
                        if tickets:
                            last_ticket = max(tickets)
                except Exception:
                    last_ticket = 0

                while True:
                    try:
                        if not self.is_connected():
                            sleep(1.0)
                            continue

                        trades = self.get_trade_history(days=lookback_days)
                        # Sort by id ascending
                        trades_sorted = sorted(trades, key=lambda x: int(x.get('id') or 0))
                        for t in trades_sorted:
                            try:
                                tid = int(t.get('id') or 0)
                            except Exception:
                                tid = 0
                            if tid > last_ticket:
                                try:
                                    bot_manager.add_trade(t)
                                except Exception:
                                    pass
                                last_ticket = max(last_ticket, tid)

                    except Exception:
                        pass

                    sleep(poll_interval)

            except Exception:
                return

        import threading
        self._trade_sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._trade_sync_thread.start()

    def __del__(self):
        """Деструктор - корректное отключение."""
        self.disconnect()
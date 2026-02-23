"""
MT5 Manager - централизованное управление MT5 подключением.
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

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

class MT5Manager:
    """Менеджер MT5 подключения (Singleton)."""
    
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Инициализация только один раз
        if self._initialized:
            return
            
        self.mt5 = None
        self.connected = False
        self.account_info = {}
        self.last_connect_attempt = 0
        self.connect_cooldown = 5  # секунды
        
        # Thread-safety lock для reconnect и торговых операций
        self.lock = threading.Lock()

        # Импортируем MT5 (опционально)
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            logger.info("MT5 library imported successfully")
        except ImportError:
            logger.warning("MetaTrader5 library not found - MT5 features will be unavailable")
            # Не падаем, просто работаем без MT5
        
        self._initialized = True

    def initialize(self, terminal_path: str = None) -> bool:
        """Инициализация MT5 с понятными сообщениями об ошибках."""
        try:
            if not self.mt5:
                logger.warning("MT5 library not available")
                return False
            
            if terminal_path and Path(terminal_path).exists():
                if not self.mt5.initialize(terminal_path):
                    error = self.mt5.last_error()
                    error_code = error[0] if error else None
                    
                    if error_code == -10004:
                        logger.error("MT5 terminal not running (No IPC connection)")
                    else:
                        logger.error(f"Failed to initialize MT5 with path: {terminal_path}, error: {error}")
                    return False
            else:
                if not self.mt5.initialize():
                    error = self.mt5.last_error()
                    error_code = error[0] if error else None
                    
                    if error_code == -10004:
                        logger.error("MT5 terminal not running (No IPC connection)")
                    else:
                        logger.error(f"Failed to initialize MT5, error: {error}")
                    return False

            logger.info("MT5 initialized successfully")
            return True

        except Exception as e:
            logger.error(f"MT5 initialization error: {e}")
            return False

    def connect(self, login: int, password: str, server: str, terminal_path: str = None) -> Tuple[bool, str]:
        """Подключение к торговому счету с автоинициализацией."""
        current_time = time.time()

        # Проверка cooldown
        if current_time - self.last_connect_attempt < self.connect_cooldown:
            return False, "⏱️ Подождите перед следующей попыткой подключения"

        self.last_connect_attempt = current_time

        try:
            # Проверяем инициализацию
            if not self.mt5:
                return False, "❌ MT5 библиотека не загружена (установите: pip install MetaTrader5)"
            
            # Автоматическая инициализация если еще не инициализирован
            if not self.initialize(terminal_path):
                error = self.mt5.last_error()
                error_code = error[0] if error else None
                
                # Специальная обработка ошибки "No IPC connection"
                if error_code == -10004:
                    return False, (
                        "🔌 MT5 терминал не запущен!\n\n"
                        "Решение:\n"
                        "1. Запустите MetaTrader 5 терминал вручную\n"
                        "2. Дождитесь полной загрузки терминала\n"
                        "3. Попробуйте подключиться снова"
                    )
                elif error_code == -10005:
                    return False, "❌ MT5 терминал работает под другим пользователем"
                else:
                    return False, f"❌ Не удалось инициализировать MT5: {error}"

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

    def test_connection(self, login: int, password: str, server: str, terminal_path: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Тест подключения к MT5 без изменения текущего соединения.
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, account_info_dict)
        """
        test_mt5 = None
        try:
            # Импортируем MT5 для теста
            import MetaTrader5 as test_mt5_module
            test_mt5 = test_mt5_module
            
            # Validate inputs
            if not login or not password or not server:
                return False, "Login, Password и Server обязательны", None
            
            # Initialize
            if terminal_path and Path(terminal_path).exists():
                if not test_mt5.initialize(terminal_path):
                    error = test_mt5.last_error()
                    error_code = error[0] if error else None
                    
                    # Специальная обработка "No IPC connection"
                    if error_code == -10004:
                        return False, (
                            "🔌 MT5 терминал не запущен!\n\n"
                            "Решение:\n"
                            "1. Запустите MetaTrader 5 терминал вручную\n"
                            "2. Дождитесь полной загрузки терминала\n"
                            "3. Попробуйте Test Connection снова"
                        ), None
                    
                    return False, f"Не удалось инициализировать MT5: {error}", None
            else:
                if not test_mt5.initialize():
                    error = test_mt5.last_error()
                    error_code = error[0] if error else None
                    
                    # Специальная обработка "No IPC connection"
                    if error_code == -10004:
                        return False, (
                            "🔌 MT5 терминал не запущен!\n\n"
                            "Решение:\n"
                            "1. Запустите MetaTrader 5 терминал вручную\n"
                            "2. Дождитесь полной загрузки терминала\n"
                            "3. Попробуйте Test Connection снова"
                        ), None
                    
                    return False, f"Не удалось инициализировать MT5: {error}", None
            
            # Try login
            login_int = int(login) if isinstance(login, str) else login
            authorized = test_mt5.login(login_int, password=password, server=server)
            
            if not authorized:
                error = test_mt5.last_error()
                test_mt5.shutdown()
                return False, f"Ошибка авторизации: {error}", None
            
            # Get account info
            account = test_mt5.account_info()
            if not account:
                test_mt5.shutdown()
                return False, "Не удалось получить информацию о счёте", None
            
            account_dict = {
                'login': account.login,
                'name': account.name,
                'server': account.server,
                'balance': account.balance,
                'currency': account.currency,
                'equity': account.equity,
                'margin': account.margin,
                'margin_free': account.margin_free
            }
            
            # Shutdown test connection
            test_mt5.shutdown()
            
            message = f"✅ Подключение успешно!\n\nAccount: {account.login}\nName: {account.name}\nServer: {account.server}\nBalance: ${account.balance:.2f}\nCurrency: {account.currency}"
            logger.info(f"[MT5] Test connection successful: {account.login}@{server}")
            
            return True, message, account_dict
            
        except Exception as e:
            if test_mt5:
                try:
                    test_mt5.shutdown()
                except:
                    pass
            logger.error(f"[MT5] Test connection failed: {e}")
            return False, f"Ошибка тестирования: {str(e)}", None

    def apply_settings(self, login: int, password: str, server: str, terminal_path: str = None) -> Tuple[bool, str]:
        """
        Применить новые настройки MT5 с reconnect без перезапуска бота.
        
        Thread-safe: использует self.lock для предотвращения конфликтов с торговыми операциями.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        with self.lock:
            try:
                # Validate inputs
                if not login or not password or not server:
                    return False, "Login, Password и Server обязательны"
                
                login_int = int(login) if isinstance(login, str) else login
                
                # Disconnect from current connection if any
                was_connected = self.connected
                if was_connected:
                    logger.info("[MT5] Disconnecting for reconnect...")
                    self.disconnect()
                    time.sleep(0.5)  # Small delay
                
                # (Re)Initialize with new settings
                if not self.initialize(terminal_path):
                    return False, "Не удалось инициализировать MT5"
                
                # Connect with new credentials
                success, message = self.connect(login_int, password, server)
                
                if success:
                    logger.info(f"[MT5] Settings applied and connected: {login_int}@{server}")
                    return True, f"✅ Настройки применены! {message}"
                else:
                    return False, f"Настройки сохранены, но не удалось подключиться: {message}"
                    
            except Exception as e:
                logger.error(f"[MT5] Failed to apply settings: {e}")
                return False, f"Ошибка применения настроек: {str(e)}"

    def reconnect(self) -> Tuple[bool, str]:
        """
        Переподключение к MT5 с текущими credentials.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        with self.lock:
            try:
                if not self.account_info:
                    return False, "Нет сохранённых credentials для reconnect"
                
                # Get current credentials
                login = self.account_info.get('login')
                server = self.account_info.get('server')
                
                if not login or not server:
                    return False, "Incomplete credentials"
                
                # Disconnect
                self.disconnect()
                time.sleep(0.5)
                
                # Note: we can't reconnect without password, which we don't store
                # This method is more for forced disconnect/connect cycle
                logger.warning("[MT5] Reconnect called but password not available")
                return False, "Reconnect requires password (use apply_settings instead)"
                
            except Exception as e:
                logger.error(f"[MT5] Reconnect failed: {e}")
                return False, f"Ошибка reconnect: {str(e)}"

    def is_connected(self) -> bool:
        """Проверка подключения."""
        if not self.mt5 or not self.connected:
            return False

        try:
            # Проверяем соединение через ping
            terminal_info = self.mt5.terminal_info()
            return terminal_info is not None
        except Exception as e:
            self.logger.debug(f"Connection check failed: {e}")
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
    
    def get_symbol_price(self, symbol: str) -> float:
        """Получение текущей цены символа (bid price)."""
        if self.is_connected():
            try:
                tick = self.mt5.symbol_info_tick(symbol)
                if tick:
                    return float(tick.bid)
            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
        return 0.0
    
    def get_open_positions(self) -> list:
        """Получение списка открытых позиций."""
        positions = []
        if self.is_connected():
            try:
                pos_list = self.mt5.positions_get()
                if pos_list:
                    for pos in pos_list:
                        positions.append({
                            'ticket': pos.ticket,
                            'symbol': pos.symbol,
                            'type': 'BUY' if pos.type == 0 else 'SELL',
                            'volume': pos.volume,
                            'price_open': pos.price_open,
                            'price_current': pos.price_current,
                            'profit': pos.profit,
                            'sl': pos.sl,
                            'tp': pos.tp,
                            'time': pos.time
                        })
            except Exception as e:
                logger.error(f"Error getting open positions: {e}")
        return positions

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
                # Учтём только торговые сделки (buy/sell) И ТОЛЬКО ЗАКРЫТЫЕ (entry=1)
                # entry=0 - открытие позиции, entry=1 - закрытие позиции (OUT)
                is_trade = deal.type in [self.mt5.DEAL_TYPE_BUY, self.mt5.DEAL_TYPE_SELL]
                is_closed = deal.entry == 1 if hasattr(deal, 'entry') else True  # если нет entry, считаем что закрыта
                
                if is_trade and is_closed:
                    pnl = float(deal.profit) if deal.profit is not None else 0.0

                    # deal.time can be datetime or int timestamp depending on MT5 bindings
                    try:
                        t = deal.time
                        if isinstance(t, int) or isinstance(t, float):
                            from datetime import datetime
                            dt = datetime.fromtimestamp(int(t))
                        else:
                            dt = t
                        # Корректировка на разницу часовых поясов MT5 сервера (-2 часа)
                        dt = dt - timedelta(hours=2)
                    except Exception:
                        from datetime import datetime
                        dt = datetime.now()

                    result.append({
                        'id': int(deal.ticket),
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M'),
                        'instrument': deal.symbol,
                        'symbol': deal.symbol,
                        'direction': 'BUY' if deal.type == self.mt5.DEAL_TYPE_BUY else 'SELL',
                        'pnl': round(pnl, 2),
                        'volume': float(deal.volume),
                        'price': float(deal.price),
                        'exit_price': float(deal.price),
                        # Дополнительные поля для детального анализа
                        'exit_time': dt,  # Полный datetime объект
                        'commission': float(deal.commission) if hasattr(deal, 'commission') else 0.0,
                        'swap': float(deal.swap) if hasattr(deal, 'swap') else 0.0,
                        'position_id': int(deal.position_id) if hasattr(deal, 'position_id') else 0,
                        'order_id': int(deal.order) if hasattr(deal, 'order') else 0,
                        'entry_type': deal.entry if hasattr(deal, 'entry') else 0,
                        'comment': deal.comment if hasattr(deal, 'comment') else ''
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
                    tf = get_data_path('trades_history.json')
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
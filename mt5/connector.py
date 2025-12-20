"""
MT5 Connector

Управление подключением к MetaTrader 5.
"""

import MetaTrader5 as mt5
from datetime import datetime
import yaml
import os


class MT5Connector:
    """
    Управление подключением к MT5.
    
    Функции:
    - Инициализация соединения
    - Проверка статуса
    - Получение информации о символах
    - Закрытие соединения
    """
    
    def __init__(self, config_path=None):
        """
        Инициализация MT5 коннектора.
        
        Args:
            config_path: Путь к YAML конфигу MT5 (опционально)
        """
        self.connected = False
        self.account_info = None
        self.config = None
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path):
        """Загрузка конфигурации из YAML файла."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        print(f"[+] MT5 config loaded from {config_path}")
    
    def connect(self, login=None, password=None, server=None, path=None, timeout=None):
        """
        Подключение к MT5.
        
        Args:
            login: Логин счёта (или берётся из config)
            password: Пароль (или берётся из config)
            server: Сервер (или берётся из config)
            path: Путь к MT5 (опционально)
            timeout: Таймаут подключения в мс (опционально)
            
        Returns:
            bool: True если подключение успешно
        """
        # Используем параметры из config если не переданы напрямую
        if self.config:
            conn = self.config['mt5']['connection']
            login = login or conn['login']
            password = password or conn['password']
            server = server or conn['server']
            path = path or conn.get('path')
            timeout = timeout or conn.get('timeout', 10000)
        
        if not all([login, password, server]):
            print("[!] Error: Login, password, and server are required")
            return False
        
        print(f"[*] Connecting to MT5...")
        print(f"    Login: {login}")
        print(f"    Server: {server}")
        
        # Инициализация MT5
        if path:
            if not mt5.initialize(path=path, login=login, password=password, 
                                  server=server, timeout=timeout):
                error = mt5.last_error()
                print(f"[!] MT5 initialization failed: {error}")
                return False
        else:
            if not mt5.initialize(login=login, password=password, 
                                  server=server, timeout=timeout):
                error = mt5.last_error()
                print(f"[!] MT5 initialization failed: {error}")
                return False
        
        # Проверка подключения
        self.account_info = mt5.account_info()
        if self.account_info is None:
            print("[!] Failed to get account info")
            mt5.shutdown()
            return False
        
        self.connected = True
        
        # Вывод информации о счёте
        print(f"[✓] Connected to MT5 successfully!")
        print(f"    Account: {self.account_info.login}")
        print(f"    Name: {self.account_info.name}")
        print(f"    Server: {self.account_info.server}")
        print(f"    Balance: ${self.account_info.balance:,.2f}")
        print(f"    Equity: ${self.account_info.equity:,.2f}")
        print(f"    Leverage: 1:{self.account_info.leverage}")
        print(f"    Currency: {self.account_info.currency}")
        
        return True
    
    def disconnect(self):
        """Отключение от MT5."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[*] Disconnected from MT5")
    
    def is_connected(self):
        """
        Проверка статуса подключения.
        
        Returns:
            bool: True если подключен
        """
        return self.connected
    
    def get_account_info(self):
        """
        Получение информации о счёте.
        
        Returns:
            dict: Информация о счёте
        """
        if not self.connected:
            print("[!] Not connected to MT5")
            return None
        
        info = mt5.account_info()
        if info is None:
            return None
        
        return {
            'login': info.login,
            'name': info.name,
            'server': info.server,
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'margin_free': info.margin_free,
            'margin_level': info.margin_level,
            'profit': info.profit,
            'leverage': info.leverage,
            'currency': info.currency
        }
    
    def get_symbol_info(self, symbol):
        """
        Получение информации о символе.
        
        Args:
            symbol: Название символа (например, "XAUUSD")
            
        Returns:
            dict: Информация о символе (point, digits, contract_size и т.д.)
        """
        if not self.connected:
            print(f"[!] Not connected to MT5")
            return None
        
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"[!] Symbol {symbol} not found")
            return None
        
        # Проверяем что символ видимый
        if not info.visible:
            print(f"[*] Symbol {symbol} is not visible, attempting to enable...")
            if not mt5.symbol_select(symbol, True):
                print(f"[!] Failed to enable symbol {symbol}")
                return None
        
        return {
            'name': info.name,
            'description': info.description,
            'point': info.point,
            'digits': info.digits,
            'trade_contract_size': info.trade_contract_size,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'bid': info.bid,
            'ask': info.ask,
            'spread': info.spread,
            'spread_float': info.spread_float,
            'trade_mode': info.trade_mode
        }
    
    def get_positions(self):
        """
        Получение открытых позиций.
        
        Returns:
            list: Список открытых позиций
        """
        if not self.connected:
            print("[!] Not connected to MT5")
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [
            {
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'time': datetime.fromtimestamp(pos.time)
            }
            for pos in positions
        ]
    
    def get_terminal_info(self):
        """
        Получение информации о терминале MT5.
        
        Returns:
            dict: Информация о терминале
        """
        if not self.connected:
            print("[!] Not connected to MT5")
            return None
        
        info = mt5.terminal_info()
        if info is None:
            return None
        
        return {
            'community_account': info.community_account,
            'community_connection': info.community_connection,
            'connected': info.connected,
            'trade_allowed': info.trade_allowed,
            'tradeapi_disabled': info.tradeapi_disabled,
            'email_enabled': info.email_enabled,
            'ftp_enabled': info.ftp_enabled,
            'build': info.build,
            'maxbars': info.maxbars,
            'codepage': info.codepage,
            'company': info.company,
            'name': info.name,
            'language': info.language,
            'data_path': info.data_path,
            'commondata_path': info.commondata_path
        }

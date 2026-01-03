"""
Live Trader - Live and Demo Trading Module
"""

import logging
import time
from datetime import datetime
from typing import Dict, Tuple
import threading
import json
from pathlib import Path

# Добавить импорт
try:
    from src.ai.news_filter import GPTNewsFilter
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False

try:
    from src.ml.predictor import TradePredictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

class LiveTrader:
    def __init__(self, config_dir: str = 'config', enable_trading: bool = False, enable_gpt: bool = True) -> None:
        """
        Args:
            config_dir: Путь к папке с конфигами
            enable_trading: True = реальная торговля, False = только мониторинг
            enable_gpt: True = использовать GPT фильтр, False = отключить
        """
        self.config_dir: str = config_dir
        self.enable_trading: bool = enable_trading
        self.enable_gpt: bool = enable_gpt
        self.connected: bool = False
        
        # Загрузка конфигов
        self.load_configs()
        
        # Подключение к MT5
        self.connect_mt5()
        
        # Инициализация стратегий
        self.init_strategies()
        
        # Инициализация фильтров
        self.init_filters()
        
        # Инициализация executor
        from src.core.executor import Executor
        self.executor = Executor(mt5_connector=self.mt5_connector)
    
    def start(self) -> None:
        """Запуск трейдера (для совместимости)."""
        pass
    
    def load_configs(self) -> None:
        """Загрузка конфигурационных файлов."""
        config_path = Path(self.config_dir)
        
        # Загружаем MT5 конфиг
        mt5_config_path = config_path / 'mt5.yaml'
        if mt5_config_path.exists():
            import yaml
            with open(mt5_config_path, 'r') as f:
                self.mt5_config = yaml.safe_load(f)
        else:
            self.mt5_config = {}
        
        # Загружаем конфиг инструментов
        instruments_config_path = config_path / 'instruments.yaml'
        if instruments_config_path.exists():
            import yaml
            with open(instruments_config_path, 'r') as f:
                self.instruments_config = yaml.safe_load(f)
        else:
            self.instruments_config = {}
        
        # Загружаем конфиг портфеля
        portfolio_config_path = config_path / 'portfolio.yaml'
        if portfolio_config_path.exists():
            import yaml
            with open(portfolio_config_path, 'r') as f:
                self.portfolio_config = yaml.safe_load(f)
        else:
            self.portfolio_config = {}
    
    def connect_mt5(self) -> bool:
        """Подключение к MetaTrader 5."""
        import MetaTrader5 as mt5
        
        # Загружаем данные из конфига
        mt5_config = self.mt5_config.get('mt5', {}).get('connection', {})
        
        login = mt5_config.get('login')
        password = mt5_config.get('password')
        server = mt5_config.get('server')
        path = mt5_config.get('path')
        
        # Инициализация MT5
        if not mt5.initialize(path=path):
            error = mt5.last_error()
            raise ConnectionError(f"MT5 initialize failed: {error}")
        
        # Авторизация
        if login and password and server:
            authorized = mt5.login(login=int(login), password=password, server=server)
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                raise ConnectionError(f"MT5 login failed: {error}")
        
        # Проверяем подключение
        account_info = mt5.account_info()
        if account_info is None:
            raise ConnectionError("Failed to get account info")
        
        self.connected = True
        self.account_info = account_info
        self.mt5_connector = mt5  # Для executor
        
        return True
    
    def get_connection_status(self) -> dict:
        """Возвращает статус подключения."""
        if not self.connected:
            return {'connected': False, 'message': 'Не подключено'}
        
        import MetaTrader5 as mt5
        info = mt5.account_info()
        
        if info:
            return {
                'connected': True,
                'message': 'Подключено',
                'broker': info.company,
                'account': info.login,
                'balance': info.balance,
                'equity': info.equity
            }
        return {'connected': False, 'message': 'Соединение потеряно'}
    
    def init_strategies(self):
        """Инициализация стратегий."""
        # Загружаем стратегии из конфига
        self.strategies = {}
        
        instruments = self.instruments_config.get('instruments', {})
        
        for symbol, config in instruments.items():
            if config.get('enabled', False):
                strategy_name = config.get('strategy', 'eurusd_strategy')
                
                try:
                    if strategy_name == 'eurusd_strategy':
                        from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement as EURUSDStrategy
                        self.strategies[symbol] = EURUSDStrategy()
                    elif strategy_name == 'xauusd_strategy':
                        from src.strategies.xauusd_strategy import XAUUSDStrategy
                        self.strategies[symbol] = XAUUSDStrategy(symbol, config)
                    
                    print(f"[✓] Strategy loaded: {symbol} -> {strategy_name}")
                    
                except Exception as e:
                    print(f"[!] Failed to load strategy for {symbol}: {e}")
    
    def init_filters(self):
        """Инициализация фильтров."""
        # Инициализация GPT фильтра
        self.gpt_filter = None
        if self.enable_gpt and GPT_AVAILABLE:
            try:
                self.gpt_filter = GPTNewsFilter()
                print("[✓] GPT News Filter initialized")
            except Exception as e:
                print(f"[!] GPT Filter disabled: {e}")
        elif not self.enable_gpt:
            print("[!] GPT Filter disabled by user setting")
        else:
            print("[!] GPT Filter not available (missing dependencies)")
        
        # Инициализация ML предиктора
        self.ml_predictor = None
        if ML_AVAILABLE:
            try:
                self.ml_predictor = TradePredictor()
                if self.ml_predictor.is_trained:
                    print("[✓] ML Predictor loaded")
                else:
                    print("[!] ML Predictor not trained yet")
            except Exception as e:
                print(f"[!] ML Predictor disabled: {e}")
        else:
            print("[!] ML Predictor not available (missing dependencies)")
    
    def check_signals(self):
        """Проверка сигналов для всех стратегий."""
        signals = []
        
        for symbol, strategy in self.strategies.items():
            try:
                # Получаем данные
                h1_data, m15_data = self.load_market_data(symbol)
                
                if h1_data is None or m15_data is None:
                    continue
                
                # Проверяем сигналы стратегии
                signal = strategy.check_signal(h1_data, m15_data)
                
                if signal and signal.get('valid', False):
                    # Применяем фильтры
                    filtered_signal = self.process_signal(symbol, signal, h1_data, m15_data, len(m15_data)-1)
                    
                    if filtered_signal:
                        signals.append(f"{symbol}: {filtered_signal}")
                        
                        # Если разрешена торговля, открываем сделку
                        if self.enable_trading:
                            self.execute_trade(symbol, filtered_signal)
            
            except Exception as e:
                print(f"[!] Error checking {symbol}: {e}")
        
        return signals
    
    def load_market_data(self, symbol: str):
        """Загрузка рыночных данных."""
        try:
            from src.core.data_loader import DataLoader
            
            data_loader = DataLoader(instrument=symbol.lower())
            h1_data, m15_data = data_loader.load()
            
            return h1_data, m15_data
            
        except Exception as e:
            print(f"[!] Failed to load data for {symbol}: {e}")
            return None, None
    
    def process_signal(self, instrument: str, signal: dict, h1_data=None, m15_data=None, m15_idx=None):
        """Обработка сигнала с ML и GPT фильтрами."""
        
        if not signal.get('valid', False):
            return
        
        # 1. ML проверка (если есть данные)
        if h1_data is not None and m15_data is not None and m15_idx is not None:
            ml_ok, ml_prob = self.check_ml_filter(h1_data, m15_data, m15_idx, signal)
            if not ml_ok:
                return f"ML filtered (prob: {ml_prob:.1%})"
        
        # 2. GPT проверка
        gpt_ok, gpt_reason = self.check_gpt_filter(instrument)
        if not gpt_ok:
            return f"GPT filtered: {gpt_reason}"
        
        # Сигнал прошел все фильтры
        direction = "BUY" if signal.get('direction') == 'long' else "SELL"
        entry_price = signal.get('entry_price', 0)
        sl = signal.get('stop_loss', 0)
        tp = signal.get('take_profit', 0)
        
        return f"{direction} @ {entry_price:.5f} (SL: {sl:.5f}, TP: {tp:.5f})"
    
    def check_ml_filter(self, h1_data, m15_data, m15_idx, signal):
        """ML фильтр сигнала."""
        if not self.ml_predictor:
            return True, 0.5
        
        try:
            # Получаем признаки для ML
            features = self.ml_predictor.extract_features(h1_data, m15_data, m15_idx)
            prediction = self.ml_predictor.predict(features)
            
            # Если предсказание не совпадает с сигналом, фильтруем
            signal_direction = 1 if signal.get('direction') == 'long' else 0
            if prediction != signal_direction:
                return False, prediction
            
            return True, prediction
        except Exception as e:
            print(f"[!] ML filter error: {e}")
            return True, 0.5
    
    def check_gpt_filter(self, instrument: str) -> Tuple[bool, str]:
        """GPT фильтр сигнала."""
        if not self.gpt_filter:
            return True, "GPT filter disabled"
        
        try:
            safe, risk_level, reason = self.gpt_filter.check_trading_safety(instrument)
            
            if not safe:
                return False, reason
            
            return True, reason
        except Exception as e:
            print(f"[!] GPT filter error: {e}")
            return True, "GPT filter error"
    
    def execute_trade(self, symbol: str, signal: dict):
        """Исполнение сделки."""
        try:
            result = self.executor.execute_signal(symbol, signal)
            
            if result:
                print(f"[TRADE] {symbol}: {result}")
                
        except Exception as e:
            print(f"[!] Trade execution failed for {symbol}: {e}")
    
    def save_trade(self, trade: dict):
        """Сохраняет сделку в историю."""
        import json
        from pathlib import Path
        
        trades_file = Path('data/trades_history.json')
        trades_file.parent.mkdir(exist_ok=True)
        
        trades = []
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        
        trades.append(trade)
        
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
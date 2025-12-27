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
    def __init__(self, config_dir: str = 'config', enable_trading: bool = False):
        """
        Args:
            config_dir: Путь к папке с конфигами
            enable_trading: True = реальная торговля, False = только мониторинг
        """
        self.config_dir = config_dir
        self.enable_trading = enable_trading
        self.connected = False
        
        # Загрузка конфигов
        self.load_configs()
        
        # Подключение к MT5
        self.connect_mt5()
        
        # Инициализация стратегий
        self.init_strategies()
        
        # Инициализация фильтров
        self.init_filters()
    
    def load_configs(self):
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
        if GPT_AVAILABLE:
            try:
                self.gpt_filter = GPTNewsFilter()
                print("[✓] GPT News Filter initialized")
            except Exception as e:
                print(f"[!] GPT Filter disabled: {e}")
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
    
    def execute_trade(self, symbol: str, signal: dict):
        """Исполнение сделки."""
        try:
            from src.core.executor import Executor
            
            executor = Executor(enable_trading=self.enable_trading)
            result = executor.execute_signal(symbol, signal)
            
            if result:
                print(f"[TRADE] {symbol}: {result}")
                
        except Exception as e:
            print(f"[!] Trade execution failed for {symbol}: {e}")
    
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
        """Загрузка рыночных данных."""
        try:
            from src.core.data_loader import DataLoader
            
            data_loader = DataLoader()
            h1_data = data_loader.load_historical_data(symbol, 'H1', days=30)
            m15_data = data_loader.load_historical_data(symbol, 'M15', days=7)
            
            return h1_data, m15_data
            
        except Exception as e:
            print(f"[!] Failed to load data for {symbol}: {e}")
            return None, None
    
    def execute_trade(self, symbol: str, signal: dict):
        """Исполнение сделки."""
        try:
            from src.core.executor import Executor
            
            executor = Executor(enable_trading=self.enable_trading)
            result = executor.execute_signal(symbol, signal)
            
            if result:
                print(f"[TRADE] {symbol}: {result}")
                
        except Exception as e:
            print(f"[!] Trade execution failed for {symbol}: {e}")
    
    def check_gpt_filter(self, instrument: str) -> Tuple[bool, str]:
        
        if not self.gpt_filter:
            return (True, "GPT filter disabled")
        
        safe, risk_level, reason = self.gpt_filter.check_trading_safety(instrument)
        
        if not safe:
            print(f"[GPT] ⚠️ {instrument}: {risk_level} risk - {reason}")
            return (False, reason)
        
        if risk_level in ["HIGH", "MEDIUM"]:
            print(f"[GPT] ⚡ {instrument}: {risk_level} risk - {reason}")
        
        return (True, reason)
    
    def check_ml_filter(self, h1_data, m15_data, m15_idx, signal) -> Tuple[bool, float]:
        """Проверка через ML модель."""
        
        if not self.ml_predictor or not self.ml_predictor.is_trained:
            return (True, 0.5)
        
        probability, confidence = self.ml_predictor.predict_success(
            h1_data, m15_data, m15_idx, signal
        )
        
        should_trade = self.ml_predictor.should_take_trade(probability, min_probability=0.55)
        
        print(f"[ML] Probability: {probability:.1%} ({confidence})")
        
        return (should_trade, probability)
    
    def process_signal(self, instrument: str, signal: dict, h1_data=None, m15_data=None, m15_idx=None):
        """Обработка сигнала с ML и GPT фильтрами."""
        
        if not signal.get('valid', False):
            return
        
        # 1. ML проверка (если есть данные)
        if h1_data is not None and m15_data is not None and m15_idx is not None:
            ml_ok, ml_prob = self.check_ml_filter(h1_data, m15_data, m15_idx, signal)
            if not ml_ok:
                print(f"[{instrument}] Signal BLOCKED by ML: {ml_prob:.1%} probability")
                return
        else:
            ml_prob = 0.5  # Default
        
        # 2. GPT проверка
        gpt_ok, gpt_reason = self.check_gpt_filter(instrument)
        if not gpt_ok:
            print(f"[{instrument}] Signal BLOCKED by GPT: {gpt_reason}")
            return
        
        # 3. Корректировка риска на основе ML уверенности
        risk_multiplier = 1.0
        if ml_prob > 0.7:
            risk_multiplier = 1.0  # Полный риск
        elif ml_prob > 0.6:
            risk_multiplier = 0.75  # 75%
        else:
            risk_multiplier = 0.5  # 50%
        
        # Корректировка от GPT
        if self.gpt_filter:
            reduce, gpt_multiplier = self.gpt_filter.should_reduce_risk(instrument)
            if reduce and gpt_multiplier < risk_multiplier:
                risk_multiplier = gpt_multiplier
        
        # Применяем мультипликатор риска к сигналу
        signal['risk_multiplier'] = risk_multiplier
        
        # ... остальная логика открытия сделки ...
        print(f"[{instrument}] ✅ Signal APPROVED (ML: {ml_prob:.1%}, Risk: {risk_multiplier:.0%})")
    
    def run(self):
        """Запуск live trading в основном потоке"""
        print("[+] Запуск LIVE трейдинга...")
        
        if not self.mt5_connector.connect():
            print("[!] Ошибка подключения к MT5")
            return
        
        print("[+] Подключено к MT5")
        self.running = True
        
        try:
            while self.running:
                # Проверка времени рынка
                if not self._is_market_open():
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Рынок закрыт - ждём открытия...")
                    time.sleep(300)  # Проверка каждые 5 минут
                    continue
                
                self._check_signals_loop()
                time.sleep(60)  # Проверка каждую минуту
        except KeyboardInterrupt:
            print("\n[!] Остановлено пользователем")
        finally:
            self.mt5_connector.disconnect()
    
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
                # Для простоты используем последний бар для анализа
                if len(m15_data) < 2:
                    continue
                    
                current_idx = len(m15_data) - 2  # Предыдущая свеча
                analysis_price = m15_data.iloc[current_idx]['close']
                entry_price = m15_data.iloc[-1]['open']  # Следующая свеча
                
                # Имитируем вызов get_trade
                signal = {
                    'direction': None,
                    'sl': None,
                    'tp': None,
                    'valid': False,
                    'entry_price': entry_price
                }
                
                # Простая логика для демонстрации
                if hasattr(strategy, 'get_signal'):
                    try:
                        result = strategy.get_signal(m15_data, current_idx, analysis_price, entry_price)
                        if result and result.get('valid', False):
                            signal = {
                                'direction': result['direction'],
                                'stop_loss': result['sl'],
                                'take_profit': result['tp'],
                                'valid': True,
                                'entry_price': result['entry']
                            }
                    except Exception as e:
                        print(f"[!] Strategy error for {symbol}: {e}")
                        continue
                
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
    
    def _is_market_open(self) -> bool:
        """Проверка, открыт ли рынок"""
        import MetaTrader5 as mt5
        
        if not mt5.terminal_info():
            return False
            
        # Проверяем сессии для основных пар
        symbols = ['EURUSD', 'XAUUSD']
        for symbol in symbols:
            if mt5.symbol_info(symbol) is None:
                continue
                
            # Получаем информацию о сессиях
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info and hasattr(symbol_info, 'session_deals'):
                # Если есть сделки в сессии, рынок открыт
                if symbol_info.session_deals > 0:
                    return True
        
        # Простая проверка по времени
        now = datetime.now()
        if now.weekday() >= 5:  # суббота, воскресенье
            return False
            
        # Торговое время (00:00 - 23:59 UTC, но зависит от брокера)
        return True
    
    def _check_signals_loop(self):
        """Проверка сигналов для всех инструментов"""
        for instrument, strategy in self.strategies.items():
            self._check_signals(instrument, strategy)
    
    def _check_signals(self, instrument: str, strategy):
        """Проверка сигналов для инструмента"""
        try:
            # Получение последних данных
            data = self.mt5_connector.get_latest_data(instrument, timeframe='H1', count=100)
            if data.empty:
                return
            
            # Получение текущей цены
            current_price_data = self.mt5_connector.get_current_price(instrument)
            if not current_price_data:
                return
            
            current_price = current_price_data['bid']  # Используем bid цену
            
            # Упрощённая генерация сигнала для live (SMA crossover)
            signal = None
            if len(data) > 10:
                sma_short = data['close'].rolling(5).mean().iloc[-1]
                sma_long = data['close'].rolling(20).mean().iloc[-1]
                
                if sma_short > sma_long and data['close'].iloc[-1] > sma_short:
                    signal = {'type': 'BUY', 'direction': 'BUY', 'sl': current_price * 0.98, 'tp': current_price * 1.05}
                elif sma_short < sma_long and data['close'].iloc[-1] < sma_short:
                    signal = {'type': 'SELL', 'direction': 'SELL', 'sl': current_price * 1.02, 'tp': current_price * 0.95}
            
            if signal:
                self.logger.info(f"Signal generated for {instrument}: {signal}")
                
                # Исполнение сигнала (пока заглушка)
                print(f"[!] {instrument}: Сигнал {signal['type']} на цене {current_price}")
                # self.executor.execute_signal(signal, current_price)
        
        except Exception as e:
            print(f"Error checking signals for {instrument}: {e}")
    
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
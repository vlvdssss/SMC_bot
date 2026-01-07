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
from src.core.logger import logger

# Добавить импорт
try:
    from src.ai.news_filter import GPTNewsFilter
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False

try:
    from src.ai.signal_manager import AISignalManager
    AI_SIGNAL_MANAGER_AVAILABLE = True
except ImportError:
    AI_SIGNAL_MANAGER_AVAILABLE = False

try:
    from src.ml.predictor import TradePredictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    from src.monitoring import TelegramNotifier, AlertManager
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

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
        
        # Инициализация AI Signal Manager
        self.ai_signal_manager = None
        if AI_SIGNAL_MANAGER_AVAILABLE:
            try:
                self.ai_signal_manager = AISignalManager()
                logger.info("[LiveTrader] AI Signal Manager initialized")
            except Exception as e:
                logger.error(f"[LiveTrader] Failed to init AI Signal Manager: {e}")
        
        # Инициализация мониторинга
        self.telegram = None
        self.alert_manager = None
        self.notify_config = {}
        if MONITORING_AVAILABLE:
            self._init_monitoring()
    
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
                # Получаем имя класса стратегии из конфига
                strategy_class = config.get('strategy_class', 'StrategyXAUUSD')
                
                try:
                    # Only XAUUSD strategy remains (EURUSD removed)
                    if strategy_class == 'StrategyXAUUSD' or symbol == 'XAUUSD':
                        from src.strategies.xauusd_strategy import StrategyXAUUSD
                        strategy = StrategyXAUUSD()
                        
                        # Применяем пользовательские настройки из config.json
                        try:
                            config_file = Path('data/config.json')
                            if config_file.exists():
                                import json
                                with open(config_file, 'r') as f:
                                    user_config = json.load(f)
                                    strategy_settings = user_config.get('strategy', {})
                                    if strategy_settings:
                                        strategy.max_daily_trades = strategy_settings.get('max_daily_trades', strategy.max_daily_trades)
                                        strategy.max_daily_loss = strategy_settings.get('max_daily_loss', strategy.max_daily_loss)
                                        strategy.min_atr_threshold = strategy_settings.get('min_atr_threshold', strategy.min_atr_threshold)
                                        strategy.max_atr_threshold = strategy_settings.get('max_atr_threshold', strategy.max_atr_threshold)
                                        logger.info(f"[Strategy] Applied custom settings: trades={strategy.max_daily_trades}, "
                                                  f"loss={strategy.max_daily_loss}%, min_atr={strategy.min_atr_threshold}, "
                                                  f"max_atr={strategy.max_atr_threshold}")
                        except Exception as e:
                            logger.warning(f"[Strategy] Failed to load custom settings: {e}")
                        
                        self.strategies[symbol] = strategy
                    else:
                        logger.warning(f"Unknown strategy class: {strategy_class} for {symbol}")
                        continue
                    
                    logger.info(f"Strategy loaded: {symbol} -> {strategy_class}")
                    
                except Exception as e:
                    logger.error(f"Failed to load strategy for {symbol}: {e}")
                    # Алерт об ошибке стратегии
                    if self.alert_manager:
                        self.alert_manager.alert_strategy_error(strategy_class, str(e))
    
    def _init_monitoring(self):
        """Инициализация системы мониторинга."""
        try:
            import yaml
            config_path = Path('config/telegram.yaml')
            
            if not config_path.exists():
                logger.info("Telegram config not found")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            tg_config = config.get('telegram', {})
            if tg_config.get('enabled', False):
                self.telegram = TelegramNotifier(
                    token=tg_config.get('bot_token'),
                    chat_id=tg_config.get('chat_id')
                )
                self.notify_config = tg_config.get('notify', {})
                logger.info("Telegram notifications enabled in LiveTrader")
                
                # AlertManager
                self.alert_manager = AlertManager()
                
                # Связываем с Telegram
                def telegram_alert_handler(alert):
                    if self.telegram and self.notify_config.get('alerts', True):
                        if alert.level.value in ['WARNING', 'ERROR', 'CRITICAL']:
                            self.telegram.send_alert(
                                alert_type=alert.type.value,
                                message=alert.message,
                                level=alert.level.value
                            )
                
                self.alert_manager.add_handler(telegram_alert_handler)
                
        except Exception as e:
            logger.error(f"Failed to init monitoring in LiveTrader: {e}")
    
    def init_filters(self):
        """Инициализация фильтров."""
        # Инициализация GPT фильтра
        self.gpt_filter = None
        if self.enable_gpt and GPT_AVAILABLE:
            try:
                self.gpt_filter = GPTNewsFilter()
                logger.info("GPT News Filter initialized")
            except Exception as e:
                logger.warning(f"GPT Filter disabled: {e}")
        elif not self.enable_gpt:
            logger.info("GPT Filter disabled by user setting")
        else:
            logger.warning("GPT Filter not available (missing dependencies)")
        
        # Инициализация ML предиктора
        self.ml_predictor = None
        if ML_AVAILABLE:
            try:
                self.ml_predictor = TradePredictor()
                if self.ml_predictor.is_trained:
                    logger.info("ML Predictor loaded")
                else:
                    logger.warning("ML Predictor not trained yet")
            except Exception as e:
                logger.warning(f"ML Predictor disabled: {e}")
                # Алерт об ошибке ML
                if self.alert_manager:
                    self.alert_manager.alert_ml_error(str(e))
        else:
            logger.warning("ML Predictor not available (missing dependencies)")
    
    def check_signals(self):
        """Проверка сигналов для всех стратегий."""
        signals = []
        
        # Проверяем AI сигналы если доступны
        if self.ai_signal_manager:
            ai_signals = self._check_ai_signals()
            if ai_signals:
                signals.extend(ai_signals)
        
        for symbol, strategy in self.strategies.items():
            try:
                # Check AI permission first
                if not self._should_trade_allowed(symbol):
                    logger.info(f"[LiveTrader] Trading blocked by AI for {symbol}")
                    continue
                
                # Получаем данные
                h1_data, m15_data = self.load_market_data(symbol)
                
                if h1_data is None or m15_data is None:
                    logger.debug(f"[LiveTrader] No market data for {symbol}")
                    continue
                
                # Проверяем сигналы стратегии
                logger.debug(f"[LiveTrader] Checking strategy signals for {symbol}...")
                signal = strategy.check_signal(h1_data, m15_data)
                
                if signal and signal.get('valid', False):
                    logger.info(f"[LiveTrader] ✅ Valid signal from strategy: {signal.get('direction')} @ {signal.get('entry')}")
                    # Применяем фильтры
                    filtered_signal = self.process_signal(symbol, signal, h1_data, m15_data, len(m15_data)-1)
                else:
                    if signal:
                        logger.info(f"[LiveTrader] ❌ Strategy signal NOT valid for {symbol}: {signal}")
                    else:
                        logger.debug(f"[LiveTrader] No strategy signal for {symbol}")
                    
                    if filtered_signal:
                        # Apply AI risk multiplier
                        filtered_signal = self._apply_ai_risk_multiplier(symbol, filtered_signal)
                        
                        signals.append(f"{symbol}: {filtered_signal}")
                        
                        # Если разрешена торговля, открываем сделку
                        if self.enable_trading:
                            self.execute_trade(symbol, filtered_signal)
            
            except Exception as e:
                logger.error(f"Error checking {symbol}: {e}")
        
        return signals
    
    def load_market_data(self, symbol: str):
        """Загрузка рыночных данных."""
        try:
            from src.core.data_loader import DataLoader
            
            data_loader = DataLoader(instrument=symbol.lower())
            h1_data, m15_data = data_loader.load()
            
            return h1_data, m15_data
            
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}: {e}")
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
            logger.error(f"ML filter error: {e}")
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
            logger.error(f"GPT filter error: {e}")
            return True, "GPT filter error"
    
    def execute_trade(self, symbol: str, signal: dict):
        """Исполнение сделки."""
        try:
            result = self.executor.execute_signal(symbol, signal)
            
            if result:
                logger.info(f"Trade executed for {symbol}: {result}")
                
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {e}")
    
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
    
    # ========== AI Integration Methods ==========
    
    def _check_ai_signals(self) -> list:
        """
        Проверка и исполнение AI сигналов.
        
        Returns:
            List of triggered AI signals ready for execution
        """
        if not self.ai_signal_manager:
            return []
        
        triggered_signals = []
        
        try:
            import MetaTrader5 as mt5
            current_time = datetime.now()
            
            # Проверяем каждый символ
            for symbol in ['XAUUSD', 'EURUSD']:
                # Получаем текущую цену
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    continue
                
                current_price = (tick.bid + tick.ask) / 2
                
                # Проверяем триггеры
                signals = self.ai_signal_manager.check_triggers(
                    current_price=current_price,
                    symbol=symbol,
                    current_time=current_time
                )
                
                if signals:
                    for ai_signal in signals:
                        # Конвертируем AI сигнал в формат стратегии
                        strategy_signal = self._convert_ai_signal_to_strategy(ai_signal)
                        triggered_signals.append(strategy_signal)
                        
                        logger.info(
                            f"[AI-Signal] Triggered: {symbol} {ai_signal.type} "
                            f"@ {ai_signal.entry_price} (conf: {ai_signal.confidence}%)"
                        )
        
        except Exception as e:
            logger.error(f"[AI] Signal check failed: {e}")
        
        return triggered_signals
    
    def _convert_ai_signal_to_strategy(self, ai_signal) -> dict:
        """
        Конвертация AI сигнала в формат стратегии.
        
        Args:
            ai_signal: AISignal объект
        
        Returns:
            Dict в формате стратегии
        """
        return {
            'symbol': ai_signal.symbol,
            'direction': 'long' if ai_signal.type.upper() == 'BUY' else 'short',
            'entry_price': ai_signal.entry_price,
            'sl': ai_signal.stop_loss,
            'tp': ai_signal.take_profit,
            'confidence': ai_signal.confidence / 100.0,  # 0-1 scale
            'reasoning': ai_signal.reasoning,
            'source': 'AI-GPT',
            'ai_signal_id': ai_signal.id,
            'timestamp': datetime.now().isoformat()
        }
    
    def _should_trade_allowed(self, symbol: str) -> bool:
        """Check if AI allows trading for symbol."""
        if not self.ai_signal_manager:
            return True  # AI not available, allow trading
        
        try:
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission(symbol)
            
            if not allowed:
                logger.warning(f"[AI] Trading blocked for {symbol}: {reason}")
            
            return allowed
        except Exception as e:
            logger.error(f"[AI] Permission check failed: {e}")
            return True  # Fail-safe: allow trading on error
    
    def _apply_ai_risk_multiplier(self, symbol: str, signal: dict) -> dict:
        """Apply AI risk multiplier to signal position size."""
        if not self.ai_signal_manager:
            return signal
        
        try:
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission(symbol)
            
            if multiplier != 1.0:
                logger.info(f"[AI] Applying risk multiplier {multiplier:.2f}x for {symbol}: {reason}")
                
                # Reduce position size
                if 'volume' in signal:
                    signal['volume'] = signal['volume'] * multiplier
                
                # Store original and modified for logging
                signal['ai_risk_multiplier'] = multiplier
                signal['ai_risk_reason'] = reason
            
            return signal
        except Exception as e:
            logger.error(f"[AI] Risk multiplier failed: {e}")
            return signal  # Fail-safe: return original signal
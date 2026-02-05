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
import sys
from src.core.logger import logger
from src.core.risk_manager import RiskManager

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
        # Check if already initialized (prevent duplicate logs)
        if hasattr(self, '_initialized') and self._initialized:
            logger.debug("[LiveTrader] Already initialized, skipping duplicate init...")
            return
        
        logger.info("="*80)
        logger.info("[LiveTrader] Initializing LiveTrader...")
        logger.info(f"[LiveTrader] Mode: {'REAL TRADING' if enable_trading else 'MONITORING ONLY'}")
        logger.info(f"[LiveTrader] GPT filter: {'ENABLED' if enable_gpt else 'DISABLED'}")
        self._initialized = False
        
        self.config_dir: str = config_dir
        self.enable_trading: bool = enable_trading
        self.enable_gpt: bool = enable_gpt
        self.connected: bool = False
        
        # Загрузка конфигов
        logger.info("[LiveTrader] Loading configuration files...")
        self.load_configs()
        
        # Подключение к MT5
        logger.info("[LiveTrader] Connecting to MetaTrader 5...")
        self.connect_mt5()
        
        # Инициализация стратегий
        logger.info("[LiveTrader] Initializing trading strategies...")
        self.init_strategies()
        
        # Инициализация фильтров
        logger.info("[LiveTrader] Initializing filters (GPT, ML)...")
        self.init_filters()
        
        # Инициализация executor
        logger.info("[LiveTrader] Initializing Executor...")
        from src.core.executor import Executor
        self.executor = Executor(mt5_connector=self.mt5_connector)
        logger.info("[LiveTrader] Executor ready")
        
        # Инициализация RiskManager для trailing расчётов
        logger.info("[LiveTrader] Initializing RiskManager...")
        risk_config = self.config.get('trading', {}).get('risk', {})
        self.risk_manager = RiskManager(config=risk_config)
        logger.info("[LiveTrader] RiskManager ready")
        
        # Инициализация V4 Trailing Stop Handler
        trailing_config = self.config.get('trading', {}).get('trailing_stop', {})
        trailing_enabled = trailing_config.get('enabled', False)
        
        if trailing_enabled:
            logger.info("[LiveTrader] Initializing V4 Trailing Stop...")
            from src.live.trailing_stop_v4 import TrailingStopV4
            self.trailing_v4 = TrailingStopV4(mt5_connector=self.mt5_connector)
            logger.info("[V4-Trailing] ✅ ENABLED (30% activation, 50% stop distance)")
        else:
            logger.info("[V4-Trailing] ⛔ DISABLED in settings")
            from src.live.trailing_stop_v4 import TrailingStopV4
            self.trailing_v4 = TrailingStopV4(mt5_connector=self.mt5_connector)
        
        # Инициализация NewsFetcher (для V3)
        self.news_fetcher = None
        try:
            from src.ai.news_fetcher import RealTimeNewsFetcher
            self.news_fetcher = RealTimeNewsFetcher()
            logger.info("[LiveTrader] NewsFetcher initialized")
        except Exception as e:
            logger.warning(f"[LiveTrader] NewsFetcher not available: {e}")
        
        # Инициализация AI Signal Manager
        self.ai_signal_manager = None
        if AI_SIGNAL_MANAGER_AVAILABLE:
            try:
                logger.info("[LiveTrader] Initializing AI Signal Manager...")
                # Передаем telegram_notifier если он уже инициализирован
                telegram_for_signals = getattr(self, 'telegram', None)
                self.ai_signal_manager = AISignalManager(telegram_notifier=telegram_for_signals)
                # Set executor reference for position checks
                self.ai_signal_manager.set_executor(self.executor)
                
                # 🚀 АКТИВАЦИЯ SIGNAL QUALITY V3.0
                try:
                    from src.ai.activate_v3 import activate_v3, ENABLE_SIGNAL_QUALITY_V3
                    if ENABLE_SIGNAL_QUALITY_V3 and self.news_fetcher:
                        self.ai_signal_manager = activate_v3(
                            self.ai_signal_manager,
                            self.news_fetcher,
                            enable=True
                        )
                    elif ENABLE_SIGNAL_QUALITY_V3:
                        logger.warning("[LiveTrader] V3 enabled but news_fetcher not available - using V2")
                except ImportError as e:
                    logger.info(f"[LiveTrader] V3 module not found ({e}) - using V2 logic")
                
                logger.info("[LiveTrader] AI Signal Manager initialized with executor reference")
            except Exception as e:
                logger.error(f"[LiveTrader] Failed to init AI Signal Manager: {e}")
        else:
            logger.warning("[LiveTrader] AI Signal Manager unavailable")
        
        # Инициализация мониторинга
        logger.info("[LiveTrader] Initializing monitoring (Telegram)...")
        self.telegram = None
        self.alert_manager = None
        self.notify_config = {}
        if MONITORING_AVAILABLE:
            self._init_monitoring()
        else:
            logger.warning("[LiveTrader] Monitoring modules unavailable")
        
        # Отслеживание открытых позиций для Telegram уведомлений
        self.tracked_positions = {}  # {ticket: {symbol, direction, entry_time, ...}}
        
        # Устанавливаем Telegram в TrailingStopV4 после инициализации
        if hasattr(self, 'trailing_v4') and self.telegram:
            self.trailing_v4.telegram = self.telegram
            logger.info("[LiveTrader] Telegram notifier set to V4 Trailing Stop")
        
        logger.info("[LiveTrader] LiveTrader fully initialized")
        logger.info("="*80)
    
    def start(self) -> None:
        """Запуск трейдера (для совместимости)."""
        pass
    
    def load_configs(self) -> None:
        """Загрузка конфигурационных файлов."""
        import yaml
        config_path = Path(self.config_dir)
        
        # Загружаем MT5 конфиг
        mt5_config_path = config_path / 'mt5.yaml'
        if mt5_config_path.exists():
            with open(mt5_config_path, 'r') as f:
                self.mt5_config = yaml.safe_load(f)
        else:
            self.mt5_config = {}
        
        # Загружаем конфиг инструментов
        instruments_config_path = config_path / 'instruments.yaml'
        if instruments_config_path.exists():
            with open(instruments_config_path, 'r') as f:
                self.instruments_config = yaml.safe_load(f)
        else:
            self.instruments_config = {}
        
        # Загружаем конфиг портфеля
        portfolio_config_path = config_path / 'portfolio.yaml'
        if portfolio_config_path.exists():
            with open(portfolio_config_path, 'r') as f:
                self.portfolio_config = yaml.safe_load(f)
        else:
            self.portfolio_config = {}
        
        # Загружаем trading.yaml (для RiskManager и других настроек)
        trading_config_path = config_path / 'trading.yaml'
        if trading_config_path.exists():
            with open(trading_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
    
    def _is_trading_enabled_for_instrument(self, symbol: str) -> bool:
        """Проверить включена ли торговля для инструмента."""
        try:
            instrument_config = self.instruments_config.get('instruments', {}).get(symbol, {})
            # Проверяем оба флага: enabled (общий) и trading_enabled (торговля)
            is_enabled = instrument_config.get('enabled', False)
            is_trading = instrument_config.get('trading_enabled', True)
            
            if not is_enabled:
                logger.debug(f"[TRADE] {symbol} instrument disabled")
                return False
            
            if not is_trading:
                logger.debug(f"[TRADE] {symbol} trading disabled (analysis only)")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"[TRADE] Failed to check trading config for {symbol}: {e}")
            return True  # По умолчанию разрешаем если не смогли проверить
    
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
                            config_file = get_data_path('config.json')
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
                                        logger.info(f"[Strategy] ⚙️ Применены кастомные настройки для {symbol}: "
                                                  f"trades={strategy.max_daily_trades}, loss={strategy.max_daily_loss}%, "
                                                  f"ATR=[{strategy.min_atr_threshold}-{strategy.max_atr_threshold}]")
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
                logger.warning("📱 [TELEGRAM] Config not found at config/telegram.yaml")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            tg_config = config.get('telegram', {})
            enabled = tg_config.get('enabled', False)
            bot_token = tg_config.get('bot_token', '').strip()
            chat_id = tg_config.get('chat_id', '').strip()
            
            logger.info(f"📱 [TELEGRAM] Config loaded: enabled={enabled}, token_len={len(bot_token)}, chat_id={chat_id}")
            
            if not enabled:
                logger.info("📱 [TELEGRAM] Notifications DISABLED in config (enabled: false)")
                return
            
            if not bot_token or not chat_id:
                logger.error(f"📱 [TELEGRAM] ❌ Cannot initialize: Missing credentials!")
                logger.error(f"📱 [TELEGRAM]    bot_token: {'EMPTY' if not bot_token else f'{len(bot_token)} chars'}")
                logger.error(f"📱 [TELEGRAM]    chat_id: {'EMPTY' if not chat_id else chat_id}")
                logger.error(f"📱 [TELEGRAM]    Please configure in Settings -> Telegram tab")
                return
            
            # Create TelegramNotifier
            self.telegram = TelegramNotifier(
                token=bot_token,
                chat_id=chat_id
            )
            self.notify_config = tg_config.get('notify', {})
            
            if self.telegram.enabled:
                logger.info("📱 [TELEGRAM] ✅ Notifications ENABLED and ready!")
                logger.info(f"📱 [TELEGRAM]    Notify on trade_opened: {self.notify_config.get('trade_opened', True)}")
                logger.info(f"📱 [TELEGRAM]    Notify on trade_closed: {self.notify_config.get('trade_closed', True)}")
                logger.info(f"📱 [TELEGRAM]    Notify on startup: {self.notify_config.get('startup', True)}")
            else:
                logger.error("📱 [TELEGRAM] ❌ Notifier created but NOT enabled (check token/chat_id)")
            
            # AlertManager
            self.alert_manager = AlertManager()
            
            # Обновляем telegram в AI Signal Manager если он был создан ранее
            if self.ai_signal_manager and self.telegram:
                self.ai_signal_manager.telegram = self.telegram
                logger.info("[LiveTrader] Telegram notifier set to AI Signal Manager")
            
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
            logger.error(f"📱 [TELEGRAM] Failed to init monitoring: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def init_filters(self):
        """Инициализация фильтров."""
        # Инициализация GPT фильтра
        self.gpt_filter = None
        
        # Проверяем конфиг на enabled флаг
        try:
            import yaml
            with open('config/ai.yaml', 'r', encoding='utf-8') as f:
                ai_config = yaml.safe_load(f)
                news_filter_enabled = ai_config.get('news_filter', {}).get('enabled', False)
        except Exception as e:
            logger.warning(f"Failed to load news_filter config: {e}")
            news_filter_enabled = False
        
        if not news_filter_enabled:
            logger.info("📰 [NEWS FILTER] DISABLED by config (news_filter.enabled=false)")
        elif self.enable_gpt and GPT_AVAILABLE and news_filter_enabled:
            try:
                self.gpt_filter = GPTNewsFilter()
                logger.info("📰 [NEWS FILTER] ENABLED")
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
    
    def _check_trading_hours(self) -> bool:
        """
        Проверить разрешено ли торговать сейчас
        
        Правила:
        - ЗАПРЕТ: 23:30 - 01:00 (каждый день) - Strict night ban
        - РАЗРЕШЕНО: Понедельник 01:00 - Пятница 21:00
        - ЗАПРЕТ: Суббота, Воскресенье
        
        Returns:
            True если торговля разрешена
        """
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        minute = now.minute
        
        # Проверка выходных
        if weekday >= 5:  # Saturday=5, Sunday=6
            if weekday == 5:
                logger.debug(f"[Trading Hours] Saturday - trading blocked")
            else:
                logger.debug(f"[Trading Hours] Sunday - trading blocked")
            return False
        
        # Проверка времени недели
        if weekday == 0 and hour < 1:  # Monday before 01:00
            logger.debug(f"[Trading Hours] Monday before 01:00 - trading blocked")
            return False
        
        if weekday == 4 and hour >= 21:  # Friday after 21:00
            logger.debug(f"[Trading Hours] Friday after 21:00 - trading blocked")
            return False
        
        # Проверка строгого запрета 23:30-01:00 (Strict night ban)
        if hour == 23 and minute >= 30:
            logger.debug(f"[Trading Hours] Strict night ban (23:30-01:00) - trading blocked")
            return False
        if hour == 0:  # 00:00-00:59
            logger.debug(f"[Trading Hours] Strict night ban (23:30-01:00) - trading blocked")
            return False
        
        return True
    
    def check_signals(self):
        """Проверка сигналов для всех стратегий."""
        # Проверка времени торговли
        if not self._check_trading_hours():
            logger.debug("[LiveTrader] Trading blocked by schedule")
            return []
        
        signals = []
        
        # Проверяем AI сигналы ПЕРЕД проверкой позиций (AI сигналы сохраняются и ждут)
        if self.ai_signal_manager:
            logger.debug("[LiveTrader] Checking AI signals...")
            ai_signals = self._check_ai_signals()
            if ai_signals:
                logger.info(f"[LiveTrader] Found {len(ai_signals)} AI signals")
                signals.extend(ai_signals)
                
                # КРИТИЧНО: Проверяем нет ли открытой позиции ПЕРЕД исполнением
                if self.executor and self.executor.has_position():
                    logger.warning("[LiveTrader] Position already open - AI signals saved but NOT executed yet")
                    return signals  # Сигналы сохранены, исполним после закрытия позиции
                
                # КРИТИЧНО: Проверяем доступность GPT перед торговлей
                if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                    analyst = getattr(self.analyst_scheduler, 'analyst', None)
                    if analyst and not analyst.is_gpt_available():
                        logger.error("[LiveTrader] 🚫 GPT connection DISABLED - AI trading blocked")
                        logger.warning("[LiveTrader] Recovery in progress... waiting for GPT reconnection")
                        return signals  # Не торгуем пока GPT недоступен
                
                # Исполняем AI сигналы (только один раз здесь)
                if self.enable_trading:
                    for ai_signal in ai_signals:
                        symbol = ai_signal.get('symbol')
                        logger.info(f"[LiveTrader] Executing AI signal for {symbol}")
                        self.execute_trade(symbol, ai_signal)
                        break  # ← ВАЖНО: Только 1 сделка за раз
            else:
                logger.debug("[LiveTrader] No triggered AI signals found")
        else:
            logger.debug("[LiveTrader] AI signal manager not available")
        
        # Проверка обычных стратегий: SKIP если есть позиция
        if self.executor and self.executor.has_position():
            logger.debug("[LiveTrader] Position already open - skipping strategy signal checks")
            return signals
        
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
                    
                    if filtered_signal:
                        # Apply AI risk multiplier
                        filtered_signal = self._apply_ai_risk_multiplier(symbol, filtered_signal)
                        
                        direction = "BUY" if filtered_signal.get('direction') == 'long' else "SELL"
                        signals.append(f"{symbol}: {direction} @ {filtered_signal.get('entry_price', 0):.5f}")
                        
                        # Если разрешена торговля, открываем сделку
                        if self.enable_trading:
                            self.execute_trade(symbol, filtered_signal)
                # Removed: NOT valid signal logging - too spammy in logs
            
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
            # Только в файл лог, не спамить консоль
            logger.debug(f"Failed to load data for {symbol}: {e}")
            logger.debug("Backtest data file not found - normal for live trading")
            return None, None
    
    def process_signal(self, instrument: str, signal: dict, h1_data=None, m15_data=None, m15_idx=None):
        """Обработка сигнала с ML и GPT фильтрами."""
        
        if not signal.get('valid', False):
            logger.debug(f"[LiveTrader] Signal not valid, skipping")
            return None
        
        # 1. ML проверка (если есть данные)
        if h1_data is not None and m15_data is not None and m15_idx is not None:
            ml_ok, ml_prob = self.check_ml_filter(h1_data, m15_data, m15_idx, signal)
            if not ml_ok:
                logger.info(f"[LiveTrader] Signal filtered by ML (prob: {ml_prob:.1%})")
                return None
        
        # 2. GPT проверка
        gpt_ok, gpt_reason = self.check_gpt_filter(instrument)
        if not gpt_ok:
            logger.info(f"[LiveTrader] Signal filtered by GPT: {gpt_reason}")
            return None
        
        # Сигнал прошел все фильтры - возвращаем обработанный dict
        direction = "BUY" if signal.get('direction') == 'long' else "SELL"
        entry_price = signal.get('entry_price', signal.get('entry', 0))
        sl = signal.get('sl', signal.get('stop_loss', 0))
        tp = signal.get('tp', signal.get('take_profit', 0))
        
        processed_signal = {
            'symbol': instrument,
            'direction': signal.get('direction'),
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'valid': True
        }
        
        # Копируем дополнительные поля если есть
        for key in ['confidence', 'reasoning', 'source', 'ai_signal_id', 'timestamp']:
            if key in signal:
                processed_signal[key] = signal[key]
        
        logger.info(f"[LiveTrader] ✅ Signal passed all filters: {direction} @ {entry_price:.5f} (SL: {sl:.5f}, TP: {tp:.5f})")
        return processed_signal
    
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
            # КРИТИЧНО: Проверяем статус сигнала - prevent duplicate trades
            signal_id = signal.get('ai_signal_id')
            if signal_id and self.ai_signal_manager:
                # Проверяем что сигнал ready для исполнения (pending или triggered)
                # 'pending' = ждет триггера, 'triggered' = цена достигла entry
                # 'filled' = уже исполнен (БЛОКИРУЕМ)
                active_signals = self.ai_signal_manager.get_active_signals(symbol=symbol)
                signal_found = False
                for s in active_signals:
                    if s.get('id') == signal_id:
                        status = s.get('status')
                        if status == 'filled':
                            logger.warning(f"[TRADE] Signal {signal_id} already filled - ignoring")
                            return None
                        if status not in ['pending', 'triggered']:
                            logger.warning(f"[TRADE] Signal {signal_id} has status {status} - ignoring")
                            return None
                        signal_found = True
                        break
                
                if not signal_found:
                    logger.warning(f"[TRADE] Signal {signal_id} not found in active signals - ignoring")
                    return None
            
            # Safety: Check GPT availability before trading
            if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                analyst = getattr(self.analyst_scheduler, 'analyst', None)
                if analyst and not analyst.is_gpt_available():
                    logger.error(f"[TRADE] 🚫 Cannot execute {symbol} trade - GPT connection disabled")
                    logger.warning("[TRADE] Trading blocked until GPT recovery completes")
                    return None
            
            # КРИТИЧНО: Проверяем нет ли уже открытой позиции
            if self.executor.has_position():
                logger.warning(f"[TRADE] Position already open - ignoring new signal for {symbol}")
                return None
            
            # Проверяем включена ли торговля для этого инструмента
            if not self._is_trading_enabled_for_instrument(symbol):
                logger.info(f"[TRADE] Trading disabled for {symbol} in config - signal ignored")
                return None
            
            result = self.executor.execute_signal(symbol, signal)
            
            if result:
                logger.info(f"Trade executed for {symbol}: {result}")
                
                # Извлекаем данные из сигнала (используется в нескольких местах)
                direction = signal.get('direction', '').upper()
                if direction.lower() == 'long':
                    direction = 'BUY'
                elif direction.lower() == 'short':
                    direction = 'SELL'
                
                entry = signal.get('entry_price', 0)
                sl = signal.get('sl', signal.get('stop_loss', 0))
                tp = signal.get('tp', signal.get('take_profit', 0))
                lot_size = signal.get('lot_size', signal.get('volume', 0.01))
                
                # Отмечаем AI сигнал как исполненный (если есть)
                if self.ai_signal_manager and signal.get('ai_signal_id'):
                    try:
                        filled_price = signal.get('entry_price', 0)
                        self.ai_signal_manager.mark_signal_filled(
                            signal_id=signal['ai_signal_id'],
                            filled_price=filled_price
                        )
                    except Exception as e:
                        logger.error(f"[TRADE] Failed to mark AI signal as filled: {e}")
                
                # Отправка Telegram уведомления
                if self.telegram:
                    try:
                        # Определяем режим торговли
                        from src.core.bot_manager import BotManager
                        bot_manager = BotManager()
                        trading_mode = bot_manager.trading_mode
                        
                        reasoning = signal.get('reasoning', '')
                        confidence = signal.get('confidence', 0) * 100  # Convert to %
                        
                        # Отправляем уведомление
                        self.telegram.send_trade_opened(
                            symbol=symbol,
                            direction=direction,
                            lot=lot_size,
                            entry=entry,
                            sl=sl,
                            tp=tp,
                            mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                            reasoning=reasoning,
                            confidence=confidence
                        )
                        logger.info(f"[Telegram] Trade opened notification sent for {symbol}")
                    except Exception as tg_error:
                        logger.error(f"[Telegram] Failed to send trade opened notification: {tg_error}")
                
                # Запоминаем позицию для отслеживания закрытия и трейлинга
                try:
                    # Получаем последнюю открытую позицию из MT5
                    positions = self.mt5_connector.positions_get(symbol=symbol)
                    if positions and len(positions) > 0:
                        pos = positions[-1]  # Последняя открытая позиция
                        self.tracked_positions[pos.ticket] = {
                            'symbol': symbol,
                            'direction': direction,
                            'entry_price': entry,
                            'sl': sl,
                            'current_sl': sl,  # Инициализируем текущий SL
                            'tp': tp,
                            'entry_time': datetime.now(),
                            'volume': lot_size,
                            'sl_moved': False,  # Флаг что SL еще не перемещен
                            'breakeven_moved': False  # Флаг что breakeven еще не выполнен
                        }
                        logger.info(f"[Position] Tracking #{pos.ticket} for trailing/close notification")
                except Exception as track_error:
                    logger.error(f"[Position] Failed to track position: {track_error}")
                
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {e}")
    
    def check_trailing_stop(self):
        """
        V4 Trailing Stop - Fixed parameters for M5 scalping.
        
        Uses TrailingStopV4 module with fixed activation/stop levels.
        """
        # Check if trailing stop enabled in config
        trailing_config = self.config.get('trading', {}).get('trailing_stop', {})
        if not trailing_config.get('enabled', False):
            # Log once that trailing is disabled (avoid spam)
            if not hasattr(self, '_trailing_disabled_logged'):
                logger.info("[V4-Trailing] ⛔ Trailing stop DISABLED in settings")
                self._trailing_disabled_logged = True
            return
        
        # Reset flag when enabled (for next disable)
        if hasattr(self, '_trailing_disabled_logged'):
            logger.info("[V4-Trailing] ✅ Trailing stop ENABLED (30% activation, 50% stop)")
            delattr(self, '_trailing_disabled_logged')
        
        if not self.tracked_positions:
            return
        
        try:
            # V4: Use new simplified trailing stop handler
            if hasattr(self, 'trailing_v4'):
                self.trailing_v4.check_and_apply(self.tracked_positions)
            else:
                logger.warning("[LiveTrader] V4 trailing stop handler not initialized")
        
        except Exception as e:
            logger.error(f"[V4-Trailing] Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _modify_position_sl(self, ticket: int, new_sl: float, symbol: str = None) -> bool:
        """Изменяет Stop Loss открытой позиции."""
        try:
            # Получаем текущую позицию
            positions = self.mt5_connector.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                logger.warning(f"[TrailingSL] Position #{ticket} not found")
                return False
            
            position = positions[0]
            symbol = symbol or position.symbol
            
            # Нормализуем SL по digit symbol
            symbol_info = self.mt5_connector.symbol_info(symbol)
            if symbol_info:
                new_sl = round(new_sl, symbol_info.digits)
            
            # Формируем запрос на модификацию
            request = {
                "action": self.mt5_connector.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": new_sl,
                "tp": position.tp,
                "magic": 123456,
                "comment": "Trailing SL",
            }
            
            # Отправляем запрос
            result = self.mt5_connector.order_send(request)
            
            if result and result.retcode == self.mt5_connector.TRADE_RETCODE_DONE:
                logger.info(f"[TrailingSL] ✅ MT5 confirmed SL modification for #{ticket}")
                return True
            else:
                error_code = result.retcode if result else "No result"
                error_msg = result.comment if result else "No response from MT5"
                logger.error(f"[TrailingSL] ❌ Failed to modify SL for #{ticket}: [{error_code}] {error_msg}")
                return False
        
        except Exception as e:
            logger.error(f"[TrailingSL] Error modifying SL: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def check_closed_positions(self):
        """Проверяет закрытые позиции и отправляет Telegram уведомления."""
        if not self.telegram:
            return
        
        # Import datetime at function start to avoid UnboundLocalError
        from datetime import datetime, timedelta
        import time
        
        try:
            # Проходим по отслеживаемым позициям (если они есть)
            for ticket in list(self.tracked_positions.keys()):
                pos_info = self.tracked_positions[ticket]
                
                # Пропускаем если уже обработали закрытие
                if pos_info.get('notification_sent', False):
                    continue
                
                # Проверяем есть ли позиция в открытых
                position = self.mt5_connector.positions_get(ticket=ticket)
                
                if not position or len(position) == 0:
                    # Позиция закрыта - проверяем историю
                    logger.info(f"[Closed] Position #{ticket} CLOSED - fetching history...")
                    
                    # Даём MT5 время записать в историю (500ms)
                    time.sleep(0.5)
                    
                    # Ищем в истории сделок (расширенный диапазон - 24 часа)
                    history = self.mt5_connector.history_deals_get(
                        datetime.now() - timedelta(hours=24),
                        datetime.now()
                    )
                    
                    deal_found = False
                    closing_deal = None
                    
                    if history:
                        for deal in history:
                            if deal.position_id == ticket and deal.entry == 1:  # 1 = OUT
                                deal_found = True
                                closing_deal = deal
                                logger.info(f"[Closed] Found closing deal for #{ticket}, profit=${deal.profit:.2f}")
                                break
                    
                    if deal_found and closing_deal:
                        # Нашли сделку закрытия - отправляем полный отчёт
                        pos_info = self.tracked_positions[ticket]
                        
                        # Вычисляем profit напрямую из MT5
                        profit = closing_deal.profit if hasattr(closing_deal, 'profit') else 0.0
                        
                        # Вычисляем длительность
                        duration = datetime.now() - pos_info['entry_time']
                        hours = int(duration.total_seconds() // 3600)
                        minutes = int((duration.total_seconds() % 3600) // 60)
                        duration_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
                        
                        # Вычисляем пипсы
                        price_diff = abs(closing_deal.price - pos_info['entry_price'])
                        pips = price_diff * 10000  # для forex
                        if pos_info['symbol'] == 'XAUUSD':
                            pips = price_diff * 100  # для золота
                        
                        # Определяем причину закрытия ПРАВИЛЬНО
                        # Сравниваем цену закрытия с TP и SL
                        close_price = closing_deal.price
                        entry_price = pos_info['entry_price']
                        sl_price = pos_info.get('sl', 0)
                        tp_price = pos_info.get('tp', 0)
                        
                        # Определяем насколько близко к TP/SL закрылась сделка
                        tp_distance = abs(close_price - tp_price) if tp_price else 999999
                        sl_distance = abs(close_price - sl_price) if sl_price else 999999
                        
                        # Если закрылась ближе к TP - значит взяла TP
                        # Если ближе к SL - значит взяла SL
                        # Порог - 0.5$ для XAUUSD
                        CLOSE_THRESHOLD = 0.5
                        
                        if profit > 1.0:  # Прибыльная сделка
                            if tp_distance < CLOSE_THRESHOLD:
                                result_reason = "Take Profit"
                            else:
                                result_reason = "Trailing Stop"
                        elif profit < -1.0:  # Убыточная сделка
                            if sl_distance < CLOSE_THRESHOLD:
                                result_reason = "Stop Loss"
                            else:
                                result_reason = "Manual Close"
                        else:  # Около нуля
                            result_reason = "Breakeven"
                        
                        # Получаем режим торговли
                        from src.core.bot_manager import BotManager
                        bot_manager = BotManager()
                        trading_mode = bot_manager.trading_mode
                        
                        # Отправляем уведомление
                        self.telegram.send_trade_closed(
                            symbol=pos_info['symbol'],
                            direction=pos_info['direction'],
                            profit=profit,
                            pips=pips,
                            duration=duration_str,
                            mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                            result_reason=result_reason
                        )
                        
                        logger.info(f"[Telegram] Trade closed notification sent for #{ticket}: {result_reason}, profit=${profit:.2f}")
                        
                        # Удаляем из отслеживаемых
                        del self.tracked_positions[ticket]
                    
                    else:
                        # Не нашли в истории - отправляем уведомление с примерными данными
                        pos_info = self.tracked_positions[ticket]
                        logger.warning(f"[Closed] Deal for #{ticket} not found in history - sending notification with estimated data")
                        
                        # Пытаемся рассчитать profit по текущей цене
                        estimated_profit = 0.0
                        estimated_pips = 0.0
                        duration_str = "N/A"
                        try:
                            # Получаем текущую цену
                            tick = self.mt5_connector.symbol_info_tick(pos_info['symbol'])
                            if tick:
                                current_price = tick.bid if pos_info['direction'] == 'BUY' else tick.ask
                                entry_price = pos_info.get('entry_price', 0)
                                volume = pos_info.get('volume', 0.01)
                                open_time = pos_info.get('entry_time')
                                
                                # Рассчитываем длительность
                                if open_time:
                                    from datetime import datetime, timedelta
                                    # open_time уже является datetime объектом из tracked_positions
                                    if isinstance(open_time, str):
                                        open_dt = datetime.fromisoformat(open_time)
                                    elif isinstance(open_time, datetime):
                                        open_dt = open_time
                                    else:
                                        # Если это timestamp (int/float)
                                        open_dt = datetime.fromtimestamp(open_time)
                                    
                                    duration = datetime.now() - open_dt
                                    minutes = int(duration.total_seconds() / 60)
                                    seconds = int(duration.total_seconds() % 60)
                                    duration_str = f"{minutes}m {seconds}s"
                                
                                if entry_price > 0:
                                    # Рассчитываем profit
                                    if pos_info['direction'] == 'BUY':
                                        price_diff = current_price - entry_price
                                    else:  # SELL
                                        price_diff = entry_price - current_price
                                    
                                    # ИСПРАВЛЕНО: Правильный расчет для XAUUSD
                                    # Contract size = 100 унций, но формула должна быть:
                                    # profit = price_diff * volume * contract_size / 100
                                    # Для volume=0.01: price_diff * 0.01 * 100 = price_diff * 1.0
                                    # Например: price_diff = -2.43, volume = 0.01 → profit = -2.43
                                    contract_size = 100  # XAUUSD = 100 унций на лот
                                    lot_to_oz = volume * contract_size  # 0.01 lot = 1 oz
                                    estimated_profit = price_diff * lot_to_oz
                                    estimated_pips = price_diff * 100  # 1 pip = $0.01
                                    logger.info(f"[Closed] Estimated profit: ${estimated_profit:.2f} ({estimated_pips:.1f} pips), duration: {duration_str}")
                        except Exception as e:
                            logger.error(f"[Closed] Failed to calculate estimated profit: {e}")
                        
                        # Отправляем уведомление
                        if self.telegram and self.notify_config.get('trade_closed', True):
                            from src.core.bot_manager import BotManager
                            bot_manager = BotManager()
                            trading_mode = bot_manager.trading_mode
                            
                            self.telegram.send_trade_closed(
                                symbol=pos_info['symbol'],
                                direction=pos_info['direction'],
                                profit=estimated_profit,
                                pips=estimated_pips,
                                duration=duration_str,
                                mode='pure_ai' if trading_mode == 'pure_ai' else 'strategy',
                                result_reason="Trailing Stop"
                            )
                            logger.info(f"[Telegram] Trade closed notification sent for #{ticket} (estimated data)")
                        
                        # Сохраняем сделку в историю для статистики
                        try:
                            from pathlib import Path
                            import json
                            from datetime import datetime
                            
                            trades_file = Path('data/trades_history.json')
                            trades = []
                            if trades_file.exists():
                                with open(trades_file, 'r', encoding='utf-8') as f:
                                    trades = json.load(f)
                            
                            trade_record = {
                                'ticket': ticket,
                                'symbol': pos_info['symbol'],
                                'type': pos_info['direction'],
                                'volume': pos_info.get('volume', 0.01),
                                'entry': pos_info.get('entry_price', 0),
                                'pnl': estimated_profit,
                                'pips': estimated_pips,
                                'duration': duration_str,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'result': 'Trailing Stop',
                                'mode': 'pure_ai'
                            }
                            
                            trades.append(trade_record)
                            
                            trades_file.parent.mkdir(exist_ok=True)
                            with open(trades_file, 'w', encoding='utf-8') as f:
                                json.dump(trades, f, indent=2, ensure_ascii=False)
                            
                            logger.info(f"[History] Trade #{ticket} saved to history: ${estimated_profit:.2f}")
                            
                            # Обновляем статистику в bot_manager
                            from src.core.bot_manager import BotManager
                            bot_manager = BotManager()
                            bot_manager.load_stats()  # Перечитываем из файла
                            
                        except Exception as e:
                            logger.error(f"[History] Failed to save trade: {e}")
                        
                        # Удаляем из tracked
                        del self.tracked_positions[ticket]
                    
                    # AUTO-REQUERY: Trigger GPT analysis 5 minutes after position close
                    if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                        logger.info("[LiveTrader] 🔄 Position closed - triggering GPT analysis in 5 minutes")
                        self.analyst_scheduler.trigger_immediate_analysis(
                            symbol=pos_info['symbol'],
                            reason="position_closed",
                            cooldown_minutes=5  # Wait 5 minutes before next analysis
                        )
            
            # FALLBACK: Если нет tracked позиций, но есть закрытые сделки в MT5
            # Проверяем последние сделки и запускаем анализ если нужно
            if not self.tracked_positions:
                # Нет отслеживаемых позиций - проверяем MT5 напрямую
                current_positions = self.mt5_connector.positions_get()
                if not current_positions or len(current_positions) == 0:
                    # Нет открытых позиций в MT5
                    # Проверяем есть ли активные сигналы
                    has_active_signals = False
                    if self.ai_signal_manager:
                        active_signals = self.ai_signal_manager.get_active_signals()
                        has_active_signals = len(active_signals) > 0
                    
                    # Если нет позиций и нет сигналов - запускаем анализ через 5 минут
                    if not has_active_signals:
                        if hasattr(self, 'analyst_scheduler') and self.analyst_scheduler:
                            # Проверяем когда был последний анализ
                            last_analysis_time = getattr(self, '_last_fallback_analysis_time', None)
                            current_time = datetime.now()
                            
                            if last_analysis_time is None or (current_time - last_analysis_time).total_seconds() > 300:  # 5 минут
                                logger.info("[LiveTrader] 🔄 FALLBACK: No positions and no signals - triggering analysis")
                                self.analyst_scheduler.trigger_immediate_analysis(
                                    symbol='XAUUSD',
                                    reason="fallback_no_positions",
                                    cooldown_minutes=5
                                )
                                self._last_fallback_analysis_time = current_time
        
        except Exception as e:
            logger.error(f"[Telegram] Failed to check closed positions: {e}")
    
    def save_trade(self, trade: dict):
        """Сохраняет сделку в историю."""
        import json
        from pathlib import Path
        
        trades_file = get_data_path('trades_history.json')
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
            logger.debug("[AI] Signal manager not available")
            return []
        
        triggered_signals = []
        
        try:
            import MetaTrader5 as mt5
            current_time = datetime.now()
            
            logger.debug(f"[AI] Checking signals at {current_time.strftime('%H:%M:%S')}")
            
            # Проверяем каждый символ
            for symbol in ['XAUUSD', 'EURUSD']:
                # Получаем текущую цену
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    logger.debug(f"[AI] No tick data for {symbol}")
                    continue
                
                current_price = (tick.bid + tick.ask) / 2
                logger.debug(f"[AI] {symbol} current price: {current_price}")
                
                # Проверяем триггеры
                signals = self.ai_signal_manager.check_triggers(
                    current_price=current_price,
                    symbol=symbol,
                    current_time=current_time
                )
                
                logger.debug(f"[AI] {symbol} found {len(signals) if signals else 0} triggered signals")
                
                if signals:
                    for ai_signal in signals:
                        # Конвертируем AI сигнал в формат стратегии
                        strategy_signal = self._convert_ai_signal_to_strategy(ai_signal)
                        
                        logger.info(
                            f"[AI-Signal] Triggered: {symbol} {ai_signal.type} "
                            f"@ {ai_signal.entry_price} (conf: {ai_signal.confidence}%)"
                        )
                        
                        # НЕ исполняем здесь - будет исполнено в основном цикле check_signals
                        # Это предотвращает двойной вход в сделку
                        
                        triggered_signals.append(strategy_signal)
        
        except Exception as e:
            logger.error(f"[AI] Signal check failed: {e}", exc_info=True)
        
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
            'stop_loss': ai_signal.stop_loss,  # Дублируем для совместимости
            'take_profit': ai_signal.take_profit,
            'confidence': ai_signal.confidence / 100.0,  # 0-1 scale
            'reasoning': ai_signal.reasoning,
            'source': 'AI-GPT',
            'ai_signal_id': ai_signal.id,
            'valid': True,  # AI сигналы всегда валидны после проверки
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
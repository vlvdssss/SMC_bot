#!/usr/bin/env python3
"""  
Pure AI Trader - Trading based solely on GPT signals

Режим торговли только по сигналам ChatGPT:
- Анализ каждые 30 минут (по умолчанию)
- Скриншоты M5, M15
- Новости с внешних источников
- GPT генерирует готовые сигналы
- Дедупликация по entry price
- Таймфрейм исполнения: M5/M15
- Символы: XAUUSD, EURUSD
- Максимум 1 позиция на инструмент
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import MetaTrader5 as mt5

from src.core.logger import logger
from src.ai.market_analyst import MarketAnalystService
from src.ai.signal_manager import AISignalManager


class PureAITrader:
    """
    Pure AI Trading Mode - торговля только по GPT сигналам.
    
    Логика:
    1. Каждые 30 минут (по умолчанию) запускает анализ для XAUUSD и EURUSD
    2. GPT анализирует скриншоты M5/M15 + новости
    3. Генерирует сигналы с entry/SL/TP
    4. SignalManager проверяет дубликаты и управляет TTL
    5. Executor исполняет сделки на M5/M15 таймфрейме
    6. Максимум 1 открытая позиция на инструмент
    """
    
    # Конфигурация
    SYMBOLS = ["XAUUSD"]  # TEMPORARY: Только золото, EURUSD отключен
    ANALYSIS_INTERVAL = 30 * 60  # IMPROVED: 30 minutes instead of 2 hours (more frequent analysis)
    MIN_CONFIDENCE = 70  # IMPROVED: Lowered from 75 to 70 (balanced approach)
    MAX_TRADES_PER_DAY = 5  # Максимум сделок в день
    COOLDOWN_MINUTES = 30  # IMPROVED: Пауза 30 мин после сделки (вместо 2 часов)
    
    def __init__(self, api_key: str = None, executor=None, analysis_interval_hours: int = None, telegram_notifier=None):
        """
        Initialize Pure AI Trader.
        
        Args:
            api_key: OpenAI API key
            executor: Executor instance for trade execution
            analysis_interval_hours: Интервал анализа в часах (по умолчанию 5)
            telegram_notifier: TelegramNotifier для уведомлений о price invalidation
        """
        self.api_key = api_key
        self.executor = executor
        
        # Применяем пользовательский интервал если задан
        if analysis_interval_hours is not None:
            self.ANALYSIS_INTERVAL = analysis_interval_hours * 60 * 60
        
        # Инициализация сервисов
        self.analyst = MarketAnalystService(api_key=api_key)
        self.signal_manager = AISignalManager(telegram_notifier=telegram_notifier)
        
        # Состояние
        self.running = False
        self.thread = None
        self.last_cycle_time = None  # NEW: для отслеживания глобального цикла
        self.last_analysis_time = {}  # {symbol: datetime}
        self.daily_trades = {}  # {date: count}
        self.symbol_cooldown = {}  # {symbol: datetime}
        self.tracked_positions = {}  # NEW: {symbol: {ticket, entry_time, direction, entry_price}} - для мониторинга закрытий
        
        logger.info("[PureAI] Pure AI Trader initialized")
        logger.info(f"[PureAI] Symbols: {', '.join(self.SYMBOLS)}")
        logger.info(f"[PureAI] Analysis every {self.ANALYSIS_INTERVAL // 60} minutes")
        logger.info(f"[PureAI] Timeframes: M5, M15")
        logger.info(f"[PureAI] Max 1 position per symbol")
    
    def start(self):
        """Запуск Pure AI Trading режима."""
        if self.running:
            logger.warning("[PureAI] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        logger.info("[PureAI] ✅ Pure AI Trading mode STARTED")
    
    def stop(self):
        """Остановка Pure AI Trading режима."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("[PureAI] ⏸️ Pure AI Trading mode STOPPED")
    
    def _run_loop(self):
        """Главный цикл анализа."""
        logger.info("[PureAI] 🔄 Analysis loop started")
        
        # Первый анализ сразу при старте
        self._run_analysis_cycle()
        
        while self.running:
            try:
                # Мониторинг закрытых позиций
                self._check_closed_positions()
                
                # Ждем до следующего цикла
                next_analysis = self._get_next_analysis_time()
                wait_seconds = (next_analysis - datetime.now()).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"[PureAI] Next analysis at {next_analysis.strftime('%H:%M:%S')}")
                    time.sleep(min(wait_seconds, 60))  # Проверяем каждую минуту
                    continue
                
                # Запускаем анализ
                self._run_analysis_cycle()
                
            except Exception as e:
                logger.error(f"[PureAI] Error in main loop: {e}")
                time.sleep(60)
    
    def _get_next_analysis_time(self) -> datetime:
        """Вычисляет время следующего анализа (каждые ANALYSIS_INTERVAL секунд)."""
        now = datetime.now()
        
        # Если последний цикл не был, запускаем сразу
        if self.last_cycle_time is None:
            return now
        
        # Следующий анализ через ANALYSIS_INTERVAL секунд после последнего
        next_time = self.last_cycle_time + timedelta(seconds=self.ANALYSIS_INTERVAL)
        
        # Если уже прошло время - запускаем сразу
        if next_time <= now:
            return now
        
        return next_time
    
    def _run_analysis_cycle(self):
        """Запуск полного цикла анализа для всех символов."""
        try:
            logger.info("=" * 60)
            logger.info(f"[PureAI] 🧠 Starting analysis cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            # Проверяем лимит сделок в день
            today = datetime.now().date()
            if not self._check_daily_limit(today):
                logger.warning(f"[PureAI] Daily trade limit reached ({self.MAX_TRADES_PER_DAY})")
                return
            
            # Анализируем каждый символ
            for symbol in self.SYMBOLS:
                try:
                    self._analyze_symbol(symbol)
                    time.sleep(5)  # Небольшая пауза между символами
                except Exception as e:
                    logger.error(f"[PureAI] Error analyzing {symbol}: {e}")
            
            # Сохраняем время завершения цикла
            self.last_cycle_time = datetime.now()
            logger.info("[PureAI] ✅ Analysis cycle completed")
            
        except Exception as e:
            logger.error(f"[PureAI] Error in analysis cycle: {e}")
    
    def _analyze_symbol(self, symbol: str):
        """
        Анализ одного символа и генерация сигнала.
        
        Args:
            symbol: Торговый символ (XAUUSD, EURUSD)
        """
        try:
            # Проверяем cooldown
            if not self._check_cooldown(symbol):
                # Показываем сколько осталось до следующего анализа
                if symbol in self.symbol_cooldown:
                    cooldown_end = self.symbol_cooldown[symbol]
                    remaining = (cooldown_end - datetime.now()).total_seconds() / 60
                    if remaining > 0:
                        logger.info(f"[PureAI] {symbol} in cooldown - next analysis in {remaining:.0f} minutes ({cooldown_end.strftime('%H:%M')})") 
                return
            
            logger.info(f"[PureAI] 📊 Analyzing {symbol}...")
            
            # Запускаем GPT анализ
            analysis = self.analyst.analyze_market(symbol)
            
            if not analysis:
                logger.warning(f"[PureAI] No analysis returned for {symbol}")
                return
            
            # Извлекаем данные
            summary = analysis.get('summary', {})
            signals = analysis.get('signals', [])
            blocks = analysis.get('trading_blocks', {})
            
            sentiment = summary.get('sentiment', 'neutral')
            confidence = summary.get('confidence', 0)
            
            logger.info(f"[PureAI] {symbol} → Sentiment: {sentiment.upper()}, Confidence: {confidence}%")
            
            # Проверяем блокировки
            if blocks.get('block_trading', False):
                reason = blocks.get('reason', 'Unknown')
                logger.warning(f"[PureAI] {symbol} BLOCKED: {reason}")
                
                # Устанавливаем блокировку в signal manager
                block_until = blocks.get('block_until')
                self.signal_manager.set_block(
                    block_type='hard_block',
                    reason=reason,
                    expires_at=block_until
                )
                return
            
            # Обрабатываем сигналы
            if not signals:
                logger.info(f"[PureAI] {symbol} → No signals generated")
                return
            
            for signal_data in signals:
                self._process_signal(symbol, signal_data, analysis)
            
            # Обновляем время последнего анализа
            self.last_analysis_time[symbol] = datetime.now()
            
        except Exception as e:
            logger.error(f"[PureAI] Error analyzing {symbol}: {e}", exc_info=True)
    
    def _process_signal(self, symbol: str, signal_data: Dict, analysis: Dict):
        """
        Обработка и создание сигнала.
        
        Args:
            symbol: Trading symbol
            signal_data: Данные сигнала от GPT
            analysis: Полный анализ
        """
        try:
            # Извлекаем параметры
            signal_type = signal_data.get('type', '').upper()
            entry_price = float(signal_data.get('entry_price', 0))
            stop_loss = float(signal_data.get('stop_loss', 0))
            take_profit = float(signal_data.get('take_profit', 0))
            confidence = float(signal_data.get('confidence', 0))
            reasoning = signal_data.get('reasoning', 'No reason provided')
            
            # Валидация
            if not signal_type or signal_type not in ['BUY', 'SELL']:
                logger.warning(f"[PureAI] Invalid signal type: {signal_type}")
                return
            
            if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
                logger.warning(f"[PureAI] Invalid prices: Entry={entry_price}, SL={stop_loss}, TP={take_profit}")
                return
            
            # Confidence filtering removed - accept all valid signals
            logger.info(f"[PureAI] {symbol} signal confidence: {confidence}% (filtering disabled)")
            
            # Проверяем дубликаты через signal manager
            if self.signal_manager.is_duplicate_signal(
                symbol=symbol,
                signal_type=signal_type,
                entry_price=entry_price
            ):
                logger.info(f"[PureAI] {symbol} {signal_type} signal is duplicate, skipping")
                return
            
            # Создаем сигнал
            signal = self.signal_manager.create_signal_from_analysis(
                symbol=symbol,
                analysis=analysis,
                signal_data=signal_data
            )
            
            if signal:
                logger.info(f"[PureAI] ✅ {symbol} {signal_type} signal created")
                logger.info(f"         Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                logger.info(f"         Confidence: {confidence}%, R:R: {signal_data.get('risk_reward', 0):.2f}")
                logger.info(f"         Reason: {reasoning}")
                
                # Обновляем счетчик сделок
                today = datetime.now().date()
                self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
                
                # Устанавливаем cooldown для символа (30 минут)
                cooldown_end = datetime.now() + timedelta(minutes=self.COOLDOWN_MINUTES)
                self.symbol_cooldown[symbol] = cooldown_end
                logger.info(f"[PureAI] ⏱️ {symbol} cooldown set - next analysis at {cooldown_end.strftime('%H:%M')} ({self.COOLDOWN_MINUTES} min)")
                
                # Сохраняем информацию о позиции для мониторинга закрытия
                self.tracked_positions[symbol] = {
                    'signal_type': signal_type,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': datetime.now(),
                    'cooldown_end': cooldown_end
                }
            
        except Exception as e:
            logger.error(f"[PureAI] Error processing signal: {e}", exc_info=True)
    
    def _check_closed_positions(self):
        """
        Проверка закрытых позиций и логирование завершения сделок.
        Вызывается каждую минуту в главном цикле.
        """
        if not self.tracked_positions:
            return
        
        if not self.executor or not hasattr(self.executor, 'has_position'):
            return
        
        try:
            # Проверяем каждую отслеживаемую позицию
            for symbol in list(self.tracked_positions.keys()):
                pos_info = self.tracked_positions[symbol]
                
                # Проверяем есть ли позиция в MT5
                has_pos = self.executor.has_position(symbol=symbol)
                
                if not has_pos:
                    # Позиция закрыта!
                    entry_time = pos_info['entry_time']
                    signal_type = pos_info['signal_type']
                    entry_price = pos_info['entry_price']
                    cooldown_end = pos_info.get('cooldown_end', datetime.now())
                    
                    # Вычисляем время держания позиции
                    duration = datetime.now() - entry_time
                    duration_str = f"{duration.seconds // 60}m" if duration.seconds < 3600 else f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
                    
                    # Вычисляем оставшийся кулдаун
                    remaining_cooldown = (cooldown_end - datetime.now()).total_seconds() / 60
                    
                    logger.info("=" * 60)
                    logger.info(f"[PureAI] 🏁 POSITION CLOSED: {symbol}")
                    logger.info(f"[PureAI]    Direction: {signal_type}")
                    logger.info(f"[PureAI]    Entry: {entry_price:.5f if 'EUR' in symbol else entry_price:.2f}")
                    logger.info(f"[PureAI]    Duration: {duration_str}")
                    
                    if remaining_cooldown > 0:
                        logger.info(f"[PureAI]    ⏱️ Cooldown active: next analysis in {remaining_cooldown:.0f} minutes (at {cooldown_end.strftime('%H:%M')})")
                    else:
                        logger.info(f"[PureAI]    ✅ Cooldown expired - symbol available for analysis")
                    
                    logger.info("=" * 60)
                    
                    # Удаляем из отслеживания
                    del self.tracked_positions[symbol]
                    
        except Exception as e:
            logger.error(f"[PureAI] Error checking closed positions: {e}")
    
    def _check_cooldown(self, symbol: str) -> bool:
        """
        Проверка cooldown для символа.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if no cooldown, False if in cooldown
        """
        if symbol not in self.symbol_cooldown:
            return True
        
        cooldown_end = self.symbol_cooldown[symbol]
        if datetime.now() >= cooldown_end:
            del self.symbol_cooldown[symbol]
            return True
        
        return False
    
    def _check_daily_limit(self, date) -> bool:
        """
        Проверка лимита сделок в день.
        
        Args:
            date: Дата для проверки
            
        Returns:
            True if under limit, False if limit reached
        """
        trades_today = self.daily_trades.get(date, 0)
        return trades_today < self.MAX_TRADES_PER_DAY
    
    def get_status(self) -> Dict:
        """
        Получить текущий статус Pure AI Trader.
        
        Returns:
            Словарь со статусом
        """
        today = datetime.now().date()
        
        status = {
            'running': self.running,
            'mode': 'Pure AI Trading',
            'symbols': self.SYMBOLS,
            'analysis_interval': f"{self.ANALYSIS_INTERVAL // 3600}h",
            'trades_today': self.daily_trades.get(today, 0),
            'max_trades_per_day': self.MAX_TRADES_PER_DAY,
            'last_analysis': {},
            'cooldowns': {}
        }
        
        # Последние анализы
        for symbol, timestamp in self.last_analysis_time.items():
            status['last_analysis'][symbol] = timestamp.strftime('%H:%M:%S')
        
        # Активные cooldown'ы
        for symbol, cooldown_end in self.symbol_cooldown.items():
            remaining = (cooldown_end - datetime.now()).total_seconds() / 60
            if remaining > 0:
                status['cooldowns'][symbol] = f"{remaining:.0f} min"
        
        return status
    
    def get_next_analysis_time(self) -> str:
        """
        Получить время следующего анализа в человеко-читаемом формате.
        
        Returns:
            Строка с временем следующего анализа
        """
        try:
            next_time = self._get_next_analysis_time()
            now = datetime.now()
            
            if next_time <= now:
                return "сейчас"
            
            delta = next_time - now
            delta_minutes = int(delta.total_seconds() / 60)
            
            if delta_minutes < 60:
                return f"через {delta_minutes} мин"
            else:
                hours = delta_minutes // 60
                minutes = delta_minutes % 60
                if minutes > 0:
                    return f"через {hours}ч {minutes}мин"
                else:
                    return f"через {hours}ч"
        except Exception as e:
            logger.error(f"[PureAI] Error getting next analysis time: {e}")
            return "не определено"


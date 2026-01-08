#!/usr/bin/env python3
"""
Pure AI Trader - Trading based solely on GPT signals

Режим торговли только по сигналам ChatGPT:
- Анализ каждые 2 часа
- Скриншоты 5M, 15M, 1H
- Новости с внешних источников
- GPT генерирует готовые сигналы
- Дедупликация по entry price
- Таймфрейм исполнения: 15M
- Символы: XAUUSD, EURUSD
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
    1. Каждые 2 часа запускает анализ для XAUUSD и EURUSD
    2. GPT анализирует скриншоты 5M/15M/1H + новости
    3. Генерирует сигналы с entry/SL/TP
    4. SignalManager проверяет дубликаты и управляет TTL
    5. Executor исполняет сделки на 15M таймфрейме
    """
    
    # Конфигурация
    SYMBOLS = ["XAUUSD", "EURUSD"]
    ANALYSIS_INTERVAL = 5 * 60 * 60  # 5 часов в секундах
    MIN_CONFIDENCE = 70  # Минимальная уверенность для входа
    MAX_TRADES_PER_DAY = 5  # Максимум сделок в день
    COOLDOWN_HOURS = 2  # Пауза между сделками одного символа
    
    def __init__(self, api_key: str = None, executor=None, analysis_interval_hours: int = None):
        """
        Initialize Pure AI Trader.
        
        Args:
            api_key: OpenAI API key
            executor: Executor instance for trade execution
            analysis_interval_hours: Интервал анализа в часах (по умолчанию 5)
        """
        self.api_key = api_key
        self.executor = executor
        
        # Применяем пользовательский интервал если задан
        if analysis_interval_hours is not None:
            self.ANALYSIS_INTERVAL = analysis_interval_hours * 60 * 60
        
        # Инициализация сервисов
        self.analyst = MarketAnalystService(api_key=api_key)
        self.signal_manager = AISignalManager()
        
        # Состояние
        self.running = False
        self.thread = None
        self.last_analysis_time = {}  # {symbol: datetime}
        self.daily_trades = {}  # {date: count}
        self.symbol_cooldown = {}  # {symbol: datetime}
        
        logger.info("[PureAI] Pure AI Trader initialized")
        logger.info(f"[PureAI] Symbols: {', '.join(self.SYMBOLS)}")
        logger.info(f"[PureAI] Analysis every {self.ANALYSIS_INTERVAL // 3600} hours")
    
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
        """Вычисляет время следующего анализа (каждые 2 часа)."""
        now = datetime.now()
        current_hour = now.hour
        
        # Округляем до следующего четного часа: 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
        next_hour = ((current_hour // 2) * 2 + 2) % 24
        
        if next_hour <= current_hour:
            # Следующий день
            next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
            next_time += timedelta(days=1)
        else:
            next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
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
                logger.info(f"[PureAI] {symbol} in cooldown, skipping")
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
            
            # Проверяем минимальную уверенность
            if confidence < self.MIN_CONFIDENCE:
                logger.info(f"[PureAI] {symbol} signal confidence too low: {confidence}% < {self.MIN_CONFIDENCE}%")
                return
            
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
                
                # Устанавливаем cooldown для символа
                self.symbol_cooldown[symbol] = datetime.now() + timedelta(hours=self.COOLDOWN_HOURS)
            
        except Exception as e:
            logger.error(f"[PureAI] Error processing signal: {e}", exc_info=True)
    
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

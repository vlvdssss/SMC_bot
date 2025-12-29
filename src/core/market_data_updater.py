"""
Market Data Updater - обновление рыночных данных.
"""

import threading
import time
from typing import Optional, Callable
from datetime import datetime
from src.core.logger import logger


class MarketDataUpdater:
    """Обновлятор рыночных данных."""

    def __init__(self, mt5_manager, manual_trade_state, update_callback: Optional[Callable] = None):
        self.mt5_manager = mt5_manager
        self.manual_trade_state = manual_trade_state
        self.update_callback = update_callback

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.update_interval = 1.0  # секунды

        logger.info("MarketDataUpdater initialized")

    def start(self):
        """Запуск обновления данных."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("MarketDataUpdater started")

    def stop(self):
        """Остановка обновления данных."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("MarketDataUpdater stopped")

    def _update_loop(self):
        """Цикл обновления данных."""
        while self.running:
            try:
                self._update_market_data()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"MarketDataUpdater error: {e}")
                time.sleep(5.0)  # Пауза при ошибке

    def _update_market_data(self):
        """Обновление рыночных данных."""
        if not self.mt5_manager or not self.mt5_manager.is_connected():
            return

        try:
            # Получаем текущие цены
            symbol = self.manual_trade_state.symbol
            if not symbol:
                return

            # Получаем tick данные
            tick = self.mt5_manager.mt5.symbol_info_tick(symbol)
            if not tick:
                return

            bid = tick.bid
            ask = tick.ask
            spread = ask - bid

            # Обновляем состояние
            self.manual_trade_state.update_from_market_data(bid, ask, spread)

            # Вызываем callback если есть
            if self.update_callback:
                self.update_callback()

        except Exception as e:
            logger.error(f"Error updating market data: {e}")

    def force_update(self):
        """Принудительное обновление."""
        self._update_market_data()

    def set_update_interval(self, interval: float):
        """Установка интервала обновления."""
        self.update_interval = max(0.1, interval)  # минимум 0.1 сек

    def set_symbol(self, symbol: str):
        """Установка символа для мониторинга."""
        if symbol != self.manual_trade_state.symbol:
            self.manual_trade_state.set_symbol(symbol)
            self.force_update()  # Немедленное обновление для нового символа
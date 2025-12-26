"""
Live Trader - Live and Demo Trading Module
"""

import logging
import time
from datetime import datetime
from typing import Dict
import threading

class LiveTrader:
    def __init__(self, strategies: Dict, executor, mt5_connector):
        self.strategies = strategies
        self.executor = executor
        self.mt5_connector = mt5_connector
        self.logger = logging.getLogger('LiveTrader')
        self.running = False
        self.thread = None
    
    def start(self):
        """Запуск live trading"""
        self.running = True
        self.thread = threading.Thread(target=self._trading_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Live trader started")
    
    def stop(self):
        """Остановка live trading"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Live trader stopped")
    
    def _trading_loop(self):
        """Главный цикл торговли"""
        while self.running:
            try:
                # Проверка каждого инструмента
                for instrument, strategy in self.strategies.items():
                    self._check_signals(instrument, strategy)
                
                # Пауза между проверками
                time.sleep(60)  # Проверка каждую минуту
            
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(60)
    
    def _check_signals(self, instrument: str, strategy):
        """Проверка сигналов для инструмента"""
        try:
            # Получение последних данных
            data = self.mt5_connector.get_latest_data(instrument, timeframe='H1', count=100)
            if data.empty:
                return
            
            # Получение текущей цены
            current_price = self.mt5_connector.get_current_price(instrument)
            if not current_price:
                return
            
            # Генерация сигнала
            signal = strategy.generate_signal(data.iloc[-1], data)
            
            if signal:
                self.logger.info(f"Signal generated for {instrument}: {signal}")
                
                # Исполнение сигнала
                if self.executor.execute_signal(signal, current_price):
                    self.logger.info(f"Signal executed for {instrument}")
                else:
                    self.logger.warning(f"Failed to execute signal for {instrument}")
        
        except Exception as e:
            self.logger.error(f"Error checking signals for {instrument}: {e}")
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
                self._check_signals_loop()
                time.sleep(60)  # Проверка каждую минуту
        except KeyboardInterrupt:
            print("\n[!] Остановлено пользователем")
        finally:
            self.mt5_connector.disconnect()
    
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
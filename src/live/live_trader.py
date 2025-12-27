"""
Live Trader - Live and Demo Trading Module
"""

import logging
import time
from datetime import datetime
from typing import Dict, Tuple
import threading

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
    def __init__(self, strategies: Dict, executor, mt5_connector):
        self.strategies = strategies
        self.executor = executor
        self.mt5_connector = mt5_connector
        self.logger = logging.getLogger('LiveTrader')
        self.running = False
        self.thread = None
        
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
    
    def check_gpt_filter(self, instrument: str) -> Tuple[bool, str]:
        """Проверка через GPT перед открытием сделки."""
        
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
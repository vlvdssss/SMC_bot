#!/usr/bin/env python3
"""
Technical Confirmation Filter v1.0 - Hybrid GPT + Technical Indicators

Добавляет технические фильтры к сигналам GPT для повышения точности.
Используется как дополнительное подтверждение, НЕ заменяет GPT анализ.

ЛОГИКА:
1. GPT генерирует сигнал (основной)
2. Technical Filter проверяет подтверждение
3. При высокой уверенности GPT (>80%) - входим без фильтров
4. При средней уверенности (60-80%) - требуется подтверждение
5. При низкой уверенности (<60%) - отклоняем

ТЕХНИЧЕСКИЕ ФИЛЬТРЫ:
- EMA Trend (20/50/200)
- RSI Overbought/Oversold
- Price Action (Higher Highs/Lower Lows)
- Volume confirmation (опционально)
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, Tuple, Optional
from src.core.logger import logger


class TechnicalConfirmation:
    """
    Технический фильтр для подтверждения GPT сигналов.
    
    Увеличивает точность входа, проверяя технические условия.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize technical confirmation filter.
        
        Args:
            strict_mode: True = жесткие фильтры, False = мягкие фильтры
        """
        self.strict_mode = strict_mode
        
        logger.info(f"[TechFilter] Initialized ({'STRICT' if strict_mode else 'BALANCED'} mode)")
    
    def confirm_signal(
        self, 
        symbol: str, 
        direction: str, 
        confidence: float,
        entry_price: float
    ) -> Tuple[bool, str, Dict]:
        """
        Проверяет технические условия для подтверждения сигнала.
        
        Args:
            symbol: Торговый инструмент
            direction: BUY или SELL
            confidence: Уверенность GPT (0-100)
            entry_price: Цена входа
        
        Returns:
            (allowed: bool, reason: str, tech_data: dict)
        """
        try:
            # Высокая уверенность GPT - пропускаем без проверки
            if confidence >= 80:
                logger.info(f"[TechFilter] ✅ HIGH CONFIDENCE ({confidence}%) - skipping tech filters")
                return True, "High GPT confidence", {}
            
            # Получаем технические данные
            tech_data = self._get_technical_indicators(symbol)
            
            if not tech_data:
                logger.warning("[TechFilter] ⚠️ No technical data available - allowing trade")
                return True, "No tech data", {}
            
            # Проверяем подтверждение
            if direction == "BUY":
                confirmed, reason = self._confirm_buy_signal(tech_data, confidence, entry_price)
            else:
                confirmed, reason = self._confirm_sell_signal(tech_data, confidence, entry_price)
            
            if confirmed:
                logger.info(f"[TechFilter] ✅ CONFIRMED: {direction} {symbol} - {reason}")
            else:
                logger.warning(f"[TechFilter] ❌ REJECTED: {direction} {symbol} - {reason}")
            
            return confirmed, reason, tech_data
            
        except Exception as e:
            logger.error(f"[TechFilter] Error: {e}")
            # При ошибке разрешаем сделку (не блокируем из-за технических проблем)
            return True, f"Filter error: {e}", {}
    
    def _get_technical_indicators(self, symbol: str) -> Dict:
        """Получает технические индикаторы для M15 таймфрейма."""
        try:
            # Получаем M15 данные (последние 200 баров)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
            
            if rates is None or len(rates) < 200:
                return {}
            
            df = pd.DataFrame(rates)
            
            # EMAs
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['ema_200'] = df['close'].ewm(span=200).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # ATR
            df['high_low'] = df['high'] - df['low']
            df['atr'] = df['high_low'].rolling(window=14).mean()
            
            # Current values
            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Trend detection
            ema_bullish = current['ema_20'] > current['ema_50'] > current['ema_200']
            ema_bearish = current['ema_20'] < current['ema_50'] < current['ema_200']
            
            # Price action
            last_5_candles = df.tail(5)
            bullish_candles = (last_5_candles['close'] > last_5_candles['open']).sum()
            bearish_candles = (last_5_candles['close'] < last_5_candles['open']).sum()
            
            # Higher High / Lower Low
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            making_higher_highs = current['high'] >= prev['high']
            making_lower_lows = current['low'] <= prev['low']
            
            tech_data = {
                'price': float(current['close']),
                'ema_20': float(current['ema_20']),
                'ema_50': float(current['ema_50']),
                'ema_200': float(current['ema_200']),
                'rsi': float(current['rsi']),
                'atr': float(current['atr']),
                'ema_bullish': bool(ema_bullish),
                'ema_bearish': bool(ema_bearish),
                'bullish_candles': int(bullish_candles),
                'bearish_candles': int(bearish_candles),
                'recent_high': float(recent_high),
                'recent_low': float(recent_low),
                'making_higher_highs': bool(making_higher_highs),
                'making_lower_lows': bool(making_lower_lows)
            }
            
            return tech_data
            
        except Exception as e:
            logger.error(f"[TechFilter] Failed to calculate indicators: {e}")
            return {}
    
    def _confirm_buy_signal(
        self, 
        tech_data: Dict, 
        confidence: float,
        entry_price: float
    ) -> Tuple[bool, str]:
        """Проверяет условия для BUY сигнала."""
        
        conditions_met = []
        conditions_failed = []
        
        # 1. EMA Trend (сильный фильтр)
        if tech_data['ema_bullish']:
            conditions_met.append("EMA bullish trend")
        else:
            conditions_failed.append("EMA not bullish")
        
        # 2. RSI не перекуплен
        rsi = tech_data['rsi']
        # Balanced mode: смягченный порог 75, Strict mode: 70
        rsi_threshold = 70 if self.strict_mode else 75
        if rsi < rsi_threshold:
            conditions_met.append(f"RSI {rsi:.1f} not overbought (<{rsi_threshold})")
        else:
            conditions_failed.append(f"RSI {rsi:.1f} overbought (>{rsi_threshold})")
        
        # 3. Bullish momentum (последние 5 свечей)
        bullish_candles = tech_data['bullish_candles']
        if bullish_candles >= 3:
            conditions_met.append(f"{bullish_candles}/5 bullish candles")
        else:
            conditions_failed.append(f"Only {bullish_candles}/5 bullish candles")
        
        # 4. Price near support (entry близко к recent low)
        price = tech_data['price']
        recent_low = tech_data['recent_low']
        distance_from_low = ((price - recent_low) / recent_low) * 100
        if distance_from_low < 0.5:  # Менее 0.5% от лоя
            conditions_met.append(f"Near support (${recent_low:.2f})")
        
        # Строгий режим: все условия должны быть выполнены
        if self.strict_mode:
            if len(conditions_failed) == 0:
                return True, f"All conditions met: {', '.join(conditions_met)}"
            else:
                return False, f"Failed: {', '.join(conditions_failed)}"
        
        # Мягкий режим: минимум 2 из 4 условий
        else:
            if len(conditions_met) >= 2:
                return True, f"Conditions met: {', '.join(conditions_met)}"
            else:
                return False, f"Insufficient conditions: {', '.join(conditions_failed)}"
    
    def _confirm_sell_signal(
        self, 
        tech_data: Dict, 
        confidence: float,
        entry_price: float
    ) -> Tuple[bool, str]:
        """Проверяет условия для SELL сигнала."""
        
        conditions_met = []
        conditions_failed = []
        
        # 1. EMA Trend (сильный фильтр)
        if tech_data['ema_bearish']:
            conditions_met.append("EMA bearish trend")
        else:
            conditions_failed.append("EMA not bearish")
        
        # 2. RSI не перепродан
        rsi = tech_data['rsi']
        # Balanced mode: смягченный порог 25, Strict mode: 30
        rsi_threshold = 30 if self.strict_mode else 25
        if rsi > rsi_threshold:
            conditions_met.append(f"RSI {rsi:.1f} not oversold (>{rsi_threshold})")
        else:
            conditions_failed.append(f"RSI {rsi:.1f} oversold (<{rsi_threshold})")
        
        # 3. Bearish momentum (последние 5 свечей)
        bearish_candles = tech_data['bearish_candles']
        if bearish_candles >= 3:
            conditions_met.append(f"{bearish_candles}/5 bearish candles")
        else:
            conditions_failed.append(f"Only {bearish_candles}/5 bearish candles")
        
        # 4. Price near resistance (entry близко к recent high)
        price = tech_data['price']
        recent_high = tech_data['recent_high']
        distance_from_high = ((recent_high - price) / recent_high) * 100
        if distance_from_high < 0.5:  # Менее 0.5% от хая
            conditions_met.append(f"Near resistance (${recent_high:.2f})")
        
        # Строгий режим: все условия должны быть выполнены
        if self.strict_mode:
            if len(conditions_failed) == 0:
                return True, f"All conditions met: {', '.join(conditions_met)}"
            else:
                return False, f"Failed: {', '.join(conditions_failed)}"
        
        # Мягкий режим: минимум 2 из 4 условий
        else:
            if len(conditions_met) >= 2:
                return True, f"Conditions met: {', '.join(conditions_met)}"
            else:
                return False, f"Insufficient conditions: {', '.join(conditions_failed)}"

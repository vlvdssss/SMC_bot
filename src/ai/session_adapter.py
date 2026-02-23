#!/usr/bin/env python3
"""
Session-Based Trading Adapter v1.0

Адаптирует торговые параметры под текущую торговую сессию:
- ASIAN (00:00-08:00 UTC): Тихий рынок, узкие диапазоны
- EUROPEAN (08:00-16:00 UTC): Средняя волатильность
- US (16:00-24:00 UTC): Высокая волатильность

АДАПТАЦИИ:
- Минимальная confidence для входа
- Множители SL/TP
- Максимальный spread
- Торговая агрессивность
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Tuple
from src.core.logger import logger


class TradingSession(Enum):
    """Торговые сессии с их характеристиками."""
    
    ASIAN = "asian"
    EUROPEAN = "european"  
    US = "us"
    OVERLAP = "overlap"  # Пересечение сессий (повышенная волатильность)


class SessionAdapter:
    """
    Адаптирует торговые параметры под текущую сессию.
    
    Учитывает особенности каждой сессии для оптимизации входов.
    """
    
    def __init__(self):
        """Initialize session adapter."""
        logger.info("[SessionAdapter] Initialized - will adapt strategy by trading session")
    
    def get_current_session(self, hour: int = None) -> TradingSession:
        """
        Определяет текущую торговую сессию.
        
        Args:
            hour: Час UTC (0-23), если None - берется текущий
        
        Returns:
            TradingSession enum
        """
        if hour is None:
            hour = datetime.utcnow().hour
        
        # Asian session (00:00-08:00 UTC) - Токио, Сингапур, Гонконг
        if 0 <= hour < 8:
            return TradingSession.ASIAN
        
        # European session (08:00-16:00 UTC) - Лондон, Франкфурт
        elif 8 <= hour < 16:
            # Overlap: European + US (15:00-16:00 UTC) - максимальная волатильность
            if 15 <= hour < 16:
                return TradingSession.OVERLAP
            return TradingSession.EUROPEAN
        
        # US session (16:00-24:00 UTC) - Нью-Йорк
        else:
            return TradingSession.US
    
    def get_session_parameters(self, session: TradingSession = None) -> Dict:
        """
        Возвращает параметры для текущей сессии.
        
        Returns:
            Dict с адаптированными параметрами
        """
        if session is None:
            session = self.get_current_session()
        
        if session == TradingSession.ASIAN:
            params = {
                'name': 'ASIAN',
                'min_confidence': 80,  # Выше порог (тихий рынок = меньше сигналов)
                'sl_multiplier': 0.8,  # Меньше SL (узкие диапазоны)
                'tp_multiplier': 1.2,  # Меньше TP (цели ближе)
                'max_spread_multiplier': 1.0,  # Нормальный spread
                'lot_multiplier': 0.8,  # Меньше лот (низкая волатильность)
                'description': 'Low volatility, narrow ranges, higher quality setups'
            }
        
        elif session == TradingSession.EUROPEAN:
            params = {
                'name': 'EUROPEAN',
                'min_confidence': 70,  # Средний порог (сбалансированный подход)
                'sl_multiplier': 1.0,  # Нормальный SL
                'tp_multiplier': 1.5,  # Средний TP
                'max_spread_multiplier': 1.0,  # Нормальный spread
                'lot_multiplier': 1.0,  # Нормальный лот
                'description': 'Medium volatility, balanced approach'
            }
        
        elif session == TradingSession.US:
            params = {
                'name': 'US',
                'min_confidence': 65,  # Ниже порог (больше возможностей)
                'sl_multiplier': 1.3,  # Шире SL (высокая волатильность)
                'tp_multiplier': 2.0,  # Больше TP (дальние цели возможны)
                'max_spread_multiplier': 1.5,  # Допустим больший spread
                'lot_multiplier': 1.2,  # Больше лот (высокая волатильность)
                'description': 'High volatility, wider targets, aggressive approach'
            }
        
        else:  # OVERLAP
            params = {
                'name': 'OVERLAP (EU+US)',
                'min_confidence': 60,  # Самый низкий порог (максимум возможностей)
                'sl_multiplier': 1.5,  # Самый широкий SL (максимальная волатильность)
                'tp_multiplier': 2.5,  # Максимальный TP (большие движения)
                'max_spread_multiplier': 2.0,  # Допустим широкий spread
                'lot_multiplier': 1.5,  # Максимальный лот (оптимальные условия)
                'description': 'Maximum volatility, best opportunities, most aggressive'
            }
        
        return params
    
    def adapt_signal_parameters(
        self,
        entry: float,
        sl: float,
        tp: float,
        confidence: float,
        lot: float,
        session: TradingSession = None
    ) -> Tuple[float, float, float, bool, str]:
        """
        Адаптирует параметры сигнала под текущую сессию.
        
        Args:
            entry: Цена входа
            sl: Stop Loss
            tp: Take Profit
            confidence: Уверенность GPT (0-100)
            lot: Размер лота
            session: Торговая сессия (если None - определяется автоматически)
        
        Returns:
            (new_sl, new_tp, new_lot, allowed, reason)
        """
        if session is None:
            session = self.get_current_session()
        
        params = self.get_session_parameters(session)
        
        # Проверяем минимальную confidence для сессии
        if confidence < params['min_confidence']:
            reason = f"Confidence {confidence}% below {params['name']} minimum {params['min_confidence']}%"
            logger.warning(f"[SessionAdapter] ❌ {reason}")
            return sl, tp, lot, False, reason
        
        # Адаптируем SL/TP
        sl_distance = abs(entry - sl)
        tp_distance = abs(entry - tp)
        
        new_sl_distance = sl_distance * params['sl_multiplier']
        new_tp_distance = tp_distance * params['tp_multiplier']
        
        # Рассчитываем новые уровни
        if entry > sl:  # BUY
            new_sl = entry - new_sl_distance
            new_tp = entry + new_tp_distance
        else:  # SELL
            new_sl = entry + new_sl_distance
            new_tp = entry - new_tp_distance
        
        # Адаптируем лот
        new_lot = lot * params['lot_multiplier']
        new_lot = round(new_lot, 2)  # Округляем до 0.01
        
        logger.info(f"[SessionAdapter] ✅ {params['name']} SESSION ADAPTATION:")
        logger.info(f"[SessionAdapter]    Confidence: {confidence}% >= {params['min_confidence']}%")
        logger.info(f"[SessionAdapter]    SL: ${sl:.2f} → ${new_sl:.2f} (x{params['sl_multiplier']})")
        logger.info(f"[SessionAdapter]    TP: ${tp:.2f} → ${new_tp:.2f} (x{params['tp_multiplier']})")
        logger.info(f"[SessionAdapter]    Lot: {lot:.2f} → {new_lot:.2f} (x{params['lot_multiplier']})")
        logger.info(f"[SessionAdapter]    Description: {params['description']}")
        
        reason = f"{params['name']} session adapted"
        return new_sl, new_tp, new_lot, True, reason
    
    def should_trade_in_session(self, confidence: float, session: TradingSession = None) -> Tuple[bool, str]:
        """
        Проверяет, стоит ли торговать в текущую сессию.
        
        Args:
            confidence: Уверенность GPT
            session: Торговая сессия
        
        Returns:
            (allowed: bool, reason: str)
        """
        if session is None:
            session = self.get_current_session()
        
        params = self.get_session_parameters(session)
        
        if confidence >= params['min_confidence']:
            return True, f"{params['name']} session OK"
        else:
            return False, f"Confidence {confidence}% < {params['name']} minimum {params['min_confidence']}%"
    
    def get_session_info(self) -> Dict:
        """Возвращает информацию о текущей сессии."""
        session = self.get_current_session()
        params = self.get_session_parameters(session)
        
        return {
            'session': session.value,
            'session_name': params['name'],
            'current_hour_utc': datetime.utcnow().hour,
            'parameters': params
        }

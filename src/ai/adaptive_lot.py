#!/usr/bin/env python3
"""
Adaptive Lot Sizing v1.0

Динамически адаптирует размер позиции на основе:
1. Winrate последних N сделок
2. Текущей серии выигрышей/проигрышей
3. Drawdown
4. Волатильности рынка

ЛОГИКА:
- После побед → увеличить лот (но не более чем в 2x)
- После убытков → уменьшить лот (защита капитала)
- После drawdown → консервативный подход
- При высокой волатильности → уменьшить лот
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.core.logger import logger


class AdaptiveLotSizing:
    """
    Динамический расчет размера позиции.
    
    Адаптируется к текущей эффективности торговли.
    """
    
    def __init__(
        self,
        base_lot: float = 0.01,
        min_lot: float = 0.01,
        max_lot: float = 0.05,
        lookback_trades: int = 10
    ):
        """
        Initialize adaptive lot sizing.
        
        Args:
            base_lot: Базовый размер лота
            min_lot: Минимальный лот
            max_lot: Максимальный лот
            lookback_trades: Сколько последних сделок анализировать
        """
        self.base_lot = base_lot
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.lookback_trades = lookback_trades
        
        logger.info(f"[AdaptiveLot] Initialized: base={base_lot}, min={min_lot}, max={max_lot}")
    
    def calculate_lot(
        self,
        recent_trades: List[Dict],
        current_confidence: float,
        signal_quality_multiplier: float = 1.0,
        session_multiplier: float = 1.0,
        instrument_base_lot: float = None,
        instrument_max_lot: float = None
    ) -> float:
        """
        Рассчитывает адаптивный размер лота.
        
        Args:
            recent_trades: Список последних сделок с ключом 'pnl'
            current_confidence: Уверенность текущего сигнала (0-100)
            signal_quality_multiplier: Множитель качества сигнала
            session_multiplier: Множитель торговой сессии
            instrument_base_lot: Базовый лот для конкретного инструмента (переопределяет self.base_lot)
            instrument_max_lot: Максимальный лот для конкретного инструмента (переопределяет self.max_lot)
        
        Returns:
            Адаптированный размер лота
        """
        try:
            # Начинаем с базового лота (инструмент-специфичный или глобальный)
            lot = instrument_base_lot if instrument_base_lot is not None else self.base_lot
            base_lot_used = lot  # Запоминаем для логов
            max_lot_limit = instrument_max_lot if instrument_max_lot is not None else self.max_lot
            
            # 1. PERFORMANCE MULTIPLIER - на основе последних сделок
            if recent_trades and len(recent_trades) >= 3:
                performance_mult = self._calculate_performance_multiplier(recent_trades)
                lot *= performance_mult
                logger.debug(f"[AdaptiveLot] Performance multiplier: {performance_mult:.2f}")
            
            # 2. CONFIDENCE MULTIPLIER - на основе уверенности GPT
            confidence_mult = self._calculate_confidence_multiplier(current_confidence)
            lot *= confidence_mult
            logger.debug(f"[AdaptiveLot] Confidence multiplier: {confidence_mult:.2f}")
            
            # 3. SIGNAL QUALITY MULTIPLIER - от Signal Quality system
            lot *= signal_quality_multiplier
            logger.debug(f"[AdaptiveLot] Signal quality multiplier: {signal_quality_multiplier:.2f}")
            
            # 4. SESSION MULTIPLIER - от Session Adapter
            lot *= session_multiplier
            logger.debug(f"[AdaptiveLot] Session multiplier: {session_multiplier:.2f}")
            
            # 5. STREAK PROTECTION - защита от серий
            if recent_trades:
                streak_mult = self._calculate_streak_multiplier(recent_trades)
                lot *= streak_mult
                logger.debug(f"[AdaptiveLot] Streak multiplier: {streak_mult:.2f}")
            
            # Ограничиваем min/max
            lot = max(self.min_lot, min(max_lot_limit, lot))
            lot = round(lot, 2)  # Округляем до 0.01
            
            logger.info(f"[AdaptiveLot] ✅ Calculated lot: {lot:.2f} (base: {base_lot_used:.2f}, max: {max_lot_limit:.2f})")
            
            return lot
            
        except Exception as e:
            logger.error(f"[AdaptiveLot] Calculation error: {e}")
            return self.base_lot
    
    def _calculate_performance_multiplier(self, recent_trades: List[Dict]) -> float:
        """
        Мультипликатор на основе winrate последних сделок.
        
        Логика:
        - Winrate > 60% → увеличиваем лот (1.3x)
        - Winrate 40-60% → нормальный лот (1.0x)
        - Winrate < 40% → уменьшаем лот (0.7x)
        """
        last_n = recent_trades[-self.lookback_trades:]
        
        if not last_n:
            return 1.0
        
        wins = sum(1 for trade in last_n if trade.get('pnl', 0) > 0)
        winrate = wins / len(last_n)
        
        if winrate >= 0.6:
            multiplier = 1.3  # Увеличиваем при успехе
        elif winrate >= 0.4:
            multiplier = 1.0  # Нормальный
        else:
            multiplier = 0.7  # Уменьшаем при неудаче
        
        logger.debug(f"[AdaptiveLot] Winrate: {winrate*100:.1f}% ({wins}/{len(last_n)} wins)")
        
        return multiplier
    
    def _calculate_confidence_multiplier(self, confidence: float) -> float:
        """
        Мультипликатор на основе confidence GPT.
        
        Логика:
        - Confidence > 85% → максимальный лот (1.2x)
        - Confidence 70-85% → нормальный (1.0x)
        - Confidence < 70% → уменьшенный (0.8x)
        """
        if confidence >= 85:
            return 1.2  # Высокая уверенность
        elif confidence >= 70:
            return 1.0  # Средняя уверенность
        else:
            return 0.8  # Низкая уверенность
    
    def _calculate_streak_multiplier(self, recent_trades: List[Dict]) -> float:
        """
        Мультипликатор на основе текущей серии.
        
        Логика:
        - Серия выигрышей (3+) → увеличиваем (1.2x)
        - Серия убытков (3+) → уменьшаем (0.6x)
        - Иначе → нормальный (1.0x)
        """
        if not recent_trades or len(recent_trades) < 3:
            return 1.0
        
        # Проверяем последние 3 сделки
        last_3 = recent_trades[-3:]
        all_wins = all(trade.get('pnl', 0) > 0 for trade in last_3)
        all_losses = all(trade.get('pnl', 0) < 0 for trade in last_3)
        
        if all_wins:
            logger.debug("[AdaptiveLot] Win streak detected (+3)")
            return 1.2  # Серия побед - увеличиваем
        elif all_losses:
            logger.debug("[AdaptiveLot] Loss streak detected (-3)")
            return 0.6  # Серия убытков - сильно уменьшаем
        else:
            return 1.0  # Смешанные результаты
    
    def get_lot_recommendation(
        self,
        recent_trades: List[Dict],
        current_confidence: float
    ) -> Dict:
        """
        Возвращает детальную рекомендацию по лоту.
        
        Returns:
            Dict с рекомендацией и обоснованием
        """
        lot = self.calculate_lot(recent_trades, current_confidence)
        
        # Анализируем последние сделки
        last_n = recent_trades[-self.lookback_trades:] if recent_trades else []
        wins = sum(1 for t in last_n if t.get('pnl', 0) > 0) if last_n else 0
        winrate = (wins / len(last_n) * 100) if last_n else 0
        
        # Определяем рекомендацию
        if lot > self.base_lot * 1.2:
            recommendation = "AGGRESSIVE"
            reason = f"Strong performance (WR: {winrate:.0f}%), high confidence ({current_confidence:.0f}%)"
        elif lot < self.base_lot * 0.8:
            recommendation = "CONSERVATIVE"
            reason = f"Weak performance (WR: {winrate:.0f}%) or low confidence ({current_confidence:.0f}%)"
        else:
            recommendation = "BALANCED"
            reason = f"Normal conditions (WR: {winrate:.0f}%, confidence: {current_confidence:.0f}%)"
        
        return {
            'lot': lot,
            'recommendation': recommendation,
            'reason': reason,
            'base_lot': self.base_lot,
            'multiplier': lot / self.base_lot,
            'winrate': winrate,
            'trades_analyzed': len(last_n)
        }

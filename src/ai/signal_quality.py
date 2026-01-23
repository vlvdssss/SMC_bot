#!/usr/bin/env python3
"""
Signal Quality System v3.0 - Separated Accuracy & Quality Architecture

АРХИТЕКТУРА:
1. Signal Accuracy - Влияет ТОЛЬКО на разрешение входа
2. Signal Quality - Влияет ТОЛЬКО на размер лота
3. News Filter - Блокирует входы при HIGH IMPACT новостях по золоту

Эти параметры НЕЗАВИСИМЫ друг от друга.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional
from src.core.logger import logger


class SignalAccuracy(Enum):
    """
    Точность сигнала - определяет ТОЛЬКО разрешение входа.
    НЕ влияет на размер лота.
    """
    VERY_LOW = ("very_low", 0, "Вход категорически запрещён")
    LOW = ("low", 1, "Вход запрещён - низкая точность")
    MEDIUM = ("medium", 2, "Вход возможен при дополнительных фильтрах")
    HIGH = ("high", 3, "Вход разрешён - хорошая точность")
    VERY_HIGH = ("very_high", 4, "Вход приоритетный - отличная точность")
    
    def __init__(self, key: str, threshold: int, description: str):
        self.key = key
        self.threshold = threshold  # Порог для принятия решения
        self.description = description
    
    def allows_entry(self) -> bool:
        """Разрешён ли вход при данной точности."""
        return self.threshold >= 2  # MEDIUM и выше
    
    @classmethod
    def from_confidence(cls, confidence: float) -> 'SignalAccuracy':
        """
        Преобразует confidence (0-100%) в уровень точности.
        
        Градация:
        - 0-40%: VERY_LOW (запрещён)
        - 40-50%: LOW (запрещён)
        - 50-65%: MEDIUM (возможен с фильтрами)
        - 65-80%: HIGH (разрешён)
        - 80-100%: VERY_HIGH (приоритетный)
        """
        if confidence >= 80:
            return cls.VERY_HIGH
        elif confidence >= 65:
            return cls.HIGH
        elif confidence >= 50:
            return cls.MEDIUM
        elif confidence >= 40:
            return cls.LOW
        else:
            return cls.VERY_LOW


class SignalQuality(Enum):
    """
    Качество сигнала - определяет ТОЛЬКО размер лота.
    НЕ влияет на разрешение входа.
    """
    POOR = ("poor", 0.5, "Минимальный лот - слабый сигнал")
    NORMAL = ("normal", 1.0, "Базовый лот - обычный сигнал")
    GOOD = ("good", 1.5, "Увеличенный лот - хороший сигнал")
    EXCELLENT = ("excellent", 2.0, "Максимальный лот - отличный сигнал")
    
    def __init__(self, key: str, multiplier: float, description: str):
        self.key = key
        self.multiplier = multiplier  # Множитель лота
        self.description = description
    
    @classmethod
    def from_rr_and_conditions(cls, risk_reward: float, has_confirmation: bool = False) -> 'SignalQuality':
        """
        Определяет качество на основе R:R и подтверждающих факторов.
        
        Args:
            risk_reward: Risk/Reward ratio (например, 2.5 = 1:2.5)
            has_confirmation: Есть ли подтверждающие сигналы (EMA, SMC, etc.)
        
        Градация:
        - R:R < 1.5: POOR (слабый)
        - R:R 1.5-2.5: NORMAL (обычный)
        - R:R 2.5-4.0: GOOD (хороший)
        - R:R > 4.0 + подтверждение: EXCELLENT (отличный)
        """
        if risk_reward >= 4.0 and has_confirmation:
            return cls.EXCELLENT
        elif risk_reward >= 2.5:
            return cls.GOOD
        elif risk_reward >= 1.5:
            return cls.NORMAL
        else:
            return cls.POOR


class RiskMode(Enum):
    """
    Режим риска - модифицирует ПОРОГИ accuracy и MAX лот quality.
    НЕ принимает прямого решения о входе.
    """
    CONSERVATIVE = ("conservative", 0.6, 1.0, "Консервативный - только HIGH+ accuracy, макс 1.0x лот")
    BALANCED = ("balanced", 0.5, 1.5, "Сбалансированный - MEDIUM+ accuracy, макс 1.5x лот")
    AGGRESSIVE = ("aggressive", 0.4, 2.0, "Агрессивный - LOW+ accuracy, макс 2.0x лот")
    
    def __init__(self, key: str, min_confidence: float, max_lot_mult: float, description: str):
        self.key = key
        self.min_confidence = min_confidence  # Минимальная уверенность для входа
        self.max_lot_mult = max_lot_mult      # Максимальный множитель лота
        self.description = description
    
    def allows_entry(self, accuracy: SignalAccuracy) -> bool:
        """Проверяет, разрешён ли вход при данном режиме и точности."""
        if self == RiskMode.CONSERVATIVE:
            return accuracy in [SignalAccuracy.HIGH, SignalAccuracy.VERY_HIGH]
        elif self == RiskMode.BALANCED:
            return accuracy.allows_entry()  # MEDIUM+
        else:  # AGGRESSIVE
            return accuracy != SignalAccuracy.VERY_LOW
    
    def adjust_lot_multiplier(self, quality_mult: float) -> float:
        """Ограничивает множитель лота максимумом режима."""
        return min(quality_mult, self.max_lot_mult)


@dataclass
class SignalDecision:
    """
    Итоговое решение по сигналу - комбинация accuracy, quality, risk mode.
    """
    accuracy: SignalAccuracy
    quality: SignalQuality
    risk_mode: RiskMode
    entry_allowed: bool
    lot_multiplier: float
    block_reason: Optional[str] = None
    
    def __str__(self) -> str:
        status = "✅ ALLOWED" if self.entry_allowed else "❌ BLOCKED"
        return (
            f"{status} | Accuracy: {self.accuracy.key.upper()} | "
            f"Quality: {self.quality.key.upper()} (lot: {self.lot_multiplier:.2f}x) | "
            f"Mode: {self.risk_mode.key.upper()}"
        )


class SignalEvaluator:
    """
    Оценщик сигналов - принимает финальное решение о входе и лоте.
    """
    
    def __init__(self, risk_mode: RiskMode = RiskMode.BALANCED):
        self.risk_mode = risk_mode
        logger.info(f"[Signal Evaluator] Initialized with {risk_mode.description}")
    
    def evaluate(
        self, 
        confidence: float,
        risk_reward: float,
        has_confirmation: bool = False,
        news_block: bool = False
    ) -> SignalDecision:
        """
        Принимает решение о входе и размере лота.
        
        Args:
            confidence: Уверенность GPT (0-100)
            risk_reward: R:R ratio
            has_confirmation: Есть ли подтверждение от индикаторов
            news_block: Блокировка из-за HIGH IMPACT новостей
        
        Returns:
            SignalDecision с финальным вердиктом
        """
        # 1. Определяем точность
        accuracy = SignalAccuracy.from_confidence(confidence)
        
        # 2. Определяем качество
        quality = SignalQuality.from_rr_and_conditions(risk_reward, has_confirmation)
        
        # 3. Проверяем разрешение входа
        entry_allowed = True
        block_reason = None
        
        # 3.1. Блокировка новостями (приоритет 1)
        if news_block:
            entry_allowed = False
            block_reason = "HIGH IMPACT news for GOLD - entry blocked"
            logger.warning(f"[Signal Evaluator] 📰 {block_reason}")
        
        # 3.2. Проверка точности (приоритет 2)
        elif not accuracy.allows_entry():
            entry_allowed = False
            block_reason = f"Accuracy too low: {accuracy.key} ({accuracy.description})"
            logger.warning(f"[Signal Evaluator] 🎯 {block_reason}")
        
        # 3.3. Проверка режима риска (приоритет 3)
        elif not self.risk_mode.allows_entry(accuracy):
            entry_allowed = False
            block_reason = f"Risk mode {self.risk_mode.key} requires higher accuracy"
            logger.warning(f"[Signal Evaluator] ⚙️ {block_reason}")
        
        # 4. Определяем множитель лота
        if entry_allowed:
            # Берём базовый множитель из качества
            base_mult = quality.multiplier
            # Ограничиваем максимумом режима
            lot_multiplier = self.risk_mode.adjust_lot_multiplier(base_mult)
            
            logger.info(
                f"[Signal Evaluator] ✅ Entry ALLOWED | "
                f"Accuracy: {accuracy.key} | Quality: {quality.key} | "
                f"Lot: {lot_multiplier:.2f}x (base: {base_mult:.2f}x, mode cap: {self.risk_mode.max_lot_mult:.2f}x)"
            )
        else:
            lot_multiplier = 0.0
        
        return SignalDecision(
            accuracy=accuracy,
            quality=quality,
            risk_mode=self.risk_mode,
            entry_allowed=entry_allowed,
            lot_multiplier=lot_multiplier,
            block_reason=block_reason
        )
    
    def set_risk_mode(self, mode: RiskMode):
        """Изменить режим риска."""
        self.risk_mode = mode
        logger.info(f"[Signal Evaluator] Risk mode changed to: {mode.description}")


# ============================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================

if __name__ == "__main__":
    # Создаём оценщик в режиме BALANCED
    evaluator = SignalEvaluator(RiskMode.BALANCED)
    
    print("\n=== TEST CASES ===\n")
    
    # Case 1: Высокая уверенность, хороший R:R, нет новостей
    decision = evaluator.evaluate(
        confidence=75,
        risk_reward=3.0,
        has_confirmation=True,
        news_block=False
    )
    print(f"Case 1 (Good signal): {decision}\n")
    
    # Case 2: Средняя уверенность, низкий R:R
    decision = evaluator.evaluate(
        confidence=55,
        risk_reward=1.2,
        has_confirmation=False,
        news_block=False
    )
    print(f"Case 2 (Medium signal): {decision}\n")
    
    # Case 3: Высокая уверенность, но HIGH IMPACT новости
    decision = evaluator.evaluate(
        confidence=85,
        risk_reward=4.0,
        has_confirmation=True,
        news_block=True
    )
    print(f"Case 3 (News block): {decision}\n")
    
    # Case 4: Низкая уверенность
    decision = evaluator.evaluate(
        confidence=35,
        risk_reward=2.0,
        has_confirmation=False,
        news_block=False
    )
    print(f"Case 4 (Low accuracy): {decision}\n")
    
    # Case 5: Режим CONSERVATIVE - требует HIGH accuracy
    evaluator.set_risk_mode(RiskMode.CONSERVATIVE)
    decision = evaluator.evaluate(
        confidence=60,  # MEDIUM accuracy
        risk_reward=3.0,
        has_confirmation=True,
        news_block=False
    )
    print(f"Case 5 (Conservative mode): {decision}\n")

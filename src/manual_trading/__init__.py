"""
Manual Trading Module

Модуль для ручной торговли с AI-поддержкой.
Обеспечивает полный контроль над сделками через GUI.
"""

from .controller import ManualTradingController
from .validator import TradeValidator
from .calculator import RiskCalculator
from .ai_analyzer import ManualAIAnalyzer

__all__ = [
    'ManualTradingController',
    'TradeValidator',
    'RiskCalculator',
    'ManualAIAnalyzer'
]
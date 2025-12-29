"""
Trade Validator

Валидация параметров ручной сделки.
"""

import logging
from typing import Tuple, Optional
from ..models import TradeRequest

logger = logging.getLogger(__name__)


class TradeValidator:
    """Валидатор параметров сделки."""

    def __init__(self, config: dict):
        self.config = config
        self.min_rr_warning = config.get('MIN_RR_WARNING', 1.5)
        self.max_risk_percent = config.get('MAX_RISK_PERCENT', 5.0)

    def validate_trade_request(self, request: TradeRequest) -> Tuple[bool, Optional[str]]:
        """
        Полная валидация запроса на сделку.

        Returns:
            (is_valid, error_message)
        """
        try:
            # Базовая валидация
            self._validate_basic_params(request)

            # Валидация риск-менеджмента
            self._validate_risk_management(request)

            # Валидация уровней
            self._validate_price_levels(request)

            # Предупреждения
            warnings = self._check_warnings(request)
            if warnings:
                logger.warning(f"Trade warnings: {warnings}")

            return True, None

        except ValueError as e:
            logger.error(f"Trade validation failed: {e}")
            return False, str(e)

    def _validate_basic_params(self, request: TradeRequest):
        """Валидация базовых параметров."""
        if not request.symbol:
            raise ValueError("Symbol is required")

        if request.direction not in ['buy', 'sell']:
            raise ValueError(f"Invalid direction: {request.direction}")

        if request.lot_size <= 0:
            raise ValueError("Lot size must be positive")

        if request.risk_amount <= 0:
            raise ValueError("Risk amount must be positive")

    def _validate_risk_management(self, request: TradeRequest):
        """Валидация риск-менеджмента."""
        # Проверка максимального риска
        if request.risk_amount > self.max_risk_percent:
            raise ValueError(f"Risk amount {request.risk_amount}% exceeds maximum {self.max_risk_percent}%")

        # Проверка RR ratio
        if request.risk_reward_ratio < 0.1:
            raise ValueError("Risk-reward ratio too low")

    def _validate_price_levels(self, request: TradeRequest):
        """Валидация ценовых уровней."""
        if request.direction == 'buy':
            if request.stop_loss >= request.entry_price:
                raise ValueError("Stop loss must be below entry for buy orders")
            if request.take_profit <= request.entry_price:
                raise ValueError("Take profit must be above entry for buy orders")
        else:  # sell
            if request.stop_loss <= request.entry_price:
                raise ValueError("Stop loss must be above entry for sell orders")
            if request.take_profit >= request.entry_price:
                raise ValueError("Take profit must be below entry for sell orders")

        # Проверка минимального спреда
        sl_distance = abs(request.entry_price - request.stop_loss)
        tp_distance = abs(request.entry_price - request.take_profit)

        if sl_distance < 0.00001:  # Минимальный спред
            raise ValueError("Stop loss too close to entry")

        if tp_distance < 0.00001:
            raise ValueError("Take profit too close to entry")

    def _check_warnings(self, request: TradeRequest) -> list:
        """Проверка предупреждений."""
        warnings = []

        if request.risk_reward_ratio < self.min_rr_warning:
            warnings.append(f"Low RR ratio: {request.risk_reward_ratio:.2f} < {self.min_rr_warning}")

        return warnings
"""
Risk Calculator

Расчет риск-менеджмента для ручной торговли.
"""

import logging
from typing import Tuple, Optional
from ..models import TradeRequest

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Калькулятор риск-менеджмента."""

    def __init__(self, config: dict):
        self.config = config
        self.pip_value = config.get('PIP_VALUE', 0.0001)  # Для EURUSD
        self.contract_size = config.get('CONTRACT_SIZE', 100000)

    def calculate_lot_size(self, symbol: str, entry_price: float,
                          stop_loss: float, risk_amount: float,
                          account_balance: float) -> Tuple[float, str]:
        """
        Расчет объема позиции на основе риска.

        Args:
            symbol: Торговая пара
            entry_price: Цена входа
            stop_loss: Стоп-лосс
            risk_amount: Риск в процентах или долларах
            account_balance: Баланс счета

        Returns:
            (lot_size, explanation)
        """
        try:
            # Определяем риск в долларах
            if risk_amount <= 1.0:  # Процент
                risk_dollars = account_balance * (risk_amount / 100)
            else:  # Фиксированная сумма
                risk_dollars = risk_amount

            # Расчет стоп-лосса в пипсах
            sl_pips = abs(entry_price - stop_loss) / self.pip_value

            # Расчет стоимости одного пипса
            pip_value_per_lot = self.contract_size * self.pip_value

            # Расчет объема
            lot_size = risk_dollars / (sl_pips * pip_value_per_lot)

            # Округление до стандартных размеров
            lot_size = self._round_lot_size(lot_size)

            explanation = (".2f"
                          ".4f"
                          ".2f")

            return lot_size, explanation

        except Exception as e:
            logger.error(f"Lot size calculation failed: {e}")
            return 0.01, f"Error: {e}"

    def calculate_rr_ratio(self, entry_price: float, stop_loss: float,
                          take_profit: float, direction: str) -> float:
        """
        Расчет соотношения риск/прибыль.
        """
        try:
            risk = abs(entry_price - stop_loss)
            reward = abs(entry_price - take_profit)

            if reward == 0:
                return 0.0

            return reward / risk

        except Exception as e:
            logger.error(f"RR calculation failed: {e}")
            return 0.0

    def validate_risk_parameters(self, lot_size: float, risk_amount: float,
                               account_balance: float) -> Tuple[bool, str]:
        """
        Валидация параметров риска.
        """
        # Минимальный лот
        if lot_size < 0.01:
            return False, "Lot size too small (minimum 0.01)"

        # Максимальный лот
        if lot_size > 100.0:
            return False, "Lot size too large (maximum 100.0)"

        # Риск не более 10% от баланса
        max_risk = account_balance * 0.1
        if risk_amount > max_risk:
            return False, ".2f"

        return True, "Risk parameters valid"

    def _round_lot_size(self, lot_size: float) -> float:
        """Округление объема до стандартных значений."""
        # Стандартные размеры: 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, etc.
        standard_sizes = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]

        for size in standard_sizes:
            if lot_size <= size:
                return size

        return 100.0  # Максимум
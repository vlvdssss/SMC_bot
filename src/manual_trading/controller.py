"""
Manual Trading Controller

Основной контроллер для ручной торговли.
Координирует все компоненты: GUI, валидацию, расчеты, AI-анализ.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from .validator import TradeValidator
from .calculator import RiskCalculator
from .ai_analyzer import ManualAIAnalyzer
from ..models import TradeRequest, AIPrediction

logger = logging.getLogger(__name__)


class ManualTradingController:
    """Контроллер ручной торговли."""

    def __init__(self, config: dict, executor, llm_client=None):
        # Keep original config reference but normalize expected keys
        self.config = config or {}

        # Backwards-compatibility: support multiple possible key names for AI predict flag
        predict_flag = None
        if 'ENABLE_MANUAL_AI_PREDICT' in self.config:
            predict_flag = self.config.get('ENABLE_MANUAL_AI_PREDICT')
        elif 'ai_predict_enabled' in self.config:
            predict_flag = self.config.get('ai_predict_enabled')
        elif 'enable_manual_ai_predict' in self.config:
            predict_flag = self.config.get('enable_manual_ai_predict')

        # Ensure canonical key exists for other code paths
        self.config['ENABLE_MANUAL_AI_PREDICT'] = bool(predict_flag)
        self.executor = executor
        self.llm_client = llm_client

        # Инициализация компонентов
        self.validator = TradeValidator(config)
        self.calculator = RiskCalculator(config)
        self.ai_analyzer = ManualAIAnalyzer(llm_client, self.config) if llm_client else None

        # Состояние
        self.last_prediction: Optional[AIPrediction] = None
        self.pending_trade: Optional[TradeRequest] = None

        logger.info("Manual Trading Controller initialized")

    def prepare_trade(self, trade_params: Dict[str, Any],
                     account_balance: float) -> Tuple[bool, str, Optional[TradeRequest]]:
        """
        Подготовка сделки: валидация, расчеты, создание TradeRequest.

        Returns:
            (success, message, trade_request)
        """
        try:
            # Расчет объема позиции
            lot_size, calc_msg = self.calculator.calculate_lot_size(
                symbol=trade_params['symbol'],
                entry_price=trade_params['entry_price'],
                stop_loss=trade_params['stop_loss'],
                risk_amount=trade_params['risk_amount'],
                account_balance=account_balance
            )

            if lot_size == 0:
                return False, f"Не удалось рассчитать объем позиции: {calc_msg}", None

            # Расчет RR
            rr_ratio = self.calculator.calculate_rr_ratio(
                entry_price=trade_params['entry_price'],
                stop_loss=trade_params['stop_loss'],
                take_profit=trade_params['take_profit'],
                direction=trade_params['direction']
            )

            # Создание TradeRequest
            trade_request = TradeRequest(
                symbol=trade_params['symbol'],
                direction=trade_params['direction'],
                entry_price=trade_params['entry_price'],
                stop_loss=trade_params['stop_loss'],
                take_profit=trade_params['take_profit'],
                lot_size=lot_size,
                risk_amount=trade_params['risk_amount'],
                risk_reward_ratio=rr_ratio,
                source='manual',
                timestamp=datetime.now(),
                metadata={
                    'calculation': calc_msg,
                    'prepared_by': 'manual_trading_controller'
                }
            )

            # Валидация
            is_valid, error_msg = self.validator.validate_trade_request(trade_request)
            if not is_valid:
                return False, f"Валидация не пройдена: {error_msg}", None

            # Сохраняем как pending
            self.pending_trade = trade_request

            message = f"Сделка подготовлена: {lot_size:.2f} лотов, RR={rr_ratio:.2f}"
            logger.info(f"Trade prepared: {message}")

            return True, message, trade_request

        except Exception as e:
            logger.error(f"Trade preparation failed: {e}")
            return False, f"Ошибка подготовки: {e}", None

    def execute_trade(self, trade_request: Optional[TradeRequest] = None) -> Tuple[bool, str]:
        """
        Исполнение сделки через executor.

        Returns:
            (success, message)
        """
        try:
            # Используем переданный или pending trade
            request = trade_request or self.pending_trade

            if not request:
                return False, "Нет подготовленной сделки"

            if request.source != 'manual':
                return False, "Можно исполнять только ручные сделки"

            # Проверяем executor
            if not self.executor:
                return False, "Executor не доступен"

            # Исполняем через executor
            result = self.executor.execute_manual_trade(request)

            if result.success:
                message = f"Сделка открыта: тикет #{result.ticket}"
                logger.info(f"Manual trade executed: {message}")

                # Очищаем pending trade
                self.pending_trade = None

                return True, message
            else:
                error_msg = result.error_message or "Неизвестная ошибка"
                logger.error(f"Manual trade failed: {error_msg}")
                return False, f"Ошибка исполнения: {error_msg}"

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return False, f"Ошибка исполнения: {e}"

    def get_ai_prediction(self, trade_context: Dict[str, Any]) -> Optional[AIPrediction]:
        """
        Получение AI-прогноза для сделки.
        """
        try:
            if not self.ai_analyzer:
                logger.warning("AI analyzer not available")
                return None

            if not self.config.get('ENABLE_MANUAL_AI_PREDICT', False):
                logger.warning("AI prediction disabled in config")
                return None

            prediction = self.ai_analyzer.analyze_manual_trade(trade_context)

            if prediction:
                self.last_prediction = prediction
                logger.info(f"AI prediction generated: {prediction.market_bias}, confidence: {prediction.confidence}")
            else:
                logger.error("AI prediction failed")

            return prediction

        except Exception as e:
            logger.error(f"AI prediction error: {e}")
            return None

    def get_pending_trade_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о подготовленной сделке."""
        if not self.pending_trade:
            return None

        return {
            'symbol': self.pending_trade.symbol,
            'direction': self.pending_trade.direction,
            'lot_size': self.pending_trade.lot_size,
            'risk_amount': self.pending_trade.risk_amount,
            'rr_ratio': self.pending_trade.risk_reward_ratio,
            'entry_price': self.pending_trade.entry_price,
            'stop_loss': self.pending_trade.stop_loss,
            'take_profit': self.pending_trade.take_profit
        }

    def clear_pending_trade(self):
        """Очистка подготовленной сделки."""
        self.pending_trade = None
        logger.info("Pending trade cleared")

    def is_enabled(self) -> bool:
        """Проверка включена ли ручная торговля."""
        return self.config.get('enabled', False)
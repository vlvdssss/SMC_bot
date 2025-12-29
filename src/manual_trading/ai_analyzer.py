"""
Manual AI Analyzer

AI-анализ для ручной торговли.
Формирует прогнозы на основе рыночных данных и параметров сделки.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ..models import AIPrediction

logger = logging.getLogger(__name__)


class ManualAIAnalyzer:
    """AI-анализатор для ручной торговли."""

    def __init__(self, llm_client, config: dict):
        self.llm_client = llm_client
        self.config = config
        self.model = config.get('AI_MODEL', 'gpt-4o-mini')
        self.max_tokens = config.get('AI_MAX_TOKENS', 1000)

    def analyze_manual_trade(self, context: Dict[str, Any]) -> Optional[AIPrediction]:
        """
        Анализ ручной сделки с помощью AI.

        Args:
            context: Полный контекст сделки и рынка

        Returns:
            AIPrediction или None при ошибке
        """
        try:
            # Формируем prompt
            prompt = self._build_analysis_prompt(context)

            # Отправляем запрос
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3  # Стабильные ответы
            )

            # Парсим ответ
            content = response.choices[0].message.content
            logger.info(f"AI Response: {content}")

            prediction_data = self._parse_ai_response(content)
            if prediction_data:
                prediction = AIPrediction(
                    **prediction_data,
                    timestamp=datetime.now(),
                    context=context
                )
                return prediction

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Формирование промпта для AI."""
        symbol = context.get('symbol', 'EURUSD')
        timeframe = context.get('timeframe', 'H1')
        direction = context.get('direction', 'buy')
        entry = context.get('entry_price', 0)
        sl = context.get('stop_loss', 0)
        tp = context.get('take_profit', 0)
        rr = context.get('risk_reward_ratio', 0)

        # SMC структура
        smc_structure = context.get('smc_structure', 'Не определена')

        # ML bias
        ml_bias = context.get('ml_bias', 'Нейтральный')
        ml_confidence = context.get('ml_confidence', 0.5)

        # Новости
        news_status = context.get('news_status', 'Нет важных новостей')

        # Additional contextual hints
        volatility = context.get('volatility_est', 'N/A')
        price_distance = context.get('price_distance', 'N/A')
        account_balance = context.get('account_balance', 'N/A')

        prompt = f"""
Анализируй возможность ручной сделки:

ИНСТРУМЕНТ: {symbol}
ТАЙМФРЕЙМ: {timeframe}

ПАРАМЕТРЫ СДЕЛКИ:
- Направление: {direction.upper()}
- Вход: {entry}
- Stop Loss: {sl}
- Take Profit: {tp}
- Risk/Reward: {rr:.2f}

РЫНОЧНЫЙ КОНТЕКСТ:
- SMC структура: {smc_structure}
- ML bias: {ml_bias} (уверенность: {ml_confidence:.1%})
- Новости: {news_status}
- Волатильность (приблиз.): {volatility}
- Расстояние цены до входа: {price_distance}
- Баланс счета: {account_balance}

ПРОАНАЛИЗИРУЙ:
1. Соответствие сделки рыночным условиям
2. Риски и возможности
3. Уровни инвалидации
4. Вероятность успеха

Верни ответ в формате JSON с обязательными полями.
"""
        return prompt

    def _get_system_prompt(self) -> str:
        """Системный промпт для AI."""
        return """
Ты - опытный трейдер-аналитик. Анализируй ручные сделки на основе технического анализа.

ОЦЕНИВАЙ:
- Соответствие SMC структуре
- ML bias и уверенность
- Новостной фон
- Параметры риска

ВЕРНИ JSON с полями:
{
  "market_bias": "bullish|bearish|range",
  "trade_alignment": "aligned|neutral|risky",
  "scenarios": {
    "best_case": "описание",
    "worst_case": "описание"
  },
  "invalidation_levels": ["уровень1", "уровень2"],
  "confidence": "low|medium|high",
  "comment": "подробный анализ"
}

Будь объективен и консервативен в оценках.
"""

    def _parse_ai_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Парсинг ответа AI."""
        try:
            # Ищем JSON в ответе
            start = content.find('{')
            end = content.rfind('}') + 1

            if start == -1 or end == 0:
                logger.error("No JSON found in AI response")
                return None

            json_str = content[start:end]
            data = json.loads(json_str)

            # Валидация обязательных полей
            required_fields = ['market_bias', 'trade_alignment', 'scenarios',
                             'invalidation_levels', 'confidence', 'comment']

            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return None
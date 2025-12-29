"""
GPT News Filter для BAZA Trading Bot

Проверяет экономические события перед открытием сделки.
Стоимость: ~$0.001 за запрос (GPT-4o-mini)
"""

import os
from openai import OpenAI
from datetime import datetime
from typing import Tuple
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class GPTNewsFilter:
    def __init__(self):
        # API ключ из переменной окружения или конфига
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Дешёвая и быстрая модель

        # Кэш чтобы не спрашивать каждый раз
        self.cache = {}
        self.cache_duration = 3600  # 1 час

    def check_trading_safety(self, instrument: str) -> Tuple[bool, str, str]:
        """
        Проверяет безопасность торговли для инструмента.

        Args:
            instrument: 'XAUUSD' или 'EURUSD'

        Returns:
            Tuple[safe: bool, risk_level: str, reason: str]
            - safe: True если можно торговать
            - risk_level: 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
            - reason: Объяснение
        """

        # Проверяем кэш
        cache_key = f"{instrument}_{datetime.now().strftime('%Y-%m-%d_%H')}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Формируем запрос
        today = datetime.now().strftime("%Y-%m-%d")
        hour = datetime.now().hour

        prompt = f"""
Сегодня {today}, текущее время {hour}:00 UTC.

Проанализируй торговый инструмент {instrument}:
1. Есть ли сегодня крупные экономические события, которые могут вызвать высокую волатильность?
   (NFP, FOMC, ECB, CPI, GDP и т.д.)
2. Рискованно ли сейчас торговать? (открытие рынка, выход новостей, низкая ликвидность)

Для XAUUSD учитывай: решения ФРС, экономические данные США, геополитические события
Для EURUSD учитывай: решения ЕЦБ, экономические данные ЕС/США, важные выступления

Ответь ТОЛЬКО в этом формате:
RISK_LEVEL: [LOW/MEDIUM/HIGH/EXTREME]
SAFE_TO_TRADE: [YES/NO]
REASON: [Одно предложение объяснения на русском]

Пример:
RISK_LEVEL: HIGH
SAFE_TO_TRADE: NO
REASON: Сегодня заседание FOMC в 18:00 UTC, ожидаем высокую волатильность.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты финансовый аналитик рынка. Отвечай кратко и точно на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1  # Низкая температура для консистентности
            )

            answer = response.choices[0].message.content.strip()

            # Парсим ответ
            risk_level = "MEDIUM"
            safe = True
            reason = "No major events detected"

            for line in answer.split('\n'):
                if 'RISK_LEVEL:' in line:
                    risk_level = line.split(':')[1].strip()
                elif 'SAFE_TO_TRADE:' in line:
                    safe = 'YES' in line.upper()
                elif 'REASON:' in line:
                    reason = line.split(':', 1)[1].strip()

            result = (safe, risk_level, reason)

            # Кэшируем на час
            self.cache[cache_key] = result

            return result

        except Exception as e:
            # Если ошибка API — разрешаем торговлю (fail-safe)
            print(f"[GPT Filter] Error: {e}")
            return (True, "UNKNOWN", f"API error: {str(e)}")

    def should_reduce_risk(self, instrument: str) -> Tuple[bool, float]:
        """
        Проверяет нужно ли уменьшить риск.

        Returns:
            Tuple[reduce: bool, multiplier: float]
            - reduce: True если нужно уменьшить
            - multiplier: 0.5 = половина обычного риска
        """
        safe, risk_level, reason = self.check_trading_safety(instrument)

        if risk_level == "EXTREME":
            return (True, 0.0)  # Не торговать
        elif risk_level == "HIGH":
            return (True, 0.5)  # 50% от обычного риска
        elif risk_level == "MEDIUM":
            return (True, 0.75)  # 75% от обычного риска
        else:
            return (False, 1.0)  # Полный риск

    def get_market_summary(self) -> str:
        """Получает общую сводку по рынку."""

        prompt = """
Дай краткую сводку по рынку на сегодня (2-3 предложения):
- Ключевые события, влияющие на XAUUSD (золото) и EURUSD
- Общее настроение рынка
- Предупреждения для трейдеров

Будь краток.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Unable to get market summary: {e}"
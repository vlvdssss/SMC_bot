"""
GPT News Filter для BAZA Trading Bot

Проверяет экономические события перед открытием сделки.
Стоимость: ~$0.001 за запрос (GPT-4o-mini)
"""

import os
from openai import OpenAI
from datetime import datetime
from typing import Tuple

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
Today is {today}, current hour is {hour}:00 UTC.

For trading instrument {instrument}, analyze:
1. Are there any major economic events TODAY that could cause high volatility?
   (NFP, FOMC, ECB, CPI, GDP, etc.)
2. Is it a risky time to trade? (market open, news release, low liquidity)

For XAUUSD consider: Fed decisions, US economic data, geopolitical events
For EURUSD consider: ECB decisions, EU/US economic data, major speeches

Respond in this EXACT format:
RISK_LEVEL: [LOW/MEDIUM/HIGH/EXTREME]
SAFE_TO_TRADE: [YES/NO]
REASON: [One sentence explanation]

Example:
RISK_LEVEL: HIGH
SAFE_TO_TRADE: NO
REASON: FOMC meeting today at 18:00 UTC, expect high volatility.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial market analyst. Be concise and accurate."},
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
Give a brief market summary for today (2-3 sentences):
- Key events affecting XAUUSD (Gold) and EURUSD
- Overall market sentiment
- Any warnings for traders

Be concise.
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
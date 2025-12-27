"""Тест GPT фильтра"""

import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv('config/.env')

from src.ai.news_filter import GPTNewsFilter

def test_filter():
    print("Testing GPT News Filter...")
    print("=" * 50)

    filter = GPTNewsFilter()

    # Тест XAUUSD
    print("\n[XAUUSD]")
    safe, risk, reason = filter.check_trading_safety("XAUUSD")
    print(f"Safe: {safe}")
    print(f"Risk: {risk}")
    print(f"Reason: {reason}")

    # Тест EURUSD
    print("\n[EURUSD]")
    safe, risk, reason = filter.check_trading_safety("EURUSD")
    print(f"Safe: {safe}")
    print(f"Risk: {risk}")
    print(f"Reason: {reason}")

    # Общая сводка
    print("\n[Market Summary]")
    summary = filter.get_market_summary()
    print(summary)

    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_filter()
#!/usr/bin/env python3
"""
OpenAI API Diagnostic Tool
Проверяет работоспособность OpenAI API и выдаёт детальный отчёт
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI, APIError, RateLimitError, APIConnectionError, Timeout

def test_openai_connection():
    """Тестирует соединение с OpenAI API и выводит детальную диагностику."""
    
    print("=" * 80)
    print("OpenAI API Diagnostic Tool")
    print("=" * 80)
    print()
    
    # Step 1: Load API key
    print("📋 Step 1: Loading API key...")
    load_dotenv("config/.env")
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ ОШИБКА: API ключ не найден!")
        print()
        print("💡 Решение:")
        print("   1. Создай файл config/.env")
        print("   2. Добавь строку: OPENAI_API_KEY=sk-proj-...")
        print("   3. Перезапусти этот скрипт")
        print()
        return False
    
    print(f"✅ API ключ найден: {api_key[:15]}...{api_key[-4:]}")
    print()
    
    # Step 2: Validate format
    print("📋 Step 2: Validating key format...")
    if not api_key.startswith('sk-'):
        print(f"❌ ОШИБКА: Неверный формат ключа!")
        print(f"   Текущий ключ: {api_key[:30]}...")
        print(f"   OpenAI ключи должны начинаться с 'sk-' или 'sk-proj-'")
        print()
        return False
    
    print("✅ Формат ключа корректный")
    print()
    
    # Step 3: Initialize client
    print("📋 Step 3: Initializing OpenAI client...")
    try:
        client = OpenAI(api_key=api_key)
        print("✅ Client инициализирован")
        print()
    except Exception as e:
        print(f"❌ ОШИБКА при создании client: {type(e).__name__}")
        print(f"   Детали: {e}")
        print()
        return False
    
    # Step 4: Test models list (minimal API call)
    print("📋 Step 4: Testing API connection (models.list)...")
    try:
        response = client.models.list()
        models = [m.id for m in response.data]
        print(f"✅ API соединение работает!")
        print(f"   Доступно моделей: {len(models)}")
        print(f"   Примеры: {', '.join(models[:5])}...")
        print()
    except RateLimitError as e:
        print("❌ ОШИБКА: Rate Limit (превышен лимит запросов)")
        print(f"   Детали: {e}")
        print()
        print("💡 Решение:")
        print("   1. Проверь квоту: https://platform.openai.com/account/usage")
        print("   2. Подожди некоторое время и попробуй снова")
        print("   3. Убедись, что у тебя есть активный план/кредиты")
        print()
        return False
    except APIConnectionError as e:
        print("❌ ОШИБКА: Connection Failed (нет соединения)")
        print(f"   Детали: {e}")
        print()
        print("💡 Решение:")
        print("   1. Проверь интернет соединение")
        print("   2. Отключи VPN/Proxy (если используешь)")
        print("   3. Проверь firewall настройки")
        print()
        return False
    except APIError as e:
        if "invalid" in str(e).lower() and "key" in str(e).lower():
            print("❌ ОШИБКА: Invalid API Key (ключ неверный)")
            print(f"   Детали: {e}")
            print()
            print("💡 Решение:")
            print("   1. Проверь ключ на: https://platform.openai.com/api-keys")
            print("   2. Убедись, что ключ скопирован полностью (без пробелов)")
            print("   3. Создай новый ключ если старый не работает")
            print()
        else:
            print(f"❌ ОШИБКА API: {e.code if hasattr(e, 'code') else 'N/A'}")
            print(f"   Детали: {e}")
            print()
        return False
    except Exception as e:
        print(f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {type(e).__name__}")
        print(f"   Детали: {e}")
        print()
        return False
    
    # Step 5: Test actual completion (GPT call)
    print("📋 Step 5: Testing GPT completion (gpt-4o-mini)...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'test successful' in 2 words"}
            ],
            max_tokens=10,
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        print(f"✅ GPT completion работает!")
        print(f"   Model: {response.model}")
        print(f"   Response: {content}")
        print(f"   Tokens used: {response.usage.total_tokens}")
        print()
    except RateLimitError as e:
        print("❌ Rate Limit на completion")
        print(f"   Детали: {e}")
        print("   (models.list работает, но нет квоты на запросы)")
        print()
        return False
    except Exception as e:
        print(f"❌ ОШИБКА при completion: {type(e).__name__}")
        print(f"   Детали: {e}")
        print()
        return False
    
    # Step 6: Check gpt-4o availability
    print("📋 Step 6: Checking GPT-4o access...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "test"}
            ],
            max_tokens=5,
            temperature=0.0
        )
        print("✅ GPT-4o доступен!")
        print(f"   Model: {response.model}")
        print()
    except APIError as e:
        if "model" in str(e).lower() or "not found" in str(e).lower():
            print("⚠️ GPT-4o недоступен для твоего аккаунта")
            print(f"   Детали: {e}")
            print()
            print("💡 Решение:")
            print("   1. Убедись, что у тебя есть доступ к GPT-4")
            print("   2. Проверь тарифный план: https://platform.openai.com/account/billing")
            print("   3. Можно использовать gpt-4o-mini вместо gpt-4o (дешевле)")
            print()
            print("   (Измени в config/ai.yaml: model: gpt-4o-mini)")
            print()
        else:
            print(f"⚠️ Ошибка при проверке GPT-4o: {e}")
            print()
    except RateLimitError:
        print("⚠️ Rate limit - не могу проверить GPT-4o (но скорее всего работает)")
        print()
    except Exception as e:
        print(f"⚠️ Не удалось проверить GPT-4o: {type(e).__name__}: {e}")
        print()
    
    # Final summary
    print("=" * 80)
    print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 80)
    print()
    print("Твой OpenAI API настроен правильно и готов к использованию!")
    print()
    print("Рекомендации:")
    print("  • Следи за квотой: https://platform.openai.com/account/usage")
    print("  • Используй safety limits в config/ai.yaml (max_daily_calls, max_monthly_cost)")
    print("  • Проверяй баланс регулярно")
    print()
    
    return True


if __name__ == "__main__":
    success = test_openai_connection()
    sys.exit(0 if success else 1)

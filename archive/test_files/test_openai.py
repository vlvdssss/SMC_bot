#!/usr/bin/env python3
"""
OpenAI API Tester - перевірка роботи ChatGPT
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Завантажити .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  .env not found at: {env_path}")

# Отримати ключ
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("❌ OPENAI_API_KEY not found in environment!")
    print("Please add it to .env file:")
    print("OPENAI_API_KEY=sk-...")
    sys.exit(1)

# Показати маскований ключ
masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
print(f"✅ API Key found: {masked_key}")
print()

# Спробувати підключитись
try:
    client = OpenAI(api_key=api_key)
    print("🔄 Testing OpenAI API...")
    print()
    
    # Тест 1: Простий запит
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": "What is the capital of Ukraine?"}
        ],
        temperature=0.3,
        max_tokens=50
    )
    
    answer = response.choices[0].message.content
    usage = response.usage
    
    print("=" * 60)
    print("TEST 1: Simple Question")
    print("=" * 60)
    print(f"Question: What is the capital of Ukraine?")
    print(f"Answer: {answer}")
    print(f"Tokens used: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")
    print()
    
    # Тест 2: Аналіз ринку
    response2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional forex market analyst."},
            {"role": "user", "content": "Analyze XAUUSD (Gold) market in 2 sentences. Current price: 2650. Trend?"}
        ],
        temperature=0.5,
        max_tokens=100
    )
    
    analysis = response2.choices[0].message.content
    usage2 = response2.usage
    
    print("=" * 60)
    print("TEST 2: Market Analysis")
    print("=" * 60)
    print(f"Question: Analyze XAUUSD market")
    print(f"Analysis: {analysis}")
    print(f"Tokens used: {usage2.total_tokens} (prompt: {usage2.prompt_tokens}, completion: {usage2.completion_tokens})")
    print()
    
    # Тест 3: Перевірка моделей
    print("=" * 60)
    print("TEST 3: Available Models")
    print("=" * 60)
    models = client.models.list()
    gpt_models = [m.id for m in models.data if 'gpt' in m.id.lower()][:5]
    print("Available GPT models:")
    for model in gpt_models:
        print(f"  - {model}")
    print()
    
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"Total tokens used: {usage.total_tokens + usage2.total_tokens}")
    print(f"Estimated cost: ${(usage.total_tokens + usage2.total_tokens) * 0.000002:.6f}")
    
except Exception as e:
    print("=" * 60)
    print("❌ ERROR!")
    print("=" * 60)
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    import traceback
    print()
    print("Full traceback:")
    traceback.print_exc()
    sys.exit(1)

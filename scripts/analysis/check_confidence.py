import yaml

print("="*60)
print("ПРОВЕРКА ИЗМЕНЕНИЙ")
print("="*60)

# Проверяем конфиг
with open('config/ai.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

min_conf_config = config['market_analyst']['signals']['min_confidence']
print(f"\n1. config/ai.yaml:")
print(f"   min_confidence = {min_conf_config}")

# Проверяем код
from src.ai.pure_ai_trader import PureAITrader
min_conf_code = PureAITrader.MIN_CONFIDENCE

print(f"\n2. src/ai/pure_ai_trader.py:")
print(f"   MIN_CONFIDENCE = {min_conf_code}")

print(f"\n{'='*60}")
if min_conf_config == 75 and min_conf_code == 75:
    print("✅ УСПЕХ! Уверенность увеличена до 75%")
else:
    print(f"❌ ОШИБКА! config={min_conf_config}, code={min_conf_code}")
print("="*60)

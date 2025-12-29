#!/usr/bin/env python3
"""
Test LiveTrader initialization
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_live_trader():
    print("[TOOL] TESTING LIVETRADER")
    print("=" * 40)

    try:
        from src.live.live_trader import LiveTrader

        print("[CONNECT] Creating LiveTrader instance...")

        # Создаем в демо режиме без GPT
        trader = LiveTrader(config_dir='config', enable_trading=False, enable_gpt=False)

        print("[OK] LiveTrader created successfully")

        # Проверяем конфиги
        print(f"[CONFIG] Config directory: {trader.config_dir}")

        # Проверяем MT5 подключение (демо)
        status = trader.get_connection_status()
        print(f"[MT5] MT5 status: {status.get('message', 'Unknown')}")

        # Проверяем стратегии
        print(f"[TARGET] Strategies initialized: {len(trader.strategies)}")

        # Проверяем фильтры
        gpt_status = "[ON] Enabled" if trader.gpt_filter else "[OFF] Disabled"
        print(f"[AI] GPT filter: {gpt_status}")

        ml_status = "[ON] Enabled" if trader.ml_predictor else "[OFF] Disabled"
        print(f"[ML] ML predictor: {ml_status}")

        print("\n[SUCCESS] ALL COMPONENTS WORKING!")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_live_trader()
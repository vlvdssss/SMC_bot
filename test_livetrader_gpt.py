#!/usr/bin/env python3
"""
Test LiveTrader with GPT enabled
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_livetrader_gpt():
    from src.live.live_trader import LiveTrader

    print("[LAUNCH] Testing LiveTrader with GPT...")
    trader = LiveTrader(config_dir='config', enable_trading=False, enable_gpt=True)

    gpt_status = "Enabled" if trader.gpt_filter else "Disabled"
    print(f"[AI] GPT filter: {gpt_status}")

    if trader.gpt_filter:
        print("[OK] LiveTrader with GPT working!")
        return True
    else:
        print("[ERROR] GPT not initialized")
        return False

if __name__ == '__main__':
    test_livetrader_gpt()
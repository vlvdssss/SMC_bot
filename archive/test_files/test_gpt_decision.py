#!/usr/bin/env python3
"""
Test GPT Decision Engine v2.0
"""

import sys
import json
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import logger
from src.ai.market_analyst import MarketAnalystService

def test_decision_engine():
    """Test GPT Decision Engine with new format."""
    
    print("="*80)
    print("🧪 TESTING GPT DECISION ENGINE v2.0")
    print("="*80)
    
    # Initialize
    print("\n1. Initializing MarketAnalystService...")
    analyst = MarketAnalystService()
    
    # Run analysis
    print("\n2. Running market analysis for XAUUSD...")
    print("   - Capturing 4 timeframes (M5, M15, M30, H1)")
    print("   - Filtering HIGH-impact news only")
    print("   - Requesting decision format (no analysis text)")
    print()
    
    result = analyst.analyze_market('XAUUSD')
    
    # Display results
    print("\n" + "="*80)
    print("📊 ANALYSIS RESULTS")
    print("="*80)
    
    # Check format
    if "decision" in result:
        decision = result["decision"]
        print(f"\n✅ Decision Format: VALID")
        print(f"   Action: {decision.get('action')}")
        print(f"   Confidence: {decision.get('confidence')}%")
        print(f"   Block: {decision.get('block')}")
        
        if decision.get('action') in ['BUY', 'SELL']:
            if "trade" in result:
                trade = result["trade"]
                print(f"\n📈 Trade Details:")
                print(f"   Entry: ${trade.get('entry')}")
                print(f"   Stop Loss: ${trade.get('stop_loss')}")
                print(f"   Take Profit: ${trade.get('take_profit')}")
                print(f"   Risk/Reward: {trade.get('risk_reward')}")
            else:
                print(f"\n❌ ERROR: Missing 'trade' object for {decision.get('action')} action")
        else:
            print(f"\n⚪ No trade signal (action = {decision.get('action')})")
    else:
        print(f"\n❌ ERROR: Missing 'decision' field")
        print(f"   Response keys: {list(result.keys())}")
    
    # Full JSON
    print("\n" + "="*80)
    print("📄 FULL RESPONSE (JSON)")
    print("="*80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()

if __name__ == "__main__":
    try:
        test_decision_engine()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

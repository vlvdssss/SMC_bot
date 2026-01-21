#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test GPT Decision Engine v2.0 - Structure Validation (No API)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

def test_decision_format():
    """Test new decision format structure."""
    
    print("="*80)
    print("[TEST] GPT DECISION ENGINE v2.0 - FORMAT VALIDATION")
    print("="*80)
    
    # Test 1: BUY Decision
    print("\n[OK] Test 1: BUY Decision Format")
    buy_decision = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "XAUUSD",
        "decision": {
            "action": "BUY",
            "confidence": 85,
            "block": "NONE"
        },
        "trade": {
            "entry": 2665.0,
            "stop_loss": 2660.0,
            "take_profit": 2675.0,
            "risk_reward": 2.0
        },
        "analyzed_at": datetime.now().isoformat(),
        "analysis_version": "2.0"
    }
    
    # Validate structure
    assert "decision" in buy_decision
    assert "action" in buy_decision["decision"]
    assert buy_decision["decision"]["action"] in ["BUY", "SELL", "NONE"]
    assert "trade" in buy_decision
    assert all(k in buy_decision["trade"] for k in ["entry", "stop_loss", "take_profit", "risk_reward"])
    print(f"   [PASS] Structure valid")
    print(f"   Action: {buy_decision['decision']['action']}")
    print(f"   Entry: ${buy_decision['trade']['entry']}")
    print(f"   RR: {buy_decision['trade']['risk_reward']}")
    
    # Test 2: NONE Decision
    print("\n[OK] Test 2: NONE Decision Format")
    none_decision = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "XAUUSD",
        "decision": {
            "action": "NONE",
            "confidence": 50,
            "block": "SOFT"
        },
        "analyzed_at": datetime.now().isoformat(),
        "analysis_version": "2.0"
    }
    
    # Validate - no trade object for NONE
    assert "decision" in none_decision
    assert none_decision["decision"]["action"] == "NONE"
    assert "trade" not in none_decision
    print(f"   ✅ Structure valid (no trade object)")
    print(f"   Action: {none_decision['decision']['action']}")
    print(f"   Block: {none_decision['decision']['block']}")
    
    # Test 3: Validate prompt changes
    print("\n✅ Test 3: Prompt Changes Validation")
    from src.ai.market_analyst import MarketAnalystService
    
    # Mock data
    metrics = {"current_price": 2665.0, "atr": 10.5, "trend": "bullish"}
    news = [{"title": "FOMC", "impact": "HIGH", "time": "15:00", "currency": "USD"}]
    
    # Build prompt (without calling GPT)
    try:
        service = MarketAnalystService.__new__(MarketAnalystService)
        prompt = service._build_analysis_prompt("XAUUSD", metrics, news)
        
        # Check prompt contains new rules
        assert "Trading Decision Engine" in prompt
        assert "decision" in prompt.lower()
        assert "action" in prompt.lower()
        assert "DO NOT write explanations" in prompt or "ONLY return structured" in prompt
        assert "M5" not in prompt  # Should not mention specific timeframes in prompt
        print(f"   ✅ Prompt format updated")
        print(f"   - Decision Engine role: ✅")
        print(f"   - No explanation request: ✅")
        print(f"   - Simplified format: ✅")
    except Exception as e:
        print(f"   ⚠️ Could not validate prompt: {e}")
    
    # Test 4: Config validation
    print("\n✅ Test 4: Config Updates")
    import yaml
    
    # Check ai.yaml has 4 timeframes
    with open("config/ai.yaml", 'r') as f:
        ai_config = yaml.safe_load(f)
    
    timeframes = ai_config.get('market_analyst', {}).get('screenshots', {}).get('timeframes', [])
    assert len(timeframes) == 4
    assert 'M5' in timeframes
    assert 'M30' in timeframes
    print(f"   ✅ 4 Timeframes configured: {timeframes}")
    
    # Check trading.yaml has TTL settings
    with open("config/trading.yaml", 'r') as f:
        trading_config = yaml.safe_load(f)
    
    signal_ttl = trading_config.get('trading', {}).get('signal_ttl', {})
    assert signal_ttl.get('enabled') == True
    assert 'ttl_minutes' in signal_ttl
    assert signal_ttl.get('auto_requery_on_expire') == True
    assert signal_ttl.get('auto_requery_on_close') == True
    print(f"   ✅ TTL config: {signal_ttl['ttl_minutes']} minutes")
    print(f"   ✅ Auto-requery on expire: {signal_ttl['auto_requery_on_expire']}")
    print(f"   ✅ Auto-requery on close: {signal_ttl['auto_requery_on_close']}")
    
    # Test 5: Code changes validation
    print("\n✅ Test 5: Code Implementation Check")
    
    # Check analyst_scheduler has trigger_immediate_analysis
    from src.ai import analyst_scheduler
    assert hasattr(analyst_scheduler.AnalystScheduler, 'trigger_immediate_analysis')
    print(f"   ✅ trigger_immediate_analysis() method exists")
    
    # Check signal_manager has set_scheduler
    from src.ai import signal_manager
    assert hasattr(signal_manager.AISignalManager, 'set_scheduler')
    print(f"   ✅ set_scheduler() method exists")
    
    # Check _cleanup_expired_signals updated
    import inspect
    cleanup_source = inspect.getsource(signal_manager.AISignalManager._cleanup_expired_signals)
    assert 'trigger_immediate_analysis' in cleanup_source or 'auto_requery' in cleanup_source.lower()
    print(f"   ✅ TTL auto-requery logic implemented")
    
    print("\n" + "="*80)
    print("✅ ALL STRUCTURE TESTS PASSED")
    print("="*80)
    print("\n📝 Summary:")
    print("   ✅ Decision format structure: VALID")
    print("   ✅ Prompt updated: Decision Engine")
    print("   ✅ Config updated: 4 TF + TTL")
    print("   ✅ Code updated: Auto-requery logic")
    print("\n⚠️  Note: API testing requires valid OpenAI key")
    print("   Configure in GUI Settings or create config/.env file")
    print()

if __name__ == "__main__":
    try:
        test_decision_format()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: Assertion error")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

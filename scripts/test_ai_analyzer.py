#!/usr/bin/env python3
"""
Quick AI Analyzer Tester
Проверяет работу AI Market Analyst v2.0
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from datetime import datetime
from src.ai.market_analyst import MarketAnalystService
from src.ai.signal_manager import AISignalManager
from dotenv import load_dotenv

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_section(text):
    print("\n" + "-" * 60)
    print(f"  {text}")
    print("-" * 60)

def test_ai_analyzer():
    """Test AI Market Analyst"""
    print_header("AI MARKET ANALYST TESTER v2.0")
    
    # Load env
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env")
        return False
    
    print("✓ OpenAI API key loaded")
    
    # Initialize MT5
    print("\n📊 Initializing MetaTrader 5...")
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return False
    print("✓ MT5 initialized")
    
    # Initialize services
    print("\n🤖 Initializing AI services...")
    try:
        analyst = MarketAnalystService(api_key=api_key)
        print("✓ MarketAnalystService initialized")
        
        signal_manager = AISignalManager()
        print("✓ AISignalManager initialized")
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        mt5.shutdown()
        return False
    
    # Run analysis
    print_section("Running Market Analysis for XAUUSD")
    print("⏳ Analyzing... (this takes ~10-15 seconds)")
    
    try:
        start_time = datetime.now()
        analysis = analyst.analyze_market("XAUUSD")
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"✓ Analysis completed in {duration:.1f}s")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        mt5.shutdown()
        return False
    
    # Display results
    print_header("ANALYSIS RESULTS")
    
    # Summary
    summary = analysis.get('summary', {})
    print(f"\n📈 SENTIMENT: {summary.get('sentiment', 'N/A').upper()}")
    print(f"🎯 CONFIDENCE: {summary.get('confidence', 0)}%")
    print(f"📅 TIMESTAMP: {summary.get('analysis_time', 'N/A')}")
    
    # Trading blocks
    blocks = analysis.get('trading_blocks', {})
    block_type = blocks.get('block_type', 'none')
    block_reason = blocks.get('reason', 'No reason')
    
    print_section("Trading Blocks")
    block_icons = {
        'none': '✅',
        'bias': '↗️',
        'warning': '⚠️',
        'soft_block': '⛔',
        'hard_block': '🚫'
    }
    icon = block_icons.get(block_type, '❓')
    print(f"{icon} BLOCK TYPE: {block_type.upper()}")
    print(f"📝 REASON: {block_reason}")
    
    # Process through SignalManager
    print_section("SignalManager Processing")
    try:
        result = signal_manager.process_analysis(analysis)
        
        allowed, multiplier, reason = signal_manager.get_trading_permission("XAUUSD")
        print(f"{'✅' if allowed else '🚫'} TRADING: {'ALLOWED' if allowed else 'BLOCKED'}")
        print(f"📊 RISK MULTIPLIER: {multiplier:.2f}x")
        print(f"💬 DECISION REASON: {reason}")
        
    except Exception as e:
        print(f"❌ SignalManager processing failed: {e}")
    
    # Signals
    signals = analysis.get('signals', [])
    print_section(f"Trading Signals ({len(signals)} found)")
    
    if signals:
        for i, sig in enumerate(signals, 1):
            print(f"\n🎯 SIGNAL #{i}:")
            print(f"   Type: {sig.get('type', 'N/A').upper()}")
            print(f"   Entry: {sig.get('entry_price', 0):.2f}")
            print(f"   SL: {sig.get('stop_loss', 0):.2f}")
            print(f"   TP: {sig.get('take_profit', 0):.2f}")
            print(f"   Confidence: {sig.get('confidence', 0)}%")
            print(f"   Reasoning: {sig.get('reasoning', 'N/A')}")
    else:
        print("No trading signals generated")
    
    # Active signals check
    print_section("Active Signals Status")
    active = signal_manager.get_active_signals("XAUUSD")
    print(f"📌 Active signals in manager: {len(active)}")
    if active:
        for sig in active:
            print(f"   • {sig['type'].upper()} @ {sig['entry_price']:.2f} (Conf: {sig['confidence']}%)")
    
    # Detailed Analysis Display
    print_section("Detailed Analysis (Russian)")
    detailed = analysis.get('analysis', {})
    if detailed:
        sections = [
            ('trend', '### ТРЕНД'),
            ('support_resistance', '### УРОВНИ ПОДДЕРЖКИ И СОПРОТИВЛЕНИЯ'),
            ('patterns', '### ПАТТЕРНЫ'),
            ('entry_exit', '### ТОЧКИ ВХОДА И ВЫХОДА'),
            ('risk_assessment', '### ОЦЕНКА РИСКА'),
            ('news_impact', '### УЧЕТ НОВОСТЕЙ'),
            ('recommendation', '### РЕКОМЕНДАЦИИ')
        ]
        
        for key, title in sections:
            if key in detailed:
                print(f"\n{title}")
                print(detailed[key])
    else:
        print("⚠️  No detailed analysis found")
    
    # Raw structure check
    print_section("Data Structure Validation")
    checks = {
        'summary exists': 'summary' in analysis,
        'signals list': isinstance(analysis.get('signals'), list),
        'trading_blocks': 'trading_blocks' in analysis,
        'block_type valid': blocks.get('block_type') in ['none', 'bias', 'warning', 'soft_block', 'hard_block'],
        'sentiment present': bool(summary.get('sentiment')),
        'confidence value': 0 <= summary.get('confidence', 0) <= 100,
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_passed = False
    
    # Cleanup
    mt5.shutdown()
    
    print_header("TEST SUMMARY")
    if all_passed:
        print("✅ ALL CHECKS PASSED - AI Analyzer working correctly!")
        return True
    else:
        print("⚠️  SOME CHECKS FAILED - Review results above")
        return False

if __name__ == "__main__":
    try:
        success = test_ai_analyzer()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

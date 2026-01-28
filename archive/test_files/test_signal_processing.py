#!/usr/bin/env python3
"""
Тест для нового process_analysis() метода в SignalManager.
Проверяет все сценарии: BUY/SELL, NONE, position blocking, max 1 pending signal.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ai.signal_manager import AISignalManager
from datetime import datetime
import json


class MockExecutor:
    """Mock executor для тестирования."""
    
    def __init__(self):
        self.positions = {}
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol."""
        return symbol in self.positions
    
    def add_position(self, symbol: str):
        """Simulate opening position."""
        self.positions[symbol] = True
        print(f"[MockExecutor] Position opened for {symbol}")
    
    def remove_position(self, symbol: str):
        """Simulate closing position."""
        if symbol in self.positions:
            del self.positions[symbol]
            print(f"[MockExecutor] Position closed for {symbol}")


class MockScheduler:
    """Mock scheduler для тестирования."""
    
    def __init__(self):
        self.triggered_count = 0
    
    def trigger_immediate_analysis(self, reason: str = ""):
        """Mock trigger."""
        self.triggered_count += 1
        print(f"[MockScheduler] Triggered analysis #{self.triggered_count}: {reason}")


def test_buy_signal_creation():
    """Test 1: BUY signal creation."""
    print("\n" + "="*60)
    print("TEST 1: BUY Signal Creation")
    print("="*60)
    
    manager = AISignalManager()
    executor = MockExecutor()
    scheduler = MockScheduler()
    
    manager.set_executor(executor)
    manager.set_scheduler(scheduler)
    
    # Create BUY analysis
    analysis = {
        "symbol": "XAUUSD",
        "analysis_version": "2.0",
        "decision": {
            "action": "BUY",
            "confidence": 75,
            "block": "NONE"
        },
        "trade": {
            "entry": 2650.50,
            "stop_loss": 2645.00,
            "take_profit": 2660.00,
            "risk_reward": 1.7
        }
    }
    
    result = manager.process_analysis(analysis)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    print(f"Active signals: {len(manager.active_signals)}")
    
    if result["signals_created"] == 1:
        print("✅ TEST PASSED: Signal created")
    else:
        print("❌ TEST FAILED: Signal not created")
    
    return manager, executor, scheduler


def test_position_blocking():
    """Test 2: Position blocking (should not create signal if position exists)."""
    print("\n" + "="*60)
    print("TEST 2: Position Blocking")
    print("="*60)
    
    manager = AISignalManager()
    executor = MockExecutor()
    scheduler = MockScheduler()
    
    manager.set_executor(executor)
    manager.set_scheduler(scheduler)
    
    # Simulate existing position
    executor.add_position("XAUUSD")
    
    # Try to create BUY signal
    analysis = {
        "symbol": "XAUUSD",
        "decision": {
            "action": "BUY",
            "confidence": 80,
            "block": "NONE"
        },
        "trade": {
            "entry": 2650.50,
            "stop_loss": 2645.00,
            "take_profit": 2660.00,
            "risk_reward": 1.7
        }
    }
    
    result = manager.process_analysis(analysis)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    print(f"Active signals: {len(manager.active_signals)}")
    
    if result["signals_created"] == 0 and result.get("block_reason") == "position_already_open":
        print("✅ TEST PASSED: Signal blocked (position exists)")
    else:
        print("❌ TEST FAILED: Signal not blocked")


def test_max_pending_signals():
    """Test 3: Max 1 pending signal per symbol."""
    print("\n" + "="*60)
    print("TEST 3: Max 1 Pending Signal Limit")
    print("="*60)
    
    manager = AISignalManager()
    executor = MockExecutor()
    scheduler = MockScheduler()
    
    manager.set_executor(executor)
    manager.set_scheduler(scheduler)
    
    # Create first signal
    analysis1 = {
        "symbol": "XAUUSD",
        "decision": {
            "action": "BUY",
            "confidence": 70,
            "block": "NONE"
        },
        "trade": {
            "entry": 2650.50,
            "stop_loss": 2645.00,
            "take_profit": 2660.00,
            "risk_reward": 1.7
        }
    }
    
    result1 = manager.process_analysis(analysis1)
    print(f"\nFirst signal result: {json.dumps(result1, indent=2)}")
    print(f"Active signals: {len(manager.active_signals)}")
    
    # Try to create second signal for same symbol
    analysis2 = {
        "symbol": "XAUUSD",
        "decision": {
            "action": "SELL",
            "confidence": 85,
            "block": "NONE"
        },
        "trade": {
            "entry": 2655.00,
            "stop_loss": 2660.00,
            "take_profit": 2645.00,
            "risk_reward": 2.0
        }
    }
    
    result2 = manager.process_analysis(analysis2)
    print(f"\nSecond signal result: {json.dumps(result2, indent=2)}")
    print(f"Active signals: {len(manager.active_signals)}")
    
    if result1["signals_created"] == 1 and result2["signals_created"] == 0:
        if result2.get("block_reason") == "max_pending_signals_reached":
            print("✅ TEST PASSED: Second signal blocked (max 1 pending)")
        else:
            print("⚠️  TEST WARNING: Second signal blocked but wrong reason")
    else:
        print("❌ TEST FAILED: Max pending signals not enforced")


def test_none_decision():
    """Test 4: NONE decision (should schedule retry)."""
    print("\n" + "="*60)
    print("TEST 4: NONE Decision Retry Scheduling")
    print("="*60)
    
    manager = AISignalManager()
    executor = MockExecutor()
    scheduler = MockScheduler()
    
    manager.set_executor(executor)
    manager.set_scheduler(scheduler)
    
    analysis = {
        "symbol": "XAUUSD",
        "decision": {
            "action": "NONE",
            "confidence": 45,
            "block": "NONE"
        }
    }
    
    result = manager.process_analysis(analysis)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    print(f"Active signals: {len(manager.active_signals)}")
    
    if result["signals_created"] == 0 and result.get("retry_scheduled"):
        print("✅ TEST PASSED: NONE decision, retry scheduled")
    else:
        print("❌ TEST FAILED: Retry not scheduled")


def test_block_levels():
    """Test 5: Block levels (SOFT, HARD)."""
    print("\n" + "="*60)
    print("TEST 5: Block Levels")
    print("="*60)
    
    manager = AISignalManager()
    executor = MockExecutor()
    scheduler = MockScheduler()
    
    manager.set_executor(executor)
    manager.set_scheduler(scheduler)
    
    # Test SOFT block
    analysis_soft = {
        "symbol": "XAUUSD",
        "decision": {
            "action": "BUY",
            "confidence": 75,
            "block": "SOFT"
        },
        "trade": {
            "entry": 2650.50,
            "stop_loss": 2645.00,
            "take_profit": 2660.00,
            "risk_reward": 1.7
        }
    }
    
    result_soft = manager.process_analysis(analysis_soft)
    print(f"\nSOFT block result: {json.dumps(result_soft, indent=2)}")
    
    # Test HARD block
    analysis_hard = {
        "symbol": "EURUSD",
        "decision": {
            "action": "SELL",
            "confidence": 80,
            "block": "HARD"
        },
        "trade": {
            "entry": 1.0850,
            "stop_loss": 1.0870,
            "take_profit": 1.0820,
            "risk_reward": 1.5
        }
    }
    
    result_hard = manager.process_analysis(analysis_hard)
    print(f"\nHARD block result: {json.dumps(result_hard, indent=2)}")
    
    if result_soft["risk_multiplier"] == 0.5:
        print("✅ SOFT block: risk_multiplier = 0.5")
    else:
        print(f"❌ SOFT block: risk_multiplier = {result_soft['risk_multiplier']} (expected 0.5)")
    
    if result_hard["risk_multiplier"] == 0.0:
        print("✅ HARD block: risk_multiplier = 0.0")
    else:
        print(f"❌ HARD block: risk_multiplier = {result_hard['risk_multiplier']} (expected 0.0)")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SIGNAL MANAGER v2.0 - PROCESS_ANALYSIS TESTS")
    print("="*60)
    
    try:
        # Run all tests
        test_buy_signal_creation()
        test_position_blocking()
        test_max_pending_signals()
        test_none_decision()
        test_block_levels()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

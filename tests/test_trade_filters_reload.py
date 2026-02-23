#!/usr/bin/env python3
"""
Quick Test: TradeFilters Config Reload
Verify that TradeFilters reads from trading.yaml (no conflicts) and reloads without restart
"""

import sys
import yaml
from pathlib import Path
from src.core.config_manager import get_config_manager
from src.core.trade_filters import TradeFilters
from src.core.logger import logger

def test_filters_config_reload():
    """Test that TradeFilters reloads config without restart"""
    
    print("\n" + "="*60)
    print("TEST: TradeFilters Config Reload (trading.yaml)")
    print("="*60)
    
    # 1. Get ConfigManager
    config_mgr = get_config_manager()
    
    # 2. Create TradeFilters (should load initial config)
    print("\n[1] Creating TradeFilters...")
    filters = TradeFilters(mt5_connector=None, config_manager=config_mgr)
    
    initial_confidence = filters.config['min_confidence']
    initial_daily_limit = filters.config['daily_limit']
    initial_spread = filters.config['max_spread_pips']
    
    print(f"\n[2] Initial config:")
    print(f"  min_confidence: {initial_confidence}")
    print(f"  daily_limit: {initial_daily_limit}")
    print(f"  max_spread_pips: {initial_spread}")
    
    # 3. Modify trading.yaml
    print(f"\n[3] Modifying trading.yaml...")
    trading_path = Path("config/trading.yaml")
    
    with open(trading_path, 'r', encoding='utf-8') as f:
        trading_config = yaml.safe_load(f)
    
    # Change values in trading.filters section
    filters_config = trading_config['trading']['filters']
    old_confidence = filters_config['min_confidence']
    old_daily = filters_config['daily_limit']
    old_spread = filters_config['max_spread_pips']
    
    filters_config['min_confidence'] = 99  # Set extremely high
    filters_config['daily_limit'] = 1       # Set very low
    filters_config['max_spread_pips'] = 0.5 # Set very tight
    
    with open(trading_path, 'w', encoding='utf-8') as f:
        yaml.dump(trading_config, f, default_flow_style=False)
    
    print(f"  ✅ Modified trading.yaml:")
    print(f"    min_confidence: {old_confidence} → 99")
    print(f"    daily_limit: {old_daily} → 1")
    print(f"    max_spread_pips: {old_spread} → 0.5")
    
    # 4. Force reload via ConfigManager
    print(f"\n[4] Forcing config reload...")
    config_mgr.reload_all()
    
    # 5. Check if TradeFilters picked up changes
    print(f"\n[5] Checking TradeFilters config after reload:")
    new_confidence = filters.config['min_confidence']
    new_daily_limit = filters.config['daily_limit']
    new_spread = filters.config['max_spread_pips']
    
    print(f"  min_confidence: {new_confidence}")
    print(f"  daily_limit: {new_daily_limit}")
    print(f"  max_spread_pips: {new_spread}")
    
    # 6. Verify changes
    success = True
    
    if new_confidence == 99:
        print(f"  ✅ min_confidence updated correctly")
    else:
        print(f"  ❌ min_confidence NOT updated (expected 99, got {new_confidence})")
        success = False
    
    if new_daily_limit == 1:
        print(f"  ✅ daily_limit updated correctly")
    else:
        print(f"  ❌ daily_limit NOT updated (expected 1, got {new_daily_limit})")
        success = False
    
    if new_spread == 0.5:
        print(f"  ✅ max_spread_pips updated correctly")
    else:
        print(f"  ❌ max_spread_pips NOT updated (expected 0.5, got {new_spread})")
        success = False
    
    # 7. Restore original values
    print(f"\n[6] Restoring original trading.yaml values...")
    filters_config['min_confidence'] = old_confidence
    filters_config['daily_limit'] = old_daily
    filters_config['max_spread_pips'] = old_spread
    
    with open(trading_path, 'w', encoding='utf-8') as f:
        yaml.dump(trading_config, f, default_flow_style=False)
    
    config_mgr.reload_all()
    
    print(f"  ✅ Restored original values")
    
    # 8. Final result
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED: TradeFilters hot reload works!")
        print("   Source: trading.yaml (single source of truth, no conflicts)")
        print("="*60)
        return 0
    else:
        print("❌ TEST FAILED: TradeFilters not reading from config!")
        print("="*60)
        return 1


if __name__ == "__main__":
    try:
        exit_code = test_filters_config_reload()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

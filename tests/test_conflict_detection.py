"""
Тест обнаружения конфликтов в конфигурациях
После рефакторинга должно быть 0 конфликтов (все параметры в trading.yaml)
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.config_manager import get_config_manager
from src.gui.dialogs_v2 import EffectiveConfigDialog
import tkinter as tk

def test_conflict_detection():
    """Тест обнаружения конфликтов параметров"""
    
    print("=" * 60)
    print("TEST: Zero Conflicts After Refactoring")
    print("="*60)
    
    # Get ConfigManager
    config_manager = get_config_manager()
    
    print("\n[1] Loading configs...")
    ai_config = config_manager.load_config('ai.yaml')
    trading_config = config_manager.load_config('trading.yaml')
    
    # Check trade_filters NOT in ai.yaml anymore
    print("\n[2] Verifying trade_filters removed from ai.yaml:")
    ai_trade_filters = ai_config.get('market_analyst', {}).get('trade_filters')
    
    if ai_trade_filters is None:
        print(f"  ✅ trade_filters NOT in ai.yaml (good - eliminated duplicates)")
    else:
        print(f"  ❌ trade_filters STILL in ai.yaml (bad - conflict not resolved)")
        print(f"     Found: {ai_trade_filters.keys()}")
    
    # Check parameters now ONLY in trading.yaml
    print("\n[3] Verifying all filter parameters in trading.yaml:")
    
    trading_filters = trading_config.get('trading', {}).get('filters', {})
    
    expected_params = [
        'min_confidence', 'max_spread_pips', 'daily_limit', 
        'cooldown_after_win', 'cooldown_after_loss', 'cooldown_after_2_losses',
        'htf_timeframe', 'htf_ema_fast', 'htf_ema_slow',
        'min_rr', 'min_setup_score', 'enabled'
    ]
    
    missing = []
    for param in expected_params:
        if param in trading_filters:
            print(f"  ✅ trading.filters.{param} = {trading_filters[param]}")
        else:
            print(f"  ❌ trading.filters.{param} MISSING!")
            missing.append(param)
    
    # Test _detect_conflicts method
    print("\n[4] Testing EffectiveConfigDialog._detect_conflicts()...")
    
    # Create dummy root window (not visible)
    root = tk.Tk()
    root.withdraw()
    
    # Create dialog (doesn't show, just creates internal structure)
    dialog = EffectiveConfigDialog(root, config_manager)
    
    # Get effective config
    effective = config_manager.get_effective_config()
    configs = effective.get('configs', {})
    
    # Detect conflicts
    conflicts = dialog._detect_conflicts(configs)
    
    print(f"  Found {len(conflicts)} conflicts")
    
    if conflicts:
        print("\n[5] ❌ UNEXPECTED CONFLICTS FOUND:")
        for i, conflict in enumerate(conflicts, 1):
            print(f"\n  Conflict #{i}: {conflict['param']}")
            print(f"    Sources:")
            for source in conflict['sources']:
                print(f"      • {source['file']}: {source['path']} = {source['value']}")
            print(f"    Winner: {conflict['winner']}")
            print(f"    Reason: {conflict['reason']}")
    else:
        print("  ✅ No conflicts detected (single source of truth architecture)")
    
    # Close window
    root.destroy()
    
    print("\n" + "=" * 60)
    
    success = (ai_trade_filters is None) and (len(missing) == 0) and (len(conflicts) == 0)
    
    if success:
        print("✅ TEST PASSED: Zero conflicts!")
        print("   • trade_filters removed from ai.yaml")
        print("   • All 12 filter parameters in trading.yaml")
        print("   • No duplicate definitions detected")
        print("   • Single source of truth confirmed")
    else:
        print("❌ TEST FAILED:")
        if ai_trade_filters is not None:
            print("   • trade_filters still in ai.yaml (should be removed)")
        if missing:
            print(f"   • Missing parameters in trading.yaml: {missing}")
        if conflicts:
            print(f"   • {len(conflicts)} conflicts still detected")
    
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == '__main__':
    exit_code = test_conflict_detection()
    sys.exit(exit_code)

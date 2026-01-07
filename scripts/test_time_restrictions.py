#!/usr/bin/env python3
"""
Time Restrictions Tester
Проверяет работу временных ограничений торговли
"""

import sys
from pathlib import Path
from datetime import datetime, time, timedelta

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.signal_manager import AISignalManager

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_result(time_str, allowed, reason):
    icon = "✅" if allowed else "🚫"
    print(f"{icon} {time_str:20} | {reason}")

def test_time_restrictions():
    """Test time restrictions logic"""
    print_header("TIME RESTRICTIONS TESTER")
    
    manager = AISignalManager()
    
    # Test scenarios
    scenarios = [
        # Format: (weekday, hour, expected_allowed, description)
        (0, 10, True, "Monday 10:00 - Normal trading"),
        (0, 1, False, "Monday 01:00 - Weekend block ending"),
        (1, 15, True, "Tuesday 15:00 - Normal trading"),
        (1, 22, False, "Tuesday 22:00 - Night block start"),
        (1, 23, False, "Tuesday 23:00 - Night block"),
        (2, 0, False, "Wednesday 00:00 - Night block"),
        (2, 1, False, "Wednesday 01:00 - Night block"),
        (2, 2, True, "Wednesday 02:00 - Night block end"),
        (3, 12, True, "Thursday 12:00 - Normal trading"),
        (4, 21, True, "Friday 21:00 - Normal trading"),
        (4, 22, False, "Friday 22:00 - Weekend block start"),
        (5, 10, False, "Saturday 10:00 - Weekend block"),
        (5, 22, False, "Saturday 22:00 - Weekend block"),
        (6, 15, False, "Sunday 15:00 - Weekend block"),
        (6, 23, False, "Sunday 23:00 - Weekend block"),
    ]
    
    print("\n📅 Testing time restrictions:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for weekday, hour, expected_allowed, description in scenarios:
        # Simulate time
        test_time = datetime.now()
        test_time = test_time.replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        )
        # Adjust weekday (0=Monday)
        days_diff = weekday - test_time.weekday()
        test_time = test_time + timedelta(days=days_diff)
        
        # Test with simulated time
        allowed, reason = manager._is_trading_time_allowed(test_time)
        
        # Check result
        if allowed == expected_allowed:
            print_result(description, allowed, reason)
            passed += 1
        else:
            print(f"❌ FAILED: {description}")
            print(f"   Expected: {expected_allowed}, Got: {allowed}")
            print(f"   Reason: {reason}")
            failed += 1
    
    # Test current time
    print_header("CURRENT TIME CHECK")
    allowed, risk_multiplier, reason = manager.get_trading_permission()
    now = datetime.now()
    print(f"Current time: {now.strftime('%A %H:%M')}")
    print(f"Trading allowed: {'✅ YES' if allowed else '🚫 NO'}")
    print(f"Risk multiplier: {risk_multiplier:.1f}")
    print(f"Reason: {reason}")
    
    # Summary
    print_header("TEST SUMMARY")
    total = passed + failed
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️  {failed} TESTS FAILED")
        return False

def show_schedule():
    """Show analysis schedule from config"""
    print_header("ANALYSIS SCHEDULE")
    
    import yaml
    config_path = Path("config/ai.yaml")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        schedule = config.get('market_analyst', {}).get('schedule', {})
        times = schedule.get('times', [])
        
        print(f"Schedule enabled: {schedule.get('enabled', False)}")
        print(f"Analysis times: {len(times)} per day")
        print("\n📅 Schedule:")
        for t in times:
            print(f"   • {t}")
        
        # Show restrictions
        restrictions = schedule.get('restrictions', {})
        print("\n🚫 Time Restrictions:")
        
        night = restrictions.get('night_block', {})
        if night.get('enabled'):
            print(f"   • Night block: {night.get('start')} - {night.get('end')}")
        
        weekend = restrictions.get('weekend_block', {})
        if weekend.get('enabled'):
            print(f"   • Weekend block: Friday {weekend.get('friday_start')} - Monday {weekend.get('monday_end')}")
            
    except Exception as e:
        print(f"❌ Failed to load config: {e}")

if __name__ == "__main__":
    try:
        show_schedule()
        success = test_time_restrictions()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

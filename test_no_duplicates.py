"""
Test: Check for duplicate parameters in CONFIG_SCHEMA
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.gui.dialogs_v2 import CONFIG_SCHEMA

def test_no_duplicates():
    """Check that CONFIG_SCHEMA has no semantic duplicates"""
    
    print("=" * 60)
    print("TEST: No Duplicate Parameters in CONFIG_SCHEMA")
    print("=" * 60)
    
    # Check for known problematic duplicates
    problematic_params = {
        'min_confidence': [],
        'max_spread': [],
        'daily_limit': [],
    }
    
    # Scan all parameters
    for key, meta in CONFIG_SCHEMA.items():
        label = meta.get('label', '').lower()
        
        # Check min_confidence
        if 'min confidence' in label or 'min_confidence' in key:
            problematic_params['min_confidence'].append({
                'key': key,
                'tab': meta.get('tab'),
                'label': meta.get('label'),
                'default': meta.get('default')
            })
        
        # Check spread
        if 'spread' in label or 'spread' in key:
            problematic_params['max_spread'].append({
                'key': key,
                'tab': meta.get('tab'),
                'label': meta.get('label'),
                'default': meta.get('default')
            })
        
        # Check daily limit
        if ('daily' in label and 'limit' in label) or 'daily_limit' in key or ('trades' in label and 'day' in label):
            problematic_params['daily_limit'].append({
                'key': key,
                'tab': meta.get('tab'),
                'label': meta.get('label'),
                'default': meta.get('default')
            })
    
    # Report results
    print("\n[1] Checking for duplicates...")
    
    issues_found = []
    
    # Min Confidence
    print("\n[2] Min Confidence Parameters:")
    conf_params = problematic_params['min_confidence']
    if len(conf_params) == 0:
        print("  ❌ ERROR: No min_confidence parameter found!")
        issues_found.append("No min_confidence parameter")
    elif len(conf_params) == 1:
        print(f"  ✅ Only 1 min_confidence parameter:")
        print(f"     • {conf_params[0]['key']} in {conf_params[0]['tab']} tab")
        print(f"       Label: {conf_params[0]['label']}")
        print(f"       Default: {conf_params[0]['default']}")
    else:
        print(f"  ❌ DUPLICATE: Found {len(conf_params)} min_confidence parameters:")
        for p in conf_params:
            print(f"     • {p['key']} in {p['tab']} tab (default: {p['default']})")
        issues_found.append(f"Duplicate min_confidence ({len(conf_params)})")
    
    # Max Spread
    print("\n[3] Max Spread Parameters:")
    spread_params = problematic_params['max_spread']
    if len(spread_params) == 0:
        print("  ❌ ERROR: No max_spread parameter found!")
        issues_found.append("No max_spread parameter")
    elif len(spread_params) == 1:
        print(f"  ✅ Only 1 max_spread parameter:")
        print(f"     • {spread_params[0]['key']} in {spread_params[0]['tab']} tab")
        print(f"       Label: {spread_params[0]['label']}")
        print(f"       Default: {spread_params[0]['default']}")
    else:
        print(f"  ❌ DUPLICATE: Found {len(spread_params)} max_spread parameters:")
        for p in spread_params:
            print(f"     • {p['key']} in {p['tab']} tab (default: {p['default']})")
        issues_found.append(f"Duplicate max_spread ({len(spread_params)})")
    
    # Daily Limit
    print("\n[4] Daily Trade Limit Parameters:")
    limit_params = problematic_params['daily_limit']
    if len(limit_params) == 0:
        print("  ❌ ERROR: No daily_limit parameter found!")
        issues_found.append("No daily_limit parameter")
    elif len(limit_params) == 1:
        print(f"  ✅ Only 1 daily_limit parameter:")
        print(f"     • {limit_params[0]['key']} in {limit_params[0]['tab']} tab")
        print(f"       Label: {limit_params[0]['label']}")
        print(f"       Default: {limit_params[0]['default']}")
    else:
        print(f"  ❌ DUPLICATE: Found {len(limit_params)} daily_limit parameters:")
        for p in limit_params:
            print(f"     • {p['key']} in {p['tab']} tab (default: {p['default']})")
        issues_found.append(f"Duplicate daily_limit ({len(limit_params)})")
    
    # Summary
    print("\n" + "=" * 60)
    if not issues_found:
        print("✅ TEST PASSED: No duplicate parameters found!")
        print("   • min_confidence: 1 (in Filters)")
        print("   • max_spread: 1 (in Filters)")
        print("   • daily_limit: 1 (in Filters)")
    else:
        print("❌ TEST FAILED: Issues found:")
        for issue in issues_found:
            print(f"   • {issue}")
    print("=" * 60)
    
    return 0 if not issues_found else 1

if __name__ == '__main__':
    exit_code = test_no_duplicates()
    sys.exit(exit_code)

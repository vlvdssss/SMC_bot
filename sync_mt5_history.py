#!/usr/bin/env python3
"""
🔄 MT5 History Sync Tool - Ручная синхронизация истории сделок из MT5
Используй когда нужно восстановить пропущенные сделки в trades_history.csv
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime, timedelta
from src.core.mt5_manager import MT5Manager
import logging

# Helper function for data paths
def get_data_path(filename):
    """Get path to data file."""
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir / filename

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def sync_history(days: int = 7, force: bool = False):
    """Синхронизация истории сделок из MT5."""
    
    print("=" * 80)
    print("🔄 MT5 HISTORY SYNC TOOL")
    print("=" * 80)
    
    # Load MT5 config
    print("\n📁 Loading MT5 configuration...")
    import yaml
    config_path = Path(__file__).parent / 'config' / 'mt5.yaml'
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        mt5_config = yaml.safe_load(f)
    
    connection = mt5_config.get('mt5', {}).get('connection', {})
    login = connection.get('login')
    password = connection.get('password')
    server = connection.get('server')
    
    if not all([login, password, server]):
        print("❌ MT5 credentials missing in config!")
        return False
    
    print(f"✅ Config loaded (Login: {login}, Server: {server})")
    
    # Connect to MT5
    print("\n📡 Connecting to MT5...")
    mt5_manager = MT5Manager()
    
    if not mt5_manager.connect(login=login, password=password, server=server):
        print("❌ Failed to connect to MT5!")
        return False
    
    print("✅ Connected to MT5")
    
    # Get account info
    account = mt5_manager.get_account_info()
    if account:
        print(f"📊 Account: {account.get('login', 'N/A')}")
        print(f"💰 Balance: ${account.get('balance', 0):.2f}")
        print(f"📈 Equity: ${account.get('equity', 0):.2f}")
    
    # Get trade history from MT5
    print(f"\n📥 Loading trade history from MT5 (last {days} days)...")
    mt5_trades = mt5_manager.get_trade_history(days=days)
    
    if not mt5_trades:
        print("⚠️ No trades found in MT5 history")
        return True
    
    print(f"✅ Found {len(mt5_trades)} trades in MT5")
    
    # Load existing trades from file
    trades_file = get_data_path('trades_history.json')
    existing_trades = []
    existing_ids = set()
    
    if trades_file.exists():
        try:
            with open(trades_file, 'r', encoding='utf-8') as f:
                existing_trades = json.load(f)
                existing_ids = {int(t.get('id', 0)) for t in existing_trades if t.get('id')}
            print(f"📂 Found {len(existing_trades)} trades in history file")
        except Exception as e:
            print(f"⚠️ Failed to load existing history: {e}")
    else:
        print("📂 No existing history file found")
    
    # Find new trades
    new_trades = []
    for trade in mt5_trades:
        trade_id = int(trade.get('id', 0))
        if trade_id and (trade_id not in existing_ids or force):
            new_trades.append(trade)
    
    if not new_trades:
        print("\n✅ All trades are already synchronized!")
        return True
    
    print(f"\n🆕 Found {len(new_trades)} new trades to add:")
    print("-" * 80)
    
    # Show new trades
    for i, trade in enumerate(new_trades, 1):
        pnl_icon = "✅" if trade.get('pnl', 0) > 0 else ("❌" if trade.get('pnl', 0) < 0 else "⚖️")
        print(f"{pnl_icon} {i:2d}. {trade['date']} {trade['time']}: "
              f"{trade['direction']:4s} {trade['instrument']:6s} "
              f"({trade['volume']:.2f} lot) → ${trade['pnl']:+.2f}")
    
    print("-" * 80)
    total_pnl = sum(t.get('pnl', 0) for t in new_trades)
    print(f"💰 Total P&L from new trades: ${total_pnl:+.2f}")
    
    # Confirm
    if not force:
        response = input("\n❓ Add these trades to history? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Sync cancelled")
            return False
    
    # Add new trades to history
    print("\n💾 Saving new trades...")
    
    # Merge with existing (avoid duplicates)
    all_trades = existing_trades.copy()
    added_count = 0
    
    for trade in new_trades:
        trade_id = int(trade.get('id', 0))
        if trade_id not in existing_ids:
            all_trades.append(trade)
            existing_ids.add(trade_id)
            added_count += 1
    
    # Save to JSON
    try:
        temp_file = trades_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(all_trades, f, indent=2, ensure_ascii=False, default=str)
        temp_file.replace(trades_file)
        print(f"✅ Saved {len(all_trades)} trades to JSON")
    except Exception as e:
        print(f"❌ Failed to save JSON: {e}")
        return False
    
    # Export to CSV
    print("📊 Exporting to CSV...")
    try:
        import csv
        csv_file = get_data_path('trades_history.csv')
        
        fieldnames = [
            'id', 'date', 'time', 'instrument', 'direction', 
            'volume', 'entry_price', 'exit_price', 'sl', 'tp',
            'pnl', 'commission', 'swap', 'duration_minutes',
            'close_reason', 'strategy', 'confidence'
        ]
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for trade in all_trades:
                row = {
                    'id': trade.get('id', ''),
                    'date': trade.get('date', ''),
                    'time': trade.get('time', ''),
                    'instrument': trade.get('instrument', trade.get('symbol', '')),
                    'direction': trade.get('direction', ''),
                    'volume': trade.get('volume', 0),
                    'entry_price': trade.get('entry_price', 0),
                    'exit_price': trade.get('exit_price', trade.get('price', 0)),
                    'sl': trade.get('sl', 0),
                    'tp': trade.get('tp', 0),
                    'pnl': trade.get('pnl', 0),
                    'commission': trade.get('commission', 0),
                    'swap': trade.get('swap', 0),
                    'duration_minutes': trade.get('duration_minutes', 0),
                    'close_reason': trade.get('close_reason', ''),
                    'strategy': trade.get('strategy', 'AI'),
                    'confidence': trade.get('confidence', 0)
                }
                writer.writerow(row)
        
        print(f"✅ Exported {len(all_trades)} trades to CSV")
    
    except Exception as e:
        print(f"❌ Failed to export CSV: {e}")
        return False
    
    print("\n" + "=" * 80)
    print(f"✅ SYNC COMPLETE! Added {added_count} new trades")
    print(f"📊 Total trades in history: {len(all_trades)}")
    print("=" * 80)
    
    # Disconnect
    mt5_manager.disconnect()
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync trade history from MT5')
    parser.add_argument('--days', type=int, default=7, help='Number of days to sync (default: 7)')
    parser.add_argument('--force', action='store_true', help='Force re-sync all trades (ignore duplicates)')
    
    args = parser.parse_args()
    
    try:
        success = sync_history(days=args.days, force=args.force)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

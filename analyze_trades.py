#!/usr/bin/env python3
"""
Trade History Analyzer - Анализ истории сделок
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_trades():
    """Analyze trade history and show statistics"""
    
    # Load CSV
    csv_path = Path('data/trades_history.csv')
    if not csv_path.exists():
        print("❌ Trade history not found!")
        return
    
    df = pd.read_csv(csv_path)
    
    if len(df) == 0:
        print("❌ No trades found in history!")
        return
    
    print("=" * 80)
    print("📊 TRADE HISTORY ANALYSIS")
    print("=" * 80)
    
    # ОБЩАЯ СТАТИСТИКА
    total_trades = len(df)
    total_pnl = df['pnl'].sum()
    wins = len(df[df['pnl'] > 0])
    losses = len(df[df['pnl'] < 0])
    breakeven = len(df[df['pnl'] == 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
    avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losses > 0 else 0
    
    print(f"\n🎯 OVERALL STATISTICS:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Wins: {wins} ({win_rate:.1f}%)")
    print(f"  Losses: {losses} ({100-win_rate:.1f}%)")
    print(f"  Breakeven: {breakeven}")
    print(f"  Total P&L: ${total_pnl:.2f}")
    print(f"  Avg Win: ${avg_win:.2f}")
    print(f"  Avg Loss: ${avg_loss:.2f}")
    
    if avg_loss != 0:
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        print(f"  Profit Factor: {profit_factor:.2f}")
    
    # ПО ИНСТРУМЕНТАМ
    print(f"\n💰 BY INSTRUMENT:")
    for instrument in df['instrument'].unique():
        inst_df = df[df['instrument'] == instrument]
        inst_pnl = inst_df['pnl'].sum()
        inst_trades = len(inst_df)
        inst_wins = len(inst_df[inst_df['pnl'] > 0])
        inst_wr = (inst_wins / inst_trades * 100) if inst_trades > 0 else 0
        print(f"  {instrument}: {inst_trades} trades, ${inst_pnl:.2f} P&L, {inst_wr:.1f}% WR")
    
    # ПО НАПРАВЛЕНИЯМ
    print(f"\n📈 BY DIRECTION:")
    for direction in ['BUY', 'SELL']:
        dir_df = df[df['direction'] == direction]
        if len(dir_df) > 0:
            dir_pnl = dir_df['pnl'].sum()
            dir_trades = len(dir_df)
            dir_wins = len(dir_df[dir_df['pnl'] > 0])
            dir_wr = (dir_wins / dir_trades * 100) if dir_trades > 0 else 0
            print(f"  {direction}: {dir_trades} trades, ${dir_pnl:.2f} P&L, {dir_wr:.1f}% WR")
    
    # ТОП 5 ЛУЧШИХ СДЕЛОК
    print(f"\n🏆 TOP 5 BEST TRADES:")
    top_trades = df.nlargest(5, 'pnl')[['date', 'time', 'instrument', 'direction', 'pnl']]
    for idx, trade in top_trades.iterrows():
        print(f"  {trade['date']} {trade['time']}: {trade['direction']} {trade['instrument']} → ${trade['pnl']:.2f}")
    
    # ТОП 5 ХУДШИХ СДЕЛОК
    print(f"\n💔 TOP 5 WORST TRADES:")
    worst_trades = df.nsmallest(5, 'pnl')[['date', 'time', 'instrument', 'direction', 'pnl']]
    for idx, trade in worst_trades.iterrows():
        print(f"  {trade['date']} {trade['time']}: {trade['direction']} {trade['instrument']} → ${trade['pnl']:.2f}")
    
    # ПОСЛЕДНИЕ 10 СДЕЛОК
    print(f"\n📋 LAST 10 TRADES:")
    recent = df.tail(10)[['date', 'time', 'instrument', 'direction', 'volume', 'pnl']]
    for idx, trade in recent.iterrows():
        pnl_color = "✅" if trade['pnl'] > 0 else ("❌" if trade['pnl'] < 0 else "⚖️")
        print(f"  {pnl_color} {trade['date']} {trade['time']}: {trade['direction']} {trade['instrument']} "
              f"({trade['volume']} lot) → ${trade['pnl']:.2f}")
    
    # ДНЕВНАЯ СТАТИСТИКА
    print(f"\n📅 DAILY BREAKDOWN:")
    df['date'] = pd.to_datetime(df['date'])
    daily = df.groupby(df['date'].dt.date).agg({
        'pnl': ['sum', 'count']
    }).round(2)
    daily.columns = ['P&L', 'Trades']
    print(daily.tail(7).to_string())
    
    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        analyze_trades()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

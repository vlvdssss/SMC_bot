#!/usr/bin/env python3
"""Проверка сделок за сегодня"""
import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

today_start = datetime(2026, 1, 15, 0, 0)
now = datetime.now()

history = mt5.history_deals_get(today_start, now)

print(f"\n📊 Сделки за сегодня ({now.strftime('%Y-%m-%d')}):")
print("="*60)

total_pnl = 0
for deal in history:
    if deal.profit != 0:
        time_str = datetime.fromtimestamp(deal.time).strftime("%H:%M:%S")
        print(f"  Ticket: {deal.ticket}")
        print(f"  Symbol: {deal.symbol}")
        print(f"  Profit: ${deal.profit:.2f}")
        print(f"  Time: {time_str}")
        print("-"*60)
        total_pnl += deal.profit

print(f"\n💰 Total PnL today: ${total_pnl:.2f}")
print("="*60)

mt5.shutdown()

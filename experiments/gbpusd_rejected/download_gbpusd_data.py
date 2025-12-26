"""
Download GBPUSD historical data from MT5.

Downloads H1 and M15 data for 2023-2025.
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os

# Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

print("[*] MT5 initialized")

# Symbol
symbol = "GBPUSD"

# Date range
start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 12, 20, tzinfo=timezone.utc)

print(f"\n[*] Downloading {symbol} data...")
print(f"    From: {start_date.strftime('%Y-%m-%d')}")
print(f"    To: {end_date.strftime('%Y-%m-%d')}")

# Download H1
print("\n[*] Downloading H1 data...")
h1_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_date, end_date)

if h1_rates is None or len(h1_rates) == 0:
    print("[!] Failed to download H1 data")
    mt5.shutdown()
    quit()

df_h1 = pd.DataFrame(h1_rates)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
print(f"    H1 bars: {len(df_h1)}")

# Download M15
print("\n[*] Downloading M15 data...")

# M15 in chunks (по году)
m15_frames = []

for year in [2023, 2024, 2025]:
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    year_end = datetime(year, 12, 31, 23, 59, tzinfo=timezone.utc) if year < 2025 else end_date
    
    print(f"    Downloading {year}...")
    m15_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, year_start, year_end)
    
    if m15_rates is None or len(m15_rates) == 0:
        print(f"    [!] Failed for {year}")
        continue
    
    df_chunk = pd.DataFrame(m15_rates)
    df_chunk['time'] = pd.to_datetime(df_chunk['time'], unit='s')
    m15_frames.append(df_chunk)
    print(f"    {year}: {len(df_chunk)} bars")

if len(m15_frames) == 0:
    print("[!] Failed to download M15 data")
    mt5.shutdown()
    quit()

df_m15 = pd.concat(m15_frames, ignore_index=True)
print(f"    Total M15 bars: {len(df_m15)}")

# Save to CSV
output_dir = "data/backtest"
os.makedirs(output_dir, exist_ok=True)

h1_file = os.path.join(output_dir, "GBPUSD_H1_2023_2025.csv")
m15_file = os.path.join(output_dir, "GBPUSD_M15_2023_2025.csv")

df_h1.to_csv(h1_file, index=False)
df_m15.to_csv(m15_file, index=False)

print(f"\n[✓] Data saved:")
print(f"    H1: {h1_file}")
print(f"    M15: {m15_file}")

# Shutdown MT5
mt5.shutdown()
print("\n[✓] Done!")

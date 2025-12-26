"""
Download data for SCREENING instruments

Instruments:
1) USDCHF
2) EURGBP
3) NZDUSD
4) USDJPY
5) AUDCAD
6) XAGUSD

Timeframes: H1, M15
Period: 2023-01-01 to 2025-12-20
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os


def initialize_mt5():
    """Initialize MT5 connection"""
    if not mt5.initialize():
        print(f"MT5 initialization failed, error code: {mt5.last_error()}")
        return False
    print("MT5 initialized successfully")
    return True


def download_instrument_data(symbol: str, timeframe, start_date: datetime, end_date: datetime):
    """Download data for one instrument and timeframe"""
    print(f"\nDownloading {symbol} {timeframe}...")
    
    # Convert timeframe to MT5 constant
    if timeframe == "H1":
        mt5_timeframe = mt5.TIMEFRAME_H1
        tf_str = "H1"
    elif timeframe == "M15":
        mt5_timeframe = mt5.TIMEFRAME_M15
        tf_str = "M15"
    else:
        print(f"Unknown timeframe: {timeframe}")
        return None
    
    # For M15, download by year to avoid "Invalid params" error
    if timeframe == "M15":
        all_data = []
        current_year = start_date.year
        end_year = end_date.year
        
        while current_year <= end_year:
            year_start = datetime(current_year, 1, 1)
            year_end = datetime(current_year, 12, 31, 23, 59, 59)
            
            # Adjust boundaries
            if current_year == start_date.year:
                year_start = start_date
            if current_year == end_year:
                year_end = end_date
            
            print(f"  Downloading {current_year}...")
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, year_start, year_end)
            
            if rates is not None and len(rates) > 0:
                all_data.append(pd.DataFrame(rates))
                print(f"  {current_year}: {len(rates)} bars")
            else:
                print(f"  {current_year}: Failed - {mt5.last_error()}")
            
            current_year += 1
        
        if not all_data:
            print(f"Failed to get data for {symbol} {timeframe}")
            return None
        
        # Combine all years
        df = pd.concat(all_data, ignore_index=True)
        
    else:
        # Get data
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            print(f"Failed to get data for {symbol} {timeframe}: {mt5.last_error()}")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(rates)
    
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Rename columns
    df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'tick_volume': 'Volume'
    }, inplace=True)
    
    # Select only OHLCV
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    
    print(f"Downloaded {len(df)} bars for {symbol} {timeframe}")
    
    return df


def save_data(df: pd.DataFrame, symbol: str, timeframe: str):
    """Save data to CSV"""
    os.makedirs('data/backtest', exist_ok=True)
    
    filename = f"data/backtest/{symbol}_{timeframe}_2023_2025.csv"
    df.to_csv(filename)
    print(f"Saved to {filename}")


def main():
    """Main function"""
    # Instruments to download
    instruments = [
        'USDCHF',
        'EURGBP',
        'NZDUSD',
        'USDJPY',
        'AUDCAD',
        'XAGUSD'
    ]
    
    # Timeframes
    timeframes = ['H1', 'M15']
    
    # Date range
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 20)
    
    print("=" * 60)
    print("DOWNLOADING SCREENING DATA")
    print("=" * 60)
    print(f"Instruments: {', '.join(instruments)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print("=" * 60)
    
    # Initialize MT5
    if not initialize_mt5():
        return
        
    try:
        # Download data for each instrument and timeframe
        for symbol in instruments:
            print(f"\n{'=' * 60}")
            print(f"INSTRUMENT: {symbol}")
            print(f"{'=' * 60}")
            
            for timeframe in timeframes:
                df = download_instrument_data(symbol, timeframe, start_date, end_date)
                
                if df is not None:
                    save_data(df, symbol, timeframe)
                else:
                    print(f"WARNING: Failed to download {symbol} {timeframe}")
                    
        print("\n" + "=" * 60)
        print("DOWNLOAD COMPLETED")
        print("=" * 60)
        
    finally:
        mt5.shutdown()
        print("\nMT5 connection closed")


if __name__ == "__main__":
    main()

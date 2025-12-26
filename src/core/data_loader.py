"""Data loader for trading strategies H1 and M15 data."""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional


class DataLoader:
    """Load and filter H1 and M15 data."""

    def __init__(self,
                 instrument: str = 'xauusd',
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 h1_path: Optional[str] = None,
                 m15_path: Optional[str] = None):
        """
        Initialize data loader.

        Args:
            instrument: Instrument name (xauusd, us30)
            start_date: Start date filter (YYYY-MM-DD), inclusive
            end_date: End date filter (YYYY-MM-DD), inclusive
            h1_path: Custom path to H1 CSV file (optional)
            m15_path: Custom path to M15 CSV file (optional)
        """
        instrument = instrument.lower()
        
        # Default paths
        if h1_path is None:
            h1_path = f'data/backtest/{instrument.upper()}_H1_2023_2025.csv'
        if m15_path is None:
            m15_path = f'data/backtest/{instrument.upper()}_M15_2023_2025.csv'
        
        self.instrument = instrument
        self.h1_path = Path(h1_path)
        self.m15_path = Path(m15_path)
        self.start_date = pd.to_datetime(start_date) if start_date else None
        self.end_date = pd.to_datetime(end_date) if end_date else None

    def load(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load and filter H1 and M15 data."""
        # Load H1
        h1 = pd.read_csv(self.h1_path)
        h1['time'] = pd.to_datetime(h1['time'])
        h1 = h1.sort_values('time').reset_index(drop=True)

        # Load M15
        m15 = pd.read_csv(self.m15_path)
        m15['time'] = pd.to_datetime(m15['time'])
        m15 = m15.sort_values('time').reset_index(drop=True)
        
        # Filter by date range
        if self.start_date:
            h1 = h1[h1['time'] >= self.start_date].reset_index(drop=True)
            m15 = m15[m15['time'] >= self.start_date].reset_index(drop=True)

        if self.end_date:
            # Include entire end_date (until 23:59:59)
            end_datetime = self.end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            h1 = h1[h1['time'] <= end_datetime].reset_index(drop=True)
            m15 = m15[m15['time'] <= end_datetime].reset_index(drop=True)

        return h1, m15

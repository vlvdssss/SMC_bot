#!/usr/bin/env python3
"""
Chart Screenshot Service - Captures MT5 charts for AI analysis

Creates visual snapshots of price charts for GPT-4 Vision analysis.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
import MetaTrader5 as mt5
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
import pandas as pd

from src.core.logger import logger


class ChartScreenshotService:
    """Service for capturing chart screenshots for AI analysis."""
    
    def __init__(self):
        """Initialize screenshot service."""
        self.output_dir = Path("data/screenshots")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("[Screenshot] Service initialized")
    
    def capture_chart(
        self, 
        symbol: str, 
        timeframe: int, 
        bars: int = 100
    ) -> Optional[str]:
        """
        Capture chart screenshot using matplotlib.
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            bars: Number of bars to display
        
        Returns:
            Path to saved screenshot or None
        """
        try:
            # Get data from MT5
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
            if rates is None:
                logger.error(f"[Screenshot] Failed to get rates for {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Create figure
            fig, ax = plt.subplots(figsize=(14, 8), facecolor='#1a1a1a')
            ax.set_facecolor('#1a1a1a')
            
            # Plot candlesticks
            self._plot_candlesticks(ax, df)
            
            # Add moving averages
            self._add_moving_averages(ax, df)
            
            # Add support/resistance zones
            self._add_sr_zones(ax, df)
            
            # Styling
            timeframe_str = self._timeframe_to_string(timeframe)
            ax.set_title(
                f"{symbol} - {timeframe_str} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                color='white', fontsize=14, fontweight='bold'
            )
            ax.set_xlabel('Time', color='white')
            ax.set_ylabel('Price', color='white')
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.2, color='gray')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{timeframe_str}_{timestamp}.png"
            filepath = self.output_dir / filename
            
            plt.savefig(filepath, facecolor='#1a1a1a', edgecolor='none', dpi=150)
            plt.close()
            
            logger.info(f"[Screenshot] Captured: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"[Screenshot] Capture failed: {e}")
            return None
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlestick chart."""
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Bullish candles (green)
        ax.bar(up.time, up.close - up.open, bottom=up.open, 
               color='#00ff88', width=0.0006, alpha=0.8)
        ax.bar(up.time, up.high - up.close, bottom=up.close, 
               color='#00ff88', width=0.0001)
        ax.bar(up.time, up.open - up.low, bottom=up.low, 
               color='#00ff88', width=0.0001)
        
        # Bearish candles (red)
        ax.bar(down.time, down.open - down.close, bottom=down.close, 
               color='#ff4757', width=0.0006, alpha=0.8)
        ax.bar(down.time, down.high - down.open, bottom=down.open, 
               color='#ff4757', width=0.0001)
        ax.bar(down.time, down.close - down.low, bottom=down.low, 
               color='#ff4757', width=0.0001)
    
    def _add_moving_averages(self, ax, df: pd.DataFrame):
        """Add EMA lines."""
        df['ema12'] = df['close'].ewm(span=12).mean()
        df['ema26'] = df['close'].ewm(span=26).mean()
        
        ax.plot(df.time, df.ema12, color='#00d4aa', linewidth=1.5, 
                label='EMA 12', alpha=0.8)
        ax.plot(df.time, df.ema26, color='#ff6b6b', linewidth=1.5, 
                label='EMA 26', alpha=0.8)
        
        ax.legend(loc='upper left', facecolor='#1a1a1a', 
                 edgecolor='gray', fontsize=9)
    
    def _add_sr_zones(self, ax, df: pd.DataFrame):
        """Add support/resistance zones."""
        # 24h high/low as zones
        high_24 = df['high'].tail(24).max() if len(df) >= 24 else df['high'].max()
        low_24 = df['low'].tail(24).min() if len(df) >= 24 else df['low'].min()
        
        ax.axhline(high_24, color='#ff4757', linestyle='--', 
                   linewidth=1, alpha=0.5, label='24H High')
        ax.axhline(low_24, color='#00ff88', linestyle='--', 
                   linewidth=1, alpha=0.5, label='24H Low')
        
        # Current price line
        current = df['close'].iloc[-1]
        ax.axhline(current, color='#ffd93d', linestyle='-', 
                   linewidth=2, alpha=0.7, label='Current Price')
    
    def _timeframe_to_string(self, timeframe: int) -> str:
        """Convert MT5 timeframe to string."""
        timeframes = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1"
        }
        return timeframes.get(timeframe, f"TF_{timeframe}")
    
    def cleanup_old_screenshots(self, days: int = 7):
        """Remove screenshots older than specified days."""
        try:
            cutoff = datetime.now().timestamp() - (days * 86400)
            removed = 0
            
            for file in self.output_dir.glob("*.png"):
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    removed += 1
            
            if removed > 0:
                logger.info(f"[Screenshot] Cleaned up {removed} old screenshots")
        
        except Exception as e:
            logger.error(f"[Screenshot] Cleanup failed: {e}")


if __name__ == "__main__":
    # Test
    service = ChartScreenshotService()
    path = service.capture_chart("XAUUSD", mt5.TIMEFRAME_H1, 100)
    print(f"Screenshot saved: {path}")

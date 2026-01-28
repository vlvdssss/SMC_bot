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

# CRITICAL: Set matplotlib backend BEFORE importing pyplot
# This prevents "main thread is not in main loop" errors in background threads
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for threading

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
            
            # Create figure with higher quality
            fig, ax = plt.subplots(figsize=(16, 10), facecolor='#0d1117')
            ax.set_facecolor('#0d1117')
            
            # Plot candlesticks
            self._plot_candlesticks(ax, df)
            
            # Add moving averages
            self._add_moving_averages(ax, df)
            
            # Add support/resistance zones
            self._add_sr_zones(ax, df)
            
            # Styling with better visibility
            timeframe_str = self._timeframe_to_string(timeframe)
            ax.set_title(
                f"{symbol} - {timeframe_str} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                color='#ffffff', fontsize=16, fontweight='bold', pad=15
            )
            ax.set_xlabel('Time', color='#c9d1d9', fontsize=12, fontweight='bold')
            ax.set_ylabel('Price', color='#c9d1d9', fontsize=12, fontweight='bold')
            ax.tick_params(colors='#c9d1d9', labelsize=10)
            ax.grid(True, alpha=0.25, color='#30363d', linestyle='--', linewidth=0.8)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{timeframe_str}_{timestamp}.png"
            filepath = self.output_dir / filename
            
            # Save and close figure explicitly
            try:
                # High quality: DPI 200, optimized for GPT-4o Vision
                plt.savefig(filepath, facecolor='#0d1117', edgecolor='none', 
                           dpi=200, bbox_inches='tight', pad_inches=0.1)
                logger.info(f"[Screenshot] Captured: {filename} (DPI: 200)")
                return str(filepath)
            finally:
                # CRITICAL: Always close figure to prevent memory leaks
                plt.close(fig)
            
        except Exception as e:
            logger.error(f"[Screenshot] Capture failed for {symbol} {timeframe}: {str(e)}")
            # Close any open figures
            plt.close('all')
            return None
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlestick chart with improved visibility."""
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Bullish candles (brighter green with borders)
        ax.bar(up.time, up.close - up.open, bottom=up.open, 
               color='#26de81', edgecolor='#20bf6b', width=0.0006, alpha=0.9, linewidth=0.5)
        ax.bar(up.time, up.high - up.close, bottom=up.close, 
               color='#26de81', width=0.0001)
        ax.bar(up.time, up.open - up.low, bottom=up.low, 
               color='#26de81', width=0.0001)
        
        # Bearish candles (brighter red with borders)
        ax.bar(down.time, down.open - down.close, bottom=down.close, 
               color='#fc5c65', edgecolor='#eb3b5a', width=0.0006, alpha=0.9, linewidth=0.5)
        ax.bar(down.time, down.high - down.open, bottom=down.open, 
               color='#fc5c65', width=0.0001)
        ax.bar(down.time, down.close - down.low, bottom=down.low, 
               color='#fc5c65', width=0.0001)
    
    def _add_moving_averages(self, ax, df: pd.DataFrame):
        """Add EMA lines with better visibility."""
        df['ema12'] = df['close'].ewm(span=12).mean()
        df['ema26'] = df['close'].ewm(span=26).mean()
        
        # Brighter colors with thicker lines
        ax.plot(df.time, df.ema12, color='#45aaf2', linewidth=2.5, 
                label='EMA 12 (Fast)', alpha=0.9, linestyle='-')
        ax.plot(df.time, df.ema26, color='#fd79a8', linewidth=2.5, 
                label='EMA 26 (Slow)', alpha=0.9, linestyle='-')
        
        ax.legend(loc='upper left', facecolor='#161b22', 
                 edgecolor='#30363d', fontsize=11, framealpha=0.9)
    
    def _add_sr_zones(self, ax, df: pd.DataFrame):
        """Add support/resistance zones with better visibility."""
        # 24h high/low as zones
        high_24 = df['high'].tail(24).max() if len(df) >= 24 else df['high'].max()
        low_24 = df['low'].tail(24).min() if len(df) >= 24 else df['low'].min()
        
        # Thicker lines with better colors
        ax.axhline(high_24, color='#ee5a6f', linestyle='--', 
                   linewidth=2, alpha=0.7, label='24H Resistance')
        ax.axhline(low_24, color='#1dd1a1', linestyle='--', 
                   linewidth=2, alpha=0.7, label='24H Support')
        
        # Current price line - bright yellow
        current = df['close'].iloc[-1]
        ax.axhline(current, color='#fed330', linestyle='-', 
                   linewidth=3, alpha=0.85, label=f'Current: ${current:.2f}')
        
        # Add price labels on the right
        ax.text(df['time'].iloc[-1], high_24, f'  ${high_24:.2f}', 
                color='#ee5a6f', fontsize=10, va='center', fontweight='bold')
        ax.text(df['time'].iloc[-1], low_24, f'  ${low_24:.2f}', 
                color='#1dd1a1', fontsize=10, va='center', fontweight='bold')
    
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

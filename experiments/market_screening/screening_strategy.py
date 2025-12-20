"""
Unified Screening Strategy - SMC Retracement

НАЗНАЧЕНИЕ:
Единая логика для FAST SCREENING нескольких инструментов.
НЕТ адаптации под конкретный рынок.

ЛОГИКА:
- HTF (H1): BOS direction filter
- LTF (M15): OB retracement entries
- Premium/Discount zones
- RR 2:1
- Risk 0.5%

ИСПОЛЬЗУЕТСЯ ДЛЯ:
USDCHF, EURGBP, NZDUSD, USDJPY, AUDCAD, XAGUSD
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class ScreeningStrategy:
    """
    Unified SMC Retracement Strategy for Market Screening
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.name = f"SMC_Screening_{symbol}"
        
        # UNIFIED PARAMETERS (одинаковые для всех инструментов)
        self.risk_percent = 0.5  # 0.5% per trade
        self.risk_reward = 2.0   # RR 2:1
        self.max_trades_per_day = 1
        
        # HTF parameters (H1)
        self.htf_swing_lookback = 10  # bars для определения swing
        
        # LTF parameters (M15)
        self.ltf_ob_lookback = 20  # bars для поиска OB
        self.impulse_min_pips = 15  # минимальный импульс для OB
        
        # Premium/Discount
        self.discount_threshold = 0.5  # ниже 50% от swing range
        self.premium_threshold = 0.5   # выше 50% от swing range
        
        # State
        self.position = None
        self.last_trade_date = None
        self.h1_direction = None  # 'bullish' or 'bearish'
        self.h1_swing_high = None
        self.h1_swing_low = None
        
        # Debug counters
        self.debug_stats = {
            'total_bars': 0,
            'h1_direction_found': 0,
            'ob_found': 0,
            'price_in_ob': 0,
            'premium_discount_ok': 0,
            'signals_generated': 0
        }
        
    def analyze(self, data_h1: pd.DataFrame, data_m15: pd.DataFrame, 
                current_idx: int) -> Optional[Dict]:
        """
        Main analysis method
        
        Returns:
            Dict with signal or None
        """
        self.debug_stats['total_bars'] += 1
        
        # Get current date
        current_date = data_m15.index[current_idx].date()
        
        # Check max trades per day
        if self.last_trade_date == current_date:
            return None
            
        # Step 1: Determine HTF direction (H1)
        h1_idx = self._get_h1_index(data_h1, data_m15.index[current_idx])
        if h1_idx < self.htf_swing_lookback:
            return None
            
        self._update_h1_direction(data_h1, h1_idx)
        
        if self.h1_direction is None:
            return None
        
        self.debug_stats['h1_direction_found'] += 1
            
        # Step 2: Find OB on LTF (M15)
        if current_idx < self.ltf_ob_lookback:
            return None
            
        ob_zone = self._find_order_block(data_m15, current_idx)
        
        if ob_zone is None:
            return None
        
        self.debug_stats['ob_found'] += 1
            
        # Step 3: Check if price in OB zone
        current_price = data_m15['Close'].iloc[current_idx]
        
        if not self._is_price_in_ob(current_price, ob_zone):
            return None
        
        self.debug_stats['price_in_ob'] += 1
            
        # Step 4: Check Premium/Discount
        if not self._check_premium_discount(current_price, ob_zone):
            return None
        
        self.debug_stats['premium_discount_ok'] += 1
            
        # Step 5: Generate signal
        signal = self._generate_signal(data_m15, current_idx, ob_zone)
        
        if signal:
            self.last_trade_date = current_date
            self.debug_stats['signals_generated'] += 1
            
        return signal
        
    def _get_h1_index(self, data_h1: pd.DataFrame, m15_timestamp) -> int:
        """Find corresponding H1 index for M15 timestamp"""
        h1_timestamps = data_h1.index
        # Find closest H1 bar at or before M15 timestamp
        valid_indices = h1_timestamps <= m15_timestamp
        if not valid_indices.any():
            return -1
        return valid_indices.sum() - 1
        
    def _update_h1_direction(self, data_h1: pd.DataFrame, h1_idx: int):
        """Update HTF direction based on BOS"""
        if h1_idx < self.htf_swing_lookback:
            return
            
        # Get PREVIOUS swing high/low (EXCLUDING current bar)
        lookback_data = data_h1.iloc[h1_idx - self.htf_swing_lookback:h1_idx]
        
        swing_high = lookback_data['High'].max()
        swing_low = lookback_data['Low'].min()
        
        current_high = data_h1['High'].iloc[h1_idx]
        current_low = data_h1['Low'].iloc[h1_idx]
        
        # Check for BOS (current bar breaks previous swing)
        if current_high > swing_high:
            self.h1_direction = 'bullish'
            self.h1_swing_high = swing_high
            self.h1_swing_low = swing_low
        elif current_low < swing_low:
            self.h1_direction = 'bearish'
            self.h1_swing_high = swing_high
            self.h1_swing_low = swing_low
            
    def _find_order_block(self, data_m15: pd.DataFrame, current_idx: int) -> Optional[Dict]:
        """Find Order Block on M15"""
        if current_idx < self.ltf_ob_lookback:
            return None
            
        # Look at last 20 bars before current
        lookback_data = data_m15.iloc[current_idx - self.ltf_ob_lookback:current_idx]
        
        if len(lookback_data) < 3:
            return None
        
        # Current price (to measure impulse to)
        current_price = data_m15['Close'].iloc[current_idx]
        
        # Find impulse moves (scan backwards through lookback)
        for i in range(len(lookback_data) - 1, 0, -1):  # Stop at 1, not 0
            if i == 0:  # Skip if no OB candle available
                continue
                
            ob_candle = lookback_data.iloc[i - 1]  # Potential OB candle
            impulse_start_price = lookback_data['Close'].iloc[i]  # After OB
            
            # Measure impulse from start to current price
            impulse_pips = abs(current_price - impulse_start_price) * 10000
            
            if impulse_pips < self.impulse_min_pips:
                continue
                
            # Bullish impulse (price moved up)
            if current_price > impulse_start_price and self.h1_direction == 'bullish':
                return {
                    'type': 'bullish',
                    'high': ob_candle['High'],
                    'low': ob_candle['Low'],
                    'close': ob_candle['Close']
                }
                
            # Bearish impulse (price moved down)
            if current_price < impulse_start_price and self.h1_direction == 'bearish':
                return {
                    'type': 'bearish',
                    'high': ob_candle['High'],
                    'low': ob_candle['Low'],
                    'close': ob_candle['Close']
                }
                
        return None
        
    def _is_price_in_ob(self, current_price: float, ob_zone: Dict) -> bool:
        """Check if current price is in OB zone"""
        return ob_zone['low'] <= current_price <= ob_zone['high']
        
    def _check_premium_discount(self, current_price: float, ob_zone: Dict) -> bool:
        """Check Premium/Discount zones"""
        if self.h1_swing_high is None or self.h1_swing_low is None:
            return False
            
        swing_range = self.h1_swing_high - self.h1_swing_low
        
        if swing_range == 0:
            return False
            
        # Calculate position in range (0 = low, 1 = high)
        price_position = (current_price - self.h1_swing_low) / swing_range
        
        # Bullish: should be in discount (below 0.5)
        if ob_zone['type'] == 'bullish':
            return price_position < self.discount_threshold
            
        # Bearish: should be in premium (above 0.5)
        if ob_zone['type'] == 'bearish':
            return price_position > self.premium_threshold
            
        return False
        
    def _generate_signal(self, data_m15: pd.DataFrame, current_idx: int, 
                        ob_zone: Dict) -> Optional[Dict]:
        """Generate trading signal"""
        current_price = data_m15['Close'].iloc[current_idx]
        
        if ob_zone['type'] == 'bullish':
            # Long setup
            entry = current_price
            stop_loss = ob_zone['low']
            risk = entry - stop_loss
            
            if risk <= 0:
                return None
                
            take_profit = entry + (risk * self.risk_reward)
            
            return {
                'direction': 'long',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percent': self.risk_percent,
                'risk_reward': self.risk_reward,
                'reason': 'H1_Bullish_M15_OB_Retracement'
            }
            
        elif ob_zone['type'] == 'bearish':
            # Short setup
            entry = current_price
            stop_loss = ob_zone['high']
            risk = stop_loss - entry
            
            if risk <= 0:
                return None
                
            take_profit = entry - (risk * self.risk_reward)
            
            return {
                'direction': 'short',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percent': self.risk_percent,
                'risk_reward': self.risk_reward,
                'reason': 'H1_Bearish_M15_OB_Retracement'
            }
            
        return None
    
    def get_debug_stats(self) -> Dict:
        """Return debug statistics"""
        return self.debug_stats.copy()

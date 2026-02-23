"""
Trade Filters - HTF Trend Gate, Setup Score, Cooldown Management
Фильтрация перед входом в сделку для повышения качества
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class TradeFilters:
    """
    Система фильтров для контроля качества входов.
    
    Порядок проверок:
    1. HTF Trend Gate (M5/M15) - направление тренда
    2. RR Gate - риск/профит соотношение
    3. Spread Gate - спред в норме
    4. Cooldown Gate - прошло достаточно времени
    5. Daily Limit Gate - дневной лимит не превышен
    6. Setup Score - итоговая оценка качества
    """
    
    def __init__(self, mt5_connector=None, config_manager=None):
        """
        Initialize trade filters.
        
        Args:
            mt5_connector: MT5 connector instance
            config_manager: ConfigManager instance (if None, will create)
        """
        self.mt5 = mt5_connector
        self.last_trade_time = {}  # symbol -> timestamp
        self.daily_trades = {}  # date -> count
        self.last_result = {}  # symbol -> 'win' or 'loss'
        self.consecutive_losses = {}  # symbol -> count
        
        # Get ConfigManager
        if config_manager is None:
            from src.core.config_manager import get_config_manager
            config_manager = get_config_manager()
        
        self.config_manager = config_manager
        
        # Load initial config
        self.config = {}
        self._load_config()
        
        # Register reload callback for hot updates
        self.config_manager.register_reload_callback(self._on_config_reload)
        
        logger.info("[TradeFilters] ✅ Initialized with ConfigManager (hot reload enabled)")
    
    def _load_config(self):
        """Load filter configuration from trading.yaml (single source of truth)"""
        # ✅ Read from trading.yaml ONLY - no more conflicts!
        trading_config = self.config_manager.load_config('trading.yaml')
        filter_config = trading_config.get('trading', {}).get('filters', {})
        
        # Store old config for change detection
        old_config = self.config.copy() if self.config else {}
        
        # TIMEFRAME MAPPING
        tf_map = {
            'M5': mt5.TIMEFRAME_M5 if mt5 else None,
            'M15': mt5.TIMEFRAME_M15 if mt5 else None,
            'M30': mt5.TIMEFRAME_M30 if mt5 else None,
            'H1': mt5.TIMEFRAME_H1 if mt5 else None,
            'H4': mt5.TIMEFRAME_H4 if mt5 else None,
        }
        
        htf_str = filter_config.get('htf_timeframe', 'M15')
        
        # Update config with defaults
        self.config = {
            'htf_timeframe': tf_map.get(htf_str, mt5.TIMEFRAME_M15 if mt5 else None),
            'htf_ema_fast': filter_config.get('htf_ema_fast', 50),
            'htf_ema_slow': filter_config.get('htf_ema_slow', 200),
            'min_rr': filter_config.get('min_rr', 1.2),
            'max_spread_pips': filter_config.get('max_spread_pips', 3.0),
            'cooldown_after_win': filter_config.get('cooldown_after_win', 15),
            'cooldown_after_loss': filter_config.get('cooldown_after_loss', 90),
            'cooldown_after_2_losses': filter_config.get('cooldown_after_2_losses', 240),
            'daily_limit': filter_config.get('daily_limit', 6),
            'min_setup_score': filter_config.get('min_setup_score', 70),
            'min_confidence': filter_config.get('min_confidence', 75)
        }
        
        # Detect changes if this is a reload
        if old_config:
            changes = []
            for key in self.config.keys():
                old_val = old_config.get(key)
                new_val = self.config.get(key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} → {new_val}")
            
            if changes:
                logger.warning(f"[TradeFilters] 🔄 Filter changes detected:")
                for change in changes:
                    logger.warning(f"  ↳ {change}")
        
        # Log loaded config
        logger.info(f"[TradeFilters] 📋 Loaded config from trading.yaml (single source of truth):")
        logger.info(f"  ├─ min_confidence: {self.config['min_confidence']}%")
        logger.info(f"  ├─ daily_limit: {self.config['daily_limit']}")
        logger.info(f"  ├─ max_spread_pips: {self.config['max_spread_pips']}")
        logger.info(f"  ├─ min_rr: {self.config['min_rr']}")
        logger.info(f"  ├─ htf_timeframe: {htf_str}")
        logger.info(f"  ├─ htf_ema_fast: {self.config['htf_ema_fast']}")
        logger.info(f"  ├─ htf_ema_slow: {self.config['htf_ema_slow']}")
        logger.info(f"  ├─ cooldown_after_win: {self.config['cooldown_after_win']} min")
        logger.info(f"  ├─ cooldown_after_loss: {self.config['cooldown_after_loss']} min")
        logger.info(f"  ├─ cooldown_after_2_losses: {self.config['cooldown_after_2_losses']} min")
        logger.info(f"  └─ min_setup_score: {self.config['min_setup_score']}")
        logger.info(f"[TradeFilters] 🔄 Source: trading.yaml via ConfigManager (hot reload enabled, no conflicts)")
    
    def _on_config_reload(self):
        """
        Callback when any config is reloaded (no arguments).
        Simply reloads the configuration.
        """
        logger.info(f"[TradeFilters] 🔄 Config reload triggered")
        self._load_config()
        logger.info(f"[TradeFilters] ✅ Config reloaded successfully (no restart needed)")
    
    def check_all_gates(self, signal: Dict, market_data: Optional[Dict] = None) -> Tuple[bool, str, int]:
        """
        Проверить все фильтры.
        
        Args:
            signal: Сигнал с action, confidence, entry, sl, tp, symbol
            market_data: Дополнительные рыночные данные
        
        Returns:
            (pass: bool, reason: str, score: int)
        """
        symbol = signal.get('symbol', 'XAUUSD')
        action = signal.get('action', 'HOLD').upper()
        confidence = signal.get('confidence', 0)
        
        # Если HOLD - пропускаем
        if action == 'HOLD':
            return False, "GPT said HOLD", 0
        
        # Проверяем confidence
        if confidence < self.config['min_confidence']:
            return False, f"Low confidence {confidence}% < {self.config['min_confidence']}%", 0
        
        score_components = {}
        
        # 1. HTF Trend Gate
        htf_ok, htf_reason, htf_score = self._check_htf_trend(symbol, action, market_data)
        score_components['htf'] = htf_score
        if not htf_ok:
            return False, f"HTF Gate: {htf_reason}", 0
        
        # 2. RR Gate
        rr_ok, rr_reason, rr_score = self._check_rr(signal)
        score_components['rr'] = rr_score
        if not rr_ok:
            return False, f"RR Gate: {rr_reason}", 0
        
        # 3. Spread Gate
        spread_ok, spread_reason, spread_score = self._check_spread(symbol)
        score_components['spread'] = spread_score
        if not spread_ok:
            return False, f"Spread Gate: {spread_reason}", 0
        
        # 4. Cooldown Gate
        cooldown_ok, cooldown_reason = self._check_cooldown(symbol)
        if not cooldown_ok:
            return False, f"Cooldown Gate: {cooldown_reason}", 0
        
        # 5. Daily Limit Gate
        limit_ok, limit_reason = self._check_daily_limit()
        if not limit_ok:
            return False, f"Daily Limit Gate: {limit_reason}", 0
        
        # 6. Calculate Setup Score
        setup_score = self._calculate_setup_score(
            htf_score=score_components['htf'],
            rr_score=score_components['rr'],
            spread_score=score_components['spread'],
            confidence=confidence
        )
        
        if setup_score < self.config['min_setup_score']:
            return False, f"Low setup score {setup_score} < {self.config['min_setup_score']}", setup_score
        
        # ✅ ALL GATES PASSED
        return True, f"All gates PASS (score: {setup_score})", setup_score
    
    def _check_htf_trend(self, symbol: str, action: str, market_data: Optional[Dict]) -> Tuple[bool, str, int]:
        """
        HTF Trend Gate: проверка тренда на M15.
        
        Returns:
            (pass, reason, score 0-30)
        """
        try:
            if not self.mt5:
                logger.warning("[HTF Gate] MT5 not available, skipping")
                return True, "MT5 N/A", 15  # Neutral score
            
            # Get M15 data
            bars = mt5.copy_rates_from_pos(symbol, self.config['htf_timeframe'], 0, 250)
            if bars is None or len(bars) < 200:
                logger.warning(f"[HTF Gate] Not enough data for {symbol}")
                return True, "Insufficient data", 15
            
            df = pd.DataFrame(bars)
            df['close'] = df['close'].astype(float)
            
            # Calculate EMAs
            ema_fast = df['close'].ewm(span=self.config['htf_ema_fast'], adjust=False).mean()
            ema_slow = df['close'].ewm(span=self.config['htf_ema_slow'], adjust=False).mean()
            
            last_fast = ema_fast.iloc[-1]
            last_slow = ema_slow.iloc[-1]
            
            # EMA slope (last 10 bars)
            slope_slow = (ema_slow.iloc[-1] - ema_slow.iloc[-10]) / 10
            
            # Determine trend
            if last_fast > last_slow and slope_slow > 0:
                trend = "UP"
                score = 30
            elif last_fast < last_slow and slope_slow < 0:
                trend = "DOWN"
                score = 30
            else:
                trend = "FLAT"
                score = 10
            
            # Check alignment
            if trend == "UP" and action == "BUY":
                return True, f"Trend {trend} aligned with {action}", score
            elif trend == "DOWN" and action == "SELL":
                return True, f"Trend {trend} aligned with {action}", score
            elif trend == "FLAT":
                # В флете торговать можем, но со снижением score
                logger.info(f"[HTF Gate] FLAT market - reduced score")
                return True, f"Trend FLAT - allowed but low score", score
            else:
                # Counter-trend - block
                return False, f"Counter-trend: {trend} vs {action}", 0
        
        except Exception as e:
            logger.error(f"[HTF Gate] Error: {e}")
            return True, f"Error: {e}", 15
    
    def _check_rr(self, signal: Dict) -> Tuple[bool, str, int]:
        """
        RR Gate: проверка риск/профит.
        
        Returns:
            (pass, reason, score 0-20)
        """
        entry = signal.get('entry', 0)
        sl = signal.get('sl', 0)
        tp = signal.get('tp', 0)
        
        if entry == 0 or sl == 0 or tp == 0:
            return True, "SL/TP N/A", 10
        
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0:
            return False, "Risk is 0", 0
        
        rr = reward / risk
        
        if rr < self.config['min_rr']:
            return False, f"RR {rr:.2f} < {self.config['min_rr']}", 0
        
        # Score based on RR
        if rr >= 2.0:
            score = 20
        elif rr >= 1.5:
            score = 15
        else:
            score = 10
        
        return True, f"RR {rr:.2f} OK", score
    
    def _check_spread(self, symbol: str) -> Tuple[bool, str, int]:
        """
        Spread Gate: проверка спреда.
        
        Returns:
            (pass, reason, score 0-15)
        """
        try:
            if not self.mt5:
                return True, "MT5 N/A", 10
            
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return True, "Symbol info N/A", 10
            
            spread = symbol_info.spread
            point = symbol_info.point
            
            # XAUUSD: spread в центах (0.01 = 1 pip)
            # EURUSD: spread в 0.00001 (10 pips = 0.0001)
            is_forex = "USD" in symbol and symbol != "XAUUSD"
            
            if is_forex:
                spread_pips = spread / 10  # For EURUSD
            else:
                spread_pips = spread * point * 100  # For XAUUSD
            
            max_spread = self.config['max_spread_pips']
            
            if spread_pips > max_spread:
                return False, f"Spread {spread_pips:.1f} pips > {max_spread}", 0
            
            # Score based on spread
            if spread_pips < max_spread * 0.5:
                score = 15
            elif spread_pips < max_spread * 0.75:
                score = 12
            else:
                score = 8
            
            return True, f"Spread {spread_pips:.1f} pips OK", score
        
        except Exception as e:
            logger.error(f"[Spread Gate] Error: {e}")
            return True, "Error checking spread", 10
    
    def _check_cooldown(self, symbol: str) -> Tuple[bool, str]:
        """
        Cooldown Gate: динамический кулдаун после сделок.
        """
        now = datetime.now()
        last_time = self.last_trade_time.get(symbol)
        
        if not last_time:
            return True, "First trade"
        
        time_passed = (now - last_time).total_seconds() / 60  # minutes
        
        # Определяем требуемый кулдаун
        consecutive = self.consecutive_losses.get(symbol, 0)
        last_res = self.last_result.get(symbol, 'neutral')
        
        if consecutive >= 2:
            required = self.config['cooldown_after_2_losses']
        elif last_res == 'loss':
            required = self.config['cooldown_after_loss']
        else:
            required = self.config['cooldown_after_win']
        
        if time_passed < required:
            remaining = int(required - time_passed)
            return False, f"Cooldown: {remaining} min remaining (need {required} min)"
        
        return True, f"Cooldown OK ({int(time_passed)} min passed)"
    
    def _check_daily_limit(self) -> Tuple[bool, str]:
        """
        Daily Limit Gate: дневной лимит сделок.
        """
        today = datetime.now().date()
        count = self.daily_trades.get(today, 0)
        
        if count >= self.config['daily_limit']:
            return False, f"Daily limit {count}/{self.config['daily_limit']} reached"
        
        return True, f"Daily limit OK ({count}/{self.config['daily_limit']})"
    
    def _calculate_setup_score(self, htf_score: int, rr_score: int, spread_score: int, confidence: int) -> int:
        """
        Расчет итогового setup score (0-100).
        
        Компоненты:
        - HTF: 30 points
        - RR: 20 points
        - Spread: 15 points
        - Confidence: 10 points (75% = 7.5, 100% = 10)
        - Base: 25 points
        """
        conf_points = min(10, confidence / 10)
        total = htf_score + rr_score + spread_score + conf_points + 25
        return int(min(100, total))
    
    def record_trade_result(self, symbol: str, pnl: float):
        """
        Записать результат сделки для cooldown logic.
        """
        now = datetime.now()
        self.last_trade_time[symbol] = now
        
        # Update daily counter
        today = now.date()
        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
        
        # Update result
        if pnl > 0:
            self.last_result[symbol] = 'win'
            self.consecutive_losses[symbol] = 0
            logger.info(f"[Filters] {symbol} WIN recorded, cooldown: {self.config['cooldown_after_win']} min")
        else:
            self.last_result[symbol] = 'loss'
            self.consecutive_losses[symbol] = self.consecutive_losses.get(symbol, 0) + 1
            losses = self.consecutive_losses[symbol]
            cooldown = self.config['cooldown_after_2_losses'] if losses >= 2 else self.config['cooldown_after_loss']
            logger.warning(f"[Filters] {symbol} LOSS recorded ({losses} consecutive), cooldown: {cooldown} min")
    
    def reset_daily_stats(self):
        """Сброс дневной статистики (вызывать в начале дня)."""
        self.daily_trades = {}
        logger.info("[Filters] Daily stats reset")

#!/usr/bin/env python3
"""
AI Signal Manager v2.0 - Enhanced signal and block management

Handles AI-generated signals with TTL, multi-level blocks, and risk multipliers.
Integrates with LiveTrader for flexible trading control.

Key Features:
- TTL-based signal expiration with confidence decay
- Multi-level block types (HARD/SOFT/WARNING/BIAS)
- Risk multiplier system (0.0-1.0)
- Signal priority and history tracking
- Graceful degradation on AI failures
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading

from src.core.logger import logger


class BlockType(Enum):
    """Types of AI trading blocks."""
    NONE = "none"              # No restrictions (multiplier: 1.0)
    BIAS = "bias"              # Soft suggestion (multiplier: 0.8-0.9)
    WARNING = "warning"        # Reduce risk (multiplier: 0.5)
    SOFT_BLOCK = "soft_block"  # Allow only high confidence >70% (multiplier: 0.3)
    HARD_BLOCK = "hard_block"  # Complete block (multiplier: 0.0)


@dataclass
class AISignal:
    """AI trading signal with TTL and decay."""
    id: str
    symbol: str
    type: str  # BUY or SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    trigger_time: str
    reasoning: str
    confidence: float
    risk_reward: float
    created_at: str
    expires_at: str  # TTL
    analysis_version: str = "1.0"
    status: str = "pending"
    triggered_at: Optional[str] = None
    priority: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def is_expired(self) -> bool:
        """Check if signal expired."""
        try:
            return datetime.now() > datetime.fromisoformat(self.expires_at)
        except:
            return False
    
    def get_confidence_with_decay(self) -> float:
        """Get confidence with time decay."""
        try:
            created = datetime.fromisoformat(self.created_at)
            expires = datetime.fromisoformat(self.expires_at)
            now = datetime.now()
            
            total_lifetime = (expires - created).total_seconds()
            elapsed = (now - created).total_seconds()
            
            if elapsed >= total_lifetime:
                return self.confidence * 0.5
            
            decay_factor = 1.0 - (elapsed / total_lifetime) * 0.5
            return self.confidence * decay_factor
        except:
            return self.confidence


class AISignalManager:
    """
    AI Signal Manager v2.0 with enhanced features.
    
    Manages signals, blocks, and risk multipliers based on AI analysis.
    """
    
    def __init__(self):
        """Initialize Signal Manager v2.0."""
        self.signals_dir = Path("data/ai_signals")
        self.signals_dir.mkdir(parents=True, exist_ok=True)
        
        # Load AI config
        self.config = self._load_config()
        
        self.active_signals: List[AISignal] = []
        self.signal_history: List[Dict] = []
        
        # Block state
        self.block_type = BlockType.NONE
        self.block_reason = None
        self.block_until = None
        self.risk_multiplier = 1.0
        
        # Analysis metadata
        self.latest_analysis_time = None
        self.latest_analysis_version = None
        
        # Track if state already loaded globally
        self._state_loaded = False
        
        self._lock = threading.Lock()
        self._load_state(verbose=True)  # Log on init
        
        logger.info("[AI-Signal] Manager v2.0 initialized")
    
    def _load_config(self) -> Dict:
        """Load AI configuration from ai.yaml."""
        try:
            import yaml
            config_path = Path("config/ai.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"[AI-Signal] Failed to load config: {e}")
        return {}
    
    def _is_trading_time_allowed(self, test_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if current time allows trading.
        
        Args:
            test_time: Optional datetime for testing (default: now)
        
        Returns:
            (allowed, reason)
        """
        now = test_time or datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Night block: 22:00 - 02:00
        if current_hour >= 22 or current_hour < 2:
            return False, "Night time block (22:00-02:00)"
        
        # Weekend block: Friday 22:00 - Monday 02:00
        # Friday after 22:00
        if current_weekday == 4 and current_hour >= 22:
            return False, "Weekend block starting (Friday 22:00)"
        
        # Saturday (all day)
        if current_weekday == 5:
            return False, "Weekend block (Saturday)"
        
        # Sunday (all day)
        if current_weekday == 6:
            return False, "Weekend block (Sunday)"
        
        # Monday before 02:00
        if current_weekday == 0 and current_hour < 2:
            return False, "Weekend block ending (Monday 02:00)"
        
        return True, "OK"
    
    def check_volatility_filter(self, symbol: str) -> Tuple[bool, str]:
        """Pre-filter: Check if market volatility is sufficient for trading.
        
        Returns:
            (pass_filter, reason)
        """
        try:
            import MetaTrader5 as mt5
            
            # Get recent data
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
            if rates is None or len(rates) < 20:
                return True, "Not enough data for volatility check"
            
            import pandas as pd
            df = pd.DataFrame(rates)
            
            # Calculate ATR (Average True Range)
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Check if ATR is too low (market too quiet)
            # For XAUUSD: minimum $2-3 ATR
            min_atr = 2.0 if symbol == "XAUUSD" else 0.0002  # 2 pips for EURUSD
            
            if atr < min_atr:
                return False, f"Low volatility: ATR ${atr:.2f} < ${min_atr:.2f} (market too quiet)"
            
            return True, f"Volatility OK: ATR ${atr:.2f}"
            
        except Exception as e:
            logger.warning(f"[AI-Signal] Volatility check failed: {e}")
            return True, "Volatility check unavailable"
    
    def process_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process AI analysis with GPT Decision Engine format (v2.0).
        
        Expected format:
        {
            "decision": {
                "action": "BUY|SELL|NONE",
                "confidence": 0-100,
                "block": "NONE|SOFT|HARD"
            },
            "trade": {  # Only present if action = BUY/SELL
                "entry": float,
                "stop_loss": float,
                "take_profit": float,
                "risk_reward": float
            }
        }
        
        Logic:
        - BUY/SELL: Create signal if no position exists, max 1 pending per symbol
        - NONE: Schedule retry in 15 minutes
        - TTL: Signals expire after configured time (default 60 min)
        - Block levels: NONE (1.0x), SOFT (0.5x), HARD (0.0x blocked)
        
        Args:
            analysis: Analysis dict from MarketAnalystService
        
        Returns:
            Summary dict with signals_created, action, block info
        """
        try:
            with self._lock:
                # Update metadata
                self.latest_analysis_time = datetime.now().isoformat()
                self.latest_analysis_version = analysis.get("analysis_version", "2.0")
                
                # Get symbol from analysis
                symbol = analysis.get("symbol", "XAUUSD")
                
                # Initialize summary
                summary = {
                    "signals_created": 0,
                    "decision_action": "NONE",
                    "block_type": "none",
                    "risk_multiplier": 1.0,
                    "symbol": symbol
                }
                
                # Extract decision data
                decision = analysis.get("decision", {})
                action = decision.get("action", "NONE").upper()
                confidence = decision.get("confidence", 0)
                block_level = decision.get("block", "NONE").upper()
                
                summary["decision_action"] = action
                summary["block_type"] = block_level.lower()
                
                logger.info(
                    f"[AI-Signal] 📊 Decision received: {action} "
                    f"(confidence: {confidence}%, block: {block_level}, symbol: {symbol})"
                )
                
                # 1. Process block level first (affects risk multiplier)
                self._process_block_level(block_level, summary)
                
                # 2. Handle BUY/SELL actions
                if action in ["BUY", "SELL"]:
                    # Check if trade data exists
                    if "trade" not in analysis:
                        logger.error(f"[AI-Signal] ❌ {action} decision but no trade data provided")
                        return summary
                    
                    trade_data = analysis["trade"]
                    
                    # Check #1: Position already exists?
                    if hasattr(self, 'executor') and self.executor:
                        if self.executor.has_position():
                            logger.warning(
                                f"[AI-Signal] ⛔ Position already open for {symbol} - "
                                f"skipping {action} signal creation"
                            )
                            summary["block_reason"] = "position_already_open"
                            return summary
                    else:
                        logger.debug("[AI-Signal] No executor reference - skipping position check")
                    
                    # Check #2: Already has pending signal for this symbol?
                    pending_count = sum(
                        1 for s in self.active_signals 
                        if s.symbol == symbol and s.status == "pending"
                    )
                    
                    if pending_count >= 1:
                        logger.warning(
                            f"[AI-Signal] ⛔ Already {pending_count} pending signal(s) for {symbol} - "
                            f"max 1 allowed, skipping new signal"
                        )
                        summary["block_reason"] = "max_pending_signals_reached"
                        return summary
                    
                    # Build signal data from decision + trade
                    signal_data = {
                        "type": action,
                        "entry_price": trade_data.get("entry"),
                        "stop_loss": trade_data.get("stop_loss"),
                        "take_profit": trade_data.get("take_profit"),
                        "confidence": confidence,
                        "risk_reward": trade_data.get("risk_reward", 1.5),
                        "reasoning": f"GPT Decision Engine: {action} @ {confidence}% confidence",
                        "trigger_time": "immediate"  # v2.0 always immediate
                    }
                    
                    # Validate signal structure and quality
                    if not self._validate_signal(signal_data):
                        logger.warning(f"[AI-Signal] ❌ Signal validation failed for {action} decision")
                        summary["block_reason"] = "validation_failed"
                        return summary
                    
                    # Create signal with TTL
                    signal = self._create_signal(
                        symbol=symbol,
                        signal_data=signal_data,
                        version=analysis.get("analysis_version", "2.0")
                    )
                    
                    # Add to active signals
                    self.active_signals.append(signal)
                    summary["signals_created"] = 1
                    
                    # Log to history
                    self.signal_history.append({
                        "action": "created",
                        "signal_id": signal.id,
                        "timestamp": datetime.now().isoformat(),
                        "confidence": confidence,
                        "symbol": symbol
                    })
                    
                    # Get TTL config
                    ttl_config = self.config.get('trading', {}).get('signal_ttl', {})
                    ttl_minutes = ttl_config.get('ttl_minutes', 60)
                    
                    logger.info(
                        f"[AI-Signal] ✅ Signal created: {signal.type} {symbol} @ {signal.entry_price:.5f} "
                        f"| SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} "
                        f"| Confidence: {signal.confidence}% | TTL: {ttl_minutes}min "
                        f"| Expires: {signal.expires_at[11:16]}"
                    )
                
                # 3. Handle NONE action
                elif action == "NONE":
                    logger.info(
                        f"[AI-Signal] 🔵 NONE decision for {symbol} - "
                        f"confidence: {confidence}% - scheduling retry in 15 min"
                    )
                    
                    # Schedule retry after 15 minutes
                    self._schedule_none_retry(symbol)
                    summary["retry_scheduled"] = True
                
                else:
                    logger.warning(f"[AI-Signal] ⚠️ Unknown action: {action}")
                
                # 4. Cleanup expired signals (will trigger auto-requery if TTL expired)
                self._cleanup_expired_signals()
                
                # 5. Save state
                self._save_state()
                
                return summary
                
        except Exception as e:
            logger.error(f"[AI-Signal] ❌ Failed to process analysis: {e}", exc_info=True)
            return {"error": str(e), "signals_created": 0}
    
    def _process_block_level(self, block_level: str, summary: Dict):
        """Process block level from decision (v2.0)."""
        block_level = block_level.upper()
        
        if block_level == "NONE":
            summary["risk_multiplier"] = 1.0
            self.current_block = BlockType.NONE
            logger.info("[AI-Signal] Block: NONE - Full trading allowed")
            
        elif block_level == "SOFT":
            summary["risk_multiplier"] = 0.5
            self.current_block = BlockType.WARNING
            logger.warning("[AI-Signal] Block: SOFT - Reduce risk to 50%")
            
        elif block_level == "HARD":
            summary["risk_multiplier"] = 0.0
            self.current_block = BlockType.HARD_BLOCK
            logger.error("[AI-Signal] Block: HARD - Trading blocked completely")
            
        else:
            summary["risk_multiplier"] = 1.0
            self.current_block = BlockType.NONE
            logger.warning(f"[AI-Signal] Unknown block level: {block_level}, defaulting to NONE")
    
    def _process_blocks(self, blocks: Dict, summary: Dict):
        """DEPRECATED: Old block processing (keep for compatibility)."""
        block_type_str = blocks.get("block_type", "none").lower()
        block_reason = blocks.get("reason", "No reason provided")
        
        logger.info(f"[AI-Signal] Processing blocks - Type: {block_type_str}, Reason: {block_reason}")
        
        # Map block type
        if block_type_str == "hard_block":
            self.block_type = BlockType.HARD_BLOCK
            self.risk_multiplier = 0.0
            logger.warning(f"[AI-Signal] 🚫 HARD BLOCK activated: {block_reason}")
        elif block_type_str == "soft_block":
            self.block_type = BlockType.SOFT_BLOCK
            self.risk_multiplier = 0.3
            logger.warning(f"[AI-Signal] ⛔ SOFT BLOCK activated (risk 0.3x): {block_reason}")
        elif block_type_str == "warning":
            self.block_type = BlockType.WARNING
            self.risk_multiplier = 0.5
            logger.warning(f"[AI-Signal] ⚠️  WARNING block activated (risk 0.5x): {block_reason}")
        elif block_type_str == "bias":
            self.block_type = BlockType.BIAS
            self.risk_multiplier = 0.8
            logger.info(f"[AI-Signal] ↗️ BIAS applied (risk 0.8x): {block_reason}")
        else:
            self.block_type = BlockType.NONE
            self.risk_multiplier = 1.0
            logger.info(f"[AI-Signal] ✅ NO RESTRICTIONS (risk 1.0x): {block_reason}")
        
        self.block_reason = block_reason
        self.block_until = blocks.get("block_until")
        
        # Update summary
        summary["block_type"] = self.block_type.value
        summary["risk_multiplier"] = self.risk_multiplier
        summary["block_reason"] = self.block_reason
        
        summary["block_type"] = self.block_type.value
        summary["risk_multiplier"] = self.risk_multiplier
        
        if self.block_type != BlockType.NONE:
            logger.warning(
                f"[AI-Signal] Block activated: {self.block_type.value.upper()} "
                f"(multiplier: {self.risk_multiplier}) - {self.block_reason}"
            )
        else:
            logger.info("[AI-Signal] No trading restrictions")
    
    def _validate_signal(self, signal_data: Dict) -> bool:
        """Validate signal has required fields and meets quality criteria."""
        required = ["type", "entry_price", "stop_loss", "take_profit", "confidence"]
        for field in required:
            if field not in signal_data or signal_data[field] is None:
                logger.warning(f"[AI-Signal] Invalid signal - missing {field}")
                return False
        
        # Confidence check
        if signal_data["confidence"] < 50:
            logger.info(f"[AI-Signal] Skipped low confidence: {signal_data['confidence']}%")
            return False
        
        # Risk/Reward ratio check (minimum 2:1)
        entry = signal_data["entry_price"]
        sl = signal_data["stop_loss"]
        tp = signal_data["take_profit"]
        
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0:
            logger.warning(f"[AI-Signal] Invalid signal - zero risk (entry == SL)")
            return False
        
        rr_ratio = reward / risk
        
        # Читаем min_rr из конфига
        min_rr_threshold = self.config.get('market_analyst', {}).get('signals', {}).get('min_rr', 2.0)
        
        if rr_ratio < min_rr_threshold:
            logger.info(f"[AI-Signal] Rejected poor RR ratio: {rr_ratio:.2f} < {min_rr_threshold} (risk: ${risk:.2f}, reward: ${reward:.2f})")
            return False
        
        logger.info(f"[AI-Signal] Signal validated: RR={rr_ratio:.2f}, confidence={signal_data['confidence']}%")
        return True
    
    def is_duplicate_signal(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        tolerance: float = 0.001  # 0.1% tolerance
    ) -> bool:
        """
        Проверка на дубликат сигнала.
        
        Args:
            symbol: Торговый символ
            signal_type: BUY или SELL
            entry_price: Цена входа
            tolerance: Допуск для сравнения цен (0.001 = 0.1%)
        
        Returns:
            True если сигнал дубликат, False если новый
        """
        with self._lock:
            for existing_signal in self.active_signals:
                # Проверяем только активные сигналы
                if existing_signal.status not in ["pending", "triggered"]:
                    continue
                
                # Проверяем symbol и type
                if existing_signal.symbol != symbol:
                    continue
                if existing_signal.type.upper() != signal_type.upper():
                    continue
                
                # Проверяем entry price с допуском ±0.1%
                price_diff = abs(existing_signal.entry_price - entry_price)
                price_tolerance = existing_signal.entry_price * tolerance
                
                if price_diff <= price_tolerance:
                    logger.info(
                        f"[AI-Signal] Duplicate signal detected: "
                        f"{symbol} {signal_type} @ {entry_price} "
                        f"(existing: {existing_signal.entry_price})"
                    )
                    return True
        
        return False
    
    def create_signal_from_analysis(
        self,
        symbol: str,
        analysis: Dict,
        signal_data: Dict
    ) -> Optional[AISignal]:
        """
        Создание сигнала из анализа с проверкой на дубликаты.
        
        Args:
            symbol: Торговый символ
            analysis: Полный анализ от MarketAnalyst
            signal_data: Данные конкретного сигнала
        
        Returns:
            AISignal или None если дубликат
        """
        try:
            # Проверяем валидность
            if not self._validate_signal(signal_data):
                return None
            
            # Проверяем дубликаты
            if self.is_duplicate_signal(
                symbol=symbol,
                signal_type=signal_data["type"],
                entry_price=signal_data["entry_price"]
            ):
                # Проверяем, может обновить существующий если уверенность выше
                self._try_update_signal(symbol, signal_data)
                return None
            
            # Создаем новый сигнал
            version = analysis.get("analysis_version", "2.0")
            signal = self._create_signal(symbol, signal_data, version)
            
            with self._lock:
                self.active_signals.append(signal)
                
                # Log to history
                self.signal_history.append({
                    "action": "created",
                    "signal_id": signal.id,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(
                    f"[AI-Signal] Created: {signal.type} @ {signal.entry_price} "
                    f"(conf: {signal.confidence}%, RR: {signal.risk_reward:.2f})"
                )
                
                # Save state
                self._save_state()
            
            return signal
            
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to create signal: {e}")
            return None
    
    def _try_update_signal(self, symbol: str, new_signal_data: Dict):
        """Попытка обновить существующий сигнал если новый лучше."""
        with self._lock:
            for existing in self.active_signals:
                if existing.symbol != symbol:
                    continue
                if existing.type.upper() != new_signal_data["type"].upper():
                    continue
                
                # Проверяем entry price
                price_diff = abs(existing.entry_price - new_signal_data["entry_price"])
                if price_diff <= existing.entry_price * 0.001:
                    # Обновляем если уверенность выше
                    new_confidence = new_signal_data["confidence"]
                    if new_confidence > existing.confidence:
                        existing.confidence = new_confidence
                        existing.stop_loss = new_signal_data["stop_loss"]
                        existing.take_profit = new_signal_data["take_profit"]
                        existing.reasoning = new_signal_data.get("reasoning", existing.reasoning)
                        
                        logger.info(
                            f"[AI-Signal] Updated signal {existing.id}: "
                            f"confidence {existing.confidence}% → {new_confidence}%"
                        )
                        
                        self._save_state()
                    break
    
    def _create_signal(self, symbol: str, signal_data: Dict, version: str) -> AISignal:
        """Create AISignal with TTL."""
        signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate expiration (24 hours default)
        created = datetime.now()
        expires = created + timedelta(hours=24)
        
        # Priority based on confidence
        priority = int(signal_data["confidence"] / 10)
        
        return AISignal(
            id=signal_id,
            symbol=symbol,
            type=signal_data["type"],
            entry_price=float(signal_data["entry_price"]),
            stop_loss=float(signal_data["stop_loss"]),
            take_profit=float(signal_data["take_profit"]),
            trigger_time=signal_data.get("trigger_time", "immediate"),
            reasoning=signal_data.get("reasoning", ""),
            confidence=float(signal_data["confidence"]),
            risk_reward=float(signal_data.get("risk_reward", 2.0)),
            created_at=created.isoformat(),
            expires_at=expires.isoformat(),
            analysis_version=version,
            status="pending",
            priority=priority
        )
    
    def check_triggers(
        self, 
        current_price: float, 
        symbol: str, 
        current_time: datetime
    ) -> List[AISignal]:
        """Check if any signals should trigger with TTL and price validation."""
        triggered_signals = []
        expired_signals = []  # Сигналы для удаления
        
        # Note: State is loaded at init and when signals are added.
        # No need to reload every check - reduces log spam.
        
        with self._lock:
            for signal in self.active_signals:
                if signal.status != "pending" or signal.symbol != symbol:
                    continue
                
                # Check standard expiration (24h)
                if signal.is_expired():
                    signal.status = "expired"
                    expired_signals.append(signal)
                    logger.info(f"[AI-Signal] Signal {signal.id} expired (24h TTL)")
                    continue
                
                # TTL check: configurable validity time from config
                validity_minutes = self.config.get('market_analyst', {}).get('signals', {}).get('validity_minutes', 60)
                created_time = datetime.fromisoformat(signal.created_at)
                age_minutes = (current_time - created_time).total_seconds() / 60
                if age_minutes > validity_minutes:
                    signal.status = "time_expired"
                    expired_signals.append(signal)
                    logger.info(f"[AI-Signal] Signal {signal.id} expired ({validity_minutes}min TTL, age: {age_minutes:.1f}min)")
                    continue
                
                # Price invalidation: if price moved too far from entry
                pip_multiplier = 10 if symbol == "EURUSD" else 1
                price_diff = abs(current_price - signal.entry_price) * pip_multiplier
                if price_diff > 30:  # 30 pips
                    signal.status = "price_invalidated"
                    expired_signals.append(signal)
                    logger.info(f"[AI-Signal] Signal {signal.id} invalidated (price moved {price_diff:.1f} pips from entry)")
                    continue
                
                # Entry distance check: if price already too far from entry (missed opportunity)
                # For BUY: if current > entry + 20 pips (price already ran up)
                # For SELL: if current < entry - 20 pips (price already ran down)
                if signal.type == "BUY" and (current_price - signal.entry_price) * pip_multiplier > 20:
                    signal.status = "price_invalidated"
                    expired_signals.append(signal)
                    logger.info(f"[AI-Signal] BUY signal {signal.id} invalidated (price already ran up {price_diff:.1f} pips above entry)")
                    continue
                elif signal.type == "SELL" and (signal.entry_price - current_price) * pip_multiplier > 20:
                    signal.status = "price_invalidated"
                    expired_signals.append(signal)
                    logger.info(f"[AI-Signal] SELL signal {signal.id} invalidated (price already ran down {price_diff:.1f} pips below entry)")
                    continue
                
                # Check time trigger
                if signal.trigger_time != "immediate":
                    if not self._is_time_reached(signal.trigger_time, current_time):
                        continue
                
                # Check price trigger
                if self._is_price_triggered(signal, current_price):
                    signal.status = "triggered"
                    signal.triggered_at = current_time.isoformat()
                    triggered_signals.append(signal)
                    
                    # Log to history
                    self.signal_history.append({
                        "action": "triggered",
                        "signal_id": signal.id,
                        "timestamp": current_time.isoformat(),
                        "price": current_price
                    })
                    
                    logger.info(f"[AI-Signal] Triggered: {signal.id} at price {current_price}")
            
            # НЕ удаляем triggered сигналы сразу - они нужны для исполнения!
            # Удалим их ПОСЛЕ успешного открытия позиции (в mark_signal_filled)
            
            # Удаляем только expired/invalidated сигналы
            for signal in expired_signals:
                try:
                    self.active_signals.remove(signal)
                    # Добавляем в историю
                    self.signal_history.append({
                        "action": signal.status,
                        "signal_id": signal.id,
                        "timestamp": current_time.isoformat(),
                        "reason": f"Status: {signal.status}"
                    })
                except ValueError:
                    pass  # Сигнал уже удалён
            
            if triggered_signals or expired_signals:
                self._save_state()
        
        return triggered_signals
    
    def _is_time_reached(self, trigger_time: str, current_time: datetime) -> bool:
        """Check if trigger time reached."""
        try:
            hour, minute = map(int, trigger_time.split(':'))
            trigger_dt = current_time.replace(hour=hour, minute=minute, second=0)
            
            window_start = trigger_dt - timedelta(minutes=5)
            window_end = trigger_dt + timedelta(minutes=10)
            
            return window_start <= current_time <= window_end
        except:
            return True
    
    def _is_price_triggered(self, signal: AISignal, current_price: float) -> bool:
        """Check if price reached entry level."""
        if signal.type == "BUY":
            return current_price <= signal.entry_price
        elif signal.type == "SELL":
            return current_price >= signal.entry_price
        return False
    
    def _cleanup_expired_signals(self):
        """Remove expired signals and trigger auto-requery if configured."""
        original_count = len(self.active_signals)
        
        # Check for TTL expired signals before cleanup
        ttl_expired = False
        for signal in self.active_signals:
            if signal.status == "pending":
                validity_minutes = self.config.get('market_analyst', {}).get('signals', {}).get('validity_minutes', 60)
                created_time = datetime.fromisoformat(signal.created_at)
                age_minutes = (datetime.now() - created_time).total_seconds() / 60
                
                if age_minutes > validity_minutes:
                    ttl_expired = True
                    logger.warning(f"[AI-Signal] ⏱️ Signal {signal.id} TTL expired ({age_minutes:.1f}/{validity_minutes} min)")
                    break
        
        # Cleanup expired signals
        now = datetime.now()
        expired_statuses = {"expired", "time_expired", "price_invalidated", "triggered"}
        
        self.active_signals = [
            s for s in self.active_signals
            if s.status == "pending" and not s.is_expired()
        ]
        
        removed = original_count - len(self.active_signals)
        if removed > 0:
            logger.info(f"[AI-Signal] Cleaned up {removed} expired/invalidated/triggered signals")
            self._save_state()
        
        # Trigger auto-requery if TTL expired and enabled
        if ttl_expired:
            auto_requery = self.config.get('trading', {}).get('signal_ttl', {}).get('auto_requery_on_expire', True)
            if auto_requery and hasattr(self, 'scheduler') and self.scheduler:
                logger.info("[AI-Signal] 🔄 Triggering auto-requery (TTL expired)")
                self.scheduler.trigger_immediate_analysis(reason="ttl_expired")
    
    def set_scheduler(self, scheduler):
        """Set reference to analyst_scheduler for auto-requery."""
        self.scheduler = scheduler
        logger.info("[AI-Signal] Scheduler reference set for auto-requery")
    
    def set_executor(self, executor):
        """Set reference to live trader executor for position checks."""
        self.executor = executor
        logger.info("[AI-Signal] Executor reference set for position checks")
    
    def _schedule_none_retry(self, symbol: str):
        """
        Schedule automatic retry in 15 minutes after NONE decision.
        
        Before triggering, checks that no pending signal exists for the symbol
        to avoid creating duplicates.
        
        Args:
            symbol: Trading symbol for retry
        """
        try:
            if not hasattr(self, 'scheduler') or not self.scheduler:
                logger.warning("[AI-Signal] No scheduler reference - cannot schedule NONE retry")
                return
            
            # Use threading.Timer for 15-minute delay
            def retry_callback():
                # Check if pending signal exists before retry
                pending_count = sum(
                    1 for s in self.active_signals 
                    if s.symbol == symbol and s.status == "pending"
                )
                
                if pending_count > 0:
                    logger.info(
                        f"[AI-Signal] 🔄 NONE retry cancelled: "
                        f"{pending_count} pending signal(s) exist for {symbol}"
                    )
                    return
                
                # Trigger immediate analysis
                logger.info(f"[AI-Signal] 🔄 Triggering retry after NONE decision for {symbol}")
                self.scheduler.trigger_immediate_analysis(reason=f"none_retry_{symbol}")
            
            # Schedule for 15 minutes (900 seconds)
            retry_timer = threading.Timer(900, retry_callback)
            retry_timer.daemon = True
            retry_timer.start()
            
            logger.info(f"[AI-Signal] ⏰ Scheduled NONE retry for {symbol} in 15 minutes")
            
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to schedule NONE retry: {e}")
    
    
    def get_trading_permission(
        self, 
        symbol: str = None
    ) -> Tuple[bool, float, str]:
        """
        Get trading permission with risk multiplier.
        
        Returns:
            (allowed: bool, risk_multiplier: float, reason: str)
        """
        # Check time restrictions first
        time_allowed, time_reason = self._is_trading_time_allowed()
        if not time_allowed:
            return False, 0.0, time_reason
        
        # Check if block expired
        if self.block_until:
            try:
                until = datetime.fromisoformat(self.block_until)
                if datetime.now() > until:
                    self.block_type = BlockType.NONE
                    self.block_reason = None
                    self.block_until = None
                    self.risk_multiplier = 1.0
                    logger.info("[AI-Signal] Block expired - CLEARED")
            except:
                pass
        
        # Return permission based on block type
        if self.block_type == BlockType.HARD_BLOCK:
            return False, 0.0, self.block_reason or "Hard block active"
        
        # All other types allow trading with multiplier
        return True, self.risk_multiplier, self.block_reason or "OK"
    
    def get_active_signals(self, symbol: str = None) -> List[Dict]:
        """Get active signals."""
        with self._lock:
            signals = [s for s in self.active_signals if not s.is_expired()]
            if symbol:
                signals = [s for s in signals if s.symbol == symbol]
            
            # Sort by priority
            signals.sort(key=lambda s: s.priority, reverse=True)
            
            return [s.to_dict() for s in signals]
    
    def cancel_signal(self, signal_id: str) -> bool:
        """Cancel specific signal."""
        with self._lock:
            for signal in self.active_signals:
                if signal.id == signal_id:
                    signal.status = "cancelled"
                    self.signal_history.append({
                        "action": "cancelled",
                        "signal_id": signal_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    self._save_state()
                    logger.info(f"[AI-Signal] Cancelled: {signal_id}")
                    return True
        return False
    
    def mark_signal_filled(self, signal_id: str, filled_price: float = None) -> bool:
        """
        Mark signal as filled after position opened.
        This removes the signal from active list.
        
        Args:
            signal_id: Signal ID (or symbol for backwards compatibility)
            filled_price: Actual fill price
        
        Returns:
            True if signal was found and marked, False otherwise
        """
        with self._lock:
            for signal in self.active_signals:
                # Match by ID or by symbol (for backwards compatibility)
                if signal.id == signal_id or signal.symbol == signal_id:
                    signal.status = "filled"
                    
                    # Log to history
                    self.signal_history.append({
                        "action": "filled",
                        "signal_id": signal.id,
                        "timestamp": datetime.now().isoformat(),
                        "filled_price": filled_price
                    })
                    
                    # Remove from active list
                    self.active_signals.remove(signal)
                    self._save_state()
                    
                    logger.info(f"[AI-Signal] Signal {signal.id} marked as FILLED @ {filled_price}")
                    return True
        
        logger.warning(f"[AI-Signal] Signal {signal_id} not found for marking as filled")
        return False
    
    def clear_all_signals(self):
        """Clear all signals."""
        with self._lock:
            self.active_signals = []
            self.block_type = BlockType.NONE
            self.block_reason = None
            self.block_until = None
            self.risk_multiplier = 1.0
            self._save_state()
            logger.info("[AI-Signal] All signals cleared")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get status summary."""
        with self._lock:
            active = [s for s in self.active_signals if not s.is_expired()]
            
            return {
                "block_type": self.block_type.value,
                "block_reason": self.block_reason,
                "risk_multiplier": self.risk_multiplier,
                "active_signals_count": len(active),
                "pending_count": len([s for s in active if s.status == "pending"]),
                "triggered_count": len([s for s in active if s.status == "triggered"]),
                "latest_analysis": self.latest_analysis_time,
                "analysis_version": self.latest_analysis_version
            }
    
    def _save_state(self):
        """Save state to file."""
        try:
            # Сохраняем pending и triggered сигналы (triggered нужны для исполнения после перезапуска)
            active_signals_to_save = [
                s.to_dict() for s in self.active_signals 
                if s.status in ["pending", "triggered"] and not s.is_expired()
            ]
            
            state = {
                "block_type": self.block_type.value,
                "block_reason": self.block_reason,
                "block_until": self.block_until,
                "risk_multiplier": self.risk_multiplier,
                "latest_analysis_time": self.latest_analysis_time,
                "latest_analysis_version": self.latest_analysis_version,
                "active_signals": active_signals_to_save,
                "signal_history": self.signal_history[-100:],  # Last 100
                "updated_at": datetime.now().isoformat()
            }
            
            filepath = self.signals_dir / "active_signals.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to save state: {e}")
    
    def _load_state(self, verbose: bool = False):
        """Load state from file.
        
        Args:
            verbose: If True, log only on first load. If False, only log when state changes.
        """
        try:
            filepath = self.signals_dir / "active_signals.json"
            if not filepath.exists():
                self._state_loaded = True
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Backward compatibility: если state это список (старый формат), создаём новый формат
            if isinstance(state, list):
                logger.info(f"[AI-Signal] Converting old format (list) to new format (dict)")
                state = {
                    "active_signals": state,
                    "block_type": "none",
                    "block_reason": None,
                    "block_until": None,
                    "risk_multiplier": 1.0,
                    "signal_history": []
                }
            
            # Track if state changed
            old_signal_count = len(self.active_signals)
            old_block_type = self.block_type.value
            
            # Load block state
            block_type_str = state.get("block_type", "none")
            self.block_type = BlockType(block_type_str)
            self.block_reason = state.get("block_reason")
            self.block_until = state.get("block_until")
            self.risk_multiplier = state.get("risk_multiplier", 1.0)
            
            # Load metadata
            self.latest_analysis_time = state.get("latest_analysis_time")
            self.latest_analysis_version = state.get("latest_analysis_version")
            
            # Load signals
            self.active_signals = []  # Clear and reload
            validity_minutes = self.config.get('market_analyst', {}).get('signals', {}).get('validity_minutes', 60)
            now = datetime.now()
            
            # Track loaded signals to prevent duplicates
            loaded_signal_ids = set()
            
            # Список допустимых полей AISignal
            valid_fields = {
                'id', 'symbol', 'type', 'entry_price', 'stop_loss', 'take_profit',
                'trigger_time', 'reasoning', 'confidence', 'risk_reward', 
                'created_at', 'expires_at', 'analysis_version', 'status', 
                'triggered_at', 'priority'
            }
            
            for signal_data in state.get("active_signals", []):
                try:
                    # Фильтруем только допустимые поля (убираем 'direction' и другие старые поля)
                    filtered_data = {k: v for k, v in signal_data.items() if k in valid_fields}
                    signal = AISignal(**filtered_data)
                    
                    # Проверка дубликатов (по ID)
                    if signal.id in loaded_signal_ids:
                        logger.warning(f"[AI-Signal] Duplicate signal {signal.id} skipped on load")
                        continue
                    
                    # Проверяем статус (pending или triggered - оба допустимы)
                    if signal.status not in ["pending", "triggered"]:
                        continue
                    
                    # Проверяем 24h expiration
                    if signal.is_expired():
                        continue
                    
                    # Проверяем TTL (validity_minutes)
                    created_time = datetime.fromisoformat(signal.created_at)
                    age_minutes = (now - created_time).total_seconds() / 60
                    if age_minutes > validity_minutes:
                        logger.info(f"[AI-Signal] Signal {signal.id} skipped on load (age: {age_minutes:.1f}min > {validity_minutes}min)")
                        continue
                    
                    # Сигнал валиден - загружаем
                    self.active_signals.append(signal)
                    loaded_signal_ids.add(signal.id)  # Отмечаем как загруженный
                except Exception as e:
                    logger.warning(f"[AI-Signal] Failed to load signal: {e}")
            
            # Load history
            self.signal_history = state.get("signal_history", [])
            
            # Очистка истекших сигналов сразу после загрузки
            self._cleanup_expired_signals()
            
            # Если какие-то сигналы были отфильтрованы при загрузке, пересохраняем файл
            loaded_count = len(state.get("active_signals", []))
            current_count = len(self.active_signals)
            if loaded_count != current_count:
                logger.info(f"[AI-Signal] Filtered out {loaded_count - current_count} expired signals from file")
                self._save_state()
            
            # Only log if (verbose AND first load) OR state changed
            new_signal_count = len(self.active_signals)
            new_block_type = self.block_type.value
            
            should_log = (
                (verbose and not self._state_loaded) or 
                (new_signal_count != old_signal_count or new_block_type != old_block_type)
            )
            
            if should_log:
                logger.info(
                    f"[AI-Signal] Loaded state: {new_signal_count} signals, "
                    f"block={new_block_type}, multiplier={self.risk_multiplier}"
                )
            
            self._state_loaded = True
            
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to load state: {e}")


if __name__ == "__main__":
    # Test
    manager = AISignalManager()
    print(f"Status: {manager.get_status_summary()}")
    
    # Test permission
    allowed, multiplier, reason = manager.get_trading_permission()
    print(f"Trading: allowed={allowed}, multiplier={multiplier}, reason={reason}")

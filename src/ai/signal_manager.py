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
        
        self._lock = threading.Lock()
        self._load_state()
        
        logger.info("[AI-Signal] Manager v2.0 initialized")
    
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
    
    def process_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process AI analysis and create signals.
        
        Args:
            analysis: Analysis dict from MarketAnalystService
        
        Returns:
            Summary dict
        """
        try:
            with self._lock:
                # Update metadata
                self.latest_analysis_time = datetime.now().isoformat()
                self.latest_analysis_version = analysis.get("analysis_version", "1.0")
                
                summary = {
                    "signals_created": 0,
                    "signals_updated": 0,
                    "block_type": "none",
                    "risk_multiplier": 1.0
                }
                
                # Process trading blocks with new types
                blocks = analysis.get("trading_blocks", {})
                self._process_blocks(blocks, summary)
                
                # Process signals
                signals = analysis.get("signals", [])
                for signal_data in signals:
                    if self._validate_signal(signal_data):
                        signal = self._create_signal(
                            analysis["symbol"], 
                            signal_data,
                            analysis.get("analysis_version", "1.0")
                        )
                        self.active_signals.append(signal)
                        summary["signals_created"] += 1
                        
                        # Log to history
                        self.signal_history.append({
                            "action": "created",
                            "signal_id": signal.id,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        logger.info(
                            f"[AI-Signal] Created: {signal.type} @ {signal.entry_price} "
                            f"(conf: {signal.confidence}%, expires: {signal.expires_at[11:16]})"
                        )
                
                # Cleanup expired
                self._cleanup_expired_signals()
                
                # Save state
                self._save_state()
                
                return summary
                
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to process analysis: {e}")
            return {"error": str(e)}
    
    def _process_blocks(self, blocks: Dict, summary: Dict):
        """Process block information with new block types."""
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
        """Validate signal has required fields."""
        required = ["type", "entry_price", "stop_loss", "take_profit", "confidence"]
        for field in required:
            if field not in signal_data or signal_data[field] is None:
                logger.warning(f"[AI-Signal] Invalid signal - missing {field}")
                return False
        
        if signal_data["confidence"] < 50:
            logger.info(f"[AI-Signal] Skipped low confidence: {signal_data['confidence']}%")
            return False
        
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
        """Check if any signals should trigger."""
        triggered_signals = []
        
        with self._lock:
            for signal in self.active_signals:
                if signal.status != "pending" or signal.symbol != symbol:
                    continue
                
                if signal.is_expired():
                    signal.status = "expired"
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
                    
                    logger.info(f"[AI-Signal] Triggered: {signal.id}")
            
            if triggered_signals:
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
        """Remove expired signals."""
        original_count = len(self.active_signals)
        
        self.active_signals = [
            s for s in self.active_signals
            if not s.is_expired() or s.status == "triggered"
        ]
        
        removed = original_count - len(self.active_signals)
        if removed > 0:
            logger.info(f"[AI-Signal] Cleaned up {removed} expired signals")
    
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
            state = {
                "block_type": self.block_type.value,
                "block_reason": self.block_reason,
                "block_until": self.block_until,
                "risk_multiplier": self.risk_multiplier,
                "latest_analysis_time": self.latest_analysis_time,
                "latest_analysis_version": self.latest_analysis_version,
                "active_signals": [s.to_dict() for s in self.active_signals],
                "signal_history": self.signal_history[-100:],  # Last 100
                "updated_at": datetime.now().isoformat()
            }
            
            filepath = self.signals_dir / "active_signals.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to save state: {e}")
    
    def _load_state(self):
        """Load state from file."""
        try:
            filepath = self.signals_dir / "active_signals.json"
            if not filepath.exists():
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
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
            for signal_data in state.get("active_signals", []):
                try:
                    signal = AISignal(**signal_data)
                    if not signal.is_expired():
                        self.active_signals.append(signal)
                except Exception as e:
                    logger.warning(f"[AI-Signal] Failed to load signal: {e}")
            
            # Load history
            self.signal_history = state.get("signal_history", [])
            
            logger.info(
                f"[AI-Signal] Loaded state: {len(self.active_signals)} signals, "
                f"block={self.block_type.value}, multiplier={self.risk_multiplier}"
            )
            
        except Exception as e:
            logger.error(f"[AI-Signal] Failed to load state: {e}")


if __name__ == "__main__":
    # Test
    manager = AISignalManager()
    print(f"Status: {manager.get_status_summary()}")
    
    # Test permission
    allowed, multiplier, reason = manager.get_trading_permission()
    print(f"Trading: allowed={allowed}, multiplier={multiplier}, reason={reason}")

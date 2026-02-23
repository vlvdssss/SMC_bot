"""
Configuration Presets for Production Runs

Provides ready-to-use configuration presets for different trading scenarios.
Each preset is a complete configuration profile optimized for specific use cases.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class ConfigPreset:
    """Base class for configuration presets"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.config_changes: Dict[str, Any] = {}
    
    def get_config_changes(self) -> Dict[str, Any]:
        """
        Returns a dictionary of config changes to apply.
        Format: {"config_file.yaml": {"path.to.key": value}}
        """
        return self.config_changes
    
    def get_summary(self) -> Dict[str, Any]:
        """Returns a summary of key parameters for logging"""
        return {}


class XAUUSD_Safe_5Day_Preset(ConfigPreset):
    """
    XAUUSD 5-Day Run (Safe) - DEFAULT PRESET
    
    Purpose: Stable 5-day production run on XAUUSD only
    Strategy: Conservative filters, fixed lot size, quality over quantity
    
    Key Features:
    - XAUUSD only (no EURUSD)
    - High confidence threshold (75%)
    - Moderate daily limit (6 trades)
    - Conservative spread filter (1.5 pips)
    - Fixed lot size (no adaptive scaling)
    - Reasonable cooldowns (not 999 minutes)
    - Signal inversion OFF (proper signal interpretation)
    """
    
    def __init__(self):
        super().__init__(
            name="XAUUSD_SAFE_5D",
            description="XAUUSD 5-Day Safe - Balanced quality and frequency"
        )
        
        # Define all configuration changes
        self.config_changes = {
            # ==================== AI.YAML ====================
            "ai.yaml": {
                "pure_ai.symbols": ["XAUUSD"],
            },
            
            # ==================== PORTFOLIO.YAML ====================
            "portfolio.yaml": {
                "portfolio.instruments": ["XAUUSD"],
                "portfolio.allocation": {"XAUUSD": 1.0},
                "portfolio.name": "XAUUSD Pure Strategy (5-Day Safe)",
            },
            
            # ==================== TRADING.YAML ====================
            "trading.yaml": {
                # Core settings
                "trading.enabled": True,
                "trading.mode": "auto",
                "trading.dry_run": False,  # Set to true for initial testing
                
                # Filters (MOST CRITICAL)
                "trading.filters.enabled": True,
                "trading.filters.min_confidence": 75,
                "trading.filters.min_rr": 1.2,
                "trading.filters.min_setup_score": 70,
                "trading.filters.daily_limit": 6,
                "trading.filters.max_spread_pips": 1.5,  # Conservative for XAUUSD
                
                # Cooldowns (reasonable, not 999)
                "trading.filters.cooldown_after_win": 15,
                "trading.filters.cooldown_after_loss": 45,  # Not 90
                "trading.filters.cooldown_after_2_losses": 180,  # Not 240
                
                # HTF filter
                "trading.filters.htf_timeframe": "M15",
                "trading.filters.htf_ema_fast": 50,
                "trading.filters.htf_ema_slow": 200,
                
                # Signal quality (CRITICAL: invert_signals must be false)
                "trading.signal_quality.invert_signals": False,  # Proper signal interpretation
                
                # Signal TTL
                "trading.signal_ttl.enabled": True,
                "trading.signal_ttl.ttl_minutes": 30,
                "trading.signal_ttl.auto_requery_on_close": True,
                "trading.signal_ttl.auto_requery_on_expire": True,
                "trading.signal_ttl.auto_requery_on_invalidate": True,
                "trading.signal_ttl.requery_cooldown_minutes": 15,
                
                # Risk (fixed lot, no scaling)
                "trading.risk.fixed_lot_size": 0.01,
                "trading.risk.default_sl_pips": 40,
                "trading.risk.default_tp_pips": 100,
                "trading.risk.max_spread_pips": 1.5,
                
                # V5 improvements (adaptive lot OFF for stability)
                "trading.v5_improvements.adaptive_lot.enabled": False,
                "trading.v5_improvements.adaptive_lot.base_lot": 0.01,
                "trading.v5_improvements.adaptive_lot.max_lot": 0.05,
                "trading.v5_improvements.adaptive_lot.lookback_trades": 10,
                
                # Protections (reasonable cooldowns)
                "trading.profit_protection.enabled": True,
                "trading.profit_protection.consecutive_wins": 3,
                "trading.profit_protection.cooldown_minutes": 180,  # Not 999
                
                "trading.stop_loss_protection.enabled": True,
                "trading.stop_loss_protection.consecutive_stops": 2,
                "trading.stop_loss_protection.cooldown_minutes": 180,  # Not 999
                
                # Trading hours (XAUUSD safe window)
                "trading.hours.start": "01:10",
                "trading.hours.end": "23:30",
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Returns key parameters for logging"""
        return {
            "preset": self.name,
            "description": self.description,
            "symbol": "XAUUSD",
            "mode": "auto",
            "dry_run": False,
            "filters": {
                "min_confidence": 75,
                "min_rr": 1.2,
                "min_setup_score": 70,
                "daily_limit": 6,
                "max_spread_pips": 1.5,
            },
            "cooldowns": {
                "after_win": 15,
                "after_loss": 45,
                "after_2_losses": 180,
            },
            "protections": {
                "profit_protection_cooldown": 180,
                "stop_loss_protection_cooldown": 180,
            },
            "risk": {
                "fixed_lot_size": 0.01,
                "default_sl_pips": 40,
                "default_tp_pips": 100,
            },
            "signal_quality": {
                "invert_signals": False,  # CRITICAL
            },
            "v5_improvements": {
                "adaptive_lot": False,
            }
        }


class XAUUSD_Strict_Preset(ConfigPreset):
    """
    XAUUSD STRICT - Quality over Quantity
    
    Purpose: Fewer entries, higher accuracy, less noise
    Strategy: Very conservative filters, high confidence threshold
    
    Key Features:
    - Higher confidence (82% vs 75%)
    - Lower daily limit (4 vs 6)
    - Tighter spread (1.2 vs 1.5)
    - Longer cooldowns (reduces overtrading)
    - Shorter signal TTL (20 min - fresher signals)
    
    Best For:
    - When bot is "overtrading"
    - Choppy/sideways markets
    - Calm testing without excessive trades
    """
    
    def __init__(self):
        super().__init__(
            name="XAUUSD_STRICT",
            description="XAUUSD Strict - Few high-quality trades only"
        )
        
        self.config_changes = {
            # ==================== AI.YAML ====================
            "ai.yaml": {
                "pure_ai.symbols": ["XAUUSD"],
            },
            
            # ==================== PORTFOLIO.YAML ====================
            "portfolio.yaml": {
                "portfolio.instruments": ["XAUUSD"],
                "portfolio.allocation": {"XAUUSD": 1.0},
                "portfolio.name": "XAUUSD Strict Strategy (High Quality)",
            },
            
            # ==================== TRADING.YAML ====================
            "trading.yaml": {
                # Core settings
                "trading.enabled": True,
                "trading.mode": "auto",
                "trading.dry_run": False,
                
                # Filters (STRICT - quality over quantity)
                "trading.filters.enabled": True,
                "trading.filters.min_confidence": 82,  # Higher than SAFE (75)
                "trading.filters.min_rr": 1.3,  # Higher than SAFE (1.2)
                "trading.filters.min_setup_score": 78,  # Higher than SAFE (70)
                "trading.filters.daily_limit": 4,  # Lower than SAFE (6)
                "trading.filters.max_spread_pips": 1.2,  # Tighter than SAFE (1.5)
                
                # Cooldowns (longer to reduce overtrading)
                "trading.filters.cooldown_after_win": 20,  # vs SAFE (15)
                "trading.filters.cooldown_after_loss": 90,  # vs SAFE (45)
                "trading.filters.cooldown_after_2_losses": 240,  # vs SAFE (180)
                
                # HTF filter
                "trading.filters.htf_timeframe": "M15",
                "trading.filters.htf_ema_fast": 50,
                "trading.filters.htf_ema_slow": 200,
                
                # Signal quality (CRITICAL)
                "trading.signal_quality.invert_signals": False,
                
                # Signal TTL (shorter for fresher signals)
                "trading.signal_ttl.enabled": True,
                "trading.signal_ttl.ttl_minutes": 20,  # vs SAFE (30)
                "trading.signal_ttl.auto_requery_on_close": True,
                "trading.signal_ttl.auto_requery_on_expire": True,
                "trading.signal_ttl.auto_requery_on_invalidate": True,
                "trading.signal_ttl.requery_cooldown_minutes": 20,  # vs SAFE (15)
                
                # Risk (fixed lot, higher TP)
                "trading.risk.fixed_lot_size": 0.01,
                "trading.risk.default_sl_pips": 40,
                "trading.risk.default_tp_pips": 110,  # vs SAFE (100)
                "trading.risk.max_spread_pips": 1.2,
                
                # V5 improvements (adaptive lot OFF)
                "trading.v5_improvements.adaptive_lot.enabled": False,
                "trading.v5_improvements.adaptive_lot.base_lot": 0.01,
                "trading.v5_improvements.adaptive_lot.max_lot": 0.05,
                "trading.v5_improvements.adaptive_lot.lookback_trades": 10,
                
                # Protections (longer cooldowns)
                "trading.profit_protection.enabled": True,
                "trading.profit_protection.consecutive_wins": 3,
                "trading.profit_protection.cooldown_minutes": 240,  # vs SAFE (180)
                
                "trading.stop_loss_protection.enabled": True,
                "trading.stop_loss_protection.consecutive_stops": 2,
                "trading.stop_loss_protection.cooldown_minutes": 240,  # vs SAFE (180)
                
                # Trading hours
                "trading.hours.start": "01:10",
                "trading.hours.end": "23:30",
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "preset": self.name,
            "description": self.description,
            "symbol": "XAUUSD",
            "mode": "auto",
            "dry_run": False,
            "filters": {
                "min_confidence": 82,
                "min_rr": 1.3,
                "min_setup_score": 78,
                "daily_limit": 4,
                "max_spread_pips": 1.2,
            },
            "cooldowns": {
                "after_win": 20,
                "after_loss": 90,
                "after_2_losses": 240,
            },
            "protections": {
                "profit_protection_cooldown": 240,
                "stop_loss_protection_cooldown": 240,
            },
            "risk": {
                "fixed_lot_size": 0.01,
                "default_sl_pips": 40,
                "default_tp_pips": 110,
            },
            "signal_quality": {
                "invert_signals": False,
            },
            "signal_ttl": {
                "ttl_minutes": 20,
                "requery_cooldown": 20,
            },
            "v5_improvements": {
                "adaptive_lot": False,
            }
        }


class XAUUSD_Active_Preset(ConfigPreset):
    """
    XAUUSD ACTIVE - More Trades, Controlled Risk
    
    Purpose: Catch more moves without becoming a casino
    Strategy: Lower threshold, more frequent entries, shorter cooldowns
    
    Key Features:
    - Lower confidence (70% vs 75%)
    - Higher daily limit (8 vs 6)
    - Wider spread tolerance (1.8 vs 1.5)
    - Shorter cooldowns (catch more moves)
    - Longer signal TTL (45 min - more flexible)
    - Lower TP (90 vs 100 - take profit faster)
    
    Best For:
    - When too few trades on SAFE/STRICT
    - Need to accumulate statistics faster
    - Trending markets with good movement
    """
    
    def __init__(self):
        super().__init__(
            name="XAUUSD_ACTIVE",
            description="XAUUSD Active - More frequent trades without chaos"
        )
        
        self.config_changes = {
            # ==================== AI.YAML ====================
            "ai.yaml": {
                "pure_ai.symbols": ["XAUUSD"],
            },
            
            # ==================== PORTFOLIO.YAML ====================
            "portfolio.yaml": {
                "portfolio.instruments": ["XAUUSD"],
                "portfolio.allocation": {"XAUUSD": 1.0},
                "portfolio.name": "XAUUSD Active Strategy (Higher Frequency)",
            },
            
            # ==================== TRADING.YAML ====================
            "trading.yaml": {
                # Core settings
                "trading.enabled": True,
                "trading.mode": "auto",
                "trading.dry_run": False,
                
                # Filters (ACTIVE - more trades)
                "trading.filters.enabled": True,
                "trading.filters.min_confidence": 70,  # Lower than SAFE (75)
                "trading.filters.min_rr": 1.15,  # Lower than SAFE (1.2)
                "trading.filters.min_setup_score": 65,  # Lower than SAFE (70)
                "trading.filters.daily_limit": 8,  # Higher than SAFE (6)
                "trading.filters.max_spread_pips": 1.8,  # Wider than SAFE (1.5)
                
                # Cooldowns (shorter to catch more moves)
                "trading.filters.cooldown_after_win": 10,  # vs SAFE (15)
                "trading.filters.cooldown_after_loss": 30,  # vs SAFE (45)
                "trading.filters.cooldown_after_2_losses": 120,  # vs SAFE (180)
                
                # HTF filter
                "trading.filters.htf_timeframe": "M15",
                "trading.filters.htf_ema_fast": 50,
                "trading.filters.htf_ema_slow": 200,
                
                # Signal quality (CRITICAL)
                "trading.signal_quality.invert_signals": False,
                
                # Signal TTL (longer for more flexibility)
                "trading.signal_ttl.enabled": True,
                "trading.signal_ttl.ttl_minutes": 45,  # vs SAFE (30)
                "trading.signal_ttl.auto_requery_on_close": True,
                "trading.signal_ttl.auto_requery_on_expire": True,
                "trading.signal_ttl.auto_requery_on_invalidate": True,
                "trading.signal_ttl.requery_cooldown_minutes": 10,  # vs SAFE (15)
                
                # Risk (fixed lot, lower TP for faster exits)
                "trading.risk.fixed_lot_size": 0.01,
                "trading.risk.default_sl_pips": 40,
                "trading.risk.default_tp_pips": 90,  # vs SAFE (100)
                "trading.risk.max_spread_pips": 1.8,
                
                # V5 improvements (adaptive lot OFF)
                "trading.v5_improvements.adaptive_lot.enabled": False,
                "trading.v5_improvements.adaptive_lot.base_lot": 0.01,
                "trading.v5_improvements.adaptive_lot.max_lot": 0.05,
                "trading.v5_improvements.adaptive_lot.lookback_trades": 10,
                
                # Protections (shorter cooldowns, more tolerance)
                "trading.profit_protection.enabled": True,
                "trading.profit_protection.consecutive_wins": 4,  # vs SAFE (3)
                "trading.profit_protection.cooldown_minutes": 120,  # vs SAFE (180)
                
                "trading.stop_loss_protection.enabled": True,
                "trading.stop_loss_protection.consecutive_stops": 3,  # vs SAFE (2)
                "trading.stop_loss_protection.cooldown_minutes": 120,  # vs SAFE (180)
                
                # Trading hours
                "trading.hours.start": "01:10",
                "trading.hours.end": "23:30",
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "preset": self.name,
            "description": self.description,
            "symbol": "XAUUSD",
            "mode": "auto",
            "dry_run": False,
            "filters": {
                "min_confidence": 70,
                "min_rr": 1.15,
                "min_setup_score": 65,
                "daily_limit": 8,
                "max_spread_pips": 1.8,
            },
            "cooldowns": {
                "after_win": 10,
                "after_loss": 30,
                "after_2_losses": 120,
            },
            "protections": {
                "profit_protection_cooldown": 120,
                "stop_loss_protection_cooldown": 120,
            },
            "risk": {
                "fixed_lot_size": 0.01,
                "default_sl_pips": 40,
                "default_tp_pips": 90,
            },
            "signal_quality": {
                "invert_signals": False,
            },
            "signal_ttl": {
                "ttl_minutes": 45,
                "requery_cooldown": 10,
            },
            "v5_improvements": {
                "adaptive_lot": False,
            }
        }


# ==================== PRESET REGISTRY ====================

AVAILABLE_PRESETS: Dict[str, ConfigPreset] = {
    "XAUUSD_SAFE_5D": XAUUSD_Safe_5Day_Preset(),
    "XAUUSD_STRICT": XAUUSD_Strict_Preset(),
    "XAUUSD_ACTIVE": XAUUSD_Active_Preset(),
}

DEFAULT_PRESET = "XAUUSD_SAFE_5D"


# ==================== PRESET MANAGER ====================

class PresetManager:
    """Manages configuration presets"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        logger.info(f"[PresetManager] Initialized with config_dir: {config_dir}")
    
    def get_preset(self, preset_name: str) -> ConfigPreset:
        """Get a preset by name"""
        if preset_name not in AVAILABLE_PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(AVAILABLE_PRESETS.keys())}")
        return AVAILABLE_PRESETS[preset_name]
    
    def list_presets(self) -> List[str]:
        """List all available presets"""
        return list(AVAILABLE_PRESETS.keys())
    
    def apply_preset(self, preset_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply a preset to configuration files
        
        Args:
            preset_name: Name of the preset to apply
            dry_run: If True, only return changes without applying
        
        Returns:
            Dict with applied changes and summary
        """
        preset = self.get_preset(preset_name)
        config_changes = preset.get_config_changes()
        
        logger.info(f"[PresetManager] Applying preset: {preset_name}")
        logger.info(f"[PresetManager] Description: {preset.description}")
        
        applied_changes = {}
        
        for config_file, changes in config_changes.items():
            config_path = self.config_dir / config_file
            
            if not config_path.exists():
                logger.error(f"[PresetManager] Config file not found: {config_path}")
                continue
            
            logger.info(f"[PresetManager] Processing {config_file}: {len(changes)} changes")
            
            if not dry_run:
                # Load existing config
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                # Apply changes
                for key_path, value in changes.items():
                    keys = key_path.split('.')
                    current = config
                    
                    # Navigate to the parent key
                    for key in keys[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    
                    # Set the value
                    old_value = current.get(keys[-1], "NOT_SET")
                    current[keys[-1]] = value
                    
                    logger.info(f"  [{config_file}] {key_path}: {old_value} → {value}")
                    applied_changes[f"{config_file}::{key_path}"] = {
                        "old": old_value,
                        "new": value
                    }
                
                # Save config
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
                logger.info(f"[PresetManager] ✅ Saved {config_file}")
        
        summary = preset.get_summary()
        
        logger.info(f"[PresetManager] ✅ Preset '{preset_name}' applied successfully")
        logger.info(f"[PresetManager] 🔑 Key Parameters:")
        self._log_summary(summary)
        
        return {
            "success": True,
            "preset": preset_name,
            "description": preset.description,
            "applied_changes": applied_changes,
            "summary": summary
        }
    
    def _log_summary(self, summary: Dict[str, Any], indent: int = 0):
        """Recursively log summary with proper formatting"""
        prefix = "  " * indent
        for key, value in summary.items():
            if isinstance(value, dict):
                logger.info(f"{prefix}  • {key}:")
                self._log_summary(value, indent + 1)
            else:
                logger.info(f"{prefix}  • {key}: {value}")


# ==================== SINGLETON ====================

_preset_manager: PresetManager = None

def get_preset_manager(config_dir: Path = None) -> PresetManager:
    """Get singleton PresetManager instance"""
    global _preset_manager
    if _preset_manager is None:
        if config_dir is None:
            # Default config directory
            config_dir = Path(__file__).parent.parent.parent / "config"
        _preset_manager = PresetManager(config_dir)
    return _preset_manager


# ==================== HELPER FUNCTIONS ====================

def apply_default_preset():
    """Apply the default preset (XAUUSD_SAFE_5D)"""
    manager = get_preset_manager()
    return manager.apply_preset(DEFAULT_PRESET)


def get_preset_summary(preset_name: str) -> Dict[str, Any]:
    """Get summary of a preset without applying it"""
    manager = get_preset_manager()
    preset = manager.get_preset(preset_name)
    return preset.get_summary()

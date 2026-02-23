#!/usr/bin/env python3
"""
Settings Dialogs V2 - Модальные окна настроек для GUI V2
Без открытия редакторов - все в Toplevel окнах
"""

import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from pathlib import Path
import threading
import time
import os
import requests
try:
    import openai
except ImportError:
    openai = None
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from src.core.logger import logger
from src.core.config_manager import get_config_manager


# ==================== CONFIG SCHEMA ====================
CONFIG_SCHEMA = {
    # Trading Settings
    "trading_enabled": {"type": bool, "default": True, "tab": "Trading", "label": "Trading Enabled"},
    "dry_run_mode": {"type": bool, "default": False, "tab": "Trading", "label": "🧪 DRY RUN Mode (No Real Orders)"},
    "trading_mode": {"type": str, "default": "auto", "tab": "Trading", "label": "Trading Mode", 
                     "options": ["auto", "semi-auto", "manual"]},
    "fixed_lot_size": {"type": float, "default": 0.01, "tab": "Trading", "label": "Fixed Lot Size", "min": 0.01, "max": 10.0},
    "default_sl_pips": {"type": int, "default": 40, "tab": "Trading", "label": "Default SL (pips)", "min": 10, "max": 200},
    "default_tp_pips": {"type": int, "default": 100, "tab": "Trading", "label": "Default TP (pips)", "min": 20, "max": 500},
    
    # Risk Management
    "risk_percent": {"type": float, "default": 1.0, "tab": "Risk", "label": "Risk % per Trade", "min": 0.1, "max": 5.0},
    "max_daily_loss": {"type": float, "default": 50.0, "tab": "Risk", "label": "Max Daily Loss ($)", "min": 0},
    "max_daily_profit": {"type": float, "default": 150.0, "tab": "Risk", "label": "Max Daily Profit ($)", "min": 0},
    "max_open_positions": {"type": int, "default": 3, "tab": "Risk", "label": "Max Open Positions", "min": 1, "max": 10},
    "max_trades_per_hour": {"type": int, "default": 5, "tab": "Risk", "label": "Max Trades/Hour", "min": 1, "max": 20},
    "max_losses_in_row": {"type": int, "default": 3, "tab": "Risk", "label": "Max Losses in Row (0=off)", "min": 0, "max": 10},
    # NOTE: Daily trade limit moved to Filters tab (filter_daily_limit)
    
    # Trade Filters (NEW - from trading.yaml)
    "filter_enabled": {"type": bool, "default": True, "tab": "Filters", "label": "Trade Filters Enabled"},
    "filter_min_confidence": {"type": int, "default": 75, "tab": "Filters", "label": "Min Confidence %", "min": 50, "max": 95},
    "filter_min_setup_score": {"type": int, "default": 70, "tab": "Filters", "label": "Min Setup Score", "min": 50, "max": 100},
    "filter_min_rr": {"type": float, "default": 1.2, "tab": "Filters", "label": "Min Risk/Reward", "min": 1.0, "max": 5.0},
    "filter_max_spread_pips": {"type": float, "default": 3.0, "tab": "Filters", "label": "Max Spread (pips)", "min": 0.5, "max": 10.0},
    "filter_daily_limit": {"type": int, "default": 6, "tab": "Filters", "label": "Daily Trade Limit", "min": 1, "max": 50},
    "filter_cooldown_win": {"type": int, "default": 15, "tab": "Filters", "label": "Cooldown After Win (min)", "min": 0, "max": 120},
    "filter_cooldown_loss": {"type": int, "default": 90, "tab": "Filters", "label": "Cooldown After Loss (min)", "min": 0, "max": 300},
    "filter_cooldown_2losses": {"type": int, "default": 240, "tab": "Filters", "label": "Cooldown After 2 Losses (min)", "min": 0, "max": 600},
    "filter_htf_timeframe": {"type": str, "default": "M15", "tab": "Filters", "label": "HTF Timeframe", "options": ["M5", "M15", "M30", "H1", "H4"]},
    "filter_htf_ema_fast": {"type": int, "default": 50, "tab": "Filters", "label": "HTF EMA Fast", "min": 10, "max": 100},
    "filter_htf_ema_slow": {"type": int, "default": 200, "tab": "Filters", "label": "HTF EMA Slow", "min": 100, "max": 300},
    
    # Trailing Stop
    "trailing_enabled": {"type": bool, "default": True, "tab": "Trading", "label": "Trailing Stop Enabled"},
    "trailing_activation_percent": {"type": int, "default": 30, "tab": "Trading", "label": "Trailing Activation %", "min": 10, "max": 90},
    "trailing_step_percent": {"type": int, "default": 10, "tab": "Trading", "label": "Trailing Step %", "min": 5, "max": 30},
    
    # Stop Loss Protection
    "stop_protection_enabled": {"type": bool, "default": True, "tab": "Risk", "label": "Stop Loss Protection"},
    "stop_consecutive_stops": {"type": int, "default": 2, "tab": "Risk", "label": "Consecutive Stops", "min": 1, "max": 5},
    "stop_cooldown_minutes": {"type": int, "default": 10, "tab": "Risk", "label": "Cooldown (min)", "min": 1, "max": 60},
    
    # Profit Protection
    "profit_protection_enabled": {"type": bool, "default": True, "tab": "Risk", "label": "Profit Protection"},
    "profit_consecutive_wins": {"type": int, "default": 3, "tab": "Risk", "label": "Consecutive Wins", "min": 2, "max": 10},
    "profit_cooldown_minutes": {"type": int, "default": 20, "tab": "Risk", "label": "Cooldown (min)", "min": 1, "max": 120},
    
    # AI Settings
    "ai_enabled": {"type": bool, "default": True, "tab": "AI", "label": "AI Enabled"},
    "ai_model": {"type": str, "default": "gpt-4o", "tab": "AI", "label": "GPT Model", 
                 "options": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]},
    "ai_temperature": {"type": float, "default": 0.3, "tab": "AI", "label": "Temperature", "min": 0.0, "max": 1.0},
    # NOTE: Min confidence moved to Filters tab (filter_min_confidence)
    "ai_interval_minutes": {"type": int, "default": 60, "tab": "AI", "label": "Analysis Interval (min)", "min": 15, "max": 240},
    "ai_timeout": {"type": int, "default": 30, "tab": "AI", "label": "API Timeout (sec)", "min": 10, "max": 120},
    "ai_force_json": {"type": bool, "default": True, "tab": "AI", "label": "Force JSON Response"},
    
    # Time Restrictions
    "night_block_enabled": {"type": bool, "default": False, "tab": "AI", "label": "Block Night Trading"},
    "weekend_block_enabled": {"type": bool, "default": True, "tab": "AI", "label": "Block Weekend Trading"},
    
    # Signal TTL
    "signal_ttl_minutes": {"type": int, "default": 30, "tab": "AI", "label": "Signal TTL (min)", "min": 5, "max": 120},
    "signal_auto_requery": {"type": bool, "default": True, "tab": "AI", "label": "Auto Re-query on Expire"},
    
    # Logging
    "log_level": {"type": str, "default": "INFO", "tab": "Logging", "label": "Log Level", 
                  "options": ["DEBUG", "INFO", "WARNING", "ERROR"]},
    "log_autosave": {"type": bool, "default": True, "tab": "Logging", "label": "Auto-save Logs"},
    "log_export_path": {"type": str, "default": "logs/", "tab": "Logging", "label": "Export Path"},
    
    # V5 Improvements
    "adaptive_lot_enabled": {"type": bool, "default": True, "tab": "Advanced", "label": "Adaptive Lot Size"},
    "adaptive_lot_base": {"type": float, "default": 0.01, "tab": "Advanced", "label": "Base Lot", "min": 0.01, "max": 1.0},
    "adaptive_lot_max": {"type": float, "default": 0.05, "tab": "Advanced", "label": "Max Lot", "min": 0.01, "max": 5.0},
    "adaptive_lot_lookback": {"type": int, "default": 10, "tab": "Advanced", "label": "Lookback Trades", "min": 5, "max": 50},
}


# ==================== COLORS ====================
class Colors:
    BG_DARK = '#0d1117'
    BG_PANEL = '#161b22'
    BG_CARD = '#1c2128'
    BG_HOVER = '#21262d'
    BORDER = '#30363d'
    TEXT_PRIMARY = '#c9d1d9'
    TEXT_SECONDARY = '#8b949e'
    TEXT_MUTED = '#6e7681'
    ACCENT = '#58a6ff'
    SUCCESS = '#3fb950'
    ERROR = '#f85149'
    WARNING = '#d29922'


# ==================== SETTINGS DIALOG ====================
class SettingsDialog(tk.Toplevel):
    """Главное окно настроек с вкладками"""
    
    def __init__(self, parent, title="Settings", initial_config=None, on_save=None):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        self.initial_config = initial_config or {}
        
        self.title(title)
        self.configure(bg=Colors.BG_DARK)
        self.resizable(False, False)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        
        # Центрирование
        self.update_idletasks()
        w, h = 650, 600
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.vars = {}
        self._build_ui()
        
        # Загрузить конфиги из YAML
        self._load_configs()
    
    def _build_ui(self):
        """Построить UI"""
        # Header
        header = tk.Frame(self, bg=Colors.BG_PANEL, height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="⚙️ Settings",
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.TEXT_PRIMARY).pack(side='left', padx=20, pady=15)
        
        # Separator
        tk.Frame(self, bg=Colors.BORDER, height=1).pack(fill='x')
        
        # Notebook (НЕ трогаем стили - используем тему приложения)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Создать вкладки
        tabs = {}
        for tab_name in ["Trading", "Risk", "Filters", "AI", "Logging", "Advanced"]:
            frame = tk.Frame(nb, bg=Colors.BG_DARK)
            
            # Scrollable canvas
            canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
            scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
            content = tk.Frame(canvas, bg=Colors.BG_DARK)
            
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            canvas.pack(side='left', fill='both', expand=True)
            canvas.create_window((0, 0), window=content, anchor='nw')
            
            content.bind('<Configure>', lambda e, c=canvas: c.configure(scrollregion=c.bbox('all')))
            
            tabs[tab_name] = content
            nb.add(frame, text=tab_name)
        
        # Заполнить вкладки по schema
        for key, meta in CONFIG_SCHEMA.items():
            tab_name = meta["tab"]
            if tab_name not in tabs:
                continue
            
            content = tabs[tab_name]
            self._create_field(content, key, meta)
        
        # Добавить кастомные вкладки GPT API и Telegram
        self._create_gpt_api_tab(nb)
        self._create_telegram_tab(nb)
        
        # Кнопки
        btns = tk.Frame(self, bg=Colors.BG_DARK)
        btns.pack(fill='x', padx=15, pady=(0, 15))
        
        tk.Button(btns, text="Reset to Default",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_SECONDARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 padx=15, pady=8,
                 command=self._reset_defaults).pack(side='left')
        
        tk.Button(btns, text="Cancel",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 padx=15, pady=8,
                 command=self._cancel).pack(side='right')
        
        tk.Button(btns, text="Save",
                 font=('Arial', 10, 'bold'),
                 bg=Colors.SUCCESS,
                 fg='white',
                 activebackground='#2ea043',
                 relief='flat',
                 padx=20, pady=8,
                 command=self._save).pack(side='right', padx=(0, 8))
    
    def _create_field(self, parent, key, meta):
        """Создать поле по схеме"""
        row = tk.Frame(parent, bg=Colors.BG_DARK)
        row.pack(fill='x', pady=6, padx=15)
        
        # Label
        tk.Label(row, text=meta["label"],
                font=('Arial', 9),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY,
                anchor='w').pack(side='left', fill='x', expand=True)
        
        # Widget
        field_type = meta["type"]
        
        if field_type == bool:
            var = tk.BooleanVar(value=meta["default"])
            self.vars[key] = var
            tk.Checkbutton(row, variable=var,
                          bg=Colors.BG_DARK,
                          activebackground=Colors.BG_DARK,
                          selectcolor=Colors.BG_CARD,
                          highlightthickness=0).pack(side='right')
        
        elif "options" in meta:
            var = tk.StringVar(value=meta["default"])
            self.vars[key] = var
            combo = ttk.Combobox(row, textvariable=var,
                                values=meta["options"],
                                width=15,
                                state='readonly')
            combo.pack(side='right')
        
        elif field_type in (int, float):
            if field_type == int:
                var = tk.IntVar(value=meta["default"])
            else:
                var = tk.DoubleVar(value=meta["default"])
            self.vars[key] = var
            
            entry = tk.Entry(row, textvariable=var,
                           font=('Arial', 9),
                           width=12,
                           bg=Colors.BG_CARD,
                           fg=Colors.TEXT_PRIMARY,
                           insertbackground=Colors.TEXT_PRIMARY,
                           relief='flat',
                           highlightthickness=1,
                           highlightbackground=Colors.BORDER,
                           highlightcolor=Colors.ACCENT)
            entry.pack(side='right')
        
        elif field_type == str:
            var = tk.StringVar(value=meta["default"])
            self.vars[key] = var
            entry = tk.Entry(row, textvariable=var,
                           font=('Arial', 9),
                           width=20,
                           bg=Colors.BG_CARD,
                           fg=Colors.TEXT_PRIMARY,
                           insertbackground=Colors.TEXT_PRIMARY,
                           relief='flat',
                           highlightthickness=1,
                           highlightbackground=Colors.BORDER,
                           highlightcolor=Colors.ACCENT)
            entry.pack(side='right')
    
    def _load_configs(self):
        """Загрузить значения из конфигов"""
        try:
            # Trading config
            trading_path = Path('config/trading.yaml')
            if trading_path.exists():
                with open(trading_path, 'r', encoding='utf-8') as f:
                    trading_config = yaml.safe_load(f) or {}
                
                trading = trading_config.get('trading', {})
                risk = trading.get('risk', {})
                trailing = trading.get('trailing_stop', {})
                stop_prot = trading.get('stop_loss_protection', {})
                profit_prot = trading.get('profit_protection', {})
                signal_ttl = trading.get('signal_ttl', {})
                v5 = trading.get('v5_improvements', {}).get('adaptive_lot', {})
                filters = trading.get('filters', {})  # NEW: Trade Filters
                
                # Map to vars
                mapping = {
                    'trading_enabled': trading.get('enabled', True),
                    'dry_run_mode': trading.get('dry_run', False),
                    'trading_mode': trading.get('mode', 'manual'),
                    'fixed_lot_size': risk.get('fixed_lot_size', 0.01),
                    'default_sl_pips': risk.get('default_sl_pips', 40),
                    'default_tp_pips': risk.get('default_tp_pips', 100),
                    # max_spread_pips removed - use filter_max_spread_pips instead
                    'trailing_enabled': trailing.get('enabled', True),
                    'trailing_activation_percent': trailing.get('activation_profit_percent', 30),
                    'trailing_step_percent': trailing.get('trailing_step_percent', 10),
                    'stop_protection_enabled': stop_prot.get('enabled', True),
                    'stop_consecutive_stops': stop_prot.get('consecutive_stops', 2),
                    'stop_cooldown_minutes': stop_prot.get('cooldown_minutes', 10),
                    'profit_protection_enabled': profit_prot.get('enabled', True),
                    'profit_consecutive_wins': profit_prot.get('consecutive_wins', 3),
                    'profit_cooldown_minutes': profit_prot.get('cooldown_minutes', 20),
                    'signal_ttl_minutes': signal_ttl.get('ttl_minutes', 30),
                    'signal_auto_requery': signal_ttl.get('auto_requery_on_expire', True),
                    'adaptive_lot_enabled': v5.get('enabled', True),
                    'adaptive_lot_base': v5.get('base_lot', 0.01),
                    'adaptive_lot_max': v5.get('max_lot', 0.05),
                    'adaptive_lot_lookback': v5.get('lookback_trades', 10),
                    # Trade Filters (NEW)
                    'filter_enabled': filters.get('enabled', True),
                    'filter_min_confidence': filters.get('min_confidence', 75),
                    'filter_min_setup_score': filters.get('min_setup_score', 70),
                    'filter_min_rr': filters.get('min_rr', 1.2),
                    'filter_max_spread_pips': filters.get('max_spread_pips', 3.0),
                    'filter_daily_limit': filters.get('daily_limit', 6),
                    'filter_cooldown_win': filters.get('cooldown_after_win', 15),
                    'filter_cooldown_loss': filters.get('cooldown_after_loss', 90),
                    'filter_cooldown_2losses': filters.get('cooldown_after_2_losses', 240),
                    'filter_htf_timeframe': filters.get('htf_timeframe', 'M15'),
                    'filter_htf_ema_fast': filters.get('htf_ema_fast', 50),
                    'filter_htf_ema_slow': filters.get('htf_ema_slow', 200),
                }
                
                for key, value in mapping.items():
                    if key in self.vars:
                        self.vars[key].set(value)
            
            # AI config
            ai_path = Path('config/ai.yaml')
            if ai_path.exists():
                with open(ai_path, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f) or {}
                
                gpt = ai_config.get('market_analyst', {}).get('gpt', {})
                schedule = ai_config.get('market_analyst', {}).get('schedule', {})
                restrictions = schedule.get('restrictions', {})
                
                mapping = {
                    'ai_enabled': ai_config.get('ai_enabled', True),
                    'ai_model': gpt.get('model', 'gpt-4o'),
                    'ai_temperature': gpt.get('temperature', 0.3),
                    # ai_min_confidence removed - use filter_min_confidence instead
                    'ai_interval_minutes': schedule.get('interval_minutes', 60),
                    'night_block_enabled': restrictions.get('night_block', {}).get('enabled', False),
                    'weekend_block_enabled': restrictions.get('weekend_block', {}).get('enabled', True),
                }
                
                for key, value in mapping.items():
                    if key in self.vars:
                        try:
                            self.vars[key].set(value)
                        except:
                            pass
        
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to load configs: {e}")
    
    def _save(self):
        """Сохранить настройки"""
        try:
            data = {}
            for key, var in self.vars.items():
                try:
                    data[key] = var.get()
                except:
                    data[key] = CONFIG_SCHEMA[key]["default"]
            
            # Log trading_enabled value
            logger.info(f"[SETTINGS] Saving trading_enabled: {data.get('trading_enabled', None)}")
            
            # Сохранить в YAML файлы
            self._save_to_yaml(data)
            
            if self.on_save:
                self.on_save(data)
            
            messagebox.showinfo("Success", "Settings saved successfully!", parent=self)
            self._close()
        
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{e}", parent=self)
    
    def _save_to_yaml(self, data):
        """Записать в YAML файлы"""
        try:
            # Trading config
            trading_path = Path('config/trading.yaml')
            if trading_path.exists():
                with open(trading_path, 'r', encoding='utf-8') as f:
                    trading_config = yaml.safe_load(f) or {}
            else:
                trading_config = {'trading': {}}
            
            trading = trading_config.setdefault('trading', {})
            risk = trading.setdefault('risk', {})
            trailing = trading.setdefault('trailing_stop', {})
            stop_prot = trading.setdefault('stop_loss_protection', {})
            profit_prot = trading.setdefault('profit_protection', {})
            signal_ttl = trading.setdefault('signal_ttl', {})
            v5 = trading.setdefault('v5_improvements', {}).setdefault('adaptive_lot', {})
            filters = trading.setdefault('filters', {})  # NEW: Trade Filters
            
            # Update values
            trading['enabled'] = data.get('trading_enabled', True)
            trading['dry_run'] = data.get('dry_run_mode', False)  # QA/Testing mode
            trading['mode'] = data.get('trading_mode', 'manual')  # Trading mode: auto, semi-auto, manual
            risk['fixed_lot_size'] = data.get('fixed_lot_size', 0.01)
            risk['default_sl_pips'] = data.get('default_sl_pips', 40)
            risk['default_tp_pips'] = data.get('default_tp_pips', 100)
            # max_spread_pips removed - use filter_max_spread_pips instead
            
            trailing['enabled'] = data.get('trailing_enabled', True)
            trailing['activation_profit_percent'] = data.get('trailing_activation_percent', 30)
            trailing['trailing_step_percent'] = data.get('trailing_step_percent', 10)
            
            stop_prot['enabled'] = data.get('stop_protection_enabled', True)
            stop_prot['consecutive_stops'] = data.get('stop_consecutive_stops', 2)
            stop_prot['cooldown_minutes'] = data.get('stop_cooldown_minutes', 10)
            
            profit_prot['enabled'] = data.get('profit_protection_enabled', True)
            profit_prot['consecutive_wins'] = data.get('profit_consecutive_wins', 3)
            profit_prot['cooldown_minutes'] = data.get('profit_cooldown_minutes', 20)
            
            signal_ttl['ttl_minutes'] = data.get('signal_ttl_minutes', 30)
            signal_ttl['auto_requery_on_expire'] = data.get('signal_auto_requery', True)
            
            v5['enabled'] = data.get('adaptive_lot_enabled', True)
            v5['base_lot'] = data.get('adaptive_lot_base', 0.01)
            v5['max_lot'] = data.get('adaptive_lot_max', 0.05)
            v5['lookback_trades'] = data.get('adaptive_lot_lookback', 10)
            
            # Trade Filters (NEW)
            filters['enabled'] = data.get('filter_enabled', True)
            filters['min_confidence'] = data.get('filter_min_confidence', 75)
            filters['min_setup_score'] = data.get('filter_min_setup_score', 70)
            filters['min_rr'] = data.get('filter_min_rr', 1.2)
            filters['max_spread_pips'] = data.get('filter_max_spread_pips', 3.0)
            filters['daily_limit'] = data.get('filter_daily_limit', 6)
            filters['cooldown_after_win'] = data.get('filter_cooldown_win', 15)
            filters['cooldown_after_loss'] = data.get('filter_cooldown_loss', 90)
            filters['cooldown_after_2_losses'] = data.get('filter_cooldown_2losses', 240)
            filters['htf_timeframe'] = data.get('filter_htf_timeframe', 'M15')
            filters['htf_ema_fast'] = data.get('filter_htf_ema_fast', 50)
            filters['htf_ema_slow'] = data.get('filter_htf_ema_slow', 200)
            
            with open(trading_path, 'w', encoding='utf-8') as f:
                yaml.dump(trading_config, f, default_flow_style=False, allow_unicode=True)
            
            # AI config
            ai_path = Path('config/ai.yaml')
            if ai_path.exists():
                with open(ai_path, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f) or {}
            else:
                ai_config = {}
            
            ai_config['ai_enabled'] = data.get('ai_enabled', True)
            
            gpt = ai_config.setdefault('market_analyst', {}).setdefault('gpt', {})
            gpt['model'] = data.get('ai_model', 'gpt-4o')
            gpt['temperature'] = data.get('ai_temperature', 0.3)
            
            schedule = ai_config.setdefault('market_analyst', {}).setdefault('schedule', {})
            schedule['interval_minutes'] = data.get('ai_interval_minutes', 60)
            
            restrictions = schedule.setdefault('restrictions', {})
            restrictions.setdefault('night_block', {})['enabled'] = data.get('night_block_enabled', False)
            restrictions.setdefault('weekend_block', {})['enabled'] = data.get('weekend_block_enabled', True)
            
            with open(ai_path, 'w', encoding='utf-8') as f:
                yaml.dump(ai_config, f, default_flow_style=False, allow_unicode=True)
            
            # GPT API Key to .env
            if hasattr(self, 'gpt_api_key_var'):
                api_key = self.gpt_api_key_var.get().strip()
                if api_key:
                    env_path = Path('.env')
                    env_lines = []
                    if env_path.exists():
                        with open(env_path, 'r', encoding='utf-8') as f:
                            env_lines = f.readlines()
                    
                    updated = False
                    for i, line in enumerate(env_lines):
                        if line.startswith('OPENAI_API_KEY='):
                            env_lines[i] = f'OPENAI_API_KEY={api_key}\n'
                            updated = True
                            break
                    
                    if not updated:
                        env_lines.append(f'OPENAI_API_KEY={api_key}\n')
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.writelines(env_lines)
                    os.environ['OPENAI_API_KEY'] = api_key
                    logger.info(f"[SETTINGS] GPT API key saved to .env")
            
            # Telegram settings
            if hasattr(self, 'telegram_token_var'):
                telegram_path = Path('config/telegram.yaml')
                if telegram_path.exists():
                    with open(telegram_path, 'r', encoding='utf-8') as f:
                        telegram_config = yaml.safe_load(f) or {}
                else:
                    telegram_config = {}
                
                telegram = telegram_config.setdefault('telegram', {})
                telegram['bot_token'] = self.telegram_token_var.get().strip()
                telegram['chat_id'] = self.telegram_chat_id_var.get().strip()
                
                with open(telegram_path, 'w', encoding='utf-8') as f:
                    yaml.dump(telegram_config, f, default_flow_style=False, allow_unicode=True)
                logger.info(f"[SETTINGS] Telegram settings saved")
            
            logger.info("[SETTINGS] ✅ Configs saved to YAML files")
            
            # Reload configs through ConfigManager to apply changes
            try:
                config_manager = get_config_manager()
                reload_results = config_manager.reload_all()
                logger.info(f"[SETTINGS] ✅ Configs reloaded successfully: {reload_results}")
            except Exception as reload_err:
                logger.error(f"[SETTINGS] Failed to reload configs: {reload_err}")
        
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save to YAML: {e}")
            raise
    
    def _reset_defaults(self):
        """Сбросить к дефолтам"""
        if messagebox.askyesno("Reset Defaults", 
                              "Reset all settings to default values?", 
                              parent=self):
            for key, meta in CONFIG_SCHEMA.items():
                if key in self.vars:
                    self.vars[key].set(meta["default"])
    
    def _create_gpt_api_tab(self, notebook):
        """Создать вкладку GPT API Settings"""
        frame = tk.Frame(notebook, bg=Colors.BG_DARK)
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Info
        info = tk.Label(content, text="ℹ️ Get your API key from: https://platform.openai.com/api-keys",
                       font=('Arial', 9), bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
                       wraplength=500, pady=10)
        info.pack(fill='x', padx=15, pady=10)
        
        # API Key
        self.gpt_api_key_var = tk.StringVar()
        try:
            env_path = Path('.env')
            if env_path.exists() and load_dotenv:
                load_dotenv(env_path)
                key = os.getenv('OPENAI_API_KEY', '')
                if key:
                    self.gpt_api_key_var.set(key)
        except:
            pass
        
        row = tk.Frame(content, bg=Colors.BG_DARK)
        row.pack(fill='x', padx=15, pady=5)
        tk.Label(row, text="API Key:", font=('Arial', 10), bg=Colors.BG_DARK, fg=Colors.TEXT_SECONDARY, width=15, anchor='w').pack(side='left')
        key_entry = tk.Entry(row, textvariable=self.gpt_api_key_var, font=('Arial', 10), width=40, show='*')
        key_entry.pack(side='left', padx=5)
        
        # TEST button
        test_status = tk.Label(content, text="", font=('Arial', 9), bg=Colors.BG_DARK, fg=Colors.TEXT_SECONDARY)
        test_status.pack(padx=15, pady=5)
        
        def test_connection():
            key = self.gpt_api_key_var.get().strip()
            if not key:
                messagebox.showerror("Error", "Please enter API Key!")
                return
            test_status.config(text="⏳ Testing...", fg=Colors.WARNING)
            
            def run():
                try:
                    if not openai:
                        raise ImportError("openai library not installed")
                    client = openai.OpenAI(api_key=key)
                    start = time.time()
                    client.chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':'ping'}], max_tokens=5)
                    latency = int((time.time()-start)*1000)
                    self.after(0, lambda: [test_status.config(text=f"✅ API OK ({latency}ms)", fg=Colors.SUCCESS),
                                          messagebox.showinfo("Success", f"GPT API works!\nLatency: {latency}ms")])
                except Exception as e:
                    self.after(0, lambda: [test_status.config(text=f"❌ {str(e)[:40]}", fg=Colors.ERROR),
                                          messagebox.showerror("Failed", f"Error:\n{e}")])
            threading.Thread(target=run, daemon=True).start()
        
        tk.Button(content, text="🔌 TEST CONNECTION", font=('Arial', 10, 'bold'), bg=Colors.ACCENT, fg='white',
                 relief='flat', padx=15, pady=8, command=test_connection).pack(pady=10)
        
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        notebook.add(frame, text='🔑 GPT API')
    
    def _create_telegram_tab(self, notebook):
        """Создать вкладку Telegram Settings"""
        frame = tk.Frame(notebook, bg=Colors.BG_DARK)
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Load telegram config
        telegram_config = {}
        try:
            tel_path = Path('config/telegram.yaml')
            if tel_path.exists():
                with open(tel_path, 'r', encoding='utf-8') as f:
                    telegram_config = yaml.safe_load(f) or {}
        except:
            pass
        tel_settings = telegram_config.get('telegram', {})
        
        # Info
        info = tk.Label(content, text="ℹ️ Get Chat ID from @userinfobot",
                       font=('Arial', 9), bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
                       wraplength=500, pady=10)
        info.pack(fill='x', padx=15, pady=10)
        
        # Bot Token
        self.telegram_token_var = tk.StringVar(value=tel_settings.get('bot_token', ''))
        row = tk.Frame(content, bg=Colors.BG_DARK)
        row.pack(fill='x', padx=15, pady=5)
        tk.Label(row, text="Bot Token:", font=('Arial', 10), bg=Colors.BG_DARK, fg=Colors.TEXT_SECONDARY, width=15, anchor='w').pack(side='left')
        tk.Entry(row, textvariable=self.telegram_token_var, font=('Arial', 10), width=40, show='*').pack(side='left', padx=5)
        
        # Chat ID
        self.telegram_chat_id_var = tk.StringVar(value=tel_settings.get('chat_id', ''))
        row = tk.Frame(content, bg=Colors.BG_DARK)
        row.pack(fill='x', padx=15, pady=5)
        tk.Label(row, text="Chat ID:", font=('Arial', 10), bg=Colors.BG_DARK, fg=Colors.TEXT_SECONDARY, width=15, anchor='w').pack(side='left')
        tk.Entry(row, textvariable=self.telegram_chat_id_var, font=('Arial', 10), width=40).pack(side='left', padx=5)
        
        # TEST button
        test_status = tk.Label(content, text="", font=('Arial', 9), bg=Colors.BG_DARK, fg=Colors.TEXT_SECONDARY)
        test_status.pack(padx=15, pady=5)
        
        def test_bot():
            token = self.telegram_token_var.get().strip()
            chat_id = self.telegram_chat_id_var.get().strip()
            if not token or not chat_id:
                messagebox.showerror("Error", "Enter Bot Token and Chat ID!")
                return
            test_status.config(text="⏳ Testing...", fg=Colors.WARNING)
            
            def run():
                try:
                    me_url = f"https://api.telegram.org/bot{token}/getMe"
                    me_resp = requests.get(me_url, timeout=10).json()
                    if not me_resp.get('ok'):
                        raise Exception(me_resp.get('description', 'Invalid token'))
                    bot_name = me_resp['result'].get('username', 'Unknown')
                    
                    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                    requests.post(send_url, json={'chat_id': chat_id, 'text': f'✅ BAZA Bot test OK!\nBot: @{bot_name}'}, timeout=10)
                    
                    self.after(0, lambda: [test_status.config(text=f"✅ Bot OK (@{bot_name})", fg=Colors.SUCCESS),
                                          messagebox.showinfo("Success", f"Telegram works!\nBot: @{bot_name}\nChat ID: {chat_id}")])
                except Exception as e:
                    self.after(0, lambda: [test_status.config(text=f"❌ {str(e)[:40]}", fg=Colors.ERROR),
                                          messagebox.showerror("Failed", f"Error:\n{e}")])
            threading.Thread(target=run, daemon=True).start()
        
        tk.Button(content, text="🤖 TEST BOT", font=('Arial', 10, 'bold'), bg=Colors.ACCENT, fg='white',
                 relief='flat', padx=15, pady=8, command=test_bot).pack(pady=10)
        
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        notebook.add(frame, text='📱 Telegram')
    
    def _cancel(self):
        """Отменить"""
        self._close()
    
    def _close(self):
        """Закрыть окно"""
        try:
            self.grab_release()
        except:
            pass
        self.destroy()


# ==================== MT5 SETTINGS DIALOG ====================
class MT5SettingsDialog(tk.Toplevel):
    """Окно настроек MT5 с Test Connection и Save без перезапуска"""
    
    def __init__(self, parent, mt5_manager=None, status_bar=None, title="MT5 Settings"):
        super().__init__(parent)
        self.parent = parent
        self.mt5_manager = mt5_manager
        self.status_bar = status_bar
        self.testing = False  # Flag для предотвращения множественных тестов
        
        self.title(title)
        self.configure(bg=Colors.BG_DARK)
        self.resizable(False, False)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        
        # Центрирование
        self.update_idletasks()
        w, h = 520, 600  # Увеличена высота для кнопок
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self._build_ui()
        self._load_config()
    
    def _build_ui(self):
        """Построить UI"""
        # Header
        header = tk.Frame(self, bg=Colors.BG_PANEL, height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🔧 MT5 Settings",
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.TEXT_PRIMARY).pack(side='left', padx=20, pady=15)
        
        # Separator
        tk.Frame(self, bg=Colors.BORDER, height=1).pack(fill='x')
        
        # Content
        content = tk.Frame(self, bg=Colors.BG_DARK)
        content.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Login
        self._create_row(content, "Login:", is_first=True)
        self.login_var = tk.StringVar()
        tk.Entry(content, textvariable=self.login_var,
                font=('Arial', 10),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY,
                insertbackground=Colors.TEXT_PRIMARY,
                relief='flat',
                highlightthickness=1,
                highlightbackground=Colors.BORDER,
                highlightcolor=Colors.ACCENT).pack(fill='x', pady=(5, 15))
        
        # Password
        self._create_row(content, "Password:")
        password_frame = tk.Frame(content, bg=Colors.BG_DARK)
        password_frame.pack(fill='x', pady=(5, 15))
        
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(password_frame, textvariable=self.password_var,
                font=('Arial', 10),
                show='●',  # Маскировка пароля
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY,
                insertbackground=Colors.TEXT_PRIMARY,
                relief='flat',
                highlightthickness=1,
                highlightbackground=Colors.BORDER,
                highlightcolor=Colors.ACCENT)
        self.password_entry.pack(side='left', fill='x', expand=True)
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar(value=False)
        tk.Checkbutton(password_frame, text="Show",
                      variable=self.show_password_var,
                      command=self._toggle_password,
                      bg=Colors.BG_DARK,
                      fg=Colors.TEXT_SECONDARY,
                      selectcolor=Colors.BG_CARD,
                      activebackground=Colors.BG_DARK,
                      activeforeground=Colors.TEXT_PRIMARY,
                      font=('Arial', 8)).pack(side='right', padx=(8, 0))
        
        # Server
        self._create_row(content, "Server:")
        self.server_var = tk.StringVar()
        tk.Entry(content, textvariable=self.server_var,
                font=('Arial', 10),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY,
                insertbackground=Colors.TEXT_PRIMARY,
                relief='flat',
                highlightthickness=1,
                highlightbackground=Colors.BORDER,
                highlightcolor=Colors.ACCENT).pack(fill='x', pady=(5, 15))
        
        # Path (optional)
        self._create_row(content, "Terminal Path (optional):")
        self.path_var = tk.StringVar()
        tk.Entry(content, textvariable=self.path_var,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                insertbackground=Colors.TEXT_PRIMARY,
                relief='flat',
                highlightthickness=1,
                highlightbackground=Colors.BORDER,
                highlightcolor=Colors.ACCENT).pack(fill='x', pady=(5, 20))
        
        # Status Bar (зелёный/красный)
        status_container = tk.Frame(self, bg=Colors.BG_CARD, height=50)
        status_container.pack(fill='x', padx=30, pady=(0, 15))
        status_container.pack_propagate(False)
        
        self.status_label = tk.Label(status_container, text="Status: Ready",
                                     font=('Arial', 9),
                                     bg=Colors.BG_CARD,
                                     fg=Colors.TEXT_SECONDARY,
                                     anchor='w',
                                     justify='left',
                                     wraplength=450)
        self.status_label.pack(fill='both', padx=15, pady=10)
        
        # Buttons
        btns = tk.Frame(self, bg=Colors.BG_DARK)
        btns.pack(fill='x', padx=30, pady=(0, 30))
        
        # Left: Test Connection
        tk.Button(btns, text="Test Connection",
                 font=('Arial', 10),
                 bg=Colors.ACCENT,
                 fg='white',
                 activebackground='#1f6feb',
                 relief='flat',
                 padx=15, pady=8,
                 command=self._test_connection).pack(side='left')
        
        # Right: Cancel + Save
        tk.Button(btns, text="Cancel",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 padx=15, pady=8,
                 command=self._cancel).pack(side='right')
        
        tk.Button(btns, text="Save",
                 font=('Arial', 10, 'bold'),
                 bg=Colors.SUCCESS,
                 fg='white',
                 activebackground='#2ea043',
                 relief='flat',
                 padx=20, pady=8,
                 command=self._save).pack(side='right', padx=(0, 8))
    
    def _toggle_password(self):
        """Toggle password visibility"""
        if self.show_password_var.get():
            self.password_entry.config(show='')
        else:
            self.password_entry.config(show='●')
    
    def _create_row(self, parent, text, is_first=False):
        """Создать строку с label"""
        tk.Label(parent, text=text,
                font=('Arial', 9, 'bold' if is_first else 'normal'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY,
                anchor='w').pack(fill='x')
    
    def _load_config(self):
        """Загрузить конфиг MT5"""
        try:
            # Сначала .env
            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('MT5_LOGIN='):
                            self.login_var.set(line.split('=', 1)[1])
                        elif line.startswith('MT5_PASSWORD='):
                            self.password_var.set(line.split('=', 1)[1])
                        elif line.startswith('MT5_SERVER='):
                            self.server_var.set(line.split('=', 1)[1])
            
            # Потом mt5.yaml (приоритет)
            mt5_path = Path('config/mt5.yaml')
            if mt5_path.exists():
                with open(mt5_path, 'r', encoding='utf-8') as f:
                    mt5_config = yaml.safe_load(f) or {}
                
                conn = mt5_config.get('mt5', {}).get('connection', {})
                if conn.get('login'):
                    self.login_var.set(str(conn['login']))
                if conn.get('password'):
                    self.password_var.set(conn['password'])
                if conn.get('server'):
                    self.server_var.set(conn['server'])
                if conn.get('path'):
                    self.path_var.set(conn['path'])
        
        except Exception as e:
            logger.error(f"[MT5 SETTINGS] Failed to load config: {e}")
            self._update_status(False, f"Failed to load config: {e}")
    
    def _update_status(self, success: bool, message: str):
        """Обновить статус бар (зелёный/красный)"""
        if success:
            self.status_label.configure(
                text=f"✅ {message}",
                fg=Colors.SUCCESS
            )
        else:
            self.status_label.configure(
                text=f"❌ {message}",
                fg=Colors.ERROR
            )
    
    def _test_connection(self):
        """Тест подключения к MT5 в отдельном потоке"""
        if self.testing:
            self._update_status(False, "Test already in progress...")
            return
        
        login = self.login_var.get().strip()
        password = self.password_var.get().strip()
        server = self.server_var.get().strip()
        path = self.path_var.get().strip()
        
        if not login or not password or not server:
            self._update_status(False, "Please fill Login, Password and Server fields")
            return
        
        # Показать статус "Testing..."
        self.status_label.configure(text="🔄 Testing connection...", fg=Colors.TEXT_PRIMARY)
        self.testing = True
        
        # Запуск в отдельном потоке
        import threading
        thread = threading.Thread(target=self._test_connection_thread, 
                                  args=(login, password, server, path),
                                  daemon=True)
        thread.start()
    
    def _test_connection_thread(self, login: str, password: str, server: str, path: str):
        """Worker thread для Test Connection"""
        try:
            if self.mt5_manager:
                # Используем mt5_manager.test_connection()
                success, message, account_info = self.mt5_manager.test_connection(
                    login=int(login) if login.isdigit() else login,
                    password=password,
                    server=server,
                    terminal_path=path if path else None
                )
            else:
                # Fallback: прямое тестирование через MetaTrader5
                success, message, account_info = self._direct_test_connection(login, password, server, path)
            
            # Обновить UI в главном потоке
            self.after(0, self._test_connection_complete, success, message)
            
        except Exception as e:
            logger.error(f"[MT5 SETTINGS] Test connection error: {e}")
            self.after(0, self._test_connection_complete, False, f"Error: {str(e)}")
    
    def _direct_test_connection(self, login: str, password: str, server: str, path: str):
        """Direct test connection (fallback если нет mt5_manager)"""
        try:
            import MetaTrader5 as mt5
            
            # Initialize
            if path and Path(path).exists():
                if not mt5.initialize(path):
                    error = mt5.last_error()
                    return False, f"Failed to initialize MT5: {error}", None
            else:
                if not mt5.initialize():
                    error = mt5.last_error()
                    return False, f"Failed to initialize MT5: {error}", None
            
            # Login
            login_int = int(login) if login.isdigit() else 0
            authorized = mt5.login(login_int, password=password, server=server)
            
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                return False, f"Authorization failed: {error}", None
            
            # Get account info
            account = mt5.account_info()
            if not account:
                mt5.shutdown()
                return False, "Failed to get account info", None
            
            account_dict = {
                'login': account.login,
                'name': account.name,
                'server': account.server,
                'balance': account.balance,
                'currency': account.currency
            }
            
            mt5.shutdown()
            
            message = f"Connected!\n Account: {account.login} | Balance: ${account.balance:.2f}"
            return True, message, account_dict
            
        except Exception as e:
            return False, f"Test failed: {str(e)}", None
    
    def _test_connection_complete(self, success: bool, message: str):
        """Callback после завершения теста (в главном потоке)"""
        self.testing = False
        self._update_status(success, message)
    
    def _save(self):
        """Сохранить настройки MT5 и применить без перезапуска"""
        try:
            login = self.login_var.get().strip()
            password = self.password_var.get().strip()
            server = self.server_var.get().strip()
            path = self.path_var.get().strip()
            
            if not login or not password or not server:
                self._update_status(False, "Login, Password and Server are required!")
                return
            
            # Сохранить в mt5.yaml
            mt5_path = Path('config/mt5.yaml')
            mt5_config = {
                'mt5': {
                    'connection': {
                        'login': int(login) if login.isdigit() else login,
                        'password': password,
                        'server': server,
                        'path': path or "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                        'timeout': 60000
                    }
                }
            }
            
            mt5_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mt5_path, 'w', encoding='utf-8') as f:
                yaml.dump(mt5_config, f, default_flow_style=False, allow_unicode=True)
            
            # Также обновить .env (для совместимости)
            env_path = Path('.env')
            lines = []
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            # Заменить или добавить
            found = {'login': False, 'password': False, 'server': False}
            for i, line in enumerate(lines):
                if line.startswith('MT5_LOGIN='):
                    lines[i] = f'MT5_LOGIN={login}\n'
                    found['login'] = True
                elif line.startswith('MT5_PASSWORD='):
                    lines[i] = f'MT5_PASSWORD={password}\n'
                    found['password'] = True
                elif line.startswith('MT5_SERVER='):
                    lines[i] = f'MT5_SERVER={server}\n'
                    found['server'] = True
            
            if not found['login']:
                lines.append(f'MT5_LOGIN={login}\n')
            if not found['password']:
                lines.append(f'MT5_PASSWORD={password}\n')
            if not found['server']:
                lines.append(f'MT5_SERVER={server}\n')
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info("[MT5 SETTINGS] ✅ MT5 config saved to mt5.yaml and .env")
            
            # Применить настройки через mt5_manager (без перезапуска)
            if self.mt5_manager:
                self._update_status(True, "Applying settings...")
                
                # Применить в отдельном потоке
                import threading
                thread = threading.Thread(target=self._apply_settings_thread, 
                                         args=(login, password, server, path),
                                         daemon=True)
                thread.start()
            else:
                self._update_status(True, "Settings saved! (Restart required)")
                messagebox.showinfo("Success", "MT5 settings saved!\nRestart bot to apply.", parent=self)
                self._close()
        
        except Exception as e:
            logger.error(f"[MT5 SETTINGS] Failed to save: {e}")
            self._update_status(False, f"Failed to save: {e}")
    
    def _apply_settings_thread(self, login: str, password: str, server: str, path: str):
        """Worker thread для применения настроек"""
        try:
            success, message = self.mt5_manager.apply_settings(
                login=int(login) if login.isdigit() else login,
                password=password,
                server=server,
                terminal_path=path if path else None
            )
            
            # Обновить UI в главном потоке
            self.after(0, self._apply_settings_complete, success, message)
            
        except Exception as e:
            logger.error(f"[MT5 SETTINGS] Apply settings error: {e}")
            self.after(0, self._apply_settings_complete, False, f"Error: {str(e)}")
    
    def _apply_settings_complete(self, success: bool, message: str):
        """Callback после применения настроек (в главном потоке)"""
        self._update_status(success, message)
        
        # Обновить status_bar если доступен
        if self.status_bar and self.mt5_manager:
            is_connected = self.mt5_manager.is_connected()
            self.status_bar.update_mt5_status(is_connected)
        
        if success:
            logger.info(f"[MT5 SETTINGS] {message}")
            messagebox.showinfo("Success", "MT5 settings saved and applied successfully!", parent=self)
            self.after(500, self._close)  # Close after 500ms
        else:
            messagebox.showwarning("Partial Success", 
                                  f"Settings saved but failed to apply:\n{message}\n\nYou may need to restart the bot.",
                                  parent=self)
    
    def _cancel(self):
        """Отменить"""
        self._close()
    
    def _close(self):
        """Закрыть окно"""
        try:
            self.grab_release()
        except:
            pass
        self.destroy()


# ==================== EFFECTIVE CONFIG DIALOG ====================

class EffectiveConfigDialog(tk.Toplevel):
    """
    Диалог для отображения эффективной конфигурации
    Показывает какие значения используются ботом прямо сейчас
    """
    
    def __init__(self, parent, title="🔍 Effective Configuration"):
        super().__init__(parent)
        self.title(title)
        self.geometry("950x750")
        self.resizable(True, True)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (950 // 2)
        y = (self.winfo_screenheight() // 2) - (750 // 2)
        self.geometry(f"950x750+{x}+{y}")
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        self.config_manager = get_config_manager()
        
        # Search state
        self.search_timer = None
        self.match_items = []
        self.current_match_index = 0
        
        self._create_widgets()
        self._load_effective_config()
    
    def _detect_conflicts(self, configs: Dict) -> List[Dict]:
        """
        Detect parameter conflicts across config files.
        
        ✅ AFTER REFACTORING (Feb 2026):
        All trade filter parameters moved to trading.yaml (single source of truth).
        No conflicts should exist anymore.
        
        This method is preserved for future use if new parameters are added
        to multiple config files.
        
        Returns:
            List of conflict dicts (should be empty list now): {
                'param': 'parameter_name',
                'sources': [
                    {'file': 'file1.yaml', 'path': 'section.param', 'value': 75},
                    {'file': 'file2.yaml', 'path': 'other.param', 'value': 50}
                ],
                'winner': 'file1.yaml',
                'reason': 'Component X reads from file1.yaml'
            }
        """
        conflicts = []
        
        # ✅ Conflict map is NOW EMPTY after refactoring
        # All filter parameters (min_confidence, max_spread_pips, daily_limit, etc.)
        # are in trading.yaml ONLY
        #
        # If new conflicts are introduced in the future, add them here:
        conflict_map = {
            # Example (not currently used):
            # 'some_param': {
            #     'sources': [
            #         ('config1.yaml', ['section', 'param']),
            #         ('config2.yaml', ['other', 'param'])
            #     ],
            #     'winner': 'config1.yaml',
            #     'reason': 'ComponentX reads from config1.yaml'
            # },
        }
        
        # Check each potential conflict
        for param_name, conflict_info in conflict_map.items():
            sources_found = []
            
            for config_file, path in conflict_info['sources']:
                # Navigate to value
                value = configs.get(config_file, {})
                for key in path:
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        value = None
                        break
                
                if value is not None:
                    sources_found.append({
                        'file': config_file,
                        'path': '.'.join(path),
                        'value': value
                    })
            
            # If found in multiple sources with different values -> conflict!
            if len(sources_found) > 1:
                values = [s['value'] for s in sources_found]
                if len(set(str(v) for v in values)) > 1:  # Different values
                    conflicts.append({
                        'param': param_name,
                        'sources': sources_found,
                        'winner': conflict_info['winner'],
                        'reason': conflict_info['reason']
                    })
        
        return conflicts
    
    def _create_widgets(self):
        """Создать UI элементы"""
        
        # Top frame with title and refresh button
        top_frame = ttk.Frame(self)
        top_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(top_frame, text="Current Runtime Configuration", 
                 font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        ttk.Button(top_frame, text="🔄 Refresh", 
                  command=self._load_effective_config).pack(side='right')
        
        # Info label
        info_text = ("These are the actual values the bot is using right now.\n"
                    "If they don't match GUI settings, config reload may have failed.")
        ttk.Label(self, text=info_text, foreground='gray', 
                 font=('Segoe UI', 9)).pack(padx=10, pady=(0, 10))
        
        # Timestamp label
        self.timestamp_label = ttk.Label(self, text="Last loaded: N/A", 
                                        foreground='#666', font=('Segoe UI', 8))
        self.timestamp_label.pack(padx=10, pady=(0, 10))
        
        # Search frame
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Label(search_frame, text="🔍 Search:").pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_changed)
        
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side='left', fill='x', expand=True)
        
        # Placeholder text
        self.search_entry.insert(0, "Type to search keys and values...")
        self.search_entry.config(foreground='gray')
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_search_focus_out)
        
        # Result counter
        self.result_counter = ttk.Label(search_frame, text="", foreground='gray', width=12)
        self.result_counter.pack(side='left', padx=(5, 0))
        
        # Navigation buttons
        ttk.Button(search_frame, text="↑", width=3,
                  command=self._prev_match).pack(side='left', padx=(2, 0))
        ttk.Button(search_frame, text="↓", width=3,
                  command=self._next_match).pack(side='left', padx=(2, 0))
        
        ttk.Button(search_frame, text="✖ Clear", 
                  command=self._clear_search).pack(side='left', padx=(5, 0))
        
        # Treeview with scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                columns=('value', 'type'),
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Column headers
        self.tree.heading('#0', text='Config Key')
        self.tree.heading('value', text='Value')
        self.tree.heading('type', text='Type')
        
        # Column widths
        self.tree.column('#0', width=400, minwidth=200)
        self.tree.column('value', width=300, minwidth=150)
        self.tree.column('type', width=100, minwidth=80)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bottom buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="📋 Copy All", 
                  command=self._copy_all_to_clipboard).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="💾 Export to File", 
                  command=self._export_to_file).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="✖ Close", 
                  command=self._close).pack(side='right', padx=5)
    
    def _load_effective_config(self):
        """Загрузить эффективную конфигурацию из ConfigManager"""
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            effective = self.config_manager.get_effective_config()
            
            # Extract timestamp and configs
            timestamp = effective.get('timestamp', 'N/A')
            configs = effective.get('configs', {})
            
            # Update timestamp label
            if hasattr(self, 'timestamp_label'):
                self.timestamp_label.config(text=f"Last loaded: {timestamp}")
            
            # ==== CONFLICTS SECTION ====
            conflicts = self._detect_conflicts(configs)
            
            if conflicts:
                # Add conflicts section at the top
                conflicts_node = self.tree.insert('', 0, text=f"⚠️ CONFLICTS DETECTED ({len(conflicts)})", 
                                                 values=('', 'conflicts'), tags=('conflicts',))
                
                for conflict in conflicts:
                    param_name = conflict['param']
                    sources = conflict['sources']
                    winner = conflict['winner']
                    reason = conflict['reason']
                    
                    # Conflict node
                    conflict_node = self.tree.insert(conflicts_node, 'end', 
                                                    text=f"🔴 {param_name}", 
                                                    values=('Multiple definitions', 'conflict'), 
                                                    tags=('conflict',))
                    
                    # Sources
                    for source in sources:
                        file = source['file']
                        path = source['path']
                        value = source['value']
                        
                        is_winner = (file == winner)
                        icon = "✅" if is_winner else "❌"
                        tag = 'winner' if is_winner else 'loser'
                        
                        self.tree.insert(conflict_node, 'end', 
                                       text=f"{icon} {file}: {path}", 
                                       values=(str(value), f"{'ACTIVE' if is_winner else 'IGNORED'}"),
                                       tags=(tag,))
                    
                    # Winner reason
                    self.tree.insert(conflict_node, 'end', 
                                   text=f"📌 Winner: {winner}", 
                                   values=(reason, 'info'), 
                                   tags=('winner_reason',))
            
            # ==== BUILD CONFIG TREE ====
            for config_name, sections in sorted(configs.items()):
                # Root node for config file
                config_node = self.tree.insert('', 'end', text=f"📄 {config_name}", 
                                              values=('', 'config'), tags=('config',))
                
                # Sections
                if isinstance(sections, dict):
                    for section_name, keys in sorted(sections.items()):
                        section_node = self.tree.insert(config_node, 'end', 
                                                       text=f"📁 {section_name}", 
                                                       values=('', 'section'), 
                                                       tags=('section',))
                        
                        # Keys
                        if isinstance(keys, dict):
                            self._add_dict_items(section_node, keys)
                        else:
                            # Section is not a dict, show value directly
                            self.tree.item(section_node, values=(str(keys), type(keys).__name__))
                else:
                    # Config is not a dict (e.g., empty or error), show error
                    self.tree.item(config_node, values=(str(sections), type(sections).__name__))
            
            # Expand all by default
            self._expand_all()
            
            # Tag styling
            self.tree.tag_configure('config', font=('Segoe UI', 10, 'bold'))
            self.tree.tag_configure('section', font=('Segoe UI', 9, 'bold'), foreground='#0066cc')
            self.tree.tag_configure('conflicts', font=('Segoe UI', 10, 'bold'), foreground='#ff6600', background='#fff3cd')
            self.tree.tag_configure('conflict', font=('Segoe UI', 9, 'bold'), foreground='#cc0000')
            self.tree.tag_configure('winner', foreground='#008800', font=('Segoe UI', 9, 'bold'))
            self.tree.tag_configure('loser', foreground='#888888', font=('Segoe UI', 9))
            self.tree.tag_configure('winner_reason', foreground='#0066cc', font=('Segoe UI', 8, 'italic'))
            
            # Search highlighting
            self.tree.tag_configure('match', background='#ffffcc')  # Soft yellow
            self.tree.tag_configure('current_match', background='#ffd700')  # Gold
            
            # Type-based coloring
            self.tree.tag_configure('type_bool', foreground='#3fb950')  # Green
            self.tree.tag_configure('type_int', foreground='#58a6ff')  # Blue
            self.tree.tag_configure('type_float', foreground='#26a69a')  # Cyan
            self.tree.tag_configure('type_str', foreground='#d0d0d0')  # White/Light gray
            self.tree.tag_configure('type_none', foreground='#666666')  # Dark gray
            
        except Exception as e:
            logger.error(f"[EFFECTIVE CONFIG] Failed to load: {e}")
            messagebox.showerror("Error", f"Failed to load effective config:\n{e}", parent=self)
    
    def _add_dict_items(self, parent_node, data_dict, prefix=''):
        """Рекурсивно добавить словарь в дерево"""
        for key, value in sorted(data_dict.items()):
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Nested dict - create node and recurse
                node = self.tree.insert(parent_node, 'end', 
                                       text=f"🔹 {key}", 
                                       values=('', 'dict'))
                self._add_dict_items(node, value, full_key)
            elif isinstance(value, (list, tuple)):
                # List/tuple - show as string
                value_str = ', '.join(str(v) for v in value) if len(value) < 10 else f"{len(value)} items"
                self.tree.insert(parent_node, 'end', 
                               text=f"▪ {key}", 
                               values=(f"[{value_str}]", type(value).__name__))
            else:
                # Simple value with type-based color
                type_name = type(value).__name__
                
                # Determine type tag
                if isinstance(value, bool):
                    type_tag = 'type_bool'
                elif isinstance(value, int):
                    type_tag = 'type_int'
                elif isinstance(value, float):
                    type_tag = 'type_float'
                elif value is None:
                    type_tag = 'type_none'
                else:
                    type_tag = 'type_str'
                
                self.tree.insert(parent_node, 'end', 
                               text=f"▪ {key}", 
                               values=(str(value), type_name),
                               tags=(type_tag,))
    
    def _expand_all(self):
        """Развернуть все узлы дерева"""
        def expand_node(node):
            self.tree.item(node, open=True)
            for child in self.tree.get_children(node):
                expand_node(child)
        
        for item in self.tree.get_children():
            expand_node(item)
    
    def _on_search_changed(self, *args):
        """Обработчик изменения поиска с debounce"""
        if self.search_timer:
            self.after_cancel(self.search_timer)
        self.search_timer = self.after(300, self._filter_tree)
    
    def _on_search_focus_in(self, event):
        """Обработчик фокуса в поле поиска"""
        if self.search_entry.get() == "Type to search keys and values...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(foreground='black')
    
    def _on_search_focus_out(self, event):
        """Обработчик потери фокуса"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Type to search keys and values...")
            self.search_entry.config(foreground='gray')
    
    def _clear_search(self):
        """Очистить поиск"""
        self.search_var.set("")
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Type to search keys and values...")
        self.search_entry.config(foreground='gray')
        self._filter_tree()
    
    def _filter_tree(self):
        """Фильтровать дерево по поисковому запросу с подсветкой"""
        query = self.search_var.get()
        
        # Skip placeholder text
        if query == "Type to search keys and values...":
            query = ""
        
        query = query.lower().strip()
        
        # Clear previous matches
        self.match_items = []
        self.current_match_index = 0
        
        # Remove all tags
        for item in self._get_all_items():
            tags = list(self.tree.item(item, 'tags'))
            tags = [t for t in tags if not t.startswith('match')]
            self.tree.item(item, tags=tags)
        
        if not query:
            # Show all, no highlighting
            self.result_counter.config(text="")
            self._expand_all()
            return
        
        # Find matches
        def check_item(item):
            text = self.tree.item(item, 'text').lower()
            values = self.tree.item(item, 'values')
            
            # Check if text or value matches
            matches = query in text or any(query in str(v).lower() for v in values)
            
            if matches:
                self.match_items.append(item)
                # Add match tag
                tags = list(self.tree.item(item, 'tags'))
                tags.append('match')
                self.tree.item(item, tags=tags)
                # Expand parents
                self._expand_to_item(item)
            
            # Check children
            for child in self.tree.get_children(item):
                check_item(child)
        
        # Process all items
        for root_item in self.tree.get_children():
            check_item(root_item)
        
        # Update counter
        count = len(self.match_items)
        if count == 0:
            self.result_counter.config(text="0 results")
        elif count == 1:
            self.result_counter.config(text="1 result")
            self._highlight_current_match()
        else:
            self.result_counter.config(text=f"{count} results")
            self._highlight_current_match()
    
    def _get_all_items(self):
        """Получить все элементы дерева рекурсивно"""
        items = []
        def collect_items(parent):
            for item in self.tree.get_children(parent):
                items.append(item)
                collect_items(item)
        collect_items('')
        return items
    
    def _expand_to_item(self, item):
        """Раскрыть все родительские узлы до элемента"""
        parent = self.tree.parent(item)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)
    
    def _prev_match(self):
        """Перейти к предыдущему совпадению"""
        if not self.match_items:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.match_items)
        self._highlight_current_match()
        self._scroll_to_current()
    
    def _next_match(self):
        """Перейти к следующему совпадению"""
        if not self.match_items:
            return
        
        self.current_match_index = (self.current_match_index + 1) % len(self.match_items)
        self._highlight_current_match()
        self._scroll_to_current()
    
    def _highlight_current_match(self):
        """Подсветить текущее совпадение"""
        if not self.match_items:
            return
        
        # Remove current_match tag from all items
        for item in self.match_items:
            tags = list(self.tree.item(item, 'tags'))
            tags = [t for t in tags if t != 'current_match']
            self.tree.item(item, tags=tags)
        
        # Add current_match tag to current item
        current_item = self.match_items[self.current_match_index]
        tags = list(self.tree.item(current_item, 'tags'))
        tags.append('current_match')
        self.tree.item(current_item, tags=tags)
        
        # Update counter with position
        count = len(self.match_items)
        pos = self.current_match_index + 1
        self.result_counter.config(text=f"{pos} of {count}")
    
    def _scroll_to_current(self):
        """Прокрутить до текущего совпадения"""
        if not self.match_items:
            return
        
        current_item = self.match_items[self.current_match_index]
        self.tree.see(current_item)
    
    def _copy_all_to_clipboard(self):
        """Скопировать всю конфигурацию в буфер обмена"""
        try:
            effective = self.config_manager.get_effective_config()
            
            # Extract timestamp and configs
            timestamp = effective.get('timestamp', 'N/A')
            configs = effective.get('configs', {})
            
            # Format as YAML-like text
            lines = [f"# Effective Configuration - {timestamp}"]
            lines.append("=" * 60)
            
            for config_name, sections in sorted(configs.items()):
                lines.append(f"\n# {config_name}")
                lines.append("-" * 60)
                if isinstance(sections, dict):
                    for section_name, keys in sorted(sections.items()):
                        lines.append(f"\n[{section_name}]")
                        if isinstance(keys, dict):
                            for key, value in sorted(keys.items()):
                                lines.append(f"  {key}: {value}")
                        else:
                            lines.append(f"  {keys}")
                else:
                    lines.append(f"  {sections}")
            
            text = '\n'.join(lines)
            
            self.clipboard_clear()
            self.clipboard_append(text)
            
            messagebox.showinfo("Success", "Configuration copied to clipboard!", parent=self)
            
        except Exception as e:
            logger.error(f"[EFFECTIVE CONFIG] Failed to copy: {e}")
            messagebox.showerror("Error", f"Failed to copy:\n{e}", parent=self)
    
    def _export_to_file(self):
        """Экспорт конфигурации в файл"""
        try:
            from tkinter import filedialog
            
            filepath = filedialog.asksaveasfilename(
                parent=self,
                title="Export Effective Config",
                defaultextension=".yaml",
                filetypes=[("YAML files", "*.yaml"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            effective = self.config_manager.get_effective_config()
            
            # Save as YAML
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(effective, f, default_flow_style=False, allow_unicode=True)
            
            messagebox.showinfo("Success", f"Configuration exported to:\n{filepath}", parent=self)
            logger.info(f"[EFFECTIVE CONFIG] Exported to {filepath}")
            
        except Exception as e:
            logger.error(f"[EFFECTIVE CONFIG] Failed to export: {e}")
            messagebox.showerror("Error", f"Failed to export:\n{e}", parent=self)
    
    def _close(self):
        """Закрыть окно"""
        try:
            self.grab_release()
        except:
            pass
        self.destroy()


# ==================== EXPLAIN LAST DECISION DIALOG ====================

class ExplainLastDecisionDialog(tk.Toplevel):
    """
    Диалог для объяснения последнего торгового решения
    Показывает детали из decision_logs.jsonl
    """
    
    def __init__(self, parent, title="🔍 Explain Last Decision"):
        super().__init__(parent)
        self.title(title)
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"800x600+{x}+{y}")
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        self.decision_log_path = Path("data/decision_logs.jsonl")
        
        self._create_widgets()
        self._load_last_decision()
    
    def _create_widgets(self):
        """Создать UI элементы"""
        
        # Top frame with title
        top_frame = ttk.Frame(self)
        top_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(top_frame, text="Last Trading Decision Explanation", 
                 font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        ttk.Button(top_frame, text="🔄 Refresh", 
                  command=self._load_last_decision).pack(side='right')
        
        # Info label
        info_text = "This shows the detailed reasoning behind the last trading decision."
        ttk.Label(self, text=info_text, foreground='gray', 
                 font=('Segoe UI', 9)).pack(padx=10, pady=(0, 10))
        
        # Main text area with scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        vsb = ttk.Scrollbar(text_frame, orient="vertical")
        
        self.text_widget = tk.Text(text_frame, 
                                   wrap='word',
                                   yscrollcommand=vsb.set,
                                   font=('Consolas', 10),
                                   bg='#2b2b2b',
                                   fg='#ffffff',
                                   insertbackground='white',
                                   padx=10,
                                   pady=10)
        
        vsb.config(command=self.text_widget.yview)
        
        self.text_widget.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        
        # Bottom buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="📋 Copy to Clipboard", 
                  command=self._copy_to_clipboard).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="✖ Close", 
                  command=self._close).pack(side='right', padx=5)
    
    def _load_last_decision(self):
        """Загрузить последнее решение из decision_logs.jsonl"""
        
        self.text_widget.delete('1.0', 'end')
        
        try:
            if not self.decision_log_path.exists():
                self.text_widget.insert('end', "❌ No decision log found\n\n")
                self.text_widget.insert('end', f"Path: {self.decision_log_path}\n")
                self.text_widget.insert('end', "\nRun the bot in DRY_RUN mode to generate decision logs.")
                return
            
            # Read last line
            with open(self.decision_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                self.text_widget.insert('end', "ℹ️ Decision log file is empty\n\n")
                self.text_widget.insert('end', "No decisions have been made yet.")
                return
            
            last_line = lines[-1].strip()
            if not last_line:
                self.text_widget.insert('end', "ℹ️ Last entry is empty\n")
                return
            
            decision = json.loads(last_line)
            
            # Format decision data
            self._display_decision(decision)
            
        except json.JSONDecodeError as e:
            self.text_widget.insert('end', f"❌ Error parsing decision log: {e}\n\n")
            self.text_widget.insert('end', f"Last line: {last_line}")
            logger.error(f"[EXPLAIN DECISION] JSON parse error: {e}")
            
        except Exception as e:
            self.text_widget.insert('end', f"❌ Error loading decision: {e}\n")
            logger.error(f"[EXPLAIN DECISION] Load error: {e}")
    
    def _display_decision(self, decision: dict):
        """Отформатировать и отобразить решение"""
        
        # Header
        self.text_widget.insert('end', "═" * 70 + "\n", 'header')
        self.text_widget.insert('end', "TRADING DECISION BREAKDOWN\n", 'header')
        self.text_widget.insert('end', "═" * 70 + "\n\n", 'header')
        
        # Signal ID
        signal_id = decision.get('signal_id', 'N/A')
        timestamp = decision.get('timestamp', 'N/A')
        self.text_widget.insert('end', f"📋 Signal ID: ", 'label')
        self.text_widget.insert('end', f"{signal_id}\n", 'value')
        self.text_widget.insert('end', f"⏰ Timestamp: ", 'label')
        self.text_widget.insert('end', f"{timestamp}\n\n", 'value')
        
        # Symbol & Direction
        symbol = decision.get('symbol', 'N/A')
        raw_signal = decision.get('raw_signal', 'N/A')
        self.text_widget.insert('end', f"💹 Symbol: ", 'label')
        self.text_widget.insert('end', f"{symbol}\n", 'value')
        self.text_widget.insert('end', f"➡️  Direction: ", 'label')
        self.text_widget.insert('end', f"{raw_signal}\n\n", 'value')
        
        # GPT Analysis
        self.text_widget.insert('end', "─" * 70 + "\n", 'separator')
        self.text_widget.insert('end', "🤖 GPT ANALYSIS\n", 'section')
        self.text_widget.insert('end', "─" * 70 + "\n\n", 'separator')
        
        gpt_action = decision.get('gpt_action', 'N/A')
        gpt_confidence = decision.get('gpt_confidence', 0)
        gpt_reasoning = decision.get('gpt_reasoning', 'N/A')
        
        self.text_widget.insert('end', f"Action: ", 'label')
        self.text_widget.insert('end', f"{gpt_action}\n", 'value')
        self.text_widget.insert('end', f"Confidence: ", 'label')
        self.text_widget.insert('end', f"{gpt_confidence}%\n", 'value')
        self.text_widget.insert('end', f"Reasoning: ", 'label')
        self.text_widget.insert('end', f"{gpt_reasoning}\n\n", 'value')
        
        # Filters
        self.text_widget.insert('end', "─" * 70 + "\n", 'separator')
        self.text_widget.insert('end', "🔍 FILTER RESULTS\n", 'section')
        self.text_widget.insert('end', "─" * 70 + "\n\n", 'separator')
        
        filters = decision.get('filters', {})
        if filters:
            for filter_name, filter_result in filters.items():
                status = "✅ PASS" if filter_result.get('passed', False) else "❌ FAIL"
                self.text_widget.insert('end', f"{filter_name}: ", 'label')
                self.text_widget.insert('end', f"{status}\n", 'value')
                
                reason = filter_result.get('reason', '')
                if reason:
                    self.text_widget.insert('end', f"  → {reason}\n", 'detail')
            self.text_widget.insert('end', "\n")
        else:
            self.text_widget.insert('end', "No filter data available\n\n", 'detail')
        
        # Setup Score
        setup_score = decision.get('setup_score', 0)
        self.text_widget.insert('end', f"📊 Setup Score: ", 'label')
        self.text_widget.insert('end', f"{setup_score}/100\n\n", 'value')
        
        # Final Decision
        self.text_widget.insert('end', "─" * 70 + "\n", 'separator')
        self.text_widget.insert('end', "⚡ FINAL DECISION\n", 'section')
        self.text_widget.insert('end', "─" * 70 + "\n\n", 'separator')
        
        final_decision = decision.get('final_decision', 'UNKNOWN')
        block_reason = decision.get('block_reason', '')
        
        if final_decision == 'ENTER':
            self.text_widget.insert('end', f"✅ DECISION: ", 'label')
            self.text_widget.insert('end', f"{final_decision}\n", 'success')
            self.text_widget.insert('end', "Trade was executed\n", 'detail')
        elif final_decision == 'HOLD':
            self.text_widget.insert('end', f"⏸️  DECISION: ", 'label')
            self.text_widget.insert('end', f"{final_decision}\n", 'warning')
            self.text_widget.insert('end', "No trade action taken\n", 'detail')
        elif final_decision == 'BLOCK':
            self.text_widget.insert('end', f"🚫 DECISION: ", 'label')
            self.text_widget.insert('end', f"{final_decision}\n", 'error')
            self.text_widget.insert('end', f"Reason: {block_reason}\n", 'detail')
        else:
            self.text_widget.insert('end', f"❓ DECISION: ", 'label')
            self.text_widget.insert('end', f"{final_decision}\n", 'value')
        
        # Configure tags for formatting
        self.text_widget.tag_config('header', font=('Segoe UI', 12, 'bold'), foreground='#00ccff')
        self.text_widget.tag_config('section', font=('Segoe UI', 11, 'bold'), foreground='#ffcc00')
        self.text_widget.tag_config('separator', foreground='#666666')
        self.text_widget.tag_config('label', font=('Segoe UI', 10, 'bold'), foreground='#aaaaaa')
        self.text_widget.tag_config('value', foreground='#ffffff')
        self.text_widget.tag_config('detail', foreground='#999999', font=('Segoe UI', 9))
        self.text_widget.tag_config('success', foreground='#00ff00', font=('Segoe UI', 11, 'bold'))
        self.text_widget.tag_config('warning', foreground='#ffaa00', font=('Segoe UI', 11, 'bold'))
        self.text_widget.tag_config('error', foreground='#ff4444', font=('Segoe UI', 11, 'bold'))
    
    def _copy_to_clipboard(self):
        """Скопировать весь текст в буфер обмена"""
        try:
            text = self.text_widget.get('1.0', 'end-1c')
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Success", "Decision copied to clipboard!", parent=self)
        except Exception as e:
            logger.error(f"[EXPLAIN DECISION] Failed to copy: {e}")
            messagebox.showerror("Error", f"Failed to copy:\n{e}", parent=self)
    
    def _close(self):
        """Закрыть окно"""
        try:
            self.grab_release()
        except:
            pass
        self.destroy()


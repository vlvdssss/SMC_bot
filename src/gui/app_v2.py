#!/usr/bin/env python3
"""
BAZA Trading Bot V2 - Modern Professional UI
Refactored with ttkbootstrap, proper grid layout, and enhanced UX
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
from pathlib import Path
import sys
import os
import yaml
from queue import Queue
from typing import Optional

# Try ttkbootstrap, fallback to ttk
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    BOOTSTRAP_AVAILABLE = True
except ImportError:
    from tkinter import ttk
    BOOTSTRAP_AVAILABLE = False
    print("⚠️ ttkbootstrap not available. Install: pip install ttkbootstrap")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.app_state import AppState
from src.core.bot_manager import bot_manager, BotManager, BotStatus
from src.core.logger import logger as app_logger
from src.core.mt5_manager import MT5Manager
from src.core.run_session_manager import get_run_session_manager
from src.core.state_core import get_state_core
from src.core.config_manager import get_config_manager

# Import AI modules conditionally
try:
    from src.ai.analyst_scheduler import get_scheduler, init_scheduler
    from src.ai.signal_manager import AISignalManager
    AI_AVAILABLE = True
except Exception as e:
    app_logger.warning(f"AI modules not available: {e}")
    AI_AVAILABLE = False

# Import settings dialogs V2 (модальные окна)
try:
    from src.gui.dialogs_v2 import SettingsDialog, MT5SettingsDialog
    SETTINGS_AVAILABLE = True
except Exception as e:
    app_logger.warning(f"Settings dialogs not available: {e}")
    SETTINGS_AVAILABLE = False


# ==================== COLOR SCHEME ====================
class Theme:
    """Unified color palette for dark terminal theme"""
    # Backgrounds (DARKER)
    BG_DARK = '#15171b'       # Main background
    BG_PANEL = '#1c1f26'      # Panels
    BG_CARD = '#21262d'       # Cards
    BG_HOVER = '#2b2f36'      # Hover state
    
    # Borders
    BORDER = '#30363d'
    
    # Text
    TEXT_PRIMARY = '#d0d0d0'  # Brighter
    TEXT_SECONDARY = '#8b8f98'
    TEXT_MUTED = '#6e7681'
    
    # Status colors (ONLY for text, NOT for buttons)
    SUCCESS = '#3fb950'       # Green
    ERROR = '#f85149'         # Red
    WARNING = '#d29922'       # Yellow/Orange
    INFO = '#58a6ff'          # Blue
    ACCENT = '#3a7bd5'        # Primary blue
    
    # Trading
    BUY = '#26a69a'          # Teal
    SELL = '#ef5350'         # Red


def configure_dark_style(root):
    """Configure unified dark theme for all ttk widgets"""    
    style = ttk.Style()
    
    # ===== BUTTONS (единый стиль, БЕЗ цветов) =====
    style.configure('App.TButton',
                    background=Theme.BG_HOVER,
                    foreground=Theme.TEXT_PRIMARY,
                    borderwidth=0,
                    focuscolor='none',
                    padding=10)
    
    style.map('App.TButton',
              background=[('active', Theme.BORDER), ('pressed', Theme.BG_CARD)],
              foreground=[('active', Theme.TEXT_PRIMARY)])
    
    # ===== TREEVIEW (темный) =====
    style.configure('Treeview',
                    background=Theme.BG_DARK,
                    fieldbackground=Theme.BG_DARK,
                    foreground=Theme.TEXT_PRIMARY,
                    borderwidth=0,
                    rowheight=30)
    
    style.configure('Treeview.Heading',
                    background=Theme.BG_PANEL,
                    foreground=Theme.TEXT_PRIMARY,
                    borderwidth=0,
                    relief='flat')
    
    style.map('Treeview',
              background=[('selected', Theme.BG_HOVER)],
              foreground=[('selected', Theme.TEXT_PRIMARY)])
    
    style.map('Treeview.Heading',
              background=[('active', Theme.BG_HOVER)])
    
    # ===== NOTEBOOK (темный) =====
    style.configure('TNotebook',
                    background=Theme.BG_DARK,
                    borderwidth=0)
    
    style.configure('TNotebook.Tab',
                    background=Theme.BG_PANEL,
                    foreground=Theme.TEXT_SECONDARY,
                    padding=[20, 10],
                    borderwidth=0)
    
    style.map('TNotebook.Tab',
              background=[('selected', Theme.BG_CARD), ('active', Theme.BG_HOVER)],
              foreground=[('selected', Theme.TEXT_PRIMARY), ('active', Theme.TEXT_PRIMARY)])
    
    # ===== FRAME =====
    style.configure('Dark.TFrame', background=Theme.BG_DARK)
    style.configure('Panel.TFrame', background=Theme.BG_PANEL)
    style.configure('Card.TFrame', background=Theme.BG_CARD)
    
    app_logger.info("✅ Dark terminal style configured")
    return style


# ==================== STATUS BAR ====================
class StatusBar(ttk.Frame):
    """Top status bar with fixed height - professional flat design"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='Dark.TFrame', height=46)  # Фиксированная высота 46px
        self.pack_propagate(False)
        
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)  # Растягивать по вертикали
        self.grid_columnconfigure(0, weight=0)  # Left section (no expand)
        self.grid_columnconfigure(1, weight=1)  # Middle spacer (expand)
        self.grid_columnconfigure(2, weight=0)  # Right section (no expand)
        
        # Left section (all status blocks)
        left_frame = ttk.Frame(self, style='Dark.TFrame')
        left_frame.grid(row=0, column=0, sticky='nsw', padx=(16, 0))
        
        col = 0
        
        # MT5 Status Block
        self.mt5_indicator = ttk.Label(left_frame, text="●", foreground=Theme.ERROR,
                                      font=('Arial', 14))
        self.mt5_indicator.grid(row=0, column=col, sticky='ns', padx=(0, 4))
        col += 1
        
        self.mt5_label = ttk.Label(left_frame, text="MT5: Disconnected",
                                  font=('Arial', 9, 'bold'),
                                  foreground=Theme.ERROR)
        self.mt5_label.grid(row=0, column=col, sticky='ns')
        col += 1
        
        # Separator
        ttk.Separator(left_frame, orient='vertical').grid(row=0, column=col, sticky='ns', padx=16)
        col += 1
        
        # Symbol Block
        self.symbol_label = ttk.Label(left_frame, text="XAUUSD", 
                                      font=('Arial', 9),
                                      foreground=Theme.TEXT_MUTED)
        self.symbol_label.grid(row=0, column=col, sticky='ns')
        col += 1
        
        # Separator
        ttk.Separator(left_frame, orient='vertical').grid(row=0, column=col, sticky='ns', padx=16)
        col += 1
        
        # Trading Status Block
        ttk.Label(left_frame, text="Trading:", 
                 font=('Arial', 9),
                 foreground=Theme.TEXT_MUTED).grid(row=0, column=col, sticky='ns', padx=(0, 5))
        col += 1
        
        self.trading_label = ttk.Label(left_frame, text="OFF", 
                                       font=('Arial', 9, 'bold'),
                                       foreground=Theme.ERROR)
        self.trading_label.grid(row=0, column=col, sticky='ns')
        col += 1
        
        # Separator
        ttk.Separator(left_frame, orient='vertical').grid(row=0, column=col, sticky='ns', padx=16)
        col += 1
        
        # AI Model Block
        ttk.Label(left_frame, text="AI Model:", 
                 font=('Arial', 9),
                 foreground=Theme.TEXT_MUTED).grid(row=0, column=col, sticky='ns', padx=(0, 5))
        col += 1
        
        self.ai_model_label = ttk.Label(left_frame, text="GPT-4o", 
                                        font=('Arial', 9, 'bold'),
                                        foreground=Theme.ACCENT)
        self.ai_model_label.grid(row=0, column=col, sticky='ns')
        
        # Right section (LIVE + Time)
        right_frame = ttk.Frame(self, style='Dark.TFrame')
        right_frame.grid(row=0, column=2, sticky='nse', padx=(0, 16))
        
        self.live_label = ttk.Label(right_frame, text="● LIVE", 
                                    font=('Arial', 9, 'bold'),
                                    foreground=Theme.SUCCESS)
        self.live_label.grid(row=0, column=0, sticky='ns', padx=(0, 12))
        
        self.time_label = ttk.Label(right_frame, text="--:--:--", 
                                    font=('Arial', 9),
                                    foreground=Theme.TEXT_MUTED)
        self.time_label.grid(row=0, column=1, sticky='ns')
        
        # Start update loop
        self._update_time()
    
    def _update_time(self):
        """Update time display every second"""
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        self.after(1000, self._update_time)
    
    def update_mt5_status(self, connected: bool):
        """Update MT5 connection status"""
        if connected:
            self.mt5_indicator.configure(foreground=Theme.SUCCESS)
            self.mt5_label.configure(text="MT5: Connected", foreground=Theme.SUCCESS)
        else:
            self.mt5_indicator.configure(foreground=Theme.ERROR)
            self.mt5_label.configure(text="MT5: Disconnected", foreground=Theme.ERROR)
    
    def update_symbol(self, symbol: str):
        """Update symbol display"""
        self.symbol_label.configure(text=symbol)
    
    def update_price(self, price: float):
        """Update price display (currently not shown in flat design)"""
        # Price removed from header for cleaner look
        pass
    
    def update_trading_status(self, active: bool):
        """Update trading status"""
        app_logger.info(f"[STATUS BAR] update_trading_status called with active={active}")
        if active:
            self.trading_label.configure(text="ON", foreground=Theme.SUCCESS)
            app_logger.info("[STATUS BAR] Trading status set to ON (green)")
        else:
            self.trading_label.configure(text="OFF", foreground=Theme.ERROR)
            app_logger.info("[STATUS BAR] Trading status set to OFF (red)")


# ==================== LEFT CONTROL PANEL ====================
class ControlPanel(ttk.Frame):
    """Left control panel with fixed width and scrollable content"""
    
    def __init__(self, parent, on_start, on_stop, on_settings, on_mt5_settings, on_test_gpt, on_show_config=None, on_explain_decision=None):
        super().__init__(parent, style='Dark.TFrame', width=360)
        self.pack_propagate(False)
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_settings = on_settings
        self.on_mt5_settings = on_mt5_settings
        self.on_test_gpt = on_test_gpt
        self.on_show_config = on_show_config
        self.on_explain_decision = on_explain_decision
        self.is_running = False
        self.is_paused = False
        
        # Create scrollable structure
        self._create_scrollable_container()
        
        # A) Control Section
        self._create_control_section()
        
        # B) NOW Status Dashboard
        self._create_now_status_dashboard()
        
        # C) Account Statistics
        self._create_stats_section()
        
        # D) Current Settings
        self._create_settings_section()
        
        # E) Quick Navigation
        self._create_nav_section()
        
        # Force update canvas scroll region
        self.content_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _create_scrollable_container(self):
        """Create canvas with scrollbar for scrollable content"""
        # Canvas
        self.canvas = tk.Canvas(self, bg=Theme.BG_DARK, 
                               highlightthickness=0, width=340)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        self.scrollbar = tk.Scrollbar(self, orient='vertical', 
                                     command=self.canvas.yview,
                                     bg=Theme.BG_PANEL,
                                     troughcolor=Theme.BG_DARK,
                                     activebackground=Theme.BORDER)
        self.scrollbar.pack(side='right', fill='y')
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Content frame (inside canvas)
        self.content_frame = tk.Frame(self.canvas, bg=Theme.BG_DARK)
        self.canvas_window = self.canvas.create_window((0, 0), 
                                                       window=self.content_frame,
                                                       anchor='nw',
                                                       width=340)
        
        # Update scroll region when content changes
        def on_frame_configure(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
        self.content_frame.bind('<Configure>', on_frame_configure)
        
        # Mouse wheel scrolling (only when cursor over sidebar)
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def on_enter(event):
            self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def on_leave(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind("<Enter>", on_enter)
        self.canvas.bind("<Leave>", on_leave)
    
    def _create_control_section(self):
        """Create control buttons section (единый темный стиль)"""
        frame = tk.Frame(self.content_frame, bg=Theme.BG_CARD, 
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        frame.pack(fill='x', padx=12, pady=(12, 10))
        
        # Header
        tk.Label(frame, text="Control", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY).pack(anchor='w', 
                                                              padx=10, pady=(10, 12))
        
        # START/STOP button (единый стиль, БЕЗ зелёного цвета)
        self.control_btn = ttk.Button(frame, text="▶ START BOT",
                                     style='App.TButton',
                                     command=self._toggle_bot)
        self.control_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # PAUSE button (единый стиль, БЕЗ жёлтого цвета)
        self.pause_btn = ttk.Button(frame, text="⏸ PAUSE",
                                   style='App.TButton',
                                   command=self._toggle_pause)
        self.pause_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # FORCE ANALYSIS button (единый стиль, БЕЗ синего цвета)
        force_btn = ttk.Button(frame, text="🚀 Force AI Analysis",
                              style='App.TButton',
                              command=self._force_analysis)
        force_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # RESET PROTECTION button (единый стиль, БЕЗ красного цвета)
        reset_btn = ttk.Button(frame, text="🔓 Reset Protection",
                              style='App.TButton',
                              command=self._reset_protection)
        reset_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # SHOW EFFECTIVE CONFIG button (диагностика)
        config_btn = ttk.Button(frame, text="🔍 Show Effective Config",
                              style='App.TButton',
                              command=self._show_effective_config)
        config_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # EXPLAIN LAST DECISION button (QA)
        explain_btn = ttk.Button(frame, text="💬 Explain Last Decision",
                                style='App.TButton',
                                command=self._explain_last_decision)
        explain_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # PRE-FLIGHT CHECK button (production readiness)
        preflight_btn = ttk.Button(frame, text="✈️ Pre-Flight Check",
                                   style='App.TButton',
                                   command=self._run_preflight_check)
        preflight_btn.pack(fill='x', padx=10, pady=(0, 8))
        
        # TEST TELEGRAM button
        test_telegram_btn = ttk.Button(frame, text="📱 Test Telegram",
                                      style='App.TButton',
                                      command=self._test_telegram)
        test_telegram_btn.pack(fill='x', padx=10, pady=(0, 12))
        
        # PRESET BUTTONS Section
        preset_label = tk.Label(frame, text="⚙️ Configuration Presets", 
                               font=('Segoe UI', 9, 'bold'),
                               bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        preset_label.pack(fill='x', padx=10, pady=(0, 6))
        
        # Preset 1: SAFE (Default)
        preset_safe_btn = ttk.Button(frame, text="🟢 SAFE (5D) - Balanced",
                                    style='App.TButton',
                                    command=lambda: self._load_preset("XAUUSD_SAFE_5D"))
        preset_safe_btn.pack(fill='x', padx=10, pady=(0, 4))
        
        # Preset 2: STRICT
        preset_strict_btn = ttk.Button(frame, text="🔵 STRICT - Quality>Quantity",
                                      style='App.TButton',
                                      command=lambda: self._load_preset("XAUUSD_STRICT"))
        preset_strict_btn.pack(fill='x', padx=10, pady=(0, 4))
        
        # Preset 3: ACTIVE
        preset_active_btn = ttk.Button(frame, text="🟡 ACTIVE - More Trades",
                                      style='App.TButton',
                                      command=lambda: self._load_preset("XAUUSD_ACTIVE"))
        preset_active_btn.pack(fill='x', padx=10, pady=(0, 10))
    
    def _create_now_status_dashboard(self):
        """Create NOW status dashboard (real-time bot state)"""
        frame = tk.Frame(self.content_frame, bg=Theme.BG_CARD,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        frame.pack(fill='x', padx=12, pady=(10, 10))
        
        # Header
        tk.Label(frame, text="⏱️ NOW Status", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w', 
                                                        padx=10, pady=(10, 8))
        
        # Bot Status
        status_row = tk.Frame(frame, bg=Theme.BG_CARD)
        status_row.pack(fill='x', padx=10, pady=3)
        tk.Label(status_row, text="Bot:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side='left')
        self.now_bot_status = tk.Label(status_row, text="STOPPED", 
                                      font=('Arial', 9, 'bold'),
                                      bg=Theme.BG_CARD, fg=Theme.ERROR)
        self.now_bot_status.pack(side='right')
        
        # Active Signal
        signal_row = tk.Frame(frame, bg=Theme.BG_CARD)
        signal_row.pack(fill='x', padx=10, pady=3)
        tk.Label(signal_row, text="Signal:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side='left')
        self.now_active_signal = tk.Label(signal_row, text="None", 
                                         font=('Arial', 9),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.now_active_signal.pack(side='right')
        
        # Block Reason
        block_row = tk.Frame(frame, bg=Theme.BG_CARD)
        block_row.pack(fill='x', padx=10, pady=3)
        tk.Label(block_row, text="Block:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side='left')
        self.now_block_reason = tk.Label(block_row, text="-", 
                                        font=('Arial', 9),
                                        bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.now_block_reason.pack(side='right')
        
        # Cooldown remaining
        cooldown_row = tk.Frame(frame, bg=Theme.BG_CARD)
        cooldown_row.pack(fill='x', padx=10, pady=3)
        tk.Label(cooldown_row, text="Cooldown:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side='left')
        self.now_cooldown = tk.Label(cooldown_row, text="-", 
                                    font=('Arial', 9),
                                    bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.now_cooldown.pack(side='right')
        
        # Next check timer
        nextcheck_row = tk.Frame(frame, bg=Theme.BG_CARD)
        nextcheck_row.pack(fill='x', padx=10, pady=3)
        tk.Label(nextcheck_row, text="Next Check:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side='left')
        self.now_next_check = tk.Label(nextcheck_row, text="-", 
                                      font=('Arial', 9),
                                      bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.now_next_check.pack(side='right')
        
        # Last decision summary
        decision_frame = tk.Frame(frame, bg=Theme.BG_CARD)
        decision_frame.pack(fill='x', padx=10, pady=(8, 10))
        tk.Label(decision_frame, text="Last Decision:", font=('Arial', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(anchor='w')
        self.now_last_decision = tk.Label(decision_frame, text="No decisions yet", 
                                         font=('Arial', 8),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED,
                                         wraplength=300, justify='left')
        self.now_last_decision.pack(anchor='w', pady=(2, 0))
    
    def _create_stats_section(self):
        """Create account statistics cards with fixed heights"""
        frame = tk.Frame(self.content_frame, bg=Theme.BG_PANEL)
        frame.pack(fill='x', padx=12, pady=10)
        
        # Header
        tk.Label(frame, text="Account Statistics", font=('Arial', 10, 'bold'),
                bg=Theme.BG_PANEL, fg=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 8))
        
        # Balance card (fixed height)
        self.balance_card = self._create_stat_card(frame, "Balance", "$0.00")
        self.balance_card.pack(fill='x', pady=(0, 6))
        
        # Today P&L card (fixed height)
        self.today_pnl_card = self._create_stat_card(frame, "Today P&L", "$0.00")
        self.today_pnl_card.pack(fill='x', pady=(0, 6))
        
        # Total P&L card (fixed height)
        self.total_pnl_card = self._create_stat_card(frame, "Total P&L", "$0.00")
        self.total_pnl_card.pack(fill='x', pady=(0, 8))
        
        # Small stats (trades, winrate) - компактно в одну строку
        small_stats = tk.Frame(frame, bg=Theme.BG_PANEL)
        small_stats.pack(fill='x')
        
        self.trades_label = tk.Label(small_stats, text="Trades today: 0",
                                     font=('Arial', 8), bg=Theme.BG_PANEL,
                                     fg=Theme.TEXT_MUTED)
        self.trades_label.pack(side='left')
        
        self.winrate_label = tk.Label(small_stats, text="Winrate: 0%",
                                      font=('Arial', 8), bg=Theme.BG_PANEL,
                                      fg=Theme.TEXT_MUTED)
        self.winrate_label.pack(side='right')
    
    def _create_stat_card(self, parent, title: str, value: str):
        """Create a statistic card with FIXED HEIGHT"""
        card = tk.Frame(parent, bg=Theme.BG_CARD, 
                       highlightbackground=Theme.BORDER,
                       highlightthickness=1,
                       height=75)  # ФИКСИРОВАННАЯ ВЫСОТА
        card.pack_propagate(False)  # ВАЖНО - чтобы высота не менялась
        
        # Title
        tk.Label(card, text=title, font=('Arial', 9), 
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(pady=(10, 2))
        
        # Value (larger font)
        value_label = tk.Label(card, text=value, font=('Arial', 13, 'bold'),
                              bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        value_label.pack(pady=(0, 10))
        
        # Store value label for updates
        card.value_label = value_label
        return card
    
    def _create_settings_section(self):
        """Create current settings display (без Entry виджетов)"""
        frame = tk.Frame(self.content_frame, bg=Theme.BG_CARD,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        frame.pack(fill='x', padx=12, pady=10)
        
        # Header
        tk.Label(frame, text="Current Settings", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY).pack(anchor='w', 
                                                              padx=10, pady=(10, 8))
        
        # Settings rows (Label + Label вместо Entry)
        self.risk_value = self._create_setting_row(frame, "Risk:", "1.0%")
        self.trading_value = self._create_setting_row(frame, "Trading:", "OFF")
        self.ai_value = self._create_setting_row(frame, "AI:", "GPT-4o")
        self.mode_value = self._create_setting_row(frame, "Mode:", "Auto")
        
        # Bottom padding
        tk.Frame(frame, height=10, bg=Theme.BG_CARD).pack()
    
    def _create_setting_row(self, parent, label_text: str, value_text: str):
        """Create a setting row with label and value (NO Entry widgets)"""
        row = tk.Frame(parent, bg=Theme.BG_CARD)
        row.pack(fill='x', pady=3, padx=10)
        
        # Label (left)
        tk.Label(row, text=label_text, font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY,
                anchor='w').pack(side='left')
        
        # Value (right, bold)
        value_label = tk.Label(row, text=value_text, font=('Arial', 9, 'bold'),
                              bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                              anchor='e')
        value_label.pack(side='right')
        
        return value_label  # Return для обновления значения
    
    def _create_nav_section(self):
        """Create quick navigation buttons (ВИДИМЫЕ, крупные кнопки)"""
        frame = tk.Frame(self.content_frame, bg=Theme.BG_CARD,
                        highlightbackground=Theme.BORDER, highlightthickness=2,  # Толще граница
                        relief='solid')
        frame.pack(fill='x', padx=12, pady=15)  # Больше отступ
        
        # Header (крупнее)
        tk.Label(frame, text="⚡ Quick Navigation", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w',  # Яркий цвет
                                                        padx=12, pady=(12, 10))
        
        # Settings Button (единый стиль)
        settings_btn = ttk.Button(frame, text="⚙️  Settings",
                                 style='App.TButton',
                                 command=self._open_settings)
        settings_btn.pack(fill='x', padx=12, pady=(0, 10))
        
        # MT5 Settings Button (единый стиль)
        mt5_btn = ttk.Button(frame, text="🔧  MT5 Settings",
                            style='App.TButton',
                            command=self._open_mt5_settings)
        mt5_btn.pack(fill='x', padx=12, pady=(0, 12))
        
        # Bottom padding
        tk.Frame(frame, height=20, bg=Theme.BG_CARD).pack()  # Больше padding
        
        # Bottom padding
        tk.Frame(frame, height=10, bg=Theme.BG_CARD).pack()
    
    # Button handlers
    def _toggle_bot(self):
        """Toggle bot start/stop (единый стиль, БЕЗ смены цвета)"""
        if self.is_running:
            self.control_btn.config(text="▶ START BOT")  # Убран bg=
            self.is_running = False
            if self.on_stop:
                self.on_stop()
        else:
            self.control_btn.config(text="■ STOP BOT")  # Убран bg=
            self.is_running = True
            if self.on_start:
                self.on_start()
    
    def _toggle_pause(self):
        """Toggle pause/resume (единый стиль, БЕЗ смены цвета)"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="▶ RESUME")  # Убран bg=
        else:
            self.pause_btn.config(text="⏸ PAUSE")   # Убран bg=
    
    def _force_analysis(self):
        messagebox.showinfo("Info", "Force AI Analysis - to be implemented")
    
    def _reset_protection(self):
        result = messagebox.askyesno("Confirm", "Reset all protection blocks?")
        if result:
            messagebox.showinfo("Success", "Protection reset")
    
    def _open_settings(self):
        if self.on_settings:
            self.on_settings()
    
    def _open_mt5_settings(self):
        if self.on_mt5_settings:
            self.on_mt5_settings()
    
    def _test_gpt(self):
        if self.on_test_gpt:
            self.on_test_gpt()
    
    def _show_effective_config(self):
        """Show effective config dialog"""
        if self.on_show_config:
            self.on_show_config()
    
    def _explain_last_decision(self):
        """Show explain last decision dialog"""
        if self.on_explain_decision:
            self.on_explain_decision()
    
    def _run_preflight_check(self):
        """Run pre-flight checks before production start"""
        from src.core.preflight_checks import get_preflight_checker
        from tkinter import messagebox
        import threading
        
        def run_check():
            try:
                checker = get_preflight_checker()
                success, report = checker.run_all_checks()
                
                # Build message
                status = "✅ PASS" if success else "❌ FAIL"
                msg = f"Pre-Flight Check: {status}\n\n"
                
                for check_name, check_data in report['checks'].items():
                    check_status = "✅" if check_data['passed'] else "❌"
                    msg += f"{check_status} {check_name.upper()}\n"
                    if not check_data['passed']:
                        error = check_data['details'].get('error', 'Unknown')
                        msg += f"   └─ {error}\n"
                
                if success:
                    params = report['critical_params']
                    msg += f"\n🔑 Critical Parameters:\n"
                    msg += f"  • Min Confidence: {params.get('min_confidence', 'N/A')}%\n"
                    msg += f"  • Daily Limit: {params.get('daily_limit', 'N/A')}\n"
                    msg += f"  • Max Spread: {params.get('max_spread_pips', 'N/A')} pips\n"
                    msg += f"  • Model: {params.get('model', 'N/A')}\n"
                    msg += f"  • Mode: {'DRY_RUN' if params.get('dry_run') else 'LIVE'}\n"
                    
                    messagebox.showinfo("Pre-Flight Check", msg)
                else:
                    messagebox.showerror("Pre-Flight Check FAILED", msg)
            
            except Exception as e:
                messagebox.showerror("Pre-Flight Error", f"Failed to run checks:\n{e}")
        
        threading.Thread(target=run_check, daemon=True).start()
    
    def _test_telegram(self):
        """Test Telegram bot connection"""
        from tkinter import messagebox
        import threading
        
        def test_thread():
            try:
                from src.core.config_manager import get_config_manager
                
                config_manager = get_config_manager()
                telegram_config = config_manager.get_config('telegram')
                
                if not telegram_config:
                    messagebox.showerror("Telegram Test", "telegram.yaml not found")
                    return
                
                enabled = telegram_config.get('bot', {}).get('enabled', False)
                
                if not enabled:
                    messagebox.showwarning("Telegram Test", 
                                          "❌ Telegram DISABLED in config\n\nEnable in config/telegram.yaml")
                    return
                
                bot_token = telegram_config.get('bot', {}).get('token', '')
                chat_id = telegram_config.get('bot', {}).get('chat_id', '')
                
                if not bot_token or not chat_id:
                    messagebox.showerror("Telegram Test",
                                        "❌ Token or Chat ID not configured\n\nCheck config/telegram.yaml")
                    return
                
                # Try to send test message (if monitoring available)
                try:
                    from src.monitoring.telegram_bot import TelegramBotWithButtons
                    # Simple check - just validate config
                    messagebox.showinfo("Telegram Test",
                                       "✅ Telegram configured\n\n"
                                       f"Token: {bot_token[:20]}...\n"
                                       f"Chat ID: {chat_id}\n\n"
                                       "To send test message, use /status in Telegram")
                except ImportError:
                    messagebox.showwarning("Telegram Test",
                                          "⚠️ Telegram modules not available\n\n"
                                          "Config OK, but monitoring not loaded")
            
            except Exception as e:
                messagebox.showerror("Telegram Test", f"Test failed:\n{e}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _load_preset(self, preset_name: str):
        """Load and apply configuration preset"""
        from tkinter import messagebox
        import threading
        
        def load_preset():
            try:
                from src.core.config_presets import get_preset_manager, AVAILABLE_PRESETS
                from src.core.config_manager import get_config_manager
                
                # Get preset info
                if preset_name not in AVAILABLE_PRESETS:
                    messagebox.showerror("Preset Error", f"Unknown preset: {preset_name}")
                    return
                
                preset = AVAILABLE_PRESETS[preset_name]
                
                # Prepare confirmation messages by preset type
                preset_descriptions = {
                    "XAUUSD_SAFE_5D": (
                        "🟢 XAUUSD SAFE (5-Day)\n"
                        "Balanced quality and frequency\n\n"
                        "• Min Confidence: 75%\n"
                        "• Daily Limit: 6 trades\n"
                        "• Max Spread: 1.5 pips\n"
                        "• Cooldowns: Moderate"
                    ),
                    "XAUUSD_STRICT": (
                        "🔵 XAUUSD STRICT\n"
                        "Quality over quantity - fewer high-quality trades\n\n"
                        "• Min Confidence: 82% (HIGH)\n"
                        "• Daily Limit: 4 trades (LOW)\n"
                        "• Max Spread: 1.2 pips (TIGHT)\n"
                        "• Cooldowns: Long (reduced overtrading)\n\n"
                        "Best for: Choppy markets, calm testing"
                    ),
                    "XAUUSD_ACTIVE": (
                        "🟡 XAUUSD ACTIVE\n"
                        "More trades without becoming a casino\n\n"
                        "• Min Confidence: 70% (LOWER)\n"
                        "• Daily Limit: 8 trades (HIGH)\n"
                        "• Max Spread: 1.8 pips (WIDER)\n"
                        "• Cooldowns: Short (catch more moves)\n\n"
                        "Best for: Trending markets, more statistics"
                    )
                }
                
                # Confirm action
                description = preset_descriptions.get(preset_name, preset.description)
                result = messagebox.askyesno(
                    "Load Preset",
                    f"{description}\n\n"
                    "Apply this preset?\n\n"
                    "This will:\n"
                    "• Update all config files (trading.yaml, ai.yaml, portfolio.yaml)\n"
                    "• Reload configurations\n"
                    "• Update GUI display\n\n"
                    "Continue?",
                    icon='question'
                )
                
                if not result:
                    self.add_log(f"⏸️ Preset load cancelled: {preset_name}", "INFO")
                    return
                
                self.add_log(f"⚙️ Loading {preset_name} preset...", "INFO")
                
                # Apply preset
                manager = get_preset_manager()
                report = manager.apply_preset(preset_name)
                
                if not report.get('success'):
                    messagebox.showerror("Preset Error", "Failed to apply preset")
                    self.add_log("❌ Preset application failed", "ERROR")
                    return
                
                # Reload configs
                config_manager = get_config_manager()
                config_manager.reload_all()
                self.add_log("🔄 Configs reloaded", "INFO")
                
                # Update GUI
                self.trading_config = config_manager.get_config('trading')
                
                # Log summary
                summary = report['summary']
                self.add_log("=" * 70, "INFO")
                self.add_log(f"✅ [PRESET] {summary['preset']} applied", "INFO")
                self.add_log("=" * 70, "INFO")
                
                # Log key parameters
                self.add_log(f"📊 Symbol: {summary['symbol']}", "INFO")
                self.add_log(f"🎯 Mode: {summary['mode']} (dry_run={summary['dry_run']})", "INFO")
                
                filters = summary['filters']
                self.add_log(f"🛡️ Filters:", "INFO")
                self.add_log(f"  • min_confidence: {filters['min_confidence']}%", "INFO")
                self.add_log(f"  • min_rr: {filters['min_rr']}", "INFO")
                self.add_log(f"  • min_setup_score: {filters['min_setup_score']}", "INFO")
                self.add_log(f"  • daily_limit: {filters['daily_limit']}", "INFO")
                self.add_log(f"  • max_spread_pips: {filters['max_spread_pips']}", "INFO")
                
                cooldowns = summary['cooldowns']
                self.add_log(f"⏰ Cooldowns:", "INFO")
                self.add_log(f"  • after_win: {cooldowns['after_win']} min", "INFO")
                self.add_log(f"  • after_loss: {cooldowns['after_loss']} min", "INFO")
                self.add_log(f"  • after_2_losses: {cooldowns['after_2_losses']} min", "INFO")
                
                protections = summary['protections']
                self.add_log(f"🛡️ Protections:", "INFO")
                self.add_log(f"  • profit_protection_cooldown: {protections['profit_protection_cooldown']} min", "INFO")
                self.add_log(f"  • stop_loss_protection_cooldown: {protections['stop_loss_protection_cooldown']} min", "INFO")
                
                risk = summary['risk']
                self.add_log(f"💰 Risk:", "INFO")
                self.add_log(f"  • fixed_lot_size: {risk['fixed_lot_size']}", "INFO")
                self.add_log(f"  • default_sl_pips: {risk['default_sl_pips']}", "INFO")
                self.add_log(f"  • default_tp_pips: {risk['default_tp_pips']}", "INFO")
                
                signal_quality = summary['signal_quality']
                self.add_log(f"🔄 Signal Quality:", "INFO")
                self.add_log(f"  • invert_signals: {signal_quality['invert_signals']} ⚠️ CRITICAL", "INFO")
                
                # Log signal TTL if available
                if 'signal_ttl' in summary:
                    signal_ttl = summary['signal_ttl']
                    self.add_log(f"⏱️ Signal TTL:", "INFO")
                    self.add_log(f"  • ttl_minutes: {signal_ttl['ttl_minutes']}", "INFO")
                    self.add_log(f"  • requery_cooldown: {signal_ttl['requery_cooldown']} min", "INFO")
                
                v5 = summary['v5_improvements']
                self.add_log(f"🚀 V5 Improvements:", "INFO")
                self.add_log(f"  • adaptive_lot: {v5['adaptive_lot']}", "INFO")
                
                self.add_log("=" * 70, "INFO")
                self.add_log("✅ Preset applied successfully!", "INFO")
                self.add_log("💡 Tip: Click 'Show Effective Config' to verify", "INFO")
                
                # Show success dialog
                messagebox.showinfo(
                    "Preset Applied",
                    f"✅ {summary['preset']} applied successfully!\n\n"
                    f"Symbol: {summary['symbol']}\n"
                    f"Min Confidence: {filters['min_confidence']}%\n"
                    f"Daily Limit: {filters['daily_limit']}\n"
                    f"Max Spread: {filters['max_spread_pips']} pips\n"
                    f"TP Target: {risk['default_tp_pips']} pips\n"
                    f"Adaptive Lot: {v5['adaptive_lot']}\n"
                    f"Invert Signals: {signal_quality['invert_signals']}\n\n"
                    "Check logs for full detail."
                )
                
            except Exception as e:
                self.add_log(f"❌ Preset error: {str(e)}", "ERROR")
                messagebox.showerror("Preset Error", f"Failed to load preset:\n\n{e}")
        
        threading.Thread(target=load_preset, daemon=True).start()
    
    def update_stats(self, balance: float, today_pnl: float, total_pnl: float, trades: int, winrate: float):
        """Update statistics cards"""
        self.balance_card.value_label.config(text=f"${balance:.2f}")
        
        # Today P&L color
        today_color = Theme.SUCCESS if today_pnl >= 0 else Theme.ERROR
        self.today_pnl_card.value_label.config(text=f"${today_pnl:+.2f}", fg=today_color)
        
        # Total P&L color
        total_color = Theme.SUCCESS if total_pnl >= 0 else Theme.ERROR
        self.total_pnl_card.value_label.config(text=f"${total_pnl:+.2f}", fg=total_color)
    
    def update_trading_status(self, active: bool):
        """Update trading status in Current Settings"""
        app_logger.info(f"[CONTROL PANEL] update_trading_status called with active={active}")
        if active:
            self.trading_value.configure(text="ON", fg=Theme.SUCCESS)
        else:
            self.trading_value.configure(text="OFF", fg=Theme.ERROR)
    
    def update_now_status(self, bot_status: str, signal_info: str = None, 
                         block_reason: str = None, cooldown: str = None,
                         next_check: str = None, last_decision: str = None):
        """
        Update NOW status dashboard
        
        Args:
            bot_status: STOPPED/WAITING/ANALYZING/BLOCKED/ORDERING/ERROR
            signal_info: e.g. "BUY 85% (2m old)"
            block_reason: e.g. "Spread too wide"
            cooldown: e.g. "45m remaining"
            next_check: e.g. "in 30s"
            last_decision: e.g. "BLOCK: Low confidence (68% < 75%)"
        """
        # Bot Status with color
        status_colors = {
            'STOPPED': Theme.ERROR,
            'WAITING': Theme.TEXT_PRIMARY,
            'ANALYZING': Theme.INFO,
            'BLOCKED': Theme.WARNING,
            'ORDERING': Theme.SUCCESS,
            'ERROR': Theme.ERROR,
            'RUNNING': Theme.SUCCESS,
            'PAUSED': Theme.WARNING
        }
        
        if hasattr(self, 'now_bot_status'):
            self.now_bot_status.config(
                text=bot_status,
                fg=status_colors.get(bot_status, Theme.TEXT_MUTED)
            )
        
        # Active Signal
        if hasattr(self, 'now_active_signal'):
            if signal_info:
                self.now_active_signal.config(text=signal_info, fg=Theme.SUCCESS)
            else:
                self.now_active_signal.config(text="None", fg=Theme.TEXT_MUTED)
        
        # Block Reason
        if hasattr(self, 'now_block_reason'):
            if block_reason:
                self.now_block_reason.config(text=block_reason, fg=Theme.WARNING)
            else:
                self.now_block_reason.config(text="-", fg=Theme.TEXT_MUTED)
        
        # Cooldown
        if hasattr(self, 'now_cooldown'):
            if cooldown:
                self.now_cooldown.config(text=cooldown, fg=Theme.WARNING)
            else:
                self.now_cooldown.config(text="-", fg=Theme.TEXT_MUTED)
        
        # Next Check
        if hasattr(self, 'now_next_check'):
            if next_check:
                self.now_next_check.config(text=next_check, fg=Theme.INFO)
            else:
                self.now_next_check.config(text="-", fg=Theme.TEXT_MUTED)
        
        # Last Decision
        if hasattr(self, 'now_last_decision'):
            if last_decision:
                self.now_last_decision.config(text=last_decision, fg=Theme.TEXT_PRIMARY)
            else:
                self.now_last_decision.config(text="No decisions yet", fg=Theme.TEXT_MUTED)


# ==================== MAIN APPLICATION ====================
class BazaAppV2:
    """Main application with refactored UI"""
    
    def __init__(self):
        # Create main window
        if BOOTSTRAP_AVAILABLE:
            self.root = ttk.Window(themename="darkly")  # ttkbootstrap
        else:
            self.root = tk.Tk()
            self.root.configure(bg=Theme.BG_DARK)
        
        self.root.title("BAZA Trading Bot V2 - Professional UI")
        self.root.state('zoomed')  # Maximize
        
        # ===== CONFIGURE DARK STYLE (ЕДИНЫЙ СТИЛЬ ДЛЯ ВСЕГО) =====
        configure_dark_style(self.root)
        
        # Initialize state
        self.app_state = AppState()
        self.update_queue = Queue()
        self.mt5_manager = MT5Manager()
        self.config_manager = get_config_manager()  # Config manager singleton
        
        # ML Training state
        self.ml_queue = Queue()
        self.ml_state = {
            'status': 'IDLE',  # IDLE/TRAINING/PAUSED/ERROR
            'dataset': None,
            'epoch': 0,
            'epochs': 50,
            'step': 0,
            'steps_total': 0,
            'device': 'CPU',
            'last_update': '--:--:--'
        }
        self.ml_worker = None
        self.ml_stop_event = threading.Event()
        self.ml_pause_event = threading.Event()
        
        # Trading loop state
        self.trading_stop_event = threading.Event()
        self.trading_thread = None
        
        # Bot Status state (for real-time pipeline tracking + signal tracking)
        self.bot_queue = Queue()
        self.bot_state = {
            'status': 'IDLE',  # IDLE/RUNNING/WAITING/ANALYZING/BLOCKED/ORDERING/TRADING/ERROR
            'last_signal': 'NONE',  # BUY/SELL/NONE
            'block_reason': '',
            'pipeline': {
                'data': 'IDLE',
                'signal': 'IDLE',
                'gpt': 'IDLE',
                'risk': 'IDLE',
                'order': 'IDLE'
            },
            'next_check_sec': 0,
            'last_update': '--:--:--',
            # Signal tracking (single source of truth)
            'active_signal': None,  # Currently active signal being traded/executed
            'last_analysis': None,  # Latest GPT analysis result
        }
        
        # RUN tab event queue (thread-safe для StateCore events)
        self.run_event_queue = Queue()
        
        # Signal state structure:
        # {
        #   'signal_id': 'abc123...',
        #   'signal_id_short': 'abc123',  # last 6 chars
        #   'action': 'BUY/SELL/HOLD',
        #   'confidence': 85,
        #   'symbol': 'XAUUSD',
        #   'entry_price': 5010.0,
        #   'stop_loss': 5015.0,
        #   'take_profit': 4995.0,
        #   'reasoning': '...',
        #   'ticket': None,  # MT5 order ticket (set when order filled)
        #   'timestamp': '2026-02-19T10:25:06',
        #   'status': 'pending/analyzing/approved/rejected/ordering/filled/failed'
        # }
        
        # Load configs
        self.trading_config = self._load_yaml_config('config/trading.yaml')
        self.ai_config = self._load_yaml_config('config/ai.yaml')
        
        # Bot manager reference
        self.bot_manager = bot_manager
       
        # RunSessionManager (для вкладки RUN/MONITOR)
        self.run_session = get_run_session_manager()
        
        # StateCore (подписка на события)
        self.state_core = get_state_core()
        self.state_core.subscribe_to_events(self._on_statecore_event)
        
        # Custom log handler to capture logs
        self._setup_log_handler()
        
        # Create UI
        self._create_ui()
        
        # Update trading status from config
        trading_enabled = self.trading_config.get('trading', {}).get('enabled', True)
        app_logger.info(f"[GUI V2] Loading trading status from config: enabled={trading_enabled}")
        self.status_bar.update_trading_status(trading_enabled)
        self.control_panel.update_trading_status(trading_enabled)
        
        # Start update loops
        self._process_queue()
        self._update_mt5_data()
        self._update_stats()
        self._update_positions_loop()
        self._update_ai_data()
        self._poll_ml_queue()  # ML queue polling
        self._poll_bot_queue()  # Bot status polling
        self._update_analysis_history_loop()  # Analysis history auto-refresh
        self._poll_run_session()  # Run session polling (RUN tab)
        
        app_logger.info("[GUI V2] Application initialized")
    
    def _create_ui(self):
        """Create main UI layout using grid"""
        # Main container
        main_container = ttk.Frame(self.root, style='Dark.TFrame')
        main_container.pack(fill='both', expand=True)
        
        # Configure grid: 2 rows (statusbar + content), 2 columns (left panel + main)
        main_container.grid_rowconfigure(0, weight=0)  # Status bar (fixed)
        main_container.grid_rowconfigure(1, weight=1)  # Content (expand)
        main_container.grid_columnconfigure(0, weight=0)  # Left panel (fixed 360px)
        main_container.grid_columnconfigure(1, weight=1)  # Main area (expand)
        
        # 1) Status Bar (row 0, spanning both columns)
        self.status_bar = StatusBar(main_container)
        self.status_bar.grid(row=0, column=0, columnspan=2, sticky='ew')
        
        # 2) Left Control Panel (row 1, column 0)
        self.control_panel = ControlPanel(main_container,
                                         on_start=self._start_bot,
                                         on_stop=self._stop_bot,
                                         on_settings=self._open_settings,
                                         on_mt5_settings=self._open_mt5_settings,
                                         on_test_gpt=self._test_gpt,
                                         on_show_config=self._show_effective_config,
                                         on_explain_decision=self._explain_last_decision)
        self.control_panel.grid(row=1, column=0, sticky='nsw')
        
        # 3) Right Content Area (row 1, column 1) - contains bot status + tabs
        content_frame = ttk.Frame(main_container, style='Dark.TFrame')
        content_frame.grid(row=1, column=1, sticky='nsew', padx=(0, 0))
        content_frame.grid_rowconfigure(0, weight=0)  # Bot status card (fixed)
        content_frame.grid_rowconfigure(1, weight=1)  # Notebook (expand)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # 3a) Bot Status Card (top of content area)
        self.bot_status_card = self._create_bot_status_card(content_frame)
        self.bot_status_card.grid(row=0, column=0, sticky='ew', padx=8, pady=(8, 4))
        
        # 3b) Notebook Tabs (below bot status)
        self.notebook = ttk.Notebook(content_frame, style='Dark.TNotebook')
        self.notebook.grid(row=1, column=0, sticky='nsew')
        
        # Create tabs
        self._create_tabs()
    
    def _create_bot_status_card(self, parent):
        """Create bot status card with pipeline visualization"""
        card = tk.Frame(parent, bg=Theme.BG_CARD, 
                       highlightbackground=Theme.BORDER, highlightthickness=1, height=110)
        card.pack_propagate(False)
        
        # Main container with padding
        container = tk.Frame(card, bg=Theme.BG_CARD)
        container.pack(fill='both', expand=True, padx=16, pady=12)
        container.grid_columnconfigure(0, weight=0)  # Left: Status
        container.grid_columnconfigure(1, weight=1)  # Center: Pipeline
        container.grid_columnconfigure(2, weight=0)  # Right: Info
        
        # ===== LEFT: Bot Status =====
        left_frame = tk.Frame(container, bg=Theme.BG_CARD)
        left_frame.grid(row=0, column=0, sticky='nsw', padx=(0, 24))
        
        tk.Label(left_frame, text="BOT STATUS", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(anchor='w')
        
        self.bot_status_label = tk.Label(left_frame, text="IDLE", 
                                         font=('Arial', 18, 'bold'),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.bot_status_label.pack(anchor='w', pady=(4, 0))
        
        # ===== CENTER: Pipeline =====
        center_frame = tk.Frame(container, bg=Theme.BG_CARD)
        center_frame.grid(row=0, column=1, sticky='nsew', padx=24)
        
        tk.Label(center_frame, text="PIPELINE", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(anchor='w')
        
        # Pipeline steps container
        pipeline_container = tk.Frame(center_frame, bg=Theme.BG_CARD)
        pipeline_container.pack(fill='x', pady=(8, 0))
        
        self.pipeline_steps = {}
        steps = [
            ('data', 'Data'),
            ('signal', 'Signal'),
            ('gpt', 'GPT'),
            ('risk', 'Risk'),
            ('order', 'Order')
        ]
        
        for i, (key, label) in enumerate(steps):
            step_frame = tk.Frame(pipeline_container, bg=Theme.BG_CARD)
            step_frame.pack(side='left', padx=(0, 16) if i < len(steps)-1 else (0, 0))
            
            # Indicator dot
            indicator = tk.Label(step_frame, text="●", font=('Arial', 16),
                               bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
            indicator.pack(side='left', padx=(0, 6))
            
            # Step name
            name_label = tk.Label(step_frame, text=label, font=('Arial', 9),
                                 bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
            name_label.pack(side='left')
            
            # Store references
            self.pipeline_steps[key] = {'indicator': indicator, 'label': name_label}
            
            # Arrow between steps (except last)
            if i < len(steps) - 1:
                tk.Label(pipeline_container, text="→", font=('Arial', 12),
                        bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left', padx=(0, 16))
        
        # ===== RIGHT: Info =====
        right_frame = tk.Frame(container, bg=Theme.BG_CARD)
        right_frame.grid(row=0, column=2, sticky='nse', padx=(24, 0))
        
        # Active signal with confidence and ID
        signal_frame = tk.Frame(right_frame, bg=Theme.BG_CARD)
        signal_frame.pack(anchor='e', pady=(0, 3))
        
        tk.Label(signal_frame, text="Active Signal:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left', padx=(0, 6))
        self.bot_signal_label = tk.Label(signal_frame, text="NONE", 
                                         font=('Arial', 9, 'bold'),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.bot_signal_label.pack(side='left')
        
        # Signal ID (hidden when no signal)
        self.bot_signal_id_frame = tk.Frame(right_frame, bg=Theme.BG_CARD)
        tk.Label(self.bot_signal_id_frame, text="ID:", font=('Arial', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left', padx=(0, 4))
        self.bot_signal_id_label = tk.Label(self.bot_signal_id_frame, text="", 
                                            font=('Consolas', 8),
                                            bg=Theme.BG_CARD, fg=Theme.ACCENT)
        self.bot_signal_id_label.pack(side='left')
        
        # Ticket (when position opened)
        self.bot_ticket_frame = tk.Frame(right_frame, bg=Theme.BG_CARD)
        tk.Label(self.bot_ticket_frame, text="Ticket:", font=('Arial', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left', padx=(0, 4))
        self.bot_ticket_label = tk.Label(self.bot_ticket_frame, text="", 
                                         font=('Arial', 8, 'bold'),
                                         bg=Theme.BG_CARD, fg=Theme.SUCCESS)
        self.bot_ticket_label.pack(side='left')
        
        # Block reason (hidden by default)
        self.bot_block_frame = tk.Frame(right_frame, bg=Theme.BG_CARD)
        
        tk.Label(self.bot_block_frame, text="Blocked:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.WARNING).pack(side='left', padx=(0, 6))
        self.bot_block_label = tk.Label(self.bot_block_frame, text="", 
                                        font=('Arial', 9),
                                        bg=Theme.BG_CARD, fg=Theme.WARNING)
        self.bot_block_label.pack(side='left')
        
        tk.Label(self.bot_block_frame, text="Blocked:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.WARNING).pack(side='left', padx=(0, 6))
        self.bot_block_label = tk.Label(self.bot_block_frame, text="", 
                                        font=('Arial', 9),
                                        bg=Theme.BG_CARD, fg=Theme.WARNING)
        self.bot_block_label.pack(side='left')
        
        # Next check timer
        timer_frame = tk.Frame(right_frame, bg=Theme.BG_CARD)
        timer_frame.pack(anchor='e')
        
        tk.Label(timer_frame, text="Next check:", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left', padx=(0, 6))
        self.bot_timer_label = tk.Label(timer_frame, text="--s", 
                                        font=('Arial', 9, 'bold'),
                                        bg=Theme.BG_CARD, fg=Theme.ACCENT)
        self.bot_timer_label.pack(side='left')
        
        return card
    
    def _create_tabs(self):
        """Create notebook tabs"""
        # RUN Tab (ДОМАШНЯЯ - первая)
        self.run_tab = self._create_run_tab()
        self.notebook.add(self.run_tab, text='🏠 RUN')
        
        # Logs Tab
        self.logs_tab = self._create_logs_tab()
        self.notebook.add(self.logs_tab, text='📝 Logs')
        
        # AI Decision Tab
        self.ai_tab = self._create_ai_tab()
        self.notebook.add(self.ai_tab, text='🤖 AI Decision')
        
        # Positions Tab
        self.positions_tab = self._create_positions_tab()
        self.notebook.add(self.positions_tab, text='📊 Positions')
        
        # Orders Tab
        self.orders_tab = self._create_orders_tab()
        self.notebook.add(self.orders_tab, text='📈 Orders')
        
        # Risk Tab
        self.risk_tab = self._create_risk_tab()
        self.notebook.add(self.risk_tab, text='🛡️ Risk')
        
        # ML Tab
        self.ml_tab = self._create_ml_tab()
        self.notebook.add(self.ml_tab, text='🧠 ML')
    
    def _create_run_tab(self):
        """Create RUN/MONITOR tab - домашняя вкладка для мониторинга прогона"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Main content with scrollbar
        canvas = tk.Canvas(frame, bg=Theme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ==================== RUN CONTROLLER ====================
        controller_card = tk.Frame(scrollable_frame, bg=Theme.BG_CARD, 
                                   highlightbackground=Theme.BORDER, highlightthickness=1)
        controller_card.pack(fill='x', padx=12, pady=(12, 8))
        
        controller_inner = tk.Frame(controller_card, bg=Theme.BG_CARD)
        controller_inner.pack(fill='x', padx=16, pady=12)
        
        # Title
        tk.Label(controller_inner, text="🏠 RUN CONTROLLER", font=('Arial', 14, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w', pady=(0, 12))
        
        # Buttons row
        btn_frame = tk.Frame(controller_inner, bg=Theme.BG_CARD)
        btn_frame.pack(fill='x', pady=(0, 12))
        
        self.run_start_btn = ttk.Button(btn_frame, text="▶ Start 5-Day Test", 
                                        style='App.TButton', command=self._run_start)
        self.run_start_btn.pack(side='left', padx=(0, 8))
        
        self.run_pause_btn = ttk.Button(btn_frame, text="⏸ Pause", 
                                        style='App.TButton', command=self._run_pause, state='disabled')
        self.run_pause_btn.pack(side='left', padx=(0, 8))
        
        self.run_reset_btn = ttk.Button(btn_frame, text="🔄 Reset/New Run", 
                                        style='App.TButton', command=self._run_reset, state='disabled')
        self.run_reset_btn.pack(side='left', padx=(0, 8))
        
        self.run_export_btn = ttk.Button(btn_frame, text="📤 Export Report", 
                                         style='App.TButton', command=self._run_export, state='disabled')
        self.run_export_btn.pack(side='left', padx=(0, 8))
        
        self.run_folder_btn = ttk.Button(btn_frame, text="📁 Open Folder", 
                                         style='App.TButton', command=self._run_open_folder, state='disabled')
        self.run_folder_btn.pack(side='left')
        
        # Status info
        info_grid = tk.Frame(controller_inner, bg=Theme.BG_CARD)
        info_grid.pack(fill='x')
        
        row = 0
        for label_text in ['Run Status:', 'Run ID:', 'Day:', 'Start Time:', 'ETA End:']:
            tk.Label(info_grid, text=label_text, font=('Arial', 10),
                    bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).grid(row=row, column=0, sticky='w', pady=3)
            row += 1
        
        self.run_status_label = tk.Label(info_grid, text="STOPPED", font=('Arial', 10, 'bold'),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.run_status_label.grid(row=0, column=1, sticky='w', padx=(12, 0), pady=3)
        
        self.run_id_label = tk.Label(info_grid, text="--", font=('Arial', 10),
                                      bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.run_id_label.grid(row=1, column=1, sticky='w', padx=(12, 0), pady=3)
        
        self.run_day_label = tk.Label(info_grid, text="--/5", font=('Arial', 10),
                                       bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.run_day_label.grid(row=2, column=1, sticky='w', padx=(12, 0), pady=3)
        
        self.run_start_time_label = tk.Label(info_grid, text="--", font=('Arial', 10),
                                             bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.run_start_time_label.grid(row=3, column=1, sticky='w', padx=(12, 0), pady=3)
        
        self.run_eta_label = tk.Label(info_grid, text="--", font=('Arial', 10),
                                       bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.run_eta_label.grid(row=4, column=1, sticky='w', padx=(12, 0), pady=3)
        
        # ==================== PROGRESS BARS ====================
        progress_card = tk.Frame(scrollable_frame, bg=Theme.BG_CARD,
                                highlightbackground=Theme.BORDER, highlightthickness=1)
        progress_card.pack(fill='x', padx=12, pady=8)
        
        progress_inner = tk.Frame(progress_card, bg=Theme.BG_CARD)
        progress_inner.pack(fill='x', padx=16, pady=12)
        
        tk.Label(progress_inner, text="📊 PROGRESS", font=('Arial', 13, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w', pady=(0, 12))
        
        # Today progress
        tk.Label(progress_inner, text="Today (0-24h)", font=('Arial', 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(anchor='w', pady=(0, 4))
        
        self.run_today_progressbar = ttk.Progressbar(progress_inner, length=600, mode='determinate')
        self.run_today_progressbar.pack(fill='x', pady=(0, 4))
        
        today_time_frame = tk.Frame(progress_inner, bg=Theme.BG_CARD)
        today_time_frame.pack(fill='x', pady=(0, 16))
        
        self.run_today_elapsed_label = tk.Label(today_time_frame, text="Elapsed: 00:00:00", 
                                                font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.run_today_elapsed_label.pack(side='left')
        
        self.run_today_remaining_label = tk.Label(today_time_frame, text="Remaining: 24:00:00", 
                                                  font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.run_today_remaining_label.pack(side='right')
        
        # Total progress
        tk.Label(progress_inner, text="Total (0-120h / 5 days)", font=('Arial', 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(anchor='w', pady=(0, 4))
        
        self.run_total_progressbar = ttk.Progressbar(progress_inner, length=600, mode='determinate')
        self.run_total_progressbar.pack(fill='x', pady=(0, 4))
        
        total_time_frame = tk.Frame(progress_inner, bg=Theme.BG_CARD)
        total_time_frame.pack(fill='x')
        
        self.run_total_elapsed_label = tk.Label(total_time_frame, text="Elapsed: 00:00:00", 
                                                font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.run_total_elapsed_label.pack(side='left')
        
        self.run_total_remaining_label = tk.Label(total_time_frame, text="Remaining: 120:00:00", 
                                                  font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.run_total_remaining_label.pack(side='right')
        
        # ==================== HEALTH COUNTERS ====================
        counters_card = tk.Frame(scrollable_frame, bg=Theme.BG_CARD,
                                highlightbackground=Theme.BORDER, highlightthickness=1)
        counters_card.pack(fill='x', padx=12, pady=8)
        
        counters_inner = tk.Frame(counters_card, bg=Theme.BG_CARD)
        counters_inner.pack(fill='x', padx=16, pady=12)
        
        tk.Label(counters_inner, text="💚 HEALTH COUNTERS", font=('Arial', 13, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w', pady=(0, 12))
        
        # Grid для счётчиков
        counters_grid = tk.Frame(counters_inner, bg=Theme.BG_CARD)
        counters_grid.pack(fill='x')
        
        # Заголовки колонок
        tk.Label(counters_grid, text="Metric", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, width=30, anchor='w').grid(row=0, column=0, sticky='w', padx=(0, 8), pady=4)
        tk.Label(counters_grid, text="Today", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, width=10).grid(row=0, column=1, pady=4)
        tk.Label(counters_grid, text="Total", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, width=10).grid(row=0, column=2, pady=4)
        
        # Счётчики
        self.run_counter_labels = {}
        row = 1
        for metric_name, display_name in [
            ('mt5_disconnected', 'MT5 Disconnected'),
            ('reconnect', 'MT5 Reconnect'),
            ('invariants', 'Invariants Violated'),
            ('order_lock_timeout', 'Order Lock Timeout'),
            ('analysis_lock_timeout', 'Analysis Lock Timeout'),
            ('circuit_breaker', 'Circuit Breaker'),
            ('orders_sent', 'Orders Sent'),
            ('positions_opened', 'Positions Opened'),
            ('positions_closed', 'Positions Closed'),
            ('enters', 'Enters (ENTER decision)'),
            ('holds', 'Holds (HOLD decision)'),
            ('blocks', 'Blocks (filter/gate)'),
        ]:
            tk.Label(counters_grid, text=display_name, font=('Arial', 10),
                    bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').grid(row=row, column=0, sticky='w', padx=(0, 8), pady=3)
            
            today_label = tk.Label(counters_grid, text="0", font=('Arial', 10),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, width=10)
            today_label.grid(row=row, column=1, pady=3)
            
            total_label = tk.Label(counters_grid, text="0", font=('Arial', 10),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, width=10)
            total_label.grid(row=row, column=2, pady=3)
            
            self.run_counter_labels[metric_name] = {'today': today_label, 'total': total_label}
            row += 1
        
        # ==================== LIVE FEED ====================
        feed_card = tk.Frame(scrollable_frame, bg=Theme.BG_CARD,
                            highlightbackground=Theme.BORDER, highlightthickness=1)
        feed_card.pack(fill='both', expand=True, padx=12, pady=8)
        
        feed_inner = tk.Frame(feed_card, bg=Theme.BG_CARD)
        feed_inner.pack(fill='both', expand=True, padx=16, pady=12)
        
        # Header
        feed_header = tk.Frame(feed_inner, bg=Theme.BG_CARD)
        feed_header.pack(fill='x', pady=(0, 8))
        
        tk.Label(feed_header, text="📡 LIVE FEED", font=('Arial', 13, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(side='left')
        
        # Filter buttons
        filter_frame = tk.Frame(feed_header, bg=Theme.BG_CARD)
        filter_frame.pack(side='right')
        
        ttk.Button(filter_frame, text="Copy", command=self._run_feed_copy).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="Export", command=self._run_feed_export).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="Clear", command=self._run_feed_clear).pack(side='left')
        
        # Text widget
        self.run_feed_text = tk.Text(feed_inner, height=12, bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                                     font=('Consolas', 9), wrap='word', state='disabled',
                                     highlightbackground=Theme.BORDER, highlightthickness=1)
        self.run_feed_text.pack(fill='both', expand=True)
        
        # Scrollbar для feed
        feed_scrollbar = ttk.Scrollbar(self.run_feed_text, command=self.run_feed_text.yview)
        feed_scrollbar.pack(side='right', fill='y')
        self.run_feed_text.config(yscrollcommand=feed_scrollbar.set)
        
        # ==================== ADVISOR ====================
        advisor_card = tk.Frame(scrollable_frame, bg=Theme.BG_CARD,
                               highlightbackground=Theme.BORDER, highlightthickness=1)
        advisor_card.pack(fill='x', padx=12, pady=(8, 12))
        
        advisor_inner = tk.Frame(advisor_card, bg=Theme.BG_CARD)
        advisor_inner.pack(fill='x', padx=16, pady=12)
        
        tk.Label(advisor_inner, text="💡 ADVISOR", font=('Arial', 13, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor='w', pady=(0, 8))
        
        self.run_advisor_frame = tk.Frame(advisor_inner, bg=Theme.BG_CARD)
        self.run_advisor_frame.pack(fill='x')
        
        self.run_advisor_label = tk.Label(self.run_advisor_frame, 
                                          text="No suggestions. System healthy. ✅",
                                          font=('Arial', 10), bg=Theme.BG_CARD, fg=Theme.SUCCESS,
                                          justify='left', wraplength=700)
        self.run_advisor_label.pack(anchor='w')
        
        return frame
    
    def _create_logs_tab(self):
        """Create logs tab with filters"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Top toolbar
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="📝 System Logs", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        # Filter checkboxes
        filter_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        filter_frame.pack(side='left', padx=8)
        
        self.filter_vars = {}
        for filter_name in ['System', 'Trading', 'GPT', 'Risk', 'MT5']:
            var = tk.BooleanVar(value=True)
            self.filter_vars[filter_name] = var
            cb = ttk.Checkbutton(filter_frame, text=filter_name, variable=var,
                               command=self._apply_log_filters)
            cb.pack(side='left', padx=4)
        
        # Search
        search_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        search_frame.pack(side='left', padx=20)
        
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side='left', padx=(0, 4))
        
        ttk.Button(search_frame, text="Search", command=self._search_logs).pack(side='left', padx=2)
        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side='left')
        
        # Action buttons
        action_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        action_frame.pack(side='right', padx=8)
        
        ttk.Button(action_frame, text="Clear", command=self._clear_logs).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Export", command=self._export_logs).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Copy", command=self._copy_logs).pack(side='left')
        
        # Autoscroll toggle
        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Autoscroll", variable=self.autoscroll_var).pack(side='left', padx=(10, 0))
        
        # Logs text widget
        logs_frame = ttk.Frame(frame, style='Dark.TFrame')
        logs_frame.pack(fill='both', expand=True, padx=8, pady=8)
        
        self.logs_text = scrolledtext.ScrolledText(logs_frame,
                                                   font=('Consolas', 9),
                                                   wrap='word',
                                                   bg=Theme.BG_PANEL,
                                                   fg=Theme.TEXT_PRIMARY,
                                                   insertbackground=Theme.TEXT_PRIMARY,
                                                   relief='flat',
                                                   state='disabled')
        self.logs_text.pack(fill='both', expand=True)
        
        # Configure log tags
        self.logs_text.tag_config('INFO', foreground=Theme.TEXT_PRIMARY)
        self.logs_text.tag_config('WARN', foreground=Theme.WARNING, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('ERROR', foreground=Theme.ERROR, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('GPT', foreground=Theme.INFO, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('TRADE', foreground=Theme.SUCCESS, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('HIDDEN', foreground=Theme.BG_PANEL)  # Hidden logs
        
        # Store all logs for filtering
        self.all_logs = []  # List of (message, level, category) tuples
        
        return frame
    
    def _apply_log_filters(self):
        """Apply log filters and redraw logs"""
        # Get active filters
        active_filters = {k for k, v in self.filter_vars.items() if v.get()}
        
        # Redraw logs
        self.logs_text.config(state='normal')
        self.logs_text.delete('1.0', 'end')
        
        for message, level, category in self.all_logs:
            if category in active_filters:
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_line = f"[{timestamp}] {message}\n"
                
                # Determine tag
                tag = 'INFO'
                if 'ERROR' in level.upper():
                    tag = 'ERROR'
                elif 'WARN' in level.upper():
                    tag = 'WARN'
                elif 'GPT' in message.upper() or 'ai' in message.lower():
                    tag = 'GPT'
                elif any(word in message.upper() for word in ['BUY', 'SELL', 'TRADE', 'POSITION']):
                    tag = 'TRADE'
                
                self.logs_text.insert('end', log_line, tag)
        
        # Autoscroll
        if self.autoscroll_var.get():
            self.logs_text.see('end')
        
        self.logs_text.config(state='disabled')
    
    def _create_ai_tab(self):
        """Create AI Decision tab"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Top toolbar
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="🤖 AI Decision Engine", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        # Refresh button
        ttk.Button(toolbar, text="🔄 Refresh Analysis", command=self._refresh_ai_analysis).pack(side='right', padx=8)
        
        # Main content area with 3 sections
        content = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        content.pack(fill='both', expand=True)
        
        # Configure grid
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=0, minsize=150)  # Active Signal section
        content.grid_rowconfigure(1, weight=0, minsize=120)  # Last Analysis section
        content.grid_rowconfigure(2, weight=1)  # History section (expandable)
        
        # ========== SECTION 1: ACTIVE SIGNAL (Used for Trading) ==========
        active_section = tk.Frame(content, bg=Theme.BG_DARK)
        active_section.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=4, pady=(0, 8))
        
        tk.Label(active_section, text="🎯 Active Signal (Used for Trading)", font=('Arial', 11, 'bold'),
                bg=Theme.BG_DARK, fg=Theme.SUCCESS, anchor='w').pack(fill='x', padx=8, pady=(4, 8))
        
        active_grid = tk.Frame(active_section, bg=Theme.BG_DARK)
        active_grid.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        active_grid.grid_columnconfigure(0, weight=1)
        active_grid.grid_columnconfigure(1, weight=1)
        
        # Active signal card (left)
        active_signal_card = tk.Frame(active_grid, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        active_signal_card.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        
        tk.Label(active_signal_card, text="Signal & Confidence", font=('Arial', 9, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(pady=(8, 4))
        
        self.active_signal_label = tk.Label(active_signal_card, text="NONE", font=('Arial', 18, 'bold'),
                                          bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.active_signal_label.pack(pady=4)
        
        self.active_confidence_label = tk.Label(active_signal_card, text="0%", font=('Arial', 14),
                                               bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.active_confidence_label.pack(pady=(0, 8))
        
        # Active signal details (right)
        active_details_card = tk.Frame(active_grid, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        active_details_card.grid(row=0, column=1, sticky='nsew', padx=(4, 0))
        
        tk.Label(active_details_card, text="Trade Details", font=('Arial', 9, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(pady=(8, 4))
        
        self.active_details_label = tk.Label(active_details_card, text="No active signal\n\nWaiting for GPT decision...",
                                            font=('Arial', 9), bg=Theme.BG_CARD,
                                            fg=Theme.TEXT_SECONDARY, justify='center', wraplength=280)
        self.active_details_label.pack(pady=8, padx=12)
        
        # ========== SECTION 2: LAST GPT ANALYSIS (Latest Response) ==========
        analysis_section = tk.Frame(content, bg=Theme.BG_DARK)
        analysis_section.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=4, pady=(0, 8))
        
        tk.Label(analysis_section, text="🤖 Last GPT Analysis (Latest Response)", font=('Arial', 11, 'bold'),
                bg=Theme.BG_DARK, fg=Theme.ACCENT, anchor='w').pack(fill='x', padx=8, pady=(4, 8))
        
        analysis_grid = tk.Frame(analysis_section, bg=Theme.BG_DARK)
        analysis_grid.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        analysis_grid.grid_columnconfigure(0, weight=1)
        analysis_grid.grid_columnconfigure(1, weight=1)
        
        # Last analysis signal (left)
        last_signal_card = tk.Frame(analysis_grid, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        last_signal_card.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        
        tk.Label(last_signal_card, text="GPT Decision", font=('Arial', 9, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(pady=(8, 4))
        
        self.last_signal_label = tk.Label(last_signal_card, text="HOLD", font=('Arial', 16, 'bold'),
                                          bg=Theme.BG_CARD, fg=Theme.WARNING)
        self.last_signal_label.pack(pady=4)
        
        self.signal_time_label = tk.Label(last_signal_card, text="--:--:--", font=('Arial', 8),
                                          bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.signal_time_label.pack(pady=(0, 8))
        
        # Last analysis confidence (right)
        last_conf_card = tk.Frame(analysis_grid, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        last_conf_card.grid(row=0, column=1, sticky='nsew', padx=(4, 0))
        
        tk.Label(last_conf_card, text="Confidence", font=('Arial', 9, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(pady=(8, 4))
        
        self.confidence_label = tk.Label(last_conf_card, text="0%", font=('Arial', 16, 'bold'),
                                        bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY)
        self.confidence_label.pack(pady=4)
        
        self.recommendation_label = tk.Label(last_conf_card, text="No analysis yet",
                                            font=('Arial', 8), bg=Theme.BG_CARD,
                                            fg=Theme.TEXT_MUTED, wraplength=200, justify='center')
        self.recommendation_label.pack(pady=(0, 8))
        
        # ========== SECTION 3: Analysis History ==========
        history_card = tk.Frame(content, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        history_card.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=4, pady=4)
        
        # Header with toolbar
        header_frame = tk.Frame(history_card, bg=Theme.BG_CARD)
        header_frame.pack(fill='x', padx=8, pady=(8, 4))
        
        tk.Label(header_frame, text="Recent Analysis", font=('Arial', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, anchor='w').pack(side='left')
        
        # Cleanup buttons
        btn_frame = tk.Frame(header_frame, bg=Theme.BG_CARD)
        btn_frame.pack(side='right')
        
        ttk.Button(btn_frame, text="🗑️ Clear Old", 
                  command=self._clear_old_analysis, width=12).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🗑️ Clear All", 
                  command=self._clear_all_analysis, width=12).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🔄 Reload", 
                  command=self._reload_analysis_history, width=10).pack(side='left', padx=2)
        
        # Scrollable text for analysis
        self.analysis_text = scrolledtext.ScrolledText(history_card,
                                                       font=('Consolas', 9),
                                                       wrap='word',
                                                       bg=Theme.BG_PANEL,
                                                       fg=Theme.TEXT_PRIMARY,
                                                       relief='flat',
                                                       state='disabled',
                                                       height=10)
        self.analysis_text.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Load initial history
        self.root.after(500, self._reload_analysis_history)
        
        return frame
    
    def _refresh_ai_analysis(self):
        """Force refresh AI analysis"""
        self.add_log("🔄 Refreshing AI analysis...", "INFO")
        # Trigger scheduler if available
        if AI_AVAILABLE:
            try:
                scheduler = get_scheduler()
                if scheduler and hasattr(scheduler, 'trigger_immediate_analysis'):
                    # Get symbols from PureAITrader
                    try:
                        from src.ai.pure_ai_trader import PureAITrader
                        symbols = getattr(PureAITrader, 'SYMBOLS', ['XAUUSD'])
                        symbol = symbols[0] if symbols else 'XAUUSD'
                    except:
                        symbol = 'XAUUSD'
                    
                    scheduler.trigger_immediate_analysis(symbol=symbol, reason="manual_refresh")
                    self.add_log(f"✅ Analysis refresh requested for {symbol}", "INFO")
                else:
                    self.add_log("⚠️ AI scheduler not available", "WARN")
            except Exception as e:
                self.add_log(f"Failed to refresh analysis: {e}", "ERROR")
    
    def _clear_old_analysis(self):
        """Clear analysis history older than 24 hours"""
        try:
            from pathlib import Path
            from datetime import datetime, timedelta
            
            history_dir = Path("data/ai_analysis")
            if not history_dir.exists():
                self.add_log("📂 No analysis history found", "INFO")
                return
            
            now = datetime.now()
            cutoff_time = now - timedelta(hours=24)
            removed_count = 0
            
            for file in history_dir.glob("analysis_*.json"):
                try:
                    # Parse timestamp from filename: analysis_YYYYMMDD_HHMMSS.json
                    timestamp_str = file.stem.replace("analysis_", "")
                    file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if file_time < cutoff_time:
                        file.unlink()
                        removed_count += 1
                except Exception as e:
                    app_logger.debug(f"Failed to process {file.name}: {e}")
            
            self.add_log(f"🗑️ Cleared {removed_count} old analysis files (>24h)", "INFO")
            self._reload_analysis_history()
        except Exception as e:
            self.add_log(f"❌ Failed to clear old analysis: {e}", "ERROR")
    
    def _clear_all_analysis(self):
        """Clear all analysis history"""
        try:
            from pathlib import Path
            
            history_dir = Path("data/ai_analysis")
            if not history_dir.exists():
                self.add_log("📂 No analysis history found", "INFO")
                return
            
            removed_count = 0
            for file in history_dir.glob("analysis_*.json"):
                try:
                    file.unlink()
                    removed_count += 1
                except Exception as e:
                    app_logger.debug(f"Failed to delete {file.name}: {e}")
            
            self.add_log(f"🗑️ Cleared all {removed_count} analysis files", "INFO")
            self._reload_analysis_history()
        except Exception as e:
            self.add_log(f"❌ Failed to clear analysis: {e}", "ERROR")
    
    def _reload_analysis_history(self, silent=False):
        """Reload and display analysis history"""
        try:
            from pathlib import Path
            import json
            
            history_dir = Path("data/ai_analysis")
            if not history_dir.exists():
                self._update_analysis_text("No analysis history available.")
                if not silent:
                    self.add_log("📂 No analysis history directory", "INFO")
                return
            
            # Get all analysis files sorted by timestamp (newest first)
            files = sorted(history_dir.glob("analysis_*.json"), reverse=True)
            
            if not files:
                self._update_analysis_text("No analysis history available.\n\nAnalysis results will appear here after GPT completes market analysis.")
                return
            
            # Build history text (show last 10)
            history_lines = []
            for i, file in enumerate(files[:10]):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                    
                    timestamp = analysis.get('timestamp', 'N/A')
                    signal = analysis.get('signal', 'HOLD')
                    confidence = analysis.get('confidence', 0)
                    symbol = analysis.get('symbol', 'XAUUSD')
                    
                    decision = analysis.get('decision', {})
                    action = decision.get('action', signal)
                    reasoning = decision.get('reasoning', 'No reasoning')[:100]
                    
                    history_lines.append(f"{'='*60}")
                    history_lines.append(f"[{i+1}] {timestamp}")
                    history_lines.append(f"Symbol: {symbol} | Action: {action} | Confidence: {confidence}%")
                    history_lines.append(f"Reasoning: {reasoning}...")
                    history_lines.append("")
                except Exception as e:
                    app_logger.debug(f"Failed to read {file.name}: {e}")
            
            if history_lines:
                self._update_analysis_text("\n".join(history_lines))
            else:
                self._update_analysis_text("No valid analysis found in history.")
                
            if not silent:
                self.add_log(f"📂 Loaded {len(files)} analysis files (showing last 10)", "INFO")
        except Exception as e:
            self.add_log(f"❌ Failed to reload analysis: {e}", "ERROR")
            app_logger.error(f"[GUI V2] Analysis reload error: {e}")
    
    def _update_analysis_text(self, text: str):
        """Update analysis text widget"""
        try:
            self.analysis_text.config(state='normal')
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, text)
            self.analysis_text.config(state='disabled')
        except Exception as e:
            app_logger.error(f"[GUI V2] Failed to update analysis text: {e}")
    
    def _create_positions_tab(self):
        """Create Positions tab with Treeview"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Top toolbar
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="📊 Open Positions", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        # Position count
        self.positions_count_label = ttk.Label(toolbar, text="Positions: 0",
                                              font=('Arial', 10),
                                              foreground=Theme.TEXT_SECONDARY)
        self.positions_count_label.pack(side='left', padx=10)
        
        # Refresh button
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_positions).pack(side='right', padx=8)
        ttk.Button(toolbar, text="❌ Close All", command=self._close_all_positions).pack(side='right', padx=4)
        
        # Treeview container
        tree_frame = ttk.Frame(frame, style='Dark.TFrame')
        tree_frame.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Scrollbars
        yscrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        yscrollbar.pack(side='right', fill='y')
        
        xscrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        xscrollbar.pack(side='bottom', fill='x')
        
        # Treeview
        columns = ('Ticket', 'Symbol', 'Type', 'Lots', 'Entry', 'Current', 'SL', 'TP', 'PnL', 'Time')
        self.positions_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                          yscrollcommand=yscrollbar.set,
                                          xscrollcommand=xscrollbar.set)
        
        # Configure scrollbars
        yscrollbar.config(command=self.positions_tree.yview)
        xscrollbar.config(command=self.positions_tree.xview)
        
        # Column headings
        self.positions_tree.heading('Ticket', text='Ticket')
        self.positions_tree.heading('Symbol', text='Symbol')
        self.positions_tree.heading('Type', text='Type')
        self.positions_tree.heading('Lots', text='Lots')
        self.positions_tree.heading('Entry', text='Entry Price')
        self.positions_tree.heading('Current', text='Current')
        self.positions_tree.heading('SL', text='Stop Loss')
        self.positions_tree.heading('TP', text='Take Profit')
        self.positions_tree.heading('PnL', text='P&L ($)')
        self.positions_tree.heading('Time', text='Open Time')
        
        # Column widths
        self.positions_tree.column('Ticket', width=80, anchor='center')
        self.positions_tree.column('Symbol', width=80, anchor='center')
        self.positions_tree.column('Type', width=60, anchor='center')
        self.positions_tree.column('Lots', width=60, anchor='center')
        self.positions_tree.column('Entry', width=80, anchor='e')
        self.positions_tree.column('Current', width=80, anchor='e')
        self.positions_tree.column('SL', width=80, anchor='e')
        self.positions_tree.column('TP', width=80, anchor='e')
        self.positions_tree.column('PnL', width=100, anchor='e')
        self.positions_tree.column('Time', width=150, anchor='center')
        
        self.positions_tree.pack(fill='both', expand=True)
        
        # Context menu
        self.positions_menu = tk.Menu(self.positions_tree, tearoff=0)
        self.positions_menu.add_command(label="Close Position", command=self._close_selected_position)
        self.positions_menu.add_command(label="Modify SL/TP", command=self._modify_position)
        self.positions_tree.bind('<Button-3>', self._show_positions_menu)
        
        return frame
    
    def _refresh_positions(self):
        """Refresh positions display"""
        try:
            # Clear existing
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            if not self.mt5_manager.connected:
                return
            
            # Get positions from MT5
            positions = self.mt5_manager.get_open_positions()
            self.positions_count_label.config(text=f"Positions: {len(positions)}")
            
            for pos in positions:
                ticket = pos.get('ticket', 0)
                symbol = pos.get('symbol', '')
                pos_type = 'BUY' if pos.get('type', 0) == 0 else 'SELL'
                lots = pos.get('volume', 0)
                entry = pos.get('price_open', 0)
                current = pos.get('price_current', 0)
                sl = pos.get('sl', 0) or '--'
                tp = pos.get('tp', 0) or '--'
                pnl = pos.get('profit', 0)
                time_str = datetime.fromtimestamp(pos.get('time', 0)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Color code P&L
                tag = 'profit' if pnl >= 0 else 'loss'
                
                self.positions_tree.insert('', 'end', values=(
                    ticket, symbol, pos_type, f"{lots:.2f}",
                    f"{entry:.5f}", f"{current:.5f}",
                    sl if isinstance(sl, str) else f"{sl:.5f}",
                    tp if isinstance(tp, str) else f"{tp:.5f}",
                    f"{pnl:+.2f}", time_str
                ), tags=(tag,))
            
            # Configure tags
            self.positions_tree.tag_configure('profit', foreground=Theme.SUCCESS)
            self.positions_tree.tag_configure('loss', foreground=Theme.ERROR)
            
        except Exception as e:
            app_logger.error(f"Failed to refresh positions: {e}")
    
    def _close_selected_position(self):
        """Close selected position"""
        selection = self.positions_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a position")
            return
        
        item = self.positions_tree.item(selection[0])
        ticket = item['values'][0]
        
        result = messagebox.askyesno("Confirm", f"Close position #{ticket}?")
        if result:
            self.add_log(f"Closing position #{ticket}...", "INFO")
            # Close via bot_manager or MT5
    
    def _close_all_positions(self):
        """Close all positions"""
        result = messagebox.askyesno("Confirm", "Close ALL positions?")
        if result:
            self.add_log("Closing all positions...", "WARN")
    
    def _modify_position(self):
        """Modify position SL/TP"""
        messagebox.showinfo("Info", "Modify position - to be implemented")
    
    def _show_positions_menu(self, event):
        """Show context menu for positions"""
        try:
            self.positions_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.positions_menu.grab_release()
    
    def _create_orders_tab(self):
        """Create Orders/History tab"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Top toolbar with filters
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="📈 Trading History", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        # Period filter
        filter_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        filter_frame.pack(side='left', padx=10)
        
        ttk.Label(filter_frame, text="Period:", foreground=Theme.TEXT_MUTED).pack(side='left', padx=(0, 4))
        self.period_var = tk.StringVar(value='Today')
        period_combo = ttk.Combobox(filter_frame, textvariable=self.period_var,
                                   values=['Today', 'Last 7 days', 'Last 30 days', 'All'],
                                   state='readonly', width=12)
        period_combo.pack(side='left', padx=4)
        period_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_orders())
        
        # Result filter
        ttk.Label(filter_frame, text="Result:", foreground=Theme.TEXT_MUTED).pack(side='left', padx=(10, 4))
        self.result_var = tk.StringVar(value='All')
        result_combo = ttk.Combobox(filter_frame, textvariable=self.result_var,
                                   values=['All', 'Wins', 'Losses'],
                                   state='readonly', width=10)
        result_combo.pack(side='left', padx=4)
        result_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_orders())
        
        # Symbol filter
        ttk.Label(filter_frame, text="Symbol:", foreground=Theme.TEXT_MUTED).pack(side='left', padx=(10, 4))
        self.symbol_var = tk.StringVar(value='All')
        symbol_combo = ttk.Combobox(filter_frame, textvariable=self.symbol_var,
                                   values=['All', 'XAUUSD', 'EURUSD', 'GBPUSD'],
                                   state='readonly', width=10)
        symbol_combo.pack(side='left', padx=4)
        symbol_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_orders())
        
        # Stats display
        stats_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        stats_frame.pack(side='right', padx=8)
        
        self.orders_stats_label = ttk.Label(stats_frame,
                                           text="Total: 0 | Wins: 0 | Losses: 0 | W/R: 0%",
                                           font=('Arial', 9),
                                           foreground=Theme.TEXT_SECONDARY)
        self.orders_stats_label.pack()
        
        # Treeview container
        tree_frame = ttk.Frame(frame, style='Dark.TFrame')
        tree_frame.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Scrollbars
        yscrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        yscrollbar.pack(side='right', fill='y')
        
        xscrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        xscrollbar.pack(side='bottom', fill='x')
        
        # Treeview
        columns = ('Ticket', 'Time', 'Symbol', 'Type', 'Lots', 'Entry', 'Exit', 'SL', 'TP', 'PnL', 'Duration')
        self.orders_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                       yscrollcommand=yscrollbar.set,
                                       xscrollcommand=xscrollbar.set)
        
        yscrollbar.config(command=self.orders_tree.yview)
        xscrollbar.config(command=self.orders_tree.xview)
        
        # Column headings
        for col in columns:
            self.orders_tree.heading(col, text=col)
        
        # Column widths
        self.orders_tree.column('Ticket', width=80, anchor='center')
        self.orders_tree.column('Time', width=140, anchor='center')
        self.orders_tree.column('Symbol', width=80, anchor='center')
        self.orders_tree.column('Type', width=60, anchor='center')
        self.orders_tree.column('Lots', width=60, anchor='center')
        self.orders_tree.column('Entry', width=80, anchor='e')
        self.orders_tree.column('Exit', width=80, anchor='e')
        self.orders_tree.column('SL', width=70, anchor='e')
        self.orders_tree.column('TP', width=70, anchor='e')
        self.orders_tree.column('PnL', width=100, anchor='e')
        self.orders_tree.column('Duration', width=80, anchor='center')
        
        self.orders_tree.pack(fill='both', expand=True)
        
        return frame
    
    def _refresh_orders(self):
        """Refresh orders history with filters"""
        try:
            # Clear existing
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            if not self.mt5_manager.connected:
                return
            
            # Get period dates
            from datetime import timedelta
            period = self.period_var.get()
            
            # Convert period filter to days
            if period == 'Today':
                days = 1
            elif period == 'Last 7 days':
                days = 7
            elif period == 'Last 30 days':
                days = 30
            else:
                days = 365
            
            # Get history from MT5
            history = self.mt5_manager.get_trade_history(days=days)
            
            # Apply filters
            result_filter = self.result_var.get()
            symbol_filter = self.symbol_var.get()
            
            wins = 0
            losses = 0
            total_pnl = 0
            
            for deal in history:
                pnl = deal.get('pnl', 0)
                symbol = deal.get('symbol', '')
                
                # Filter by result
                if result_filter == 'Wins' and pnl <= 0:
                    continue
                if result_filter == 'Losses' and pnl >= 0:
                    continue
                
                # Filter by symbol
                if symbol_filter != 'All' and symbol != symbol_filter:
                    continue
                
                # Update stats
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
                total_pnl += pnl
                
                # Add to tree
                ticket = deal.get('id', 0)
                time_str = f"{deal.get('date', '')} {deal.get('time', '')}"
                deal_type = deal.get('direction', 'BUY')
                lots = deal.get('volume', 0)
                entry = deal.get('price', 0)
                exit_price = deal.get('exit_price', entry)
                sl = '--'  # SL/TP not available in closed deals history
                tp = '--'
                duration = '--'  # Duration not tracked in history
                
                tag = 'win' if pnl >= 0 else 'loss'
                
                self.orders_tree.insert('', 'end', values=(
                    ticket, time_str, symbol, deal_type,
                    f"{lots:.2f}", f"{entry:.5f}", f"{exit_price:.5f}",
                    sl if isinstance(sl, str) else f"{sl:.5f}",
                    tp if isinstance(tp, str) else f"{tp:.5f}",
                    f"{pnl:+.2f}", duration
                ), tags=(tag,))
            
            # Configure tags
            self.orders_tree.tag_configure('win', foreground=Theme.SUCCESS)
            self.orders_tree.tag_configure('loss', foreground=Theme.ERROR)
            
            # Update stats
            total = wins + losses
            winrate = (wins / total * 100) if total > 0 else 0
            self.orders_stats_label.config(
                text=f"Total: {total} | Wins: {wins} | Losses: {losses} | W/R: {winrate:.1f}%"
            )
            
        except Exception as e:
            app_logger.error(f"Failed to refresh orders: {e}")
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    
    def _create_risk_tab(self):
        """Create Risk tab with limits and counters"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # Top toolbar
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="🛡️ Risk Management", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_risk).pack(side='right', padx=8)
        ttk.Button(toolbar, text="🔓 Reset Limits", command=self._reset_risk_limits).pack(side='right', padx=4)
        
        # Main content with 2 columns
        content = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        content.pack(fill='both', expand=True)
        
        # Configure grid
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Get initial values from config
        safety_config = self.trading_config.get('trading', {}).get('safety_limits', {})
        
        # Left column: Daily & Position Limits
        left_col = ttk.Frame(content, style='Dark.TFrame')
        left_col.grid(row=0, column=0, sticky='nsew', padx=4)
        
        # Daily Limits Card
        daily_card = tk.Frame(left_col, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        daily_card.pack(fill='both', expand=True, pady=4)
        
        tk.Label(daily_card, text="Daily Limits", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        # Daily Loss (read from config)
        max_daily_loss = safety_config.get('max_daily_loss', 50.0)
        self._create_risk_row(daily_card, "Max Daily Loss:", f"${max_daily_loss:.2f}", "daily_loss")
        self._create_risk_row(daily_card, "Current Loss:", "$0.00", "current_loss")
        self._create_progress_bar(daily_card, "loss_progress")
        
        tk.Frame(daily_card, bg=Theme.BORDER, height=1).pack(fill='x', padx=12, pady=8)
        
        # Daily Profit (read from config)
        max_daily_profit = safety_config.get('max_daily_profit', 150.0)
        self._create_risk_row(daily_card, "Max Daily Profit:", f"${max_daily_profit:.2f}", "daily_profit")
        self._create_risk_row(daily_card, "Current Profit:", "$0.00", "current_profit")
        self._create_progress_bar(daily_card, "profit_progress")
        
        # Position Limits Card
        pos_card = tk.Frame(left_col, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        pos_card.pack(fill='both', expand=True, pady=4)
        
        tk.Label(pos_card, text="Position Limits", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        max_open_pos = safety_config.get('max_open_positions', 3)
        self._create_risk_row(pos_card, "Max Positions:", str(max_open_pos), "max_positions")
        self._create_risk_row(pos_card, "Open Positions:", "0", "open_positions")
        self._create_risk_row(pos_card, "Max Duration:", "24h", "max_duration")
        
        # Right column: Session & Cooldowns
        right_col = ttk.Frame(content, style='Dark.TFrame')
        right_col.grid(row=0, column=1, sticky='nsew', padx=4)
        
        # Session Limits Card
        session_card = tk.Frame(right_col, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        session_card.pack(fill='both', expand=True, pady=4)
        
        tk.Label(session_card, text="Session Limits", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        max_trades_day = safety_config.get('max_trades_per_day', 15)
        max_trades_hour = safety_config.get('max_trades_per_hour', 5)
        max_losses_row = safety_config.get('max_losses_in_row', 3)
        
        self._create_risk_row(session_card, "Max Trades/Day:", str(max_trades_day), "max_trades_day")
        self._create_risk_row(session_card, "Trades Today:", "0", "trades_today")
        self._create_risk_row(session_card, "Max Trades/Hour:", str(max_trades_hour), "max_trades_hour")
        self._create_risk_row(session_card, "Trades This Hour:", "0", "trades_hour")
        self._create_risk_row(session_card, "Max Losses in Row:", str(max_losses_row), "max_losses_row")
        self._create_risk_row(session_card, "Current Streak:", "0", "current_streak")
        
        # Cooldown & Risk Card
        cooldown_card = tk.Frame(right_col, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        cooldown_card.pack(fill='both', expand=True, pady=4)
        
        tk.Label(cooldown_card, text="Cooldowns & Risk", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        self._create_risk_row(cooldown_card, "After Loss:", "5 min", "cooldown_loss")
        self._create_risk_row(cooldown_card, "After Win:", "2 min", "cooldown_win")
        self._create_risk_row(cooldown_card, "Max Risk/Trade:", "2.0%", "max_risk_trade")
        self._create_risk_row(cooldown_card, "Max Total Risk:", "6.0%", "max_total_risk")
        self._create_risk_row(cooldown_card, "Max Lot Size:", "0.50", "max_lot")
        self._create_risk_row(cooldown_card, "Min Balance:", "$50.00", "min_balance")
        
        return frame
    
    def _create_risk_row(self, parent, label: str, value: str, key: str):
        """Create a risk parameter row"""
        row = tk.Frame(parent, bg=Theme.BG_CARD)
        row.pack(fill='x', padx=12, pady=3)
        
        tk.Label(row, text=label, font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left')
        
        value_label = tk.Label(row, text=value, font=('Arial', 9, 'bold'),
                              bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        value_label.pack(side='right')
        
        # Store reference
        if not hasattr(self, 'risk_labels'):
            self.risk_labels = {}
        self.risk_labels[key] = value_label
    
    def _create_progress_bar(self, parent, key: str):
        """Create a progress bar for risk visualization"""
        canvas = tk.Canvas(parent, height=8, bg=Theme.BG_CARD, highlightthickness=0)
        canvas.pack(fill='x', padx=12, pady=(0, 12))
        
        # Store reference
        if not hasattr(self, 'risk_progress'):
            self.risk_progress = {}
        self.risk_progress[key] = canvas
    
    def _create_ml_tab(self):
        """Create ML training tab"""
        frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        # ========== TOP TOOLBAR ==========
        toolbar = ttk.Frame(frame, style='Dark.TFrame', padding=8)
        toolbar.pack(fill='x', side='top')
        
        ttk.Label(toolbar, text="🧠 ML Training", font=('Arial', 12, 'bold'),
                 foreground=Theme.ACCENT).pack(side='left', padx=(8, 20))
        
        # Control buttons (left side)
        btn_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        btn_frame.pack(side='left', padx=8)
        
        self.ml_load_btn = ttk.Button(btn_frame, text="Load Data", 
                                      command=self._ml_load_data, style='App.TButton')
        self.ml_load_btn.pack(side='left', padx=2)
        
        # Dataset dropdown
        self.ml_dataset_var = tk.StringVar(value="No dataset")
        self.ml_dataset_combo = ttk.Combobox(btn_frame, textvariable=self.ml_dataset_var,
                                            width=25, state='readonly')
        self.ml_dataset_combo['values'] = ["No dataset"]
        self.ml_dataset_combo.pack(side='left', padx=8)
        
        self.ml_train_btn = ttk.Button(btn_frame, text="Start Train",
                                       command=self._ml_start_train, style='App.TButton')
        self.ml_train_btn.pack(side='left', padx=2)
        
        self.ml_pause_btn = ttk.Button(btn_frame, text="Pause",
                                       command=self._ml_pause_train, style='App.TButton', state='disabled')
        self.ml_pause_btn.pack(side='left', padx=2)
        
        self.ml_stop_btn = ttk.Button(btn_frame, text="Stop",
                                      command=self._ml_stop_train, style='App.TButton', state='disabled')
        self.ml_stop_btn.pack(side='left', padx=2)
        
        self.ml_export_btn = ttk.Button(btn_frame, text="Export Model",
                                        command=self._ml_export_model, style='App.TButton')
        self.ml_export_btn.pack(side='left', padx=2)
        
        # Status labels (right side)
        status_frame = ttk.Frame(toolbar, style='Dark.TFrame')
        status_frame.pack(side='right', padx=8)
        
        self.ml_device_label = ttk.Label(status_frame, text="Device: CPU",
                                         font=('Arial', 9), foreground=Theme.TEXT_MUTED)
        self.ml_device_label.pack(side='left', padx=10)
        
        self.ml_update_label = ttk.Label(status_frame, text="Last update: --:--:--",
                                         font=('Arial', 9), foreground=Theme.TEXT_MUTED)
        self.ml_update_label.pack(side='left', padx=10)
        
        self.ml_state_label = ttk.Label(status_frame, text="State: IDLE",
                                        font=('Arial', 9, 'bold'), foreground=Theme.TEXT_MUTED)
        self.ml_state_label.pack(side='left', padx=10)
        
        # ========== MAIN CONTENT ==========
        content = ttk.Frame(frame, style='Dark.TFrame')
        content.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Training Progress Card (top)
        progress_card = tk.Frame(content, bg=Theme.BG_CARD,
                                highlightbackground=Theme.BORDER, highlightthickness=1)
        progress_card.pack(fill='x', pady=(0, 8))
        
        tk.Label(progress_card, text="Training Progress", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        # Epoch + Progress bar + Percent
        prog_container = tk.Frame(progress_card, bg=Theme.BG_CARD)
        prog_container.pack(fill='x', padx=12, pady=(0, 12))
        
        # Epoch label (left)
        self.ml_epoch_label = tk.Label(prog_container, text="Epoch 0 / 50",
                                       font=('Arial', 10, 'bold'),
                                       bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.ml_epoch_label.pack(side='left', padx=(0, 12))
        
        # Progress bar (center, expand)
        prog_bar_frame = tk.Frame(prog_container, bg=Theme.BG_CARD)
        prog_bar_frame.pack(side='left', fill='x', expand=True, padx=(0, 12))
        
        self.ml_progress = ttk.Progressbar(prog_bar_frame, length=400,
                                          mode='determinate', maximum=100)
        self.ml_progress.pack(fill='x')
        
        # Percent label (right)
        self.ml_percent_label = tk.Label(prog_container, text="0%",
                                         font=('Arial', 10, 'bold'),
                                         bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        self.ml_percent_label.pack(side='right')
        
        # Metrics row: Step | ETA | Batch | LR | Checkpoint
        metrics_info_row = tk.Frame(progress_card, bg=Theme.BG_CARD)
        metrics_info_row.pack(fill='x', padx=12, pady=(0, 12))
        
        self.ml_step_label = tk.Label(metrics_info_row, text="Step: 0/0",
                                      font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.ml_step_label.pack(side='left', padx=(0, 20))
        
        self.ml_eta_label = tk.Label(metrics_info_row, text="ETA: --:--:--",
                                     font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.ml_eta_label.pack(side='left', padx=(0, 20))
        
        self.ml_batch_label = tk.Label(metrics_info_row, text="Batch: 128",
                                       font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.ml_batch_label.pack(side='left', padx=(0, 20))
        
        self.ml_lr_label = tk.Label(metrics_info_row, text="LR: 0.0003",
                                    font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.ml_lr_label.pack(side='left', padx=(0, 20))
        
        self.ml_checkpoint_label = tk.Label(metrics_info_row, text="Checkpoint: every 2 epochs",
                                           font=('Arial', 9), bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.ml_checkpoint_label.pack(side='left')
        
        # 4 Metrics cards (horizontal)
        metrics_cards_row = tk.Frame(progress_card, bg=Theme.BG_CARD)
        metrics_cards_row.pack(fill='x', padx=12, pady=(0, 12))
        
        # Train Loss card
        train_loss_card = tk.Frame(metrics_cards_row, bg=Theme.BG_PANEL,
                                   highlightbackground=Theme.BORDER, highlightthickness=1)
        train_loss_card.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        tk.Label(train_loss_card, text="Train Loss", font=('Arial', 9),
                bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED).pack(padx=10, pady=(8, 2))
        self.ml_train_loss_label = tk.Label(train_loss_card, text="0.834",
                                            font=('Arial', 14, 'bold'), bg=Theme.BG_PANEL, fg=Theme.TEXT_PRIMARY)
        self.ml_train_loss_label.pack(padx=10, pady=(2, 8))
        
        # Val Loss card
        val_loss_card = tk.Frame(metrics_cards_row, bg=Theme.BG_PANEL,
                                 highlightbackground=Theme.BORDER, highlightthickness=1)
        val_loss_card.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        tk.Label(val_loss_card, text="Val Loss", font=('Arial', 9),
                bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED).pack(padx=10, pady=(8, 2))
        self.ml_val_loss_label = tk.Label(val_loss_card, text="0.901",
                                          font=('Arial', 14, 'bold'), bg=Theme.BG_PANEL, fg=Theme.TEXT_PRIMARY)
        self.ml_val_loss_label.pack(padx=10, pady=(2, 8))
        
        # F1 card
        f1_card = tk.Frame(metrics_cards_row, bg=Theme.BG_PANEL,
                          highlightbackground=Theme.BORDER, highlightthickness=1)
        f1_card.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        tk.Label(f1_card, text="F1", font=('Arial', 9),
                bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED).pack(padx=10, pady=(8, 2))
        self.ml_f1_label = tk.Label(f1_card, text="0.62",
                                    font=('Arial', 14, 'bold'), bg=Theme.BG_PANEL, fg=Theme.TEXT_PRIMARY)
        self.ml_f1_label.pack(padx=10, pady=(2, 8))
        
        # Overfit card
        overfit_card = tk.Frame(metrics_cards_row, bg=Theme.BG_PANEL,
                               highlightbackground=Theme.BORDER, highlightthickness=1)
        overfit_card.pack(side='left', fill='both', expand=True)
        
        tk.Label(overfit_card, text="Overfit", font=('Arial', 9),
                bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED).pack(padx=10, pady=(8, 2))
        self.ml_overfit_label = tk.Label(overfit_card, text="LOW",
                                         font=('Arial', 14, 'bold'), bg=Theme.BG_PANEL, fg=Theme.SUCCESS)
        self.ml_overfit_label.pack(padx=10, pady=(2, 8))
        
        # Show Plot button (right side)
        plot_btn_frame = tk.Frame(progress_card, bg=Theme.BG_CARD)
        plot_btn_frame.pack(fill='x', padx=12, pady=(0, 12))
        
        ttk.Button(plot_btn_frame, text="Show Plot", command=self._ml_show_plot,
                  style='App.TButton').pack(side='right')
        
        # ========== BOTTOM: TWO COLUMNS ==========
        bottom = ttk.Frame(content, style='Dark.TFrame')
        bottom.pack(fill='both', expand=True)
        
        bottom.grid_rowconfigure(0, weight=1)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=2)
        
        # ===== LEFT: Dataset & Features =====
        left_card = tk.Frame(bottom, bg=Theme.BG_CARD,
                            highlightbackground=Theme.BORDER, highlightthickness=1)
        left_card.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        
        tk.Label(left_card, text="Dataset & Features", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        # Dataset info (grid layout for alignment)
        info_frame = tk.Frame(left_card, bg=Theme.BG_CARD)
        info_frame.pack(fill='x', padx=12, pady=(0, 12))
        info_frame.columnconfigure(1, weight=1)
        
        self._create_info_row_grid(info_frame, 0, "Rows:", "0", "ml_rows")
        self._create_info_row_grid(info_frame, 1, "Features:", "0", "ml_features")
        self._create_info_row_grid(info_frame, 2, "Timeframe:", "M5", "ml_timeframe")
        self._create_info_row_grid(info_frame, 3, "Symbols:", "XAUUSD", "ml_symbols")
        self._create_info_row_grid(info_frame, 4, "Split:", "80 / 20", "ml_split")
        self._create_info_row_grid(info_frame, 5, "NaNs:", "0.12 %", "ml_nans")
        self._create_info_row_grid(info_frame, 6, "Class balance:", "", "ml_class_balance", is_balance=True)
        
        # Separator
        separator = tk.Frame(left_card, bg=Theme.BORDER, height=1)
        separator.pack(fill='x', padx=12, pady=(8, 12))
        
        # Action buttons (2x2 grid with proper spacing)
        action_frame = tk.Frame(left_card, bg=Theme.BG_CARD)
        action_frame.pack(fill='x', padx=12, pady=(0, 12))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        ttk.Button(action_frame, text="Preview", command=self._ml_preview_data,
                  style='App.TButton').grid(row=0, column=0, sticky='ew', padx=(0, 5), pady=(0, 8))
        ttk.Button(action_frame, text="Rebuild Features", command=self._ml_rebuild_features,
                  style='App.TButton').grid(row=0, column=1, sticky='ew', padx=(5, 0), pady=(0, 8))
        
        ttk.Button(action_frame, text="Normalize", command=self._ml_normalize,
                  style='App.TButton').grid(row=1, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(action_frame, text="Split Train/Val", command=self._ml_split_data,
                  style='App.TButton').grid(row=1, column=1, sticky='ew', padx=(5, 0))
        
        # Feature set checkboxes (2 columns, compact)
        tk.Label(left_card, text="Feature Set", font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, anchor='w').pack(fill='x', padx=12, pady=(12, 6))
        
        features_frame = tk.Frame(left_card, bg=Theme.BG_CARD)
        features_frame.pack(fill='x', padx=12, pady=(0, 12))
        features_frame.columnconfigure(0, weight=1)
        features_frame.columnconfigure(1, weight=1)
        
        self.ml_features = {}
        features_list = ['ATR', 'RSI', 'EMA Slope', 'MACD', 'Volume', 'Spread', 'Session']
        for i, feature in enumerate(features_list):
            var = tk.BooleanVar(value=True)
            self.ml_features[feature] = var
            row = i // 2
            col = i % 2
            cb = ttk.Checkbutton(features_frame, text=feature, variable=var)
            cb.grid(row=row, column=col, sticky='w', pady=1, padx=(0, 10))
        
        # ===== RIGHT: ML Logs =====
        right_card = tk.Frame(bottom, bg=Theme.BG_CARD,
                             highlightbackground=Theme.BORDER, highlightthickness=1)
        right_card.grid(row=0, column=1, sticky='nsew', padx=(4, 0))
        
        tk.Label(right_card, text="ML Logs", font=('Arial', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        # Log toolbar
        log_toolbar = tk.Frame(right_card, bg=Theme.BG_CARD)
        log_toolbar.pack(fill='x', padx=12, pady=(0, 8))
        
        # Filters
        filter_frame = tk.Frame(log_toolbar, bg=Theme.BG_CARD)
        filter_frame.pack(side='left')
        
        self.ml_log_filters = {}
        for level in ['INFO', 'TRAIN', 'WARN', 'ERROR']:
            var = tk.BooleanVar(value=True)
            self.ml_log_filters[level] = var
            cb = ttk.Checkbutton(filter_frame, text=level, variable=var,
                                command=self._ml_apply_log_filters)
            cb.pack(side='left', padx=4)
        
        # Buttons
        log_btn_frame = tk.Frame(log_toolbar, bg=Theme.BG_CARD)
        log_btn_frame.pack(side='right')
        
        ttk.Button(log_btn_frame, text="Copy", command=self._ml_copy_logs,
                  style='App.TButton').pack(side='left', padx=2)
        ttk.Button(log_btn_frame, text="Export", command=self._ml_export_logs,
                  style='App.TButton').pack(side='left', padx=2)
        ttk.Button(log_btn_frame, text="Clear", command=self._ml_clear_logs,
                  style='App.TButton').pack(side='left', padx=2)
        
        self.ml_autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_btn_frame, text="Autoscroll",
                       variable=self.ml_autoscroll_var).pack(side='left', padx=(10, 0))
        
        # Logs text widget
        logs_container = tk.Frame(right_card, bg=Theme.BG_CARD)
        logs_container.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        
        self.ml_logs_text = scrolledtext.ScrolledText(logs_container,
                                                      font=('Consolas', 9),
                                                      wrap='word',
                                                      bg=Theme.BG_PANEL,
                                                      fg=Theme.TEXT_PRIMARY,
                                                      insertbackground=Theme.TEXT_PRIMARY,
                                                      relief='flat',
                                                      height=15)
        self.ml_logs_text.pack(fill='both', expand=True)
        
        # Configure tags for log levels
        self.ml_logs_text.tag_config('INFO', foreground=Theme.TEXT_MUTED)
        self.ml_logs_text.tag_config('TRAIN', foreground=Theme.ACCENT)
        self.ml_logs_text.tag_config('WARN', foreground=Theme.WARNING)
        self.ml_logs_text.tag_config('ERROR', foreground=Theme.ERROR)
        
        # Initial log message
        self._ml_add_log("ML Training ready. Load dataset to begin.", "INFO")
        
        return frame
    
    def _create_info_row(self, parent, label: str, value: str, key: str):
        """Create info row for ML dataset (legacy method, use _create_info_row_grid)"""
        row = tk.Frame(parent, bg=Theme.BG_CARD)
        row.pack(fill='x', pady=3)
        
        tk.Label(row, text=label, font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left')
        
        value_label = tk.Label(row, text=value, font=('Arial', 9, 'bold'),
                              bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY)
        value_label.pack(side='right')
        
        # Store reference
        if not hasattr(self, 'ml_info_labels'):
            self.ml_info_labels = {}
        self.ml_info_labels[key] = value_label
    
    def _create_info_row_grid(self, parent, row_idx: int, label: str, value: str, key: str, is_balance: bool = False):
        """Create info row for ML dataset using grid layout for proper alignment"""
        # Label (left, muted)
        tk.Label(parent, text=label, font=('Arial', 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, anchor='w').grid(
                    row=row_idx, column=0, sticky='w', pady=4)
        
        # Initialize storage
        if not hasattr(self, 'ml_info_labels'):
            self.ml_info_labels = {}
        
        # Value (right, bold, aligned)
        if is_balance:
            # Special handling for class balance with colored percentages
            balance_frame = tk.Frame(parent, bg=Theme.BG_CARD)
            balance_frame.grid(row=row_idx, column=1, sticky='e', pady=4)
            
            buy_label = tk.Label(balance_frame, text="BUY 51%", font=('Arial', 9, 'bold'),
                                bg=Theme.BG_CARD, fg='#4a9d7e')  # Subtle green
            buy_label.pack(side='left')
            
            tk.Label(balance_frame, text=" / ", font=('Arial', 9),
                    bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED).pack(side='left')
            
            sell_label = tk.Label(balance_frame, text="SELL 49%", font=('Arial', 9, 'bold'),
                                 bg=Theme.BG_CARD, fg='#c96969')  # Subtle red
            sell_label.pack(side='left')
            
            # Store references for both parts
            self.ml_info_labels[key] = balance_frame
            self.ml_info_labels[f"{key}_buy"] = buy_label
            self.ml_info_labels[f"{key}_sell"] = sell_label
        else:
            value_label = tk.Label(parent, text=value, font=('Arial', 9, 'bold'),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, anchor='e')
            value_label.grid(row=row_idx, column=1, sticky='e', pady=4)
            self.ml_info_labels[key] = value_label
    
    def _refresh_risk(self):
        """Refresh risk limits display"""
        try:
            # Reload config from file (in case settings changed)
            self.trading_config = self._load_yaml_config('config/trading.yaml')
            safety_config = self.trading_config.get('trading', {}).get('safety_limits', {})
            
            # Update labels with actual config values
            if hasattr(self, 'risk_labels'):
                self.risk_labels['daily_loss'].config(text=f"${safety_config.get('max_daily_loss', 50.0):.2f}")
                self.risk_labels['daily_profit'].config(text=f"${safety_config.get('max_daily_profit', 150.0):.2f}")
                self.risk_labels['max_positions'].config(text=str(safety_config.get('max_open_positions', 3)))
                self.risk_labels['max_trades_day'].config(text=str(safety_config.get('max_trades_per_day', 15)))
                self.risk_labels['max_trades_hour'].config(text=str(safety_config.get('max_trades_per_hour', 5)))
                self.risk_labels['max_losses_row'].config(text=str(safety_config.get('max_losses_in_row', 3)))
                
                # Get current values from bot_manager
                stats = self.bot_manager.stats
                self.risk_labels['current_loss'].config(text=f"${abs(min(stats.get('today_pnl', 0), 0)):.2f}")
                self.risk_labels['current_profit'].config(text=f"${max(stats.get('today_pnl', 0), 0):.2f}")
                self.risk_labels['open_positions'].config(text=str(len(stats.get('open_positions', []))))
                self.risk_labels['trades_today'].config(text=str(stats.get('trades', 0)))
            
            self.add_log("🔄 Risk limits refreshed", "INFO")
        except Exception as e:
            app_logger.error(f"Failed to refresh risk: {e}")
    
    def _reset_risk_limits(self):
        """Reset risk protection blocks"""
        result = messagebox.askyesno("Confirm", "Reset all risk protection blocks?")
        if result:
            self.add_log("🔓 Risk limits reset", "WARN")
            # Reset bot_manager protection
    
    # Log methods
    def add_log(self, message: str, level: str = 'INFO'):
        """Add log entry (thread-safe via queue)"""
        self.update_queue.put(('log', message, level))
    
    def _add_log_internal(self, message: str, level: str):
        """Internal method to add log to text widget"""
        # Apply secret sanitizer
        message = self._sanitize_secrets(message)
        
        # Determine category
        category = 'System'
        if any(word in message.upper() for word in ['BUY', 'SELL', 'TRADE', 'POSITION', 'ORDER']):
            category = 'Trading'
        elif 'GPT' in message.upper() or 'AI' in message.upper():
            category = 'GPT'
        elif any(word in message.upper() for word in ['RISK', 'PROTECT', 'LOSS', 'LIMIT']):
            category = 'Risk'
        elif 'MT5' in message.upper():
            category = 'MT5'
        
        # Store in all_logs
        self.all_logs.append((message, level, category))
        
        # Keep only last 1000 logs
        if len(self.all_logs) > 1000:
            self.all_logs.pop(0)
        
        # Check if category is filtered
        if not self.filter_vars.get(category, tk.BooleanVar(value=True)).get():
            return  # Skip filtered logs
        
        self.logs_text.config(state='normal')
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"
        
        # Determine tag
        tag = 'INFO'
        if 'ERROR' in level.upper() or 'error' in message.lower():
            tag = 'ERROR'
        elif 'WARN' in level.upper() or 'warning' in message.lower():
            tag = 'WARN'
        elif 'GPT' in message.upper() or 'ai' in message.lower():
            tag = 'GPT'
        elif 'BUY' in message.upper() or 'SELL' in message.upper() or 'trade' in message.lower():
            tag = 'TRADE'
        
        self.logs_text.insert('end', log_line, tag)
        
        # Limit log size (keep last 500 lines)
        line_count = int(self.logs_text.index('end-1c').split('.')[0])
        if line_count > 500:
            self.logs_text.delete('1.0', f'{line_count - 500}.0')
        
        # Autoscroll
        if self.autoscroll_var.get():
            self.logs_text.see('end')
        
        self.logs_text.config(state='disabled')
    
    def _sanitize_secrets(self, text: str) -> str:
        """Sanitize sensitive information from logs"""
        import re
        
        # API keys (sk-...)
        text = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-***HIDDEN***', text)
        
        # Telegram tokens (digits:alphanumeric)
        text = re.sub(r'\d{8,}:[a-zA-Z0-9_-]{30,}', '***TELEGRAM_TOKEN***', text)
        
        # MT5 passwords (in connection strings)
        text = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\',\s]+', 'password=***', text, flags=re.IGNORECASE)
        
        # Login numbers (8+ digits)
        text = re.sub(r'login["\']?\s*[:=]\s*["\']?(\d{8,})', 'login=***\\1', text, flags=re.IGNORECASE)
        
        return text
    
    def _search_logs(self):
        """Search in logs"""
        query = self.search_entry.get()
        if query:
            # Highlight search results
            self.logs_text.tag_remove('search', '1.0', 'end')
            idx = '1.0'
            while True:
                idx = self.logs_text.search(query, idx, nocase=True, stopindex='end')
                if not idx:
                    break
                endidx = f"{idx}+{len(query)}c"
                self.logs_text.tag_add('search', idx, endidx)
                idx = endidx
            self.logs_text.tag_config('search', background='yellow', foreground='black')
    
    def _clear_search(self):
        """Clear search highlighting"""
        self.logs_text.tag_remove('search', '1.0', 'end')
        self.search_entry.delete(0, 'end')
    
    def _clear_logs(self):
        """Clear all logs"""
        self.logs_text.config(state='normal')
        self.logs_text.delete('1.0', 'end')
        self.logs_text.config(state='disabled')
    
    def _export_logs(self):
        """Export logs to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(defaultextension=".txt",
                                               filetypes=[("Text files", "*.txt")])
        if filename:
            content = self.logs_text.get('1.0', 'end')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Success", f"Logs exported to {filename}")
    
    def _copy_logs(self):
        """Copy logs to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.logs_text.get('1.0', 'end'))
        messagebox.showinfo("Success", "Logs copied to clipboard")
    
    # Setup log handler
    def _setup_log_handler(self):
        """Setup custom log handler to capture logs"""
        # Use logger's GUI callback instead of adding handler
        app_logger.set_gui_callback(self._log_callback)
    
    def _log_callback(self, message: str, level: str):
        """Callback для логгера - добавление логов в GUI"""
        self.update_queue.put(('log', message, level))
    
    # Bot control
    def _start_bot(self):
        """Start bot with Pre-Flight checks"""
        try:
            # ==================== PRE-FLIGHT ACCEPTANCE CHECKS ====================
            from src.core.preflight_checks import get_preflight_checker
            
            self.add_log("=" * 60, "INFO")
            self.add_log("🛫 PRE-FLIGHT CHECKS", "INFO")
            self.add_log("=" * 60, "INFO")
            
            # Run all checks
            checker = get_preflight_checker()
            checks_passed, report = checker.run_all_checks()
            
            if not checks_passed:
                self.add_log("❌ PRE-FLIGHT FAILED - Start blocked", "ERROR")
                
                # Build error message
                errors = []
                for check_name, check_data in report['checks'].items():
                    if not check_data['passed']:
                        error = check_data['details'].get('error', 'Unknown error')
                        errors.append(f"• {check_name.upper()}: {error}")
                
                error_msg = "Pre-Flight checks FAILED:\n\n" + "\n".join(errors)
                error_msg += "\n\nFix issues before starting bot."
                
                messagebox.showerror("Pre-Flight Failed", error_msg)
                return
            
            self.add_log("✅ All pre-flight checks PASSED", "INFO")
            
            # Check LIVE vs DRY_RUN mode
            dry_run = self.trading_config.get('trading', {}).get('dry_run', False)
            
            if not dry_run:
                # LIVE MODE - show warning
                result = messagebox.askyesno(
                    "⚠️ LIVE TRADING MODE",
                    "WARNING: LIVE TRADING IS ENABLED!\n\n"
                    "Bot will execute REAL trades with REAL money.\n\n"
                    "Are you sure you want to continue?",
                    icon='warning'
                )
                if not result:
                    self.add_log("⏸️ Start cancelled by user (LIVE mode warning)", "WARN")
                    return
                
                self.add_log("🔴 LIVE TRADING MODE CONFIRMED", "WARN")
            else:
                self.add_log("🟢 DRY_RUN MODE (SIMULATED)", "INFO")
            
            # Export effective config to run folder
            run_session = get_run_session_manager()
            if run_session.run_dir:
                effective_config = self.config_manager.get_effective_config()
                run_session.save_run_config(effective_config, report)
                self.add_log(f"✅ Config saved to {run_session.run_dir}", "INFO")
            
            self.add_log("=" * 60, "INFO")
            
            # ==================== NORMAL START SEQUENCE ====================
            self.add_log("🚀 Starting bot...", "INFO")
            
            # Check if trading is enabled in config
            trading_enabled = self.trading_config.get('trading', {}).get('enabled', True)
            if not trading_enabled:
                self.add_log("⚠️ Trading is DISABLED in settings", "WARN")
                messagebox.showwarning(
                    "Trading Disabled", 
                    "Trading is currently disabled in settings.\n\n"
                    "Go to Settings → Trading tab and enable 'Trading Enabled' checkbox."
                )
                return
            
            # Check MT5 connection
            if not self.mt5_manager.connected:
                self.add_log("⚠️ Connecting to MT5...", "WARN")
                
                # Load MT5 credentials from config
                mt5_config = self._load_yaml_config('config/mt5.yaml')
                mt5_conn = mt5_config.get('mt5', {}).get('connection', {})
                
                login = mt5_conn.get('login')
                password = mt5_conn.get('password')
                server = mt5_conn.get('server')
                
                if not login or not password or not server:
                    self.add_log("❌ MT5 credentials not configured", "ERROR")
                    messagebox.showerror("Error", "MT5 credentials not found. Please configure in MT5 Settings.")
                    return
                
                # Загрузить путь к терминалу если указан
                terminal_path = mt5_conn.get('path', '')
                
                success, msg = self.mt5_manager.connect(login, password, server, terminal_path)
                if not success:
                    self.add_log(f"❌ Failed to connect to MT5: {msg}", "ERROR")
                    # Многострочное сообщение с подробностями
                    messagebox.showerror("MT5 Connection Error", msg)
                    return
            
            # Start run session (for 5-day production runs)
            run_session = get_run_session_manager()
            if not run_session.current_run or run_session.current_run.status != "ACTIVE":
                days = 5  # Default 5-day run
                run_session.start_new_run(days=days)
                self.add_log(f"✅ Run session started: {run_session.current_run.run_id}", "INFO")
                
                # Save effective config
                effective_config = self.config_manager.get_effective_config()
                run_session.save_run_config(effective_config, report)
                self.add_log(f"✅ Config exported to: {run_session.run_dir}/run_effective_config_start.yaml", "INFO")
            
            # Start bot manager
            success = self.bot_manager.start(
                mode='demo',
                trading_mode='strategy',
                bot_queue=self.bot_queue  # Pass bot_queue for event-driven updates
            )
            
            if success:
                self.add_log("✅ Bot started successfully", "INFO")
                self.status_bar.update_trading_status(True)
                self.control_panel.update_trading_status(True)
                self.control_panel.is_running = True
                
                # Update bot status card
                self.bot_queue.put({'type': 'status', 'status': 'RUNNING'})
                self.bot_queue.put({'type': 'signal', 'signal': 'NONE'})
                self.bot_queue.put({'type': 'timer', 'seconds': 1})
                
                # Start trading loop in background thread
                self.trading_stop_event.clear()
                self.trading_thread = threading.Thread(target=self._run_trading_loop, daemon=True)
                self.trading_thread.start()
                app_logger.info("[GUI V2] Trading loop started")
            else:
                self.add_log("❌ Failed to start bot", "ERROR")
                messagebox.showerror("Error", "Failed to start bot")
        except Exception as e:
            self.add_log(f"❌ Error starting bot: {e}", "ERROR")
            app_logger.error(f"Failed to start bot: {e}")
    
    def _stop_bot(self):
        """Stop bot"""
        try:
            self.add_log("⏸️ Stopping bot...", "INFO")
            
            # Stop simulation
            self.bot_sim_running = False
            
            # Stop trading loop
            self.trading_stop_event.set()
            if self.trading_thread and self.trading_thread.is_alive():
                app_logger.info("[GUI V2] Waiting for trading loop to stop...")
                self.trading_thread.join(timeout=2)
            
            self.bot_manager.stop()  # Метод называется stop(), не stop_bot()
            self.add_log("✅ Bot stopped", "INFO")
            self.status_bar.update_trading_status(False)
            self.control_panel.update_trading_status(False)
            self.control_panel.is_running = False
            
            # Update bot status card
            self.bot_queue.put({'type': 'status', 'status': 'IDLE'})
            self.bot_queue.put({'type': 'signal', 'signal': 'NONE'})
            self.bot_queue.put({'type': 'block', 'reason': ''})
            self.bot_queue.put({'type': 'timer', 'seconds': 0})
            
            # Reset all pipeline steps
            for step in ['data', 'signal', 'gpt', 'risk', 'order']:
                self.bot_queue.put({'type': 'pipeline', 'step': step, 'state': 'IDLE'})
        except Exception as e:
            self.add_log(f"❌ Error stopping bot: {e}", "ERROR")
            app_logger.error(f"Failed to stop bot: {e}")
    
    def _run_trading_loop(self):
        """Main trading loop - calls check_signals periodically"""
        import time
        
        try:
            app_logger.info("[TRADING LOOP] Starting...")
            self.add_log("🔄 Trading loop started", "INFO")
            
            # Wait for LiveTrader initialization
            trader = None
            max_wait = 10  # 10 seconds max
            for i in range(max_wait * 10):
                if hasattr(self.bot_manager, 'live_trader') and self.bot_manager.live_trader:
                    trader = self.bot_manager.live_trader
                    break
                time.sleep(0.1)
                if self.trading_stop_event.is_set():
                    app_logger.info("[TRADING LOOP] Stopped before LiveTrader init")
                    return
            
            if not trader:
                app_logger.error("[TRADING LOOP] LiveTrader not initialized after 10s")
                self.root.after(0, lambda: self.add_log("❌ LiveTrader initialization timeout", "ERROR"))
                return
            
            app_logger.info("[TRADING LOOP] LiveTrader ready")
            self.root.after(0, lambda: self.add_log("✅ LiveTrader ready", "INFO"))
            
            # Start AI Scheduler if available
            if AI_AVAILABLE:
                try:
                    scheduler = get_scheduler()
                    if scheduler:
                        # Initialize scheduler with trader's components
                        scheduler = init_scheduler(
                            executor=trader.executor,
                            signal_manager=trader.ai_signal_manager,
                            rejected_logger=trader.rejected_logger
                        )
                        scheduler.start()
                        app_logger.info("[TRADING LOOP] AI Scheduler started")
                        self.root.after(0, lambda: self.add_log("🤖 AI Scheduler started", "INFO"))
                        
                        # Set references for auto-requery
                        trader.analyst_scheduler = scheduler
                        if trader.ai_signal_manager:
                            trader.ai_signal_manager.set_scheduler(scheduler)
                            trader.ai_signal_manager.set_executor(trader.executor)
                        
                        # Request initial analysis
                        try:
                            from src.ai.pure_ai_trader import PureAITrader
                            symbols = getattr(PureAITrader, 'SYMBOLS', ['XAUUSD'])
                            for symbol in symbols:
                                scheduler.trigger_immediate_analysis(
                                    symbol=symbol,
                                    reason="Bot started - initial analysis"
                                )
                            app_logger.info(f"[TRADING LOOP] Requested initial analysis for {symbols}")
                            self.root.after(0, lambda: self.add_log(f"🔍 Requesting AI analysis for {', '.join(symbols)}", "INFO"))
                        except Exception as e:
                            app_logger.error(f"[TRADING LOOP] Failed to request initial analysis: {e}")
                except Exception as e:
                    app_logger.error(f"[TRADING LOOP] Failed to start AI Scheduler: {e}")
                    self.root.after(0, lambda: self.add_log(f"⚠️ AI Scheduler error: {e}", "WARN"))
            
            # Main loop
            check_interval = trader.get_check_interval() if hasattr(trader, 'get_check_interval') else 3
            check_interval = int(check_interval)  # Convert to int for range()
            app_logger.info(f"[TRADING LOOP] Check interval: {check_interval}s")
            
            # Counter for periodic MT5 history sync (every 60 seconds)
            sync_counter = 0
            sync_interval = 20  # 20 iterations * 3 sec = 60 sec
            
            while not self.trading_stop_event.is_set():
                try:
                    # Update bot status
                    self.bot_queue.put({'type': 'status', 'status': 'WAITING'})
                    
                    # Countdown timer — show main-loop countdown or AI-Scheduler wait, whichever is larger
                    try:
                        _sched = get_scheduler()
                        _sched_remaining = int(getattr(_sched, '_countdown_remaining', 0)) if _sched else 0
                    except Exception:
                        _sched_remaining = 0

                    for remaining in range(check_interval, 0, -1):
                        if self.trading_stop_event.is_set():
                            break
                        # While a trade is open (TRADING status), hide re-analysis countdown.
                        # The countdown only makes sense when waiting to re-analyze after close.
                        _trading = self.bot_state.get('status') == 'TRADING'
                        if _trading:
                            self.bot_queue.put({'type': 'timer', 'seconds': 0})
                            time.sleep(1)
                            continue
                        # Prefer showing the longer AI-Scheduler countdown over the short main-loop tick
                        try:
                            _sched = get_scheduler()
                            _cur_sched = int(getattr(_sched, '_countdown_remaining', 0)) if _sched else 0
                        except Exception:
                            _cur_sched = 0
                        display_secs = _cur_sched if _cur_sched > remaining else remaining
                        self.bot_queue.put({'type': 'timer', 'seconds': display_secs})
                        time.sleep(1)
                    
                    if self.trading_stop_event.is_set():
                        break
                    
                    # Check signals
                    self.bot_queue.put({'type': 'pipeline', 'step': 'data', 'state': 'ACTIVE'})
                    self.bot_queue.put({'type': 'status', 'status': 'ANALYZING'})
                    
                    app_logger.debug("[TRADING LOOP] Checking signals...")
                    signals = trader.check_signals()
                    
                    self.bot_queue.put({'type': 'pipeline', 'step': 'data', 'state': 'SUCCESS'})
                    
                    if signals:
                        app_logger.info(f"[TRADING LOOP] Found {len(signals)} signals")
                        # Signals will be processed by trader internally
                    
                    # Check trailing stops
                    if hasattr(trader, 'check_trailing_stop'):
                        trader.check_trailing_stop()
                    
                    # Check closed positions
                    if hasattr(trader, 'check_closed_positions'):
                        trader.check_closed_positions()
                    
                    # Periodic sync with MT5 history (every ~60 seconds)
                    sync_counter += 1
                    if sync_counter >= sync_interval:
                        sync_counter = 0
                        if self.bot_manager:
                            try:
                                app_logger.debug("[TRADING LOOP] Syncing trade history from MT5...")
                                self.bot_manager._sync_with_mt5()
                            except Exception as sync_err:
                                app_logger.error(f"[TRADING LOOP] MT5 sync failed: {sync_err}")
                    
                    # Cleanup expired AI signals
                    if trader.ai_signal_manager:
                        has_positions = False
                        if self.mt5_manager and self.mt5_manager.connected:
                            positions = self.mt5_manager.get_open_positions()
                            has_positions = len(positions) > 0
                        
                        if not has_positions:
                            trader.ai_signal_manager._cleanup_expired_signals()
                    
                    # Reset pipeline
                    self.bot_queue.put({'type': 'pipeline', 'step': 'data', 'state': 'IDLE'})
                    
                except Exception as e:
                    app_logger.error(f"[TRADING LOOP] Error in iteration: {e}")
                    self.bot_queue.put({'type': 'status', 'status': 'ERROR'})
                    self.root.after(0, lambda err=str(e): self.add_log(f"❌ Trading loop error: {err}", "ERROR"))
                    time.sleep(10)
            
            app_logger.info("[TRADING LOOP] Stopped")
            self.root.after(0, lambda: self.add_log("⏸️ Trading loop stopped", "INFO"))
            
        except Exception as e:
            app_logger.error(f"[TRADING LOOP] Fatal error: {e}")
            self.root.after(0, lambda err=str(e): self.add_log(f"❌ Trading loop crashed: {err}", "ERROR"))
    
    def _open_settings(self):
        """Open settings dialog (модальное окно)"""
        if SETTINGS_AVAILABLE:
            def on_save(data):
                # Reload configs after settings change
                self.trading_config = self._load_yaml_config('config/trading.yaml')
                self.ai_config = self._load_yaml_config('config/ai.yaml')
                
                # Update trading status from reloaded config
                trading_enabled = self.trading_config.get('trading', {}).get('enabled', True)
                self.status_bar.update_trading_status(trading_enabled)
                self.control_panel.update_trading_status(trading_enabled)
                
                self.add_log("⚙️ Settings updated", "INFO")
            
            SettingsDialog(self.root, title="Settings", on_save=on_save)
        else:
            messagebox.showinfo("Info", "Settings dialog not available")
    
    def _show_effective_config(self):
        """Show effective runtime configuration dialog"""
        try:
            from src.gui.dialogs_v2 import EffectiveConfigDialog
            EffectiveConfigDialog(self.root, title="🔍 Effective Configuration")
        except Exception as e:
            app_logger.error(f"[EFFECTIVE CONFIG] Failed to open dialog: {e}")
            messagebox.showerror("Error", f"Failed to open effective config dialog:\n{e}")
    
    def _explain_last_decision(self):
        """Show last trading decision explanation dialog"""
        try:
            from src.gui.dialogs_v2 import ExplainLastDecisionDialog
            ExplainLastDecisionDialog(self.root, title="💬 Explain Last Decision")
        except Exception as e:
            app_logger.error(f"[EXPLAIN DECISION] Failed to open dialog: {e}")
            messagebox.showerror("Error", f"Failed to open decision dialog:\n{e}")
    
    def _open_mt5_settings(self):
        """Open MT5 settings (модальное окно с live update)"""
        if SETTINGS_AVAILABLE:
            MT5SettingsDialog(
                self.root, 
                mt5_manager=self.mt5_manager,
                status_bar=self.status_bar,
                title="MT5 Settings"
            )
        else:
            messagebox.showwarning("Warning", "MT5 settings dialog not available")
    
    def _test_gpt(self):
        """Test GPT connection"""
        self.add_log("🧪 Testing GPT connection...", "INFO")
        
        def test_thread():
            try:
                if AI_AVAILABLE:
                    scheduler = get_scheduler()
                    if scheduler and scheduler.analyst:
                        test_msg = "Hello GPT, this is a test message."
                        # Simple test - don't actually call API
                        self.update_queue.put(('log', "✅ GPT modules loaded", "INFO"))
                    else:
                        self.update_queue.put(('log', "⚠️ GPT analyst not initialized", "WARN"))
                else:
                    self.update_queue.put(('log', "❌ AI modules not available", "ERROR"))
            except Exception as e:
                self.update_queue.put(('log', f"❌ GPT test failed: {e}", "ERROR"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    # Update loops
    def _process_queue(self):
        """Process update queue (runs in main thread)"""
        try:
            while not self.update_queue.empty():
                item = self.update_queue.get_nowait()
                if item[0] == 'log':
                    _, message, level = item
                    self._add_log_internal(message, level)
        except Exception as e:
            app_logger.error(f"[GUI V2] Queue processing error: {e}")
        finally:
            self.root.after(100, self._process_queue)
    
    def _update_mt5_data(self):
        """Update MT5 connection status and price every second"""
        try:
            # Check MT5 connection
            is_connected = self.mt5_manager.connected
            self.status_bar.update_mt5_status(is_connected)
            
            if is_connected:
                # Get XAUUSD price
                price = self.mt5_manager.get_symbol_price('XAUUSD')
                if price:
                    self.status_bar.update_price(price)
        except Exception as e:
            app_logger.error(f"[GUI V2] MT5 data update error: {e}")
        finally:
            self.root.after(1000, self._update_mt5_data)
    
    def _update_stats(self):
        """Update statistics every 3 seconds"""
        try:
            # Check MT5 first and update bot_manager stats
            if self.mt5_manager.connected:
                # Trigger bot_manager to update from MT5
                if hasattr(self.bot_manager, '_update_stats_from_mt5'):
                    self.bot_manager._update_stats_from_mt5()
            
            # Get stats from bot_manager (single source of truth)
            balance = self.bot_manager.stats.get('balance', 0.0)
            today_pnl = self.bot_manager.stats.get('today_pnl', 0.0)
            total_pnl = self.bot_manager.stats.get('total_pnl', 0.0)
            
            # Calculate trades and winrate
            trades = self.bot_manager.stats.get('trades', 0)
            wins = self.bot_manager.stats.get('wins', 0)
            losses = self.bot_manager.stats.get('losses', 0)
            winrate = (wins / trades * 100) if trades > 0 else 0.0
            
            # Update control panel
            self.control_panel.update_stats(balance, today_pnl, total_pnl, trades, winrate)
        except Exception as e:
            app_logger.error(f"[GUI V2] Stats update error: {e}")
        finally:
            self.root.after(3000, self._update_stats)
    
    def _update_positions_loop(self):
        """Update positions and orders every 5 seconds"""
        try:
            if hasattr(self, 'positions_tree'):
                self._refresh_positions()
            if hasattr(self, 'orders_tree'):
                self._refresh_orders()
        except Exception as e:
            app_logger.error(f"[GUI V2] Positions update error: {e}")
        finally:
            self.root.after(5000, self._update_positions_loop)
    
    def _update_ai_data(self):
        """Update AI decision tab from bot_state (SINGLE SOURCE OF TRUTH)"""
        try:
            if hasattr(self, 'active_signal_label'):
                # ========== UPDATE ACTIVE SIGNAL (Used for Trading) ==========
                active_signal = self.bot_state.get('active_signal')
                
                if active_signal:
                    # Active signal exists
                    action = active_signal.get('action', 'NONE')
                    confidence = active_signal.get('confidence', 0)
                    symbol = active_signal.get('symbol', 'XAUUSD')
                    entry = active_signal.get('entry_price', 0)
                    sl = active_signal.get('stop_loss', 0)
                    tp = active_signal.get('take_profit', 0)
                    signal_id_short = active_signal.get('signal_id_short', 'N/A')
                    ticket = active_signal.get('ticket')
                    status = active_signal.get('status', 'pending')
                    
                    # Update signal & confidence
                    signal_color = Theme.SUCCESS if action == 'BUY' else Theme.ERROR
                    self.active_signal_label.config(text=action, fg=signal_color)
                    self.active_confidence_label.config(text=f"{confidence}%", fg=signal_color)
                    
                    # Update details
                    details = f"Symbol: {symbol}\n"
                    details += f"Entry: {entry:.2f}\n"
                    details += f"SL: {sl:.2f} | TP: {tp:.2f}\n"
                    details += f"ID: {signal_id_short}"
                    if ticket:
                        details += f"\nTicket: {ticket}"
                    details += f"\nStatus: {status.upper()}"
                    
                    self.active_details_label.config(text=details, fg=Theme.TEXT_PRIMARY)
                else:
                    # No active signal
                    self.active_signal_label.config(text="NONE", fg=Theme.TEXT_MUTED)
                    self.active_confidence_label.config(text="0%", fg=Theme.TEXT_MUTED)
                    self.active_details_label.config(
                        text="No active signal\n\nWaiting for GPT decision...",
                        fg=Theme.TEXT_SECONDARY
                    )
                
                # ========== UPDATE LAST GPT ANALYSIS (Latest Response) ==========
                last_analysis = self.bot_state.get('last_analysis')
                
                if last_analysis:
                    # Last analysis exists
                    action = last_analysis.get('action', 'HOLD')
                    confidence = last_analysis.get('confidence', 0)
                    timestamp = last_analysis.get('timestamp', '')
                    reasoning = last_analysis.get('reasoning', 'No reasoning')
                    
                    # Format timestamp
                    if timestamp:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp)
                            time_str = dt.strftime("%H:%M:%S")
                        except:
                            time_str = timestamp
                    else:
                        time_str = "--:--:--"
                    
                    # Update UI
                    if action == 'BUY':
                        signal_color = Theme.SUCCESS
                    elif action == 'SELL':
                        signal_color = Theme.ERROR
                    else:
                        signal_color = Theme.WARNING
                    
                    self.last_signal_label.config(text=action, fg=signal_color)
                    self.confidence_label.config(text=f"{confidence}%", fg=signal_color)
                    self.signal_time_label.config(text=time_str)
                    self.recommendation_label.config(text=reasoning[:80] + "..." if len(reasoning) > 80 else reasoning)
                else:
                    # No analysis yet
                    self.last_signal_label.config(text="HOLD", fg=Theme.WARNING)
                    self.confidence_label.config(text="0%", fg=Theme.TEXT_MUTED)
                    self.signal_time_label.config(text="--:--:--")
                    self.recommendation_label.config(text="No analysis yet")
                    
        except Exception as e:
            app_logger.error(f"[GUI V2] AI data update error: {e}")
        finally:
            self.root.after(10000, self._update_ai_data)
    
    def _update_analysis_history_loop(self):
        """Auto-refresh analysis history every 30 seconds"""
        try:
            if hasattr(self, 'analysis_text'):
                self._reload_analysis_history(silent=True)
        except Exception as e:
            app_logger.error(f"[GUI V2] Analysis history update error: {e}")
        finally:
            self.root.after(30000, self._update_analysis_history_loop)  # Every 30 seconds
    
    def run(self):
        """Run the application"""
        self.add_log("=== BAZA Trading Bot V2 Started ===", "INFO")
        self.add_log("UI refactored with modern design", "INFO")
        
        # Set close protocol for cleanup
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.root.mainloop()
    
    # ==================== ML METHODS ====================
    def _poll_ml_queue(self):
        """Poll ML queue for training updates"""
        try:
            while not self.ml_queue.empty():
                event = self.ml_queue.get_nowait()
                self._handle_ml_event(event)
        except Exception as e:
            app_logger.error(f"[ML] Queue poll error: {e}")
        finally:
            # Schedule next poll
            self.root.after(100, self._poll_ml_queue)
    
    def _handle_ml_event(self, event: dict):
        """Handle ML training event"""
        event_type = event.get('type')
        
        if event_type == 'state':
            state = event.get('value', 'IDLE')
            self.ml_state['status'] = state
            self._ml_update_state(state)
            
        elif event_type == 'progress':
            self.ml_state['epoch'] = event.get('epoch', 0)
            self.ml_state['epochs'] = event.get('epochs', 50)
            self.ml_state['step'] = event.get('step', 0)
            self.ml_state['steps_total'] = event.get('steps_total', 0)
            self._ml_update_progress(event)
            
        elif event_type == 'metrics':
            self._ml_update_metrics(event)
            
        elif event_type == 'log':
            level = event.get('level', 'INFO')
            msg = event.get('msg', '')
            self._ml_add_log(msg, level)
            
        elif event_type == 'error':
            msg = event.get('msg', 'Unknown error')
            self._ml_add_log(f"ERROR: {msg}", 'ERROR')
            self.ml_state['status'] = 'ERROR'
            self._ml_update_state('ERROR')
            
        elif event_type == 'done':
            model_path = event.get('model_path', '')
            self._ml_add_log(f"Training completed! Model saved: {model_path}", 'INFO')
            self.ml_state['status'] = 'IDLE'
            self._ml_update_state('IDLE')
    
    def _ml_update_state(self, state: str):
        """Update ML state label and buttons"""
        colors = {
            'IDLE': Theme.TEXT_MUTED,
            'TRAINING': Theme.SUCCESS,
            'PAUSED': Theme.WARNING,
            'ERROR': Theme.ERROR
        }
        self.ml_state_label.configure(text=f"State: {state}",
                                      foreground=colors.get(state, Theme.TEXT_MUTED))
        
        # Update buttons
        if state == 'TRAINING':
            self.ml_train_btn.configure(state='disabled')
            self.ml_pause_btn.configure(state='normal')
            self.ml_stop_btn.configure(state='normal')
        elif state == 'PAUSED':
            self.ml_train_btn.configure(text='Resume', state='normal')
            self.ml_pause_btn.configure(state='disabled')
            self.ml_stop_btn.configure(state='normal')
        else:  # IDLE or ERROR
            self.ml_train_btn.configure(text='Start Train', state='normal')
            self.ml_pause_btn.configure(state='disabled')
            self.ml_stop_btn.configure(state='disabled')
        
        # Update timestamp
        self.ml_state['last_update'] = datetime.now().strftime('%H:%M:%S')
        self.ml_update_label.configure(text=f"Last update: {self.ml_state['last_update']}")
    
    def _ml_update_progress(self, event: dict):
        """Update progress bar and labels"""
        epoch = event.get('epoch', 0)
        epochs = event.get('epochs', 50)
        step = event.get('step', 0)
        steps_total = event.get('steps_total', 0)
        eta_sec = event.get('eta_sec', 0)
        
        # Update epoch label
        self.ml_epoch_label.configure(text=f"Epoch {epoch} / {epochs}")
        
        # Update progress bar and percent
        if epochs > 0:
            progress = (epoch / epochs) * 100
            self.ml_progress['value'] = progress
            self.ml_percent_label.configure(text=f"{int(progress)}%")
        else:
            self.ml_progress['value'] = 0
            self.ml_percent_label.configure(text="0%")
        
        # Update step label
        self.ml_step_label.configure(text=f"Step: {step:,}/{steps_total:,}")
        
        # Update ETA
        if eta_sec > 0:
            hours = eta_sec // 3600
            minutes = (eta_sec % 3600) // 60
            seconds = eta_sec % 60
            self.ml_eta_label.configure(text=f"ETA: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.ml_eta_label.configure(text="ETA: --:--:--")
    
    def _ml_update_metrics(self, event: dict):
        """Update metrics display (4 separate cards)"""
        train_loss = event.get('train_loss', 0)
        val_loss = event.get('val_loss', 0)
        f1 = event.get('f1', 0)
        overfit = event.get('overfit', 'LOW')
        
        # Update each metric card
        self.ml_train_loss_label.configure(text=f"{train_loss:.3f}")
        self.ml_val_loss_label.configure(text=f"{val_loss:.3f}")
        self.ml_f1_label.configure(text=f"{f1:.2f}")
        
        # Overfit color
        overfit_colors = {
            'LOW': Theme.SUCCESS,
            'MED': Theme.WARNING,
            'HIGH': Theme.ERROR
        }
        self.ml_overfit_label.configure(text=overfit,
                                        foreground=overfit_colors.get(overfit, Theme.TEXT_MUTED))
    
    def _ml_add_log(self, msg: str, level: str = 'INFO'):
        """Add log to ML logs text widget"""
        timestamp = datetime.now().strftime('[%H:%M:%S]')
        full_msg = f"{timestamp} [{level}] {msg}\n"
        
        self.ml_logs_text.insert('end', full_msg, level)
        
        if self.ml_autoscroll_var.get():
            self.ml_logs_text.see('end')
    
    def _ml_apply_log_filters(self):
        """Apply ML log filters (stub for now)"""
        pass
    
    def _ml_copy_logs(self):
        """Copy ML logs to clipboard"""
        try:
            content = self.ml_logs_text.get('1.0', 'end-1c')
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self._ml_add_log("Logs copied to clipboard", "INFO")
        except Exception as e:
            self._ml_add_log(f"Failed to copy logs: {e}", "ERROR")
    
    def _ml_export_logs(self):
        """Export ML logs to file"""
        try:
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filepath:
                content = self.ml_logs_text.get('1.0', 'end-1c')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._ml_add_log(f"Logs exported to {filepath}", "INFO")
        except Exception as e:
            self._ml_add_log(f"Failed to export logs: {e}", "ERROR")
    
    def _ml_clear_logs(self):
        """Clear ML logs"""
        self.ml_logs_text.delete('1.0', 'end')
        self._ml_add_log("Logs cleared", "INFO")
    
    def _ml_load_data(self):
        """Load dataset for training"""
        try:
            from tkinter import filedialog
            filepath = filedialog.askopenfilename(
                title="Select Dataset",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if not filepath:
                return
            
            # Quick stats using pandas
            try:
                import pandas as pd
                df = pd.read_csv(filepath, nrows=5)  # Quick peek
                full_df = pd.read_csv(filepath)
                rows = len(full_df)
                features = len(full_df.columns)
                
                # Update dataset info
                dataset_name = Path(filepath).name
                self.ml_dataset_var.set(dataset_name)
                self.ml_state['dataset'] = filepath
                
                # Update info labels
                if hasattr(self, 'ml_info_labels'):
                    self.ml_info_labels['ml_rows'].configure(text=f"{rows:,}")
                    self.ml_info_labels['ml_features'].configure(text=str(features))
                
                self._ml_add_log(f"Dataset loaded: {dataset_name}", "INFO")
                self._ml_add_log(f"Rows: {rows:,}, Features: {features}", "INFO")
                
            except ImportError:
                # Fallback without pandas
                dataset_name = Path(filepath).name
                self.ml_dataset_var.set(dataset_name)
                self.ml_state['dataset'] = filepath
                self._ml_add_log(f"Dataset loaded: {dataset_name}", "INFO")
                self._ml_add_log("Install pandas for detailed stats: pip install pandas", "WARN")
                
        except Exception as e:
            self._ml_add_log(f"Failed to load dataset: {e}", "ERROR")
    
    def _ml_start_train(self):
        """Start ML training (MVP simulation)"""
        if self.ml_state['status'] == 'TRAINING':
            return
        
        if not self.ml_state.get('dataset'):
            messagebox.showwarning("No Dataset", "Please load a dataset first")
            return
        
        # Check if resuming from pause
        if self.ml_state['status'] == 'PAUSED':
            self.ml_pause_event.clear()
            self.ml_state['status'] = 'TRAINING'
            self._ml_update_state('TRAINING')
            self._ml_add_log("Training resumed", "TRAIN")
            return
        
        # Start new training
        self._ml_add_log("Starting training...", "TRAIN")
        self.ml_stop_event.clear()
        self.ml_pause_event.clear()
        
        # Reset progress
        self.ml_state['epoch'] = 0
        self.ml_state['step'] = 0
        
        # Start worker thread (MVP: simulation)
        self.ml_worker = threading.Thread(target=self._ml_training_simulation, daemon=True)
        self.ml_worker.start()
        
        self.ml_state['status'] = 'TRAINING'
        self._ml_update_state('TRAINING')
    
    def _ml_pause_train(self):
        """Pause ML training"""
        self.ml_pause_event.set()
        self.ml_state['status'] = 'PAUSED'
        self._ml_update_state('PAUSED')
        self._ml_add_log("Training paused", "TRAIN")
    
    def _ml_stop_train(self):
        """Stop ML training"""
        self.ml_stop_event.set()
        self.ml_state['status'] = 'IDLE'
        self._ml_update_state('IDLE')
        self._ml_add_log("Training stopped", "TRAIN")
    
    def _ml_export_model(self):
        """Export trained model"""
        try:
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pt",
                filetypes=[("PyTorch Model", "*.pt"), ("ONNX Model", "*.onnx"), ("All files", "*.*")]
            )
            if filepath:
                # Stub: would save actual model here
                self._ml_add_log(f"Model exported to {filepath}", "INFO")
                messagebox.showinfo("Export", f"Model exported successfully!\n{filepath}")
        except Exception as e:
            self._ml_add_log(f"Failed to export model: {e}", "ERROR")
    
    def _ml_preview_data(self):
        """Preview dataset (stub)"""
        self._ml_add_log("Preview dataset feature coming soon", "INFO")
    
    def _ml_rebuild_features(self):
        """Rebuild features (stub)"""
        self._ml_add_log("Rebuilding features...", "TRAIN")
        self._ml_add_log("Feature engineering completed", "INFO")
    
    def _ml_normalize(self):
        """Normalize dataset (stub)"""
        self._ml_add_log("Normalizing dataset...", "TRAIN")
        self._ml_add_log("Normalization completed", "INFO")
    
    def _ml_split_data(self):
        """Split train/validation (stub)"""
        self._ml_add_log("Splitting dataset (80/20)...", "TRAIN")
        self._ml_add_log("Split completed: Train=80%, Val=20%", "INFO")
    
    def _ml_show_plot(self):
        """Show training plot (stub)"""
        self._ml_add_log("Opening training plot visualization...", "INFO")
        # TODO: Show matplotlib window with loss curves, F1 score, etc.
    
    def _ml_training_simulation(self):
        """MVP: Simulate training for testing UI (replace with real training)"""
        try:
            epochs = 50
            steps_per_epoch = 600
            
            self.ml_queue.put({'type': 'state', 'value': 'TRAINING'})
            self.ml_queue.put({'type': 'log', 'level': 'TRAIN', 'msg': 'Initializing ML pipeline...'})
            time.sleep(0.5)
            
            self.ml_queue.put({'type': 'log', 'level': 'INFO', 'msg': 'Splitting dataset: train=96,000, val=24,000'})
            self.ml_queue.put({'type': 'log', 'level': 'INFO', 'msg': 'Features built and normalized'})
            self.ml_queue.put({'type': 'log', 'level': 'TRAIN', 'msg': 'Training started: epoch=55, step=18240, loss=0.861, val_F1=0.861'})
            
            import random
            
            for epoch in range(1, epochs + 1):
                if self.ml_stop_event.is_set():
                    self.ml_queue.put({'type': 'log', 'level': 'WARN', 'msg': 'Training stopped by user'})
                    break
                
                for step in range(1, steps_per_epoch + 1):
                    if self.ml_stop_event.is_set():
                        break
                    
                    # Check pause
                    while self.ml_pause_event.is_set() and not self.ml_stop_event.is_set():
                        time.sleep(0.1)
                    
                    # Simulate progress
                    total_steps = epochs * steps_per_epoch
                    current_step = (epoch - 1) * steps_per_epoch + step
                    remaining = total_steps - current_step
                    eta_sec = int(remaining * 0.05)  # ~0.05 sec per step simulation
                    
                    # Send progress update every 50 steps
                    if step % 50 == 0:
                        self.ml_queue.put({
                            'type': 'progress',
                            'epoch': epoch,
                            'epochs': epochs,
                            'step': current_step,
                            'steps_total': total_steps,
                            'eta_sec': eta_sec
                        })
                    
                    # Send metrics update every epoch
                    if step == steps_per_epoch:
                        train_loss = 1.0 - (epoch / epochs) * 0.7 + random.uniform(-0.05, 0.05)
                        val_loss = train_loss + random.uniform(0, 0.1)
                        f1 = 0.5 + (epoch / epochs) * 0.4 + random.uniform(-0.03, 0.03)
                        
                        # Determine overfit
                        diff = val_loss - train_loss
                        if diff < 0.05:
                            overfit = 'LOW'
                        elif diff < 0.15:
                            overfit = 'MED'
                        else:
                            overfit = 'HIGH'
                        
                        self.ml_queue.put({
                            'type': 'metrics',
                            'train_loss': max(0.1, train_loss),
                            'val_loss': max(0.1, val_loss),
                            'f1': min(0.95, max(0.5, f1)),
                            'overfit': overfit
                        })
                        
                        self.ml_queue.put({
                            'type': 'log',
                            'level': 'TRAIN',
                            'msg': f'epoch={epoch}, step={current_step}, loss={train_loss:.3f}, val_loss={val_loss:.3f}, F1={f1:.2f}'
                        })
                    
                    time.sleep(0.02)  # Simulate work
            
            # Training done
            if not self.ml_stop_event.is_set():
                self.ml_queue.put({'type': 'log', 'level': 'INFO', 'msg': 'Training completed successfully!'})
                self.ml_queue.put({'type': 'done', 'model_path': 'models/model_final.pt'})
            
        except Exception as e:
            self.ml_queue.put({'type': 'error', 'msg': str(e)})
    
    # ==================== BOT STATUS METHODS ====================
    
    def _poll_bot_queue(self):
        """Poll bot queue for status updates"""
        try:
            # Check trading hours if bot is running
            if hasattr(self.control_panel, 'is_running') and self.control_panel.is_running:
                self._check_trading_hours_status()
            
            while not self.bot_queue.empty():
                event = self.bot_queue.get_nowait()
                self._handle_bot_event(event)
        except Exception as e:
            app_logger.error(f"Error polling bot queue: {e}")
        finally:
            # Schedule next poll
            self.root.after(200, self._poll_bot_queue)  # 200ms for real-time feel
    
    def _check_trading_hours_status(self):
        """Check if current time is within trading hours and update status"""
        from datetime import datetime, time as datetime_time
        
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # Check if already in blocked state to avoid spam
        current_status = self.bot_state.get('status')
        
        # Weekend check
        if weekday >= 5:  # Saturday=5, Sunday=6
            if current_status != 'BLOCKED' or self.bot_state.get('block_reason') != 'Weekend':
                self.bot_queue.put({'type': 'status', 'status': 'BLOCKED'})
                self.bot_queue.put({'type': 'block', 'reason': 'Weekend'})
            return
        
        # Night hours check: 23:30 - 01:10
        night_start = datetime_time(23, 30)
        night_end = datetime_time(1, 10)
        
        if current_time >= night_start or current_time <= night_end:
            if current_status != 'BLOCKED' or 'Night hours' not in self.bot_state.get('block_reason', ''):
                self.bot_queue.put({'type': 'status', 'status': 'BLOCKED'})
                self.bot_queue.put({'type': 'block', 'reason': 'Night hours (23:30-01:10)'})
            return
        
        # Clear block if was blocked by time
        if current_status == 'BLOCKED' and self.bot_state.get('block_reason') in ['Weekend', 'Night hours (23:30-01:10)']:
            self.bot_queue.put({'type': 'status', 'status': 'RUNNING'})
            self.bot_queue.put({'type': 'block', 'reason': ''})
    
    def _handle_bot_event(self, event: dict):
        """Handle bot status event"""
        event_type = event.get('type')
        
        if event_type == 'status':
            self._bot_update_status(event)
        elif event_type == 'pipeline':
            self._bot_update_pipeline(event)
        elif event_type == 'signal':
            self._bot_update_signal(event)
        elif event_type == 'block':
            self._bot_update_block(event)
        elif event_type == 'timer':
            self._bot_update_timer(event)
        # NEW: Signal lifecycle events
        elif event_type == 'gpt_request_started':
            self._bot_gpt_request_started(event)
        elif event_type == 'gpt_decision_ready':
            self._bot_gpt_decision_ready(event)
        elif event_type == 'risk_blocked':
            self._bot_risk_blocked(event)
        elif event_type == 'risk_ok':
            self._bot_risk_ok(event)
        elif event_type == 'order_sent':
            self._bot_order_sent(event)
        elif event_type == 'order_filled':
            self._bot_order_filled(event)
        elif event_type == 'order_failed':
            self._bot_order_failed(event)
        elif event_type == 'position_opened':
            self._bot_position_opened(event)
    
    def _bot_update_status(self, event: dict):
        """Update main bot status"""
        status = event.get('status', 'IDLE')
        self.bot_state['status'] = status
        
        # Status colors
        status_colors = {
            'IDLE': Theme.TEXT_MUTED,
            'RUNNING': Theme.SUCCESS,
            'WAITING': Theme.ACCENT,
            'ANALYZING': Theme.WARNING,
            'BLOCKED': Theme.ERROR,
            'ORDERING': Theme.SUCCESS,
            'ERROR': Theme.ERROR
        }
        
        color = status_colors.get(status, Theme.TEXT_MUTED)
        self.bot_status_label.configure(text=status, fg=color)
        
        # Update timestamp
        self.bot_state['last_update'] = datetime.now().strftime("%H:%M:%S")
    
    def _bot_update_pipeline(self, event: dict):
        """Update pipeline step status"""
        step = event.get('step')  # data/signal/gpt/risk/order
        state = event.get('state')  # IDLE/ACTIVE/SUCCESS/ERROR/BLOCKED
        
        if step not in self.pipeline_steps:
            return
        
        self.bot_state['pipeline'][step] = state
        
        # Step colors
        colors = {
            'IDLE': Theme.TEXT_MUTED,
            'ACTIVE': Theme.ACCENT,
            'SUCCESS': Theme.SUCCESS,
            'ERROR': Theme.ERROR,
            'BLOCKED': Theme.WARNING
        }
        
        color = colors.get(state, Theme.TEXT_MUTED)
        self.pipeline_steps[step]['indicator'].configure(fg=color)
    
    def _bot_update_signal(self, event: dict):
        """Update last signal"""
        signal = event.get('signal', 'NONE')
        self.bot_state['last_signal'] = signal
        
        # Signal colors
        signal_colors = {
            'BUY': Theme.SUCCESS,
            'SELL': Theme.ERROR,
            'NONE': Theme.TEXT_MUTED
        }
        
        color = signal_colors.get(signal, Theme.TEXT_MUTED)
        self.bot_signal_label.configure(text=signal, fg=color)
    
    def _bot_update_block(self, event: dict):
        """Update block reason"""
        reason = event.get('reason', '')
        old_reason = self.bot_state.get('block_reason', '')
        self.bot_state['block_reason'] = reason
        
        if reason and reason != old_reason:
            # Log new block reason
            self.add_log(f"⛔ Trading blocked: {reason}", "WARN")
            self.bot_block_label.configure(text=reason)
            self.bot_block_frame.pack(anchor='e', pady=(0, 6))
        elif not reason and old_reason:
            # Log when block is lifted
            self.add_log("✅ Trading block lifted", "INFO")
            self.bot_block_frame.pack_forget()
        elif reason:
            # Just update UI without logging
            self.bot_block_label.configure(text=reason)
            self.bot_block_frame.pack(anchor='e', pady=(0, 6))
        else:
            self.bot_block_frame.pack_forget()
    
    def _bot_update_timer(self, event: dict):
        """Update next check timer"""
        seconds = event.get('seconds', 0)
        self.bot_state['next_check_sec'] = seconds
        
        if seconds > 0:
            if seconds >= 60:
                mins = seconds // 60
                secs = seconds % 60
                text = f"{mins}m {secs}s" if secs > 0 else f"{mins}m"
            else:
                text = f"{seconds}s"
            self.bot_timer_label.configure(text=text)
        else:
            # 0 seconds = either in a trade or no countdown active → hide the timer
            self.bot_timer_label.configure(text="-")

    def _bot_gpt_request_started(self, event: dict):
        """Handle GPT request started event"""
        symbol = event.get('symbol', 'XAUUSD')
        self.bot_state['status'] = 'ANALYZING'
        self.bot_state['pipeline']['gpt'] = 'ACTIVE'
        self.add_log(f"🤖 GPT analyzing {symbol}...", "INFO")
        self._bot_update_status({'status': 'ANALYZING'})
        self._bot_update_pipeline({'step': 'gpt', 'state': 'ACTIVE'})

    def _bot_gpt_decision_ready(self, event: dict):
        """Handle GPT decision ready event (SINGLE SOURCE OF TRUTH)"""
        signal_data = {
            'signal_id': event.get('signal_id'),
            'signal_id_short': event.get('signal_id', '')[-6:],
            'action': event.get('action', 'HOLD'),
            'confidence': event.get('confidence', 0),
            'symbol': event.get('symbol', 'XAUUSD'),
            'entry_price': event.get('entry_price', 0),
            'stop_loss': event.get('stop_loss', 0),
            'take_profit': event.get('take_profit', 0),
            'reasoning': event.get('reasoning', ''),
            'ticket': None,
            'timestamp': event.get('timestamp', datetime.now().isoformat()),
            'status': 'pending'
        }
        
        # Update LAST ANALYSIS (always update)
        self.bot_state['last_analysis'] = signal_data.copy()
        
        # Update LAST GPT ANALYSIS panel
        time_str = datetime.fromisoformat(signal_data['timestamp']).strftime('%H:%M:%S')
        action_color = Theme.SUCCESS if signal_data['action'] == 'BUY' else (Theme.ERROR if signal_data['action'] == 'SELL' else Theme.WARNING)
        self.last_signal_label.configure(text=signal_data['action'], fg=action_color)
        self.signal_time_label.configure(text=time_str)
        self.confidence_label.configure(text=f"{signal_data['confidence']}%", 
                                       fg=Theme.SUCCESS if signal_data['confidence'] >= 70 else Theme.WARNING)
        self.recommendation_label.configure(text=signal_data['reasoning'][:100])
        
        # Update ACTIVE SIGNAL only if actionable (BUY/SELL)
        if signal_data['action'] in ['BUY', 'SELL']:
            self.bot_state['active_signal'] = signal_data
            self.bot_state['last_signal'] = signal_data['action']
            
            # Update Bot Status Panel (small panel at top)
            signal_color = Theme.SUCCESS if signal_data['action'] == 'BUY' else Theme.ERROR
            signal_text = f"{signal_data['action']} ({signal_data['confidence']}%)"
            self.bot_signal_label.configure(text=signal_text, fg=signal_color)
            self.bot_signal_id_label.configure(text=signal_data['signal_id_short'])
            self.bot_signal_id_frame.pack(anchor='e', pady=(0, 3))
            self.bot_ticket_frame.pack_forget()
            
            # Update Active Signal Panel (big panel in AI Decision tab)
            self.active_signal_label.configure(text=signal_data['action'], fg=signal_color)
            self.active_confidence_label.configure(text=f"{signal_data['confidence']}%", fg=signal_color)
            
            # Calculate profit/loss potential
            sl_distance = abs(signal_data['entry_price'] - signal_data['stop_loss'])
            tp_distance = abs(signal_data['take_profit'] - signal_data['entry_price'])
            sl_dollars = sl_distance if signal_data['symbol'] == 'XAUUSD' else sl_distance * 100000 * 0.01
            tp_dollars = tp_distance if signal_data['symbol'] == 'XAUUSD' else tp_distance * 100000 * 0.01
            
            details_text = (
                f"{signal_data['symbol']}\n"
                f"Entry: ${signal_data['entry_price']:.2f}\n"
                f"SL: ${signal_data['stop_loss']:.2f} (-${sl_dollars:.1f})\n"
                f"TP: ${signal_data['take_profit']:.2f} (+${tp_dollars:.1f})"
            )
            self.active_details_label.configure(text=details_text, fg=Theme.TEXT_PRIMARY)
            
            self.add_log(
                f"✅ GPT Decision: {signal_data['action']} {signal_data['symbol']} @ {signal_data['entry_price']} "
                f"(Confidence: {signal_data['confidence']}%) [ID: {signal_data['signal_id_short']}]",
                "INFO"
            )
        else:
            # HOLD - clear active signal
            self.bot_state['active_signal'] = None
            self.bot_state['last_signal'] = 'NONE'
            
            # Update Bot Status Panel
            self.bot_signal_label.configure(text="NONE", fg=Theme.TEXT_MUTED)
            self.bot_signal_id_frame.pack_forget()
            self.bot_ticket_frame.pack_forget()
            
            # Update Active Signal Panel
            self.active_signal_label.configure(text="NONE", fg=Theme.TEXT_MUTED)
            self.active_confidence_label.configure(text="0%", fg=Theme.TEXT_MUTED)
            self.active_details_label.configure(
                text="No active signal\n\nWaiting for GPT decision...",
                fg=Theme.TEXT_SECONDARY
            )
            
            self.add_log(f"⏸️ GPT Decision: HOLD ({signal_data['confidence']}%)", "INFO")
        
        self._bot_update_pipeline({'step': 'gpt', 'state': 'SUCCESS'})
    
    def _bot_risk_blocked(self, event: dict):
        """Handle risk blocked event"""
        signal_id = event.get('signal_id', '')
        reason = event.get('reason', 'Unknown')
        
        # Update active signal status  
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['status'] = 'rejected'
            self.bot_state['active_signal'] = None  # Clear rejected signal
        
        self.add_log(f"🚫 Risk Manager BLOCKED: {reason} [ID: {signal_id[-6:]}]", "WARN")
        self._bot_update_pipeline({'step': 'risk', 'state': 'BLOCKED'})
        self._bot_update_block({'reason': f"Risk: {reason}"})
    
    def _bot_risk_ok(self, event: dict):
        """Handle risk approved event"""
        signal_id = event.get('signal_id', '')
        
        # Update active signal status
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['status'] = 'approved'
        
        self.add_log(f"✅ Risk Manager APPROVED [ID: {signal_id[-6:]}]", "INFO")
        self._bot_update_pipeline({'step': 'risk', 'state': 'SUCCESS'})
    
    def _bot_order_sent(self, event: dict):
        """Handle order sent event"""
        signal_id = event.get('signal_id', '')
        ticket = event.get('ticket')
        symbol = event.get('symbol', 'XAUUSD')
        
        # Update active signal
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['status'] = 'ordering'
            if ticket:
                self.bot_state['active_signal']['ticket'] = ticket
        
        self.bot_state['status'] = 'ORDERING'
        self.add_log(f"📤 Order SENT: {symbol} (Ticket: {ticket}) [ID: {signal_id[-6:]}]", "INFO")
        self._bot_update_status({'status': 'ORDERING'})
        self._bot_update_pipeline({'step': 'order', 'state': 'ACTIVE'})
    
    def _bot_order_filled(self, event: dict):
        """Handle order filled event"""
        signal_id = event.get('signal_id', '')
        ticket = event.get('ticket')
        symbol = event.get('symbol', 'XAUUSD')
        
        # Update active signal
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['status'] = 'filled'
            if ticket:
                self.bot_state['active_signal']['ticket'] = ticket
        
        self.add_log(f"✅ Order FILLED: {symbol} (Ticket: {ticket}) [ID: {signal_id[-6:]}]", "SUCCESS")
        self._bot_update_pipeline({'step': 'order', 'state': 'SUCCESS'})
    
    def _bot_order_failed(self, event: dict):
        """Handle order failed event"""
        signal_id = event.get('signal_id', '')
        error = event.get('error', 'Unknown error')
        
        # Update active signal
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['status'] = 'failed'
            self.bot_state['active_signal'] = None  # Clear failed signal
        
        self.add_log(f"❌ Order FAILED: {error} [ID: {signal_id[-6:]}]", "ERROR")
        self._bot_update_status({'status': 'ERROR'})
        self._bot_update_pipeline({'step': 'order', 'state': 'ERROR'})
    
    def _bot_position_opened(self, event: dict):
        """Handle position opened event"""
        signal_id = event.get('signal_id', '')
        ticket = event.get('ticket')
        symbol = event.get('symbol', 'XAUUSD')
        
        # Update active signal ticket
        if self.bot_state['active_signal'] and self.bot_state['active_signal']['signal_id'] == signal_id:
            self.bot_state['active_signal']['ticket'] = ticket
            self.bot_state['active_signal']['status'] = 'trading'
            
            # Update UI: Show ticket
            self.bot_ticket_label.configure(text=str(ticket))
            self.bot_ticket_frame.pack(anchor='e', pady=(0, 3))
        
        self.bot_state['status'] = 'TRADING'
        self.add_log(f"🎯 Position OPENED: {symbol} (Ticket: {ticket}) [ID: {signal_id[-6:]}]", "SUCCESS")
        self._bot_update_status({'status': 'TRADING'})
    
    def _start_bot_status_simulation(self):
        """Temporary: Simulate bot status updates for testing UI"""
        if not hasattr(self, 'bot_sim_running'):
            self.bot_sim_running = False
        
        if self.bot_sim_running:
            return
        
        self.bot_sim_running = True
        
        def simulate():
            import time
            import random
            
            try:
                cycle = 0
                while self.bot_sim_running and self.control_panel.is_running:
                    cycle += 1
                    
                    # Waiting phase
                    self.bot_queue.put({'type': 'status', 'status': 'WAITING'})
                    for i in range(5, 0, -1):
                        if not self.bot_sim_running:
                            break
                        self.bot_queue.put({'type': 'timer', 'seconds': i})
                        time.sleep(1)
                    
                    if not self.bot_sim_running:
                        break
                    
                    # Data phase
                    self.bot_queue.put({'type': 'pipeline', 'step': 'data', 'state': 'ACTIVE'})
                    time.sleep(0.5)
                    self.bot_queue.put({'type': 'pipeline', 'step': 'data', 'state': 'SUCCESS'})
                    
                    # Signal phase
                    self.bot_queue.put({'type': 'pipeline', 'step': 'signal', 'state': 'ACTIVE'})
                    time.sleep(0.8)
                    
                    # Random signal or no signal
                    if random.random() > 0.6:  # 40% chance of signal
                        signal_type = random.choice(['BUY', 'SELL'])
                        self.bot_queue.put({'type': 'signal', 'signal': signal_type})
                        self.bot_queue.put({'type': 'pipeline', 'step': 'signal', 'state': 'SUCCESS'})
                        
                        # GPT analysis
                        self.bot_queue.put({'type': 'status', 'status': 'ANALYZING'})
                        self.bot_queue.put({'type': 'pipeline', 'step': 'gpt', 'state': 'ACTIVE'})
                        time.sleep(1.5)
                        
                        # GPT decision
                        gpt_approve = random.random() > 0.3  # 70% approval
                        if gpt_approve:
                            self.bot_queue.put({'type': 'pipeline', 'step': 'gpt', 'state': 'SUCCESS'})
                            
                            # Risk check
                            self.bot_queue.put({'type': 'pipeline', 'step': 'risk', 'state': 'ACTIVE'})
                            time.sleep(0.5)
                            
                            risk_ok = random.random() > 0.2  # 80% pass
                            if risk_ok:
                                self.bot_queue.put({'type': 'pipeline', 'step': 'risk', 'state': 'SUCCESS'})
                                
                                # Place order
                                self.bot_queue.put({'type': 'status', 'status': 'ORDERING'})
                                self.bot_queue.put({'type': 'pipeline', 'step': 'order', 'state': 'ACTIVE'})
                                time.sleep(1.0)
                                self.bot_queue.put({'type': 'pipeline', 'step': 'order', 'state': 'SUCCESS'})
                                
                                # Clear block reason
                                self.bot_queue.put({'type': 'block', 'reason': ''})
                            else:
                                # Risk blocked
                                reasons = ['Max drawdown', 'Daily limit', 'Position size']
                                reason = random.choice(reasons)
                                self.bot_queue.put({'type': 'status', 'status': 'BLOCKED'})
                                self.bot_queue.put({'type': 'pipeline', 'step': 'risk', 'state': 'BLOCKED'})
                                self.bot_queue.put({'type': 'block', 'reason': reason})
                        else:
                            # GPT rejected
                            self.bot_queue.put({'type': 'pipeline', 'step': 'gpt', 'state': 'ERROR'})
                            self.bot_queue.put({'type': 'signal', 'signal': 'NONE'})
                    else:
                        # No signal
                        self.bot_queue.put({'type': 'pipeline', 'step': 'signal', 'state': 'IDLE'})
                    
                    # Reset pipeline for next cycle
                    time.sleep(2)
                    for step in ['data', 'signal', 'gpt', 'risk', 'order']:
                        self.bot_queue.put({'type': 'pipeline', 'step': step, 'state': 'IDLE'})
                    
            except Exception as e:
                app_logger.error(f"Bot simulation error: {e}")
            finally:
                self.bot_sim_running = False
        
        # Run in thread
        sim_thread = threading.Thread(target=simulate, daemon=True)
        sim_thread.start()
    
    # ==================== RUN TAB METHODS ====================
    
    def _poll_run_session(self):
        """Poll run session for updates (RUN tab)"""
        try:
            # Update elapsed time
            self.run_session.update_elapsed()
            
            # Get current run state
            state = self.run_session.current_run
            
            # If no run active, show default state
            if not state:
                self.run_status_label.configure(text='STOPPED', fg=Theme.TEXT_MUTED)
                self.run_id_label.configure(text='--')
                self.run_day_label.configure(text='--/5')
                self.run_start_time_label.configure(text='--')
                self.run_eta_label.configure(text='--')
                
                # Disable buttons
                self.run_start_btn.configure(state='normal')
                self.run_pause_btn.configure(state='disabled')
                self.run_reset_btn.configure(state='disabled')
                self.run_export_btn.configure(state='disabled')
                self.run_folder_btn.configure(state='disabled')
                
                # Reset progress bars
                self.run_today_progressbar['value'] = 0
                self.run_total_progressbar['value'] = 0
                self.run_today_elapsed_label.configure(text="Elapsed: 00:00:00")
                self.run_today_remaining_label.configure(text="Remaining: 24:00:00")
                self.run_total_elapsed_label.configure(text="Elapsed: 00:00:00")
                self.run_total_remaining_label.configure(text="Remaining: 120:00:00")
                
                # Reset counters
                for metric_name, labels in self.run_counter_labels.items():
                    labels['today'].configure(text='0')
                    labels['total'].configure(text='0')
                
                # Reset advisor
                self.run_advisor_label.configure(
                    text="No suggestions. System healthy. ✅",
                    fg=Theme.SUCCESS
                )
                
                return
            
            # Update controller
            status_colors = {
                'STOPPED': Theme.TEXT_MUTED,
                'ACTIVE': Theme.SUCCESS,
                'PAUSED': Theme.WARNING
            }
            color = status_colors.get(state.status, Theme.TEXT_MUTED)
            self.run_status_label.configure(text=state.status, fg=color)
            self.run_id_label.configure(text=state.run_id if state.run_id != 'none' else '--')
            self.run_day_label.configure(text=f"{state.current_day}/{state.total_days}" if state.run_id != 'none' else '--/5')
            self.run_start_time_label.configure(text=state.start_time if state.start_time != '--' else '--')
            
            # ETA calculation
            if state.status == 'ACTIVE' and state.run_id != 'none':
                progress_data = self.run_session.get_progress()
                eta_str = progress_data.get('eta_end', '--')
                self.run_eta_label.configure(text=eta_str)
            else:
                self.run_eta_label.configure(text='--')
            
            # Update buttons
            if state.status == 'STOPPED':
                self.run_start_btn.configure(state='normal')
                self.run_pause_btn.configure(state='disabled')
                self.run_reset_btn.configure(state='disabled')
                self.run_export_btn.configure(state='disabled')
                self.run_folder_btn.configure(state='disabled')
            elif state.status == 'ACTIVE':
                self.run_start_btn.configure(state='disabled')
                self.run_pause_btn.configure(state='normal', text='⏸ Pause')
                self.run_reset_btn.configure(state='normal')
                self.run_export_btn.configure(state='normal')
                self.run_folder_btn.configure(state='normal')
            elif state.status == 'PAUSED':
                self.run_start_btn.configure(state='disabled')
                self.run_pause_btn.configure(state='normal', text='▶ Resume')
                self.run_reset_btn.configure(state='normal')
                self.run_export_btn.configure(state='normal')
                self.run_folder_btn.configure(state='normal')
                self.run_export_btn.configure(state='normal')
            
            # Update progress bars
            if state.run_id != 'none':
                progress_data = self.run_session.get_progress()
                
                # Today progress
                today_pct = progress_data.get('today_progress', 0)
                self.run_today_progressbar['value'] = today_pct
                
                today_elapsed = progress_data.get('today_elapsed_str', '00:00:00')
                today_remaining = progress_data.get('today_remaining_str', '24:00:00')
                self.run_today_elapsed_label.configure(text=f"Elapsed: {today_elapsed}")
                self.run_today_remaining_label.configure(text=f"Remaining: {today_remaining}")
                
                # Total progress
                total_pct = progress_data.get('total_progress', 0)
                self.run_total_progressbar['value'] = total_pct
                
                total_elapsed = progress_data.get('total_elapsed_str', '00:00:00')
                total_remaining = progress_data.get('total_remaining_str', '120:00:00')
                self.run_total_elapsed_label.configure(text=f"Elapsed: {total_elapsed}")
                self.run_total_remaining_label.configure(text=f"Remaining: {total_remaining}")
            else:
                # Reset progress bars
                self.run_today_progressbar['value'] = 0
                self.run_total_progressbar['value'] = 0
                self.run_today_elapsed_label.configure(text="Elapsed: 00:00:00")
                self.run_today_remaining_label.configure(text="Remaining: 24:00:00")
                self.run_total_elapsed_label.configure(text="Elapsed: 00:00:00")
                self.run_total_remaining_label.configure(text="Remaining: 120:00:00")
            
            # Update counters
            counters = self.run_session.get_counters()
            for metric_name, labels in self.run_counter_labels.items():
                today_val = counters['today'].get(metric_name, 0)
                total_val = counters['total'].get(metric_name, 0)
                labels['today'].configure(text=str(today_val))
                labels['total'].configure(text=str(total_val))
            
            # Update advisor
            suggestions = self.run_session.get_suggestions()
            if suggestions:
                # Find highest level
                has_critical = any(s['level'] == 'CRITICAL' for s in suggestions)
                has_warning = any(s['level'] == 'WARNING' for s in suggestions)
                
                if has_critical:
                    color = Theme.ERROR
                    icon = "🔴"
                elif has_warning:
                    color = Theme.WARNING
                    icon = "⚠️"
                else:
                    color = Theme.ACCENT
                    icon = "💡"
                
                # Build text
                text_lines = [f"{icon} {len(suggestions)} suggestion(s):"]
                for s in suggestions[:5]:  # Show max 5
                    level_icon = "🔴" if s['level'] == 'CRITICAL' else "⚠️"
                    text_lines.append(f"{level_icon} {s['message']}")
                
                text = "\n".join(text_lines)
                self.run_advisor_label.configure(text=text, fg=color)
            else:
                self.run_advisor_label.configure(
                    text="No suggestions. System healthy. ✅",
                    fg=Theme.SUCCESS
                )
            
            # Process event queue (thread-safe UI updates)
            while not self.run_event_queue.empty():
                try:
                    event = self.run_event_queue.get_nowait()
                    
                    # Format event for live feed
                    event_type = event.get('type', 'unknown')
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    msg = f"[{timestamp}] {event_type}"
                    if 'data' in event and isinstance(event['data'], dict):
                        data = event['data']
                        details = []
                        for k, v in list(data.items())[:3]:  # Max 3 fields
                            details.append(f"{k}={v}")
                        if details:
                            msg += f" | {', '.join(details)}"
                    
                    # Add to feed (в main thread - thread-safe)
                    self.run_feed_text.configure(state='normal')
                    self.run_feed_text.insert('end', msg + '\n')
                    self.run_feed_text.see('end')
                    
                    # Limit feed to 2000 lines (увеличено с 500)
                    line_count = int(self.run_feed_text.index('end-1c').split('.')[0])
                    if line_count > 2000:
                        self.run_feed_text.delete('1.0', f'{line_count - 2000}.0')
                    
                    self.run_feed_text.configure(state='disabled')
                    
                except Exception as e:
                    app_logger.debug(f"[RUN] Event queue processing error: {e}")
            
        except Exception as e:
            app_logger.error(f"[RUN] Poll error: {e}")
        finally:
            # Schedule next poll (200ms - fast refresh)
            self.root.after(200, self._poll_run_session)
    
    def _on_statecore_event(self, event: dict):
        """Callback for StateCore events - добавить в queue для thread-safe обработки"""
        try:
            # Forward to run session manager
            self.run_session.handle_statecore_event(event)
            
            # Add to UI queue (thread-safe)
            self.run_event_queue.put(event)
            
        except Exception as e:
            app_logger.error(f"[RUN] Event handler error: {e}")
    
    def _run_start(self):
        """Start new 5-day run"""
        try:
            self.run_session.start_new_run(days=5)
            self.add_log("▶️ Started new 5-day run session", "INFO")
            
            # Clear feed
            self.run_feed_text.configure(state='normal')
            self.run_feed_text.delete('1.0', 'end')
            self.run_feed_text.configure(state='disabled')
            
            # Add welcome message
            self._on_statecore_event({
                'type': 'run_started',
                'data': {'run_id': self.run_session.current_run.run_id, 'days': 5}
            })
            
        except Exception as e:
            app_logger.error(f"[RUN] Start error: {e}")
            self.add_log(f"❌ Failed to start run: {e}", "ERROR")
    
    def _run_pause(self):
        """Pause/Resume run"""
        try:
            state = self.run_session.current_run
            if not state:
                return
            
            if state.status == 'ACTIVE':
                self.run_session.pause_run()
                self.add_log("⏸ Run paused", "INFO")
            elif state.status == 'PAUSED':
                self.run_session.resume_run()
                self.add_log("▶️ Run resumed", "INFO")
        except Exception as e:
            app_logger.error(f"[RUN] Pause/Resume error: {e}")
    
    def _run_reset(self):
        """Reset/Stop current run and start new one"""
        try:
            # Stop current
            self.run_session.stop_run()
            self.add_log("🛑 Run stopped", "INFO")
            
            # Ask user if they want to start new run
            from tkinter import messagebox
            result = messagebox.askyesno(
                "New Run",
                "Current run stopped. Start a new 5-day run?",
                parent=self.root
            )
            
            if result:
                self._run_start()
            
        except Exception as e:
            app_logger.error(f"[RUN] Reset error: {e}")
    
    def _run_export(self):
        """Export run report"""
        try:
            report_path = self.run_session.export_report()
            self.add_log(f"📤 Report exported: {report_path.name}", "INFO")
            
            from tkinter import messagebox
            messagebox.showinfo(
                "Export Complete",
                f"Report saved to:\n{report_path}",
                parent=self.root
            )
            
        except Exception as e:
            app_logger.error(f"[RUN] Export error: {e}")
            self.add_log(f"❌ Export failed: {e}", "ERROR")
    
    def _run_feed_copy(self):
        """Copy feed to clipboard"""
        try:
            content = self.run_feed_text.get('1.0', 'end-1c')
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.add_log("📋 Feed copied to clipboard", "INFO")
        except Exception as e:
            app_logger.error(f"[RUN] Copy error: {e}")
    
    def _run_feed_export(self):
        """Export feed to file"""
        try:
            content = self.run_feed_text.get('1.0', 'end-1c')
            
            # Save to run directory or data/
            if self.run_session.current_run and self.run_session.current_run.run_id != 'none':
                filepath = self.run_session.run_dir / f"live_feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            else:
                filepath = Path("data/logs") / f"run_feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.add_log(f"📤 Feed exported: {filepath.name}", "INFO")
            
        except Exception as e:
            app_logger.error(f"[RUN] Export feed error: {e}")
    
    def _run_feed_clear(self):
        """Clear feed"""
        try:
            self.run_feed_text.configure(state='normal')
            self.run_feed_text.delete('1.0', 'end')
            self.run_feed_text.configure(state='disabled')
            self.add_log("🗑️ Feed cleared", "INFO")
        except Exception as e:
            app_logger.error(f"[RUN] Clear feed error: {e}")
    
    def _run_open_folder(self):
        """Open run folder in file explorer"""
        try:
            if not self.run_session.run_dir or not self.run_session.run_dir.exists():
                self.add_log("❌ No active run directory", "WARN")
                return
            
            # Open folder in Windows Explorer
            import subprocess
            import os
            
            run_dir = str(self.run_session.run_dir.resolve())
            
            # Windows
            if os.name == 'nt':
                subprocess.Popen(['explorer', run_dir])
            # macOS
            elif os.name == 'posix' and os.uname().sysname == 'Darwin':
                subprocess.Popen(['open', run_dir])
            # Linux
            else:
                subprocess.Popen(['xdg-open', run_dir])
            
            self.add_log(f"📁 Opened folder: {self.run_session.run_dir.name}", "INFO")
            
        except Exception as e:
            app_logger.error(f"[RUN] Open folder error: {e}")
            self.add_log(f"❌ Failed to open folder: {e}", "ERROR")
    
    # ==================== CLEANUP ====================
    
    def _on_closing(self):
        """Cleanup before closing application"""
        try:
            app_logger.info("[GUI] Application closing - cleanup started")
            
            # Unsubscribe from StateCore events
            if hasattr(self, 'state_core'):
                try:
                    # Assuming StateCore has unsubscribe method
                    # (if not implemented, this will just pass)
                    if hasattr(self.state_core, 'unsubscribe_from_events'):
                        self.state_core.unsubscribe_from_events(self._on_statecore_event)
                    app_logger.info("[GUI] Unsubscribed from StateCore events")
                except Exception as e:
                    app_logger.debug(f"[GUI] StateCore unsubscribe error: {e}")
            
            # Shutdown RunSessionManager
            if hasattr(self, 'run_session'):
                try:
                    self.run_session.shutdown()
                    app_logger.info("[GUI] RunSessionManager shutdown complete")
                except Exception as e:
                    app_logger.error(f"[GUI] RunSessionManager shutdown error: {e}")
            
            # Stop ML worker if running
            if hasattr(self, 'ml_worker') and self.ml_worker:
                try:
                    self.ml_stop_event.set()
                    app_logger.info("[GUI] ML worker stop signal sent")
                except Exception as e:
                    app_logger.debug(f"[GUI] ML worker stop error: {e}")
            
            # Stop trading thread if running
            if hasattr(self, 'trading_thread') and self.trading_thread:
                try:
                    self.trading_stop_event.set()
                    app_logger.info("[GUI] Trading thread stop signal sent")
                except Exception as e:
                    app_logger.debug(f"[GUI] Trading thread stop error: {e}")
            
            app_logger.info("[GUI] Cleanup complete - destroying window")
            
        except Exception as e:
            app_logger.error(f"[GUI] Cleanup error: {e}")
        
        finally:
            # Destroy window
            self.root.destroy()
    
    # ==================== CONFIG ====================
    
    def _load_yaml_config(self, filepath: str) -> dict:
        """Load YAML configuration file"""
        try:
            config_path = Path(filepath)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            app_logger.error(f"Failed to load config {filepath}: {e}")
        return {}


# ==================== MAIN ====================
def main():
    """Entry point"""
    print("=" * 60)
    print("🚀 BAZA Trading Bot V2 - Professional UI")
    print("=" * 60)
    
    app = BazaAppV2()
    app.run()


if __name__ == "__main__":
    main()

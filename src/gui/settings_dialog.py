#!/usr/bin/env python3
"""
Settings Dialog - Управление настройками бота
"""

import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from pathlib import Path
from src.core.logger import logger


class Colors:
    """Цветовая схема"""
    BG_DARK = '#0d1117'
    BG_PANEL = '#161b22'
    BG_CARD = '#21262d'
    TEXT_PRIMARY = '#c9d1d9'
    TEXT_SECONDARY = '#8b949e'
    TEXT_MUTED = '#6e7681'
    BORDER = '#30363d'
    SUCCESS = '#3fb950'
    WARNING = '#d29922'
    ERROR = '#f85149'


class SettingsDialog:
    """Диалог настроек"""
    
    def __init__(self, parent, on_save_callback):
        self.parent = parent
        self.on_save_callback = on_save_callback
        self.configs = {}
        
        # Создать окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("⚙ Settings")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg=Colors.BG_DARK)
        self.dialog.resizable(False, False)
        
        # Сделать модальным
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Загрузить конфиги
        self._load_configs()
        
        # Создать UI
        self._create_ui()
        
        # Центрировать окно
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _load_configs(self):
        """Загрузить конфиги"""
        try:
            config_files = ['ai.yaml', 'portfolio.yaml', 'trading.yaml']
            
            for filename in config_files:
                path = Path('config') / filename
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        self.configs[filename] = yaml.safe_load(f)
                else:
                    self.configs[filename] = {}
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to load configs: {e}")
            messagebox.showerror("Error", f"Failed to load configs: {e}")
    
    def _create_ui(self):
        """Создать UI"""
        # Header
        header = tk.Frame(self.dialog, bg=Colors.BG_PANEL, height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="⚙ Settings",
                font=('Arial', 14, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.TEXT_PRIMARY).pack(side='left', padx=20, pady=15)
        
        # Separator
        tk.Frame(self.dialog, bg=Colors.BORDER, height=1).pack(fill='x')
        
        # Notebook (tabs)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=Colors.BG_DARK, borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=Colors.BG_CARD,
                       foreground=Colors.TEXT_PRIMARY,
                       padding=[20, 10])
        style.map('TNotebook.Tab',
                 background=[('selected', Colors.BG_PANEL)],
                 foreground=[('selected', Colors.SUCCESS)])
        
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Tabs
        self.trading_tab = self._create_trading_tab()
        self.ai_tab = self._create_ai_tab()
        self.strategy_tab = self._create_strategy_tab()
        self.gpt_api_tab = self._create_gpt_api_tab()
        self.telegram_tab = self._create_telegram_tab()
        
        self.notebook.add(self.trading_tab, text='💰 Trading')
        self.notebook.add(self.ai_tab, text='🤖 AI')
        self.notebook.add(self.strategy_tab, text='📊 Strategy')
        self.notebook.add(self.gpt_api_tab, text='🔑 GPT API')
        self.notebook.add(self.telegram_tab, text='📱 Telegram')
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg=Colors.BG_DARK)
        button_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        tk.Button(button_frame, text="Cancel",
                 font=('Arial', 11),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 relief='flat',
                 padx=20, pady=10,
                 command=self.dialog.destroy).pack(side='right', padx=(10, 0))
        
        tk.Button(button_frame, text="Save & Apply",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=20, pady=10,
                 command=self._save_settings).pack(side='right')
    
    def _create_trading_tab(self):
        """Trading настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Risk Management
        self._create_section(content, "Risk Management")
        
        portfolio_config = self.configs.get('portfolio.yaml', {})
        trading_config = self.configs.get('trading.yaml', {})
        risk_config = trading_config.get('trading', {}).get('risk', {})
        
        # Risk per trade
        risk_frame = self._create_setting_row(content, "Risk per trade (%)")
        self.risk_per_trade = tk.Entry(risk_frame, font=('Arial', 10), width=10)
        self.risk_per_trade.insert(0, str(portfolio_config.get('portfolio', {}).get('risk_model', {}).get('max_total_exposure', 1.25)))
        self.risk_per_trade.pack(side='right')
        
        # Max lot size
        lot_frame = self._create_setting_row(content, "Maximum lot size")
        self.max_lot = tk.Entry(lot_frame, font=('Arial', 10), width=10)
        self.max_lot.insert(0, str(risk_config.get('max_lot_size', 1.0)))
        self.max_lot.pack(side='right')
        
        # Stop Loss / Take Profit
        self._create_section(content, "Stop Loss / Take Profit")
        
        sl_frame = self._create_setting_row(content, "Default SL (pips)")
        self.default_sl = tk.Entry(sl_frame, font=('Arial', 10), width=10)
        self.default_sl.insert(0, str(risk_config.get('default_sl_pips', 50)))
        self.default_sl.pack(side='right')
        
        tp_frame = self._create_setting_row(content, "Default TP (pips)")
        self.default_tp = tk.Entry(tp_frame, font=('Arial', 10), width=10)
        self.default_tp.insert(0, str(risk_config.get('default_tp_pips', 100)))
        self.default_tp.pack(side='right')
        
        # Trailing Stop
        self._create_section(content, "Trailing Stop")
        
        trailing_config = trading_config.get('trading', {}).get('trailing_stop', {})
        
        trail_frame = self._create_setting_row(content, "Enable trailing stop")
        self.trail_enabled = tk.BooleanVar(value=trailing_config.get('enabled', False))
        tk.Checkbutton(trail_frame, variable=self.trail_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        trail_dist_frame = self._create_setting_row(content, "Trailing distance (pips)")
        self.trail_distance = tk.Entry(trail_dist_frame, font=('Arial', 10), width=10)
        self.trail_distance.insert(0, str(trailing_config.get('distance_pips', 20)))
        self.trail_distance.pack(side='right')
        
        # Trading Hours
        self._create_section(content, "Trading Hours (UTC)")
        
        hours_config = trading_config.get('trading', {}).get('hours', {})
        
        start_frame = self._create_setting_row(content, "Start time")
        self.trade_start = tk.Entry(start_frame, font=('Arial', 10), width=10)
        self.trade_start.insert(0, hours_config.get('start', '02:00'))
        self.trade_start.pack(side='right')
        
        end_frame = self._create_setting_row(content, "End time")
        self.trade_end = tk.Entry(end_frame, font=('Arial', 10), width=10)
        self.trade_end.insert(0, hours_config.get('end', '22:00'))
        self.trade_end.pack(side='right')
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_ai_tab(self):
        """AI настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        ai_config = self.configs.get('ai.yaml', {})
        
        # AI Enable
        self._create_section(content, "AI Settings")
        
        enable_frame = self._create_setting_row(content, "Enable AI Analysis")
        self.ai_enabled = tk.BooleanVar(value=ai_config.get('ai_enabled', True))
        tk.Checkbutton(enable_frame, variable=self.ai_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # GPT Model
        model_frame = self._create_setting_row(content, "GPT Model")
        self.gpt_model = ttk.Combobox(model_frame, width=15, 
                                     values=['gpt-4o', 'gpt-4-turbo', 'gpt-4'])
        current_model = ai_config.get('market_analyst', {}).get('gpt', {}).get('model', 'gpt-4o')
        self.gpt_model.set(current_model)
        self.gpt_model.pack(side='right')
        
        # Temperature
        temp_frame = self._create_setting_row(content, "Temperature")
        self.temperature = tk.Entry(temp_frame, font=('Arial', 10), width=10)
        current_temp = ai_config.get('market_analyst', {}).get('gpt', {}).get('temperature', 0.3)
        self.temperature.insert(0, str(current_temp))
        self.temperature.pack(side='right')
        
        # Analysis Schedule
        self._create_section(content, "Analysis Schedule")
        
        schedule_enabled_frame = self._create_setting_row(content, "Enable scheduled analysis")
        self.schedule_enabled = tk.BooleanVar(value=ai_config.get('market_analyst', {}).get('schedule', {}).get('enabled', True))
        tk.Checkbutton(schedule_enabled_frame, variable=self.schedule_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Analysis times
        times_frame = self._create_setting_row(content, "Analysis times")
        current_times = ai_config.get('market_analyst', {}).get('schedule', {}).get('times', [])
        self.analysis_times = tk.Entry(times_frame, font=('Arial', 10), width=30)
        self.analysis_times.insert(0, ', '.join(current_times))
        self.analysis_times.pack(side='right')
        
        # Filters
        self._create_section(content, "Signal Filters")
        
        signals_config = ai_config.get('market_analyst', {}).get('signals', {})
        
        conf_frame = self._create_setting_row(content, "Min confidence (%)")
        self.min_confidence = tk.Entry(conf_frame, font=('Arial', 10), width=10)
        self.min_confidence.insert(0, str(signals_config.get('min_confidence', 70)))
        self.min_confidence.pack(side='right')
        
        rr_frame = self._create_setting_row(content, "Min Risk/Reward ratio")
        self.min_rr = tk.Entry(rr_frame, font=('Arial', 10), width=10)
        self.min_rr.insert(0, str(signals_config.get('min_rr', 1.5)))
        self.min_rr.pack(side='right')
        
        # Time restrictions
        self._create_section(content, "Time Restrictions")
        
        night_block_frame = self._create_setting_row(content, "Block night trading (22:00-02:00)")
        self.night_block = tk.BooleanVar(value=ai_config.get('market_analyst', {}).get('schedule', {}).get('restrictions', {}).get('night_block', {}).get('enabled', True))
        tk.Checkbutton(night_block_frame, variable=self.night_block,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        weekend_block_frame = self._create_setting_row(content, "Block weekend trading")
        self.weekend_block = tk.BooleanVar(value=ai_config.get('market_analyst', {}).get('schedule', {}).get('restrictions', {}).get('weekend_block', {}).get('enabled', True))
        tk.Checkbutton(weekend_block_frame, variable=self.weekend_block,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_strategy_tab(self):
        """Strategy настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Timeframes
        self._create_section(content, "Timeframes")
        
        trading_config = self.configs.get('trading.yaml', {})
        indicators_config = trading_config.get('trading', {}).get('indicators', {})
        
        tf_frame = self._create_setting_row(content, "Active timeframes")
        self.timeframes = tk.Entry(tf_frame, font=('Arial', 10), width=30)
        current_tfs = indicators_config.get('timeframes', ['M15', 'M30', 'H1', 'H4'])
        self.timeframes.insert(0, ', '.join(current_tfs))
        self.timeframes.pack(side='right')
        
        # Indicators
        self._create_section(content, "Indicators")
        
        ema_frame = self._create_setting_row(content, "EMA periods")
        self.ema_periods = tk.Entry(ema_frame, font=('Arial', 10), width=20)
        current_emas = indicators_config.get('ema_periods', [20, 50, 200])
        self.ema_periods.insert(0, ', '.join(map(str, current_emas)))
        self.ema_periods.pack(side='right')
        
        rsi_frame = self._create_setting_row(content, "RSI period")
        self.rsi_period = tk.Entry(rsi_frame, font=('Arial', 10), width=10)
        self.rsi_period.insert(0, str(indicators_config.get('rsi_period', 14)))
        self.rsi_period.pack(side='right')
        
        atr_frame = self._create_setting_row(content, "ATR period")
        self.atr_period = tk.Entry(atr_frame, font=('Arial', 10), width=10)
        self.atr_period.insert(0, str(indicators_config.get('atr_period', 14)))
        self.atr_period.pack(side='right')
        
        # SMC Settings
        self._create_section(content, "Smart Money Concepts")
        
        smc_config = trading_config.get('trading', {}).get('smc', {})
        
        smc_frame = self._create_setting_row(content, "Enable SMC analysis")
        self.smc_enabled = tk.BooleanVar(value=smc_config.get('enabled', True))
        tk.Checkbutton(smc_frame, variable=self.smc_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        ob_frame = self._create_setting_row(content, "Order Block detection")
        self.ob_enabled = tk.BooleanVar(value=smc_config.get('order_blocks', True))
        tk.Checkbutton(ob_frame, variable=self.ob_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        fvg_frame = self._create_setting_row(content, "Fair Value Gap detection")
        self.fvg_enabled = tk.BooleanVar(value=smc_config.get('fair_value_gaps', True))
        tk.Checkbutton(fvg_frame, variable=self.fvg_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Trend Filter
        self._create_section(content, "Trend Filter")
        
        trend_config = trading_config.get('trading', {}).get('trend_filter', {})
        
        trend_frame = self._create_setting_row(content, "Enable trend filter")
        self.trend_filter = tk.BooleanVar(value=trend_config.get('enabled', True))
        tk.Checkbutton(trend_frame, variable=self.trend_filter,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_gpt_api_tab(self):
        """GPT API настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        content = tk.Frame(frame, bg=Colors.BG_DARK)
        content.pack(fill='both', expand=True, padx=30, pady=30)
        
        # OpenAI API
        self._create_section(content, "OpenAI API Configuration")
        
        # Info text
        info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                             highlightbackground=Colors.BORDER,
                             highlightthickness=1)
        info_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(info_frame,
                text="ℹ️ Get your API key from: https://platform.openai.com/api-keys",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                wraplength=500).pack(padx=15, pady=10)
        
        # API Key
        api_key_frame = tk.Frame(content, bg=Colors.BG_DARK)
        api_key_frame.pack(fill='x', pady=10)
        
        tk.Label(api_key_frame, text="API Key:",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY,
                width=15,
                anchor='w').pack(side='left')
        
        self.gpt_api_key = tk.Entry(api_key_frame, font=('Arial', 10), width=45, show='*')
        # Load from environment or config
        import os
        current_key = os.getenv('OPENAI_API_KEY', '')
        self.gpt_api_key.insert(0, current_key)
        self.gpt_api_key.pack(side='left', padx=(0, 10))
        
        # Show/Hide button
        self.show_api_key = tk.BooleanVar(value=False)
        
        def toggle_api_key():
            if self.show_api_key.get():
                self.gpt_api_key.config(show='')
                show_btn.config(text='Hide')
            else:
                self.gpt_api_key.config(show='*')
                show_btn.config(text='Show')
        
        show_btn = tk.Button(api_key_frame, text="Show",
                            font=('Arial', 9),
                            bg=Colors.BG_CARD,
                            fg=Colors.TEXT_PRIMARY,
                            relief='flat',
                            padx=10, pady=3,
                            command=lambda: [self.show_api_key.set(not self.show_api_key.get()), toggle_api_key()])
        show_btn.pack(side='left')
        
        # Usage info
        usage_frame = tk.Frame(content, bg=Colors.BG_CARD,
                              highlightbackground=Colors.WARNING,
                              highlightthickness=1)
        usage_frame.pack(fill='x', pady=(20, 0))
        
        usage_text = """⚠️ Important:
• API key is stored in .env file (not committed to git)
• Typical cost: ~$0.01-0.05 per analysis
• Model: GPT-4o (default)
• Make sure you have credits on your OpenAI account"""
        
        tk.Label(usage_frame,
                text=usage_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.WARNING,
                justify='left',
                wraplength=500).pack(padx=15, pady=10, anchor='w')
        
        return frame
    
    def _create_telegram_tab(self):
        """Telegram настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Telegram Bot Configuration
        self._create_section(content, "Telegram Bot Configuration")
        
        # Enable Telegram
        enable_frame = self._create_setting_row(content, "Enable Telegram notifications")
        
        telegram_config = {}
        try:
            telegram_path = Path('config') / 'telegram.yaml'
            if telegram_path.exists():
                import yaml
                with open(telegram_path, 'r', encoding='utf-8') as f:
                    telegram_config = yaml.safe_load(f) or {}
        except:
            pass
        
        telegram_settings = telegram_config.get('telegram', {})
        
        self.telegram_enabled = tk.BooleanVar(value=telegram_settings.get('enabled', False))
        tk.Checkbutton(enable_frame, variable=self.telegram_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Bot Token
        token_frame = self._create_setting_row(content, "Bot Token:")
        self.telegram_token = tk.Entry(token_frame, font=('Arial', 10), width=35, show='*')
        self.telegram_token.insert(0, telegram_settings.get('bot_token', ''))
        self.telegram_token.pack(side='right')
        
        # Chat ID
        chat_frame = self._create_setting_row(content, "Chat ID:")
        self.telegram_chat_id = tk.Entry(chat_frame, font=('Arial', 10), width=35)
        self.telegram_chat_id.insert(0, telegram_settings.get('chat_id', ''))
        self.telegram_chat_id.pack(side='right')
        
        # Enable Bot with buttons
        enable_bot_frame = self._create_setting_row(content, "Enable interactive bot")
        self.telegram_enable_bot = tk.BooleanVar(value=telegram_settings.get('enable_bot', True))
        tk.Checkbutton(enable_bot_frame, variable=self.telegram_enable_bot,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Notification Settings
        self._create_section(content, "Notification Settings")
        
        notify_config = telegram_settings.get('notify', {})
        
        # Startup
        startup_frame = self._create_setting_row(content, "Notify on startup")
        self.notify_startup = tk.BooleanVar(value=notify_config.get('startup', True))
        tk.Checkbutton(startup_frame, variable=self.notify_startup,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Trade opened
        trade_open_frame = self._create_setting_row(content, "Notify on trade opened")
        self.notify_trade_opened = tk.BooleanVar(value=notify_config.get('trade_opened', True))
        tk.Checkbutton(trade_open_frame, variable=self.notify_trade_opened,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Trade closed
        trade_close_frame = self._create_setting_row(content, "Notify on trade closed")
        self.notify_trade_closed = tk.BooleanVar(value=notify_config.get('trade_closed', True))
        tk.Checkbutton(trade_close_frame, variable=self.notify_trade_closed,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Daily report
        daily_frame = self._create_setting_row(content, "Daily report (23:55)")
        self.notify_daily_report = tk.BooleanVar(value=notify_config.get('daily_report', True))
        tk.Checkbutton(daily_frame, variable=self.notify_daily_report,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Alerts
        alerts_frame = self._create_setting_row(content, "System alerts")
        self.notify_alerts = tk.BooleanVar(value=notify_config.get('alerts', True))
        tk.Checkbutton(alerts_frame, variable=self.notify_alerts,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Alert level
        alert_level_frame = self._create_setting_row(content, "Alert minimum level")
        self.alert_min_level = ttk.Combobox(alert_level_frame, width=15,
                                           values=['INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.alert_min_level.set(telegram_settings.get('alert_min_level', 'WARNING'))
        self.alert_min_level.pack(side='right')
        
        # Info panel
        info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                             highlightbackground=Colors.BORDER,
                             highlightthickness=1)
        info_frame.pack(fill='x', pady=(20, 0))
        
        info_text = """ℹ️ How to setup Telegram bot:
1. Create bot via @BotFather on Telegram
2. Copy bot token and paste above
3. Get your Chat ID from @userinfobot
4. Enable notifications you want to receive"""
        
        tk.Label(info_frame,
                text=info_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                justify='left',
                wraplength=500).pack(padx=15, pady=10, anchor='w')
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_section(self, parent, title):
        """Создать секцию"""
        frame = tk.Frame(parent, bg=Colors.BG_DARK)
        frame.pack(fill='x', pady=(20, 10))
        
        tk.Label(frame, text=title,
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w')
        
        tk.Frame(frame, bg=Colors.BORDER, height=1).pack(fill='x', pady=(5, 0))
    
    def _create_setting_row(self, parent, label):
        """Создать строку настройки"""
        frame = tk.Frame(parent, bg=Colors.BG_DARK)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=label,
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY).pack(side='left')
        
        return frame
    
    def _save_settings(self):
        """Сохранить настройки"""
        try:
            # Обновить AI config
            ai_config = self.configs.get('ai.yaml', {})
            ai_config['ai_enabled'] = self.ai_enabled.get()
            
            if 'market_analyst' not in ai_config:
                ai_config['market_analyst'] = {}
            
            if 'gpt' not in ai_config['market_analyst']:
                ai_config['market_analyst']['gpt'] = {}
            
            ai_config['market_analyst']['gpt']['model'] = self.gpt_model.get()
            ai_config['market_analyst']['gpt']['temperature'] = float(self.temperature.get())
            
            if 'schedule' not in ai_config['market_analyst']:
                ai_config['market_analyst']['schedule'] = {}
            
            ai_config['market_analyst']['schedule']['enabled'] = self.schedule_enabled.get()
            
            # Parse analysis times
            times_str = self.analysis_times.get()
            times_list = [t.strip() for t in times_str.split(',') if t.strip()]
            ai_config['market_analyst']['schedule']['times'] = times_list
            
            # Time restrictions
            if 'restrictions' not in ai_config['market_analyst']['schedule']:
                ai_config['market_analyst']['schedule']['restrictions'] = {}
            
            if 'night_block' not in ai_config['market_analyst']['schedule']['restrictions']:
                ai_config['market_analyst']['schedule']['restrictions']['night_block'] = {}
            
            ai_config['market_analyst']['schedule']['restrictions']['night_block']['enabled'] = self.night_block.get()
            
            if 'weekend_block' not in ai_config['market_analyst']['schedule']['restrictions']:
                ai_config['market_analyst']['schedule']['restrictions']['weekend_block'] = {}
            
            ai_config['market_analyst']['schedule']['restrictions']['weekend_block']['enabled'] = self.weekend_block.get()
            
            # Signal filters
            if 'signals' not in ai_config['market_analyst']:
                ai_config['market_analyst']['signals'] = {}
            
            ai_config['market_analyst']['signals']['min_confidence'] = int(self.min_confidence.get())
            ai_config['market_analyst']['signals']['min_rr'] = float(self.min_rr.get())
            
            # Обновить Portfolio config
            portfolio_config = self.configs.get('portfolio.yaml', {})
            
            if 'portfolio' not in portfolio_config:
                portfolio_config['portfolio'] = {}
            
            if 'risk_model' not in portfolio_config['portfolio']:
                portfolio_config['portfolio']['risk_model'] = {}
            
            portfolio_config['portfolio']['risk_model']['max_total_exposure'] = float(self.risk_per_trade.get())
            
            # Обновить Trading config
            trading_config = self.configs.get('trading.yaml', {})
            
            if 'trading' not in trading_config:
                trading_config['trading'] = {}
            
            # Risk settings
            if 'risk' not in trading_config['trading']:
                trading_config['trading']['risk'] = {}
            
            trading_config['trading']['risk']['max_lot_size'] = float(self.max_lot.get())
            trading_config['trading']['risk']['default_sl_pips'] = int(self.default_sl.get())
            trading_config['trading']['risk']['default_tp_pips'] = int(self.default_tp.get())
            
            # Trailing stop
            if 'trailing_stop' not in trading_config['trading']:
                trading_config['trading']['trailing_stop'] = {}
            
            trading_config['trading']['trailing_stop']['enabled'] = self.trail_enabled.get()
            trading_config['trading']['trailing_stop']['distance_pips'] = int(self.trail_distance.get())
            
            # Trading hours
            if 'hours' not in trading_config['trading']:
                trading_config['trading']['hours'] = {}
            
            trading_config['trading']['hours']['start'] = self.trade_start.get()
            trading_config['trading']['hours']['end'] = self.trade_end.get()
            
            # Indicators
            if 'indicators' not in trading_config['trading']:
                trading_config['trading']['indicators'] = {}
            
            # Parse timeframes
            tf_str = self.timeframes.get()
            tf_list = [t.strip() for t in tf_str.split(',') if t.strip()]
            trading_config['trading']['indicators']['timeframes'] = tf_list
            
            # Parse EMA periods
            ema_str = self.ema_periods.get()
            ema_list = [int(p.strip()) for p in ema_str.split(',') if p.strip()]
            trading_config['trading']['indicators']['ema_periods'] = ema_list
            
            trading_config['trading']['indicators']['rsi_period'] = int(self.rsi_period.get())
            trading_config['trading']['indicators']['atr_period'] = int(self.atr_period.get())
            
            # SMC settings
            if 'smc' not in trading_config['trading']:
                trading_config['trading']['smc'] = {}
            
            trading_config['trading']['smc']['enabled'] = self.smc_enabled.get()
            trading_config['trading']['smc']['order_blocks'] = self.ob_enabled.get()
            trading_config['trading']['smc']['fair_value_gaps'] = self.fvg_enabled.get()
            
            # Trend filter
            if 'trend_filter' not in trading_config['trading']:
                trading_config['trading']['trend_filter'] = {}
            
            trading_config['trading']['trend_filter']['enabled'] = self.trend_filter.get()
            
            # Обновить Telegram config
            telegram_config = {}
            telegram_path = Path('config') / 'telegram.yaml'
            if telegram_path.exists():
                with open(telegram_path, 'r', encoding='utf-8') as f:
                    telegram_config = yaml.safe_load(f) or {}
            
            if 'telegram' not in telegram_config:
                telegram_config['telegram'] = {}
            
            telegram_config['telegram']['enabled'] = self.telegram_enabled.get()
            telegram_config['telegram']['bot_token'] = self.telegram_token.get()
            telegram_config['telegram']['chat_id'] = self.telegram_chat_id.get()
            telegram_config['telegram']['enable_bot'] = self.telegram_enable_bot.get()
            
            if 'notify' not in telegram_config['telegram']:
                telegram_config['telegram']['notify'] = {}
            
            telegram_config['telegram']['notify']['startup'] = self.notify_startup.get()
            telegram_config['telegram']['notify']['trade_opened'] = self.notify_trade_opened.get()
            telegram_config['telegram']['notify']['trade_closed'] = self.notify_trade_closed.get()
            telegram_config['telegram']['notify']['daily_report'] = self.notify_daily_report.get()
            telegram_config['telegram']['notify']['alerts'] = self.notify_alerts.get()
            telegram_config['telegram']['alert_min_level'] = self.alert_min_level.get()
            
            # Сохранить GPT API key в .env
            env_path = Path('.env')
            env_lines = []
            api_key_updated = False
            
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add OPENAI_API_KEY
            new_api_key = self.gpt_api_key.get().strip()
            if new_api_key:
                for i, line in enumerate(env_lines):
                    if line.startswith('OPENAI_API_KEY='):
                        env_lines[i] = f'OPENAI_API_KEY={new_api_key}\n'
                        api_key_updated = True
                        break
                
                if not api_key_updated:
                    env_lines.append(f'OPENAI_API_KEY={new_api_key}\n')
                
                with open(env_path, 'w') as f:
                    f.writelines(env_lines)
                
                # Update environment variable
                import os
                os.environ['OPENAI_API_KEY'] = new_api_key
            
            # Сохранить файлы
            ai_path = Path('config') / 'ai.yaml'
            with open(ai_path, 'w', encoding='utf-8') as f:
                yaml.dump(ai_config, f, default_flow_style=False, allow_unicode=True)
            
            portfolio_path = Path('config') / 'portfolio.yaml'
            with open(portfolio_path, 'w', encoding='utf-8') as f:
                yaml.dump(portfolio_config, f, default_flow_style=False, allow_unicode=True)
            
            trading_path = Path('config') / 'trading.yaml'
            with open(trading_path, 'w', encoding='utf-8') as f:
                yaml.dump(trading_config, f, default_flow_style=False, allow_unicode=True)
            
            with open(telegram_path, 'w', encoding='utf-8') as f:
                yaml.dump(telegram_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("="*80)
            logger.info("[SETTINGS] ✅ Все настройки успешно сохранены")
            logger.info("="*80)
            messagebox.showinfo("Success", "Settings saved!\nRestart bot to apply changes.")
            
            # Вызвать callback
            if self.on_save_callback:
                self.on_save_callback()
            
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")

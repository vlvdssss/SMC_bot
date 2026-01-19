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
    BG_HOVER = '#30363d'       # Hover эффект
    TEXT_PRIMARY = '#c9d1d9'
    TEXT_SECONDARY = '#8b949e'
    TEXT_MUTED = '#6e7681'
    BORDER = '#30363d'
    PRIMARY = '#1f6feb'       # Синий (для кнопок)
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
        self.instruments_tab = self._create_instruments_tab()
        self.trading_tab = self._create_trading_tab()
        self.ai_tab = self._create_ai_tab()
        self.schedule_tab = self._create_schedule_tab()  # NEW: AI Schedule tab
        self.strategy_tab = self._create_strategy_tab()
        self.gpt_api_tab = self._create_gpt_api_tab()
        self.telegram_tab = self._create_telegram_tab()
        
        self.notebook.add(self.instruments_tab, text='📈 Instruments')
        self.notebook.add(self.trading_tab, text='💰 Trading')
        self.notebook.add(self.ai_tab, text='🤖 AI')
        self.notebook.add(self.schedule_tab, text='⏰ Schedule')  # NEW
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
        
        # Save & Apply (без перезапуска)
        tk.Button(button_frame, text="Save & Apply",
                 font=('Arial', 11),
                 bg=Colors.PRIMARY,
                 fg='white',
                 relief='flat',
                 padx=20, pady=10,
                 command=self._save_settings).pack(side='right', padx=(0, 10))
        
        # Apply & Restart (сохранить + перезапустить бота)
        tk.Button(button_frame, text="Apply & Restart",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=20, pady=10,
                 command=self._save_and_restart).pack(side='right')
    
    def _create_instruments_tab(self):
        """Настройки инструментов (XAUUSD, EURUSD)"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Загружаем конфиг
        instruments_config = {}
        try:
            instruments_path = Path('config/instruments.yaml')
            if instruments_path.exists():
                with open(instruments_path, 'r', encoding='utf-8') as f:
                    instruments_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load instruments config: {e}")
        
        # === XAUUSD (GOLD) ===
        self._create_section(content, "🥇 XAUUSD (Золото)")
        
        xauusd_config = instruments_config.get('instruments', {}).get('XAUUSD', {})
        
        # General Enable
        xauusd_enabled_frame = self._create_setting_row(content, "Включить инструмент")
        self.xauusd_enabled = tk.BooleanVar(value=xauusd_config.get('enabled', True))
        tk.Checkbutton(xauusd_enabled_frame, variable=self.xauusd_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Analysis Enable
        xauusd_analysis_frame = self._create_setting_row(content, "📊 GPT Анализ (скриншоты + сигналы)")
        self.xauusd_analysis = tk.BooleanVar(value=xauusd_config.get('analysis_enabled', True))
        tk.Checkbutton(xauusd_analysis_frame, variable=self.xauusd_analysis,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Trading Enable
        xauusd_trading_frame = self._create_setting_row(content, "💰 Торговля (вход в сделки)")
        self.xauusd_trading = tk.BooleanVar(value=xauusd_config.get('trading_enabled', True))
        tk.Checkbutton(xauusd_trading_frame, variable=self.xauusd_trading,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Info
        tk.Label(content, 
                text="💡 Если GPT Анализ выключен - бот не будет делать скриншоты и запрашивать сигналы у GPT\n"
                     "   Если Торговля выключена - сигналы будут генерироваться, но сделки не откроются",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(fill='x', pady=(5, 15), padx=20)
        
        # Separator
        tk.Frame(content, bg=Colors.BORDER, height=2).pack(fill='x', pady=15)
        
        # === EURUSD ===
        self._create_section(content, "💶 EURUSD (Евро/Доллар)")
        
        eurusd_config = instruments_config.get('instruments', {}).get('EURUSD', {})
        
        # General Enable
        eurusd_enabled_frame = self._create_setting_row(content, "Включить инструмент")
        self.eurusd_enabled = tk.BooleanVar(value=eurusd_config.get('enabled', True))
        tk.Checkbutton(eurusd_enabled_frame, variable=self.eurusd_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Analysis Enable
        eurusd_analysis_frame = self._create_setting_row(content, "📊 GPT Анализ (скриншоты + сигналы)")
        self.eurusd_analysis = tk.BooleanVar(value=eurusd_config.get('analysis_enabled', True))
        tk.Checkbutton(eurusd_analysis_frame, variable=self.eurusd_analysis,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Trading Enable
        eurusd_trading_frame = self._create_setting_row(content, "💰 Торговля (вход в сделки)")
        self.eurusd_trading = tk.BooleanVar(value=eurusd_config.get('trading_enabled', True))
        tk.Checkbutton(eurusd_trading_frame, variable=self.eurusd_trading,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Info
        tk.Label(content, 
                text="💡 Если GPT Анализ выключен - бот не будет делать скриншоты и запрашивать сигналы у GPT\n"
                     "   Если Торговля выключена - сигналы будут генерироваться, но сделки не откроются",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(fill='x', pady=(5, 15), padx=20)
        
        # Update scroll region
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
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
        self._create_section(content, "💰 Risk Management (Управление Рисками)")
        
        portfolio_config = self.configs.get('portfolio.yaml', {})
        trading_config = self.configs.get('trading.yaml', {})
        risk_config = trading_config.get('trading', {}).get('risk', {})
        
        # Risk per trade - УПРОЩЁННОЕ ОБЪЯСНЕНИЕ
        risk_frame = self._create_setting_row(content, "💵 Риск на сделку (% от баланса)")
        self.risk_per_trade = tk.Entry(risk_frame, font=('Arial', 10), width=10)
        self.risk_per_trade.insert(0, str(portfolio_config.get('portfolio', {}).get('risk_model', {}).get('max_total_exposure', 1.25)))
        self.risk_per_trade.pack(side='right')
        self._bind_paste(self.risk_per_trade)
        
        # Подсказка для Risk
        risk_hint = tk.Label(content, 
                            text="💡 Пример: 1% при балансе $10,000 = максимум $100 риска на сделку",
                            font=('Arial', 8, 'italic'),
                            bg=Colors.BG_DARK,
                            fg=Colors.TEXT_MUTED,
                            justify='left')
        risk_hint.pack(fill='x', pady=(2, 5), padx=20)
        
        # Max lot size - УПРОЩЁННОЕ ОБЪЯСНЕНИЕ
        lot_frame = self._create_setting_row(content, "📊 Максимальный лот (объём позиции)")
        self.max_lot = tk.Entry(lot_frame, font=('Arial', 10), width=10)
        self.max_lot.insert(0, str(risk_config.get('max_lot_size', 1.0)))
        self.max_lot.pack(side='right')
        self._bind_paste(self.max_lot)
        
        # Подсказка для Lot Size с ДЕНЬГАМИ
        lot_hint = tk.Label(content, 
                           text="💡 1 лот = $100,000 (EURUSD) или ~$200,000 (XAUUSD на золото)\n"
                                "   0.01 лот = $1,000 | 0.1 лот = $10,000 | 1.0 лот = $100,000\n"
                                "   Рекомендация: 0.01-0.1 для безопасной торговли",
                           font=('Arial', 8, 'italic'),
                           bg=Colors.BG_DARK,
                           fg=Colors.TEXT_MUTED,
                           justify='left')
        lot_hint.pack(fill='x', pady=(2, 5), padx=20)
        
        # Кнопка для открытия подробного руководства
        help_btn_frame = tk.Frame(content, bg=Colors.BG_DARK)
        help_btn_frame.pack(fill='x', pady=(0, 10), padx=20)
        
        help_btn = tk.Button(help_btn_frame,
                            text="📖 Открыть подробное руководство по размеру лота",
                            font=('Arial', 9),
                            bg=Colors.BG_CARD,
                            fg=Colors.PRIMARY,
                            activebackground=Colors.BG_HOVER,
                            activeforeground=Colors.PRIMARY,
                            relief='flat',
                            cursor='hand2',
                            command=self._open_lot_size_guide)
        help_btn.pack(pady=3)
        
        # Stop Loss / Take Profit
        self._create_section(content, "Stop Loss / Take Profit")
        
        sl_frame = self._create_setting_row(content, "Default SL (pips)")
        self.default_sl = tk.Entry(sl_frame, font=('Arial', 10), width=10)
        self.default_sl.insert(0, str(risk_config.get('default_sl_pips', 50)))
        self.default_sl.pack(side='right')
        self._bind_paste(self.default_sl)
        
        tp_frame = self._create_setting_row(content, "Default TP (pips)")
        self.default_tp = tk.Entry(tp_frame, font=('Arial', 10), width=10)
        self.default_tp.insert(0, str(risk_config.get('default_tp_pips', 100)))
        self.default_tp.pack(side='right')
        self._bind_paste(self.default_tp)
        
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
        self._bind_paste(self.trail_distance)
        
        # Trading Hours
        self._create_section(content, "Trading Hours (UTC)")
        
        hours_config = trading_config.get('trading', {}).get('hours', {})
        
        start_frame = self._create_setting_row(content, "Start time")
        self.trade_start = tk.Entry(start_frame, font=('Arial', 10), width=10)
        self.trade_start.insert(0, hours_config.get('start', '02:00'))
        self.trade_start.pack(side='right')
        self._bind_paste(self.trade_start)
        
        end_frame = self._create_setting_row(content, "End time")
        self.trade_end = tk.Entry(end_frame, font=('Arial', 10), width=10)
        self.trade_end.insert(0, hours_config.get('end', '22:00'))
        self.trade_end.pack(side='right')
        self._bind_paste(self.trade_end)
        
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
        self._bind_paste(self.temperature)
        
        # Analysis Schedule - moved to Schedule tab
        # See _create_schedule_tab() for schedule configuration
        
        # Filters
        self._create_section(content, "Signal Filters")
        
        signals_config = ai_config.get('market_analyst', {}).get('signals', {})
        
        conf_frame = self._create_setting_row(content, "Min confidence (%)")
        self.min_confidence = tk.Entry(conf_frame, font=('Arial', 10), width=10)
        self.min_confidence.insert(0, str(signals_config.get('min_confidence', 70)))
        self.min_confidence.pack(side='right')
        self._bind_paste(self.min_confidence)
        
        rr_frame = self._create_setting_row(content, "Min Risk/Reward ratio")
        self.min_rr = tk.Entry(rr_frame, font=('Arial', 10), width=10)
        self.min_rr.insert(0, str(signals_config.get('min_rr', 1.5)))
        self.min_rr.pack(side='right')
        self._bind_paste(self.min_rr)
        
        validity_frame = self._create_setting_row(content, "⏱ AI Signal TTL (мин): 15/30/60")
        self.signal_validity = tk.Entry(validity_frame, font=('Arial', 10), width=10)
        self.signal_validity.insert(0, str(signals_config.get('validity_minutes', 60)))
        self.signal_validity.pack(side='right')
        self._bind_paste(self.signal_validity)
        
        # Подсказка о TTL сигнала
        ttl_hint = tk.Label(content, 
                           text="💡 Время жизни AI сигнала. По истечению TTL сигнал либо отыгрывает, либо аннулируется.",
                           font=('Arial', 8, 'italic'),
                           bg=Colors.BG_DARK,
                           fg=Colors.TEXT_MUTED,
                           wraplength=450,
                           justify='left')
        ttl_hint.pack(fill='x', pady=(2, 10), padx=20)
        
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
    
    def _create_schedule_tab(self):
        """Create AI Schedule configuration tab with Time Picker + List"""
        from datetime import datetime, timedelta
        
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Load current config
        ai_config = self.configs.get('ai.yaml', {})
        schedule_config = ai_config.get('market_analyst', {}).get('schedule', {})
        
        # === HEADER ===
        header_frame = tk.Frame(content, bg=Colors.BG_DARK)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(header_frame, text="🕐 AI Analysis Schedule",
                font=('Arial', 16, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w')
        
        tk.Label(header_frame, text="Configure when AI should analyze market conditions",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(5, 0))
        
        # === ENABLE SCHEDULE ===
        self._create_section(content, "Enable Schedule")
        
        enable_frame = self._create_setting_row(content, "Enable scheduled analysis")
        self.schedule_enabled = tk.BooleanVar(value=schedule_config.get('enabled', True))
        tk.Checkbutton(enable_frame, variable=self.schedule_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # === TIME PICKER ===
        self._create_section(content, "Add Analysis Time")
        
        picker_frame = tk.Frame(content, bg=Colors.BG_CARD, padx=15, pady=15)
        picker_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        tk.Label(picker_frame, text="Add time:",
                font=('Arial', 10),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY).pack(side='left', padx=(0, 10))
        
        # Time picker (HH:MM)
        time_picker_frame = tk.Frame(picker_frame, bg=Colors.BG_CARD)
        time_picker_frame.pack(side='left', padx=(0, 10))
        
        # Hour spinbox
        self.hour_var = tk.StringVar(value="06")
        hour_spin = tk.Spinbox(time_picker_frame, from_=0, to=23, 
                              textvariable=self.hour_var,
                              font=('Arial', 11),
                              width=3,
                              format="%02.0f",
                              bg=Colors.BG_DARK,
                              fg=Colors.TEXT_PRIMARY,
                              buttonbackground=Colors.BG_PANEL,
                              relief='flat')
        hour_spin.pack(side='left', padx=(0, 5))
        
        tk.Label(time_picker_frame, text=":",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY).pack(side='left')
        
        # Minute spinbox
        self.minute_var = tk.StringVar(value="00")
        minute_spin = tk.Spinbox(time_picker_frame, from_=0, to=59,
                                textvariable=self.minute_var,
                                font=('Arial', 11),
                                width=3,
                                format="%02.0f",
                                bg=Colors.BG_DARK,
                                fg=Colors.TEXT_PRIMARY,
                                buttonbackground=Colors.BG_PANEL,
                                relief='flat')
        minute_spin.pack(side='left', padx=(5, 0))
        
        # Add button
        tk.Button(picker_frame, text="+ Add",
                 font=('Arial', 10, 'bold'),
                 bg=Colors.PRIMARY,
                 fg='white',
                 relief='flat',
                 padx=15, pady=5,
                 command=self._add_time).pack(side='left', padx=(0, 10))
        
        # Quick add buttons
        tk.Button(picker_frame, text="Every Hour",
                 font=('Arial', 9),
                 bg=Colors.BG_PANEL,
                 fg=Colors.TEXT_PRIMARY,
                 relief='flat',
                 padx=10, pady=5,
                 command=lambda: self._quick_add('hour')).pack(side='left', padx=2)
        
        tk.Button(picker_frame, text="Every 2h",
                 font=('Arial', 9),
                 bg=Colors.BG_PANEL,
                 fg=Colors.TEXT_PRIMARY,
                 relief='flat',
                 padx=10, pady=5,
                 command=lambda: self._quick_add('2hour')).pack(side='left', padx=2)
        
        tk.Button(picker_frame, text="Clear All",
                 font=('Arial', 9),
                 bg=Colors.DANGER,
                 fg='white',
                 relief='flat',
                 padx=10, pady=5,
                 command=self._clear_all_times).pack(side='left', padx=2)
        
        # === SCHEDULED TIMES LIST ===
        self._create_section(content, "Scheduled Times")
        
        list_frame = tk.Frame(content, bg=Colors.BG_CARD, padx=15, pady=15)
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        # Scrollable list
        list_canvas = tk.Canvas(list_frame, bg=Colors.BG_CARD, 
                               highlightthickness=0, height=200)
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', 
                                      command=list_canvas.yview)
        self.times_list_content = tk.Frame(list_canvas, bg=Colors.BG_CARD)
        
        self.times_list_content.bind('<Configure>', 
                                    lambda e: list_canvas.configure(scrollregion=list_canvas.bbox('all')))
        list_canvas.create_window((0, 0), window=self.times_list_content, anchor='nw')
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        
        list_canvas.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')
        
        # Load existing times
        self.scheduled_times = schedule_config.get('times', [])
        self._refresh_times_list()
        
        # === STATISTICS ===
        stats_frame = tk.Frame(content, bg=Colors.BG_PANEL, padx=15, pady=15)
        stats_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.stats_label = tk.Label(stats_frame, text="",
                                    font=('Arial', 10),
                                    bg=Colors.BG_PANEL,
                                    fg=Colors.TEXT_PRIMARY,
                                    justify='left')
        self.stats_label.pack(anchor='w')
        
        self._update_stats()
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _add_time(self):
        """Add time to scheduled list"""
        hour = self.hour_var.get().zfill(2)
        minute = self.minute_var.get().zfill(2)
        time_str = f"{hour}:{minute}"
        
        if time_str not in self.scheduled_times:
            self.scheduled_times.append(time_str)
            self.scheduled_times.sort()
            self._refresh_times_list()
            self._update_stats()
    
    def _remove_time(self, time_str):
        """Remove time from scheduled list"""
        if time_str in self.scheduled_times:
            self.scheduled_times.remove(time_str)
            self._refresh_times_list()
            self._update_stats()
    
    def _quick_add(self, mode):
        """Quick add preset times"""
        self.scheduled_times.clear()
        
        if mode == 'hour':
            # Every hour (00:00, 01:00, 02:00, ...)
            for h in range(24):
                self.scheduled_times.append(f"{h:02d}:00")
        elif mode == '2hour':
            # Every 2 hours (00:00, 02:00, 04:00, ...)
            for h in range(0, 24, 2):
                self.scheduled_times.append(f"{h:02d}:00")
        
        self.scheduled_times.sort()
        self._refresh_times_list()
        self._update_stats()
    
    def _clear_all_times(self):
        """Clear all scheduled times"""
        self.scheduled_times.clear()
        self._refresh_times_list()
        self._update_stats()
    
    def _refresh_times_list(self):
        """Refresh the times list display"""
        # Clear existing items
        for widget in self.times_list_content.winfo_children():
            widget.destroy()
        
        if not self.scheduled_times:
            tk.Label(self.times_list_content, 
                    text="No scheduled times. Add times using the picker above.",
                    font=('Arial', 10, 'italic'),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(pady=20)
            return
        
        # Add each time as a row
        for time_str in self.scheduled_times:
            row = tk.Frame(self.times_list_content, bg=Colors.BG_DARK, padx=10, pady=5)
            row.pack(fill='x', pady=2)
            
            # Time label
            tk.Label(row, text=f"• {time_str}",
                    font=('Arial', 11),
                    bg=Colors.BG_DARK,
                    fg=Colors.TEXT_PRIMARY).pack(side='left')
            
            # Remove button
            tk.Button(row, text="Remove",
                     font=('Arial', 9),
                     bg=Colors.DANGER,
                     fg='white',
                     relief='flat',
                     padx=10, pady=2,
                     command=lambda t=time_str: self._remove_time(t)).pack(side='right')
    
    def _update_stats(self):
        """Update statistics display"""
        from datetime import datetime, timedelta
        
        count = len(self.scheduled_times)
        
        # Calculate next analysis time
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        next_time = None
        for time_str in self.scheduled_times:
            if time_str > current_time:
                next_time = time_str
                break
        
        if not next_time and self.scheduled_times:
            next_time = self.scheduled_times[0]  # Tomorrow
        
        # Estimate cost (~$0.30 per analysis)
        estimated_cost = count * 0.30
        
        stats_text = f"📊 Times per day: {count}\n"
        
        if next_time:
            stats_text += f"⏰ Next analysis: {next_time}\n"
        
        stats_text += f"💰 Est. cost: ~${estimated_cost:.2f}/day (~${estimated_cost * 30:.2f}/month)"
        
        self.stats_label.config(text=stats_text)
    
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
        self._bind_paste(self.timeframes)
        
        # Indicators
        self._create_section(content, "Indicators")
        
        ema_frame = self._create_setting_row(content, "EMA periods")
        self.ema_periods = tk.Entry(ema_frame, font=('Arial', 10), width=20)
        current_emas = indicators_config.get('ema_periods', [20, 50, 200])
        self.ema_periods.insert(0, ', '.join(map(str, current_emas)))
        self.ema_periods.pack(side='right')
        self._bind_paste(self.ema_periods)
        
        rsi_frame = self._create_setting_row(content, "RSI period")
        self.rsi_period = tk.Entry(rsi_frame, font=('Arial', 10), width=10)
        self.rsi_period.insert(0, str(indicators_config.get('rsi_period', 14)))
        self.rsi_period.pack(side='right')
        self._bind_paste(self.rsi_period)
        
        atr_frame = self._create_setting_row(content, "ATR period")
        self.atr_period = tk.Entry(atr_frame, font=('Arial', 10), width=10)
        self.atr_period.insert(0, str(indicators_config.get('atr_period', 14)))
        self.atr_period.pack(side='right')
        self._bind_paste(self.atr_period)
        
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
        
        self.gpt_api_key = tk.Entry(api_key_frame, font=('Arial', 10), width=40, show='*')
        
        # Загрузить существующий API ключ из .env
        try:
            import os
            from dotenv import load_dotenv
            env_path = Path('.env')
            if env_path.exists():
                load_dotenv(env_path)
                existing_key = os.getenv('OPENAI_API_KEY', '')
                if existing_key:
                    self.gpt_api_key.insert(0, existing_key)
                    logger.info(f"[SETTINGS] Loaded existing API key: {len(existing_key)} chars")
        except Exception as e:
            logger.warning(f"[SETTINGS] Failed to load API key from .env: {e}")
        
        self.gpt_api_key.pack(side='left', padx=(0, 5))
        
        # Добавить поддержку вставки Ctrl+V
        self._bind_paste(self.gpt_api_key)
        
        # Paste button
        def paste_api_key():
            try:
                text = self.dialog.clipboard_get()
                if text:
                    self.gpt_api_key.delete(0, tk.END)
                    self.gpt_api_key.insert(0, text)
                    logger.info(f"[SETTINGS] Pasted API key via Paste button: {len(text)} chars")
            except Exception as e:
                logger.error(f"[SETTINGS] Paste button failed: {e}")
                messagebox.showerror("Paste Error", f"Failed to paste from clipboard: {e}")
        
        paste_btn = tk.Button(api_key_frame, text="📋 Paste",
                             font=('Arial', 9),
                             bg=Colors.SUCCESS,
                             fg='white',
                             relief='flat',
                             padx=10, pady=3,
                             command=paste_api_key)
        paste_btn.pack(side='left', padx=(0, 5))
        
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
        
        token_entry_frame = tk.Frame(token_frame, bg=Colors.BG_DARK)
        token_entry_frame.pack(side='right')
        
        self.telegram_token = tk.Entry(token_entry_frame, font=('Arial', 10), width=30, show='*')
        self.telegram_token.insert(0, telegram_settings.get('bot_token', ''))
        self.telegram_token.pack(side='left', padx=(0, 5))
        self._bind_paste(self.telegram_token)
        
        # Paste button for token
        def paste_token():
            try:
                text = self.dialog.clipboard_get()
                if text:
                    self.telegram_token.delete(0, tk.END)
                    self.telegram_token.insert(0, text)
                    logger.info(f"[SETTINGS] Pasted Telegram token: {len(text)} chars")
            except Exception as e:
                logger.error(f"[SETTINGS] Paste token failed: {e}")
                messagebox.showerror("Paste Error", f"Failed to paste: {e}")
        
        tk.Button(token_entry_frame, text="📋",
                 font=('Arial', 9),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=8, pady=3,
                 command=paste_token).pack(side='left')
        
        # Chat ID
        chat_frame = self._create_setting_row(content, "Chat ID:")
        
        chat_entry_frame = tk.Frame(chat_frame, bg=Colors.BG_DARK)
        chat_entry_frame.pack(side='right')
        
        self.telegram_chat_id = tk.Entry(chat_entry_frame, font=('Arial', 10), width=30)
        self.telegram_chat_id.insert(0, telegram_settings.get('chat_id', ''))
        self.telegram_chat_id.pack(side='left', padx=(0, 5))
        self._bind_paste(self.telegram_chat_id)
        
        # Paste button for chat_id
        def paste_chat_id():
            try:
                text = self.dialog.clipboard_get()
                if text:
                    self.telegram_chat_id.delete(0, tk.END)
                    self.telegram_chat_id.insert(0, text)
                    logger.info(f"[SETTINGS] Pasted Chat ID: {len(text)} chars")
            except Exception as e:
                logger.error(f"[SETTINGS] Paste chat_id failed: {e}")
                messagebox.showerror("Paste Error", f"Failed to paste: {e}")
        
        tk.Button(chat_entry_frame, text="📋",
                 font=('Arial', 9),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=8, pady=3,
                 command=paste_chat_id).pack(side='left')
        
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
            
            # Analysis times from new Schedule tab (Time Picker + List)
            ai_config['market_analyst']['schedule']['times'] = self.scheduled_times
            
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
            ai_config['market_analyst']['signals']['validity_minutes'] = int(self.signal_validity.get())
            
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
            
            # Сохранить Instruments config
            instruments_path = Path('config') / 'instruments.yaml'
            instruments_config = {}
            if instruments_path.exists():
                with open(instruments_path, 'r', encoding='utf-8') as f:
                    instruments_config = yaml.safe_load(f) or {}
            
            if 'instruments' not in instruments_config:
                instruments_config['instruments'] = {}
            
            # Update XAUUSD
            if 'XAUUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['XAUUSD'] = {}
            instruments_config['instruments']['XAUUSD']['enabled'] = self.xauusd_enabled.get()
            instruments_config['instruments']['XAUUSD']['analysis_enabled'] = self.xauusd_analysis.get()
            instruments_config['instruments']['XAUUSD']['trading_enabled'] = self.xauusd_trading.get()
            
            # Update EURUSD
            if 'EURUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['EURUSD'] = {}
            instruments_config['instruments']['EURUSD']['enabled'] = self.eurusd_enabled.get()
            instruments_config['instruments']['EURUSD']['analysis_enabled'] = self.eurusd_analysis.get()
            instruments_config['instruments']['EURUSD']['trading_enabled'] = self.eurusd_trading.get()
            
            with open(instruments_path, 'w', encoding='utf-8') as f:
                yaml.dump(instruments_config, f, default_flow_style=False, allow_unicode=True)
            
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
    
    def _save_and_restart(self):
        """Сохранить настройки и перезапустить бота"""
        try:
            # Сначала сохраняем все настройки (используем код из _save_settings)
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
            
            # Analysis times from Schedule tab
            ai_config['market_analyst']['schedule']['times'] = self.scheduled_times
            
            # AI signal validity
            ai_config['market_analyst']['signal_validity_minutes'] = int(self.signal_validity.get())
            
            # Обновить Portfolio config
            portfolio_config = self.configs.get('portfolio.yaml', {})
            if 'portfolio' not in portfolio_config:
                portfolio_config['portfolio'] = {}
            
            # Сохраняем только risk_per_trade (max_total_exposure)
            if 'risk_model' not in portfolio_config.get('portfolio', {}):
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
            
            # Сохранить Instruments config
            instruments_path = Path('config') / 'instruments.yaml'
            instruments_config = {}
            if instruments_path.exists():
                with open(instruments_path, 'r', encoding='utf-8') as f:
                    instruments_config = yaml.safe_load(f) or {}
            
            if 'instruments' not in instruments_config:
                instruments_config['instruments'] = {}
            
            # Update XAUUSD
            if 'XAUUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['XAUUSD'] = {}
            instruments_config['instruments']['XAUUSD']['enabled'] = self.xauusd_enabled.get()
            instruments_config['instruments']['XAUUSD']['analysis_enabled'] = self.xauusd_analysis.get()
            instruments_config['instruments']['XAUUSD']['trading_enabled'] = self.xauusd_trading.get()
            
            # Update EURUSD
            if 'EURUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['EURUSD'] = {}
            instruments_config['instruments']['EURUSD']['enabled'] = self.eurusd_enabled.get()
            instruments_config['instruments']['EURUSD']['analysis_enabled'] = self.eurusd_analysis.get()
            instruments_config['instruments']['EURUSD']['trading_enabled'] = self.eurusd_trading.get()
            
            with open(instruments_path, 'w', encoding='utf-8') as f:
                yaml.dump(instruments_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("="*80)
            logger.info("[SETTINGS] ✅ Settings saved, restarting bot...")
            logger.info("="*80)
            
            # Перезапускаем бота через callback
            if self.on_save_callback:
                # Закрываем диалог
                self.dialog.destroy()
                
                # Вызываем callback с флагом restart
                self.on_save_callback(restart=True)
                
                messagebox.showinfo("Success", "Settings saved!\nBot restarted with new configuration.")
            else:
                messagebox.showwarning("Warning", "Settings saved but bot restart not available.\nPlease restart manually.")
                self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save and restart: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
    
    def _open_lot_size_guide(self):
        """Открыть руководство по размеру лота"""
        try:
            import os
            import subprocess
            from pathlib import Path
            
            guide_path = Path('docs') / 'LOT_SIZE_GUIDE.md'
            
            if not guide_path.exists():
                messagebox.showwarning(
                    "Руководство не найдено",
                    "Файл LOT_SIZE_GUIDE.md не найден в папке docs/\n\n"
                    "Создайте его или скачайте из репозитория проекта."
                )
                return
            
            # Открыть файл в системном редакторе для Markdown
            if os.name == 'nt':  # Windows
                os.startfile(guide_path)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.run(['xdg-open', guide_path])
            
            logger.info(f"[SETTINGS] Opened lot size guide: {guide_path}")
            
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to open guide: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть руководство:\n{e}")
    
    def _bind_paste(self, entry_widget):
        """Добавить поддержку Ctrl+V для Entry виджета"""
        def paste(event=None):
            try:
                # Получить текст из буфера обмена через Tkinter
                text = self.dialog.clipboard_get()
                if text:
                    # Очистить поле и вставить текст
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, text)
                    logger.info(f"[SETTINGS] Pasted text via Ctrl+V: {len(text)} chars")
                return 'break'
            except Exception as e:
                logger.error(f"[SETTINGS] Paste failed: {e}")
                return 'break'
        
        # Привязать Ctrl+V
        entry_widget.bind('<Control-v>', paste)
        entry_widget.bind('<Control-V>', paste)
        
        # Добавить контекстное меню (правая кнопка мыши)
        def show_menu(event):
            menu = tk.Menu(entry_widget, tearoff=0)
            menu.add_command(label="Paste (Ctrl+V)", command=lambda: paste())
            menu.post(event.x_root, event.y_root)
        
        entry_widget.bind('<Button-3>', show_menu)

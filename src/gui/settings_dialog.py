#!/usr/bin/env python3
"""
Settings Dialog - Управление настройками бота
"""

import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from pathlib import Path
from datetime import datetime
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
    ACCENT = '#1f6feb'        # Alias for PRIMARY (синий акцент)
    SUCCESS = '#3fb950'
    WARNING = '#d29922'
    ERROR = '#f85149'
    INFO = '#58a6ff'          # Информация (синий)


class SettingsDialog:
    """Диалог настроек"""
    
    def __init__(self, parent, on_save_callback):
        self.parent = parent
        self.on_save_callback = on_save_callback
        self.configs = {}
        
        # Создать окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("⚙ Settings")
        self.dialog.geometry("1200x800")
        self.dialog.configure(bg=Colors.BG_DARK)
        self.dialog.resizable(True, True)
        
        # Минимальный размер
        self.dialog.minsize(1000, 700)
        
        # Сделать модальным
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Загрузить конфиги
        self._load_configs()
        
        # Создать UI
        self._create_ui()
        
        # Центрировать окно
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (800 // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _load_configs(self):
        """Загрузить конфиги"""
        try:
            config_files = ['ai.yaml', 'portfolio.yaml', 'trading.yaml', 'telegram.yaml']
            
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
        self.trading_tab = self._create_trading_tab()  # Now includes AI settings
        # self.ai_tab = self._create_ai_tab()  # MERGED into Trading tab
        # self.strategy_tab = self._create_strategy_tab()  # REMOVED: Unused tab
        self.quick_actions_tab = self._create_quick_actions_tab()  # NEW: Quick Actions
        self.safety_tab = self._create_safety_tab()  # NEW: Safety & Limits
        self.advanced_tab = self._create_advanced_tab()  # NEW: Advanced Settings
        self.v5_tab = self._create_v5_tab()  # NEW: V5 Improvements
        
        # Create GPT API and Telegram tabs with error handling
        try:
            logger.info("[SETTINGS] Creating GPT API tab...")
            self.gpt_api_tab = self._create_gpt_api_tab()
            logger.info("[SETTINGS] GPT API tab created successfully")
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to create GPT API tab: {e}", exc_info=True)
            self.gpt_api_tab = None
        
        try:
            logger.info("[SETTINGS] Creating Telegram tab...")
            self.telegram_tab = self._create_telegram_tab()
            logger.info("[SETTINGS] Telegram tab created successfully")
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to create Telegram tab: {e}", exc_info=True)
            self.telegram_tab = None
        
        self.notebook.add(self.instruments_tab, text='📈 Instruments')
        self.notebook.add(self.trading_tab, text='💰 Trading & AI')
        # self.notebook.add(self.ai_tab, text='🤖 AI')  # MERGED into Trading
        # self.notebook.add(self.strategy_tab, text='📊 Strategy')  # REMOVED
        self.notebook.add(self.quick_actions_tab, text='⚡ Quick Actions')
        self.notebook.add(self.safety_tab, text='🛡️ Safety & Limits')
        self.notebook.add(self.advanced_tab, text='⚙️ Advanced')
        self.notebook.add(self.v5_tab, text='🚀 V5 Improvements')
        
        if self.gpt_api_tab:
            self.notebook.add(self.gpt_api_tab, text='🔑 GPT API')
        if self.telegram_tab:
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
                 bg=Colors.ACCENT,
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
        
        # Risk Management - SIMPLIFIED: Fixed lot only
        self._create_section(content, "💰 Risk Management (Управление Рисками)")
        
        trading_config = self.configs.get('trading.yaml', {})
        risk_config = trading_config.get('trading', {}).get('risk', {})
        
        # Fixed Lot Size ONLY
        lot_frame = self._create_setting_row(content, "📊 Lot Size (фиксированный объём позиции)")
        self.fixed_lot = tk.Entry(lot_frame, font=('Arial', 12, 'bold'), width=10)
        self.fixed_lot.insert(0, str(risk_config.get('fixed_lot_size', 0.01)))
        self.fixed_lot.pack(side='right')
        self._bind_paste(self.fixed_lot)
        
        # Подсказка для Lot Size
        lot_hint = tk.Label(content, 
                           text="💡 Бот ВСЕГДА торгует ТОЛЬКО этим лотом (не зависит от баланса/риска)\n"
                                "   1 лот = $100,000 | 0.1 лот = $10,000 | 0.01 лот = $1,000\n"
                                "   Если средств недостаточно → сделка НЕ открывается (ошибка)",
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
                            fg=Colors.ACCENT,
                            activebackground=Colors.BG_HOVER,
                            activeforeground=Colors.ACCENT,
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
        
        # === TRAILING STOP - SIMPLIFIED (V4) ===
        self._create_section(content, "🎯 Trailing Stop (Автоматическая защита прибыли)")
        
        trailing_config = trading_config.get('trading', {}).get('trailing_stop', {})
        
        # Enable checkbox
        trail_frame = self._create_setting_row(content, "✅ Включить trailing stop")
        self.trail_enabled = tk.BooleanVar(value=trailing_config.get('enabled', False))
        tk.Checkbutton(trail_frame, variable=self.trail_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD,
                      font=('Arial', 10, 'bold')).pack(side='right')
        
        # Info panel с объяснением V4
        info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                             highlightbackground=Colors.BORDER,
                             highlightthickness=1)
        info_frame.pack(fill='x', pady=(5, 15), padx=20)
        
        info_text = """ℹ️ TrailingStopV4 - Процентная система (АВТОМАТИЧЕСКАЯ)
Единственный параметр: % активации от расстояния до TP.
Остальное рассчитывается системой:
• Первый SL = Activation - 10% (например: 40% → первый SL на 30%)
• Шаг движения: фиксированный 10% каждые 10% профита
• Защищает прибыль автоматически, без ручных настроек пипсов"""
        
        tk.Label(info_frame,
                text=info_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                justify='left',
                wraplength=650).pack(padx=15, pady=10)
        
        # ПАРАМЕТР 1: Activation %
        tk.Label(content,
                text="📈 Активация при профите (% от TP distance):",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY,
                anchor='w').pack(fill='x', pady=(10, 5), padx=40)
        
        activation_frame = tk.Frame(content, bg=Colors.BG_DARK)
        activation_frame.pack(fill='x', pady=5, padx=40)
        
        tk.Label(activation_frame,
                text="Активация:",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY).pack(side='left', padx=5)
        
        self.trail_activation_percent = tk.Entry(activation_frame,
                                                 font=('Arial', 10, 'bold'),
                                                 width=8,
                                                 bg=Colors.BG_CARD,
                                                 fg=Colors.SUCCESS,
                                                 insertbackground=Colors.TEXT_PRIMARY)
        self.trail_activation_percent.insert(0, str(trailing_config.get('activation_profit_percent', 40)))
        self.trail_activation_percent.pack(side='left', padx=5)
        self._bind_paste(self.trail_activation_percent)
        
        tk.Label(activation_frame,
                text="% от TP distance",
                font=('Arial', 9),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=5)
        
        tk.Label(content,
                text="💡 При 40%: если TP $15 → активация при +$6 профита",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # ПАРАМЕТР 2: Trailing Step %
        tk.Label(content,
                text="⚙️ Шаг трейлинга (% от TP distance):",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY,
                anchor='w').pack(fill='x', pady=(10, 5), padx=40)
        
        step_frame = tk.Frame(content, bg=Colors.BG_DARK)
        step_frame.pack(fill='x', pady=5, padx=40)
        
        tk.Label(step_frame,
                text="Шаг:",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY).pack(side='left', padx=5)
        
        self.trail_step_percent = tk.Entry(step_frame,
                                          font=('Arial', 10, 'bold'),
                                          width=8,
                                          bg=Colors.BG_CARD,
                                          fg=Colors.SUCCESS,
                                          insertbackground=Colors.TEXT_PRIMARY)
        self.trail_step_percent.insert(0, str(trailing_config.get('trailing_step_percent', 10)))
        self.trail_step_percent.pack(side='left', padx=5)
        self._bind_paste(self.trail_step_percent)
        
        tk.Label(step_frame,
                text="% (каждые X% профита двигать SL вверх)",
                font=('Arial', 9),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=5)
        
        tk.Label(content,
                text="💡 При 10%: если TP $15 → SL двигается каждые $1.5 профита",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Подробные примеры
        example_frame = tk.Frame(content, bg=Colors.BG_DARK)
        example_frame.pack(fill='x', pady=(5, 10), padx=40)
        
        tk.Label(example_frame,
                text="💡 Примеры работы:\n"
                     "   Актив 40%, шаг 10%: профит $6 (40%) → первый SL $4.5 (30%), далее каждые $1.5\n"
                     "   Актив 30%, шаг 5%: профит $4.5 (30%) → первый SL $3.75 (25%), далее каждые $0.75\n"
                     "   Актив 60%, шаг 15%: профит $9 (60%) → первый SL $6.75 (45%), далее каждые $2.25",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(side='left')
        
        # === STOP LOSS PROTECTION - ЗАЩИТА ОТ СЕРИИ СТОПОВ ===
        self._create_section(content, "🛡️ Stop Loss Protection (Защита от серии стопов)")
        
        protection_config = trading_config.get('trading', {}).get('stop_loss_protection', {})
        
        # Enable checkbox
        protection_enable_frame = self._create_setting_row(content, "✅ Включить защиту от стопов")
        self.stop_protection_enabled = tk.BooleanVar(value=protection_config.get('enabled', True))
        tk.Checkbutton(protection_enable_frame, variable=self.stop_protection_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD,
                      font=('Arial', 10, 'bold')).pack(side='right')
        
        # Info panel
        protection_info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                                        highlightbackground=Colors.BORDER,
                                        highlightthickness=1)
        protection_info_frame.pack(fill='x', pady=(5, 15), padx=20)
        
        protection_info_text = """ℹ️ Stop Loss Protection - Умная защита от серии убытков
Блокирует торговлю на N минут после серии стоп-лоссов.
• Считаются только УБЫТОЧНЫЕ сделки (минусовые)
• Trailing Stop НЕ считается стопом (это защита прибыли)
• После прибыльной сделки счетчик сбрасывается
• Защищает депозит от агрессивных серий убытков"""
        
        tk.Label(protection_info_frame,
                text=protection_info_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                justify='left',
                wraplength=650).pack(padx=15, pady=10)
        
        # Количество последовательных стопов
        stops_frame = self._create_setting_row(content, "⚠️ Количество стопов для блокировки:")
        self.stop_protection_consecutive = tk.Entry(stops_frame, font=('Arial', 10), width=8)
        self.stop_protection_consecutive.insert(0, str(protection_config.get('consecutive_stops', 2)))
        self.stop_protection_consecutive.pack(side='right', padx=5)
        self._bind_paste(self.stop_protection_consecutive)
        
        tk.Label(content,
                text="💡 Рекомендуется 2-3 стопа",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Время блокировки
        cooldown_frame = self._create_setting_row(content, "⏰ Время блокировки (минут):")
        self.stop_protection_cooldown = tk.Entry(cooldown_frame, font=('Arial', 10), width=8)
        self.stop_protection_cooldown.insert(0, str(protection_config.get('cooldown_minutes', 15)))
        self.stop_protection_cooldown.pack(side='right', padx=5)
        self._bind_paste(self.stop_protection_cooldown)
        
        tk.Label(content,
                text="💡 Рекомендуется 10-30 минут (дать рынку успокоиться)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Пример работы
        protection_example_frame = tk.Frame(content, bg=Colors.BG_DARK)
        protection_example_frame.pack(fill='x', pady=(5, 10), padx=40)
        
        tk.Label(protection_example_frame,
                text="💡 Пример: При настройках 2 стопа / 15 минут:\n"
                     "   Сделка 1: Stop Loss -$5 ❌ (стоп 1/2)\n"
                     "   Сделка 2: Stop Loss -$3 ❌ (стоп 2/2) → 🛡️ ЗАЩИТА АКТИВНА 15 минут\n"
                     "   Бот не торгует 15 минут, затем возобновляет работу\n"
                     "   Прибыльная сделка сбрасывает счетчик!",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(side='left')
        
        # === PROFIT PROTECTION - ФИКСАЦИЯ ПРИБЫЛИ ===
        self._create_section(content, "💎 Profit Protection (Фиксация прибыли)")
        
        profit_protection_config = trading_config.get('trading', {}).get('profit_protection', {})
        
        # Enable checkbox
        profit_enable_frame = self._create_setting_row(content, "✅ Включить фиксацию прибыли")
        self.profit_protection_enabled = tk.BooleanVar(value=profit_protection_config.get('enabled', True))
        tk.Checkbutton(profit_enable_frame, variable=self.profit_protection_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD,
                      font=('Arial', 10, 'bold')).pack(side='right')
        
        # Info panel
        profit_info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                                     highlightbackground=Colors.BORDER,
                                     highlightthickness=1)
        profit_info_frame.pack(fill='x', pady=(5, 15), padx=20)
        
        profit_info_text = """ℹ️ Profit Protection - Защита от жадности
Блокирует торговлю на N минут после серии прибыльных сделок.
• Защищает заработанную прибыль от последующих убытков
• Trailing Stop СЧИТАЕТСЯ прибыльной сделкой
• После убыточной сделки счетчик сбрасывается
• Психологическая защита: зафиксировать прибыль, сделать паузу"""
        
        tk.Label(profit_info_frame,
                text=profit_info_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                justify='left',
                wraplength=650).pack(padx=15, pady=10)
        
        # Количество последовательных прибыльных сделок
        wins_frame = self._create_setting_row(content, "💰 Количество профитов для блокировки:")
        self.profit_protection_consecutive = tk.Entry(wins_frame, font=('Arial', 10), width=8)
        self.profit_protection_consecutive.insert(0, str(profit_protection_config.get('consecutive_wins', 3)))
        self.profit_protection_consecutive.pack(side='right', padx=5)
        self._bind_paste(self.profit_protection_consecutive)
        
        tk.Label(content,
                text="💡 Рекомендуется 3-5 прибыльных сделок",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Время блокировки
        profit_cooldown_frame = self._create_setting_row(content, "⏰ Время паузы (минут):")
        self.profit_protection_cooldown = tk.Entry(profit_cooldown_frame, font=('Arial', 10), width=8)
        self.profit_protection_cooldown.insert(0, str(profit_protection_config.get('cooldown_minutes', 10)))
        self.profit_protection_cooldown.pack(side='right', padx=5)
        self._bind_paste(self.profit_protection_cooldown)
        
        tk.Label(content,
                text="💡 Рекомендуется 10-20 минут (защитить прибыль, остыть)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Пример работы
        profit_example_frame = tk.Frame(content, bg=Colors.BG_DARK)
        profit_example_frame.pack(fill='x', pady=(5, 10), padx=40)
        
        tk.Label(profit_example_frame,
                text="💡 Пример: При настройках 3 профита / 10 минут:\n"
                     "   Сделка 1: +$5 ✅ (профит 1/3)\n"
                     "   Сделка 2: +$3 ✅ (профит 2/3)\n"
                     "   Сделка 3: +$7 ✅ (профит 3/3) → 💎 ФИКСАЦИЯ ПРИБЫЛИ 10 минут\n"
                     "   Бот делает паузу, чтобы сохранить заработанное\n"
                     "   Убыточная сделка сбрасывает счетчик!",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(side='left')
        
        # === AI ANALYSIS SETTINGS ===
        self._create_section(content, "🤖 AI Analysis Settings")
        
        ai_config = self.configs.get('ai.yaml', {})
        pure_ai_config = ai_config.get('pure_ai', {})
        
        # Analysis Interval
        interval_frame = self._create_setting_row(content, "📊 Analysis Interval (minutes)")
        self.analysis_interval = tk.Entry(interval_frame, font=('Arial', 10), width=10)
        self.analysis_interval.insert(0, str(pure_ai_config.get('analysis_interval_minutes', 30)))
        self.analysis_interval.pack(side='right')
        self._bind_paste(self.analysis_interval)
        
        # Hint
        interval_hint = tk.Label(content,
                                text="💡 Как часто GPT-4 анализирует рынок (рекомендуется: 30-60 минут)",
                                font=('Arial', 8, 'italic'),
                                bg=Colors.BG_DARK,
                                fg=Colors.TEXT_MUTED,
                                wraplength=450,
                                justify='left')
        interval_hint.pack(fill='x', pady=(2, 10), padx=20)
        
        # TTL SETTINGS - User configurable signal lifetime
        self._create_section(content, "⏱ Signal Time To Live (TTL)")
        # Load configs for TTL
        ai_config = self.configs.get('ai.yaml', {})
        ttl_config = trading_config.get('trading', {}).get('signal_ttl', {})
        
        validity_frame = self._create_setting_row(content, "⏱ Signal TTL (minutes)")
        self.signal_validity = tk.Entry(validity_frame, font=('Arial', 10), width=10)
        self.signal_validity.insert(0, str(ttl_config.get('ttl_minutes', 60)))
        self.signal_validity.pack(side='right')
        self._bind_paste(self.signal_validity)
        
        # Auto-requery on expire
        auto_requery_expire_frame = self._create_setting_row(content, "Auto-requery on TTL expire")
        self.auto_requery_expire = tk.BooleanVar(value=ttl_config.get('auto_requery_on_expire', True))
        tk.Checkbutton(auto_requery_expire_frame, variable=self.auto_requery_expire,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Auto-requery on close
        auto_requery_close_frame = self._create_setting_row(content, "Auto-requery on position close")
        self.auto_requery_close = tk.BooleanVar(value=ttl_config.get('auto_requery_on_close', True))
        tk.Checkbutton(auto_requery_close_frame, variable=self.auto_requery_close,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Cooldown минуты (задержка перед новым анализом)
        cooldown_frame = self._create_setting_row(content, "⏳ Cooldown до анализа (минуты)")
        self.requery_cooldown = tk.Entry(cooldown_frame, font=('Arial', 10), width=10)
        self.requery_cooldown.insert(0, str(ttl_config.get('requery_cooldown_minutes', 5)))
        self.requery_cooldown.pack(side='right')
        self._bind_paste(self.requery_cooldown)
        
        # Подсказка о TTL
        ttl_hint = tk.Label(content, 
                           text="💡 TTL: Время жизни сигнала. После истечения/закрытия → auto-requery через cooldown минут.",
                           font=('Arial', 8, 'italic'),
                           bg=Colors.BG_DARK,
                           fg=Colors.TEXT_MUTED,
                           wraplength=450,
                           justify='left')
        ttl_hint.pack(fill='x', pady=(2, 10), padx=20)
        
        # === MANUAL TRADING CONTROLS - 🎮 РУЧНОЕ УПРАВЛЕНИЕ SL/TP/LOT ===
        self._create_section(content, "🎮 Manual Trading Controls (Ручное управление)")
        
        manual_overrides = ai_config.get('manual_overrides', {})
        
        # Info panel с объяснением
        manual_info_frame = tk.Frame(content, bg=Colors.BG_CARD,
                                     highlightbackground=Colors.BORDER,
                                     highlightthickness=1)
        manual_info_frame.pack(fill='x', pady=(5, 15), padx=20)
        
        manual_info_text = """ℹ️ Ручное управление SL/TP/LOT
Вы можете взять контроль над SL, TP и размером лота вместо AI.
• Когда ВЫКЛЮЧЕНО: AI выбирает SL/TP на основе волатильности, сессии, ATR (адаптивный режим)
• Когда ВКЛЮЧЕНО: Используются ваши фиксированные значения из полей ниже
• Можно настроить отдельно для GOLD (XAUUSD) и FOREX (EURUSD)
• fixed_lot = null → адаптивный лот (0.01-0.05) | число → фиксированный лот"""
        
        tk.Label(manual_info_frame,
                text=manual_info_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                justify='left',
                wraplength=650).pack(padx=15, pady=10)
        
        # Enable Manual Mode checkbox
        manual_enable_frame = self._create_setting_row(content, "✅ Включить ручной режим (Manual Mode)")
        self.manual_mode_enabled = tk.BooleanVar(value=manual_overrides.get('enabled', False))
        tk.Checkbutton(manual_enable_frame, variable=self.manual_mode_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD,
                      font=('Arial', 10, 'bold')).pack(side='right')
        
        # === XAUUSD (GOLD) SETTINGS ===
        tk.Label(content,
                text="💰 XAUUSD (GOLD) - в долларах:",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.WARNING,
                anchor='w').pack(fill='x', pady=(15, 5), padx=30)
        
        xauusd_settings = manual_overrides.get('xauusd', {})
        
        # XAUUSD SL
        xau_sl_frame = self._create_setting_row(content, "  Stop Loss (dollars)")
        self.manual_xau_sl = tk.Entry(xau_sl_frame, font=('Arial', 10, 'bold'), width=10,
                                      bg=Colors.BG_CARD, fg=Colors.ERROR)
        self.manual_xau_sl.insert(0, str(xauusd_settings.get('sl_dollars', 4.5)))
        self.manual_xau_sl.pack(side='right', padx=5)
        self._bind_paste(self.manual_xau_sl)
        
        tk.Label(content,
                text="     💡 Рекомендуется: $3.5-$8 (базовое $4.5)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # XAUUSD TP
        xau_tp_frame = self._create_setting_row(content, "  Take Profit (dollars)")
        self.manual_xau_tp = tk.Entry(xau_tp_frame, font=('Arial', 10, 'bold'), width=10,
                                      bg=Colors.BG_CARD, fg=Colors.SUCCESS)
        self.manual_xau_tp.insert(0, str(xauusd_settings.get('tp_dollars', 12.0)))
        self.manual_xau_tp.pack(side='right', padx=5)
        self._bind_paste(self.manual_xau_tp)
        
        tk.Label(content,
                text="     💡 Рекомендуется: $9-$18 (базовое $12)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # XAUUSD Fixed Lot
        xau_lot_frame = self._create_setting_row(content, "  Fixed Lot (оставьте пустым для адаптивного)")
        self.manual_xau_lot = tk.Entry(xau_lot_frame, font=('Arial', 10), width=10,
                                       bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY)
        current_xau_lot = xauusd_settings.get('fixed_lot')
        if current_xau_lot is not None:
            self.manual_xau_lot.insert(0, str(current_xau_lot))
        self.manual_xau_lot.pack(side='right', padx=5)
        self._bind_paste(self.manual_xau_lot)
        
        tk.Label(content,
                text="     💡 Пустое = adaptive 0.01-0.05 | Число (0.01-0.05) = фиксированный лот",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === EURUSD (FOREX) SETTINGS ===
        tk.Label(content,
                text="💱 EURUSD (FOREX) - в пипсах:",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.INFO,
                anchor='w').pack(fill='x', pady=(15, 5), padx=30)
        
        eurusd_settings = manual_overrides.get('eurusd', {})
        
        # EURUSD SL
        eur_sl_frame = self._create_setting_row(content, "  Stop Loss (pips)")
        self.manual_eur_sl = tk.Entry(eur_sl_frame, font=('Arial', 10, 'bold'), width=10,
                                      bg=Colors.BG_CARD, fg=Colors.ERROR)
        self.manual_eur_sl.insert(0, str(eurusd_settings.get('sl_pips', 30)))
        self.manual_eur_sl.pack(side='right', padx=5)
        self._bind_paste(self.manual_eur_sl)
        
        tk.Label(content,
                text="     💡 Рекомендуется: 25-50 пипсов (базовое 30)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # EURUSD TP
        eur_tp_frame = self._create_setting_row(content, "  Take Profit (pips)")
        self.manual_eur_tp = tk.Entry(eur_tp_frame, font=('Arial', 10, 'bold'), width=10,
                                      bg=Colors.BG_CARD, fg=Colors.SUCCESS)
        self.manual_eur_tp.insert(0, str(eurusd_settings.get('tp_pips', 50)))
        self.manual_eur_tp.pack(side='right', padx=5)
        self._bind_paste(self.manual_eur_tp)
        
        tk.Label(content,
                text="     💡 Рекомендуется: 45-65 пипсов (базовое 50)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # EURUSD Fixed Lot
        eur_lot_frame = self._create_setting_row(content, "  Fixed Lot (оставьте пустым для адаптивного)")
        self.manual_eur_lot = tk.Entry(eur_lot_frame, font=('Arial', 10), width=10,
                                       bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY)
        current_eur_lot = eurusd_settings.get('fixed_lot')
        if current_eur_lot is not None:
            self.manual_eur_lot.insert(0, str(current_eur_lot))
        self.manual_eur_lot.pack(side='right', padx=5)
        self._bind_paste(self.manual_eur_lot)
        
        tk.Label(content,
                text="     💡 Пустое = adaptive 0.01-0.05 | Число (0.01-0.05) = фиксированный лот",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # Примеры использования
        examples_frame = tk.Frame(content, bg=Colors.BG_DARK)
        examples_frame.pack(fill='x', pady=(10, 15), padx=40)
        
        tk.Label(examples_frame,
                text="💡 Примеры:\n"
                     "   Консервативно: SL $3.5, TP $10, Lot 0.01 (маленькие риски)\n"
                     "   Агрессивно: SL $6, TP $18, Lot 0.03 (большие риски)\n"
                     "   Гибридно: SL $5, TP $15, Lot пустое (AI выбирает 0.01-0.05)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(side='left')
        
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
        
        # TTL настройка (из trading.yaml)
        trading_config = self.configs.get('trading.yaml', {})
        ttl_config = trading_config.get('trading', {}).get('signal_ttl', {})
        
        validity_frame = self._create_setting_row(content, "⏱ Signal TTL (minutes)")
        self.signal_validity = tk.Entry(validity_frame, font=('Arial', 10), width=10)
        self.signal_validity.insert(0, str(ttl_config.get('ttl_minutes', 60)))
        self.signal_validity.pack(side='right')
        self._bind_paste(self.signal_validity)
        
        # Auto-requery on expire
        auto_requery_expire_frame = self._create_setting_row(content, "Auto-requery on TTL expire")
        self.auto_requery_expire = tk.BooleanVar(value=ttl_config.get('auto_requery_on_expire', True))
        tk.Checkbutton(auto_requery_expire_frame, variable=self.auto_requery_expire,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Auto-requery on close
        auto_requery_close_frame = self._create_setting_row(content, "Auto-requery on position close")
        self.auto_requery_close = tk.BooleanVar(value=ttl_config.get('auto_requery_on_close', True))
        tk.Checkbutton(auto_requery_close_frame, variable=self.auto_requery_close,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # Подсказка о TTL
        ttl_hint = tk.Label(content, 
                           text="💡 TTL: Время жизни сигнала. После истечения → auto-requery (если enabled). После закрытия позиции → auto-requery.",
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
        
        # Hint for weekend block
        weekend_hint = tk.Label(content,
                               text="💡 Weekend: Friday 22:00 → Monday 01:00 UTC (Forex closed)",
                               font=('Arial', 8, 'italic'),
                               bg=Colors.BG_DARK,
                               fg=Colors.TEXT_MUTED,
                               wraplength=450,
                               justify='left')
        weekend_hint.pack(fill='x', pady=(2, 10), padx=20)
        
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
    
    def _create_quick_actions_tab(self):
        """⚡ Quick Actions - Быстрые действия"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Header
        header_frame = tk.Frame(content, bg=Colors.BG_CARD,
                               highlightbackground=Colors.ACCENT,
                               highlightthickness=2)
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        tk.Label(header_frame, 
                text="⚡ QUICK ACTIONS - Быстрые действия\\n\\nБыстрый доступ к важным функциям без перезапуска бота",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ACCENT,
                justify='left').pack(padx=15, pady=15, anchor='w')
        
        # === АНАЛИЗ И ДАННЫЕ ===
        self._create_section(content, "📊 Analysis & Data (Анализ и Данные)")
        
        # Force AI Analysis
        btn_frame_1 = tk.Frame(content, bg=Colors.BG_CARD, highlightbackground=Colors.BORDER, highlightthickness=1)
        btn_frame_1.pack(fill='x', padx=40, pady=5)
        
        tk.Button(btn_frame_1,
                 text="🚀 Force AI Analysis Now",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.ACCENT,
                 fg='white',
                 activebackground=Colors.INFO,
                 relief='flat',
                 cursor='hand2',
                 width=30,
                 command=self._force_analysis).pack(side='left', padx=15, pady=10)
        
        tk.Label(btn_frame_1,
                text="Запустить GPT анализ прямо сейчас (игнорируя интервал)",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=10)
        
        # Reload Config
        btn_frame_2 = tk.Frame(content, bg=Colors.BG_CARD, highlightbackground=Colors.BORDER, highlightthickness=1)
        btn_frame_2.pack(fill='x', padx=40, pady=5)
        
        tk.Button(btn_frame_2,
                 text="🔄 Reload Config",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.WARNING,
                 fg='black',
                 activebackground='#e0a800',
                 relief='flat',
                 cursor='hand2',
                 width=30,
                 command=self._reload_config).pack(side='left', padx=15, pady=10)
        
        tk.Label(btn_frame_2,
                text="Перезагрузить все конфиги без перезапуска бота",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=10)
        
        # === ФАЙЛЫ И ПАПКИ ===
        self._create_section(content, "📁 Files & Folders (Файлы и Папки)")
        
        files_container = tk.Frame(content, bg=Colors.BG_DARK)
        files_container.pack(fill='x', padx=40, pady=10)
        
        # Open Logs
        btn_logs = tk.Button(files_container,
                            text="📄 Open Logs Folder",
                            font=('Arial', 10, 'bold'),
                            bg=Colors.BG_CARD,
                            fg=Colors.TEXT_PRIMARY,
                            activebackground=Colors.BG_HOVER,
                            relief='flat',
                            cursor='hand2',
                            width=25,
                            command=self._open_logs_folder)
        btn_logs.pack(side='left', padx=5)
        
        # Open Screenshots
        btn_screens = tk.Button(files_container,
                               text="📸 Open Screenshots",
                               font=('Arial', 10, 'bold'),
                               bg=Colors.BG_CARD,
                               fg=Colors.TEXT_PRIMARY,
                               activebackground=Colors.BG_HOVER,
                               relief='flat',
                               cursor='hand2',
                               width=25,
                               command=self._open_screenshots_folder)
        btn_screens.pack(side='left', padx=5)
        
        # Clean Old Data
        btn_clean = tk.Button(files_container,
                             text="🧹 Clean Old Data",
                             font=('Arial', 10, 'bold'),
                             bg=Colors.BG_CARD,
                             fg=Colors.WARNING,
                             activebackground=Colors.BG_HOVER,
                             relief='flat',
                             cursor='hand2',
                             width=25,
                             command=self._clean_old_data)
        btn_clean.pack(side='left', padx=5)
        
        # === СТАТИСТИКА ===
        self._create_section(content, "📈 Statistics (Статистика)")
        
        btn_frame_stats = tk.Frame(content, bg=Colors.BG_CARD, highlightbackground=Colors.BORDER, highlightthickness=1)
        btn_frame_stats.pack(fill='x', padx=40, pady=5)
        
        tk.Button(btn_frame_stats,
                 text="📊 View Today's Stats",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.INFO,
                 fg='white',
                 activebackground='#4080ff',
                 relief='flat',
                 cursor='hand2',
                 width=30,
                 command=self._view_today_stats).pack(side='left', padx=15, pady=10)
        
        tk.Label(btn_frame_stats,
                text="Показать детальную статистику за сегодня",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=10)
        
        # === АВАРИЙНЫЕ ДЕЙСТВИЯ ===
        self._create_section(content, "⚠️ Emergency Actions (Аварийные Действия)")
        
        warning_frame = tk.Frame(content, bg='#4a1f1f',
                                highlightbackground=Colors.ERROR,
                                highlightthickness=2)
        warning_frame.pack(fill='x', padx=40, pady=10)
        
        tk.Label(warning_frame,
                text="⚠️ ОСТОРОЖНО: Эти действия немедленно влияют на работу бота!",
                font=('Arial', 10, 'bold'),
                bg='#4a1f1f',
                fg=Colors.ERROR).pack(pady=10)
        
        emergency_container = tk.Frame(warning_frame, bg='#4a1f1f')
        emergency_container.pack(fill='x', padx=15, pady=(0, 15))
        
        # Emergency Stop All
        tk.Button(emergency_container,
                 text="⚡ EMERGENCY STOP ALL",
                 font=('Arial', 12, 'bold'),
                 bg=Colors.ERROR,
                 fg='white',
                 activebackground='#c01010',
                 relief='flat',
                 cursor='hand2',
                 width=28,
                 height=2,
                 command=self._emergency_stop).pack(pady=5)
        
        tk.Label(emergency_container,
                text="Закрыть ВСЕ позиции и ОСТАНОВИТЬ бота НЕМЕДЛЕННО",
                font=('Arial', 9, 'italic'),
                bg='#4a1f1f',
                fg=Colors.TEXT_MUTED).pack()
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_safety_tab(self):
        """🛡️ Safety & Limits - Лимиты безопасности"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Header
        header_frame = tk.Frame(content, bg=Colors.BG_CARD,
                               highlightbackground=Colors.ERROR,
                               highlightthickness=2)
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        tk.Label(header_frame, 
                text="🛡️ SAFETY & LIMITS - Защита депозита\\n\\nАвтоматические лимиты для защиты от больших потерь",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ERROR,
                justify='left').pack(padx=15, pady=15, anchor='w')
        
        trading_config = self.configs.get('trading.yaml', {})
        safety_config = trading_config.get('trading', {}).get('safety_limits', {})
        
        # === ДНЕВНЫЕ ЛИМИТЫ ===
        self._create_section(content, "💰 Daily Limits (Дневные Лимиты)")
        
        # Enable Daily Limits
        daily_enable_frame = self._create_setting_row(content, "✅ Включить дневные лимиты")
        self.daily_limits_enabled = tk.BooleanVar(value=safety_config.get('enabled', True))
        tk.Checkbutton(daily_enable_frame, variable=self.daily_limits_enabled,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD,
                      font=('Arial', 10, 'bold')).pack(side='right')
        
        # Max Daily Loss
        loss_frame = self._create_setting_row(content, "📉 Max Daily Loss ($)")
        self.max_daily_loss = tk.Entry(loss_frame, font=('Arial', 10, 'bold'), width=10,
                                        bg=Colors.BG_CARD, fg=Colors.ERROR)
        self.max_daily_loss.insert(0, str(safety_config.get('max_daily_loss', 50.0)))
        self.max_daily_loss.pack(side='right', padx=5)
        self._bind_paste(self.max_daily_loss)
        
        tk.Label(content,
                text="     💡 При достижении убытка за день - бот ОСТАНАВЛИВАЕТСЯ автоматически",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Daily Profit
        profit_frame = self._create_setting_row(content, "📈 Max Daily Profit ($)")
        self.max_daily_profit = tk.Entry(profit_frame, font=('Arial', 10, 'bold'), width=10,
                                          bg=Colors.BG_CARD, fg=Colors.SUCCESS)
        self.max_daily_profit.insert(0, str(safety_config.get('max_daily_profit', 100.0)))
        self.max_daily_profit.pack(side='right', padx=5)
        self._bind_paste(self.max_daily_profit)
        
        tk.Label(content,
                text="     💡 При достижении профита за день - бот ФИКСИРУЕТ прибыль и останавливается",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === ЛИМИТЫ ПОЗИЦИЙ ===
        self._create_section(content, "📊 Position Limits (Лимиты Позиций)")
        
        # Max Open Positions
        positions_frame = self._create_setting_row(content, "🔢 Max Open Positions")
        self.max_open_positions = tk.Entry(positions_frame, font=('Arial', 10), width=10)
        self.max_open_positions.insert(0, str(safety_config.get('max_open_positions', 2)))
        self.max_open_positions.pack(side='right', padx=5)
        self._bind_paste(self.max_open_positions)
        
        tk.Label(content,
                text="     💡 Максимум позиций одновременно (рекомендуется 1-3)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Position Duration
        duration_frame = self._create_setting_row(content, "⏰ Max Position Duration (hours)")
        self.max_position_duration = tk.Entry(duration_frame, font=('Arial', 10), width=10)
        self.max_position_duration.insert(0, str(safety_config.get('max_position_duration_hours', 24)))
        self.max_position_duration.pack(side='right', padx=5)
        self._bind_paste(self.max_position_duration)
        
        tk.Label(content,
                text="     💡 Принудительно закрыть позицию через N часов (0 = без лимита)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === ЛИМИТЫ ТОРГОВЫХ СЕССИЙ ===
        self._create_section(content, "🎯 Session Limits (Лимиты Торговых Сессий)")
        
        # Max Trades Per Day
        trades_day_frame = self._create_setting_row(content, "📊 Max Trades Per Day")
        self.max_trades_per_day = tk.Entry(trades_day_frame, font=('Arial', 10), width=10)
        self.max_trades_per_day.insert(0, str(safety_config.get('max_trades_per_day', 20)))
        self.max_trades_per_day.pack(side='right', padx=5)
        self._bind_paste(self.max_trades_per_day)
        
        tk.Label(content,
                text="     💡 Максимум сделок за день по всем инструментам (0 = без лимита)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Trades Per Hour
        trades_hour_frame = self._create_setting_row(content, "⏱️ Max Trades Per Hour")
        self.max_trades_per_hour = tk.Entry(trades_hour_frame, font=('Arial', 10), width=10)
        self.max_trades_per_hour.insert(0, str(safety_config.get('max_trades_per_hour', 5)))
        self.max_trades_per_hour.pack(side='right', padx=5)
        self._bind_paste(self.max_trades_per_hour)
        
        tk.Label(content,
                text="     💡 Защита от слишком частого открытия позиций (0 = без лимита)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Losses In Row
        losses_row_frame = self._create_setting_row(content, "🔴 Stop After N Losses In Row")
        self.max_losses_in_row = tk.Entry(losses_row_frame, font=('Arial', 10, 'bold'), width=10,
                                          bg=Colors.BG_CARD, fg=Colors.ERROR)
        self.max_losses_in_row.insert(0, str(safety_config.get('max_losses_in_row', 3)))
        self.max_losses_in_row.pack(side='right', padx=5)
        self._bind_paste(self.max_losses_in_row)
        
        tk.Label(content,
                text="     💡 ОСТАНОВИТЬ БОТ после N убыточных сделок подряд (0 = отключено)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === RISK MANAGEMENT ===
        self._create_section(content, "⚠️ Risk Management (Управление Риском)")
        
        # Max Risk Per Trade
        risk_trade_frame = self._create_setting_row(content, "📉 Max Risk Per Trade (% of balance)")
        self.max_risk_per_trade = tk.Entry(risk_trade_frame, font=('Arial', 10, 'bold'), width=10,
                                           bg=Colors.BG_CARD, fg=Colors.WARNING)
        self.max_risk_per_trade.insert(0, str(safety_config.get('max_risk_per_trade_pct', 2.0)))
        self.max_risk_per_trade.pack(side='right', padx=5)
        self._bind_paste(self.max_risk_per_trade)
        
        tk.Label(content,
                text="     💡 Максимальный риск в одной сделке (% от текущего баланса)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Total Risk
        total_risk_frame = self._create_setting_row(content, "📊 Max Total Risk (% of balance)")
        self.max_total_risk = tk.Entry(total_risk_frame, font=('Arial', 10, 'bold'), width=10,
                                       bg=Colors.BG_CARD, fg=Colors.WARNING)
        self.max_total_risk.insert(0, str(safety_config.get('max_total_risk_pct', 5.0)))
        self.max_total_risk.pack(side='right', padx=5)
        self._bind_paste(self.max_total_risk)
        
        tk.Label(content,
                text="     💡 Максимальный суммарный риск всех открытых позиций (% баланса)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Lot Size
        max_lot_frame = self._create_setting_row(content, "🎚️ Max Lot Size")
        self.max_lot_size = tk.Entry(max_lot_frame, font=('Arial', 10), width=10)
        self.max_lot_size.insert(0, str(safety_config.get('max_lot_size', 1.0)))
        self.max_lot_size.pack(side='right', padx=5)
        self._bind_paste(self.max_lot_size)
        
        tk.Label(content,
                text="     💡 Максимальный размер лота (защита от случайно больших объемов)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Min Balance Protection
        min_balance_frame = self._create_setting_row(content, "💰 Minimum Balance Protection ($)")
        self.min_balance_protection = tk.Entry(min_balance_frame, font=('Arial', 10, 'bold'), width=10,
                                               bg=Colors.BG_CARD, fg=Colors.ERROR)
        self.min_balance_protection.insert(0, str(safety_config.get('min_balance_protection', 50.0)))
        self.min_balance_protection.pack(side='right', padx=5)
        self._bind_paste(self.min_balance_protection)
        
        tk.Label(content,
                text="     💡 НЕ открывать новые позиции если баланс НИЖЕ этого значения",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === COOLDOWN PERIODS ===
        self._create_section(content, "⏸️ Cooldown Periods (Паузы После Сделок)")
        
        # Cooldown After Loss
        cooldown_loss_frame = self._create_setting_row(content, "🔴 Cooldown After Loss (minutes)")
        self.cooldown_after_loss = tk.Entry(cooldown_loss_frame, font=('Arial', 10), width=10)
        self.cooldown_after_loss.insert(0, str(safety_config.get('cooldown_after_loss_min', 15)))
        self.cooldown_after_loss.pack(side='right', padx=5)
        self._bind_paste(self.cooldown_after_loss)
        
        tk.Label(content,
                text="     💡 Пауза перед следующей сделкой после убытка (0 = без паузы)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Cooldown After Win
        cooldown_win_frame = self._create_setting_row(content, "🟢 Cooldown After Win (minutes)")
        self.cooldown_after_win = tk.Entry(cooldown_win_frame, font=('Arial', 10), width=10)
        self.cooldown_after_win.insert(0, str(safety_config.get('cooldown_after_win_min', 5)))
        self.cooldown_after_win.pack(side='right', padx=5)
        self._bind_paste(self.cooldown_after_win)
        
        tk.Label(content,
                text="     💡 Пауза перед следующей сделкой после профита (0 = без паузы)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === ЛИМИТЫ GPT ===
        self._create_section(content, "🤖 GPT Limits (Лимиты GPT)")
        
        ai_config = self.configs.get('ai.yaml', {})
        gpt_safety = ai_config.get('market_analyst', {}).get('safety', {})
        
        # Max Daily Calls
        calls_frame = self._create_setting_row(content, "📞 Max Daily GPT Calls")
        self.max_daily_calls = tk.Entry(calls_frame, font=('Arial', 10), width=10)
        self.max_daily_calls.insert(0, str(gpt_safety.get('max_daily_calls', 50)))
        self.max_daily_calls.pack(side='right', padx=5)
        self._bind_paste(self.max_daily_calls)
        
        tk.Label(content,
                text="     💡 Максимум запросов к GPT в день (защита от перерасхода)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # Max Monthly Cost
        cost_frame = self._create_setting_row(content, "💵 Max Monthly Cost ($)")
        self.max_monthly_cost = tk.Entry(cost_frame, font=('Arial', 10, 'bold'), width=10,
                                          bg=Colors.BG_CARD, fg=Colors.WARNING)
        self.max_monthly_cost.insert(0, str(gpt_safety.get('max_monthly_cost', 50.0)))
        self.max_monthly_cost.pack(side='right', padx=5)
        self._bind_paste(self.max_monthly_cost)
        
        tk.Label(content,
                text="     💡 Максимальный бюджет на GPT в месяц",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_advanced_tab(self):
        """⚙️ Advanced Settings - Расширенные настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        # Header
        header_frame = tk.Frame(content, bg=Colors.BG_CARD,
                               highlightbackground=Colors.WARNING,
                               highlightthickness=2)
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        tk.Label(header_frame, 
                text="⚙️ ADVANCED SETTINGS - Расширенные настройки\\n\\nТехнические параметры для опытных пользователей",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.WARNING,
                justify='left').pack(padx=15, pady=15, anchor='w')
        
        trading_config = self.configs.get('trading.yaml', {})
        instruments_config = self.configs.get('instruments.yaml', {})
        
        # === TRADING HOURS ===
        self._create_section(content, "⏰ Trading Hours (Часы Торговли)")
        
        hours_config = trading_config.get('trading', {}).get('hours', {})
        
        # Start Time
        start_frame = self._create_setting_row(content, "🌅 Start Time (UTC)")
        self.trading_start = tk.Entry(start_frame, font=('Arial', 10), width=10)
        self.trading_start.insert(0, str(hours_config.get('start', '01:00')))
        self.trading_start.pack(side='right', padx=5)
        self._bind_paste(self.trading_start)
        
        tk.Label(content,
                text="     💡 Начало торговли в UTC (формат: HH:MM)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 5), padx=40)
        
        # End Time
        end_frame = self._create_setting_row(content, "🌙 End Time (UTC)")
        self.trading_end = tk.Entry(end_frame, font=('Arial', 10), width=10)
        self.trading_end.insert(0, str(hours_config.get('end', '23:00')))
        self.trading_end.pack(side='right', padx=5)
        self._bind_paste(self.trading_end)
        
        tk.Label(content,
                text="     💡 Конец торговли в UTC (формат: HH:MM)",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === XAUUSD ADVANCED ===
        self._create_section(content, "💰 XAUUSD Advanced")
        
        xauusd_config = instruments_config.get('instruments', {}).get('XAUUSD', {})
        
        # Max Trades Per Day
        xau_trades_frame = self._create_setting_row(content, "🔢 Max Trades Per Day")
        self.xauusd_max_trades = tk.Entry(xau_trades_frame, font=('Arial', 10), width=10)
        self.xauusd_max_trades.insert(0, str(xauusd_config.get('max_trades_per_day', 3)))
        self.xauusd_max_trades.pack(side='right', padx=5)
        self._bind_paste(self.xauusd_max_trades)
        
        # Commission
        xau_comm_frame = self._create_setting_row(content, "💸 Commission Per Lot ($)")
        self.xauusd_commission = tk.Entry(xau_comm_frame, font=('Arial', 10), width=10)
        self.xauusd_commission.insert(0, str(xauusd_config.get('commission_per_lot', 7.0)))
        self.xauusd_commission.pack(side='right', padx=5)
        self._bind_paste(self.xauusd_commission)
        
        # Max Spread
        risk_config = trading_config.get('trading', {}).get('risk', {})
        
        spread_frame = self._create_setting_row(content, "📊 Max Spread (pips)")
        self.max_spread = tk.Entry(spread_frame, font=('Arial', 10), width=10)
        self.max_spread.insert(0, str(risk_config.get('max_spread_pips', 3.0)))
        self.max_spread.pack(side='right', padx=5)
        self._bind_paste(self.max_spread)
        
        tk.Label(content,
                text="     💡 Не входить в сделку, если спред больше этого значения",
                font=('Arial', 8, 'italic'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED).pack(fill='x', pady=(2, 10), padx=40)
        
        # === EURUSD ADVANCED ===
        self._create_section(content, "💶 EURUSD Advanced")
        
        eurusd_config = instruments_config.get('instruments', {}).get('EURUSD', {})
        
        # Max Trades Per Day
        eur_trades_frame = self._create_setting_row(content, "🔢 Max Trades Per Day")
        self.eurusd_max_trades = tk.Entry(eur_trades_frame, font=('Arial', 10), width=10)
        self.eurusd_max_trades.insert(0, str(eurusd_config.get('max_trades_per_day', 3)))
        self.eurusd_max_trades.pack(side='right', padx=5)
        self._bind_paste(self.eurusd_max_trades)
        
        # Commission
        eur_comm_frame = self._create_setting_row(content, "💸 Commission Per Lot ($)")
        self.eurusd_commission = tk.Entry(eur_comm_frame, font=('Arial', 10), width=10)
        self.eurusd_commission.insert(0, str(eurusd_config.get('commission_per_lot', 3.0)))
        self.eurusd_commission.pack(side='right', padx=5)
        self._bind_paste(self.eurusd_commission)
        
        # === OPERATING MODES ===
        self._create_section(content, "🌟 Operating Modes (Режимы Работы)")
        
        modes_frame = tk.Frame(content, bg=Colors.BG_CARD,
                              highlightbackground=Colors.ACCENT,
                              highlightthickness=1)
        modes_frame.pack(fill='x', padx=40, pady=10)
        
        tk.Label(modes_frame,
                text="Выберите режим работы бота:",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w', padx=15, pady=(15, 5))
        
        self.operating_mode = tk.StringVar(value=trading_config.get('trading', {}).get('operating_mode', 'full_auto'))
        
        modes = [
            ('full_auto', '🤖 Full Auto', 'Полный автомат: анализ + вход в сделки'),
            ('analysis_only', '👀 Analysis Only', 'Только анализ, БЕЗ входа в сделки'),
            ('semi_auto', '🎮 Semi-Auto', 'Анализ автомат, вход вручную (GUI)'),
            ('safe_mode', '🚨 Safe Mode', 'Консервативный режим с жесткими лимитами')
        ]
        
        for mode_val, mode_label, mode_desc in modes:
            mode_frame = tk.Frame(modes_frame, bg=Colors.BG_CARD)
            mode_frame.pack(fill='x', padx=15, pady=3)
            
            tk.Radiobutton(mode_frame,
                          text=mode_label,
                          variable=self.operating_mode,
                          value=mode_val,
                          bg=Colors.BG_CARD,
                          fg=Colors.TEXT_PRIMARY,
                          selectcolor=Colors.BG_DARK,
                          activebackground=Colors.BG_CARD,
                          font=('Arial', 10, 'bold')).pack(side='left')
            
            tk.Label(mode_frame,
                    text=f"  - {mode_desc}",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_MUTED).pack(side='left', padx=5)
        
        tk.Label(modes_frame,
                text="",
                bg=Colors.BG_CARD).pack(pady=10)
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        return frame
    
    def _create_v5_tab(self):
        """🚀 V5 Improvements - Новые модули для повышения винрейта"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # Заголовок и описание
        header_frame = tk.Frame(content, bg=Colors.BG_CARD,
                               highlightbackground=Colors.INFO,
                               highlightthickness=2)
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        header_text = """🚀 V5 IMPROVEMENTS - Модули для увеличения винрейта

✅ Technical Filter - гибридная стратегия GPT + технические индикаторы
✅ Session Adapter - адаптация параметров под торговые сессии (Asian/European/US)
✅ Adaptive Lot Sizing - умный расчет лота на основе текущей производительности
✅ Rejected Signals Logger - сбор данных для анализа отклоненных сигналов

Цель: повысить винрейт с 20% до 35-40%"""
        
        tk.Label(header_frame, text=header_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.INFO,
                justify='left',
                wraplength=700).pack(padx=15, pady=15, anchor='w')
        
        # Загружаем V5 конфиг из trading.yaml
        trading_config = self.configs.get('trading.yaml', {})
        v5_config = trading_config.get('trading', {}).get('v5_improvements', {})
        
        # === 1️⃣ TECHNICAL CONFIRMATION FILTER ===
        self._create_section(content, "1️⃣ Technical Confirmation Filter")
        
        info_tech = tk.Frame(content, bg=Colors.BG_CARD,
                            highlightbackground=Colors.BORDER,
                            highlightthickness=1)
        info_tech.pack(fill='x', padx=30, pady=(0, 10))
        
        tk.Label(info_tech,
                text="📊 Гибридная стратегия: GPT сигналы подтверждаются техническими индикаторами (EMA, RSI, Price Action)",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                wraplength=650).pack(padx=15, pady=10, anchor='w')
        
        # Enable/Disable
        tech_enabled_frame = self._create_setting_row(content, "Включить Technical Filter")
        self.v5_tech_enabled = tk.BooleanVar(value=v5_config.get('technical_filter', {}).get('enabled', True))
        tk.Checkbutton(tech_enabled_frame, variable=self.v5_tech_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side='right')
        
        # Strict Mode
        tech_strict_frame = self._create_setting_row(content, "Strict Mode (более жесткие фильтры)")
        self.v5_tech_strict = tk.BooleanVar(value=v5_config.get('technical_filter', {}).get('strict_mode', False))
        tk.Checkbutton(tech_strict_frame, variable=self.v5_tech_strict,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side='right')
        
        # === 2️⃣ SESSION ADAPTER ===
        self._create_section(content, "2️⃣ Session Adapter")
        
        info_session = tk.Frame(content, bg=Colors.BG_CARD,
                               highlightbackground=Colors.BORDER,
                               highlightthickness=1)
        info_session.pack(fill='x', padx=30, pady=(0, 10))
        
        tk.Label(info_session,
                text="⏰ Адаптация параметров под торговую сессию: Asian (низкая волатильность, консервативно) → US (высокая волатильность, агрессивно)",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                wraplength=650).pack(padx=15, pady=10, anchor='w')
        
        # Enable/Disable
        session_enabled_frame = self._create_setting_row(content, "Включить Session Adapter")
        self.v5_session_enabled = tk.BooleanVar(value=v5_config.get('session_adapter', {}).get('enabled', True))
        tk.Checkbutton(session_enabled_frame, variable=self.v5_session_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side='right')
        
        # Session parameters
        session_params_frame = tk.Frame(content, bg=Colors.BG_CARD,
                                       highlightbackground=Colors.BORDER,
                                       highlightthickness=1)
        session_params_frame.pack(fill='x', padx=30, pady=(5, 10))
        
        params_text = """Asian (00:00-09:00 UTC): Min Confidence 80%, Lot ×0.8
European (07:00-16:00 UTC): Min Confidence 70%, Lot ×1.0
US (13:00-22:00 UTC): Min Confidence 65%, Lot ×1.2
Overlap (07:00-09:00, 13:00-16:00 UTC): Min Confidence 60%, Lot ×1.5"""
        
        tk.Label(session_params_frame, text=params_text,
                font=('Arial', 8),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED,
                justify='left').pack(padx=15, pady=8, anchor='w')
        
        # === 3️⃣ ADAPTIVE LOT SIZING ===
        self._create_section(content, "3️⃣ Adaptive Lot Sizing")
        
        info_lot = tk.Frame(content, bg=Colors.BG_CARD,
                           highlightbackground=Colors.BORDER,
                           highlightthickness=1)
        info_lot.pack(fill='x', padx=30, pady=(0, 10))
        
        tk.Label(info_lot,
                text="📐 Умный расчет лота: увеличивает при хорошей статистике (winrate >60%), снижает при плохой (<40%)",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                wraplength=650).pack(padx=15, pady=10, anchor='w')
        
        # Enable/Disable
        lot_enabled_frame = self._create_setting_row(content, "Включить Adaptive Lot")
        self.v5_lot_enabled = tk.BooleanVar(value=v5_config.get('adaptive_lot', {}).get('enabled', True))
        tk.Checkbutton(lot_enabled_frame, variable=self.v5_lot_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side='right')
        
        # Base Lot
        lot_base_frame = self._create_setting_row(content, "Base Lot (базовый размер)")
        self.v5_lot_base = tk.Entry(lot_base_frame, font=('Arial', 10), width=10)
        self.v5_lot_base.insert(0, str(v5_config.get('adaptive_lot', {}).get('base_lot', 0.01)))
        self.v5_lot_base.pack(side='right')
        
        # Max Lot
        lot_max_frame = self._create_setting_row(content, "Max Lot (максимальный размер)")
        self.v5_lot_max = tk.Entry(lot_max_frame, font=('Arial', 10), width=10)
        self.v5_lot_max.insert(0, str(v5_config.get('adaptive_lot', {}).get('max_lot', 0.05)))
        self.v5_lot_max.pack(side='right')
        
        # Lookback Trades
        lot_lookback_frame = self._create_setting_row(content, "Lookback Trades (анализ последних N сделок)")
        self.v5_lot_lookback = tk.Entry(lot_lookback_frame, font=('Arial', 10), width=10)
        self.v5_lot_lookback.insert(0, str(v5_config.get('adaptive_lot', {}).get('lookback_trades', 10)))
        self.v5_lot_lookback.pack(side='right')
        
        # === 4️⃣ REJECTED SIGNALS LOGGER ===
        self._create_section(content, "4️⃣ Rejected Signals Logger")
        
        info_logger = tk.Frame(content, bg=Colors.BG_CARD,
                              highlightbackground=Colors.BORDER,
                              highlightthickness=1)
        info_logger.pack(fill='x', padx=30, pady=(0, 10))
        
        tk.Label(info_logger,
                text="📝 Логирует все отклоненные сигналы в CSV/JSON для последующего анализа. Файлы: data/rejected_signals/",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY,
                wraplength=650).pack(padx=15, pady=10, anchor='w')
        
        # Enable/Disable
        logger_enabled_frame = self._create_setting_row(content, "Включить Rejected Logger")
        self.v5_logger_enabled = tk.BooleanVar(value=v5_config.get('rejected_logger', {}).get('enabled', True))
        tk.Checkbutton(logger_enabled_frame, variable=self.v5_logger_enabled,
                      bg=Colors.BG_DARK, activebackground=Colors.BG_DARK,
                      selectcolor=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side='right')
        
        # Warning
        warning_frame = tk.Frame(content, bg=Colors.BG_CARD,
                                highlightbackground=Colors.WARNING,
                                highlightthickness=2)
        warning_frame.pack(fill='x', padx=30, pady=(20, 30))
        
        warning_text = """⚠️ ВАЖНО:
• V5 модули работают В ДОПОЛНЕНИЕ к существующим фильтрам (spread, ML, GPT)
• При отключении модулей система вернется к V4 логике
• Для применения изменений нажмите 'Apply & Restart'
• Статистика по отклоненным сигналам ежемесячно сохраняется в data/rejected_signals/"""
        
        tk.Label(warning_frame, text=warning_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.WARNING,
                justify='left',
                wraplength=650).pack(padx=15, pady=10, anchor='w')
        
        return frame
    
    def _create_gpt_api_tab(self):
        """GPT API настройки"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_DARK)
        
        # Scrollable content
        canvas = tk.Canvas(frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=content, anchor='nw')
        
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
        
        # Load AI config
        ai_config = {}
        try:
            ai_path = Path('config') / 'ai.yaml'
            if ai_path.exists():
                with open(ai_path, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.debug(f"Failed to load ai config: {e}")
            logger.debug(f"Failed to load ai config: {e}")
        
        gpt_settings = ai_config.get('market_analyst', {}).get('gpt', {})
        
        # API Key
        api_key_frame = tk.Frame(content, bg=Colors.BG_DARK)
        api_key_frame.pack(fill='x', pady=10)
        
        tk.Label(api_key_frame, text="API Key:",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY,
                width=15,
                anchor='w').pack(side='left')
        
        self.gpt_api_key = tk.Entry(api_key_frame, font=('Arial', 10), width=35, show='*')
        
        # Загрузить существующий API ключ из .env
        try:
            env_path = Path('.env')
            if env_path.exists() and load_dotenv:
                load_dotenv(env_path)
                existing_key = os.getenv('OPENAI_API_KEY', '')
                if existing_key:
                    self.gpt_api_key.insert(0, existing_key)
                    masked_key = f"****{existing_key[-4:]}" if len(existing_key) > 4 else "****"
                    logger.info(f"[SETTINGS] Loaded API key: {masked_key}")
        except Exception as e:
            logger.warning(f"[SETTINGS] Failed to load API key: {e}")
        
        self.gpt_api_key.pack(side='left', padx=(0, 5))
        self._bind_paste(self.gpt_api_key)
        
        # Paste button
        def paste_api_key():
            try:
                text = self.dialog.clipboard_get().strip()
                if text:
                    self.gpt_api_key.delete(0, tk.END)
                    self.gpt_api_key.insert(0, text)
                    logger.info(f"[SETTINGS] API key pasted (masked)")
            except Exception as e:
                logger.error(f"[SETTINGS] Paste failed: {e}")
                messagebox.showerror("Paste Error", f"Failed to paste: {e}")
        
        tk.Button(api_key_frame, text="📋",
                 font=('Arial', 9),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=8, pady=3,
                 command=paste_api_key).pack(side='left', padx=(0, 5))
        
        # Show/Hide button
        self.show_api_key = tk.BooleanVar(value=False)
        
        def toggle_api_key():
            if self.show_api_key.get():
                self.gpt_api_key.config(show='')
                show_btn.config(text='👁')
            else:
                self.gpt_api_key.config(show='*')
                show_btn.config(text='🔒')
        
        show_btn = tk.Button(api_key_frame, text="🔒",
                            font=('Arial', 9),
                            bg=Colors.BG_CARD,
                            fg=Colors.TEXT_PRIMARY,
                            relief='flat',
                            padx=8, pady=3,
                            command=lambda: [self.show_api_key.set(not self.show_api_key.get()), toggle_api_key()])
        show_btn.pack(side='left')
        
        # Model
        model_frame = self._create_setting_row(content, "Model:")
        self.gpt_model = ttk.Combobox(model_frame, width=20,
                                      values=['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'])
        self.gpt_model.set(gpt_settings.get('model', 'gpt-4o'))
        self.gpt_model.pack(side='right')
        
        # Base URL (optional)
        base_url_frame = self._create_setting_row(content, "Base URL (optional):")
        self.gpt_base_url = tk.Entry(base_url_frame, font=('Arial', 10), width=30)
        self.gpt_base_url.insert(0, gpt_settings.get('base_url', ''))
        self.gpt_base_url.pack(side='right')
        self._bind_paste(self.gpt_base_url)
        
        # Temperature
        temp_frame = self._create_setting_row(content, "Temperature (0.0-1.0):")
        self.gpt_temperature = tk.Entry(temp_frame, font=('Arial', 10), width=10)
        self.gpt_temperature.insert(0, str(gpt_settings.get('temperature', 0.3)))
        self.gpt_temperature.pack(side='right')
        self._bind_paste(self.gpt_temperature)
        
        # Timeout
        timeout_frame = self._create_setting_row(content, "Timeout (seconds):")
        self.gpt_timeout = tk.Entry(timeout_frame, font=('Arial', 10), width=10)
        self.gpt_timeout.insert(0, str(gpt_settings.get('timeout', 60)))
        self.gpt_timeout.pack(side='right')
        self._bind_paste(self.gpt_timeout)
        
        # Max Retries
        retry_frame = self._create_setting_row(content, "Max Retries:")
        self.gpt_max_retries = tk.Entry(retry_frame, font=('Arial', 10), width=10)
        self.gpt_max_retries.insert(0, str(gpt_settings.get('max_retries', 3)))
        self.gpt_max_retries.pack(side='right')
        self._bind_paste(self.gpt_max_retries)
        
        # Strict JSON
        strict_frame = self._create_setting_row(content, "Strict JSON Response:")
        self.gpt_strict_json = tk.BooleanVar(value=gpt_settings.get('strict_json', True))
        tk.Checkbutton(strict_frame, variable=self.gpt_strict_json,
                      bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      selectcolor=Colors.BG_CARD).pack(side='right')
        
        # === TEST CONNECTION ===
        self._create_section(content, "🧪 Test Connection")
        
        test_frame = tk.Frame(content, bg=Colors.BG_DARK)
        test_frame.pack(fill='x', pady=10)
        
        # Test status label
        self.gpt_test_status = tk.Label(test_frame,
                                        text="Click button to test GPT API",
                                        font=('Arial', 9),
                                        bg=Colors.BG_DARK,
                                        fg=Colors.TEXT_SECONDARY)
        self.gpt_test_status.pack(side='left', padx=(0, 10))
        
        def test_gpt_connection():
            """Test GPT API in background thread"""
            api_key = self.gpt_api_key.get().strip()
            
            if not api_key:
                messagebox.showerror("Error", "Please enter API Key before testing!")
                return
            
            # Update UI
            self.gpt_test_status.config(text="⏳ Testing...", fg=Colors.WARNING)
            test_btn.config(state='disabled')
            
            def run_test():
                start_time = time.time()
                
                try:
                    if openai is None:
                        raise ImportError("openai library is not installed")
                    
                    model = self.gpt_model.get()
                    timeout = int(self.gpt_timeout.get())
                    
                    # Test ping request
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=5,
                        timeout=timeout
                    )
                    
                    latency = int((time.time() - start_time) * 1000)
                    msg = f"✅ API OK (latency {latency}ms)"
                    
                    self.dialog.after(0, lambda: [
                        self.gpt_test_status.config(text=msg, fg=Colors.SUCCESS),
                        test_btn.config(state='normal'),
                        messagebox.showinfo("Success", f"GPT API is working!\n\nModel: {model}\nLatency: {latency}ms")
                    ])
                    logger.info(f"[SETTINGS] GPT test: SUCCESS ({latency}ms)")
                    
                except openai.AuthenticationError:
                    msg = "❌ Invalid API key / unauthorized"
                    self.dialog.after(0, lambda: [
                        self.gpt_test_status.config(text=msg, fg=Colors.ERROR),
                        test_btn.config(state='normal'),
                        messagebox.showerror("Failed", f"{msg}\n\nCheck your API key.")
                    ])
                    logger.error("[SETTINGS] GPT test: AUTH FAILED")
                    
                except Exception as e:
                    msg = f"❌ Error: {str(e)[:50]}"
                    self.dialog.after(0, lambda: [
                        self.gpt_test_status.config(text=msg, fg=Colors.ERROR),
                        test_btn.config(state='normal'),
                        messagebox.showerror("Failed", f"Connection failed:\n{e}")
                    ])
                    logger.error(f"[SETTINGS] GPT test: FAILED - {e}")
            
            # Run in background thread
            threading.Thread(target=run_test, daemon=True).start()
        
        test_btn = tk.Button(test_frame, text="🔌 TEST CONNECTION",
                            font=('Arial', 10, 'bold'),
                            bg=Colors.ACCENT,
                            fg='white',
                            relief='flat',
                            padx=15, pady=8,
                            command=test_gpt_connection)
        test_btn.pack(side='right')
        
        # Usage info
        usage_frame = tk.Frame(content, bg=Colors.BG_CARD,
                              highlightbackground=Colors.WARNING,
                              highlightthickness=1)
        usage_frame.pack(fill='x', pady=(20, 0))
        
        usage_text = """⚠️ Important:
• API key is stored in .env file (not committed to git)
• Typical cost: ~$0.01-0.05 per analysis
• Model: GPT-4o (recommended for best accuracy)
• Make sure you have credits on your OpenAI account"""
        
        tk.Label(usage_frame,
                text=usage_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.WARNING,
                justify='left',
                wraplength=500).pack(padx=15, pady=10, anchor='w')
        
        content.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
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
                with open(telegram_path, 'r', encoding='utf-8') as f:
                    telegram_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.debug(f"Failed to load telegram config: {e}")
        
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
                text = self.dialog.clipboard_get().strip()
                if text:
                    self.telegram_token.delete(0, tk.END)
                    self.telegram_token.insert(0, text)
                    masked_token = f"****{text[-6:]}" if len(text) > 6 else "****"
                    logger.info(f"[SETTINGS] Pasted Telegram token: {masked_token}")
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
                text = self.dialog.clipboard_get().strip()
                if text:
                    self.telegram_chat_id.delete(0, tk.END)
                    self.telegram_chat_id.insert(0, text)
                    logger.info(f"[SETTINGS] Pasted Chat ID: {text}")
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
        
        # Chat ID hint
        chat_hint = tk.Label(content,
                            text="💡 Get your Chat ID from @userinfobot (send /start to the bot)",
                            font=('Arial', 8, 'italic'),
                            bg=Colors.BG_DARK,
                            fg=Colors.TEXT_MUTED,
                            justify='left')
        chat_hint.pack(fill='x', pady=(2, 10), padx=20)
        
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
        
        # === TEST TELEGRAM CONNECTION ===
        self._create_section(content, "🧪 Test Connection")
        
        test_frame = tk.Frame(content, bg=Colors.BG_DARK)
        test_frame.pack(fill='x', pady=10)
        
        # Test status label
        self.telegram_test_status = tk.Label(test_frame,
                                             text="Click button to test bot",
                                             font=('Arial', 9),
                                             bg=Colors.BG_DARK,
                                             fg=Colors.TEXT_SECONDARY)
        self.telegram_test_status.pack(side='left', padx=(0, 10))
        
        def test_telegram():
            """Test Telegram connection in background thread"""
            token = self.telegram_token.get().strip()
            chat_id = self.telegram_chat_id.get().strip()
            
            if not token or not chat_id:
                messagebox.showerror("Error", "Please enter both Bot Token and Chat ID before testing!")
                return
            
            masked_token = f"****{token[-6:]}" if len(token) > 6 else "****"
            logger.info(f"[SETTINGS] Testing Telegram: token={masked_token}, chat_id={chat_id}")
            
            # Update UI
            self.telegram_test_status.config(text="⏳ Testing...", fg=Colors.WARNING)
            test_btn.config(state='disabled')
            
            def run_test():
                try:
                    # 1. Test getMe (validate token)
                    me_url = f"https://api.telegram.org/bot{token}/getMe"
                    me_response = requests.get(me_url, timeout=10)
                    me_data = me_response.json()
                    
                    if not me_data.get('ok'):
                        error_msg = me_data.get('description', 'Unknown error')
                        msg = f"❌ Invalid token: {error_msg}"
                        self.dialog.after(0, lambda: [
                            self.telegram_test_status.config(text=msg, fg=Colors.ERROR),
                            test_btn.config(state='normal'),
                            messagebox.showerror("Failed", f"Bot token is invalid:\n{error_msg}")
                        ])
                        logger.error(f"[SETTINGS] Telegram test: TOKEN INVALID - {error_msg}")
                        return
                    
                    bot_username = me_data['result'].get('username', 'Unknown')
                    
                    # 2. Test sendMessage (validate chat_id)
                    test_message = f"""
🧪 <b>BAZA Bot - Test Message</b>

✅ Telegram connection is working!

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Bot: @{bot_username}
💬 Chat ID: {chat_id}

If you received this message, Telegram notifications are configured correctly! 🎉
"""
                    
                    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                    send_data = {
                        'chat_id': chat_id,
                        'text': test_message.strip(),
                        'parse_mode': 'HTML'
                    }
                    send_response = requests.post(send_url, json=send_data, timeout=10)
                    send_result = send_response.json()
                    
                    if send_result.get('ok'):
                        msg = f"✅ Bot OK (@{bot_username})"
                        self.dialog.after(0, lambda: [
                            self.telegram_test_status.config(text=msg, fg=Colors.SUCCESS),
                            test_btn.config(state='normal'),
                            messagebox.showinfo("Success", 
                                              f"✅ Test message sent!\n\n"
                                              f"Bot: @{bot_username}\n"
                                              f"Chat ID: {chat_id}\n\n"
                                              f"Check your Telegram chat.")
                        ])
                        logger.info(f"[SETTINGS] Telegram test: SUCCESS (@{bot_username})") 
                    else:
                        error_desc = send_result.get('description', 'Unknown error')
                        
                        # Parse common errors
                        if 'chat not found' in error_desc.lower():
                            error_msg = "Chat ID not found. Make sure the bot has access to this chat."
                        elif 'forbidden' in error_desc.lower():
                            error_msg = "Bot was blocked by user or removed from chat."
                        elif 'unauthorized' in error_desc.lower():
                            error_msg = "Bot token is invalid or expired."
                        else:
                            error_msg = error_desc
                        
                        msg = f"❌ {error_msg[:40]}"
                        self.dialog.after(0, lambda: [
                            self.telegram_test_status.config(text=msg, fg=Colors.ERROR),
                            test_btn.config(state='normal'),
                            messagebox.showerror("Failed",
                                               f"Failed to send message:\n\n{error_msg}\n\n"
                                               f"Possible reasons:\n"
                                               f"• Invalid Chat ID\n"
                                               f"• Bot not added to chat\n"
                                               f"• Bot was blocked")
                        ])
                        logger.error(f"[SETTINGS] Telegram test: SEND FAILED - {error_msg}")
                        
                except requests.Timeout:
                    msg = "❌ Timeout (network issue)"
                    self.dialog.after(0, lambda: [
                        self.telegram_test_status.config(text=msg, fg=Colors.ERROR),
                        test_btn.config(state='normal'),
                        messagebox.showerror("Failed", "Connection timeout. Check your internet connection.")
                    ])
                    logger.error("[SETTINGS] Telegram test: TIMEOUT")
                    
                except Exception as e:
                    msg = f"❌ Error: {str(e)[:30]}"
                    self.dialog.after(0, lambda: [
                        self.telegram_test_status.config(text=msg, fg=Colors.ERROR),
                        test_btn.config(state='normal'),
                        messagebox.showerror("Failed", f"Test failed:\n{e}")
                    ])
                    logger.error(f"[SETTINGS] Telegram test: ERROR - {e}")
            
            # Run in background thread
            threading.Thread(target=run_test, daemon=True).start()
        
        test_btn = tk.Button(test_frame, text="🔌 TEST BOT",
                            font=('Arial', 10, 'bold'),
                            bg=Colors.ACCENT,
                            fg='white',
                            relief='flat',
                            padx=15, pady=8,
                            command=test_telegram)
        test_btn.pack(side='right')
        
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
            # AI config - NO GUI changes, all fixed in code
            # We don't save ai_enabled, model, temperature, etc from GUI anymore
            ai_config = self.configs.get('ai.yaml', {})
            
            # TTL настройки (сохраняем в trading.yaml)
            trading_config = self.configs.get('trading.yaml', {})
            if 'trading' not in trading_config:
                trading_config['trading'] = {}
            if 'signal_ttl' not in trading_config['trading']:
                trading_config['trading']['signal_ttl'] = {}
            
            trading_config['trading']['signal_ttl']['ttl_minutes'] = int(self.signal_validity.get())
            trading_config['trading']['signal_ttl']['auto_requery_on_expire'] = self.auto_requery_expire.get()
            trading_config['trading']['signal_ttl']['auto_requery_on_close'] = self.auto_requery_close.get()
            trading_config['trading']['signal_ttl']['requery_cooldown_minutes'] = int(self.requery_cooldown.get())
            trading_config['trading']['signal_ttl']['enabled'] = True
            
            # Portfolio config - NOT USED ANYMORE
            # portfolio_config = self.configs.get('portfolio.yaml', {})
            
            # Risk settings - ONLY FIXED LOT
            if 'risk' not in trading_config['trading']:
                trading_config['trading']['risk'] = {}
            
            trading_config['trading']['risk']['fixed_lot_size'] = float(self.fixed_lot.get())
            trading_config['trading']['risk']['default_sl_pips'] = int(self.default_sl.get())
            trading_config['trading']['risk']['default_tp_pips'] = int(self.default_tp.get())
            
            # Trailing stop - V4 (activation % and step %)
            if 'trailing_stop' not in trading_config['trading']:
                trading_config['trading']['trailing_stop'] = {}
            
            if hasattr(self, 'trail_enabled'):
                trading_config['trading']['trailing_stop']['enabled'] = self.trail_enabled.get()
            if hasattr(self, 'trail_activation_percent'):
                trading_config['trading']['trailing_stop']['activation_profit_percent'] = int(self.trail_activation_percent.get())
            if hasattr(self, 'trail_step_percent'):
                trading_config['trading']['trailing_stop']['trailing_step_percent'] = int(self.trail_step_percent.get())
            
            # Stop Loss Protection - защита от серии стопов
            if 'stop_loss_protection' not in trading_config['trading']:
                trading_config['trading']['stop_loss_protection'] = {}
            
            if hasattr(self, 'stop_protection_enabled'):
                trading_config['trading']['stop_loss_protection']['enabled'] = self.stop_protection_enabled.get()
            if hasattr(self, 'stop_protection_consecutive'):
                trading_config['trading']['stop_loss_protection']['consecutive_stops'] = int(self.stop_protection_consecutive.get())
            if hasattr(self, 'stop_protection_cooldown'):
                trading_config['trading']['stop_loss_protection']['cooldown_minutes'] = int(self.stop_protection_cooldown.get())
            
            # Profit Protection - фиксация прибыли
            if 'profit_protection' not in trading_config['trading']:
                trading_config['trading']['profit_protection'] = {}
            
            if hasattr(self, 'profit_protection_enabled'):
                trading_config['trading']['profit_protection']['enabled'] = self.profit_protection_enabled.get()
            if hasattr(self, 'profit_protection_consecutive'):
                trading_config['trading']['profit_protection']['consecutive_wins'] = int(self.profit_protection_consecutive.get())
            if hasattr(self, 'profit_protection_cooldown'):
                trading_config['trading']['profit_protection']['cooldown_minutes'] = int(self.profit_protection_cooldown.get())
            
            # Breakeven REMOVED - percentage-based trailing is sufficient
            
            # Trading hours - HARDCODED in bot logic (not from GUI)
            # Weekend: Sat/Sun always blocked
            # Night: 23:30-01:10 always blocked
            
            # Strategy tab removed
            
            # 🚀 V5 IMPROVEMENTS - новые модули
            if 'v5_improvements' not in trading_config['trading']:
                trading_config['trading']['v5_improvements'] = {}
            
            # Technical Filter
            if hasattr(self, 'v5_tech_enabled') and hasattr(self, 'v5_tech_strict'):
                trading_config['trading']['v5_improvements']['technical_filter'] = {
                    'enabled': self.v5_tech_enabled.get(),
                    'strict_mode': self.v5_tech_strict.get()
                }
            
            # Session Adapter
            if hasattr(self, 'v5_session_enabled'):
                trading_config['trading']['v5_improvements']['session_adapter'] = {
                    'enabled': self.v5_session_enabled.get()
                }
            
            # Adaptive Lot Sizing
            if hasattr(self, 'v5_lot_enabled') and hasattr(self, 'v5_lot_base') and hasattr(self, 'v5_lot_max') and hasattr(self, 'v5_lot_lookback'):
                trading_config['trading']['v5_improvements']['adaptive_lot'] = {
                    'enabled': self.v5_lot_enabled.get(),
                    'base_lot': float(self.v5_lot_base.get()),
                    'max_lot': float(self.v5_lot_max.get()),
                    'lookback_trades': int(self.v5_lot_lookback.get())
                }
            
            # Rejected Signals Logger
            if hasattr(self, 'v5_logger_enabled'):
                trading_config['trading']['v5_improvements']['rejected_logger'] = {
                    'enabled': self.v5_logger_enabled.get()
                }
            
            logger.info("[SETTINGS] 🚀 V5 Improvements configuration saved")
            
            # 🤖 AI ANALYSIS SETTINGS
            if 'pure_ai' not in ai_config:
                ai_config['pure_ai'] = {}
            
            if hasattr(self, 'analysis_interval'):
                ai_config['pure_ai']['analysis_interval_minutes'] = int(self.analysis_interval.get())
            ai_config['pure_ai']['enabled'] = True
            ai_config['pure_ai']['symbols'] = ['XAUUSD', 'EURUSD']
            ai_config['pure_ai']['timeframes'] = ['M5', 'M15']
            ai_config['pure_ai']['max_positions_per_symbol'] = 1
            
            if hasattr(self, 'analysis_interval'):
                logger.info(f"[SETTINGS] 🤖 AI Analysis interval: {self.analysis_interval.get()} minutes")
            
            # Time Restrictions (weekend_block, night_block)
            if 'market_analyst' not in ai_config:
                ai_config['market_analyst'] = {}
            if 'schedule' not in ai_config['market_analyst']:
                ai_config['market_analyst']['schedule'] = {}
            if 'restrictions' not in ai_config['market_analyst']['schedule']:
                ai_config['market_analyst']['schedule']['restrictions'] = {}
            
            # Weekend block
            if 'weekend_block' not in ai_config['market_analyst']['schedule']['restrictions']:
                ai_config['market_analyst']['schedule']['restrictions']['weekend_block'] = {}
            if hasattr(self, 'weekend_block'):
                ai_config['market_analyst']['schedule']['restrictions']['weekend_block']['enabled'] = self.weekend_block.get()
                ai_config['market_analyst']['schedule']['restrictions']['weekend_block']['friday_start'] = '22:00'
                ai_config['market_analyst']['schedule']['restrictions']['weekend_block']['monday_end'] = '01:00'
            
            # Night block
            if 'night_block' not in ai_config['market_analyst']['schedule']['restrictions']:
                ai_config['market_analyst']['schedule']['restrictions']['night_block'] = {}
            if hasattr(self, 'night_block'):
                ai_config['market_analyst']['schedule']['restrictions']['night_block']['enabled'] = self.night_block.get()
                ai_config['market_analyst']['schedule']['restrictions']['night_block']['start'] = '22:00'
                ai_config['market_analyst']['schedule']['restrictions']['night_block']['end'] = '02:00'
            
            if hasattr(self, 'weekend_block') and hasattr(self, 'night_block'):
                logger.info(f"[SETTINGS] ⏱ Time restrictions: Weekend={self.weekend_block.get()}, Night={self.night_block.get()}")
            
            # 🎮 MANUAL TRADING CONTROLS
            if 'manual_overrides' not in ai_config:
                ai_config['manual_overrides'] = {}
            
            if hasattr(self, 'manual_mode_enabled'):
                ai_config['manual_overrides']['enabled'] = self.manual_mode_enabled.get()
            
            # XAUUSD settings
            if hasattr(self, 'manual_xau_sl') and hasattr(self, 'manual_xau_tp') and hasattr(self, 'manual_xau_lot'):
                if 'xauusd' not in ai_config['manual_overrides']:
                    ai_config['manual_overrides']['xauusd'] = {}
                
                ai_config['manual_overrides']['xauusd']['sl_dollars'] = float(self.manual_xau_sl.get())
                ai_config['manual_overrides']['xauusd']['tp_dollars'] = float(self.manual_xau_tp.get())
                
                # Fixed lot (nullable)
                xau_lot_str = self.manual_xau_lot.get().strip()
                if xau_lot_str:
                    ai_config['manual_overrides']['xauusd']['fixed_lot'] = float(xau_lot_str)
                else:
                    ai_config['manual_overrides']['xauusd']['fixed_lot'] = None
            
            # EURUSD settings
            if hasattr(self, 'manual_eur_sl') and hasattr(self, 'manual_eur_tp') and hasattr(self, 'manual_eur_lot'):
                if 'eurusd' not in ai_config['manual_overrides']:
                    ai_config['manual_overrides']['eurusd'] = {}
                
                ai_config['manual_overrides']['eurusd']['sl_pips'] = int(self.manual_eur_sl.get())
                ai_config['manual_overrides']['eurusd']['tp_pips'] = int(self.manual_eur_tp.get())
                
                # Fixed lot (nullable)
                eur_lot_str = self.manual_eur_lot.get().strip()
                if eur_lot_str:
                    ai_config['manual_overrides']['eurusd']['fixed_lot'] = float(eur_lot_str)
                else:
                    ai_config['manual_overrides']['eurusd']['fixed_lot'] = None
            
            if hasattr(self, 'manual_mode_enabled') and hasattr(self, 'manual_xau_sl') and hasattr(self, 'manual_eur_sl'):
                logger.info(f"[SETTINGS] 🎮 Manual Mode: {self.manual_mode_enabled.get()} | "
                           f"XAUUSD SL=${self.manual_xau_sl.get()} TP=${self.manual_xau_tp.get()} | "
                           f"EURUSD SL={self.manual_eur_sl.get()}pips TP={self.manual_eur_tp.get()}pips")
            else:
                ai_config['manual_overrides']['eurusd']['fixed_lot'] = None
            
            logger.info(f"[SETTINGS] 🎮 Manual Mode: {self.manual_mode_enabled.get()} | "
                       f"XAUUSD SL=${self.manual_xau_sl.get()} TP=${self.manual_xau_tp.get()} | "
                       f"EURUSD SL={self.manual_eur_sl.get()}pips TP={self.manual_eur_tp.get()}pips")
            
            # 🛡️ SAFETY & LIMITS
            if 'safety_limits' not in trading_config['trading']:
                trading_config['trading']['safety_limits'] = {}
            
            # Daily Limits
            if hasattr(self, 'daily_limits_enabled') and hasattr(self, 'max_daily_loss') and hasattr(self, 'max_daily_profit'):
                trading_config['trading']['safety_limits']['enabled'] = self.daily_limits_enabled.get()
                trading_config['trading']['safety_limits']['max_daily_loss'] = float(self.max_daily_loss.get())
                trading_config['trading']['safety_limits']['max_daily_profit'] = float(self.max_daily_profit.get())
            
            # Position Limits
            if hasattr(self, 'max_open_positions') and hasattr(self, 'max_position_duration'):
                trading_config['trading']['safety_limits']['max_open_positions'] = int(self.max_open_positions.get())
                trading_config['trading']['safety_limits']['max_position_duration_hours'] = int(self.max_position_duration.get())
            
            # Session Limits
            if hasattr(self, 'max_trades_per_day') and hasattr(self, 'max_trades_per_hour') and hasattr(self, 'max_losses_in_row'):
                trading_config['trading']['safety_limits']['max_trades_per_day'] = int(self.max_trades_per_day.get())
                trading_config['trading']['safety_limits']['max_trades_per_hour'] = int(self.max_trades_per_hour.get())
                trading_config['trading']['safety_limits']['max_losses_in_row'] = int(self.max_losses_in_row.get())
            
            # Risk Management
            if hasattr(self, 'max_risk_per_trade') and hasattr(self, 'max_total_risk') and hasattr(self, 'max_lot_size') and hasattr(self, 'min_balance_protection'):
                trading_config['trading']['safety_limits']['max_risk_per_trade_pct'] = float(self.max_risk_per_trade.get())
                trading_config['trading']['safety_limits']['max_total_risk_pct'] = float(self.max_total_risk.get())
                trading_config['trading']['safety_limits']['max_lot_size'] = float(self.max_lot_size.get())
                trading_config['trading']['safety_limits']['min_balance_protection'] = float(self.min_balance_protection.get())
            
            # Cooldown Periods
            if hasattr(self, 'cooldown_after_loss') and hasattr(self, 'cooldown_after_win'):
                trading_config['trading']['safety_limits']['cooldown_after_loss_min'] = int(self.cooldown_after_loss.get())
                trading_config['trading']['safety_limits']['cooldown_after_win_min'] = int(self.cooldown_after_win.get())
            
            # Logging
            if hasattr(self, 'max_daily_loss') and hasattr(self, 'max_open_positions'):
                logger.info(f"[SETTINGS] 🛡️ Safety Limits: Loss=${self.max_daily_loss.get()} Profit=${self.max_daily_profit.get()} "
                           f"MaxPos={self.max_open_positions.get()} MaxTrades/Day={getattr(self.max_trades_per_day, 'get', lambda: 'N/A')()} "
                           f"MaxLossesRow={getattr(self.max_losses_in_row, 'get', lambda: 'N/A')()}")
            if hasattr(self, 'max_risk_per_trade') and hasattr(self, 'max_lot_size'):
                logger.info(f"[SETTINGS] ⚠️ Risk Management: MaxRisk/Trade={self.max_risk_per_trade.get()}% "
                           f"MaxTotalRisk={self.max_total_risk.get()}% MaxLot={self.max_lot_size.get()} "
                           f"MinBalance=${self.min_balance_protection.get()}")
            if hasattr(self, 'cooldown_after_loss'):
                logger.info(f"[SETTINGS] ⏸️ Cooldowns: AfterLoss={self.cooldown_after_loss.get()}min "
                           f"AfterWin={self.cooldown_after_win.get()}min")
            
            # GPT Safety Limits (in ai.yaml)
            if 'market_analyst' not in ai_config:
                ai_config['market_analyst'] = {}
            if 'safety' not in ai_config['market_analyst']:
                ai_config['market_analyst']['safety'] = {}
            
            if hasattr(self, 'max_daily_calls'):
                ai_config['market_analyst']['safety']['max_daily_calls'] = int(self.max_daily_calls.get())
            if hasattr(self, 'max_monthly_cost'):
                ai_config['market_analyst']['safety']['max_monthly_cost'] = float(self.max_monthly_cost.get())
            
            # GPT API Settings (in ai.yaml)
            if 'gpt' not in ai_config['market_analyst']:
                ai_config['market_analyst']['gpt'] = {}
            
            if hasattr(self, 'gpt_model'):
                ai_config['market_analyst']['gpt']['model'] = self.gpt_model.get()
            if hasattr(self, 'gpt_temperature'):
                ai_config['market_analyst']['gpt']['temperature'] = float(self.gpt_temperature.get())
            if hasattr(self, 'gpt_timeout'):
                ai_config['market_analyst']['gpt']['timeout'] = int(self.gpt_timeout.get())
            if hasattr(self, 'gpt_max_retries'):
                ai_config['market_analyst']['gpt']['max_retries'] = int(self.gpt_max_retries.get())
            if hasattr(self, 'gpt_strict_json'):
                ai_config['market_analyst']['gpt']['strict_json'] = self.gpt_strict_json.get()
            if hasattr(self, 'gpt_base_url'):
                base_url = self.gpt_base_url.get().strip()
                if base_url:
                    ai_config['market_analyst']['gpt']['base_url'] = base_url
                elif 'base_url' in ai_config['market_analyst']['gpt']:
                    del ai_config['market_analyst']['gpt']['base_url']
            
            # Log GPT settings (masked)
            if hasattr(self, 'gpt_api_key') and hasattr(self, 'gpt_model'):
                api_key = self.gpt_api_key.get().strip()
                masked_key = f"****{api_key[-4:]}" if len(api_key) >= 4 else "****"
                logger.info(f"[SETTINGS] 🤖 GPT API: model={self.gpt_model.get()}, temp={self.gpt_temperature.get()}, "
                           f"timeout={self.gpt_timeout.get()}s, retries={self.gpt_max_retries.get()}, key={masked_key}")
            
            # ⚙️ ADVANCED SETTINGS
            # Trading Hours
            if hasattr(self, 'trading_start') and hasattr(self, 'trading_end'):
                if 'hours' not in trading_config['trading']:
                    trading_config['trading']['hours'] = {}
                
                trading_config['trading']['hours']['start'] = self.trading_start.get()
                trading_config['trading']['hours']['end'] = self.trading_end.get()
            
            # Max Spread
            if hasattr(self, 'max_spread'):
                trading_config['trading']['risk']['max_spread_pips'] = float(self.max_spread.get())
            
            # Operating Mode
            if hasattr(self, 'operating_mode'):
                trading_config['trading']['operating_mode'] = self.operating_mode.get()
            
            if hasattr(self, 'trading_start') and hasattr(self, 'operating_mode'):
                logger.info(f"[SETTINGS] ⚙️ Advanced: Hours={self.trading_start.get()}-{self.trading_end.get()} Mode={self.operating_mode.get()}")

            telegram_config = {}
            telegram_path = Path('config') / 'telegram.yaml'
            if telegram_path.exists():
                with open(telegram_path, 'r', encoding='utf-8') as f:
                    telegram_config = yaml.safe_load(f) or {}
            
            if 'telegram' not in telegram_config:
                telegram_config['telegram'] = {}
            
            if hasattr(self, 'telegram_enabled'):
                telegram_config['telegram']['enabled'] = self.telegram_enabled.get()
            if hasattr(self, 'telegram_token'):
                telegram_config['telegram']['bot_token'] = self.telegram_token.get()
            if hasattr(self, 'telegram_chat_id'):
                telegram_config['telegram']['chat_id'] = self.telegram_chat_id.get()
            if hasattr(self, 'telegram_enable_bot'):
                telegram_config['telegram']['enable_bot'] = self.telegram_enable_bot.get()
            
            if 'notify' not in telegram_config['telegram']:
                telegram_config['telegram']['notify'] = {}
            
            if hasattr(self, 'notify_startup'):
                telegram_config['telegram']['notify']['startup'] = self.notify_startup.get()
            if hasattr(self, 'notify_trade_opened'):
                telegram_config['telegram']['notify']['trade_opened'] = self.notify_trade_opened.get()
            if hasattr(self, 'notify_trade_closed'):
                telegram_config['telegram']['notify']['trade_closed'] = self.notify_trade_closed.get()
            if hasattr(self, 'notify_daily_report'):
                telegram_config['telegram']['notify']['daily_report'] = self.notify_daily_report.get()
            if hasattr(self, 'notify_alerts'):
                telegram_config['telegram']['notify']['alerts'] = self.notify_alerts.get()
            if hasattr(self, 'alert_min_level'):
                telegram_config['telegram']['alert_min_level'] = self.alert_min_level.get()
            
            # Log Telegram settings (masked)
            if hasattr(self, 'telegram_token') and hasattr(self, 'telegram_chat_id'):
                token = self.telegram_token.get().strip()
                masked_token = f"****{token[-6:]}" if len(token) >= 6 else "****"
                logger.info(f"[SETTINGS] 📱 Telegram: enabled={self.telegram_enabled.get()}, "
                           f"bot_enabled={self.telegram_enable_bot.get()}, token={masked_token}, chat_id={self.telegram_chat_id.get()}")
            
            # Сохранить GPT API key в .env
            env_path = Path('.env')
            env_lines = []
            api_key_updated = False
            
            if hasattr(self, 'gpt_api_key'):
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
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
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.writelines(env_lines)
                    
                    # Update environment variable
                    os.environ['OPENAI_API_KEY'] = new_api_key
            
            # Сохранить файлы
            # Save config files
            ai_path = Path('config') / 'ai.yaml'
            with open(ai_path, 'w', encoding='utf-8') as f:
                yaml.dump(ai_config, f, default_flow_style=False, allow_unicode=True)
            
            # Portfolio config - REMOVED (no % risk logic anymore)
            
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
            if hasattr(self, 'xauusd_enabled'):
                instruments_config['instruments']['XAUUSD']['enabled'] = self.xauusd_enabled.get()
            if hasattr(self, 'xauusd_analysis'):
                instruments_config['instruments']['XAUUSD']['analysis_enabled'] = self.xauusd_analysis.get()
            if hasattr(self, 'xauusd_trading'):
                instruments_config['instruments']['XAUUSD']['trading_enabled'] = self.xauusd_trading.get()
            if hasattr(self, 'xauusd_max_trades'):
                instruments_config['instruments']['XAUUSD']['max_trades_per_day'] = int(self.xauusd_max_trades.get())
            if hasattr(self, 'xauusd_commission'):
                instruments_config['instruments']['XAUUSD']['commission_per_lot'] = float(self.xauusd_commission.get())
            
            # Update EURUSD
            if 'EURUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['EURUSD'] = {}
            if hasattr(self, 'eurusd_enabled'):
                instruments_config['instruments']['EURUSD']['enabled'] = self.eurusd_enabled.get()
            if hasattr(self, 'eurusd_analysis'):
                instruments_config['instruments']['EURUSD']['analysis_enabled'] = self.eurusd_analysis.get()
            if hasattr(self, 'eurusd_trading'):
                instruments_config['instruments']['EURUSD']['trading_enabled'] = self.eurusd_trading.get()
            if hasattr(self, 'eurusd_max_trades'):
                instruments_config['instruments']['EURUSD']['max_trades_per_day'] = int(self.eurusd_max_trades.get())
            if hasattr(self, 'eurusd_commission'):
                instruments_config['instruments']['EURUSD']['commission_per_lot'] = float(self.eurusd_commission.get())
            
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
            # First, save all settings using existing _save_settings logic
            # But we need to save without closing dialog
            
            # Copy-paste save logic here (DRY violation, but necessary for restart flow)
            # Load configs
            ai_config = self.configs.get('ai.yaml', {})
            trading_config = self.configs.get('trading.yaml', {})
            
            # TTL settings
            if 'trading' not in trading_config:
                trading_config['trading'] = {}
            if 'signal_ttl' not in trading_config['trading']:
                trading_config['trading']['signal_ttl'] = {}
            
            trading_config['trading']['signal_ttl']['ttl_minutes'] = int(self.signal_validity.get())
            trading_config['trading']['signal_ttl']['auto_requery_on_expire'] = self.auto_requery_expire.get()
            trading_config['trading']['signal_ttl']['auto_requery_on_close'] = self.auto_requery_close.get()
            trading_config['trading']['signal_ttl']['requery_cooldown_minutes'] = int(self.requery_cooldown.get())
            trading_config['trading']['signal_ttl']['enabled'] = True
            
            # Risk settings - ONLY FIXED LOT
            if 'risk' not in trading_config['trading']:
                trading_config['trading']['risk'] = {}
            
            trading_config['trading']['risk']['fixed_lot_size'] = float(self.fixed_lot.get())
            trading_config['trading']['risk']['default_sl_pips'] = int(self.default_sl.get())
            trading_config['trading']['risk']['default_tp_pips'] = int(self.default_tp.get())
            
            # Trailing stop
            if 'trailing_stop' not in trading_config['trading']:
                trading_config['trading']['trailing_stop'] = {}
            
            trading_config['trading']['trailing_stop']['enabled'] = self.trail_enabled.get()
            trading_config['trading']['trailing_stop']['activation_profit_percent'] = int(self.trail_activation_percent.get())
            trading_config['trading']['trailing_stop']['trailing_step_percent'] = int(self.trail_step_percent.get())
            
            # Stop Loss Protection - защита от серии стопов
            if 'stop_loss_protection' not in trading_config['trading']:
                trading_config['trading']['stop_loss_protection'] = {}
            
            trading_config['trading']['stop_loss_protection']['enabled'] = self.stop_protection_enabled.get()
            trading_config['trading']['stop_loss_protection']['consecutive_stops'] = int(self.stop_protection_consecutive.get())
            trading_config['trading']['stop_loss_protection']['cooldown_minutes'] = int(self.stop_protection_cooldown.get())
            
            # Profit Protection - фиксация прибыли
            if 'profit_protection' not in trading_config['trading']:
                trading_config['trading']['profit_protection'] = {}
            
            trading_config['trading']['profit_protection']['enabled'] = self.profit_protection_enabled.get()
            trading_config['trading']['profit_protection']['consecutive_wins'] = int(self.profit_protection_consecutive.get())
            trading_config['trading']['profit_protection']['cooldown_minutes'] = int(self.profit_protection_cooldown.get())
            
            # Breakeven REMOVED
            
            # 🚀 V5 IMPROVEMENTS - новые модули
            if 'v5_improvements' not in trading_config['trading']:
                trading_config['trading']['v5_improvements'] = {}
            
            # Technical Filter
            trading_config['trading']['v5_improvements']['technical_filter'] = {
                'enabled': self.v5_tech_enabled.get(),
                'strict_mode': self.v5_tech_strict.get()
            }
            
            # Session Adapter
            trading_config['trading']['v5_improvements']['session_adapter'] = {
                'enabled': self.v5_session_enabled.get()
            }
            
            # Adaptive Lot Sizing
            trading_config['trading']['v5_improvements']['adaptive_lot'] = {
                'enabled': self.v5_lot_enabled.get(),
                'base_lot': float(self.v5_lot_base.get()),
                'max_lot': float(self.v5_lot_max.get()),
                'lookback_trades': int(self.v5_lot_lookback.get())
            }
            
            # Rejected Signals Logger
            trading_config['trading']['v5_improvements']['rejected_logger'] = {
                'enabled': self.v5_logger_enabled.get()
            }
            
            logger.info("[SETTINGS] 🚀 V5 Improvements configuration saved (restart mode)")
            
            # 🤖 AI ANALYSIS SETTINGS
            if 'pure_ai' not in ai_config:
                ai_config['pure_ai'] = {}
            
            ai_config['pure_ai']['analysis_interval_minutes'] = int(self.analysis_interval.get())
            ai_config['pure_ai']['enabled'] = True
            ai_config['pure_ai']['symbols'] = ['XAUUSD', 'EURUSD']
            ai_config['pure_ai']['timeframes'] = ['M5', 'M15']
            ai_config['pure_ai']['max_positions_per_symbol'] = 1
            
            logger.info(f"[SETTINGS] 🤖 AI Analysis interval: {self.analysis_interval.get()} minutes (restart mode)")
            
            # Telegram
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
            
            # GPT API key
            env_path = Path('.env')
            env_lines = []
            api_key_updated = False
            
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()
            
            new_api_key = self.gpt_api_key.get().strip()
            if new_api_key:
                for i, line in enumerate(env_lines):
                    if line.startswith('OPENAI_API_KEY='):
                        env_lines[i] = f'OPENAI_API_KEY={new_api_key}\n'
                        api_key_updated = True
                        break
                
                if not api_key_updated:
                    env_lines.append(f'OPENAI_API_KEY={new_api_key}\n')
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(env_lines)
                
                os.environ['OPENAI_API_KEY'] = new_api_key
            
            # Save files
            ai_path = Path('config') / 'ai.yaml'
            with open(ai_path, 'w', encoding='utf-8') as f:
                yaml.dump(ai_config, f, default_flow_style=False, allow_unicode=True)
            
            trading_path = Path('config') / 'trading.yaml'
            with open(trading_path, 'w', encoding='utf-8') as f:
                yaml.dump(trading_config, f, default_flow_style=False, allow_unicode=True)
            
            with open(telegram_path, 'w', encoding='utf-8') as f:
                yaml.dump(telegram_config, f, default_flow_style=False, allow_unicode=True)
            
            # Instruments config
            instruments_path = Path('config') / 'instruments.yaml'
            instruments_config = {}
            if instruments_path.exists():
                with open(instruments_path, 'r', encoding='utf-8') as f:
                    instruments_config = yaml.safe_load(f) or {}
            
            if 'instruments' not in instruments_config:
                instruments_config['instruments'] = {}
            
            if 'XAUUSD' not in instruments_config['instruments']:
                instruments_config['instruments']['XAUUSD'] = {}
            instruments_config['instruments']['XAUUSD']['enabled'] = self.xauusd_enabled.get()
            instruments_config['instruments']['XAUUSD']['analysis_enabled'] = self.xauusd_analysis.get()
            instruments_config['instruments']['XAUUSD']['trading_enabled'] = self.xauusd_trading.get()
            
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
            
            # Close dialog
            self.dialog.destroy()
            
            # Trigger restart via callback
            if self.on_save_callback:
                self.on_save_callback(restart=True)
            
            messagebox.showinfo("Success", "Settings saved!\\nBot will restart with new configuration.")
            
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save and restart: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\\n{e}")
    
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
            
            # ОТКЛЮЧЕНО: Не открываем редакторы/файлы (по требованию пользователя)
            # Вместо этого показываем messagebox с инструкцией
            messagebox.showinfo(
                "Lot Size Guide",
                f"Руководство находится здесь:\n{guide_path}\n\n"
                "Откройте его вручную для просмотра.",
                parent=self.dialog
            )
            
            logger.info(f"[SETTINGS] User notified about lot size guide: {guide_path}")
            
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
    
    # === QUICK ACTIONS HANDLERS ===
    
    def _force_analysis(self):
        """Принудительный запуск AI анализа"""
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            
            if hasattr(bot_manager, 'analyst_scheduler') and bot_manager.analyst_scheduler:
                bot_manager.analyst_scheduler.force_analysis()
                messagebox.showinfo("Success", "🚀 AI Analysis запущен!\\n\\nАнализ начнется в течение 10 секунд.\\nПроверьте логи для результатов.")
                logger.info("[SETTINGS] Force AI Analysis triggered from GUI")
            else:
                messagebox.showwarning("Warning", "Бот не запущен или analyst_scheduler недоступен")
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка запуска анализа:\\n{str(e)}")
            logger.error(f"[SETTINGS] Force analysis error: {e}")
    
    def _reload_config(self):
        """Перезагрузка конфигов"""
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            
            if hasattr(bot_manager, 'reload_configs'):
                bot_manager.reload_configs()
                messagebox.showinfo("Success", "🔄 Конфиги перезагружены!\\n\\nВсе изменения применены без перезапуска бота.")
                logger.info("[SETTINGS] Config reload triggered from GUI")
            else:
                messagebox.showinfo("Info", "Перезагрузка конфигов будет выполнена при следующем запуске бота")
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка перезагрузки:\\n{str(e)}")
            logger.error(f"[SETTINGS] Reload config error: {e}")
    
    def _open_logs_folder(self):
        """Открыть папку с логами"""
        try:
            import subprocess
            import platform
            logs_path = Path('logs').absolute()
            
            if not logs_path.exists():
                logs_path.mkdir(parents=True, exist_ok=True)
            
            if platform.system() == 'Windows':
                subprocess.Popen(f'explorer "{logs_path}"')
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', str(logs_path)])
            else:  # Linux
                subprocess.Popen(['xdg-open', str(logs_path)])
            
            logger.info(f"[SETTINGS] Opened logs folder: {logs_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Не удалось открыть папку:\\n{str(e)}")
            logger.error(f"[SETTINGS] Open logs folder error: {e}")
    
    def _open_screenshots_folder(self):
        """Открыть папку со скриншотами"""
        try:
            import subprocess
            import platform
            screenshots_path = Path('data/screenshots').absolute()
            
            if not screenshots_path.exists():
                screenshots_path.mkdir(parents=True, exist_ok=True)
            
            if platform.system() == 'Windows':
                subprocess.Popen(f'explorer "{screenshots_path}"')
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', str(screenshots_path)])
            else:
                subprocess.Popen(['xdg-open', str(screenshots_path)])
            
            logger.info(f"[SETTINGS] Opened screenshots folder: {screenshots_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Не удалось открыть папку:\\n{str(e)}")
            logger.error(f"[SETTINGS] Open screenshots folder error: {e}")
    
    def _clean_old_data(self):
        """Очистка старых данных"""
        try:
            result = messagebox.askyesno("Confirm", 
                                        "🧹 Очистить старые данные?\\n\\n"
                                        "Будут удалены:\\n"
                                        "• Скриншоты старше 7 дней\\n"
                                        "• Логи старше 30 дней\\n\\n"
                                        "Продолжить?")
            
            if result:
                # Clean screenshots
                screenshots_path = Path('data/screenshots')
                cleaned_screens = 0
                if screenshots_path.exists():
                    now = time.time()
                    for file in screenshots_path.glob('*.png'):
                        if now - file.stat().st_mtime > 7 * 86400:  # 7 days
                            file.unlink()
                            cleaned_screens += 1
                
                # Clean logs
                logs_path = Path('logs')
                cleaned_logs = 0
                if logs_path.exists():
                    now = time.time()
                    for file in logs_path.glob('*.log'):
                        if now - file.stat().st_mtime > 30 * 86400:  # 30 days
                            file.unlink()
                            cleaned_logs += 1
                
                messagebox.showinfo("Success", 
                                  f"🧹 Очистка завершена!\\n\\n"
                                  f"Удалено:\\n"
                                  f"• Скриншоты: {cleaned_screens}\\n"
                                  f"• Логи: {cleaned_logs}")
                logger.info(f"[SETTINGS] Cleaned old data: {cleaned_screens} screenshots, {cleaned_logs} logs")
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка очистки:\\n{str(e)}")
            logger.error(f"[SETTINGS] Clean old data error: {e}")
    
    def _view_today_stats(self):
        """Показать статистику за сегодня"""
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            
            if hasattr(bot_manager, 'live_trader') and bot_manager.live_trader:
                today_stats = bot_manager.live_trader.get_today_stats()
                
                stats_text = (
                    f"📊 Статистика за сегодня:\\n\\n"
                    f"💰 Баланс: ${today_stats.get('balance', 0):.2f}\\n"
                    f"📈 Прибыль: ${today_stats.get('profit', 0):.2f}\\n"
                    f"📉 Просадка: ${today_stats.get('drawdown', 0):.2f}\\n"
                    f"🔢 Сделок: {today_stats.get('trades', 0)}\\n"
                    f"✅ Прибыльных: {today_stats.get('wins', 0)}\\n"
                    f"❌ Убыточных: {today_stats.get('losses', 0)}\\n"
                    f"📊 Винрейт: {today_stats.get('winrate', 0):.1f}%"
                )
                
                messagebox.showinfo("Today's Stats", stats_text)
                logger.info("[SETTINGS] Displayed today's stats")
            else:
                messagebox.showinfo("Info", "Бот не запущен.\\nСтатистика недоступна.")
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка получения статистики:\\n{str(e)}")
            logger.error(f"[SETTINGS] View today stats error: {e}")
    
    def _emergency_stop(self):
        """Аварийная остановка"""
        try:
            result = messagebox.askyesnocancel("⚠️ EMERGENCY STOP", 
                                              "⚠️ АВАРИЙНАЯ ОСТАНОВКА!\\n\\n"
                                              "Это действие:\\n"
                                              "• Закроет ВСЕ открытые позиции НЕМЕДЛЕННО\\n"
                                              "• Остановит бота\\n"
                                              "• Прекратит любые операции\\n\\n"
                                              "Вы УВЕРЕНЫ?",
                                              icon='warning')
            
            if result:
                from src.core.bot_manager import BotManager
                bot_manager = BotManager()
                
                if hasattr(bot_manager, 'emergency_stop'):
                    bot_manager.emergency_stop()
                    messagebox.showinfo("Stopped", "⚡ EMERGENCY STOP выполнен!\\n\\nВсе позиции закрыты.\\nБот остановлен.")
                    logger.warning("[SETTINGS] EMERGENCY STOP triggered from GUI")
                else:
                    messagebox.showinfo("Info", "Бот уже остановлен")
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка аварийной остановки:\\n{str(e)}")
            logger.error(f"[SETTINGS] Emergency stop error: {e}")

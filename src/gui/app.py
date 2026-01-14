#!/usr/bin/env python3
"""
BAZA Trading Bot - Modern Trading Terminal UI
Минималистичный профессиональный интерфейс в стиле TradingView/MT5
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from datetime import datetime
from pathlib import Path
import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.app_state import AppState
from src.core.mt5_manager import MT5Manager
from src.core.bot_manager import bot_manager, BotManager
from src.core.diagnostics import SystemDiagnostics
from src.live.live_trader import LiveTrader
from src.gui.settings_dialog import SettingsDialog
from src.gui.mt5_dialog import MT5Dialog
from src.core.logger import logger as app_logger
from src.core.market_data_updater import MarketDataUpdater

# Система обновлений
from version import APP_VERSION, VERSION_CHECK_URL
from updater import UpdateChecker, UpdateWindow

try:
    from src.ai.analyst_scheduler import get_scheduler, init_scheduler
    from src.ai.signal_manager import AISignalManager
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False


# ==================== COLOR SCHEME ====================
class Colors:
    """Цветовая схема в стиле TradingView"""
    BG_DARK = '#0d1117'           # Основной фон
    BG_PANEL = '#161b22'          # Панели
    BG_CARD = '#1c2128'           # Карточки
    BG_HOVER = '#21262d'          # Hover состояние
    
    BORDER = '#30363d'            # Границы
    TEXT_PRIMARY = '#c9d1d9'      # Основной текст
    TEXT_SECONDARY = '#8b949e'    # Вторичный текст
    TEXT_MUTED = '#6e7681'        # Приглушённый текст
    
    ACCENT = '#58a6ff'            # Акцент (синий)
    SUCCESS = '#3fb950'           # Успех (зелёный)
    ERROR = '#f85149'             # Ошибка (красный)
    WARNING = '#d29922'           # Предупреждение (жёлтый)
    
    BUY = '#26a69a'               # Покупка (бирюзовый)
    SELL = '#ef5350'              # Продажа (красный)


# ==================== HEADER PANEL ====================
class HeaderPanel(tk.Frame):
    """Верхняя status-панель"""
    
    def __init__(self, parent, app_state):
        super().__init__(parent, bg=Colors.BG_PANEL, height=50)
        self.app_state = app_state
        self.pack_propagate(False)
        
        # MT5 Status
        status_frame = tk.Frame(self, bg=Colors.BG_PANEL)
        status_frame.pack(side='left', padx=20, pady=10)
        
        self.mt5_indicator = tk.Label(status_frame, text="●", 
                                      font=('Arial', 16), 
                                      bg=Colors.BG_PANEL, 
                                      fg=Colors.ERROR)
        self.mt5_indicator.pack(side='left', padx=(0, 5))
        
        self.mt5_label = tk.Label(status_frame, text="MT5: Disconnected",
                                 font=('Arial', 10, 'bold'),
                                 bg=Colors.BG_PANEL, 
                                 fg=Colors.TEXT_SECONDARY)
        self.mt5_label.pack(side='left')
        
        # Price Display
        price_frame = tk.Frame(self, bg=Colors.BG_PANEL)
        price_frame.pack(side='left', padx=20)
        
        tk.Label(price_frame, text="XAUUSD",
                font=('Arial', 9),
                bg=Colors.BG_PANEL,
                fg=Colors.TEXT_MUTED).pack(side='left', padx=(0, 10))
        
        self.price_label = tk.Label(price_frame, text="---",
                                    font=('Arial', 14, 'bold'),
                                    bg=Colors.BG_PANEL,
                                    fg=Colors.TEXT_PRIMARY)
        self.price_label.pack(side='left')
        
        # Mode Display
        mode_frame = tk.Frame(self, bg=Colors.BG_PANEL)
        mode_frame.pack(side='right', padx=20)
        
        self.mode_label = tk.Label(mode_frame, text="LIVE",
                                   font=('Arial', 10, 'bold'),
                                   bg=Colors.BG_DARK,
                                   fg=Colors.SUCCESS,
                                   padx=12, pady=4)
        self.mode_label.pack()
    
    def update_mt5_status(self, connected: bool):
        """Обновить статус MT5"""
        if connected:
            self.mt5_indicator.config(fg=Colors.SUCCESS)
            self.mt5_label.config(text="MT5: Connected", fg=Colors.SUCCESS)
        else:
            self.mt5_indicator.config(fg=Colors.ERROR)
            self.mt5_label.config(text="MT5: Disconnected", fg=Colors.ERROR)
    
    def update_price(self, price: float):
        """Обновить цену"""
        self.price_label.config(text=f"{price:.2f}")


# ==================== MODE SELECTOR ====================
class ModeSelector(tk.Frame):
    """Выбор режима торговли через Radiobutton"""
    
    def __init__(self, parent, on_mode_change):
        super().__init__(parent, bg=Colors.BG_DARK)
        self.on_mode_change = on_mode_change
        self.mode_var = tk.StringVar(value="strategy")
        
        # Заголовок
        tk.Label(self, text="Режим торговли:", 
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w', pady=(0, 15))
        
        # Strategy + AI
        rb1 = tk.Radiobutton(
            self,
            text="Strategy + AI  (Стратегия + GPT фильтр)",
            variable=self.mode_var,
            value="strategy",
            font=('Arial', 11),
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_PRIMARY,
            selectcolor=Colors.BG_CARD,
            activebackground=Colors.BG_DARK,
            activeforeground=Colors.SUCCESS,
            command=self._on_mode_change
        )
        rb1.pack(anchor='w', pady=5)
        
        # Pure AI Trading
        rb2 = tk.Radiobutton(
            self,
            text="Pure AI Trading  (Только GPT сигналы)",
            variable=self.mode_var,
            value="pure_ai",
            font=('Arial', 11),
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_PRIMARY,
            selectcolor=Colors.BG_CARD,
            activebackground=Colors.BG_DARK,
            activeforeground=Colors.SUCCESS,
            command=self._on_mode_change
        )
        rb2.pack(anchor='w', pady=5)
        
        # Статус
        status_frame = tk.Frame(self, bg=Colors.BG_CARD, 
                               highlightbackground=Colors.BORDER,
                               highlightthickness=1)
        status_frame.pack(fill='x', pady=(15, 0))
        
        self.status_label = tk.Label(status_frame, text="● Готов к запуску",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED)
        self.status_label.pack(pady=8)
        
        self.mode_status_label = tk.Label(status_frame, text="Режим: Live",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY)
        self.mode_status_label.pack(pady=(0, 8))
    
    def update_status(self, is_running):
        """Обновить статус активности"""
        if is_running:
            self.status_label.config(text="● Бот активен", fg=Colors.SUCCESS)
        else:
            self.status_label.config(text="● Готов к запуску", fg=Colors.TEXT_MUTED)
    
    def _on_mode_change(self):
        """Обработка смены режима"""
        mode = self.mode_var.get()
        if self.on_mode_change:
            self.on_mode_change(mode)


# ==================== CONTROL PANEL ====================
class ControlPanel(tk.Frame):
    """Панель управления ботом"""
    
    def __init__(self, parent, on_start, on_stop):
        super().__init__(parent, bg=Colors.BG_DARK)
        self.on_start = on_start
        self.on_stop = on_stop
        self.is_running = False
        
        # Контейнер для кнопки
        btn_container = tk.Frame(self, bg=Colors.BG_DARK)
        btn_container.pack(pady=15)
        
        # Одна кнопка Start/Stop
        self.control_btn = tk.Button(
            btn_container,
            text="▶ START BOT",
            font=('Arial', 12, 'bold'),
            bg=Colors.SUCCESS,
            fg='black',
            activebackground=Colors.SUCCESS,
            activeforeground='black',
            relief='flat',
            cursor='hand2',
            width=20,
            height=2,
            command=self._toggle_bot
        )
        self.control_btn.pack()
    
    def _toggle_bot(self):
        """Переключение Start/Stop"""
        if self.is_running:
            self.control_btn.config(text="▶ START BOT", bg=Colors.SUCCESS)
            self.is_running = False
            if self.on_stop:
                self.on_stop()
        else:
            self.control_btn.config(text="■ STOP BOT", bg=Colors.ERROR)
            self.is_running = True
            if self.on_start:
                self.on_start()
    
    def set_bot_running(self, running):
        """Установить состояние бота извне"""
        self.is_running = running
        if running:
            self.control_btn.config(text="■ STOP BOT", bg=Colors.ERROR)
        else:
            self.control_btn.config(text="▶ START BOT", bg=Colors.SUCCESS)


# ==================== STATS PANEL ====================
class StatsPanel(tk.Frame):
    """Панель статистики"""
    
    def __init__(self, parent, app_state):
        super().__init__(parent, bg=Colors.BG_DARK)
        self.app_state = app_state
        
        tk.Label(self, text="Account Statistics",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(pady=(0, 10))
        
        # Контейнер для карточек
        cards_frame = tk.Frame(self, bg=Colors.BG_DARK)
        cards_frame.pack(fill='x')
        
        # Balance
        self.balance_card = self._create_stat_card(cards_frame, "Balance", "$0.00", Colors.TEXT_PRIMARY)
        self.balance_card.pack(side='left', fill='both', expand=True, padx=5)
        
        # Today PnL
        self.today_pnl_card = self._create_stat_card(cards_frame, "Today P&L", "$0.00", Colors.TEXT_SECONDARY)
        self.today_pnl_card.pack(side='left', fill='both', expand=True, padx=5)
        
        # Total PnL
        self.total_pnl_card = self._create_stat_card(cards_frame, "Total P&L", "$0.00", Colors.TEXT_SECONDARY)
        self.total_pnl_card.pack(side='left', fill='both', expand=True, padx=5)
    
    def _create_stat_card(self, parent, title, value, color):
        """Создать карточку статистики"""
        card = tk.Frame(parent, bg=Colors.BG_CARD,
                       highlightbackground=Colors.BORDER,
                       highlightthickness=1)
        
        tk.Label(card, text=title,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(pady=(10, 5))
        
        value_label = tk.Label(card, text=value,
                              font=('Arial', 14, 'bold'),
                              bg=Colors.BG_CARD,
                              fg=color)
        value_label.pack(pady=(0, 10))
        
        return card
    
    def update_stats(self, balance, today_pnl, total_pnl):
        """Обновить статистику"""
        # Balance
        balance_label = self.balance_card.winfo_children()[1]
        balance_label.config(text=f"${balance:,.2f}")
        
        # Today PnL
        today_label = self.today_pnl_card.winfo_children()[1]
        today_color = Colors.SUCCESS if today_pnl >= 0 else Colors.ERROR
        today_label.config(text=f"${today_pnl:+,.2f}", fg=today_color)
        
        # Total PnL
        total_label = self.total_pnl_card.winfo_children()[1]
        total_color = Colors.SUCCESS if total_pnl >= 0 else Colors.ERROR
        total_label.config(text=f"${total_pnl:+,.2f}", fg=total_color)


# ==================== CURRENT SETTINGS PANEL ====================
class CurrentSettingsPanel(tk.Frame):
    """Панель текущих активных настроек"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Colors.BG_DARK)
        
        tk.Label(self, text="Current Settings",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(pady=(0, 10))
        
        # Контейнер для настроек
        settings_frame = tk.Frame(self, bg=Colors.BG_CARD,
                                 highlightbackground=Colors.BORDER,
                                 highlightthickness=1)
        settings_frame.pack(fill='x')
        
        # Trading Mode
        self._create_setting_row(settings_frame, "Trading Mode:", "Strategy + AI")
        
        # Risk %
        self._create_setting_row(settings_frame, "Risk per Trade:", "1.0%")
        
        # MT5 Status
        self._create_setting_row(settings_frame, "MT5:", "Connected")
        
        # Telegram Status
        self._create_setting_row(settings_frame, "Telegram:", "Enabled")
        
        # AI Model
        self._create_setting_row(settings_frame, "AI Model:", "GPT-4o")
    
    def _create_setting_row(self, parent, label_text, value_text):
        """Создать строку с настройкой"""
        row = tk.Frame(parent, bg=Colors.BG_CARD)
        row.pack(fill='x', padx=10, pady=5)
        
        tk.Label(row, text=label_text,
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='left')
        
        value_label = tk.Label(row, text=value_text,
                              font=('Arial', 9, 'bold'),
                              bg=Colors.BG_CARD,
                              fg=Colors.TEXT_PRIMARY)
        value_label.pack(side='right')
        
        # Сохраняем ссылку на value_label для обновления
        setattr(self, f"_{label_text.replace(':', '').replace(' ', '_').lower()}_label", value_label)
    
    def update_settings(self, settings):
        """Обновить отображаемые настройки"""
        try:
            # Trading Mode
            mode_map = {'strategy': 'Strategy + AI', 'pure_ai': 'Pure AI'}
            if hasattr(self, '_trading_mode_label'):
                self._trading_mode_label.config(
                    text=mode_map.get(settings.get('trading_mode', 'strategy'), 'Unknown')
                )
            
            # Risk %
            if hasattr(self, '_risk_per_trade_label'):
                risk = settings.get('risk_percent', 1.0)
                self._risk_per_trade_label.config(text=f"{risk}%")
            
            # MT5 Status
            if hasattr(self, '_mt5_label'):
                mt5_connected = settings.get('mt5_connected', False)
                self._mt5_label.config(
                    text="Connected" if mt5_connected else "Disconnected",
                    fg=Colors.SUCCESS if mt5_connected else Colors.ERROR
                )
            
            # Telegram Status
            if hasattr(self, '_telegram_label'):
                tg_enabled = settings.get('telegram_enabled', False)
                self._telegram_label.config(
                    text="Enabled" if tg_enabled else "Disabled",
                    fg=Colors.SUCCESS if tg_enabled else Colors.TEXT_MUTED
                )
            
            # AI Model
            if hasattr(self, '_ai_model_label'):
                model = settings.get('ai_model', 'gpt-4o')
                self._ai_model_label.config(text=model.upper())
                
        except Exception as e:
            logger.error(f"[CurrentSettingsPanel] Ошибка обновления: {e}")


# ==================== AI ANALYST PANEL ====================
class AnalystPanel(tk.Frame):
    """Панель AI Analyst"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Colors.BG_DARK)
        
        # Заголовок
        header = tk.Frame(self, bg=Colors.BG_DARK)
        header.pack(fill='x', pady=(0, 10))
        
        tk.Label(header, text="AI Market Analyst",
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(side='left')
        
        self.status_label = tk.Label(header, text="● Idle",
                                     font=('Arial', 9),
                                     bg=Colors.BG_DARK,
                                     fg=Colors.TEXT_MUTED)
        self.status_label.pack(side='right')
        
        # Notebook для вкладок (только Analysis и Logs, без чата)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Dark.TNotebook', background=Colors.BG_DARK, borderwidth=0)
        style.configure('Dark.TNotebook.Tab', 
                       background=Colors.BG_CARD, 
                       foreground=Colors.TEXT_SECONDARY,
                       padding=[15, 8],
                       font=('Arial', 10))
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', Colors.BG_PANEL)],
                 foreground=[('selected', Colors.TEXT_PRIMARY)])
        
        self.notebook = ttk.Notebook(self, style='Dark.TNotebook')
        self.notebook.pack(fill='both', expand=True)
        
        # Вкладка: Logs (первая!)
        self.logs_tab = self._create_logs_tab()
        self.notebook.add(self.logs_tab, text='📝 System Logs')
        
        # Вкладка: Analysis Summary (второя)
        self.summary_tab = self._create_summary_tab()
        self.notebook.add(self.summary_tab, text='📊 Analysis')
    
    def _create_summary_tab(self):
        """Создать вкладку Analysis Summary"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_PANEL)
        
        # Скроллинг
        canvas = tk.Canvas(frame, bg=Colors.BG_PANEL, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=Colors.BG_PANEL)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Контент
        self.summary_text = tk.Text(scrollable, 
                                    font=('Consolas', 10),
                                    bg=Colors.BG_PANEL,
                                    fg=Colors.TEXT_PRIMARY,
                                    wrap='word',
                                    relief='flat',
                                    state='disabled',
                                    padx=15, pady=15)
        self.summary_text.pack(fill='both', expand=True)
        
        return frame
    
    def _create_logs_tab(self):
        """Создать вкладку Logs"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_PANEL)
        
        # Text widget для логов
        self.logs_text = tk.Text(frame,
                                font=('Consolas', 9),
                                bg=Colors.BG_PANEL,
                                fg=Colors.TEXT_PRIMARY,
                                wrap='word',
                                relief='flat',
                                state='disabled',
                                padx=10, pady=10)
        self.logs_text.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(frame, command=self.logs_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.logs_text.config(yscrollcommand=scrollbar.set)
        
        # Теги для цветов
        self.logs_text.tag_config('INFO', foreground=Colors.TEXT_PRIMARY)
        self.logs_text.tag_config('BUY', foreground=Colors.BUY, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('SELL', foreground=Colors.SELL, font=('Consolas', 9, 'bold'))
        self.logs_text.tag_config('ERROR', foreground=Colors.ERROR)
        self.logs_text.tag_config('SUCCESS', foreground=Colors.SUCCESS)
        self.logs_text.tag_config('WARNING', foreground=Colors.WARNING)
        
        return frame
    
    def add_log(self, message, level='INFO'):
        """Добавить лог с автоскроллом"""
        self.logs_text.config(state='normal')
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"
        
        # Определить тег по уровню или содержимому
        tag = 'INFO'
        if 'ERROR' in level.upper() or 'error' in message.lower():
            tag = 'ERROR'
        elif 'BUY' in message.upper():
            tag = 'BUY'
        elif 'SELL' in message.upper():
            tag = 'SELL'
        elif 'SUCCESS' in level.upper() or 'success' in message.lower():
            tag = 'SUCCESS'
        elif 'WARNING' in level.upper() or 'warning' in message.lower():
            tag = 'WARNING'
        
        self.logs_text.insert('end', log_line, tag)
        self.logs_text.see('end')  # Автоскролл
        self.logs_text.config(state='disabled')
    
    def update_summary(self, analysis_data):
        """Обновить Analysis Summary"""
        self.summary_text.config(state='normal')
        self.summary_text.delete('1.0', 'end')
        
        # Форматирование данных анализа
        summary = f"""
Last Analysis: {analysis_data.get('timestamp', 'N/A')}

Market Sentiment: {analysis_data.get('sentiment', 'N/A')}
Confidence: {analysis_data.get('confidence', 0)}%

Trend: {analysis_data.get('trend', 'N/A')}
Volatility: {analysis_data.get('volatility', 'N/A')}

Analysis Notes:
{analysis_data.get('notes', 'No notes available')}
        """
        
        self.summary_text.insert('1.0', summary.strip())
        self.summary_text.config(state='disabled')


# ==================== MAIN APP ====================
class BazaApp:
    """Главное приложение с новым UI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"BAZA Trading Terminal v{APP_VERSION}")
        
        # Максимальное окно с фиксированным размером
        self.root.state('zoomed')  # Максимизировать окно
        self.root.resizable(False, False)  # Запретить изменение размера
        self.root.configure(bg=Colors.BG_DARK)
        
        # Инициализация состояния
        self.app_state = AppState()
        self.stop_event = threading.Event()
        self.bot_running = False
        self.bot_thread = None
        
        # BotManager (singleton)
        self.bot_manager = BotManager()
        
        # Загрузка настроек
        self.load_settings()
        self.load_mt5_config()
        
        # Создание UI (сначала UI, потом MT5 чтобы header был доступен)
        self._create_ui()
        
        # Инициализация MT5
        self._init_mt5_manager()
        
        # Запуск мониторинга
        self._start_mt5_monitoring()
        
        # Установка callback для логов
        app_logger.set_gui_callback(self.add_log)
        
        # Системная диагностика
        self._run_diagnostics()
        
        # Первичное обновление панели настроек
        if hasattr(self, 'settings_info_panel'):
            settings = self.bot_manager.get_current_settings()
            self.settings_info_panel.update_settings(settings)
        
        app_logger.info("[BAZA] Trading Terminal started")
    
    def _create_ui(self):
        """Создать UI компоненты"""
        # Header
        self.header = HeaderPanel(self.root, self.app_state)
        self.header.pack(fill='x')
        
        # Separator
        tk.Frame(self.root, bg=Colors.BORDER, height=1).pack(fill='x')
        
        # Main Content Area
        main_container = tk.Frame(self.root, bg=Colors.BG_DARK)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Left Panel (Mode + Control + Stats)
        left_panel = tk.Frame(main_container, bg=Colors.BG_DARK, width=350)
        left_panel.pack(side='left', fill='y', padx=(0, 20))
        left_panel.pack_propagate(False)
        
        # Mode Selector
        self.mode_selector = ModeSelector(left_panel, self._on_mode_change)
        self.mode_selector.pack(fill='x', pady=(0, 20))
        
        # Control Panel
        self.control_panel = ControlPanel(left_panel, self._start_bot, self._stop_bot)
        self.control_panel.pack(fill='x', pady=(0, 20))
        
        # Stats Panel
        self.stats_panel = StatsPanel(left_panel, self.app_state)
        self.stats_panel.pack(fill='x', pady=(0, 20))
        
        # Current Settings Panel
        self.settings_info_panel = CurrentSettingsPanel(left_panel)
        self.settings_info_panel.pack(fill='x', pady=(0, 20))
        
        # Settings Button
        tk.Button(left_panel, text="⚙ Settings",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 cursor='hand2',
                 command=self.show_settings_dialog).pack(fill='x', pady=(0, 10))
        
        # MT5 Button
        tk.Button(left_panel, text="🔗 MT5 Settings",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 cursor='hand2',
                 command=self.show_mt5_dialog).pack(fill='x', pady=(0, 10))
        
        # Update Button
        tk.Button(left_panel, text="🔄 Проверить обновления",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 cursor='hand2',
                 command=self.check_for_updates).pack(fill='x', pady=(0, 10))
        
        # Test GPT Connection Button
        tk.Button(left_panel, text="🧪 Test GPT",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 cursor='hand2',
                 command=self.test_gpt_connection).pack(fill='x')
        
        # Right Panel (AI Analyst)
        self.analyst_panel = AnalystPanel(main_container)
        self.analyst_panel.pack(side='right', fill='both', expand=True)
    
    def _on_mode_change(self, mode):
        """Обработка смены режима"""
        app_logger.info(f"[MODE] Switched to: {mode}")
        
        # Обновить режим в BotManager
        if mode == 'strategy':
            self.bot_manager.trading_mode = 'strategy'
            app_logger.info("[MODE] Strategy + AI enabled")
        else:
            self.bot_manager.trading_mode = 'pure_ai'
            app_logger.info("[MODE] Pure AI Trading enabled")
        
        # Обновить статус в UI
        self.mode_selector.update_status(self.bot_running)
        
        # Обновить панель настроек
        if hasattr(self, 'settings_info_panel'):
            settings = self.bot_manager.get_current_settings()
            self.settings_info_panel.update_settings(settings)
    
    def _start_bot(self):
        """Запуск бота"""
        if self.bot_running:
            app_logger.warning("[BOT] Already running")
            return
        
        try:
            app_logger.info("[BOT] Starting...")
            
            # Проверить MT5
            if not self.app_state.mt5_manager or not self.app_state.mt5_manager.is_connected():
                messagebox.showerror("Error", "MT5 not connected. Please check MT5 connection.")
                app_logger.error("[BOT] Cannot start - MT5 not connected")
                return
            
            # Обновить состояние
            self.bot_running = True
            self.control_panel.set_bot_running(True)
            self.mode_selector.update_status(False)
            
            # Уведомить BotManager о старте (для Telegram уведомлений)
            self.bot_manager.start(
                mode='live',
                trading_mode=self.bot_manager.trading_mode
            )
            
            # Запустить бота в отдельном потоке
            self.stop_event.clear()
            self.bot_thread = threading.Thread(
                target=self._run_trading_loop,
                daemon=True,
                name="TradingLoop"
            )
            self.bot_thread.start()
            
            app_logger.info(f"[BOT] Started in '{self.bot_manager.trading_mode}' mode")
            
        except Exception as e:
            app_logger.error(f"[BOT] Failed to start: {e}")
            messagebox.showerror("Error", f"Failed to start bot: {e}")
            self.bot_running = False
            self.control_panel.set_bot_running(False)
    
    def _stop_bot(self):
        """Остановка бота"""
        if not self.bot_running:
            app_logger.warning("[BOT] Not running")
            return
        
        try:
            app_logger.info("[BOT] Stopping...")
            
            # Сигнал остановки
            self.stop_event.set()
            self.bot_running = False
            
            # Обновить UI
            self.control_panel.set_bot_running(False)
            self.mode_selector.update_status(False)
            
            # Дождаться завершения потока
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=3)
            
            # Остановить AI Scheduler если запущен
            if AI_ANALYSIS_AVAILABLE:
                try:
                    scheduler = get_scheduler()
                    if scheduler:
                        scheduler.stop()
                        app_logger.info("[BOT] AI Scheduler stopped")
                except Exception as e:
                    app_logger.error(f"[BOT] Failed to stop AI Scheduler: {e}")
            
            # Уведомить BotManager об остановке (для Telegram уведомлений)
            self.bot_manager.stop()
            
            app_logger.info("[BOT] Stopped")
            
        except Exception as e:
            app_logger.error(f"[BOT] Error during stop: {e}")
    
    def _run_trading_loop(self):
        """Основной торговый цикл"""
        try:
            app_logger.info("[LOOP] Trading loop started")
            
            # Проверить что MT5 подключён
            if not self.app_state.mt5_manager or not self.app_state.mt5_manager.is_connected():
                app_logger.error("[LOOP] MT5 not connected! Cannot start trading.")
                self.root.after(0, lambda: messagebox.showerror(
                    "MT5 Error",
                    "MT5 not connected!\n\nPlease connect MT5 first:\n1. Click Settings\n2. Open MT5 Connection\n3. Test and Save"
                ))
                self._stop_bot()
                return
            
            # Создать LiveTrader с существующим MT5Manager
            trader = LiveTrader(
                config_dir='config',
                enable_trading=True,
                enable_gpt=(self.bot_manager.trading_mode == 'pure_ai')
            )
            
            # Передать MT5Manager в LiveTrader
            trader.mt5 = self.app_state.mt5_manager.mt5
            trader.mt5_manager = self.app_state.mt5_manager
            
            app_logger.info("[LOOP] LiveTrader initialized with connected MT5")
            
            # Запустить AI Scheduler для pure_ai режима
            if self.bot_manager.trading_mode == 'pure_ai' and AI_ANALYSIS_AVAILABLE:
                try:
                    scheduler = init_scheduler()
                    scheduler.start()
                    app_logger.info("[LOOP] AI Scheduler started for pure_ai mode")
                except Exception as e:
                    app_logger.error(f"[LOOP] Failed to start AI Scheduler: {e}")
            
            # Запустить мониторинг
            while not self.stop_event.is_set():
                try:
                    # Обновить статистику из MT5
                    self._update_stats_from_mt5()
                    
                    # Проверить сигналы (в зависимости от режима)
                    if self.bot_manager.trading_mode == 'strategy':
                        # Strategy + AI mode - стратегии с AI фильтрацией
                        app_logger.debug("[LOOP] Running strategy mode")
                        trader.check_signals()
                    else:
                        # Pure AI mode
                        app_logger.debug("[LOOP] Running pure AI mode")
                        trader.check_signals()
                    
                    # Обновить открытые позиции
                    self._update_positions()
                    
                    # Пауза перед следующей итерацией (30 секунд)
                    self.stop_event.wait(30)
                    
                except Exception as e:
                    app_logger.error(f"[LOOP] Error in trading loop: {e}")
                    self.stop_event.wait(10)
            
            app_logger.info("[LOOP] Trading loop stopped")
            
        except Exception as e:
            app_logger.error(f"[LOOP] Fatal error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Trading loop crashed: {e}"))
            self.root.after(0, self._stop_bot)
    
    def _update_stats_from_mt5(self):
        """Обновить статистику из MT5"""
        try:
            if self.app_state.mt5_manager and self.app_state.mt5_manager.is_connected():
                account_info = self.app_state.mt5_manager.get_account_info()
                if account_info:
                    balance = float(account_info.get('balance', 0))
                    equity = float(account_info.get('equity', 0))
                    
                    # Загрузить историю для расчета P&L
                    stats_file = Path('data/bot_stats.json')
                    if stats_file.exists():
                        with open(stats_file, 'r') as f:
                            stats = json.load(f)
                            initial_balance = stats.get('initial_balance', balance)
                            total_pnl = balance - initial_balance
                    else:
                        total_pnl = 0
                    
                    # Today PnL рассчитывается из истории сделок
                    today_pnl = 0
                    
                    # Обновить UI
                    self.root.after(0, lambda: self.stats_panel.update_stats(balance, today_pnl, total_pnl))
        except Exception as e:
            app_logger.error(f"[STATS] Error updating stats: {e}")
    
    def _update_positions(self):
        """Обновить открытые позиции"""
        try:
            if self.app_state.mt5_manager and self.app_state.mt5_manager.is_connected():
                positions = self.app_state.mt5_manager.get_open_positions()
                app_logger.debug(f"[POSITIONS] Open: {len(positions)}")
        except Exception as e:
            app_logger.error(f"[POSITIONS] Error: {e}")
    
    def add_log(self, message, level='INFO'):
        """Добавить лог в UI"""
        try:
            if hasattr(self, 'analyst_panel'):
                self.root.after(0, lambda: self.analyst_panel.add_log(message, level))
        except:
            pass
    
    def load_settings(self):
        """Загрузка настроек"""
        pass
    
    def load_mt5_config(self):
        """Загрузка конфигурации MT5"""
        pass
    
    def _init_mt5_manager(self):
        """Инициализация MT5"""
        try:
            # Загрузить конфиг MT5
            config_path = Path('config') / 'mt5.yaml'
            if not config_path.exists():
                app_logger.warning("[MT5] Config file not found")
                self.header.update_mt5_status(False)
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                mt5_config = yaml.safe_load(f)
            
            connection_config = mt5_config.get('mt5', {}).get('connection', {})
            login = connection_config.get('login')
            password = connection_config.get('password')
            server = connection_config.get('server')
            path = connection_config.get('path')
            
            if not all([login, password, server]):
                app_logger.warning("[MT5] Missing connection credentials in config")
                self.header.update_mt5_status(False)
                return
            
            # Создать MT5Manager
            self.app_state.mt5_manager = MT5Manager()
            
            # Инициализировать
            if not self.app_state.mt5_manager.initialize(path):
                app_logger.error("[MT5] Failed to initialize - is MetaTrader 5 running?")
                self.header.update_mt5_status(False)
                messagebox.showwarning(
                    "MT5 Not Running",
                    "MetaTrader 5 terminal is not running!\n\n"
                    "Please:\n"
                    "1. Open MetaTrader 5\n"
                    "2. Restart the bot\n\n"
                    "Or use Settings → MT5 Connection to reconnect."
                )
                return
            
            # Подключиться к счету
            success, message = self.app_state.mt5_manager.connect(login, password, server)
            
            if success:
                self.header.update_mt5_status(True)
                app_logger.info(f"[MT5] {message}")
                
                # Связать BotManager с MT5
                self.bot_manager.set_mt5_manager(self.app_state.mt5_manager)
                
                # Обновить статистику
                self.bot_manager._update_stats_from_mt5()
            else:
                self.header.update_mt5_status(False)
                app_logger.error(f"[MT5] Connection failed: {message}")
                messagebox.showerror(
                    "MT5 Connection Failed",
                    f"Failed to connect to MT5 account!\n\n"
                    f"Error: {message}\n\n"
                    f"Please check:\n"
                    f"• Login: {login}\n"
                    f"• Server: {server}\n"
                    f"• Password is correct\n"
                    f"• MetaTrader 5 is running\n\n"
                    f"Use Settings → MT5 Connection to update."
                )
                
        except Exception as e:
            app_logger.error(f"[MT5] Error: {e}")
            self.header.update_mt5_status(False)
    
    def _start_mt5_monitoring(self):
        """Запуск мониторинга MT5"""
        def monitor():
            while True:
                try:
                    if self.app_state.mt5_manager:
                        connected = self.app_state.mt5_manager.is_connected()
                        self.root.after(0, lambda: self.header.update_mt5_status(connected))
                        
                        if connected:
                            # Обновить цену XAUUSD
                            xauusd_price = self.app_state.mt5_manager.get_symbol_price('XAUUSD')
                            if xauusd_price > 0:
                                self.root.after(0, lambda p=xauusd_price: self.header.update_price(p))
                            
                            # Обновить статистику
                            account_info = self.app_state.mt5_manager.get_account_info() or {}
                            balance = float(account_info.get('balance', 0))
                            # TODO: Calculate today_pnl and total_pnl
                            self.root.after(0, lambda b=balance: self.stats_panel.update_stats(b, 0, 0))
                    
                    threading.Event().wait(2)
                except Exception as e:
                    app_logger.error(f"[Monitor] Error: {e}")
                    threading.Event().wait(5)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _run_diagnostics(self):
        """Запуск системной диагностики при старте."""
        try:
            app_logger.info("[Diagnostics] Running system checks...")
            
            # Запустить диагностику
            results = SystemDiagnostics.check_all()
            
            # Вывести отчёт в лог
            report = SystemDiagnostics.get_diagnostic_report()
            for line in report.split('\n'):
                app_logger.info(f"[Diagnostics] {line}")
            
            # Если есть критические проблемы - показать предупреждение
            if not results["all_ok"]:
                issues = []
                
                if not results["openai_api"]["status"]:
                    issues.append(f"• {results['openai_api']['message']}")
                    if "solution" in results["openai_api"]:
                        issues.append(f"  → {results['openai_api']['solution']}")
                
                if not results["config_files"]["status"]:
                    issues.append(f"• {results['config_files']['message']}")
                
                if issues:
                    warning_text = "⚠️ System Diagnostics\n\nSome issues detected:\n\n" + "\n".join(issues)
                    warning_text += "\n\nBot may not function correctly.\nPlease check Settings."
                    
                    messagebox.showwarning("System Diagnostics", warning_text)
                    app_logger.warning("[Diagnostics] Issues detected - user notified")
            else:
                app_logger.info("[Diagnostics] ✅ All systems operational")
                
        except Exception as e:
            app_logger.error(f"[Diagnostics] Failed to run diagnostics: {e}")
    
    def show_settings_dialog(self):
        """Показать диалог настроек"""
        try:
            SettingsDialog(self.root, on_save_callback=self._on_settings_saved)
        except Exception as e:
            app_logger.error(f"[SETTINGS] Error: {e}")
            messagebox.showerror("Error", f"Failed to open settings: {e}")
    
    def _on_settings_saved(self):
        """Callback после сохранения настроек"""
        try:
            app_logger.info("[SETTINGS] Settings updated, applying changes...")
            
            # Применить настройки без перезапуска
            if hasattr(self, 'bot_manager') and self.bot_manager:
                success = self.bot_manager.reload_config()
                if success:
                    # Обновить панель Current Settings
                    settings = self.bot_manager.get_current_settings()
                    if hasattr(self, 'settings_info_panel'):
                        self.settings_info_panel.update_settings(settings)
                    
                    messagebox.showinfo("Success", "✅ Настройки применены!\n\nИзменения вступили в силу без перезапуска.")
                    app_logger.info("[SETTINGS] ✅ Settings reloaded successfully")
                else:
                    messagebox.showwarning("Warning", "⚠️ Настройки сохранены, но не все изменения применены.\n\nРекомендуется перезапустить бота.")
            else:
                messagebox.showinfo("Saved", "Настройки сохранены. Изменения вступят в силу при следующем запуске.")
                
        except Exception as e:
            app_logger.error(f"[SETTINGS] Error applying settings: {e}")
            messagebox.showerror("Error", f"Ошибка применения настроек: {e}")
    
    def show_mt5_dialog(self):
        """Показать диалог MT5"""
        try:
            MT5Dialog(self.root, self.app_state.mt5_manager, on_save_callback=self._on_mt5_saved)
        except Exception as e:
            app_logger.error(f"[MT5] Error: {e}")
            messagebox.showerror("Error", f"Failed to open MT5 settings: {e}")
    
    def _on_mt5_saved(self):
        """Callback после сохранения MT5 настроек"""
        app_logger.info("[MT5] Settings updated, reconnection recommended")
    
    def check_for_updates(self):
        """Проверить наличие обновлений"""
        app_logger.info(f"[UPDATE] Checking for updates (current version: {APP_VERSION})")
        
        # Запускаем проверку в отдельном потоке чтобы не блокировать UI
        def check_thread():
            try:
                checker = UpdateChecker(APP_VERSION, VERSION_CHECK_URL)
                update_info = checker.check_for_updates()
                
                if update_info:
                    # Обновление доступно - показываем окно обновления в главном потоке
                    self.root.after(0, lambda: self._show_update_window(update_info))
                else:
                    # Обновлений нет
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Обновления",
                        f"У вас установлена последняя версия!\n\n"
                        f"Версия: {APP_VERSION}",
                        parent=self.root
                    ))
                    
            except ConnectionError as e:
                app_logger.error(f"[UPDATE] Connection error: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Ошибка подключения",
                    f"Не удалось проверить обновления:\n{e}\n\n"
                    f"Проверьте интернет-соединение.",
                    parent=self.root
                ))
            except Exception as e:
                app_logger.error(f"[UPDATE] Unexpected error: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Ошибка",
                    f"Произошла ошибка при проверке обновлений:\n{e}",
                    parent=self.root
                ))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _show_update_window(self, update_info):
        """Показать окно обновления"""
        try:
            UpdateWindow(self.root, APP_VERSION, update_info)
        except Exception as e:
            app_logger.error(f"[UPDATE] Failed to show update window: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть окно обновления: {e}")
    
    def test_gpt_connection(self):
        """Тестовая отправка в GPT для проверки подключения"""
        try:
            app_logger.info("[TEST-GPT] Starting connection test...")
            
            # Проверяем API ключ
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                messagebox.showerror(
                    "Test Failed",
                    "❌ OpenAI API key not found!\n\n"
                    "Please configure API key in Settings."
                )
                app_logger.error("[TEST-GPT] API key not found")
                return
            
            # Показываем что тест начался
            app_logger.info(f"[TEST-GPT] API Key: {api_key[:15]}...{api_key[-4:]}")
            
            # Создаём минимальный тест-запрос в отдельном потоке
            def run_test():
                try:
                    from openai import OpenAI
                    
                    app_logger.info("[TEST-GPT] Creating OpenAI client...")
                    client = OpenAI(api_key=api_key)
                    
                    app_logger.info("[TEST-GPT] Sending test message...")
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",  # Используем дешёвую модель для теста
                        messages=[
                            {"role": "user", "content": "Say 'OK' if you can read this"}
                        ],
                        max_tokens=10
                    )
                    
                    result = response.choices[0].message.content.strip()
                    app_logger.info(f"[TEST-GPT] ✅ Response received: {result}")
                    
                    # Показываем успех в главном потоке
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Test Successful",
                        f"✅ GPT Connection Works!\n\n"
                        f"Response: {result}\n"
                        f"Model: {response.model}\n"
                        f"API Key: {api_key[:15]}...{api_key[-4:]}"
                    ))
                    
                except Exception as e:
                    app_logger.error(f"[TEST-GPT] ❌ Test failed: {e}")
                    self.root.after(0, lambda: messagebox.showerror(
                        "Test Failed",
                        f"❌ GPT Connection Failed!\n\n"
                        f"Error: {str(e)}\n\n"
                        f"Check:\n"
                        f"• API key is valid\n"
                        f"• Account has credits\n"
                        f"• Internet connection"
                    ))
            
            # Запускаем тест в отдельном потоке
            threading.Thread(target=run_test, daemon=True).start()
            
            # Показываем что тест запущен
            messagebox.showinfo(
                "Testing GPT",
                "🧪 Testing GPT connection...\n\n"
                "Please wait, this may take a few seconds.\n"
                "Check System Logs for details."
            )
            
        except Exception as e:
            app_logger.error(f"[TEST-GPT] Failed to start test: {e}")
            messagebox.showerror("Error", f"Failed to start test: {e}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Entry point"""
    app = BazaApp()
    app.run()


if __name__ == '__main__':
    main()

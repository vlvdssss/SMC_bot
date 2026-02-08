#!/usr/bin/env python3
"""
BAZA Trading Bot - Modern Trading Terminal UI
Минималистичный профессиональный интерфейс в стиле TradingView/MT5
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
from datetime import datetime
from pathlib import Path
import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.app_state import AppState
from src.core.mt5_manager import MT5Manager
from src.core.bot_manager import bot_manager, BotManager, BotStatus
from src.core.diagnostics import SystemDiagnostics
from src.live.live_trader import LiveTrader
from src.gui.settings_dialog import SettingsDialog
from src.gui.mt5_dialog import MT5Dialog
from src.core.logger import logger as app_logger
from src.core.market_data_updater import MarketDataUpdater

try:
    from src.ai.analyst_scheduler import get_scheduler, init_scheduler
    from src.ai.signal_manager import AISignalManager
    AI_ANALYSIS_AVAILABLE = True
    app_logger.info("✅ AI modules loaded successfully")
except Exception as e:
    # Ловим ВСЕ ошибки, не только ImportError
    # Могут быть проблемы с кодировкой, инициализацией и т.д.
    import traceback
    app_logger.error(f"❌ AI modules failed to load: {e}")
    traceback.print_exc()
    AI_ANALYSIS_AVAILABLE = False


# ==================== DATA PATH HELPER ====================
def get_data_path(filename):
    """Получить абсолютный путь к файлу в data директории (работает в EXE и python)"""
    if getattr(sys, 'frozen', False):
        # Если запущен как EXE, используем директорию где находится EXE
        base_path = Path(sys.executable).parent
    else:
        # Если запущен как python скрипт, используем корневую директорию проекта
        base_path = Path(__file__).parent.parent.parent
    return base_path / 'data' / filename

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
    INFO = '#58a6ff'              # Информация (синий)
    
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
        balance_label.config(text=f"${balance:.2f}")
        
        # Today PnL
        today_label = self.today_pnl_card.winfo_children()[1]
        today_color = Colors.SUCCESS if today_pnl >= 0 else Colors.ERROR
        today_label.config(text=f"${today_pnl:+.2f}", fg=today_color)
        
        # Total PnL
        total_label = self.total_pnl_card.winfo_children()[1]
        total_color = Colors.SUCCESS if total_pnl >= 0 else Colors.ERROR
        total_label.config(text=f"${total_pnl:+.2f}", fg=total_color)


# ==================== CURRENT SETTINGS PANEL ====================
class CurrentSettingsPanel(tk.Frame):
    """Панель текущих активных настроек"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Colors.BG_DARK)
        
        tk.Label(self, text="Current Settings",
                font=('Arial', 10, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(pady=(0, 8))
        
        # Контейнер для настроек (компактный)
        settings_frame = tk.Frame(self, bg=Colors.BG_CARD,
                                 highlightbackground=Colors.BORDER,
                                 highlightthickness=1)
        settings_frame.pack(fill='x')
        
        # Risk %
        self._create_setting_row(settings_frame, "Risk:", "1.0%")
        
        # MT5 Status
        self._create_setting_row(settings_frame, "MT5:", "Connected")
        
        # AI Model
        self._create_setting_row(settings_frame, "AI:", "GPT-4o")
    
    def _create_setting_row(self, parent, label_text, value_text):
        """Создать строку с настройкой"""
        row = tk.Frame(parent, bg=Colors.BG_CARD)
        row.pack(fill='x', padx=8, pady=3)
        
        tk.Label(row, text=label_text,
                font=('Arial', 8),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='left')
        
        value_label = tk.Label(row, text=value_text,
                              font=('Arial', 8, 'bold'),
                              bg=Colors.BG_CARD,
                              fg=Colors.TEXT_PRIMARY)
        value_label.pack(side='right')
        
        # Сохраняем ссылку на value_label для обновления
        setattr(self, f"_{label_text.replace(':', '').replace(' ', '_').lower()}_label", value_label)
    
    def update_settings(self, settings):
        """Обновить отображаемые настройки"""
        try:
            # Risk %
            if hasattr(self, '_risk_label'):
                risk = settings.get('risk_percent', 1.0)
                self._risk_label.config(text=f"{risk}%")
            
            # MT5 Status
            if hasattr(self, '_mt5_label'):
                mt5_connected = settings.get('mt5_connected', False)
                self._mt5_label.config(
                    text="OK" if mt5_connected else "Off",
                    fg=Colors.SUCCESS if mt5_connected else Colors.ERROR
                )
            
            # AI Model
            if hasattr(self, '_ai_label'):
                model = settings.get('ai_model', 'gpt-4o')
                self._ai_label.config(text=model.upper())
                
        except Exception as e:
            app_logger.error(f"[CurrentSettingsPanel] Ошибка обновления: {e}")


# ==================== AI ANALYST PANEL ====================
class AnalystPanel(tk.Frame):
    """Панель AI Analyst"""
    
    def __init__(self, parent, bot_manager=None):
        super().__init__(parent, bg=Colors.BG_DARK)
        self.bot_manager = bot_manager
        
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
        """Создать вкладку AI Analysis & Signals с двухколоночным layout"""
        frame = tk.Frame(self.notebook, bg=Colors.BG_PANEL)
        
        # Верхняя панель с кнопкой обновления
        top_panel = tk.Frame(frame, bg=Colors.BG_PANEL)
        top_panel.pack(fill='x', padx=15, pady=10)
        
        tk.Label(top_panel, text="AI ANALYSIS & SIGNALS",
                font=('Arial', 14, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.ACCENT).pack(side='left')
        
        refresh_btn = tk.Button(top_panel, text="🔄 Refresh", 
                                font=('Arial', 10),
                                bg=Colors.BG_CARD,
                                fg=Colors.TEXT_PRIMARY,
                                activebackground=Colors.BG_HOVER,
                                bd=0,
                                padx=15, pady=5,
                                cursor='hand2',
                                command=self.refresh_analysis)
        refresh_btn.pack(side='right')
        
        # ===== ДВУХКОЛОНОЧНЫЙ LAYOUT =====
        content_frame = tk.Frame(frame, bg=Colors.BG_PANEL)
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # ЛЕВАЯ КОЛОНКА (60%) - Сигналы и История
        left_column = tk.Frame(content_frame, bg=Colors.BG_PANEL)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Скроллинг для левой колонки
        left_canvas = tk.Canvas(left_column, bg=Colors.BG_PANEL, highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_column, orient="vertical", command=left_canvas.yview)
        left_scrollable = tk.Frame(left_canvas, bg=Colors.BG_PANEL)
        
        left_scrollable.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=left_scrollable, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        
        # Сохраняем для обновления
        self.summary_left_scrollable = left_scrollable
        
        # ПРАВАЯ КОЛОНКА (40%) - Информационная панель
        right_column = tk.Frame(content_frame, bg=Colors.BG_PANEL, width=400)
        right_column.pack(side='right', fill='both', padx=(10, 0))
        right_column.pack_propagate(False)
        
        # Скроллинг для правой колонки
        right_canvas = tk.Canvas(right_column, bg=Colors.BG_PANEL, highlightthickness=0)
        right_scrollbar = tk.Scrollbar(right_column, orient="vertical", command=right_canvas.yview)
        right_scrollable = tk.Frame(right_canvas, bg=Colors.BG_PANEL)
        
        right_scrollable.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.create_window((0, 0), window=right_scrollable, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        right_canvas.pack(side="left", fill="both", expand=True)
        right_scrollbar.pack(side="right", fill="y")
        
        # Сохраняем для обновления
        self.summary_right_scrollable = right_scrollable
        
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
    
    def refresh_analysis(self):
        """Обновить AI Analysis & Signals с новым UI"""
        if not AI_ANALYSIS_AVAILABLE:
            # Показать ошибку в левой колонке
            for widget in self.summary_left_scrollable.winfo_children():
                widget.destroy()
            
            error_label = tk.Label(self.summary_left_scrollable,
                                  text="⚠️ AI Analysis not available\n\nInstall required packages:\npip install openai pyyaml",
                                  font=('Arial', 11),
                                  bg=Colors.BG_PANEL,
                                  fg=Colors.ERROR,
                                  justify='center')
            error_label.pack(pady=50)
            return
        
        try:
            # Получить данные
            signal_manager = AISignalManager()
            
            # Очистить обе колонки
            for widget in self.summary_left_scrollable.winfo_children():
                widget.destroy()
            for widget in self.summary_right_scrollable.winfo_children():
                widget.destroy()
            
            # ===== ЛЕВАЯ КОЛОНКА: ACTIVE SIGNALS =====
            self._create_active_signals_section(signal_manager)
            
            # ===== ЛЕВАЯ КОЛОНКА: HISTORY =====
            self._create_history_section(signal_manager)
            
            # ===== ПРАВАЯ КОЛОНКА: INFO PANELS =====
            self._create_info_panels(signal_manager)
            
        except Exception as e:
            for widget in self.summary_left_scrollable.winfo_children():
                widget.destroy()
            
            error_label = tk.Label(self.summary_left_scrollable,
                                  text=f"❌ Error loading analysis:\n{str(e)}",
                                  font=('Arial', 11),
                                  bg=Colors.BG_PANEL,
                                  fg=Colors.ERROR,
                                  justify='left')
            error_label.pack(pady=20, padx=15)
    
    def _create_active_signals_section(self, signal_manager):
        """Создать секцию активных сигналов"""
        # Заголовок секции
        header_frame = tk.Frame(self.summary_left_scrollable, bg=Colors.BG_PANEL)
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Показываем pending/triggered сигналы + открытые позиции
        active_signals = [s for s in signal_manager.active_signals if s.status in ["pending", "triggered"]]
        
        # Добавляем открытые позиции как "сигналы"
        open_positions = []
        if (hasattr(self, 'bot_manager') and self.bot_manager and 
            hasattr(self.bot_manager, 'live_trader') and self.bot_manager.live_trader):
            try:
                tracked = self.bot_manager.live_trader.tracked_positions
                for ticket, pos_info in tracked.items():
                    if not pos_info.get('notification_sent', False):
                        open_positions.append(pos_info)
            except Exception as e:
                app_logger.debug(f"[GUI] Could not get tracked positions: {e}")
        
        total_active = len(active_signals) + len(open_positions)
        
        tk.Label(header_frame,
                text=f"ACTIVE SIGNALS ({total_active})",
                font=('Arial', 13, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.ACCENT).pack(side='left')
        
        # Сначала показываем открытые позиции
        if open_positions:
            for pos in open_positions:
                self._create_position_card(self.summary_left_scrollable, pos)
        
        # Потом pending/triggered сигналы
        if active_signals:
            for signal in active_signals:
                self._create_signal_card(self.summary_left_scrollable, signal)
        
        # Placeholder если ничего нет
        if not active_signals and not open_positions:
            placeholder = tk.Frame(self.summary_left_scrollable, bg=Colors.BG_CARD,
                                  highlightbackground=Colors.BORDER, highlightthickness=1)
            placeholder.pack(fill='x', pady=(0, 15))
            
            tk.Label(placeholder,
                    text="No active signals",
                    font=('Arial', 11),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_MUTED).pack(pady=30)
    
    def _create_position_card(self, parent, pos_info):
        """Создать карточку открытой позиции"""
        card = tk.Frame(parent, bg=Colors.BG_CARD,
                       highlightbackground="#FFD700", highlightthickness=2)  # Gold border
        card.pack(fill='x', pady=(0, 12))
        
        card_content = tk.Frame(card, bg=Colors.BG_CARD)
        card_content.pack(fill='both', padx=15, pady=12)
        
        # Header: OPEN POSITION badge + Symbol
        top_row = tk.Frame(card_content, bg=Colors.BG_CARD)
        top_row.pack(fill='x', pady=(0, 10))
        
        # Direction badge
        type_color = Colors.BUY if pos_info['direction'] == 'BUY' else Colors.SELL
        tk.Label(top_row,
                text=f" {pos_info['direction']} ",
                font=('Arial', 12, 'bold'),
                bg=type_color,
                fg='white',
                padx=10, pady=2).pack(side='left', padx=(0, 8))
        
        tk.Label(top_row,
                text=pos_info['symbol'],
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_CARD,
                fg='white').pack(side='left')
        
        # Ticket number
        tk.Label(top_row,
                text=f"#{pos_info['ticket']}",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(side='right')
        
        # Entry price + current P&L
        info_row = tk.Frame(card_content, bg=Colors.BG_CARD)
        info_row.pack(fill='x', pady=(0, 8))
        
        tk.Label(info_row,
                text=f"Entry: {pos_info['entry_price']:.5f}",
                font=('Consolas', 10),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY).pack(side='left')
        
        # Status indicator (золотой цвет для открытых)
        tk.Label(card_content,
                text="● OPEN POSITION",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg="#FFD700").pack(anchor='w')
    
    def _create_signal_card(self, parent, signal):
        """Создать карточку сигнала"""
        # Карточка с темным фоном и рамкой
        card = tk.Frame(parent, bg=Colors.BG_CARD,
                       highlightbackground=Colors.BORDER, highlightthickness=1)
        card.pack(fill='x', pady=(0, 12))
        
        # Внутренние отступы
        card_content = tk.Frame(card, bg=Colors.BG_CARD)
        card_content.pack(fill='both', padx=15, pady=12)
        
        # Верхняя строка: BUY/SELL + Symbol
        top_row = tk.Frame(card_content, bg=Colors.BG_CARD)
        top_row.pack(fill='x', pady=(0, 10))
        
        # BUY/SELL badge
        type_color = Colors.BUY if signal.type.upper() == "BUY" else Colors.SELL
        type_label = tk.Label(top_row,
                             text=f" {signal.type.upper()} ",
                             font=('Arial', 12, 'bold'),
                             bg=type_color,
                             fg='white',
                             padx=10, pady=2)
        type_label.pack(side='left', padx=(0, 10))
        
        # Symbol
        tk.Label(top_row,
                text=signal.symbol,
                font=('Arial', 12, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY).pack(side='left')
        
        # Priority badge (справа)
        priority_colors = {
            0: (Colors.TEXT_MUTED, "LOW"),
            1: (Colors.WARNING, "MID"),
            2: (Colors.ERROR, "HIGH")
        }
        priority_color, priority_text = priority_colors.get(signal.priority, (Colors.TEXT_MUTED, "LOW"))
        
        priority_label = tk.Label(top_row,
                                 text=f" {priority_text} ",
                                 font=('Arial', 9, 'bold'),
                                 bg=Colors.BG_PANEL,
                                 fg=priority_color,
                                 padx=8, pady=2)
        priority_label.pack(side='right')
        
        # Разделитель
        tk.Frame(card_content, bg=Colors.BORDER, height=1).pack(fill='x', pady=(0, 10))
        
        # Prices Grid
        prices_frame = tk.Frame(card_content, bg=Colors.BG_CARD)
        prices_frame.pack(fill='x', pady=(0, 10))
        
        # Entry
        entry_frame = tk.Frame(prices_frame, bg=Colors.BG_CARD)
        entry_frame.pack(side='left', expand=True, fill='x')
        tk.Label(entry_frame,
                text="ENTRY",
                font=('Arial', 8),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(anchor='w')
        tk.Label(entry_frame,
                text=f"{signal.entry_price:.5f}",
                font=('Consolas', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w')
        
        # SL
        sl_frame = tk.Frame(prices_frame, bg=Colors.BG_CARD)
        sl_frame.pack(side='left', expand=True, fill='x')
        tk.Label(sl_frame,
                text="STOP LOSS",
                font=('Arial', 8),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(anchor='w')
        tk.Label(sl_frame,
                text=f"{signal.stop_loss:.5f}",
                font=('Consolas', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ERROR).pack(anchor='w')
        
        # TP
        tp_frame = tk.Frame(prices_frame, bg=Colors.BG_CARD)
        tp_frame.pack(side='left', expand=True, fill='x')
        tk.Label(tp_frame,
                text="TAKE PROFIT",
                font=('Arial', 8),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MUTED).pack(anchor='w')
        tk.Label(tp_frame,
                text=f"{signal.take_profit:.5f}",
                font=('Consolas', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.SUCCESS).pack(anchor='w')
        
        # Confidence Progress Bar
        confidence_frame = tk.Frame(card_content, bg=Colors.BG_CARD)
        confidence_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(confidence_frame,
                text=f"Confidence: {signal.confidence}%",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(0, 3))
        
        # Progress bar canvas
        progress_canvas = tk.Canvas(confidence_frame, height=6, bg=Colors.BG_PANEL,
                                   highlightthickness=0)
        progress_canvas.pack(fill='x')
        
        # Background bar
        progress_canvas.create_rectangle(0, 0, 1000, 6, fill=Colors.BG_PANEL, outline='')
        
        # Progress bar (зеленый градиент в зависимости от confidence)
        progress_width = int((signal.confidence / 100) * 1000)
        if signal.confidence >= 80:
            progress_color = Colors.SUCCESS
        elif signal.confidence >= 60:
            progress_color = Colors.BUY
        else:
            progress_color = Colors.WARNING
        
        progress_canvas.create_rectangle(0, 0, progress_width, 6,
                                        fill=progress_color, outline='')
        
        # Reasoning (если есть)
        if signal.reasoning:
            reasoning_text = signal.reasoning[:120] + "..." if len(signal.reasoning) > 120 else signal.reasoning
            tk.Label(card_content,
                    text=f"💡 {reasoning_text}",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY,
                    wraplength=500,
                    justify='left').pack(anchor='w', pady=(5, 0))
        
        # Разделитель перед кнопкой
        tk.Frame(card_content, bg=Colors.BORDER, height=1).pack(fill='x', pady=(10, 10))
        
        # Кнопка удаления сигнала
        delete_btn = tk.Button(card_content,
                              text="🗑️ Delete Signal",
                              font=('Arial', 10, 'bold'),
                              bg=Colors.ERROR,
                              fg='white',
                              activebackground='#c0392b',
                              activeforeground='white',
                              cursor='hand2',
                              relief='flat',
                              padx=15,
                              pady=8,
                              command=lambda sid=signal.id: self._delete_signal(sid))
        delete_btn.pack(fill='x')
        
        # Hover эффект
        def on_enter(e):
            delete_btn.config(bg='#c0392b')
        def on_leave(e):
            delete_btn.config(bg=Colors.ERROR)
        
        delete_btn.bind('<Enter>', on_enter)
        delete_btn.bind('<Leave>', on_leave)
    
    def _delete_signal(self, signal_id: str):
        """Удалить сигнал из SignalManager"""
        try:
            # Проверяем наличие bot_manager
            if not self.bot_manager:
                app_logger.error("[GUI] BotManager not available")
                messagebox.showerror("Error", "Bot manager not initialized")
                return
            
            # Проверяем наличие signal_manager
            if not hasattr(self.bot_manager, 'signal_manager') or not self.bot_manager.signal_manager:
                app_logger.error("[GUI] SignalManager not available")
                messagebox.showerror("Error", "Signal manager not initialized")
                return
            
            # Получаем SignalManager из BotManager
            signal_manager = self.bot_manager.signal_manager
            
            if signal_manager.cancel_signal(signal_id):
                app_logger.info(f"[GUI] Signal {signal_id} cancelled successfully")
                
                # Показываем уведомление в Telegram (если доступен)
                if self.bot_manager.telegram:
                    try:
                        self.bot_manager.telegram.send_message(
                            f"🗑️ <b>Signal Deleted</b>\n\nSignal {signal_id} has been cancelled."
                        )
                    except Exception as tg_error:
                        app_logger.warning(f"[GUI] Telegram notification failed: {tg_error}")
                
                # Обновляем GUI
                self.refresh_analysis()
                
                # Показываем локальный алерт
                messagebox.showinfo("Signal Deleted", f"Signal {signal_id} has been cancelled.")
            else:
                app_logger.warning(f"[GUI] Failed to cancel signal {signal_id}")
                messagebox.showerror("Error", f"Signal {signal_id} not found")
                    
        except Exception as e:
            app_logger.error(f"[GUI] Error deleting signal: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error deleting signal: {str(e)}")
    
    def _create_history_section(self, signal_manager):
        """Создать секцию истории"""
        if not signal_manager.signal_history:
            return
        
        # Заголовок
        header_frame = tk.Frame(self.summary_left_scrollable, bg=Colors.BG_PANEL)
        header_frame.pack(fill='x', pady=(20, 15))
        
        recent_history = signal_manager.signal_history[-10:]
        
        tk.Label(header_frame,
                text=f"RECENT HISTORY ({len(recent_history)})",
                font=('Arial', 13, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.ACCENT).pack(side='left')
        
        # История в виде списка
        history_container = tk.Frame(self.summary_left_scrollable, bg=Colors.BG_CARD,
                                    highlightbackground=Colors.BORDER, highlightthickness=1)
        history_container.pack(fill='x')
        
        for entry in reversed(recent_history):
            self._create_history_item(history_container, entry)
    
    def _create_history_item(self, parent, entry):
        """Создать элемент истории"""
        item_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        item_frame.pack(fill='x', padx=12, pady=6)
        
        # Parse данных
        signal_id = entry.get('signal_id', '')
        action = entry.get('action', 'unknown')
        timestamp_str = entry.get('timestamp', '')
        
        # Symbol
        symbol = "Unknown"
        if signal_id:
            parts = signal_id.split('_')
            if parts:
                symbol = parts[0]
        
        # Time with date
        time_display = "N/A"
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str)
                # Умное отображение: если сегодня - только время, иначе дата + время
                now = datetime.now()
                if dt.date() == now.date():
                    # Сегодня - показываем только время
                    time_display = dt.strftime("%H:%M:%S")
                else:
                    # Вчера или старше - показываем дату + время
                    time_display = dt.strftime("%d.%m %H:%M")
            except (ValueError, AttributeError):
                time_display = timestamp_str[:19] if len(timestamp_str) >= 19 else timestamp_str
        
        # Action emoji and text
        action_emoji = {
            "created": "✨",
            "triggered": "🎯",
            "time_expired": "⏰",
            "price_invalidated": "❌",
            "cancelled": "🚫"
        }.get(action, "•")
        
        action_text = {
            "created": "Created",
            "triggered": "Triggered",
            "time_expired": "Expired (time)",
            "price_invalidated": "Expired (price)",
            "cancelled": "Cancelled"
        }.get(action, action)
        
        # Color
        action_colors = {
            "created": Colors.SUCCESS,
            "triggered": Colors.BUY,
            "time_expired": Colors.TEXT_MUTED,
            "price_invalidated": Colors.TEXT_MUTED,
            "cancelled": Colors.ERROR
        }
        action_color = action_colors.get(action, Colors.TEXT_SECONDARY)
        
        # Left side: emoji + time + symbol + action
        left_frame = tk.Frame(item_frame, bg=Colors.BG_CARD)
        left_frame.pack(side='left', fill='x', expand=True)
        
        main_text = f"{action_emoji} {time_display}  {symbol} {action_text}"
        tk.Label(left_frame,
                text=main_text,
                font=('Arial', 10),
                bg=Colors.BG_CARD,
                fg=action_color,
                anchor='w').pack(side='left')
        
        # Right side: details
        if action == "triggered" and 'price' in entry:
            detail_text = f"@ {entry['price']:.2f}"
            tk.Label(item_frame,
                    text=detail_text,
                    font=('Consolas', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_MUTED).pack(side='right')
        
        # Separator
        tk.Frame(parent, bg=Colors.BORDER, height=1).pack(fill='x')
    
    def _create_info_panels(self, signal_manager):
        """Создать информационные панели в правой колонке"""
        # ===== AI COMMENTARY PANEL =====
        commentary_panel = tk.Frame(self.summary_right_scrollable, bg=Colors.BG_CARD,
                                   highlightbackground=Colors.BORDER, highlightthickness=1)
        commentary_panel.pack(fill='x', pady=(0, 15))
        
        # Заголовок
        tk.Label(commentary_panel,
                text="AI COMMENTARY",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ACCENT,
                anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        # Разделитель
        tk.Frame(commentary_panel, bg=Colors.BORDER, height=1).pack(fill='x', padx=12)
        
        # Контент
        if signal_manager.block_type.value != "none":
            # Блокировка активна
            block_frame = tk.Frame(commentary_panel, bg=Colors.BG_CARD)
            block_frame.pack(fill='x', padx=12, pady=12)
            
            tk.Label(block_frame,
                    text="🔒 TRADING BLOCKED",
                    font=('Arial', 10, 'bold'),
                    bg=Colors.BG_CARD,
                    fg=Colors.ERROR).pack(anchor='w', pady=(0, 5))
            
            tk.Label(block_frame,
                    text=f"Type: {signal_manager.block_type.value.upper()}",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(anchor='w')
            
            if signal_manager.block_reason:
                tk.Label(block_frame,
                        text=f"Reason: {signal_manager.block_reason}",
                        font=('Arial', 9),
                        bg=Colors.BG_CARD,
                        fg=Colors.TEXT_SECONDARY,
                        wraplength=350,
                        justify='left').pack(anchor='w', pady=(3, 0))
            
            if signal_manager.block_until:
                tk.Label(block_frame,
                        text=f"Until: {signal_manager.block_until}",
                        font=('Arial', 9),
                        bg=Colors.BG_CARD,
                        fg=Colors.TEXT_MUTED).pack(anchor='w', pady=(3, 0))
        else:
            # Нет блокировки - показываем риск мультипликатор
            info_frame = tk.Frame(commentary_panel, bg=Colors.BG_CARD)
            info_frame.pack(fill='x', padx=12, pady=12)
            
            tk.Label(info_frame,
                    text="✓ Trading Active",
                    font=('Arial', 10, 'bold'),
                    bg=Colors.BG_CARD,
                    fg=Colors.SUCCESS).pack(anchor='w', pady=(0, 8))
            
            tk.Label(info_frame,
                    text=f"Risk Multiplier: {signal_manager.risk_multiplier}x",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(anchor='w')
        
        # ===== TODAY'S HIGH-IMPACT NEWS PANEL =====
        news_panel = tk.Frame(self.summary_right_scrollable, bg=Colors.BG_CARD,
                             highlightbackground=Colors.BORDER, highlightthickness=1)
        news_panel.pack(fill='x', pady=(0, 15))
        
        tk.Label(news_panel,
                text="📰 TODAY'S HIGH-IMPACT NEWS",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ACCENT,
                anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        tk.Frame(news_panel, bg=Colors.BORDER, height=1).pack(fill='x', padx=12)
        
        # Get today's HIGH-IMPACT news
        news_content = tk.Frame(news_panel, bg=Colors.BG_CARD)
        news_content.pack(fill='x', padx=12, pady=12)
        
        try:
            from src.ai.news_fetcher import get_news_fetcher
            news_fetcher = get_news_fetcher()
            high_impact_events = news_fetcher.get_high_impact_events(hours_ahead=24)
            
            if high_impact_events:
                # Show up to 5 events
                for i, event in enumerate(high_impact_events[:5]):
                    event_frame = tk.Frame(news_content, bg=Colors.BG_CARD)
                    event_frame.pack(fill='x', pady=(0 if i == 0 else 4, 0))
                    
                    # Time and currency
                    time_label = tk.Label(event_frame,
                                         text=f"{event.time} {event.currency}",
                                         font=('Arial', 8, 'bold'),
                                         bg=Colors.BG_CARD,
                                         fg=Colors.ACCENT)
                    time_label.pack(side='left')
                    
                    # Impact badge
                    impact_color = '#FF4444' if event.impact == 'EXTREME' else '#FFA500'
                    impact_label = tk.Label(event_frame,
                                           text=event.impact,
                                           font=('Arial', 7, 'bold'),
                                           bg=impact_color,
                                           fg='white',
                                           padx=4,
                                           pady=1)
                    impact_label.pack(side='left', padx=(6, 0))
                    
                    # Event title
                    title_label = tk.Label(news_content,
                                          text=event.title[:50] + '...' if len(event.title) > 50 else event.title,
                                          font=('Arial', 9),
                                          bg=Colors.BG_CARD,
                                          fg=Colors.TEXT_PRIMARY,
                                          wraplength=250,
                                          justify='left')
                    title_label.pack(anchor='w', pady=(2, 0))
                
                # Total count
                tk.Label(news_content,
                        text=f"\nTotal HIGH events today: {len(high_impact_events)}",
                        font=('Arial', 8, 'italic'),
                        bg=Colors.BG_CARD,
                        fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(8, 0))
            else:
                tk.Label(news_content,
                        text="No HIGH-IMPACT news today",
                        font=('Arial', 9),
                        bg=Colors.BG_CARD,
                        fg=Colors.TEXT_SECONDARY).pack(anchor='w')
        except Exception as e:
            tk.Label(news_content,
                    text=f"News unavailable: {str(e)[:30]}...",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(anchor='w')
        
        # ===== SIGNAL LIFECYCLE PANEL =====
        lifecycle_panel = tk.Frame(self.summary_right_scrollable, bg=Colors.BG_CARD,
                                  highlightbackground=Colors.BORDER, highlightthickness=1)
        lifecycle_panel.pack(fill='x', pady=(0, 15))
        
        tk.Label(lifecycle_panel,
                text="SIGNAL LIFECYCLE",
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_CARD,
                fg=Colors.ACCENT,
                anchor='w').pack(fill='x', padx=12, pady=(12, 8))
        
        tk.Frame(lifecycle_panel, bg=Colors.BORDER, height=1).pack(fill='x', padx=12)
        
        lifecycle_content = tk.Frame(lifecycle_panel, bg=Colors.BG_CARD)
        lifecycle_content.pack(fill='x', padx=12, pady=12)
        
        # Triggered
        triggered_count = len([s for s in signal_manager.active_signals if s.status == "triggered"])
        tk.Label(lifecycle_content,
                text=f"🎯 Triggered: {triggered_count}",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(0, 3))
        
        # Expired
        if signal_manager.signal_history:
            recent = signal_manager.signal_history[-20:]
            expired_count = len([e for e in recent if 'expired' in e.get('action', '')])
            tk.Label(lifecycle_content,
                    text=f"⏰ Expired (recent): {expired_count}",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(0, 3))
        
        # Last Analysis
        if signal_manager.latest_analysis_time:
            tk.Label(lifecycle_content,
                    text=f"🕐 Last Analysis:",
                    font=('Arial', 9),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_SECONDARY).pack(anchor='w', pady=(8, 2))
            
            tk.Label(lifecycle_content,
                    text=signal_manager.latest_analysis_time,
                    font=('Consolas', 8),
                    bg=Colors.BG_CARD,
                    fg=Colors.TEXT_MUTED).pack(anchor='w')
            
            if signal_manager.latest_analysis_version:
                tk.Label(lifecycle_content,
                        text=f"Version: {signal_manager.latest_analysis_version}",
                        font=('Consolas', 8),
                        bg=Colors.BG_CARD,
                        fg=Colors.TEXT_MUTED).pack(anchor='w', pady=(2, 0))
    
    def update_summary(self, analysis_data):
        """Обновить Analysis Summary (deprecated - use refresh_analysis)"""
        self.refresh_analysis()


# ==================== MAIN APP ====================
class BazaApp:
    """Главное приложение с новым UI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BAZA Trading Bot - Pure AI Mode")
        
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
        
        # Загрузить AI Analysis при запуске
        if AI_ANALYSIS_AVAILABLE and hasattr(self, 'analyst_panel'):
            self.root.after(1000, self.analyst_panel.refresh_analysis)
        
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
        
        # Control Panel
        self.control_panel = ControlPanel(left_panel, self._start_bot, self._stop_bot)
        self.control_panel.pack(fill='x', pady=(0, 20))
        
        # Stats Panel
        self.stats_panel = StatsPanel(left_panel, self.app_state)
        self.stats_panel.pack(fill='x', pady=(0, 20))
        
        # Current Settings Panel
        self.settings_info_panel = CurrentSettingsPanel(left_panel)
        self.settings_info_panel.pack(fill='x', pady=(0, 10))
        
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
        
        # Test GPT Connection Button
        tk.Button(left_panel, text="🧪 Test GPT",
                 font=('Arial', 10),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 activebackground=Colors.BG_HOVER,
                 relief='flat',
                 cursor='hand2',
                 command=self.test_gpt_connection).pack(fill='x')
        
        # Right Panel (AI Analyst) - передаем bot_manager
        self.analyst_panel = AnalystPanel(main_container, bot_manager=self.bot_manager)
        self.analyst_panel.pack(side='right', fill='both', expand=True)
    
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
            
            # Обновить вкладку Analysis
            if AI_ANALYSIS_AVAILABLE and hasattr(self, 'analyst_panel'):
                self.root.after(500, self.analyst_panel.refresh_analysis)
            
            # Запустить первый анализ при старте (для EVENT-DRIVEN режима)
            if hasattr(self.bot_manager, 'analyst_scheduler') and self.bot_manager.analyst_scheduler:
                self.bot_manager.analyst_scheduler.trigger_immediate_analysis(
                    symbol="XAUUSD",
                    reason="startup",
                    cooldown_minutes=0
                )
                app_logger.info("[BOT] Triggered startup analysis for first signal")
            
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
            
            # Моментальное обновление UI - без ожидания!
            self.stop_event.set()
            self.bot_running = False
            self.control_panel.set_bot_running(False)
            
            # Все остальное делаем асинхронно в отдельном потоке
            # чтобы не блокировать GUI
            import threading
            def _async_stop():
                try:
                    # Дождаться завершения потока с коротким таймаутом
                    if self.bot_thread and self.bot_thread.is_alive():
                        self.bot_thread.join(timeout=1)  # Уменьшено с 3 до 1 сек
                    
                    # Остановить AI Scheduler если запущен
                    if AI_ANALYSIS_AVAILABLE:
                        try:
                            scheduler = get_scheduler()
                            if scheduler:
                                scheduler.stop()
                                app_logger.info("[BOT] AI Scheduler stopped")
                        except Exception as e:
                            app_logger.error(f"[BOT] Failed to stop AI Scheduler: {e}")
                    
                    # Уведомить BotManager об остановке (в фоновом потоке)
                    self.bot_manager.stop()
                    
                    app_logger.info("[BOT] Stopped")
                except Exception as e:
                    app_logger.error(f"[BOT] Error during async stop: {e}")
            
            # Запускаем остановку в фоне - GUI не блокируется!
            threading.Thread(target=_async_stop, daemon=True, name="StopThread").start()
            
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
            
            # Получить LiveTrader из BotManager (ждём пока инициализируется)
            trader = None
            max_wait = 10  # Максимум 10 секунд ожидания
            for i in range(max_wait * 10):  # Проверяем каждые 100мс
                if hasattr(self.bot_manager, 'live_trader') and self.bot_manager.live_trader:
                    trader = self.bot_manager.live_trader
                    break
                time.sleep(0.1)
            
            if not trader:
                app_logger.error("[LOOP] LiveTrader not initialized in BotManager after 10s!")
                self.root.after(0, lambda: messagebox.showerror("Error", "LiveTrader initialization failed - timeout"))
                self._stop_bot()
                return
            
            # Передать MT5Manager в LiveTrader (на случай если не был передан)
            trader.mt5 = self.app_state.mt5_manager.mt5
            trader.mt5_manager = self.app_state.mt5_manager
            
            app_logger.info("[LOOP] Using LiveTrader from BotManager (no duplicate creation)")
            
            # Запустить AI Scheduler для Pure AI режима
            if AI_ANALYSIS_AVAILABLE:
                try:
                    # КРИТИЧНО: Передаём существующий signal_manager из trader
                    scheduler = init_scheduler(
                        executor=trader.executor,
                        signal_manager=trader.ai_signal_manager
                    )
                    scheduler.start()
                    app_logger.info("[LOOP] AI Scheduler started for Pure AI mode")
                    
                    # Set references for auto-requery BEFORE requesting analysis
                    trader.analyst_scheduler = scheduler
                    if trader.ai_signal_manager:
                        trader.ai_signal_manager.set_scheduler(scheduler)
                        trader.ai_signal_manager.set_executor(trader.executor)
                    app_logger.info("[LOOP] Auto-requery configured (TTL + position close)")
                    
                    # 🔥 КРИТИЧНО: Запрашиваем первый анализ при старте Pure AI режима
                    # Scheduler reference уже установлен, так что NONE retry будет работать
                    app_logger.info("[LOOP] 🔥 Requesting initial AI analysis for Pure AI mode...")
                    try:
                        # Запрос анализа только для активных инструментов
                        for symbol in ['XAUUSD']:  # EURUSD отключен
                            scheduler.trigger_immediate_analysis(
                                symbol=symbol,
                                reason="Pure AI mode started - initial analysis"
                            )
                            app_logger.info(f"[LOOP] ✅ Initial analysis requested for {symbol}")
                    except Exception as e:
                        app_logger.error(f"[LOOP] Failed to request initial analysis: {e}")
                    
                except Exception as e:
                    app_logger.error(f"[LOOP] Failed to start AI Scheduler: {e}")
            
            # Запустить мониторинг
            while not self.stop_event.is_set():
                try:
                    # Обновить статистику из MT5
                    self._update_stats_from_mt5()
                    
                    # Pure AI mode - проверить сигналы
                    # Check stop before signal generation
                    if self.stop_event.is_set():
                        break
                    
                    app_logger.debug("[LOOP] Running pure AI mode")
                    trader.check_signals()
                    
                    # Проверить TTL истечение сигналов (ТОЛЬКО если нет открытых позиций)
                    if trader.ai_signal_manager:
                        # Блокировка: если позиция открыта - НЕ проверять TTL
                        has_positions = False
                        if self.app_state.mt5_manager and self.app_state.mt5_manager.is_connected():
                            positions = self.app_state.mt5_manager.get_open_positions()
                            has_positions = len(positions) > 0
                        
                        if not has_positions:
                            trader.ai_signal_manager._cleanup_expired_signals()
                        else:
                            app_logger.debug("[LOOP] Position open - TTL check blocked")
                    
                    # Проверить trailing stop для открытых позиций
                    trader.check_trailing_stop()
                    
                    # Проверить закрытые позиции (Telegram уведомления)
                    trader.check_closed_positions()
                    
                    # Обновить открытые позиции
                    self._update_positions()
                    
                    # Пауза перед следующей итерацией (настраивается в config/trading.yaml)
                    check_interval = trader.get_check_interval() if trader else 3
                    self.stop_event.wait(check_interval)
                    
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
                # Сначала обновляем статистику в BotManager (он рассчитает total_pnl из balance)
                if hasattr(self.bot_manager, '_update_stats_from_mt5'):
                    self.bot_manager._update_stats_from_mt5()
                
                # Теперь берем данные из bot_manager.stats (единственный источник правды)
                balance = self.bot_manager.stats.get('balance', 0)
                total_pnl = self.bot_manager.stats.get('total_pnl', 0)
                today_pnl = self.bot_manager.stats.get('today_pnl', 0)
                
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
        except Exception as e:
            app_logger.debug(f"Failed to add log to UI: {e}")
    
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
                
                # ИСПРАВЛЕНО: Обновить статистику через метод app
                self._update_stats_from_mt5()
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
                            
                            # ИСПРАВЛЕНО: Обновить статистику через общий метод
                            self.root.after(0, self._update_stats_from_mt5)
                    
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
                    # Подсчет работающих систем
                    total_systems = 3  # API, Config, Data
                    working = sum([
                        results["openai_api"]["status"],
                        results["config_files"]["status"],
                        results["data_folders"]["status"]
                    ])
                    app_logger.startup(f"All systems operational ({working}/{total_systems})")
            else:
                app_logger.startup("All systems operational")
                
        except Exception as e:
            app_logger.error(f"[Diagnostics] Failed to run diagnostics: {e}")
    
    def show_settings_dialog(self):
        """Показать диалог настроек"""
        try:
            SettingsDialog(self.root, on_save_callback=self._on_settings_saved)
        except Exception as e:
            import traceback
            app_logger.error(f"[SETTINGS] Error: {e}")
            app_logger.error(f"[SETTINGS] Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to open settings: {e}")
    
    def _on_settings_saved(self, restart=False):
        """Callback после сохранения настроек
        
        Args:
            restart: Если True - перезапустить бота после сохранения
        """
        try:
            app_logger.info(f"[SETTINGS] Settings updated, restart={restart}")
            
            if restart:
                # Перезапуск бота
                app_logger.info("[SETTINGS] Restarting bot with new configuration...")
                
                # Останавливаем если работает
                was_running = False
                if hasattr(self, 'bot_manager') and self.bot_manager:
                    if self.bot_manager.status == BotStatus.RUNNING:
                        was_running = True
                        self._stop_bot()
                        # Даем время на остановку
                        import time
                        time.sleep(1)
                
                # Перезагружаем конфиг
                if hasattr(self, 'bot_manager') and self.bot_manager:
                    self.bot_manager.reload_config()
                    
                    # Обновляем панель настроек
                    settings = self.bot_manager.get_current_settings()
                    if hasattr(self, 'settings_info_panel'):
                        self.settings_info_panel.update_settings(settings)
                
                # Запускаем снова если был запущен
                if was_running:
                    self._start_bot()
                    app_logger.info("[SETTINGS] ✅ Bot restarted with new configuration")
                else:
                    app_logger.info("[SETTINGS] ✅ Configuration reloaded (bot was stopped)")
            else:
                # Применить настройки без перезапуска
                if hasattr(self, 'bot_manager') and self.bot_manager:
                    success = self.bot_manager.reload_config()
                    if success:
                        # Обновить панель Current Settings
                        settings = self.bot_manager.get_current_settings()
                        if hasattr(self, 'settings_info_panel'):
                            self.settings_info_panel.update_settings(settings)
                        
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
    
    def _show_first_run_lot_hint(self):
        """Показать подсказку о размере лота при первом запуске"""
        try:
            hint_flag = get_data_path('.lot_hint_shown')
            
            # Если подсказка уже показывалась, пропускаем
            if hint_flag.exists():
                return
            
            # Показываем информационное окно
            result = messagebox.showinfo(
                "💡 Важно: Настройка размера позиции",
                "📊 РАЗМЕР ЛОТА (Max Lot Size) определяет сколько денег вы рискуете в сделке!\n\n"
                "🔢 Таблица размеров:\n"
                "   • 0.01 лот = $1,000 контракт\n"
                "   • 0.10 лот = $10,000 контракт\n"
                "   • 1.00 лот = $100,000 контракт\n\n"
                "⚠️ Рекомендации:\n"
                "   • Новичкам: 0.01 - 0.05 лота\n"
                "   • Средний опыт: 0.05 - 0.10 лота\n"
                "   • Опытные: 0.10 - 0.50 лота\n\n"
                "⚙️ Настроить можно в меню Settings → Risk Management\n"
                "📖 Подробное руководство: Settings → 'Открыть подробное руководство'\n\n"
                "Это сообщение больше не появится."
            )
            
            # Создать флаг что подсказка показана
            hint_flag.parent.mkdir(parents=True, exist_ok=True)
            hint_flag.touch()
            
            app_logger.info("[GUI] First-run lot size hint shown")
            
        except Exception as e:
            app_logger.error(f"[GUI] Failed to show lot hint: {e}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Entry point"""
    app = BazaApp()
    app.run()


if __name__ == '__main__':
    main()

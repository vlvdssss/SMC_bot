#!/usr/bin/env python3
"""
BAZA Trading Bot - GUI Application

Запуск: python -m src.gui.app
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.license import license_manager
try:
    import openai
except ImportError:
    openai = None


class BazaApp:
    """Главное окно приложения."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BAZA Trading Bot")
        self.root.geometry("900x700")
        self.root.configure(bg='#1a1a1a')
        self.root.resizable(True, True)
        
        # Состояние
        self.bot_running = False
        self.bot_paused = False
        self.bot_thread = None
        self.stop_event = threading.Event()
        self.trader = None
        
        # Статистика
        self.stats = {
            'balance': 100.0,
            'total_pnl': 0.0,
            'today_pnl': 0.0,
            'trades': 0,
            'wins': 0,
            'losses': 0
        }
        
        # Проверка лицензии при старте
        self.check_license_on_start()
        
        self.load_stats()
        self.create_ui()
        self.update_display()
    
    def check_license_on_start(self):
        """Проверка лицензии при запуске."""
        valid, message = license_manager.is_valid()
        
        if not valid:
            # Показываем окно активации
            self.show_activation_dialog()
    
    def show_activation_dialog(self):
        """Окно активации."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Активация BAZA")
        dialog.geometry("400x200")
        dialog.configure(bg='#1a1a1a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем
        dialog.geometry("+%d+%d" % (
            self.root.winfo_screenwidth() / 2 - 200,
            self.root.winfo_screenheight() / 2 - 100
        ))
        
        tk.Label(dialog, text="🔐 Активация BAZA Trading Bot",
                font=('Arial', 14, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=20)
        
        tk.Label(dialog, text="Введите ключ активации:",
                font=('Arial', 10),
                bg='#1a1a1a', fg='#888888').pack()
        
        key_entry = tk.Entry(dialog, font=('Arial', 12), width=25,
                            bg='#2a2a2a', fg='white', insertbackground='white')
        key_entry.pack(pady=10)
        key_entry.focus()
        
        result_label = tk.Label(dialog, text="",
                               font=('Arial', 10),
                               bg='#1a1a1a', fg='#888888')
        result_label.pack()
        
        def activate(save=True):
            key = key_entry.get()
            if not key:
                result_label.config(text="❌ Введите ключ", fg='#ff4757')
                return
                
            success, msg = license_manager.activate(key)
            
            if success:
                if save:
                    result_label.config(text=f"✅ {msg}", fg='#00d4aa')
                    dialog.after(1500, dialog.destroy)
                else:
                    result_label.config(text=f"🧪 ТЕСТ: {msg}", fg='#f39c12')
            else:
                result_label.config(text=f"❌ {msg}", fg='#ff4757')
        
        def test_key():
            """Тест ключа без сохранения."""
            activate(save=False)
        
        def on_close():
            valid, _ = license_manager.is_valid()
            if not valid:
                if messagebox.askyesno("Выход", "Без активации бот не будет работать.\nВыйти?"):
                    self.root.destroy()
                    sys.exit()
            else:
                dialog.destroy()
        
        # Кнопки
        btn_frame = tk.Frame(dialog, bg='#1a1a1a')
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Button(btn_frame, text="🧪 Тест",
                 font=('Arial', 10, 'bold'),
                 bg='#f39c12', fg='black',
                 command=test_key,
                 width=8, height=1,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="Активировать",
                 font=('Arial', 11, 'bold'),
                 bg='#00d4aa', fg='black',
                 command=lambda: activate(save=True),
                 width=12, height=1,
                 relief='flat', cursor='hand2').pack(side='right', padx=5)
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # Ждём закрытия диалога
        self.root.wait_window(dialog)
    
    def show_settings_dialog(self):
        """Диалог настроек."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки BAZA")
        dialog.geometry("500x400")
        dialog.configure(bg='#1a1a1a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем
        dialog.geometry("+%d+%d" % (
            self.root.winfo_screenwidth() / 2 - 250,
            self.root.winfo_screenheight() / 2 - 200
        ))
        
        tk.Label(dialog, text="⚙ Настройки BAZA Trading Bot",
                font=('Arial', 16, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=20)
        
        # OpenAI API Key
        api_frame = tk.Frame(dialog, bg='#2a2a2a', relief='flat')
        api_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(api_frame, text="🤖 OpenAI API Key (для GPT фильтра)",
                font=('Arial', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', pady=(10, 5))
        
        tk.Label(api_frame, text="Получите ключ на https://platform.openai.com/api-keys",
                font=('Arial', 9),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(0, 10))
        
        # Текущее значение
        current_key = os.getenv("OPENAI_API_KEY", "")
        api_entry = tk.Entry(api_frame, font=('Arial', 10), width=50,
                            bg='#0f0f0f', fg='white', insertbackground='white')
        api_entry.insert(0, current_key)
        api_entry.pack(pady=(0, 10))
        
        # Статус GPT
        status_label = tk.Label(api_frame, text="",
                               font=('Arial', 10),
                               bg='#2a2a2a', fg='#888888')
        status_label.pack(pady=(0, 10))
        
        def test_api_key():
            key = api_entry.get().strip()
            if not key:
                status_label.config(text="❌ Ключ не введён", fg='#ff4757')
                return
            
            if openai is None:
                status_label.config(text="❌ OpenAI библиотека не установлена", fg='#ff4757')
                return
            
            # Тестируем ключ
            try:
                client = openai.OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                status_label.config(text="✅ Ключ работает!", fg='#00d4aa')
            except Exception as e:
                status_label.config(text=f"❌ Ошибка: {str(e)[:50]}", fg='#ff4757')
        
        tk.Button(api_frame, text="🔍 Проверить ключ",
                 font=('Arial', 10, 'bold'),
                 bg='#00d4aa', fg='black',
                 command=test_api_key,
                 width=15, height=1,
                 relief='flat', cursor='hand2').pack(pady=(0, 10))
        
        # Раздел лицензии
        license_frame = tk.Frame(dialog, bg='#2a2a2a', relief='flat')
        license_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(license_frame, text="🔐 Лицензия (для тестирования)",
                font=('Arial', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', pady=(10, 5))
        
        def reset_license():
            """Сброс лицензии для тестирования."""
            try:
                license_path = Path('data/license.json')
                if license_path.exists():
                    license_path.unlink()
                    status_label.config(text="✅ Лицензия сброшена! Перезапустите программу.", fg='#00d4aa')
                else:
                    status_label.config(text="ℹ️ Лицензия не найдена", fg='#f39c12')
            except Exception as e:
                status_label.config(text=f"❌ Ошибка сброса: {e}", fg='#ff4757')
        
        tk.Button(license_frame, text="🔄 Сбросить лицензию",
                 font=('Arial', 10, 'bold'),
                 bg='#ff4757', fg='white',
                 command=reset_license,
                 width=15, height=1,
                 relief='flat', cursor='hand2').pack(pady=(0, 10))
        
        tk.Label(license_frame, text="⚠️ После сброса перезапустите программу для тестирования активации",
                font=('Arial', 8),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(0, 10))
        
        # Кнопки
        btn_frame = tk.Frame(dialog, bg='#1a1a1a')
        btn_frame.pack(fill='x', padx=20, pady=20)
        
        def save_settings():
            key = api_entry.get().strip()
            if key:
                # Сохраняем в переменную окружения для текущей сессии
                os.environ["OPENAI_API_KEY"] = key
                
                # Сохраняем в файл для будущих запусков
                env_file = Path('.env')
                try:
                    if env_file.exists():
                        with open(env_file, 'r') as f:
                            lines = f.readlines()
                    else:
                        lines = []
                    
                    # Удаляем старую строку с OPENAI_API_KEY
                    lines = [line for line in lines if not line.startswith('OPENAI_API_KEY=')]
                    
                    # Добавляем новую
                    lines.append(f'OPENAI_API_KEY={key}\n')
                    
                    with open(env_file, 'w') as f:
                        f.writelines(lines)
                    
                    status_label.config(text="✅ Настройки сохранены!", fg='#00d4aa')
                    
                except Exception as e:
                    status_label.config(text=f"❌ Ошибка сохранения: {e}", fg='#ff4757')
            else:
                status_label.config(text="ℹ️ Ключ очищен", fg='#f39c12')
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']
        
        tk.Button(btn_frame, text="💾 Сохранить",
                 font=('Arial', 11, 'bold'),
                 bg='#00d4aa', fg='black',
                 command=save_settings,
                 width=12, height=2,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="❌ Отмена",
                 font=('Arial', 11, 'bold'),
                 bg='#ff4757', fg='white',
                 command=dialog.destroy,
                 width=12, height=2,
                 relief='flat', cursor='hand2').pack(side='right', padx=5)
    
    def create_ui(self):
        """Создание интерфейса."""
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg='#1a1a1a')
        header.pack(fill='x', padx=20, pady=10)
        
        # Логотип
        logo = tk.Label(header, text="🤖 BAZA Trading Bot", 
                       font=('Arial', 20, 'bold'), 
                       bg='#1a1a1a', fg='white')
        logo.pack(side='left')
        
        # Лицензия
        license_info = license_manager.get_license_info()
        license_text = f"🔑 {license_info.get('type', '').upper() or 'N/A'}" if license_info['valid'] else "🔒 Не активировано"
        
        self.license_label = tk.Label(header, text=license_text,
                                     font=('Arial', 10),
                                     bg='#1a1a1a', fg='#00d4aa' if license_info['valid'] else '#ff4757')
        self.license_label.pack(side='right', padx=10)
        
        # Статус бота
        self.status_frame = tk.Frame(header, bg='#1a1a1a')
        self.status_frame.pack(side='right')
        
        self.status_dot = tk.Label(self.status_frame, text="●", 
                                   font=('Arial', 16), 
                                   bg='#1a1a1a', fg='#ff4757')
        self.status_dot.pack(side='left', padx=5)
        
        self.status_label = tk.Label(self.status_frame, text="Остановлен",
                                    font=('Arial', 12),
                                    bg='#1a1a1a', fg='#888888')
        self.status_label.pack(side='left')
        
        # ===== MT5 CONNECTION STATUS =====
        mt5_frame = tk.Frame(self.root, bg='#2a2a2a')
        mt5_frame.pack(fill='x', padx=20, pady=5)
        
        self.mt5_status = tk.Label(mt5_frame, 
                                   text="📡 MT5: Не подключено",
                                   font=('Arial', 10),
                                   bg='#2a2a2a', fg='#888888')
        self.mt5_status.pack(side='left', padx=10, pady=8)
        
        self.mt5_account = tk.Label(mt5_frame,
                                    text="",
                                    font=('Arial', 10),
                                    bg='#2a2a2a', fg='#888888')
        self.mt5_account.pack(side='right', padx=10, pady=8)
        
        # ===== CONTROL PANEL =====
        control = tk.Frame(self.root, bg='#2a2a2a', relief='flat')
        control.pack(fill='x', padx=20, pady=10)
        
        btn_frame = tk.Frame(control, bg='#2a2a2a')
        btn_frame.pack(pady=15)
        
        self.btn_start = tk.Button(btn_frame, text="▶ СТАРТ", 
                                   command=self.start_bot,
                                   font=('Arial', 11, 'bold'),
                                   bg='#00d4aa', fg='black',
                                   width=12, height=2,
                                   relief='flat', cursor='hand2')
        self.btn_start.pack(side='left', padx=5)
        
        self.btn_pause = tk.Button(btn_frame, text="⏸ ПАУЗА",
                                   command=self.pause_bot,
                                   font=('Arial', 11, 'bold'),
                                   bg='#f39c12', fg='black',
                                   width=12, height=2,
                                   relief='flat', cursor='hand2',
                                   state='disabled')
        self.btn_pause.pack(side='left', padx=5)
        
        self.btn_stop = tk.Button(btn_frame, text="⏹ СТОП",
                                  command=self.stop_bot,
                                  font=('Arial', 11, 'bold'),
                                  bg='#ff4757', fg='white',
                                  width=12, height=2,
                                  relief='flat', cursor='hand2',
                                  state='disabled')
        self.btn_stop.pack(side='left', padx=5)
        
        # Кнопка активации
        self.btn_activate = tk.Button(btn_frame, text="🔑 Ключ",
                                      command=self.show_activation_dialog,
                                      font=('Arial', 10),
                                      bg='#3a3a3a', fg='white',
                                      width=8, height=2,
                                      relief='flat', cursor='hand2')
        self.btn_activate.pack(side='left', padx=20)
        
        # Кнопка настроек
        self.btn_settings = tk.Button(btn_frame, text="⚙ Настройки",
                                      command=self.show_settings_dialog,
                                      font=('Arial', 10),
                                      bg='#4a4a4a', fg='white',
                                      width=10, height=2,
                                      relief='flat', cursor='hand2')
        self.btn_settings.pack(side='left', padx=5)
        
        # Режим
        mode_frame = tk.Frame(control, bg='#2a2a2a')
        mode_frame.pack(pady=5)
        
        self.mode_var = tk.StringVar(value='demo')
        
        tk.Radiobutton(mode_frame, text="Demo", variable=self.mode_var, 
                      value='demo', bg='#2a2a2a', fg='white',
                      selectcolor='#1a1a1a', activebackground='#2a2a2a',
                      font=('Arial', 10)).pack(side='left', padx=10)
        
        tk.Radiobutton(mode_frame, text="Live", variable=self.mode_var,
                      value='live', bg='#2a2a2a', fg='white',
                      selectcolor='#1a1a1a', activebackground='#2a2a2a',
                      font=('Arial', 10)).pack(side='left', padx=10)
        
        # ===== STATS CARDS =====
        stats_frame = tk.Frame(self.root, bg='#1a1a1a')
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        self.card_balance = self.create_stat_card(stats_frame, "Баланс", "$100.00")
        self.card_balance.pack(side='left', expand=True, fill='x', padx=5)
        
        self.card_pnl = self.create_stat_card(stats_frame, "Общая прибыль", "$0.00")
        self.card_pnl.pack(side='left', expand=True, fill='x', padx=5)
        
        self.card_today = self.create_stat_card(stats_frame, "Сегодня", "$0.00")
        self.card_today.pack(side='left', expand=True, fill='x', padx=5)
        
        self.card_winrate = self.create_stat_card(stats_frame, "Win Rate", "0%")
        self.card_winrate.pack(side='left', expand=True, fill='x', padx=5)
        
        # ===== LOGS =====
        logs_frame = tk.Frame(self.root, bg='#1a1a1a')
        logs_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        logs_header = tk.Label(logs_frame, text="📊 Логи",
                              font=('Arial', 12, 'bold'),
                              bg='#1a1a1a', fg='white')
        logs_header.pack(anchor='w', pady=(0, 5))
        
        self.logs_text = tk.Text(logs_frame, 
                                 bg='#0f0f0f', fg='#00d4aa',
                                 font=('Consolas', 10),
                                 relief='flat',
                                 state='disabled')
        self.logs_text.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(self.logs_text)
        scrollbar.pack(side='right', fill='y')
        self.logs_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.logs_text.yview)
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg='#1a1a1a')
        footer.pack(fill='x', padx=20, pady=10)
        
        tk.Label(footer, text="BAZA v3.0 | SMC + ML + GPT",
                font=('Arial', 9), bg='#1a1a1a', fg='#555555').pack()
    
    def create_stat_card(self, parent, title, value):
        """Создание карточки статистики."""
        card = tk.Frame(parent, bg='#2a2a2a', relief='flat')
        
        tk.Label(card, text=title, font=('Arial', 10),
                bg='#2a2a2a', fg='#888888').pack(pady=(10, 0))
        
        value_label = tk.Label(card, text=value, font=('Arial', 18, 'bold'),
                              bg='#2a2a2a', fg='white')
        value_label.pack(pady=(0, 10))
        
        card.value_label = value_label
        return card
    
    def log(self, message):
        """Добавление лога."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.logs_text.config(state='normal')
        self.logs_text.insert('end', f"[{timestamp}] {message}\n")
        self.logs_text.see('end')
        self.logs_text.config(state='disabled')
    
    def update_mt5_status(self, connected: bool, info: dict = None):
        """Обновление статуса MT5."""
        if connected and info:
            self.mt5_status.config(text="📡 MT5: Подключено ✓", fg='#00d4aa')
            self.mt5_account.config(
                text=f"Счёт: {info.get('account', 'N/A')} | Баланс: ${info.get('balance', 0):.2f}",
                fg='#888888'
            )
        else:
            self.mt5_status.config(text="📡 MT5: Не подключено", fg='#ff4757')
            self.mt5_account.config(text="")
    
    def update_display(self):
        """Обновление статистики."""
        self.card_balance.value_label.config(text=f"${self.stats['balance']:.2f}")
        
        pnl = self.stats['total_pnl']
        color = '#00d4aa' if pnl >= 0 else '#ff4757'
        self.card_pnl.value_label.config(
            text=f"{'+' if pnl >= 0 else ''}${pnl:.2f}", fg=color)
        
        today = self.stats['today_pnl']
        color = '#00d4aa' if today >= 0 else '#ff4757'
        self.card_today.value_label.config(
            text=f"{'+' if today >= 0 else ''}${today:.2f}", fg=color)
        
        total = self.stats['wins'] + self.stats['losses']
        winrate = (self.stats['wins'] / total * 100) if total > 0 else 0
        self.card_winrate.value_label.config(text=f"{winrate:.0f}%")
    
    def update_status(self, running, paused=False):
        """Обновление статуса бота."""
        self.bot_running = running
        self.bot_paused = paused
        
        if running and not paused:
            self.status_dot.config(fg='#00d4aa')
            self.status_label.config(text='Работает')
            self.btn_start.config(state='disabled')
            self.btn_pause.config(state='normal', text='⏸ ПАУЗА')
            self.btn_stop.config(state='normal')
        elif running and paused:
            self.status_dot.config(fg='#f39c12')
            self.status_label.config(text='Пауза')
            self.btn_pause.config(text='▶ ПРОДОЛЖИТЬ')
        else:
            self.status_dot.config(fg='#ff4757')
            self.status_label.config(text='Остановлен')
            self.btn_start.config(state='normal')
            self.btn_pause.config(state='disabled', text='⏸ ПАУЗА')
            self.btn_stop.config(state='disabled')
    
    def start_bot(self):
        """Запуск бота."""
        # Проверка лицензии
        valid, msg = license_manager.is_valid()
        if not valid:
            messagebox.showerror("Ошибка", f"Лицензия недействительна: {msg}")
            return
        
        mode = self.mode_var.get()
        
        if mode == 'live':
            if not messagebox.askyesno("Подтверждение", 
                    "Вы уверены что хотите запустить LIVE торговлю?\n\n"
                    "Будут открываться РЕАЛЬНЫЕ сделки!"):
                return
        
        self.stop_event.clear()
        self.bot_thread = threading.Thread(target=self.run_bot, args=(mode,), daemon=True)
        self.bot_thread.start()
        
        self.update_status(True, False)
        self.log(f"🚀 Бот запущен в режиме {mode.upper()}")
    
    def stop_bot(self):
        """Остановка бота."""
        self.stop_event.set()
        self.update_status(False)
        self.update_mt5_status(False)
        self.log("⏹️ Бот остановлен")
    
    def pause_bot(self):
        """Пауза/продолжение."""
        if self.bot_paused:
            self.bot_paused = False
            self.update_status(True, False)
            self.log("▶️ Бот возобновлён")
        else:
            self.bot_paused = True
            self.update_status(True, True)
            self.log("⏸️ Бот на паузе")
    
    def run_bot(self, mode):
        """Основной цикл бота."""
        try:
            from src.live.live_trader import LiveTrader
            
            self.log("📡 Подключение к MT5...")
            
            enable_trading = (mode == 'live')
            self.trader = LiveTrader(config_dir='config', enable_trading=enable_trading)
            
            # Обновляем статус MT5
            status = self.trader.get_connection_status()
            self.root.after(0, lambda: self.update_mt5_status(
                status['connected'], status
            ))
            
            if status['connected']:
                self.log(f"✅ MT5 подключен: {status.get('broker', '')} | Счёт: {status.get('account', '')}")
                self.log(f"💰 Баланс: ${status.get('balance', 0):.2f}")
            else:
                self.log(f"❌ Ошибка подключения: {status.get('message', 'Unknown')}")
                self.root.after(0, lambda: self.update_status(False))
                return
            
            self.log("🔄 Начинаю мониторинг рынка...")
            
            while not self.stop_event.is_set():
                if self.bot_paused:
                    self.stop_event.wait(1)
                    continue
                
                try:
                    # Проверка сигналов
                    signals = self.trader.check_signals()
                    
                    if signals:
                        for signal in signals:
                            self.log(f"📊 {signal}")
                        
                        # Обновляем статистику
                        self.root.after(0, self.update_display)
                    
                except Exception as e:
                    self.log(f"⚠️ Ошибка: {str(e)}")
                
                # Ждём 60 секунд
                self.stop_event.wait(60)
            
        except Exception as e:
            self.log(f"❌ Критическая ошибка: {str(e)}")
            self.root.after(0, lambda: self.update_status(False))
            self.root.after(0, lambda: self.update_mt5_status(False))
    
    def load_stats(self):
        """Загрузка статистики."""
        stats_file = Path('data/bot_stats.json')
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                self.stats.update(json.load(f))
    
    def save_stats(self):
        """Сохранение статистики."""
        stats_file = Path('data/bot_stats.json')
        stats_file.parent.mkdir(exist_ok=True)
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f)
    
    def on_closing(self):
        """При закрытии."""
        if self.bot_running:
            if messagebox.askyesno("Выход", "Бот работает. Остановить и выйти?"):
                self.stop_bot()
                self.save_stats()
                self.root.destroy()
        else:
            self.save_stats()
            self.root.destroy()
    
    def run(self):
        """Запуск приложения."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("✅ BAZA Trading Bot готов к работе")
        self.log("💡 Выберите режим и нажмите СТАРТ")
        self.root.mainloop()


def main():
    app = BazaApp()
    app.run()


if __name__ == '__main__':
    main()
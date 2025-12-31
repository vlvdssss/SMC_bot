#!/usr/bin/env python3
"""
BAZA Trading Bot - GUI Application

Запуск: python -m src.gui.app
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import customtkinter
import threading
import json
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.license import license_manager
from src.core.app_state import AppState
from src.core.mt5_manager import MT5Manager
from src.core.bot_manager import bot_manager
from src.core.logger import logger as app_logger
from src.core.manual_trade_state import ManualTradeState
from src.core.market_data_updater import MarketDataUpdater
try:
    import openai
except ImportError:
    openai = None

# Manual trading imports
try:
    from src.manual_trading.controller import ManualTradingController
    from src.models import AIPrediction
    MANUAL_TRADING_AVAILABLE = True
except ImportError:
    MANUAL_TRADING_AVAILABLE = False


class BazaApp:
    """Главное окно приложения BAZA Trading Bot."""

    def __init__(self):
        # Создание главного окна
        self.root = tk.Tk()
        self.root.title("BAZA Trading Bot")
        self.root.geometry("900x700")
        self.root.configure(bg='#1a1a1a')
        self.root.resizable(True, True)
        
        # Инициализация состояния приложения
        self.app_state = AppState()

        # Hook bot_manager updates to UI
        try:
            self.bot_manager = bot_manager
            self.bot_manager.on_update = lambda: self.root.after(0, self._on_bot_manager_update)
        except Exception:
            self.bot_manager = None
        
        # Событие для остановки бота
        self.stop_event = threading.Event()
        
        # Переменные состояния бота (инициализируем в конструкторе)
        self.bot_running = False
        self.bot_paused = False
        self.bot_thread = None
        self.trader = None
        self.live_trader = None
        
        # Загрузка настроек
        self.load_settings()
        self.load_mt5_config()
        self.load_mt5_credentials()
        
        # Инициализация MT5
        self._init_mt5_manager()
        self._start_mt5_monitoring()
        
        # Инициализация ручной торговли
        self.manual_controller = None
        self.manual_config = self._load_manual_config()
        if MANUAL_TRADING_AVAILABLE:
            config = self.manual_config
            if config.get('enabled', False):
                try:
                    llm_client = None
                    if openai and os.getenv('OPENAI_API_KEY'):
                        llm_client = openai.OpenAI()
                    
                    self.manual_controller = ManualTradingController(
                        config=config,
                        executor=None,  # Будет установлен позже
                        llm_client=llm_client
                    )
                    self.app_state.manual_trading_enabled = True
                    app_logger.info("[OK] Manual trading controller initialized")
                    # Логи по доступности AI-анализатора
                    if llm_client and self.manual_controller and self.manual_controller.ai_analyzer:
                        app_logger.info("[OK] AI analyzer (LLM) initialized and ready")
                    else:
                        app_logger.info("[INFO] AI analyzer not initialized — check OPENAI_API_KEY or config")
                except Exception as e:
                    app_logger.error(f"[ERROR] Manual trading init failed: {e}")
        
        # Состояние ручной торговли
        self.app_state.manual_trade_state = ManualTradeState()
        
        # MarketDataUpdater для обновления цен
        self.market_data_updater = MarketDataUpdater(
            mt5_manager=self.app_state.mt5_manager,
            manual_trade_state=self.app_state.manual_trade_state,
            update_callback=self._on_market_data_update
        )
        self.market_data_updater.start()
        # Интервал опроса MT5 в секундах (можно настроить)
        self.mt5_poll_interval = 1.0
        
        # Создание интерфейса
        self.create_ui()
        
        # (callback уже установлен в __init__) — не устанавливаем здесь повторно
        
        # Установка executor для manual controller
        if self.manual_controller and hasattr(self, 'app_state') and hasattr(self.app_state, 'live_trader') and self.app_state.live_trader:
            self.manual_controller.executor = self.app_state.live_trader.executor
        
        # Начальные логи
        self.log("[INFO] Приложение запущено")
        self.log("[INFO] Инициализация компонентов...")
        
        # Загрузка статистики
        self.load_stats()
    
    def _on_market_data_update(self):
        """Callback при обновлении рыночных данных."""
        try:
            state = self.app_state.manual_trade_state
            if state.direction == "buy":
                state.entry_price = state.ask_price
            elif state.direction == "sell":
                state.entry_price = state.bid_price
            else:
                state.entry_price = state.bid_price
            
            # Обновляем GUI в главном потоке
            if hasattr(self, 'manual_entry'):
                self.root.after(0, lambda: self.manual_entry.set(state.entry_price))
            
            # Пересчитываем если нужно
            self.root.after(0, self.update_manual_calculations)
            
        except Exception as e:
            self.log(f"[ERROR] Market data update error: {e}")
        
        # Установка callback для логов в GUI
        # (callback устанавливается в __init__, не нужно дублировать здесь)
    
    def _add_log_to_gui(self, message: str, level: str = "INFO"):
        """Callback для добавления логов в GUI с цветами."""
        try:
            # Проверяем, что root еще существует
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return
            # Вызываем в главном потоке
            self.root.after(0, lambda: self._insert_log_message(message, level))
        except Exception as e:
            print(f"GUI logging error: {e}")
    
    def _init_mt5_manager(self):
        """Инициализация MT5 Manager."""
        try:
            self.app_state.mt5_manager = MT5Manager()
            
            # Инициализируем MT5 с путем к терминалу из конфига
            mt5_config = self.app_state.get_mt5_config()
            terminal_path = mt5_config.get('terminal_path', '')
            
            if terminal_path and Path(terminal_path).exists():
                if self.app_state.mt5_manager.initialize(terminal_path):
                    app_logger.info(f"[OK] MT5 initialized with path: {terminal_path}")
                else:
                    app_logger.warning(f"[WARNING] Failed to initialize MT5 with path: {terminal_path}, trying without path")
                    if not self.app_state.mt5_manager.initialize():
                        app_logger.error("[ERROR] Failed to initialize MT5")
                        self.app_state.mt5_manager = None
            else:
                if self.app_state.mt5_manager.initialize():
                    app_logger.info("[OK] MT5 initialized without path")
                else:
                    app_logger.error("[ERROR] Failed to initialize MT5")
                    self.app_state.mt5_manager = None
                    
        except Exception as e:
            app_logger.error(f"[ERROR] Failed to initialize MT5 Manager: {e}")
            self.app_state.mt5_manager = None
    
    def _start_mt5_monitoring(self):
        """Запуск мониторинга статуса MT5."""
        def monitor():
            while True:
                try:
                    if not self.app_state.mt5_manager:
                        threading.Event().wait(5)
                        continue

                    connected = self.app_state.mt5_manager.is_connected()

                    # Если соединение отсутствует — обновим статус и ждём
                    if not connected:
                        if self.app_state.mt5_connected:
                            # Состояние поменялось на disconnected
                            self.app_state.update_mt5_status(False)
                            self.root.after(0, self.update_mt5_status)
                        threading.Event().wait(5)
                        continue

                    # Получаем актуальную информацию о счете каждый цикл
                    account_info = self.app_state.mt5_manager.get_account_info() or {}

                    # Обрабатываем баланс и equity
                    try:
                        new_balance = float(account_info.get('balance', self.app_state.stats.get('balance', 0.0)))
                    except Exception:
                        new_balance = float(self.app_state.stats.get('balance', 0.0))

                    try:
                        new_equity = float(account_info.get('equity', self.app_state.stats.get('equity', new_balance)))
                    except Exception:
                        new_equity = new_balance

                    old_balance = float(self.app_state.stats.get('balance', 0.0))
                    old_equity = float(self.app_state.stats.get('equity', old_balance))

                    # Обновляем внутренний флаг соединения и account_info всегда
                    self.app_state.mt5_connected = True
                    self.app_state.mt5_account_info = account_info

                    # Запускаем синхронизацию сделок из MT5 в background (если доступно)
                    try:
                        if hasattr(self.app_state.mt5_manager, 'start_trade_sync'):
                            self.app_state.mt5_manager.start_trade_sync()
                    except Exception:
                        pass

                    # Если баланс или equity изменились — обновляем AppState.stats и UI
                    if new_balance != old_balance or new_equity != old_equity:
                        # Записываем в статистику
                        self.app_state.stats['balance'] = new_balance
                        self.app_state.stats['equity'] = new_equity

                        # Вычисляем текущий (не реализованный) P&L как equity - balance
                        try:
                            pnl = new_equity - new_balance
                        except Exception:
                            pnl = 0.0

                        # Сохраняем нереализованный P&L отдельно, не затирая суммарный реализованный PnL
                        self.app_state.stats['unrealized_pnl'] = round(pnl, 2)

                        # Обновляем UI
                        self.app_state.update_mt5_status(True, account_info)
                        self.root.after(0, self.update_mt5_status)
                    else:
                        # Если ничего не изменилось — всё равно обновляем метки аккаунта периодически
                        self.root.after(0, self.update_mt5_status)

                    threading.Event().wait(self.mt5_poll_interval)

                except Exception as e:
                    app_logger.error(f"MT5 monitoring error: {e}")
                    threading.Event().wait(10)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        app_logger.info("MT5 monitoring started")

    def _on_bot_manager_update(self):
        """Callback when bot_manager stats change - sync to app_state and refresh UI."""
        try:
            if hasattr(self, 'bot_manager') and self.bot_manager:
                # copy stats to app_state
                try:
                    self.app_state.stats.update(self.bot_manager.stats)
                except Exception:
                    pass
                try:
                    self.update_display()
                except Exception:
                    pass
        except Exception:
            pass

    def _on_market_data_update(self):
        """Callback при обновлении рыночных данных."""
        # Обновляем GUI в главном потоке
        self.root.after(0, self._refresh_manual_trading_ui)

    def _refresh_manual_trading_ui(self):
        """Обновление UI ручной торговли."""
        if not self.app_state.manual_trade_state:
            return

        state = self.app_state.manual_trade_state

        # Обновляем лейблы расчетов
        try:
            # Получаем баланс
            account_balance = self.app_state.stats.get('balance', 100.0)

            # Расчет объема позиции
            if self.manual_controller and state.entry_price > 0 and state.stop_loss > 0:
                lot_size, calc_msg = self.manual_controller.calculator.calculate_lot_size(
                    symbol=state.symbol,
                    entry_price=state.entry_price,
                    stop_loss=state.stop_loss,
                    risk_amount=state.risk_amount,
                    account_balance=account_balance
                )
                state.set_lot_size(lot_size)

            # Расчет RR
            if state.entry_price > 0 and state.stop_loss > 0 and state.take_profit > 0:
                rr_ratio = self.manual_controller.calculator.calculate_rr_ratio(
                    entry_price=state.entry_price,
                    stop_loss=state.stop_loss,
                    take_profit=state.take_profit,
                    direction=state.direction
                )
                state.set_rr_ratio(rr_ratio)

            # Обновляем лейблы
            if hasattr(self, 'manual_lot_label'):
                self.manual_lot_label.config(text=f"Объем: {state.lot_size:.2f} лотов")
            if hasattr(self, 'manual_rr_label'):
                self.manual_rr_label.config(text=f"RR: {state.risk_reward_ratio:.2f}")

        except Exception as e:
            app_logger.error(f"Error refreshing manual trading UI: {e}")

    def load_settings(self):
        """Загрузка настроек из файла."""
        config_file = Path('data/config.json')
        self.enable_gpt = True  # По умолчанию включено
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.enable_gpt = config.get('enable_gpt', True)
            except:
                pass
    
    def _load_manual_config(self):
        """Загрузка конфига для manual trading."""
        try:
            import yaml
            with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('manual_trading', {})
        except Exception as e:
            self.log(f"Failed to load manual config: {e}")
            return {}
    
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
                result_label.config(text="[ERROR] Enter key", fg='#ff4757')
                return
                
            success, msg = license_manager.activate(key)
            
            if success:
                if save:
                    result_label.config(text=f"[OK] {msg}", fg='#00d4aa')
                    dialog.after(1500, dialog.destroy)
                else:
                    result_label.config(text=f"[INFO] {msg}", fg='#f39c12')
            else:
                result_label.config(text=f"[ERROR] {msg}", fg='#ff4757')
        
        # Тест без кнопки: просто используем activate(save=False) при необходимости
        
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
        
        # Загружаем настройки
        config_file = Path('data/config.json')
        current_config = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    current_config = json.load(f)
            except:
                pass
        
        # OpenAI API Key
        api_frame = tk.Frame(dialog, bg='#2a2a2a', relief='flat')
        api_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(api_frame, text="[AI] OpenAI API Key (for GPT filter)",
                font=('Arial', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', pady=(10, 5))
        
        tk.Label(api_frame, text="Получите ключ на https://platform.openai.com/api-keys",
                font=('Arial', 9),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(0, 10))
        
        # Настройка включения GPT
        gpt_enabled = tk.BooleanVar(value=current_config.get('enable_gpt', True))  # По умолчанию включено
        gpt_check = tk.Checkbutton(api_frame, text="Включить GPT фильтр новостей",
                                  variable=gpt_enabled,
                                  font=('Arial', 10),
                                  bg='#2a2a2a', fg='white',
                                  selectcolor='#1a1a1a', activebackground='#2a2a2a',
                                  activeforeground='white')
        gpt_check.pack(anchor='w', pady=(0, 10))
        
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
                status_label.config(text="[ERROR] Key not entered", fg='#ff4757')
                return
            
            if openai is None:
                status_label.config(text="[ERROR] OpenAI library not installed", fg='#ff4757')
                return
            
            # Тестируем ключ
            try:
                client = openai.OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                status_label.config(text="[OK] Key works!", fg='#00d4aa')
            except Exception as e:
                status_label.config(text=f"[ERROR] Error: {str(e)[:50]}", fg='#ff4757')
        
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
                    status_label.config(text="[OK] License reset! Restart the program.", fg='#00d4aa')
                else:
                    status_label.config(text="ℹ️ Лицензия не найдена", fg='#f39c12')
            except Exception as e:
                status_label.config(text=f"[ERROR] Reset error: {e}", fg='#ff4757')
        
        tk.Button(license_frame, text="[RESET] Reset license",
                 font=('Arial', 10, 'bold'),
                 bg='#ff4757', fg='white',
                 command=reset_license,
                 width=15, height=1,
                 relief='flat', cursor='hand2').pack(pady=(0, 10))
        
        tk.Label(license_frame, text="[WARNING] After reset, restart the program for activation testing",
                font=('Arial', 8),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(0, 10))
        
        # Кнопки
        btn_frame = tk.Frame(dialog, bg='#1a1a1a')
        btn_frame.pack(fill='x', padx=20, pady=20)
        
        def save_settings():
            key = api_entry.get().strip()
            gpt_enabled_val = gpt_enabled.get()
            
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
                    
                    status_label.config(text="[OK] Settings saved!", fg='#00d4aa')
                    
                except Exception as e:
                    status_label.config(text=f"[ERROR] Save error: {e}", fg='#ff4757')
            else:
                status_label.config(text="ℹ️ Ключ очищен", fg='#f39c12')
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']
            
            # Сохраняем настройку GPT
            config_file = Path('data/config.json')
            config_file.parent.mkdir(exist_ok=True)
            try:
                config = {}
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                
                config['enable_gpt'] = gpt_enabled_val
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                # Обновляем настройку в классе
                self.enable_gpt = gpt_enabled_val

                # Если ключ указан — попробуем инициализировать AI-анализатор в рантайме
                if key and openai is not None:
                    try:
                        # Создаем клиент LLM с ключом
                        try:
                            llm_client = openai.OpenAI(api_key=key)
                        except TypeError:
                            # fallback: some openai versions expect env var only
                            llm_client = openai.OpenAI()

                        # Если контроллер ручной торговли уже создан — подцепим анализатор
                        if getattr(self, 'manual_controller', None):
                            try:
                                from src.manual_trading.ai_analyzer import ManualAIAnalyzer
                                self.manual_controller.llm_client = llm_client
                                self.manual_controller.ai_analyzer = ManualAIAnalyzer(llm_client, self.manual_controller.config)
                                app_logger.info("[OK] AI analyzer initialized at runtime")
                                status_label.config(text="[OK] GPT initialized", fg='#00d4aa')
                            except Exception as e:
                                status_label.config(text=f"[ERROR] AI init failed: {e}", fg='#ff4757')
                        else:
                            status_label.config(text="[OK] Key saved - restart app to enable GPT", fg='#00d4aa')
                    except Exception as e:
                        status_label.config(text=f"[ERROR] OpenAI init: {e}", fg='#ff4757')
                else:
                    if not key:
                        status_label.config(text="[OK] GPT settings saved!", fg='#00d4aa')
                    
            except Exception as e:
                status_label.config(text=f"[ERROR] GPT settings save error: {e}", fg='#ff4757')
        
        tk.Button(btn_frame, text="💾 Сохранить",
                 font=('Arial', 11, 'bold'),
                 bg='#00d4aa', fg='black',
                 command=save_settings,
                 width=12, height=2,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="[CANCEL] Cancel",
                 font=('Arial', 11, 'bold'),
                 bg='#ff4757', fg='white',
                 command=dialog.destroy,
                 width=12, height=2,
                 relief='flat', cursor='hand2').pack(side='right', padx=5)
    
    def show_mt5_dialog(self):
        """Окно настроек MT5."""
        dialog = tk.Toplevel(self.root)
        dialog.title("MT5 Настройки")
        dialog.geometry("500x400")
        dialog.configure(bg='#1a1a1a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем
        dialog.geometry("+%d+%d" % (
            self.root.winfo_screenwidth() / 2 - 250,
            self.root.winfo_screenheight() / 2 - 200
        ))
        
        tk.Label(dialog, text="[MT5] MetaTrader 5 Settings",
                font=('Arial', 16, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=20)
        
        # Получаем текущие настройки
        mt5_config = self.app_state.get_mt5_config()
        
        # Фрейм для полей ввода
        input_frame = tk.Frame(dialog, bg='#1a1a1a')
        input_frame.pack(pady=10, padx=20, fill='x')
        
        # Login
        tk.Label(input_frame, text="Login:",
                font=('Arial', 11),
                bg='#1a1a1a', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        
        login_var = tk.StringVar(value=str(mt5_config.get('login', '')))
        login_entry = tk.Entry(input_frame, textvariable=login_var,
                              font=('Arial', 11), bg='#2a2a2a', fg='white',
                              insertbackground='white', width=30)
        login_entry.grid(row=0, column=1, pady=5, padx=(10, 0), sticky='ew')
        
        # Password
        tk.Label(input_frame, text="Password:",
                font=('Arial', 11),
                bg='#1a1a1a', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        
        password_var = tk.StringVar(value=mt5_config.get('password', ''))
        password_entry = tk.Entry(input_frame, textvariable=password_var, show='*',
                                 font=('Arial', 11), bg='#2a2a2a', fg='white',
                                 insertbackground='white', width=30)
        password_entry.grid(row=1, column=1, pady=5, padx=(10, 0), sticky='ew')
        
        # Server
        tk.Label(input_frame, text="Server:",
                font=('Arial', 11),
                bg='#1a1a1a', fg='white').grid(row=2, column=0, sticky='w', pady=5)
        
        server_var = tk.StringVar(value=mt5_config.get('server', ''))
        server_entry = tk.Entry(input_frame, textvariable=server_var,
                               font=('Arial', 11), bg='#2a2a2a', fg='white',
                               insertbackground='white', width=30)
        server_entry.grid(row=2, column=1, pady=5, padx=(10, 0), sticky='ew')
        
        # Terminal Path
        tk.Label(input_frame, text="Terminal Path:",
                font=('Arial', 11),
                bg='#1a1a1a', fg='white').grid(row=3, column=0, sticky='w', pady=5)
        
        terminal_var = tk.StringVar(value=mt5_config.get('terminal_path', ''))
        terminal_entry = tk.Entry(input_frame, textvariable=terminal_var,
                                 font=('Arial', 11), bg='#2a2a2a', fg='white',
                                 insertbackground='white', width=30)
        terminal_entry.grid(row=3, column=1, pady=5, padx=(10, 0), sticky='ew')
        
        # Кнопка выбора файла
        def browse_terminal():
            path = filedialog.askopenfilename(
                title="Выберите terminal64.exe",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if path:
                terminal_var.set(path)
        
        browse_btn = tk.Button(input_frame, text="📁", command=browse_terminal,
                              font=('Arial', 10), bg='#4a4a4a', fg='white',
                              width=3, relief='flat', cursor='hand2')
        browse_btn.grid(row=3, column=2, padx=(5, 0))
        
        # Статус
        status_var = tk.StringVar(value="Статус: Проверка...")
        status_label = tk.Label(dialog, textvariable=status_var,
                               font=('Arial', 10),
                               bg='#1a1a1a', fg='#888888')
        status_label.pack(pady=10)
        
        def update_status():
            if self.app_state.mt5_connected:
                account_info = self.app_state.mt5_account_info
                status_var.set(f"[CONNECTED] Connected: {account_info.get('login', 'N/A')}")
                status_label.config(fg='#00d4aa')
            else:
                status_var.set("[DISCONNECTED] Not connected")
                status_label.config(fg='#ff4757')
        
        update_status()
        
        # Функции подключения
        def connect_mt5():
            try:
                login = int(login_var.get())
                password = password_var.get()
                server = server_var.get()
                
                if not all([login, password, server]):
                    messagebox.showerror("Ошибка", "Заполните все поля!")
                    return
                
                self.log(f"🔌 Попытка подключения к MT5: {login}@{server}")
                
                success, message = self.app_state.mt5_manager.connect(login, password, server)
                
                if success:
                    # Предлагаем сохранить настройки
                    if messagebox.askyesno("Сохранение", "Сохранить учётные данные MT5 для автоматической загрузки?"):
                        try:
                            self.save_mt5_credentials(login, password, server, terminal_var.get())
                            self.log("[OK] MT5 credentials saved")
                        except Exception as save_error:
                            self.log(f"[WARNING] Failed to save data: {save_error}")
                    
                    self.log(f"[OK] MT5 connected: {message}")
                    messagebox.showinfo("Успех", f"Подключено!\n{message}")
                else:
                    self.log(f"[ERROR] MT5 error: {message}")
                    messagebox.showerror("Ошибка", message)
                
                update_status()
                
            except ValueError:
                messagebox.showerror("Ошибка", "Login должен быть числом!")
            except Exception as e:
                self.log(f"[ERROR] Connection error: {e}")
                messagebox.showerror("Ошибка", f"Ошибка подключения:\n{str(e)}")
        
        def reconnect_mt5():
            if self.app_state.mt5_manager:
                self.app_state.mt5_manager.disconnect()
                self.app_state.update_mt5_status(False)
                update_status()
                self.log("🔌 MT5 отключен")
            
            # Пауза перед переподключением
            dialog.after(1000, connect_mt5)
        
        # Кнопки
        btn_frame = tk.Frame(dialog, bg='#1a1a1a')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="🔌 Подключиться",
                 font=('Arial', 11, 'bold'),
                 bg='#00d4aa', fg='black',
                 command=connect_mt5,
                 width=15, height=2,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="[RECONNECT] Reconnect",
                 font=('Arial', 11, 'bold'),
                 bg='#f39c12', fg='black',
                 command=reconnect_mt5,
                 width=15, height=2,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="[CLOSE] Close",
                 font=('Arial', 11, 'bold'),
                 bg='#ff4757', fg='white',
                 command=dialog.destroy,
                 width=12, height=2,
                 relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        # Обновляем статус каждые 2 секунды
        def periodic_update():
            if dialog.winfo_exists():
                update_status()
                dialog.after(2000, periodic_update)
        
        periodic_update()
    
    def save_mt5_config(self):
        """Сохранение MT5 конфига."""
        config_file = Path('data/mt5_config.json')
        config_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.app_state.get_mt5_config(), f, indent=2)
            app_logger.info("MT5 config saved")
        except Exception as e:
            app_logger.error(f"Failed to save MT5 config: {e}")
    
    def load_mt5_config(self):
        """Загрузка MT5 конфига."""
        config_file = Path('data/mt5_config.json')
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.app_state.set_mt5_config(config)
                    app_logger.info("MT5 config loaded")
            except Exception as e:
                app_logger.error(f"Failed to load MT5 config: {e}")
    
    def create_manual_trading_section(self):
        """Создание секции ручной торговли."""
        # Контейнер с двумя колонками: слева - manual controls, справа - мини-логи
        manual_container = tk.Frame(self.root, bg='#1a1a1a')
        manual_container.pack(fill='both', expand=True, padx=20, pady=10)

        manual_frame = tk.Frame(manual_container, bg='#1a1a1a')
        manual_frame.pack(side='left', fill='both', expand=True)

        # Заголовок
        header = tk.Frame(manual_frame, bg='#2a2a2a')
        header.pack(fill='x', pady=(0, 10))

        tk.Label(header, text="[MANUAL] MANUAL TRADING (EXPERIMENTAL)",
                font=('Arial', 14, 'bold'),
                bg='#2a2a2a', fg='#00d4aa').pack(pady=10)

        # Основная форма
        form_frame = tk.Frame(manual_frame, bg='#1a1a1a')
        form_frame.pack(fill='x')

        # Левая колонка - параметры
        left_frame = tk.Frame(form_frame, bg='#1a1a1a')
        left_frame.pack(side='left', fill='y', padx=(0, 10))

        # Symbol selector
        symbol_frame = tk.Frame(left_frame, bg='#2a2a2a', relief='flat')
        symbol_frame.pack(fill='x', pady=5)

        tk.Label(symbol_frame, text="Инструмент:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)

        state = self.app_state.manual_trade_state
        self.manual_symbol = tk.StringVar(value=state.symbol)
        symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.manual_symbol,
                                   values=['EURUSD', 'XAUUSD'],
                                   state='readonly', font=('Arial', 10))
        symbol_combo.pack(padx=10, pady=(0, 10))
        symbol_combo.configure(background='#0f0f0f', foreground='white')
        symbol_combo.bind('<<ComboboxSelected>>', self._on_symbol_change)

        # Timeframe selector
        timeframe_frame = tk.Frame(left_frame, bg='#2a2a2a', relief='flat')
        timeframe_frame.pack(fill='x', pady=5)

        tk.Label(timeframe_frame, text="Таймфрейм:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)

        self.manual_timeframe = tk.StringVar(value=state.timeframe)
        tf_combo = ttk.Combobox(timeframe_frame, textvariable=self.manual_timeframe,
                               values=['M15', 'H1', 'H4', 'D1'],
                               state='readonly', font=('Arial', 10))
        tf_combo.pack(padx=10, pady=(0, 10))
        tf_combo.configure(background='#0f0f0f', foreground='white')
        tf_combo.bind('<<ComboboxSelected>>', self._on_timeframe_change)
        
        # Direction
        direction_frame = tk.Frame(left_frame, bg='#2a2a2a', relief='flat')
        direction_frame.pack(fill='x', pady=5)
        
        tk.Label(direction_frame, text="Направление:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        tk.Label(direction_frame, text="Направление:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        self.manual_direction = tk.StringVar(value=state.direction)
        tk.Radiobutton(direction_frame, text="Покупка", variable=self.manual_direction,
                      value='buy', bg='#2a2a2a', fg='white',
                      selectcolor='#1a1a1a', activebackground='#2a2a2a',
                      font=('Arial', 10), command=self._on_direction_change).pack(anchor='w', padx=20)
        tk.Radiobutton(direction_frame, text="Продажа", variable=self.manual_direction,
                      value='sell', bg='#2a2a2a', fg='white',
                      selectcolor='#1a1a1a', activebackground='#2a2a2a',
                      font=('Arial', 10), command=self._on_direction_change).pack(anchor='w', padx=20, pady=(0, 10))
        
        # AI Chat button under direction block (larger, left)
        self.btn_ai_chat = tk.Button(direction_frame, text="💬 Чат с аналитиком",
                         command=self.open_ai_chat,
                         font=('Arial', 11, 'bold'),
                         bg='#4a90e2', fg='white',
                         width=20, height=2,
                         relief='flat', cursor='hand2')
        self.btn_ai_chat.pack(anchor='w', padx=10, pady=(0, 10))
        
        # Правая колонка - уровни и риск
        right_frame = tk.Frame(form_frame, bg='#1a1a1a')
        right_frame.pack(side='left', fill='y', padx=(10, 0))
        
        # Entry Price
        entry_frame = tk.Frame(right_frame, bg='#2a2a2a', relief='flat')
        entry_frame.pack(fill='x', pady=5)
        
        tk.Label(entry_frame, text="Цена входа:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        self.manual_entry = tk.DoubleVar(value=state.entry_price)
        entry_spin = tk.Spinbox(entry_frame, from_=0, to=10000, increment=0.0001,
                               textvariable=self.manual_entry, font=('Arial', 10),
                               bg='#0f0f0f', fg='white', insertbackground='white',
                               buttonbackground='#2a2a2a', command=self._on_price_change)
        entry_spin.pack(padx=10, pady=(0, 10), fill='x')
        entry_spin.bind('<FocusOut>', self._on_price_change)
        
        # Stop Loss
        sl_frame = tk.Frame(right_frame, bg='#2a2a2a', relief='flat')
        sl_frame.pack(fill='x', pady=5)
        
        tk.Label(sl_frame, text="Stop Loss:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        self.manual_sl = tk.DoubleVar(value=state.stop_loss)
        sl_spin = tk.Spinbox(sl_frame, from_=0, to=10000, increment=0.0001,
                            textvariable=self.manual_sl, font=('Arial', 10),
                            bg='#0f0f0f', fg='white', insertbackground='white',
                            buttonbackground='#2a2a2a', command=self._on_price_change)
        sl_spin.pack(padx=10, pady=(0, 10), fill='x')
        sl_spin.bind('<FocusOut>', self._on_price_change)
        
        # Take Profit
        tp_frame = tk.Frame(right_frame, bg='#2a2a2a', relief='flat')
        tp_frame.pack(fill='x', pady=5)
        
        tk.Label(tp_frame, text="Take Profit:",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        self.manual_tp = tk.DoubleVar(value=state.take_profit)
        tp_spin = tk.Spinbox(tp_frame, from_=0, to=10000, increment=0.0001,
                            textvariable=self.manual_tp, font=('Arial', 10),
                            bg='#0f0f0f', fg='white', insertbackground='white',
                            buttonbackground='#2a2a2a', command=self._on_price_change)
        tp_spin.pack(padx=10, pady=(0, 10), fill='x')
        tp_spin.bind('<FocusOut>', self._on_price_change)
        
        # Risk-Reward (RR) ratio
        rr_frame = tk.Frame(right_frame, bg='#2a2a2a', relief='flat')
        rr_frame.pack(fill='x', pady=5)

        tk.Label(rr_frame, text="РР (RR):",
            font=('Arial', 10, 'bold'),
            bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)

        # RR as numeric ratio (e.g. 2.0 for 2:1)
        initial_rr = getattr(state, 'risk_reward_ratio', 1.0) or 1.0
        self.manual_rr_ratio = tk.DoubleVar(value=initial_rr)
        rr_spin = tk.Spinbox(rr_frame, from_=0.1, to=10.0, increment=0.1,
                     textvariable=self.manual_rr_ratio, format="%.1f",
                     font=('Arial', 10), bg='#0f0f0f', fg='white',
                     insertbackground='white', buttonbackground='#2a2a2a',
                     command=self._on_rr_change)
        rr_spin.pack(padx=10, pady=(0, 10), fill='x')
        rr_spin.bind('<FocusOut>', self._on_rr_change)
        
        # Risk
        risk_frame = tk.Frame(right_frame, bg='#2a2a2a', relief='flat')
        risk_frame.pack(fill='x', pady=5)
        
        tk.Label(risk_frame, text="Риск (% или $):",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=5)
        
        self.manual_risk = tk.DoubleVar(value=state.risk_amount)
        risk_spin = tk.Spinbox(risk_frame, from_=0, to=100, increment=0.1,
                              textvariable=self.manual_risk, font=('Arial', 10),
                              bg='#0f0f0f', fg='white', insertbackground='white',
                              buttonbackground='#2a2a2a', command=self._on_price_change)
        risk_spin.pack(padx=10, pady=(0, 10), fill='x')
        risk_spin.bind('<FocusOut>', self._on_price_change)

        # Быстрые действия (дублирующие кнопки, видимые рядом с полями)
        quick_action_frame = tk.Frame(right_frame, bg='#1a1a1a')
        quick_action_frame.pack(fill='x', pady=(10, 0))

        # quick Predict removed; keep Open quick

        self.btn_open_quick = tk.Button(quick_action_frame, text="[OPEN] Open",
                        command=self.manual_open_trade,
                        font=('Arial', 10, 'bold'),
                        bg='#00d4aa', fg='black',
                        width=10, height=1,
                        relief='flat', cursor='hand2', state='disabled')
        self.btn_open_quick.pack(side='left', padx=5)
        
        # Кнопки
        buttons_frame = tk.Frame(manual_frame, bg='#1a1a1a')
        buttons_frame.pack(fill='x', pady=10)
        
        # Левая часть - расчеты
        calc_frame = tk.Frame(buttons_frame, bg='#1a1a1a')
        calc_frame.pack(side='left')
        
        # Авторасчет
        self.manual_lot_label = tk.Label(calc_frame, text="Объем: --",
                                        font=('Arial', 10),
                                        bg='#1a1a1a', fg='#888888')
        self.manual_lot_label.pack(anchor='w', pady=2)
        
        self.manual_rr_label = tk.Label(calc_frame, text="RR: --",
                                       font=('Arial', 10),
                                       bg='#1a1a1a', fg='#888888')
        self.manual_rr_label.pack(anchor='w', pady=2)
        
        # Правая часть - кнопки и мини-логи
        action_frame = tk.Frame(buttons_frame, bg='#1a1a1a')
        # Размещаем блок кнопок слева в рамках buttons_frame, рядом с расчетами
        action_frame.pack(side='left', padx=(20, 0))
        action_frame.pack_propagate(False)
        
        # Predict button removed from main actions (use AI Chat)
        
        # Кнопка открытия сделки
        self.btn_open_trade = tk.Button(action_frame, text="[OPEN] Open trade",
                                       command=self.manual_open_trade,
                                       font=('Arial', 11, 'bold'),
                                       bg='#00d4aa', fg='black',
                                       width=15, height=2,
                                       relief='flat', cursor='hand2',
                                       state='disabled')
        self.btn_open_trade.pack(side='left', padx=5)
        
        # Большая панель быстрых действий (Open / Close) — располагается между кнопками и мини-логами
        trade_control_frame = tk.Frame(manual_container, bg='#1a1a1a')
        trade_control_frame.pack(side='right', padx=(10, 0), pady=(10, 0))

        self.btn_big_open = tk.Button(trade_control_frame, text='ОТКРЫТЬ\nСДЕЛКУ', command=self.manual_open_trade,
                          font=('Arial', 12, 'bold'), bg='#00d4aa', fg='black',
                          width=14, height=3, relief='flat', cursor='hand2', state='disabled')
        self.btn_big_open.pack(padx=5, pady=(0, 8))

        self.btn_big_close = tk.Button(trade_control_frame, text='ЗАКРЫТЬ\nСДЕЛКУ', command=self.manual_close_trade,
                           font=('Arial', 12, 'bold'), bg='#ff5c5c', fg='black',
                           width=14, height=3, relief='flat', cursor='hand2', state='disabled')
        self.btn_big_close.pack(padx=5)
        # Мини-логи правее кнопок — делаем дочерним элементом manual_container
        mini_logs_frame = customtkinter.CTkFrame(manual_container, height=800, width=520, fg_color="#1a1a1a")
        mini_logs_frame.pack(side='right', padx=(30, 0), pady=(10, 0), fill='y')  # Отдельный фрейм правее с отступом сверху
        mini_logs_frame.pack_propagate(False)  # Фиксированная высота

        tk.Label(mini_logs_frame, text="Логи:",
            font=('Arial', 12, 'bold'),
            bg='#1a1a1a', fg='white').pack(anchor='w', padx=10, pady=(10, 5))

        self.mini_logs_text = tk.Text(mini_logs_frame, height=20, width=120,
                         bg='#0f0f0f', fg='white',
                         font=('Consolas', 11),
                         relief='flat', state='disabled')
        self.mini_logs_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Цветные теги для мини-логов
        self.mini_logs_text.tag_config("info", foreground="#ffffff")  # Ярко-белый
        self.mini_logs_text.tag_config("warning", foreground="#ffff00", background="#333300")  # Ярко-желтый с темным фоном
        self.mini_logs_text.tag_config("error", foreground="#ff4444", background="#330000")  # Ярко-красный с темным фоном
        self.mini_logs_text.tag_config("critical", foreground="#ff0000", background="#220000")  # Ярко-красный с темным фоном
        self.ai_result_text = tk.Text(manual_frame, height=6,
                                     bg='#0f0f0f', fg='#00d4aa',
                                     font=('Consolas', 9),
                                     relief='flat', state='disabled')
        self.ai_result_text.pack(fill='x', pady=(10, 0))
    
    def update_manual_calculations(self):
        """Расчет лота и RR с полной валидацией."""
        try:
            state = self.app_state.manual_trade_state
            symbol = state.symbol
            entry = state.entry_price
            sl = state.stop_loss
            tp = state.take_profit
            risk = state.risk_amount
            direction = state.direction
            
            # Валидация входных данных
            if entry <= 0:
                self.log("Cannot calculate: entry price must be > 0")
                self.manual_lot_label.config(text="Volume: --")
                self.manual_rr_label.config(text="RR: --")
                return
                
            price_diff = abs(entry - sl)
            # Минимальная допустимая дистанция SL рассчитывается динамически:
            # - как половина текущего спреда (если есть), или
            # - как небольшая доля от цены (1e-5), чтобы учитывать инструменты с разной ценовой шкалой
            spread = getattr(state, 'spread', 0.0) or 0.0
            # Настраиваемые параметры из config/portfolio.yaml (manual_trading)
            cfg = getattr(self, 'manual_config', {}) or {}
            price_fraction = float(cfg.get('min_sl_price_fraction', 1e-5))
            spread_factor = float(cfg.get('min_sl_spread_half', 0.5))
            min_distance = max(spread * spread_factor, abs(entry) * price_fraction, 1e-8)
            if price_diff < min_distance:
                self.log(
                    f"Cannot calculate: invalid SL (too close to entry). "
                    f"price_diff={price_diff:.8f}, min_distance={min_distance:.8f}"
                )
                self.manual_lot_label.config(text="Volume: --")
                self.manual_rr_label.config(text="RR: --")
                return
            
            account_balance = self.app_state.stats.get('balance', 100.0)
            if account_balance <= 0:
                self.log("Cannot calculate: account balance unavailable")
                self.manual_lot_label.config(text="Volume: --")
                self.manual_rr_label.config(text="RR: --")
                return
            
            # Расчет объема позиции
            try:
                # Простой расчет: risk / price_diff * account_balance / 100
                lot_size = (risk / price_diff) / account_balance * 100
                lot_size = round(lot_size / 0.01) * 0.01
                lot_size = max(0.01, min(lot_size, 1.0))
            except ZeroDivisionError:
                self.log("Cannot calculate lot: division by zero")
                lot_size = 0.0
            
            # Расчет RR
            try:
                if direction == 'buy':
                    rr_ratio = abs(tp - entry) / price_diff
                else:
                    rr_ratio = abs(entry - tp) / price_diff
            except ZeroDivisionError:
                rr_ratio = 0.0
            
            # Обновление GUI
            if lot_size > 0:
                self.manual_lot_label.config(text=f"Volume: {lot_size:.2f} lots")
            else:
                self.manual_lot_label.config(text="Volume: --")
                
            if rr_ratio > 0:
                self.manual_rr_label.config(text=f"RR: {rr_ratio:.2f}")
            else:
                self.manual_rr_label.config(text="RR: --")
            
            # Включаем/отключаем кнопки открытия сделки в зависимости от валидности
            try:
                valid = state.is_valid()
            except Exception:
                valid = False

            if hasattr(self, 'btn_open_trade'):
                self.btn_open_trade.config(state='normal' if valid else 'disabled')
            if hasattr(self, 'btn_open_quick'):
                self.btn_open_quick.config(state='normal' if valid else 'disabled')
            if hasattr(self, 'btn_big_open'):
                self.btn_big_open.config(state='normal' if valid else 'disabled')

            # Enable close button only if an executor has an open position
            close_state = 'disabled'
            try:
                exec_obj = getattr(self.manual_controller, 'executor', None)
                if exec_obj and getattr(exec_obj, 'has_position', lambda: False)():
                    close_state = 'normal'
            except Exception:
                close_state = 'disabled'

            if hasattr(self, 'btn_big_close'):
                self.btn_big_close.config(state=close_state)
            
        except Exception as e:
            self.log(f"Critical calculation error: {e}")
            self.manual_lot_label.config(text="Volume: --")
            self.manual_rr_label.config(text="RR: --")
    
    def manual_predict(self):
        """AI анализ для ручной торговли."""
        if not self.manual_controller:
            self.log("[ERROR] Manual trading controller not available")
            return
        # Не запускаем автоматические пересчёты полей здесь — только собираем текущий контекст
        
        # Собираем расширенный контекст из состояния и приложения
        state = self.app_state.manual_trade_state
        # Base state dict
        context = state.to_dict() if hasattr(state, 'to_dict') else {
            'symbol': state.symbol,
            'timeframe': state.timeframe,
            'direction': state.direction,
            'entry_price': state.entry_price,
            'stop_loss': state.stop_loss,
            'take_profit': state.take_profit,
            'risk_amount': state.risk_amount,
            'lot_size': state.lot_size,
        }

        # Add account and environment info
        context['account_balance'] = float(self.app_state.stats.get('balance', 0.0))
        context['account_equity'] = float(self.app_state.stats.get('equity', context.get('entry_price', 0.0)))
        context['timestamp'] = datetime.now().isoformat()

        # Market hints
        bid = getattr(state, 'bid_price', 0.0)
        ask = getattr(state, 'ask_price', 0.0)
        spread = getattr(state, 'spread', 0.0)
        context['bid'] = bid
        context['ask'] = ask
        context['spread'] = spread

        # Simple volatility proxy: spread relative to price
        try:
            context['volatility_est'] = round((spread / max(ask, 1e-6)) * 10000, 4)
        except Exception:
            context['volatility_est'] = 0.0

        # Price distance to entry
        try:
            context['price_distance'] = round(abs((context.get('entry_price', 0.0) - ((bid+ask)/2)) ), 6)
        except Exception:
            context['price_distance'] = 0.0

        # Fallback placeholders for advanced signals
        context.setdefault('smc_structure', 'Не определена')
        context.setdefault('ml_bias', 'Нейтральный')
        context.setdefault('ml_confidence', 0.5)
        context.setdefault('news_status', 'Нет важных новостей')
        
        # Проверяем доступность AI анализатора и конфигурацию
        if not getattr(self.manual_controller, 'ai_analyzer', None):
            self.log("[ERROR] AI analyzer not available. Check OPENAI_API_KEY and manual config.")
            return

        if not self.manual_controller.config.get('ENABLE_MANUAL_AI_PREDICT', False):
            self.log("[INFO] AI prediction is disabled in manual trading config")
            return

        self.log(f"🔮 Запуск AI анализа для {context['symbol']} {context['direction'].upper()}")

        # Запускаем анализ в отдельном потоке
        def analyze():
            prediction = self.manual_controller.get_ai_prediction(context)
            if prediction:
                self.root.after(0, lambda: self.display_ai_prediction(prediction))
            else:
                self.root.after(0, lambda: self.log("[ERROR] AI analysis failed"))

        threading.Thread(target=analyze, daemon=True).start()
    
    def display_ai_prediction(self, prediction: AIPrediction):
        """Отображение AI прогноза."""
        if not MANUAL_TRADING_AVAILABLE or not AIPrediction:
            return
        self.ai_result_text.config(state='normal')
        self.ai_result_text.delete(1.0, tk.END)
        # Build a concise but informative explanation for the user
        scenarios_best = prediction.scenarios.get('best_case', 'N/A') if getattr(prediction, 'scenarios', None) else 'N/A'
        scenarios_worst = prediction.scenarios.get('worst_case', 'N/A') if getattr(prediction, 'scenarios', None) else 'N/A'
        invalids = ', '.join(prediction.invalidation_levels) if getattr(prediction, 'invalidation_levels', None) else 'N/A'

        # Extract helpful context hints (if present)
        ctx = getattr(prediction, 'context', {}) or {}
        ml_bias = ctx.get('ml_bias', 'N/A')
        ml_conf = ctx.get('ml_confidence', 'N/A')
        news = ctx.get('news_status', 'N/A')
        smc = ctx.get('smc_structure', 'N/A')

        # Переводы для стандартных полей прогноза
        bias_map = {'bullish': 'бычий', 'bearish': 'медвежий', 'range': 'флэт'}
        align_map = {'aligned': 'совпадает', 'neutral': 'нейтрально', 'risky': 'рискованно'}
        conf_map = {'low': 'низкая', 'medium': 'средняя', 'high': 'высокая'}

        bias_rus = bias_map.get(prediction.market_bias, prediction.market_bias)
        align_rus = align_map.get(prediction.trade_alignment, prediction.trade_alignment)
        conf_rus = conf_map.get(prediction.confidence, prediction.confidence)

        result = (
            f"[AI] AI FORECAST\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Рыночный тренд: {bias_rus}\n"
            f"Совпадение со сделкой: {align_rus}\n"
            f"Уверенность: {conf_rus}\n\n"
            "Короткое объяснение (почему такой прогноз):\n"
            f"- ML сигнал: {ml_bias} (conf {ml_conf})\n"
            f"- Новости: {news}\n"
            f"- SMC структура: {smc}\n\n"
            "Ключевые сценарии:\n"
            f"• Лучший: {scenarios_best}\n"
            f"• Худший: {scenarios_worst}\n\n"
            f"Уровни отмены: {invalids}\n\n"
            f"Комментарий: {prediction.comment}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        self.ai_result_text.insert(1.0, result)
        self.ai_result_text.config(state='disabled')
        
        # Log a concise Russian message for console + GUI logs
        try:
            bias_map = {'bullish': 'бычий', 'bearish': 'медвежий', 'range': 'флэт'}
            conf_map = {'low': 'низкая', 'medium': 'средняя', 'high': 'высокая'}
            bias_txt = bias_map.get(prediction.market_bias, prediction.market_bias)
            conf_txt = conf_map.get(prediction.confidence, prediction.confidence)
            short_reason = prediction.comment if getattr(prediction, 'comment', None) else ''
            self.log(f"[OK] AI прогноз: {bias_txt}, уверенность: {conf_txt}. {short_reason}")
        except Exception:
            self.log(f"[OK] AI forecast received: {prediction.market_bias}, confidence {prediction.confidence}")
    
    def open_ai_chat(self):
        """Open a simple AI chat window for analyst/assistant consultations."""
        try:
            win = tk.Toplevel(self.root)
            win.title("AI Analyst Chat")
            win.geometry("600x400")
            win.configure(bg='#1a1a1a')

            chat_box = tk.Text(win, bg='#0f0f0f', fg='white', font=('Consolas', 11))
            chat_box.pack(fill='both', expand=True, padx=10, pady=(10, 0))
            chat_box.insert('end', "AI Analyst chat initialized. Type a question below and press Send.\n")
            chat_box.config(state='disabled')

            entry_frame = tk.Frame(win, bg='#1a1a1a')
            entry_frame.pack(side='bottom', fill='x', padx=10, pady=10)

            entry_var = tk.StringVar()
            entry = tk.Entry(entry_frame, textvariable=entry_var, font=('Arial', 11), bg='#0f0f0f', fg='white', insertbackground='white')
            entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
            entry.config(state='normal')
            # ensure input is visible and focused
            win.update_idletasks()
            entry.focus_force()
            entry.lift()
            entry.bind('<Return>', lambda e: send_message())

            def send_message():
                msg = entry_var.get().strip()
                if not msg:
                    return
                entry_var.set('')
                chat_box.config(state='normal')
                chat_box.insert('end', f"You: {msg}\n")
                chat_box.see('end')
                # Build a small context
                context = {
                    'text': msg,
                    'symbol': getattr(self, 'manual_symbol', tk.StringVar(value='')).get() if hasattr(self, 'manual_symbol') else '',
                    'entry_price': getattr(self, 'manual_entry', tk.DoubleVar(value=0)).get() if hasattr(self, 'manual_entry') else 0,
                    'stop_loss': getattr(self, 'manual_sl', tk.DoubleVar(value=0)).get() if hasattr(self, 'manual_sl') else 0,
                    'take_profit': getattr(self, 'manual_tp', tk.DoubleVar(value=0)).get() if hasattr(self, 'manual_tp') else 0,
                    'direction': getattr(self, 'manual_direction', tk.StringVar(value='')).get() if hasattr(self, 'manual_direction') else ''
                }

                def do_query():
                    # Prefer controller AI prediction if available
                    response_text = None
                    try:
                        # If there is an LLM client configured, call it directly for free-form chat
                        llm = None
                        if getattr(self, 'manual_controller', None) and getattr(self.manual_controller, 'llm_client', None):
                            llm = self.manual_controller.llm_client
                        elif getattr(self, 'app_state', None) and getattr(self.app_state, 'llm_client', None):
                            llm = self.app_state.llm_client

                        if llm is not None:
                            try:
                                model = None
                                # prefer model from manual controller config
                                if getattr(self, 'manual_controller', None):
                                    model = self.manual_controller.config.get('AI_MODEL')
                                if not model:
                                    model = 'gpt-4o-mini'

                                # Build messages
                                messages = [
                                    {"role": "system", "content": "You are an experienced trading analyst. Answer concisely and helpfully."},
                                    {"role": "user", "content": msg}
                                ]

                                # Try OpenAI-like SDK call used elsewhere in project
                                try:
                                    resp = llm.chat.completions.create(model=model, messages=messages, max_tokens=800)
                                    content = None
                                    try:
                                        content = resp.choices[0].message.content
                                    except Exception:
                                        # Some SDKs return 'text' directly
                                        content = getattr(resp, 'text', None) or str(resp)
                                    if content:
                                        response_text = content
                                except Exception as e:
                                    # last-resort: try simple 'create' on llm
                                    try:
                                        resp = llm.Completion.create(model=model, prompt=msg, max_tokens=500)
                                        content = getattr(resp, 'text', None) or str(resp)
                                        response_text = content
                                    except Exception:
                                        response_text = None
                            except Exception:
                                response_text = None

                        # If no LLM or LLM failed, try controller AI analyzer (structured prediction)
                        if not response_text and getattr(self, 'manual_controller', None):
                            try:
                                if getattr(self.manual_controller, 'ai_analyzer', None):
                                    pred = self.manual_controller.get_ai_prediction(context)
                                    if pred:
                                        response_text = f"AI Prediction: {getattr(pred, 'market_bias', '')}, confidence {getattr(pred, 'confidence', '')}\n{getattr(pred, 'comment', '')}"
                            except Exception:
                                response_text = None

                        # Fallback simple rule-based responder
                        if not response_text:
                            if 'stop' in msg.lower() or 'risk' in msg.lower():
                                response_text = "Совет: проверьте расстояние SL от входа и размер риска. Рекомендуется RR >= 1.5."
                            elif 'open' in msg.lower() or 'вход' in msg.lower():
                                response_text = "Проверьте: направление, расстояние SL/TP, и объем позиции. Могу подготовить сделку по текущим полям."
                            else:
                                response_text = "AI недоступен — опишите вопрос по сделке (SL/TP/объем), или включите AI в настройках."

                    except Exception as e:
                        response_text = f"Ошибка AI: {e}"

                    # Post result back to UI
                    self.root.after(0, lambda: finish_response(response_text))

                def finish_response(text):
                    chat_box.insert('end', f"Analyst: {text}\n\n")
                    chat_box.config(state='disabled')
                    chat_box.see('end')

                threading.Thread(target=do_query, daemon=True).start()
                # return focus to entry when background thread completes
                entry.focus_force()

            send_btn = tk.Button(entry_frame, text='Send', command=send_message, font=('Arial', 11, 'bold'), bg='#00d4aa', fg='black')
            send_btn.pack(side='right')

        except Exception as e:
            self.log(f"[ERROR] open_ai_chat failed: {e}")
    
    def manual_open_trade(self):
        """Открытие ручной сделки с исправлением ошибки 'dict has no attribute 'source'."""
        if not self.manual_controller:
            self.log("[ERROR] Manual trading controller not available")
            return
        
        if self.app_state.bot_running:
            messagebox.showerror("Ошибка", "Нельзя открывать ручные сделки пока бот работает!")
            return
        
        if not self.app_state.can_execute_trades():
            messagebox.showerror("Ошибка", "MT5 не подключен!")
            return
        
        self.update_manual_calculations()
        
        state = self.app_state.manual_trade_state
        
        # Подготавливаем параметры для prepare_trade
        trade_params = {
            'symbol': str(state.symbol),
            'direction': str(state.direction),
            'entry_price': float(state.entry_price),
            'stop_loss': float(state.stop_loss),
            'take_profit': float(state.take_profit),
            'risk_amount': float(state.risk_amount)
        }
        
        self.log(f"[LAUNCH] Preparing manual trade: {trade_params}")
        
        try:
            # Сначала подготавливаем сделку
            success, message, trade_request = self.manual_controller.prepare_trade(
                trade_params, 
                self.app_state.stats.get('balance', 100.0)
            )
            
            if not success:
                self.log(f"[ERROR] Trade preparation failed: {message}")
                messagebox.showerror("Ошибка", f"Не удалось подготовить сделку:\n{message}")
                return
            
            self.log(f"[OK] Trade prepared: {message}")
            
            # Теперь исполняем
            # Если executor не установлен — попробуем создать временный Executor для live-режима
            if not getattr(self.manual_controller, 'executor', None):
                try:
                    from src.core.executor import Executor
                    if getattr(self.app_state, 'mt5_manager', None) and getattr(self.app_state.mt5_manager, 'mt5', None):
                        self.manual_controller.executor = Executor(mt5_connector=self.app_state.mt5_manager.mt5)
                        self.log("[OK] Temporary executor created for manual trade")
                except Exception as e:
                    self.log(f"[WARNING] Failed to create temporary executor: {e}")

            success, message = self.manual_controller.execute_trade(trade_request)
            
            if success:
                self.log(f"[OK] Manual trade opened: {message}")
                messagebox.showinfo("Успех", f"Сделка открыта!\n{message}")
                try:
                    if hasattr(self, 'btn_big_close'):
                        self.btn_big_close.config(state='normal')
                except Exception:
                    pass
            else:
                self.log(f"[ERROR] Trade failed: {message}")
                messagebox.showerror("Ошибка", f"Не удалось открыть сделку:\n{message}")
        except Exception as e:
            self.log(f"[CRITICAL] Trade execution error: {e}")
            messagebox.showerror("Ошибка", f"Критическая ошибка:\n{str(e)}")

    def manual_close_trade(self):
        """Закрыть текущую открытую ручную позицию (если есть)."""
        try:
            if not self.manual_controller:
                self.log("[ERROR] Manual trading controller not available")
                return

            executor = getattr(self.manual_controller, 'executor', None)
            if not executor:
                # Try to grab from app_state
                executor = getattr(self.app_state.live_trader, 'executor', None) if getattr(self, 'app_state', None) else None

            if not executor:
                self.log("[ERROR] Executor not available to close position")
                messagebox.showerror("Ошибка", "Executor не доступен для закрытия сделки")
                return

            if not executor.has_position():
                messagebox.showinfo("Инфо", "Нет открытой позиции для закрытия")
                return

            # Confirm
            if not messagebox.askyesno("Подтвердите", "Закрыть текущую позицию вручную?"):
                return

            # Determine current price
            symbol = None
            try:
                pos = getattr(executor, 'position', None)
                symbol = getattr(pos, 'instrument', None) or getattr(pos, 'symbol', None)
            except Exception:
                symbol = None

            current_price = None
            # Try MT5 tick if live
            if getattr(executor, 'is_live', False) and getattr(self, 'app_state', None) and getattr(self.app_state, 'mt5_manager', None):
                try:
                    mt5 = self.app_state.mt5_manager.mt5
                    if mt5 and symbol:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            current_price = getattr(tick, 'last', None) or getattr(tick, 'bid', None) or getattr(tick, 'ask', None)
                except Exception:
                    current_price = None

            if current_price is None:
                try:
                    current_price = executor._get_current_price(symbol or 'EURUSD')
                except Exception:
                    current_price = getattr(executor.position, 'entry_price', 0.0)

            from datetime import datetime
            pnl = None
            try:
                pnl = executor._close_position(float(current_price), datetime.now(), reason='manual_close')
            except Exception as e:
                self.log(f"[ERROR] Closing failed: {e}")
                messagebox.showerror("Ошибка", f"Не удалось закрыть позицию: {e}")
                return

            self.log(f"[OK] Position closed manually. PnL: {pnl}")
            messagebox.showinfo("Успех", f"Позиция закрыта. PnL: {pnl}")

            # Update buttons
            try:
                if hasattr(self, 'btn_big_close'):
                    self.btn_big_close.config(state='disabled')
            except Exception:
                pass

        except Exception as e:
            self.log(f"[CRITICAL] manual_close_trade error: {e}")
            messagebox.showerror("Ошибка", f"Критическая ошибка при закрытии: {e}")
    
    def create_stat_card(self, parent, title, value):
        """Создание карточки статистики."""
        frame = tk.Frame(parent, bg='#2a2a2a', relief='flat')
        
        title_label = tk.Label(frame, text=title,
                              font=('Arial', 10, 'bold'),
                              bg='#2a2a2a', fg='#888888')
        title_label.pack(pady=(10, 0))
        
        value_label = tk.Label(frame, text=value,
                              font=('Arial', 16, 'bold'),
                              bg='#2a2a2a', fg='white')
        value_label.pack(pady=(0, 10))
        
        frame.value_label = value_label
        return frame
    
    def create_ui(self):
        """Создание интерфейса."""
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg='#1a1a1a')
        header.pack(fill='x', padx=20, pady=10)
        
        # Логотип
        logo = tk.Label(header, text="[BOT] BAZA Trading Bot", 
                       font=('Arial', 20, 'bold'), 
                       bg='#1a1a1a', fg='white')
        logo.pack(side='left')
        
        # Лицензия
        license_info = license_manager.get_license_info()
        license_text = f"[LICENSE] {license_info.get('type', '').upper() or 'N/A'}" if license_info['valid'] else "[LOCKED] Not activated"
        
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
                                   text="[MT5] MT5: Not connected",
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
        
        # Кнопка MT5
        self.btn_mt5 = tk.Button(btn_frame, text="[MT5] MT5",
                                 command=self.show_mt5_dialog,
                                 font=('Arial', 10),
                                 bg='#5a5a5a', fg='white',
                                 width=8, height=2,
                                 relief='flat', cursor='hand2')
        self.btn_mt5.pack(side='left', padx=5)
        
        # Кнопка настроек
        self.btn_settings = tk.Button(btn_frame, text="⚙ Настройки",
                                      command=self.show_settings_dialog,
                                      font=('Arial', 10),
                                      bg='#4a4a4a', fg='white',
                                      width=10, height=2,
                                      relief='flat', cursor='hand2')
        self.btn_settings.pack(side='left', padx=5)
        
        # Режим (фиксирован на Live)
        mode_frame = tk.Frame(control, bg='#2a2a2a')
        mode_frame.pack(pady=5)
        
        tk.Label(mode_frame, text="Режим: Live",
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a', fg='#00d4aa').pack(side='left', padx=10)
        
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
        
        # ===== MANUAL TRADING =====
        if self.manual_controller and self.manual_controller.is_enabled():
            self.create_manual_trading_section()
        
        # ===== LOGS =====
        logs_title = customtkinter.CTkLabel(self.root, text="[LOGS] Системные логи", 
                                           font=customtkinter.CTkFont(size=16, weight="bold"), 
                                           text_color="#00FFFF")
        logs_title.pack(pady=(20, 5), padx=20, anchor="w")
        
        # Большой фрейм для логов
        self.logs_frame = customtkinter.CTkFrame(self.root, height=300, fg_color="#1e1e1e")
        self.logs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.logs_frame.pack_propagate(False)  # Важно! Чтобы height не сжимался
        
        # Текстовое поле
        self.log_text = customtkinter.CTkTextbox(self.logs_frame, font=("Consolas", 11), wrap="none")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Скроллбар
        scrollbar = customtkinter.CTkScrollbar(self.logs_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Цветные теги с контрастными фонами для лучшей читаемости
        try:
            self.log_text.tag_config("info", foreground="#ffffff", background="#1e1e1e")
            self.log_text.tag_config("warning", foreground="#ffff00", background="#333300")
            self.log_text.tag_config("error", foreground="#ff4444", background="#330000")
            self.log_text.tag_config("critical", foreground="#ff0000", background="#220000")
        except Exception:
            # Some CTkTextbox versions may not support tag_config fully — ignore if fails
            pass
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg='#1a1a1a')
        footer.pack(fill='x', padx=20, pady=10)
        
        tk.Label(footer, text="BAZA v3.0 | SMC + ML + GPT",
                font=('Arial', 9), bg='#1a1a1a', fg='#555555').pack()
    
    def _add_log_to_gui(self, message: str, level: str = "INFO"):
        """Callback для добавления логов в GUI."""
        try:
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return
            self.root.after(0, lambda: self._insert_log_message(message, level))
        except Exception as e:
            print(f"GUI logging error: {e}")

    def _insert_log_message(self, message: str, level: str):
        """Вставка сообщения в лог с цветом."""
        if not hasattr(self, 'log_text') or not self.log_text:
            return
        
        try:
            # Вставляем текст с тегом
            self.log_text.insert('end', message + '\n', level.lower())
            self.log_text.see('end')
        except Exception as e:
            print(f"Error inserting log message: {e}")
    
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
    
    def log(self, message, level="info"):
        """Добавление лога."""
        # Логируем через централизованный логгер
        if level == "info":
            app_logger.info(message)
        elif level == "warning":
            app_logger.warning(message)
        elif level == "error":
            app_logger.error(message)
        elif level == "debug":
            app_logger.debug(message)
        elif level == "critical":
            app_logger.critical(message)
        else:
            app_logger.info(message)
        
        # Добавляем в GUI
        self._add_log_to_gui(message, level.upper())
    
    def update_mt5_status(self):
        """Обновление статуса MT5 в UI."""
        if self.app_state.mt5_connected:
            account_info = self.app_state.mt5_account_info
            self.mt5_status.config(
                text=f"[MT5] MT5: Connected ({account_info.get('login', 'N/A')})",
                fg='#00d4aa'
            )
            self.mt5_account.config(
                text=f"Баланс: ${account_info.get('balance', 0):.2f} | Свободно: ${account_info.get('margin_free', 0):.2f}",
                fg='#888888'
            )
            # Обновляем баланс в статистике
            self.app_state.stats['balance'] = account_info.get('balance', 100.0)
            self.update_display()
        else:
            self.mt5_status.config(text="[MT5] MT5: Not connected", fg='#ff4757')
            self.mt5_account.config(text="", fg='#888888')
            # Возвращаем баланс к демо значению
            self.app_state.stats['balance'] = 100.0
            self.update_display()
    
    def update_display(self):
        """Обновление статистики."""
        self.card_balance.value_label.config(text=f"${self.app_state.stats['balance']:.2f}")
        
        pnl = self.app_state.stats['total_pnl']
        color = '#00d4aa' if pnl >= 0 else '#ff4757'
        self.card_pnl.value_label.config(
            text=f"{'+' if pnl >= 0 else ''}${pnl:.2f}", fg=color)
        
        today = self.app_state.stats['today_pnl']
        color = '#00d4aa' if today >= 0 else '#ff4757'
        self.card_today.value_label.config(
            text=f"{'+' if today >= 0 else ''}${today:.2f}", fg=color)
        
        total = self.app_state.stats['wins'] + self.app_state.stats['losses']
        winrate = (self.app_state.stats['wins'] / total * 100) if total > 0 else 0
        self.card_winrate.value_label.config(text=f"{winrate:.0f}%")
    
    def update_status(self, running, paused=False):
        """Обновление статуса бота."""
        self.app_state.bot_running = running
        self.app_state.bot_paused = paused
        
        if running and not paused:
            self.status_dot.config(fg='#00d4aa')
            self.status_label.config(text='Работает')
            self.btn_start.config(state='disabled')
            self.btn_pause.config(state='normal', text='⏸ ПАУЗА')
            self.btn_stop.config(state='normal')
            # Блокируем manual trading
            if hasattr(self, 'btn_open_trade'):
                self.btn_open_trade.config(state='disabled')
            if hasattr(self, 'btn_predict'):
                self.btn_predict.config(state='disabled')
        elif running and paused:
            self.status_dot.config(fg='#f39c12')
            self.status_label.config(text='Пауза')
            self.btn_pause.config(text='▶ ПРОДОЛЖИТЬ')
            # Блокируем manual trading
            if hasattr(self, 'btn_open_trade'):
                self.btn_open_trade.config(state='disabled')
            if hasattr(self, 'btn_predict'):
                self.btn_predict.config(state='disabled')
        else:
            self.status_dot.config(fg='#ff4757')
            self.status_label.config(text='Остановлен')
            self.btn_start.config(state='normal')
            self.btn_pause.config(state='disabled', text='⏸ ПАУЗА')
            self.btn_stop.config(state='disabled')
            # Разблокируем manual trading
            if hasattr(self, 'btn_open_trade'):
                self.btn_open_trade.config(state='normal')
            if hasattr(self, 'btn_predict'):
                self.btn_predict.config(state='normal')
    
    def start_bot(self):
        """Запуск бота."""
        # Проверка лицензии
        valid, msg = license_manager.is_valid()
        if not valid:
            messagebox.showerror("Ошибка", f"Лицензия недействительна: {msg}")
            return
        
        mode = 'live'  # Фиксирован на Live режиме
        
        # Подтверждение для Live торговли
        if not messagebox.askyesno("Подтверждение", 
                "Вы уверены что хотите запустить LIVE торговлю?\n\n"
                "Будут открываться РЕАЛЬНЫЕ сделки!"):
            return
        
        self.stop_event.clear()
        self.bot_thread = threading.Thread(target=self.run_bot, args=(mode,), daemon=True)
        self.bot_thread.start()
        
        self.update_status(True, False)
        self.log(f"[LAUNCH] Bot started in {mode.upper()} mode")
    
    def stop_bot(self):
        """Остановка бота."""
        self.stop_event.set()
        self.update_status(False)
        self.app_state.update_mt5_status(False)
        self.root.after(0, self.update_mt5_status)
        self.log("[STOP] Bot stopped")
    
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
        self.log("[START] Starting bot thread...")
        try:
            from src.live.live_trader import LiveTrader
            
            self.log("[CONNECT] Connecting to MT5...")
            
            enable_trading = (mode == 'live')
            self.trader = LiveTrader(config_dir='config', enable_trading=enable_trading, enable_gpt=self.enable_gpt)
            self.live_trader = self.trader  # Для совместимости
            
            # Устанавливаем executor для manual trading
            if self.manual_controller:
                # Импортируем executor из trader
                self.manual_controller.executor = self.trader.executor
                self.log("[OK] Manual trading executor connected")
            
            # Обновляем статус MT5
            status = self.trader.get_connection_status()
            if status['connected']:
                # build a consistent account_info dict to avoid passing raw ints
                account_info = {
                    'login': status.get('account'),
                    'balance': status.get('balance'),
                    'equity': status.get('equity'),
                    'broker': status.get('broker')
                }
                self.app_state.update_mt5_status(True, account_info)
            else:
                self.app_state.update_mt5_status(False)
            self.root.after(0, self.update_mt5_status)
            
            if status['connected']:
                self.log(f"[OK] MT5 connected: {status.get('broker', '')} | Account: {status.get('account', '')}")
                self.log(f"[BALANCE] Balance: ${status.get('balance', 0):.2f}")
            else:
                self.log(f"[ERROR] Connection error: {status.get('message', 'Unknown')}")
                self.root.after(0, lambda: self.update_status(False))
                return
            
            self.log("[MONITOR] Starting market monitoring...")
            
            while not self.stop_event.is_set():
                if self.bot_paused:
                    self.stop_event.wait(1)
                    continue
                
                try:
                    # Проверка сигналов
                    signals = self.trader.check_signals()
                    
                    if signals:
                        for signal in signals:
                            self.log(f"[SIGNAL] {signal}")
                        
                        # Обновляем статистику
                        self.root.after(0, self.update_display)
                    
                except Exception as e:
                    self.log(f"[WARNING] Error in signal check: {str(e)}")
                    import traceback
                    self.log(f"[DEBUG] Traceback: {traceback.format_exc()}")
                
                # Ждём 60 секунд
                self.stop_event.wait(60)
            
            self.log("[STOP] Bot thread stopped normally")
            
        except Exception as e:
            self.log(f"[CRITICAL] Critical error in bot thread: {str(e)}")
            import traceback
            self.log(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            self.root.after(0, lambda: self.update_status(False))
        
        self.log("[END] Bot thread finished")
    
    def load_stats(self):
        """Загрузка статистики."""
        stats_file = Path('data/bot_stats.json')
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                self.app_state.stats.update(json.load(f))
        
        # Если локальной истории сделок нет — попробуем подтянуть из терминала MT5.
        # Часто мониторинг MT5 стартует в фоновом потоке и соединение ещё не установлено,
        # поэтому запускаем фоновую задачу с ожиданием подключения и повторным получением истории.
        trades_file = Path('data/trades_history.json')

        def compute_from_file():
            try:
                if trades_file.exists():
                    with open(trades_file, 'r', encoding='utf-8') as f:
                        trades = json.load(f)

                    total_pnl = sum(t.get('pnl', 0) for t in trades)
                    total_trades = len(trades)
                    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
                    losses = sum(1 for t in trades if t.get('pnl', 0) <= 0)
                    today = datetime.now().strftime('%Y-%m-%d')
                    today_pnl = sum(t.get('pnl', 0) for t in trades if t.get('date') == today)

                    self.app_state.stats['total_pnl'] = round(float(total_pnl), 2)
                    self.app_state.stats['today_pnl'] = round(float(today_pnl), 2)
                    self.app_state.stats['trades'] = total_trades
                    self.app_state.stats['total_trades'] = total_trades
                    self.app_state.stats['wins'] = wins
                    self.app_state.stats['losses'] = losses
                    self.save_stats()
                    # Обновляем отображение в UI
                    try:
                        self.root.after(0, self.update_display)
                    except Exception:
                        pass
            except Exception as e:
                self.log(f"[ERROR] compute_from_file failed: {e}")

        # Если файла нет — попробуем дождаться подключения MT5 и скачать историю.
        if not trades_file.exists():
            def fetch_when_connected():
                try:
                    # Ожидаем подключение до 15 секунд
                    wait_secs = 15
                    interval = 1
                    waited = 0
                    while waited < wait_secs:
                        if self.app_state.mt5_manager and self.app_state.mt5_manager.is_connected():
                            try:
                                trades = self.app_state.mt5_manager.get_trade_history(days=365)
                            except Exception:
                                trades = []

                            if trades:
                                trades_file.parent.mkdir(exist_ok=True)
                                with open(trades_file, 'w', encoding='utf-8') as f:
                                    json.dump(trades, f, indent=2, ensure_ascii=False)
                                compute_from_file()
                            return

                        waited += interval
                        threading.Event().wait(interval)
                except Exception as e:
                    self.log(f"[ERROR] fetch_when_connected failed: {e}")

            threading.Thread(target=fetch_when_connected, daemon=True).start()
        else:
            # Файл есть — сразу пересчитываем агрегаты
            compute_from_file()
    
    def save_stats(self):
        """Сохранение статистики."""
        stats_file = Path('data/bot_stats.json')
        stats_file.parent.mkdir(exist_ok=True)
        with open(stats_file, 'w') as f:
            json.dump(self.app_state.stats, f)
    
    def on_closing(self):
        """При закрытии."""
        if self.app_state.bot_running:
            if messagebox.askyesno("Выход", "Бот работает. Остановить и выйти?"):
                self.stop_bot()
                self.save_stats()
                self.root.destroy()
        else:
            self.save_stats()
            self.root.destroy()
    
    def _on_symbol_change(self, event=None):
        """Обработчик изменения символа с немедленным обновлением цены."""
        if not hasattr(self, 'manual_symbol') or not self.manual_symbol:
            return
        new_symbol = self.manual_symbol.get()
        self.app_state.manual_trade_state.symbol = new_symbol
        self.log(f"[CHANGE] Symbol changed to {new_symbol}")
        self._update_price_now()
        self.update_manual_calculations()

    def _apply_rr_to_state(self, from_state: bool = False):
        """Применить выбранный RR к состоянию: пересчитать TP или SL в зависимости от того, что задано.

        Если `from_state` True, вызов происходит при синхронизации GUI из состояния — не перезаписываем явно
        введённые пользователем значения, но можем вычислить недостающие на основе RR.
        """
        state = self.app_state.manual_trade_state
        if not state:
            return
        try:
            rr = float(self.manual_rr_ratio.get())
        except Exception:
            return
        if rr <= 0:
            return

        entry = float(self.manual_entry.get() if hasattr(self, 'manual_entry') else state.entry_price)
        sl = float(self.manual_sl.get() if hasattr(self, 'manual_sl') else state.stop_loss)
        tp = float(self.manual_tp.get() if hasattr(self, 'manual_tp') else state.take_profit)
        direction = self.manual_direction.get() if hasattr(self, 'manual_direction') else state.direction

        # If stop loss exists, compute TP from SL
        if sl and sl > 0 and entry and entry > 0:
            if direction == 'buy':
                sl_distance = entry - sl
                if sl_distance > 0:
                    new_tp = entry + sl_distance * rr
                    # Update only TP (user SL preserved)
                    self.manual_tp.set(round(new_tp, 6))
                    state.take_profit = float(round(new_tp, 6))
            else:  # sell
                sl_distance = sl - entry
                if sl_distance > 0:
                    new_tp = entry - sl_distance * rr
                    self.manual_tp.set(round(new_tp, 6))
                    state.take_profit = float(round(new_tp, 6))
            state.risk_reward_ratio = rr
            return

        # Else if TP exists, compute SL from TP
        if tp and tp > 0 and entry and entry > 0:
            if direction == 'buy':
                tp_distance = tp - entry
                if tp_distance > 0:
                    new_sl = entry - (tp_distance / rr)
                    self.manual_sl.set(round(new_sl, 6))
                    state.stop_loss = float(round(new_sl, 6))
            else:  # sell
                tp_distance = entry - tp
                if tp_distance > 0:
                    new_sl = entry + (tp_distance / rr)
                    self.manual_sl.set(round(new_sl, 6))
                    state.stop_loss = float(round(new_sl, 6))
            state.risk_reward_ratio = rr
            return

        # If neither SL nor TP set, and `from_state` is False (user is interacting), do nothing.
        return

    def _on_rr_change(self, event=None):
        """Handler when RR spinbox changes in UI."""
        try:
            self._apply_rr_to_state()
        except Exception as e:
            self.log(f"[ERROR] RR apply error: {e}")
        # Recalculate derived values
        try:
            self.update_manual_calculations()
        except Exception:
            pass
    
    def _on_timeframe_change(self, event=None):
        """Обработчик изменения таймфрейма."""
        if not hasattr(self, 'manual_timeframe') or not self.manual_timeframe:
            return
        new_timeframe = self.manual_timeframe.get()
        self.app_state.manual_trade_state.timeframe = new_timeframe
        self.log(f"[CHANGE] Timeframe changed to {new_timeframe}")
        self.update_manual_calculations()
    
    def _on_direction_change(self):
        """Обработчик изменения направления с обновлением цены."""
        if not hasattr(self, 'manual_direction') or not self.manual_direction:
            return
        new_direction = self.manual_direction.get()
        self.app_state.manual_trade_state.direction = new_direction
        self.log(f"[CHANGE] Direction changed to {new_direction}")
        self._update_price_now()
        self.update_manual_calculations()
    
    def _update_price_now(self):
        """Немедленное обновление цены из MT5."""
        try:
            state = self.app_state.manual_trade_state
            symbol = state.symbol
            if not symbol or not self.app_state.mt5_manager or not self.app_state.mt5_manager.is_connected():
                state.entry_price = 0.0
                if hasattr(self, 'manual_entry'):
                    self.manual_entry.set(0.0)
                return
            
            tick = self.app_state.mt5_manager.mt5.symbol_info_tick(symbol)
            if not tick:
                self.log(f"[WARNING] Failed to get price for {symbol}")
                state.entry_price = 0.0
                if hasattr(self, 'manual_entry'):
                    self.manual_entry.set(0.0)
                return
            
            if state.direction == "buy":
                state.entry_price = tick.ask
            elif state.direction == "sell":
                state.entry_price = tick.bid
            else:
                state.entry_price = tick.bid
            
            if hasattr(self, 'manual_entry'):
                self.manual_entry.set(state.entry_price)
                
        except Exception as e:
            self.log(f"[ERROR] Price update error: {e}")
            state.entry_price = 0.0
    
    def _on_price_change(self, event=None):
        """Обработчик изменения цен."""
        if not all([self.manual_entry, self.manual_sl, self.manual_tp]):
            return
        state = self.app_state.manual_trade_state
        state.entry_price = self.manual_entry.get()
        state.stop_loss = self.manual_sl.get()
        state.take_profit = self.manual_tp.get()
        
        # Обновляем расчеты
        # Если задан RR и есть стоп — пересчитываем тейк автоматически
        try:
            self._apply_rr_to_state()
        except Exception:
            pass

        self.update_manual_calculations()
    
    def _on_market_data_update(self, prices=None):
        """Обработчик обновления рыночных данных."""
        try:
            state = self.app_state.manual_trade_state
            
            # Если MT5 не подключен или нет данных
            if not self.app_state.mt5_manager or not self.app_state.mt5_manager.is_connected():
                self.log("[WARNING] MT5 not connected - prices not updating")
                return
            
            # Получаем текущие цены
            symbol = state.symbol
            if not symbol:
                return
                
            tick = self.app_state.mt5_manager.mt5.symbol_info_tick(symbol)
            if not tick:
                self.log(f"[WARNING] Failed to get prices for {symbol}")
                return
            
            bid = tick.bid
            ask = tick.ask
            
            # Обновляем состояние
            state.bid_price = bid
            state.ask_price = ask
            state.spread = ask - bid
            state.market_data_timestamp = datetime.now()
            
            # Автоматически обновляем entry_price если не заблокировано
            if state.auto_update_prices and not state.prices_locked:
                if state.direction == "buy" and ask > 0:
                    state.entry_price = ask
                elif state.direction == "sell" and bid > 0:
                    state.entry_price = bid
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self.update_manual_from_state)
            
        except Exception as e:
            self.log(f"[ERROR] Market data update error: {e}")
    
    def update_manual_from_state(self):
        """Обновление GUI из состояния."""
        try:
            state = self.app_state.manual_trade_state
            
            # Обновляем переменные GUI
            self.manual_symbol.set(state.symbol)
            self.manual_timeframe.set(state.timeframe)
            # Обновляем только цену входа из состояния — не перезаписываем SL/TP/risk,
            # чтобы не ломать значения, введённые пользователем.
            self.manual_entry.set(state.entry_price)
            self.manual_direction.set(state.direction)

            # Обновляем расчеты
            # При обновлении GUI из состояния, пересчитываем TP/SL по RR,
            # но не перезаписываем явно введённые пользователем SL/TP.
            try:
                self._apply_rr_to_state(from_state=True)
            except Exception:
                pass
            self.update_manual_calculations()
            
        except Exception as e:
            self.log(f"[ERROR] GUI update error: {e}")
    
    def save_mt5_credentials(self, login: int, password: str, server: str, terminal_path: str):
        """Сохранение учетных данных MT5 в зашифрованный файл."""
        import json
        import base64
        
        try:
            # Создаем данные для сохранения
            credentials = {
                'login': login,
                'password': password,
                'server': server,
                'terminal_path': terminal_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # Простое шифрование (base64 для демо, в продакшене использовать cryptography)
            data_str = json.dumps(credentials)
            encoded_data = base64.b64encode(data_str.encode('utf-8')).decode('utf-8')
            
            # Сохраняем в файл
            config_dir = Path('config')
            config_dir.mkdir(exist_ok=True)
            cred_file = config_dir / 'mt5_credentials.enc'
            
            with open(cred_file, 'w') as f:
                f.write(encoded_data)
                
        except Exception as e:
            raise Exception(f"Не удалось сохранить учетные данные: {e}")
    
    def load_mt5_credentials(self):
        """Загрузка учетных данных MT5 из файла."""
        import json
        import base64
        
        try:
            cred_file = Path('config/mt5_credentials.enc')
            if not cred_file.exists():
                return  # Файл не существует
            
            with open(cred_file, 'r') as f:
                encoded_data = f.read()
            
            # Расшифровываем
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            credentials = json.loads(decoded_data)
            
            # Устанавливаем в app_state
            config = {
                'login': credentials['login'],
                'password': credentials['password'],
                'server': credentials['server'],
                'terminal_path': credentials.get('terminal_path', '')
            }
            self.app_state.set_mt5_config(config)
            
            self.log("[OK] MT5 credentials loaded from file")
            
        except Exception as e:
            self.log(f"[WARNING] Failed to load MT5 credentials: {e}")
    
    def run(self):
        """Запуск приложения."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Стартовые логи
        self.log("[INFO] Приложение BAZA Trading Bot запущено", "info")
        self.log("[READY] BAZA Trading Bot ready to work", "info")
        
        # Логируем запуск mainloop
        self.log("[START] Starting GUI mainloop...")
        try:
            self.root.mainloop()
        finally:
            print("GUI mainloop finished")

    def _add_log_to_gui(self, message: str, level: str = "INFO"):
        """Callback для добавления логов в GUI."""
        try:
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return
            self.root.after(0, lambda: self._insert_log_message(message, level))
        except Exception as e:
            print(f"GUI logging error: {e}")

    def _insert_log_message(self, message: str, level: str):
        """Вставка сообщения в лог с цветом."""
        # Основные логи внизу
        if hasattr(self, 'log_text') and self.log_text:
            try:
                self.log_text.configure(state='normal')
                self.log_text.insert('end', message + '\n', level.lower())
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
            except Exception as e:
                print(f"Main logs error: {e}")
        
        # Мини-логи рядом с кнопками
        if hasattr(self, 'mini_logs_text') and self.mini_logs_text:
            try:
                # Ensure the widget supports text operations
                if callable(getattr(self.mini_logs_text, 'get', None)) and callable(getattr(self.mini_logs_text, 'delete', None)):
                    self.mini_logs_text.config(state='normal')

                    # Ограничиваем количество строк в мини-логах (последние 25)
                    lines = self.mini_logs_text.get('1.0', 'end-1c').split('\n')
                    if len(lines) >= 25:
                        # Удаляем старые строки
                        try:
                            self.mini_logs_text.delete('1.0', '2.0')
                        except Exception:
                            pass

                    self.mini_logs_text.insert('end', message + '\n', level.lower())
                    self.mini_logs_text.see('end')
                    self.mini_logs_text.config(state='disabled')
                else:
                    # Fallback: try to append if object supports insert
                    if callable(getattr(self.mini_logs_text, 'insert', None)):
                        try:
                            self.mini_logs_text.insert('end', message + '\n')
                        except Exception:
                            pass
            except Exception as e:
                print(f"Mini logs error: {e}")


def main():
    app = BazaApp()
    app.run()


if __name__ == '__main__':
    main()
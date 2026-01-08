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

# License system removed - free version
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

# AI Analysis imports
try:
    from src.ai.analyst_scheduler import get_scheduler, init_scheduler
    from src.ai.signal_manager import AISignalManager
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False


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
        
        # Инициализация AI Analysis
        self.ai_scheduler = None
        self.ai_signal_manager = None
        self.ai_signals_data = []  # Store full signal data for details
        
        # Инициализация Pure AI Trader
        self.pure_ai_trader = None
        try:
            from src.ai.pure_ai_trader import PureAITrader
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                # Загружаем настройки Pure AI из config
                config_file = Path('data/config.json')
                pure_ai_config = {}
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            pure_ai_config = config.get('pure_ai', {})
                    except:
                        pass
                
                interval_hours = pure_ai_config.get('analysis_interval_hours', 5)
                self.pure_ai_trader = PureAITrader(api_key=api_key, analysis_interval_hours=interval_hours)
                app_logger.info(f"[OK] Pure AI Trader initialized (interval: {interval_hours}h)")
        except Exception as e:
            app_logger.error(f"[ERROR] Pure AI Trader init failed: {e}")
        
        if AI_ANALYSIS_AVAILABLE:
            try:
                self.ai_scheduler = init_scheduler(callback=self._on_ai_analysis_update)
                self.ai_signal_manager = AISignalManager()
                app_logger.info("[OK] AI Analysis system initialized")
            except Exception as e:
                app_logger.error(f"[ERROR] AI Analysis init failed: {e}")
        
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
        
        # Start AI display auto-update (every 5 seconds)
        if AI_ANALYSIS_AVAILABLE and self.ai_signal_manager:
            self._schedule_ai_update()
    
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
    
    def _init_mt5_manager(self) -> None:
        """Инициализация MT5 Manager с улучшенной обработкой ошибок."""
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
                        app_logger.error("[ERROR] Failed to initialize MT5 without path")
                        self.app_state.mt5_manager = None
            else:
                if terminal_path:
                    app_logger.warning(f"[WARNING] Terminal path not found: {terminal_path}")
                
                if self.app_state.mt5_manager.initialize():
                    app_logger.info("[OK] MT5 initialized without path (auto-detect)")
                else:
                    app_logger.error("[ERROR] Failed to initialize MT5 - check if MetaTrader 5 is installed")
                    self.app_state.mt5_manager = None
            
            # Передаем MT5 Manager в BotManager для получения реальной статистики
            if self.app_state.mt5_manager and self.bot_manager:
                self.bot_manager.set_mt5_manager(self.app_state.mt5_manager)
                app_logger.info("[OK] MT5 Manager connected to BotManager")
                    
        except ImportError as e:
            app_logger.error(f"[ERROR] MetaTrader5 library not found: {e}")
            self.app_state.mt5_manager = None
        except Exception as e:
            app_logger.error(f"[ERROR] Failed to initialize MT5 Manager: {e}", exc_info=True)
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

                    # Обновляем статистику (баланс, прибыли)
                    balance_changed = new_balance != old_balance or new_equity != old_equity
                    
                    if balance_changed:
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
                    
                    # Каждый цикл обновляем прибыль из истории MT5
                    try:
                        trades = self.app_state.mt5_manager.get_trade_history(days=365)
                        if trades:
                            total_pnl = sum(t.get('pnl', 0) for t in trades)
                            today_date = datetime.now().strftime('%Y-%m-%d')
                            today_pnl = sum(t.get('pnl', 0) for t in trades if t.get('date') == today_date)
                            
                            self.app_state.stats['total_pnl'] = round(float(total_pnl), 2)
                            self.app_state.stats['today_pnl'] = round(float(today_pnl), 2)
                            
                            # Обновляем счетчики сделок
                            total_trades = len(trades)
                            wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
                            losses = total_trades - wins
                            
                            self.app_state.stats['total_trades'] = total_trades
                            self.app_state.stats['trades'] = total_trades
                            self.app_state.stats['wins'] = wins
                            self.app_state.stats['losses'] = losses
                    except Exception as e:
                        app_logger.error(f"Failed to update pnl from MT5: {e}")
                    
                    # Обновляем UI
                    self.app_state.update_mt5_status(True, account_info)
                    self.root.after(0, self.update_mt5_status)
                    self.root.after(0, self.update_display)

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
        """License removed - free version."""
        pass  # No license check needed
    
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
                
            success, msg = True, "License system removed - free version"
            
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
            valid, _ = True, "Free version"
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
        dialog.geometry("550x650")  # Увеличено для новых настроек
        dialog.configure(bg='#1a1a1a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем
        dialog.geometry("+%d+%d" % (
            self.root.winfo_screenwidth() / 2 - 275,
            self.root.winfo_screenheight() / 2 - 325
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
        
        # Раздел настроек стратегии
        strategy_frame = tk.Frame(dialog, bg='#2a2a2a', relief='flat')
        strategy_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(strategy_frame, text="⚙️ Настройки стратегии XAUUSD",
                font=('Arial', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', pady=(10, 5))
        
        # Получаем текущие параметры стратегии
        strategy_config = current_config.get('strategy', {})
        
        # Максимум сделок в день
        trades_frame = tk.Frame(strategy_frame, bg='#2a2a2a')
        trades_frame.pack(fill='x', pady=5)
        tk.Label(trades_frame, text="Макс. сделок в день:",
                font=('Arial', 10), bg='#2a2a2a', fg='#cccccc', width=22, anchor='w').pack(side='left')
        max_trades_var = tk.IntVar(value=strategy_config.get('max_daily_trades', 1))
        tk.Spinbox(trades_frame, from_=1, to=10, textvariable=max_trades_var,
                  font=('Arial', 10), bg='#0f0f0f', fg='white', width=10,
                  buttonbackground='#2a2a2a', insertbackground='white').pack(side='left', padx=5)
        
        # Максимальная дневная потеря (%)
        loss_frame = tk.Frame(strategy_frame, bg='#2a2a2a')
        loss_frame.pack(fill='x', pady=5)
        tk.Label(loss_frame, text="Макс. потеря в день (%):",
                font=('Arial', 10), bg='#2a2a2a', fg='#cccccc', width=22, anchor='w').pack(side='left')
        max_loss_var = tk.DoubleVar(value=strategy_config.get('max_daily_loss', 1.0))
        tk.Spinbox(loss_frame, from_=0.5, to=5.0, increment=0.5, textvariable=max_loss_var,
                  font=('Arial', 10), bg='#0f0f0f', fg='white', width=10,
                  buttonbackground='#2a2a2a', insertbackground='white', format="%.1f").pack(side='left', padx=5)
        
        # Минимальный ATR (% от среднего)
        min_atr_frame = tk.Frame(strategy_frame, bg='#2a2a2a')
        min_atr_frame.pack(fill='x', pady=5)
        tk.Label(min_atr_frame, text="Мин. волатильность ATR:",
                font=('Arial', 10), bg='#2a2a2a', fg='#cccccc', width=22, anchor='w').pack(side='left')
        min_atr_var = tk.DoubleVar(value=strategy_config.get('min_atr_threshold', 0.7))
        tk.Spinbox(min_atr_frame, from_=0.3, to=1.0, increment=0.1, textvariable=min_atr_var,
                  font=('Arial', 10), bg='#0f0f0f', fg='white', width=10,
                  buttonbackground='#2a2a2a', insertbackground='white', format="%.1f").pack(side='left', padx=5)
        
        # Максимальный ATR (% от среднего)
        max_atr_frame = tk.Frame(strategy_frame, bg='#2a2a2a')
        max_atr_frame.pack(fill='x', pady=5)
        tk.Label(max_atr_frame, text="Макс. волатильность ATR:",
                font=('Arial', 10), bg='#2a2a2a', fg='#cccccc', width=22, anchor='w').pack(side='left')
        max_atr_var = tk.DoubleVar(value=strategy_config.get('max_atr_threshold', 1.5))
        tk.Spinbox(max_atr_frame, from_=1.0, to=3.0, increment=0.1, textvariable=max_atr_var,
                  font=('Arial', 10), bg='#0f0f0f', fg='white', width=10,
                  buttonbackground='#2a2a2a', insertbackground='white', format="%.1f").pack(side='left', padx=5)
        
        tk.Label(strategy_frame, text="ℹ️ Настройки применяются сразу при сохранении",
                font=('Arial', 8),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(10, 10))
        
        # Раздел Pure AI настроек
        pure_ai_frame = tk.Frame(dialog, bg='#2a2a2a', relief='flat')
        pure_ai_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(pure_ai_frame, text="🤖 Pure AI Trading - Настройки",
                font=('Arial', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', pady=(10, 5))
        
        # Получаем текущие настройки Pure AI
        pure_ai_config = current_config.get('pure_ai', {})
        current_interval = pure_ai_config.get('analysis_interval_hours', 5)
        
        # Интервал анализа
        interval_row = tk.Frame(pure_ai_frame, bg='#2a2a2a')
        interval_row.pack(fill='x', pady=5)
        tk.Label(interval_row, text="Интервал анализа GPT:",
                font=('Arial', 10), bg='#2a2a2a', fg='white', width=25, anchor='w').pack(side='left')
        interval_var = tk.IntVar(value=current_interval)
        tk.Spinbox(interval_row, from_=1, to=24, textvariable=interval_var,
                  font=('Arial', 10), bg='#0f0f0f', fg='white', width=10,
                  buttonbackground='#2a2a2a', insertbackground='white').pack(side='left', padx=5)
        tk.Label(interval_row, text="часов",
                font=('Arial', 10), bg='#2a2a2a', fg='#888888').pack(side='left')
        
        tk.Label(pure_ai_frame, text="ℹ️ Меньше интервал = больше запросов к GPT и расход API",
                font=('Arial', 8),
                bg='#2a2a2a', fg='#888888').pack(anchor='w', pady=(5, 10))
        
        # Кнопки
        btn_frame = tk.Frame(dialog, bg='#1a1a1a')
        btn_frame.pack(fill='x', padx=20, pady=20)
        
        def save_settings():
            key = api_entry.get().strip()
            gpt_enabled_val = gpt_enabled.get()
            
            # Получаем значения стратегии
            strategy_settings = {
                'max_daily_trades': max_trades_var.get(),
                'max_daily_loss': max_loss_var.get(),
                'min_atr_threshold': min_atr_var.get(),
                'max_atr_threshold': max_atr_var.get()
            }
            
            # Получаем значения Pure AI
            pure_ai_settings = {
                'analysis_interval_hours': interval_var.get()
            }
            
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
            
            # Сохраняем настройку GPT и стратегии
            config_file = Path('data/config.json')
            config_file.parent.mkdir(exist_ok=True)
            try:
                config = {}
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                
                config['enable_gpt'] = gpt_enabled_val
                config['strategy'] = strategy_settings  # Добавляем настройки стратегии
                config['pure_ai'] = pure_ai_settings  # Добавляем настройки Pure AI
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                # Обновляем настройку в классе
                self.enable_gpt = gpt_enabled_val
                
                # Применяем настройки к работающей стратегии
                if hasattr(self, 'bot_manager') and self.bot_manager:
                    try:
                        # Получаем активную стратегию через bot_manager
                        if hasattr(self.bot_manager, 'live_trader') and self.bot_manager.live_trader:
                            live_trader = self.bot_manager.live_trader
                            # Получаем стратегию XAUUSD из словаря стратегий
                            if hasattr(live_trader, 'strategies') and 'XAUUSD' in live_trader.strategies:
                                strategy = live_trader.strategies['XAUUSD']
                                # Применяем новые параметры
                                strategy.max_daily_trades = strategy_settings['max_daily_trades']
                                strategy.max_daily_loss = strategy_settings['max_daily_loss']
                                strategy.min_atr_threshold = strategy_settings['min_atr_threshold']
                                strategy.max_atr_threshold = strategy_settings['max_atr_threshold']
                                app_logger.info(f"[Settings] Strategy parameters updated: {strategy_settings}")
                                status_label.config(text="[OK] Настройки применены! Бот использует новые значения.", fg='#00d4aa')
                            else:
                                status_label.config(text="[OK] Настройки сохранены (применятся при запуске бота)", fg='#00d4aa')
                        
                        # Применяем настройки Pure AI
                        if hasattr(self, 'pure_ai_trader') and self.pure_ai_trader:
                            new_interval = pure_ai_settings['analysis_interval_hours'] * 60 * 60
                            self.pure_ai_trader.ANALYSIS_INTERVAL = new_interval
                            app_logger.info(f"[Settings] Pure AI interval updated: {pure_ai_settings['analysis_interval_hours']}h")
                            status_label.config(text="[OK] Pure AI настройки применены!", fg='#00d4aa')
                    
                    except Exception as e:
                        app_logger.error(f"[Settings] Failed to apply settings: {e}")
                        status_label.config(text="[OK] Настройки сохранены (применятся при перезапуске)", fg='#f39c12')
                else:
                    status_label.config(text="[OK] Настройки сохранены!", fg='#00d4aa')

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
                    # Обновляем связь с BotManager после подключения
                    if self.bot_manager:
                        self.bot_manager.set_mt5_manager(self.app_state.mt5_manager)
                        self.log("[OK] MT5 Manager reconnected to BotManager")
                    
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
        # Контейнер
        container = tk.Frame(self.root, bg='#1a1a1a')
        container.pack(fill='x', padx=20, pady=10)
        
        # Заголовок с кнопкой collapse/expand
        header = tk.Frame(container, bg='#2a2a2a')
        header.pack(fill='x', pady=(0, 5))
        
        self.manual_expanded = tk.BooleanVar(value=False)  # Скрыто по умолчанию
        
        def toggle_manual():
            if self.manual_expanded.get():
                self.manual_expanded.set(False)
                manual_content.pack_forget()
                self.btn_toggle_manual.config(text="▶ MANUAL TRADING")
            else:
                self.manual_expanded.set(True)
                manual_content.pack(fill='both', expand=True, pady=5)
                self.btn_toggle_manual.config(text="▼ MANUAL TRADING")
        
        self.btn_toggle_manual = tk.Button(header, text="▶ MANUAL TRADING",
                                          command=toggle_manual,
                                          font=('Arial', 13, 'bold'),
                                          bg='#2a2a2a', fg='#ff9500',
                                          relief='flat', cursor='hand2',
                                          anchor='w')
        self.btn_toggle_manual.pack(fill='x', padx=10, pady=10)
        
        # Контент (скрыт по умолчанию)
        manual_content = tk.Frame(container, bg='#1a1a1a')
        
        # Контейнер с двумя колонками: слева - manual controls, справа - мини-логи
        manual_container = tk.Frame(manual_content, bg='#1a1a1a')
        manual_container.pack(fill='both', expand=True)

        manual_frame = tk.Frame(manual_container, bg='#1a1a1a')
        manual_frame.pack(side='left', fill='both', expand=True)

        # Основная форма
        form_frame = tk.Frame(manual_frame, bg='#1a1a1a')
        form_frame.pack(fill='x', pady=10)

        # Левая колонка - параметры
        left_frame = tk.Frame(form_frame, bg='#1a1a1a')
        left_frame.pack(side='left', fill='y', padx=(0, 10))

        # Direction (инструмент и таймфрейм удалены - только XAUUSD M15)
        state = self.app_state.manual_trade_state
        # Hardcode values
        self.manual_symbol = tk.StringVar(value='XAUUSD')
        self.manual_timeframe = tk.StringVar(value='M15')
        # Обновляем state напрямую
        state.symbol = 'XAUUSD'
        state.timeframe = 'M15'
        
        # Direction
        direction_frame = tk.Frame(left_frame, bg='#2a2a2a', relief='flat')
        direction_frame.pack(fill='x', pady=5)
        
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
        
        # AI Chat button under direction block - улучшенный дизайн
        self.btn_ai_chat = tk.Button(direction_frame, text="💬 Чат с аналитиком",
                         command=self.open_ai_chat,
                         font=('Arial', 12, 'bold'),
                         bg='#5b7dff', fg='white',
                         width=22, height=2,
                         relief='flat', cursor='hand2',
                         bd=0, activebackground='#7a96ff')
        self.btn_ai_chat.pack(anchor='w', padx=10, pady=(5, 10))
        
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
        self.manual_rr = tk.DoubleVar(value=initial_rr)
        rr_spin = tk.Spinbox(rr_frame, from_=0.1, to=10.0, increment=0.1,
                     textvariable=self.manual_rr, format="%.1f",
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

        # Быстрая кнопка удалена - используем только большие кнопки справа
        
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
        
        # Predict button removed from main actions (use AI Chat)
        
        # Большая панель быстрых действий (Open / Close) — улучшенный дизайн
        trade_control_frame = tk.Frame(manual_container, bg='#1a1a1a')
        trade_control_frame.pack(side='right', padx=(20, 10), pady=(10, 0))

        # Современная кнопка ОТКРЫТЬ с градиентным стилем
        self.btn_big_open = tk.Button(trade_control_frame, text='▲ ОТКРЫТЬ\nСДЕЛКУ', command=self.manual_open_trade,
                          font=('Arial', 13, 'bold'), bg='#00d4aa', fg='#ffffff',
                          width=16, height=4, relief='flat', cursor='hand2', state='disabled',
                          bd=0, highlightthickness=0, activebackground='#00ffcc')
        self.btn_big_open.pack(padx=5, pady=(0, 15))

        # Современная кнопка ЗАКРЫТЬ с градиентным стилем
        self.btn_big_close = tk.Button(trade_control_frame, text='▼ ЗАКРЫТЬ\nСДЕЛКУ', command=self.manual_close_trade,
                           font=('Arial', 13, 'bold'), bg='#ff5c5c', fg='#ffffff',
                           width=16, height=4, relief='flat', cursor='hand2', state='disabled',
                           bd=0, highlightthickness=0, activebackground='#ff7777')
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
    
    def create_backtest_optimization_section(self):
        """Создание секции бэктестинга и оптимизации."""
        app_logger.info("[OK] Creating Backtest & Optimization section...")
        
        # Контейнер
        container = tk.Frame(self.root, bg='#1a1a1a')
        container.pack(fill='x', padx=20, pady=10)
        
        # Заголовок с кнопкой collapse/expand
        header = tk.Frame(container, bg='#2a2a2a')
        header.pack(fill='x', pady=(0, 5))
        
        self.backtest_expanded = tk.BooleanVar(value=True)  # Раскрыто по умолчанию
        
        def toggle_backtest():
            if self.backtest_expanded.get():
                self.backtest_expanded.set(False)
                self.backtest_content_frame.pack_forget()
                self.btn_toggle_backtest.config(text="▶ BACKTEST & OPTIMIZATION")
            else:
                self.backtest_expanded.set(True)
                self.backtest_content_frame.pack(fill='x', pady=5)
                self.btn_toggle_backtest.config(text="▼ BACKTEST & OPTIMIZATION")
        
        self.btn_toggle_backtest = tk.Button(header, text="▼ BACKTEST & OPTIMIZATION",  # Показываем стрелку вниз
                                            command=toggle_backtest,
                                            font=('Arial', 13, 'bold'),
                                            bg='#2a2a2a', fg='#ff9500',
                                            relief='flat', cursor='hand2',
                                            anchor='w')
        self.btn_toggle_backtest.pack(fill='x', padx=10, pady=10)
        
        # Контент (показываем по умолчанию)
        self.backtest_content_frame = tk.Frame(container, bg='#1a1a1a')
        self.backtest_content_frame.pack(fill='x', pady=5)  # Сразу показываем
        
        # Две колонки: слева - backtest, справа - optimization
        left_col = tk.Frame(self.backtest_content_frame, bg='#2d3e50')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        right_col = tk.Frame(self.backtest_content_frame, bg='#2d3e50')
        right_col.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # === ЛЕВАЯ КОЛОНКА: BACKTEST ===
        tk.Label(left_col, text="📊 Backtest", font=('Arial', 12, 'bold'),
                bg='#2d3e50', fg='#00d4aa').pack(pady=10)
        
        # Параметры
        params_frame = tk.Frame(left_col, bg='#2d3e50')
        params_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(params_frame, text="Symbol:", font=('Arial', 10),
                bg='#2d3e50', fg='white').grid(row=0, column=0, sticky='w', padx=5, pady=3)
        
        self.backtest_symbol = tk.StringVar(value='XAUUSD')
        symbol_combo = ttk.Combobox(params_frame, textvariable=self.backtest_symbol,
                                   values=['XAUUSD', 'EURUSD', 'Portfolio'],
                                   state='readonly', width=15)
        symbol_combo.grid(row=0, column=1, padx=5, pady=3)
        
        tk.Label(params_frame, text="Year:", font=('Arial', 10),
                bg='#2d3e50', fg='white').grid(row=1, column=0, sticky='w', padx=5, pady=3)
        
        self.backtest_year = tk.StringVar(value='2024')
        year_combo = ttk.Combobox(params_frame, textvariable=self.backtest_year,
                                 values=['2023', '2024', '2025'],
                                 state='readonly', width=15)
        year_combo.grid(row=1, column=1, padx=5, pady=3)
        
        # Кнопка запуска
        btn_run_backtest = tk.Button(left_col, text="▶ Run Backtest",
                                     command=self.run_backtest_async,
                                     font=('Arial', 11, 'bold'),
                                     bg='#00d4aa', fg='white',
                                     relief='flat', cursor='hand2',
                                     width=20, height=2)
        btn_run_backtest.pack(pady=10)
        
        # Результаты
        results_frame = tk.Frame(left_col, bg='#1e1e1e')
        results_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.backtest_results_text = tk.Text(results_frame, font=('Consolas', 9),
                                             bg='#1e1e1e', fg='#00ff00',
                                             height=8, wrap='word')
        self.backtest_results_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.backtest_results_text.insert('1.0', 'Нажмите "Run Backtest" для запуска...')
        self.backtest_results_text.config(state='disabled')
        
        # === ПРАВАЯ КОЛОНКА: OPTIMIZATION ===
        tk.Label(right_col, text="🔍 Optimization", font=('Arial', 12, 'bold'),
                bg='#2d3e50', fg='#ff9500').pack(pady=10)
        
        # Параметры оптимизации
        opt_params_frame = tk.Frame(right_col, bg='#2d3e50')
        opt_params_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(opt_params_frame, text="Method:", font=('Arial', 10),
                bg='#2d3e50', fg='white').grid(row=0, column=0, sticky='w', padx=5, pady=3)
        
        self.opt_method = tk.StringVar(value='Grid Search')
        method_combo = ttk.Combobox(opt_params_frame, textvariable=self.opt_method,
                                   values=['Grid Search', 'Random Search'],
                                   state='readonly', width=15)
        method_combo.grid(row=0, column=1, padx=5, pady=3)
        
        tk.Label(opt_params_frame, text="Metric:", font=('Arial', 10),
                bg='#2d3e50', fg='white').grid(row=1, column=0, sticky='w', padx=5, pady=3)
        
        self.opt_metric = tk.StringVar(value='combined')
        metric_combo = ttk.Combobox(opt_params_frame, textvariable=self.opt_metric,
                                   values=['combined', 'sharpe', 'profit', 'winrate'],
                                   state='readonly', width=15)
        metric_combo.grid(row=1, column=1, padx=5, pady=3)
        
        tk.Label(opt_params_frame, text="Iterations:", font=('Arial', 10),
                bg='#2d3e50', fg='white').grid(row=2, column=0, sticky='w', padx=5, pady=3)
        
        self.opt_iterations = tk.IntVar(value=50)
        iter_spinbox = tk.Spinbox(opt_params_frame, from_=10, to=500, increment=10,
                                 textvariable=self.opt_iterations, width=17)
        iter_spinbox.grid(row=2, column=1, padx=5, pady=3)
        
        # Кнопка запуска
        btn_run_opt = tk.Button(right_col, text="🔍 Run Optimization",
                               command=self.run_optimization_async,
                               font=('Arial', 11, 'bold'),
                               bg='#ff9500', fg='white',
                               relief='flat', cursor='hand2',
                               width=20, height=2)
        btn_run_opt.pack(pady=10)
        
        # Прогресс-бар
        self.opt_progress = ttk.Progressbar(right_col, mode='determinate', length=200)
        self.opt_progress.pack(pady=5)
        
        self.opt_progress_label = tk.Label(right_col, text="0 / 0",
                                          font=('Arial', 9),
                                          bg='#2d3e50', fg='#888888')
        self.opt_progress_label.pack()
        
        # Результаты
        opt_results_frame = tk.Frame(right_col, bg='#1e1e1e')
        opt_results_frame.pack(fill='both', expand=True, padx=10, pady=(10, 10))
        
        self.opt_results_text = tk.Text(opt_results_frame, font=('Consolas', 9),
                                       bg='#1e1e1e', fg='#ff9500',
                                       height=8, wrap='word')
        self.opt_results_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.opt_results_text.insert('1.0', 'Нажмите "Run Optimization" для поиска лучших параметров...')
        self.opt_results_text.config(state='disabled')
        
        # Кнопка применения лучшей конфигурации
        self.btn_apply_best = tk.Button(right_col, text="✓ Применить лучшую конфигурацию",
                                       command=self.apply_best_config,
                                       font=('Arial', 10, 'bold'),
                                       bg='#00d4aa', fg='white',
                                       relief='flat', cursor='hand2',
                                       width=25, height=1,
                                       state='disabled')
        self.btn_apply_best.pack(pady=(5, 10))
        
        # Переменная для хранения последних результатов оптимизации
        self.last_optimization_results = None
    
    def run_backtest_async(self):
        """Запуск бэктеста в фоновом потоке."""
        symbol = self.backtest_symbol.get()
        year = self.backtest_year.get()
        
        # Очищаем результаты
        self.backtest_results_text.config(state='normal')
        self.backtest_results_text.delete('1.0', 'end')
        self.backtest_results_text.insert('1.0', f'⏳ Запуск бэктеста {symbol} за {year}...\n')
        self.backtest_results_text.config(state='disabled')
        
        def run_backtest():
            try:
                # Импортируем здесь, чтобы не нагружать старт приложения
                from src.backtest.portfolio_backtester import PortfolioBacktester
                import pandas as pd
                
                self.root.after(0, lambda: self._update_backtest_text(f'📊 Загрузка данных...\n', append=True))
                
                # Загружаем данные
                data_path = f"data/backtest/{symbol}_H1_2023_2025.csv"
                if symbol == 'Portfolio':
                    # Для портфолио запускаем специальный бектест
                    backtester = PortfolioBacktester()
                    
                    start_date = f"{year}-01-01"
                    end_date = f"{int(year)+1}-01-01"
                    
                    self.root.after(0, lambda: self._update_backtest_text(f'🔄 Запуск портфолио бэктеста...\n', append=True))
                    result = backtester.run_backtest(start_date=start_date, end_date=end_date)
                    
                    # Преобразуем ключи Portfolio в стандартные
                    metrics = {
                        'total_return': result.get('roi', 0),
                        'win_rate': result.get('win_rate', 0),
                        'sharpe_ratio': 0,  # Portfolio не возвращает Sharpe
                        'max_drawdown': result.get('max_dd', 0),
                        'profit_factor': 0,  # Portfolio не возвращает PF
                        'total_trades': result.get('trades', 0)
                    }
                else:
                    # Одиночный инструмент
                    data = pd.read_csv(data_path)
                    data['time'] = pd.to_datetime(data['time'])
                    
                    # Фильтруем по году
                    data = data[(data['time'] >= f'{year}-01-01') & (data['time'] < f'{int(year)+1}-01-01')]
                    
                    self.root.after(0, lambda: self._update_backtest_text(f'📈 Данных: {len(data)} свечей\n', append=True))
                    self.root.after(0, lambda: self._update_backtest_text(f'🔄 Запуск бэктеста...\n', append=True))
                    
                    # Используем StrategyBacktester с настоящей стратегией
                    from src.backtest.strategy_backtester import StrategyBacktester
                    try:
                        from src.strategies.xauusd_strategy import StrategyXAUUSD
                        # EURUSD strategy removed - only XAUUSD remains
                    except ImportError:
                        from strategies.xauusd_strategy import StrategyXAUUSD
                        # EURUSD strategy removed - only XAUUSD remains
                    
                    # Создаем настоящую стратегию (только XAUUSD)
                    strategy = StrategyXAUUSD(symbol=symbol)
                    
                    backtester = StrategyBacktester(strategy=strategy, initial_balance=100)
                    result = backtester.run_backtest(start_date=f'{year}-01-01', end_date=f'{int(year)+1}-01-01')
                    
                    # Преобразуем ключи в стандартные
                    metrics = {
                        'total_return': result.get('roi', 0),
                        'win_rate': result.get('win_rate', 0),
                        'sharpe_ratio': 0,  # TODO: добавить расчет Sharpe
                        'max_drawdown': result.get('max_dd', 0),
                        'profit_factor': 0,  # TODO: добавить расчет PF
                        'total_trades': result.get('trades', 0)
                    }
                
                # Форматируем результаты
                result_text = f"\n{'='*40}\n✅ РЕЗУЛЬТАТЫ БЭКТЕСТА\n{'='*40}\n\n"
                result_text += f"📊 Symbol: {symbol}\n"
                result_text += f"📅 Period: {year}\n\n"
                result_text += f"💰 Total Return: {metrics.get('total_return', 0):.2f}%\n"
                result_text += f"🎯 Win Rate: {metrics.get('win_rate', 0):.2f}%\n"
                result_text += f"📈 Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
                result_text += f"📉 Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%\n"
                result_text += f"💵 Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"
                result_text += f"🔢 Total Trades: {metrics.get('total_trades', 0)}\n"
                result_text += f"\n✅ Бэктест завершен!\n"
                
                self.root.after(0, lambda: self._update_backtest_text(result_text, append=False))
                
            except Exception as e:
                error_text = f"\n❌ ОШИБКА: {str(e)}\n"
                self.root.after(0, lambda: self._update_backtest_text(error_text, append=True))
        
        # Запускаем в фоновом потоке
        threading.Thread(target=run_backtest, daemon=True).start()
    
    def _update_backtest_text(self, text, append=False):
        """Обновить текст результатов бэктеста."""
        self.backtest_results_text.config(state='normal')
        if not append:
            self.backtest_results_text.delete('1.0', 'end')
        self.backtest_results_text.insert('end', text)
        self.backtest_results_text.see('end')
        self.backtest_results_text.config(state='disabled')
    
    def run_optimization_async(self):
        """Запуск оптимизации в фоновом потоке."""
        symbol = self.backtest_symbol.get()
        year = self.backtest_year.get()
        method = self.opt_method.get()
        metric = self.opt_metric.get()
        iterations = self.opt_iterations.get()
        
        if symbol == 'Portfolio':
            self._update_opt_text('❌ Оптимизация портфолио пока не поддерживается.\nВыберите XAUUSD или EURUSD.', append=False)
            return
        
        # Очищаем результаты
        self._update_opt_text(f'⏳ Запуск оптимизации {symbol} ({method})...\n', append=False)
        self.opt_progress['value'] = 0
        self.opt_progress_label.config(text='0 / 0')
        
        def run_optimization():
            try:
                from src.backtest.optimizer import StrategyOptimizer
                import pandas as pd
                
                self.root.after(0, lambda: self._update_opt_text('📊 Запуск оптимизации...\n', append=True))
                
                # Создаем оптимизатор (без загрузки данных - это сделает StrategyBacktester)
                optimizer = StrategyOptimizer(
                    symbol=symbol, 
                    start_date=f'{year}-01-01', 
                    end_date=f'{int(year)+1}-01-01',
                    initial_balance=100
                )
                
                # Callback для прогресса
                def progress_callback(current, total):
                    percent = int(current / total * 100)
                    self.root.after(0, lambda: self.opt_progress.config(value=percent))
                    self.root.after(0, lambda: self.opt_progress_label.config(text=f'{current} / {total}'))
                
                # Запускаем оптимизацию
                if method == 'Grid Search':
                    # Уменьшенное пространство для быстроты
                    param_space = {
                        'atr_period': [14, 20],
                        'atr_multiplier': [1.5, 2.0, 2.5],
                        'risk_percent': [0.01, 0.02],
                        'min_rr': [1.5, 2.0]
                    }
                    top_configs = optimizer.optimize_grid_search(
                        param_space=param_space,
                        metric=metric,
                        top_n=3,
                        progress_callback=progress_callback
                    )
                else:  # Random Search
                    top_configs = optimizer.optimize_random_search(
                        n_iterations=iterations,
                        metric=metric,
                        top_n=3,
                        progress_callback=progress_callback
                    )
                
                # Форматируем результаты
                result_text = f"\n{'='*40}\n🏆 ТОП-3 КОНФИГУРАЦИИ\n{'='*40}\n\n"
                
                for idx, config in enumerate(top_configs[:3], 1):
                    params = config['params']
                    metrics = config['metrics']
                    score = config['score']
                    
                    result_text += f"#{idx} | Score: {score:.4f}\n"
                    result_text += f"Parameters:\n"
                    for k, v in params.items():
                        result_text += f"  {k}: {v}\n"
                    result_text += f"Metrics:\n"
                    result_text += f"  Return: {metrics.get('total_return', 0):.2f}%\n"
                    result_text += f"  Win Rate: {metrics.get('win_rate', 0):.2f}%\n"
                    result_text += f"  Sharpe: {metrics.get('sharpe_ratio', 0):.2f}\n"
                    result_text += f"  Max DD: {metrics.get('max_drawdown', 0):.2f}%\n"
                    result_text += f"\n"
                
                result_text += "✅ Оптимизация завершена!\n"
                
                self.root.after(0, lambda: self._update_opt_text(result_text, append=False))
                
                # Сохраняем лучшие результаты
                self.last_optimization_results = top_configs
                
                # Активируем кнопку применения
                self.root.after(0, lambda: self.btn_apply_best.config(state='normal'))
                
                # Сохраняем результаты в файл
                optimizer.save_results()
                
            except Exception as e:
                error_text = f"\n❌ ОШИБКА: {str(e)}\n"
                self.root.after(0, lambda: self._update_opt_text(error_text, append=True))
                import traceback
                traceback.print_exc()
        
        # Запускаем в фоновом потоке
        threading.Thread(target=run_optimization, daemon=True).start()
    
    def apply_best_config(self):
        """Применить лучшую конфигурацию из оптимизации."""
        if not self.last_optimization_results:
            messagebox.showwarning("Внимание", "Нет результатов оптимизации для применения!")
            return
        
        best_config = self.last_optimization_results[0]
        params = best_config['params']
        metrics = best_config['metrics']
        score = best_config['score']
        symbol = self.backtest_symbol.get()
        
        # Формируем сообщение с подтверждением
        msg = f"Применить лучшую конфигурацию?\n\n"
        msg += f"Symbol: {symbol}\n"
        msg += f"Score: {score:.4f}\n\n"
        msg += "Параметры:\n"
        for k, v in params.items():
            msg += f"  • {k}: {v}\n"
        msg += f"\nМетрики:\n"
        msg += f"  • Return: {metrics.get('total_return', 0):.2f}%\n"
        msg += f"  • Win Rate: {metrics.get('win_rate', 0):.2f}%\n"
        msg += f"  • Sharpe: {metrics.get('sharpe_ratio', 0):.2f}\n"
        msg += f"  • Max DD: {metrics.get('max_drawdown', 0):.2f}%\n\n"
        msg += "⚠️ Это обновит конфигурацию стратегии!"
        
        if not messagebox.askyesno("Подтверждение", msg):
            return
        
        try:
            # Сохраняем в файл конфигурации
            config_path = Path(f"config/{symbol.lower()}_optimized.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'score': score,
                'parameters': params,
                'metrics': metrics
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Успех", 
                              f"✅ Конфигурация сохранена!\n\n"
                              f"Файл: {config_path}\n\n"
                              f"Для применения перезапустите бота или обновите параметры стратегии вручную.\n\n"
                              f"Параметры:\n" + 
                              "\n".join([f"  {k}: {v}" for k, v in params.items()]))
            
            self.log(f"[OK] Лучшая конфигурация применена: {symbol}, Score: {score:.4f}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию:\n{e}")
            self.log(f"[ERROR] Failed to apply config: {e}")
    
    def _update_opt_text(self, text, append=False):
        """Обновить текст результатов оптимизации."""
        self.opt_results_text.config(state='normal')
        if not append:
            self.opt_results_text.delete('1.0', 'end')
        self.opt_results_text.insert('end', text)
        self.opt_results_text.see('end')
        self.opt_results_text.config(state='disabled')
    
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

            # Маленькая кнопка удалена - используем только большие кнопки
            # Быстрая кнопка удалена - обновляем только большую кнопку
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
        """Open a simple AI chat window for analyst/assistant consultations with screenshot support."""
        try:
            win = tk.Toplevel(self.root)
            win.title("AI Analyst Chat")
            win.geometry("700x500")
            win.configure(bg='#1a1a1a')

            # Переменная для хранения изображения
            current_image = {'path': None, 'base64': None}

            # Use grid so input area is always visible at bottom
            win.grid_rowconfigure(0, weight=1)
            win.grid_rowconfigure(1, weight=0)
            win.grid_columnconfigure(0, weight=1)

            chat_box = tk.Text(win, bg='#0f0f0f', fg='white', font=('Consolas', 11))
            chat_box.grid(row=0, column=0, sticky='nsew', padx=10, pady=(10, 5))
            chat_box.insert('end', "AI Analyst chat initialized. Type a question below and press Send.\n")
            chat_box.insert('end', "\n📸 Tip: Click 'Attach Screenshot' to upload MT5 chart for visual analysis.\n")
            chat_box.config(state='disabled')

            entry_frame = tk.Frame(win, bg='#1a1a1a')
            entry_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

            entry_var = tk.StringVar()
            entry = tk.Entry(entry_frame, textvariable=entry_var, font=('Arial', 11), bg='#0f0f0f', fg='white', insertbackground='white')
            entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
            entry.config(state='normal')
            # ensure input is visible and focused
            win.update_idletasks()
            entry.focus_force()
            entry.lift()
            entry.bind('<Return>', lambda e: send_message())

            def attach_screenshot():
                """Загрузка скриншота графика MT5 для анализа."""
                from tkinter import filedialog
                import base64
                
                file_path = filedialog.askopenfilename(
                    title="Select MT5 Screenshot",
                    filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
                )
                
                if file_path:
                    try:
                        # Читаем и кодируем изображение в base64
                        with open(file_path, 'rb') as image_file:
                            image_data = base64.b64encode(image_file.read()).decode('utf-8')
                        
                        current_image['path'] = file_path
                        current_image['base64'] = image_data
                        
                        # Отображаем в чате
                        chat_box.config(state='normal')
                        filename = file_path.split('/')[-1].split('\\')[-1]
                        chat_box.insert('end', f"\n📸 Screenshot attached: {filename}\n", 'image_tag')
                        chat_box.tag_config('image_tag', foreground='#00d4aa')
                        chat_box.config(state='disabled')
                        chat_box.see('end')
                        
                        self.log(f"[OK] Screenshot attached: {filename}")
                    except Exception as e:
                        self.log(f"[ERROR] Failed to load screenshot: {e}")
                        messagebox.showerror("Error", f"Failed to load image: {e}")

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
                        # Получаем актуальные новости
                        news_context = ""
                        try:
                            from src.ai.news_fetcher import get_news_fetcher
                            news_fetcher = get_news_fetcher()
                            
                            # Определяем инструмент из контекста
                            instrument = context.get('symbol', 'ALL')
                            if 'XAU' in instrument.upper() or 'GOLD' in instrument.upper():
                                instrument = 'XAUUSD'
                            elif 'EUR' in instrument.upper():
                                instrument = 'EURUSD'
                            
                            news_summary = news_fetcher.get_news_summary(instrument)
                            news_context = f"\n\n📰 АКТУАЛЬНЫЕ НОВОСТИ:\n{news_summary}\n"
                            app_logger.info(f"[OK] News context added to AI query")
                        except Exception as e:
                            app_logger.warning(f"Failed to fetch news: {e}")
                            news_context = "\n\n📰 АКТУАЛЬНАЯ ИНФОРМАЦИЯ:\nСегодня " + datetime.now().strftime('%d.%m.%Y') + ". Актуальное время UTC: " + datetime.now().strftime('%H:%M') + "\n"
                        
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

                                # Build messages - check if we have an image
                                if current_image['base64']:
                                    # Use vision model for image analysis
                                    model = 'gpt-4o'  # GPT-4 Vision support
                                    
                                    # Добавляем новости в контекст для анализа графика
                                    chart_prompt = msg if msg else "Проанализируй этот график MT5. Дай технический анализ: тренд, уровни поддержки/сопротивления, паттерны, точки входа/выхода и оценку риска."
                                    if news_context:
                                        chart_prompt += news_context + "\nУчти эти новости в своем анализе графика."
                                    
                                    messages = [
                                        {"role": "system", "content": f"You are an expert trading analyst with access to real-time market news. Today is {datetime.now().strftime('%d.%m.%Y %H:%M UTC')}. Analyze MT5 chart screenshots and provide detailed technical analysis including: trend direction, key support/resistance levels, chart patterns, entry/exit points, risk assessment, and consider economic news impact. Answer in Russian."},
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": chart_prompt
                                                },
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": f"data:image/png;base64,{current_image['base64']}"
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                    # Clear image after sending
                                    current_image['path'] = None
                                    current_image['base64'] = None
                                else:
                                    # Normal text-only message with news context
                                    system_prompt = f"You are an experienced trading analyst with access to real-time market data. Today is {datetime.now().strftime('%d.%m.%Y, %H:%M UTC')}. Provide accurate, helpful analysis based on current market conditions and economic events. Answer concisely in Russian."
                                    
                                    user_message = msg
                                    if news_context and any(keyword in msg.lower() for keyword in ['новост', 'событи', 'календар', 'today', 'сегодн', 'что происходит', 'что сейчас']):
                                        user_message += news_context
                                    
                                    messages = [
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": user_message}
                                    ]

                                # Try OpenAI-like SDK call used elsewhere in project
                                try:
                                    resp = llm.chat.completions.create(model=model, messages=messages, max_tokens=1500)
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

            # Кнопка для прикрепления скриншота
            attach_btn = tk.Button(entry_frame, text='📸 Attach Screenshot', command=attach_screenshot, 
                                  font=('Arial', 10), bg='#444444', fg='white', relief='raised', bd=2)
            attach_btn.pack(side='left', padx=(0, 5))
            
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
                    if hasattr(self, 'btn_close_trade'):
                        self.btn_close_trade.config(state='normal')
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
                if hasattr(self, 'btn_close_trade'):
                    self.btn_close_trade.config(state='disabled')
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
        
        # Лицензия (removed - free version)
        license_info = {"status": "Free Version", "expires": "Never", "valid": True, "type": "Free"}
        license_text = f"[LICENSE] {license_info.get('type', '').upper() or 'FREE'}"
        
        self.license_label = tk.Label(header, text=license_text,
                                     font=('Arial', 10),
                                     bg='#1a1a1a', fg='#00d4aa')
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
        
        # Улучшенный дизайн кнопки СТАРТ с градиентным эффектом
        self.btn_start = tk.Button(btn_frame, text="▶ СТАРТ", 
                                   command=self.start_bot,
                                   font=('Arial', 12, 'bold'),
                                   bg='#00d4aa', fg='#ffffff',
                                   width=14, height=2,
                                   relief='flat', cursor='hand2',
                                   bd=0, activebackground='#00ffcc')
        self.btn_start.pack(side='left', padx=8)
        
        # Улучшенный дизайн кнопки ПАУЗА
        self.btn_pause = tk.Button(btn_frame, text="⏸ ПАУЗА",
                                   command=self.pause_bot,
                                   font=('Arial', 12, 'bold'),
                                   bg='#f39c12', fg='#ffffff',
                                   width=14, height=2,
                                   relief='flat', cursor='hand2',
                                   state='disabled',
                                   bd=0, activebackground='#ffb347')
        self.btn_pause.pack(side='left', padx=8)
        
        # Улучшенный дизайн кнопки СТОП
        self.btn_stop = tk.Button(btn_frame, text="⏹ СТОП",
                                  command=self.stop_bot,
                                  font=('Arial', 12, 'bold'),
                                  bg='#ff4757', fg='#ffffff',
                                  width=14, height=2,
                                  relief='flat', cursor='hand2',
                                  state='disabled',
                                  bd=0, activebackground='#ff6b7a')
        self.btn_stop.pack(side='left', padx=8)
        
        # Улучшенная кнопка активации с современным дизайном
        self.btn_activate = tk.Button(btn_frame, text="🔑 Ключ",
                                      command=self.show_activation_dialog,
                                      font=('Arial', 11, 'bold'),
                                      bg='#6c63ff', fg='white',
                                      width=10, height=2,
                                      relief='flat', cursor='hand2',
                                      bd=0, activebackground='#8a82ff')
        self.btn_activate.pack(side='left', padx=15)
        
        # Улучшенная кнопка MT5
        self.btn_mt5 = tk.Button(btn_frame, text="[MT5] MT5",
                                 command=self.show_mt5_dialog,
                                 font=('Arial', 11, 'bold'),
                                 bg='#34495e', fg='white',
                                 width=10, height=2,
                                 relief='flat', cursor='hand2',
                                 bd=0, activebackground='#4a6278')
        self.btn_mt5.pack(side='left', padx=5)
        
        # Улучшенная кнопка настроек
        self.btn_settings = tk.Button(btn_frame, text="⚙ Настройки",
                                      command=self.show_settings_dialog,
                                      font=('Arial', 11, 'bold'),
                                      bg='#34495e', fg='white',
                                      width=12, height=2,
                                      relief='flat', cursor='hand2',
                                      bd=0, activebackground='#4a6278')
        self.btn_settings.pack(side='left', padx=5)
        
        # ===== TRADING MODE TOGGLE =====
        # Добавляем переключатель режима торговли
        mode_toggle_frame = tk.Frame(control, bg='#2a2a2a', relief='flat')
        mode_toggle_frame.pack(pady=15)
        
        tk.Label(mode_toggle_frame, text="🎯 Режим торговли:",
                font=('Arial', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left', padx=10)
        
        # Переменная для хранения режима
        self.trading_mode = tk.StringVar(value="strategy")  # "strategy" или "pure_ai"
        
        # Radio buttons с улучшенным дизайном
        strategy_radio = tk.Radiobutton(
            mode_toggle_frame,
            text="⚡ Strategy + AI  (Стратегия + GPT фильтр)",
            variable=self.trading_mode,
            value="strategy",
            font=('Arial', 11, 'bold'),
            bg='#2a2a2a', fg='#00d4aa',
            selectcolor='#1a1a1a',
            activebackground='#2a2a2a',
            activeforeground='#00ffcc',
            command=self._on_trading_mode_change
        )
        strategy_radio.pack(side='left', padx=10)
        
        pure_ai_radio = tk.Radiobutton(
            mode_toggle_frame,
            text="🤖 Pure AI Trading  (Только GPT сигналы)",
            variable=self.trading_mode,
            value="pure_ai",
            font=('Arial', 11, 'bold'),
            bg='#2a2a2a', fg='#5b7dff',
            selectcolor='#1a1a1a',
            activebackground='#2a2a2a',
            activeforeground='#7a96ff',
            command=self._on_trading_mode_change
        )
        pure_ai_radio.pack(side='left', padx=10)
        
        # Индикатор текущего режима
        self.mode_indicator = tk.Label(mode_toggle_frame, 
                                       text="[Активен]",
                                       font=('Arial', 10, 'bold'),
                                       bg='#2a2a2a', fg='#00d4aa')
        self.mode_indicator.pack(side='left', padx=10)
        
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
        
        # ===== MANUAL TRADING =====
        if self.manual_controller and self.manual_controller.is_enabled():
            self.create_manual_trading_section()
        
        # ===== AI ANALYSIS =====
        self.create_ai_analysis_section()
        
        # Создаем заглушку для log_text (используем только мини-логи в Manual Trading)
        self.log_text = None
        
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
        """Вставка сообщения в лог с цветом - только в мини-логи Manual Trading."""
        # Добавляем timestamp
        timestamp = datetime.now().strftime('[%H:%M:%S]')
        formatted_message = f"{timestamp} {message}"
        
        # Пишем только в мини-логи Manual Trading
        if hasattr(self, 'mini_logs_text') and self.mini_logs_text:
            try:
                self.mini_logs_text.config(state='normal')
                self.mini_logs_text.insert('end', formatted_message + '\n', level.lower())
                self.mini_logs_text.see('end')
                self.mini_logs_text.config(state='disabled')
            except Exception as e:
                print(f"Error inserting mini log message: {e}")
    
    def create_stat_card(self, parent, title, value):
        """Создание карточки статистики с улучшенным дизайном."""
        card = tk.Frame(parent, bg='#2d3e50', relief='flat', bd=0)
        
        # Заголовок с градиентным цветом
        tk.Label(card, text=title, font=('Arial', 11, 'bold'),
                bg='#2d3e50', fg='#95a5a6').pack(pady=(12, 0))
        
        # Значение - более крупный и контрастный шрифт
        value_label = tk.Label(card, text=value, font=('Arial', 18, 'bold'),
                              bg='#2d3e50', fg='#ecf0f1')
        value_label.pack(pady=(0, 12))
        
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
            # Блокируем manual trading (маленькая кнопка удалена)
            if hasattr(self, 'btn_predict'):
                self.btn_predict.config(state='disabled')
        else:
            self.status_dot.config(fg='#ff4757')
            self.status_label.config(text='Остановлен')
            self.btn_start.config(state='normal')
            self.btn_pause.config(state='disabled', text='⏸ ПАУЗА')
            self.btn_stop.config(state='disabled')
            # Разблокируем manual trading
            # Маленькая кнопка удалена
            if hasattr(self, 'btn_predict'):
                self.btn_predict.config(state='normal')
    
    def start_bot(self):
        """Запуск бота."""
        # Проверка лицензии
        valid, msg = True, "Free version"
        if not valid:
            messagebox.showerror("Ошибка", f"Лицензия недействительна: {msg}")
            return
        
        mode = 'live'  # Фиксирован на Live режиме
        
        # Подтверждение для Live торговли
        if not messagebox.askyesno("Подтверждение", 
                "Вы уверены что хотите запустить LIVE торговлю?\n\n"
                "Будут открываться РЕАЛЬНЫЕ сделки!"):
            return
        
        # Получаем выбранный режим торговли
        trading_mode = self.trading_mode.get()  # "strategy" или "pure_ai"
        
        # Используем bot_manager для старта (с telegram уведомлением)
        if self.bot_manager:
            success = self.bot_manager.start(mode=mode, trading_mode=trading_mode)
            if success:
                self.update_status(True, False)
                self.log(f"[LAUNCH] Bot started in {mode.upper()} mode | Trading: {trading_mode.upper()}")
            else:
                messagebox.showerror("Ошибка", "Не удалось запустить бота")
        else:
            # Fallback если bot_manager недоступен
            self.stop_event.clear()
            self.bot_thread = threading.Thread(target=self.run_bot, args=(mode,), daemon=True)
            self.bot_thread.start()
            
            self.update_status(True, False)
            self.log(f"[LAUNCH] Bot started in {mode.upper()} mode")
    
    def stop_bot(self):
        """Остановка бота."""
        # Используем bot_manager для остановки (с telegram уведомлением)
        if self.bot_manager:
            self.bot_manager.stop()
        
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
    
    def _on_trading_mode_change(self):
        """Обработчик переключения режима торговли."""
        mode = self.trading_mode.get()
        
        if mode == "strategy":
            # Режим Strategy + AI
            self.log("=" * 60)
            self.log("[MODE] ⚡ Переключено на режим: Strategy + AI")
            self.log("[MODE] Бот торгует по стратегии с GPT фильтрацией")
            self.log("=" * 60)
            
            # Останавливаем Pure AI Trader если запущен
            if self.pure_ai_trader and hasattr(self.pure_ai_trader, 'running') and self.pure_ai_trader.running:
                self.pure_ai_trader.stop()
                self.log("[PureAI] Pure AI Trader остановлен")
            
            # Обновляем индикатор
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="[Активен]", fg='#00d4aa')
        
        elif mode == "pure_ai":
            # Режим Pure AI Trading
            self.log("=" * 60)
            self.log("[MODE] 🤖 Переключено на режим: Pure AI Trading")
            self.log("[MODE] Бот торгует только по сигналам GPT (каждые 2 часа)")
            self.log("[MODE] Символы: XAUUSD, EURUSD | Таймфрейм: 15M")
            self.log("=" * 60)
            
            # Проверяем доступность
            if not self.pure_ai_trader:
                self.log("[ERROR] Pure AI Trader не инициализирован!")
                self.log("[ERROR] Проверьте OPENAI_API_KEY в настройках")
                messagebox.showerror("Ошибка", 
                    "Pure AI Trader недоступен!\n\n"
                    "Убедитесь что:\n"
                    "1. Установлен OPENAI_API_KEY\n"
                    "2. Модуль src/ai/pure_ai_trader.py доступен")
                # Возвращаем на Strategy mode
                self.trading_mode.set("strategy")
                return
            
            # Запускаем Pure AI Trader если бот активен
            if self.bot_running and not self.bot_paused:
                # Устанавливаем executor если доступен
                if hasattr(self, 'trader') and hasattr(self.trader, 'executor'):
                    self.pure_ai_trader.executor = self.trader.executor
                    self.log("[PureAI] Executor подключен")
                
                # Запускаем
                self.pure_ai_trader.start()
                self.log("[PureAI] ✅ Pure AI Trader запущен")
                
                # Выводим статус
                status = self.pure_ai_trader.get_status()
                self.log(f"[PureAI] Интервал анализа: {status['analysis_interval']}")
                self.log(f"[PureAI] Макс. сделок в день: {status['max_trades_per_day']}")
            else:
                self.log("[PureAI] Будет активирован при запуске бота")
            
            # Обновляем индикатор
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="[Активен]", fg='#5b7dff')
    
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
            
            # Запускаем Pure AI Trader если выбран соответствующий режим
            if self.trading_mode.get() == "pure_ai" and self.pure_ai_trader:
                self.pure_ai_trader.executor = self.trader.executor
                self.pure_ai_trader.start()
                self.log("[PureAI] ✅ Pure AI Trader started in background")
            
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
            rr = float(self.manual_rr.get())
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
        # Добавляем timestamp
        timestamp = datetime.now().strftime('[%H:%M:%S]')
        formatted_message = f"{timestamp} {message}"
        
        # Основные логи внизу
        if hasattr(self, 'log_text') and self.log_text:
            try:
                self.log_text.configure(state='normal')
                self.log_text.insert('end', formatted_message + '\n', level.lower())
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

                    self.mini_logs_text.insert('end', formatted_message + '\n', level.lower())
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
    
    # ========== AI ANALYSIS SECTION ==========
    
    def create_ai_analysis_section(self):
        """Create AI Market Analysis section."""
        if not AI_ANALYSIS_AVAILABLE or not self.ai_scheduler:
            return
        
        # Main container
        ai_container = tk.Frame(self.root, bg='#1a1a1a')
        ai_container.pack(fill='both', expand=False, padx=20, pady=10)
        
        # Header
        header_frame = tk.Frame(ai_container, bg='#1a1a1a')
        header_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(header_frame, text="🤖 AI Market Analyst", 
                font=('Arial', 16, 'bold'), bg='#1a1a1a', fg='#FFFFFF').pack(side='left')
        
        # Manual trigger button
        self.ai_analyze_button = tk.Button(
            header_frame, text="▶️ Analyze Now", command=self._trigger_ai_analysis,
            bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=15, pady=5
        )
        self.ai_analyze_button.pack(side='right', padx=5)
        
        # Status label
        self.ai_status_label = tk.Label(
            header_frame, text="● Idle", font=('Arial', 10),
            bg='#1a1a1a', fg='#888888'
        )
        self.ai_status_label.pack(side='right', padx=10)
        
        # Content frame (2 columns)
        content_frame = tk.Frame(ai_container, bg='#1a1a1a')
        content_frame.pack(fill='both', expand=False)
        
        # LEFT: Analysis summary
        left_frame = tk.Frame(content_frame, bg='#2b2b2b', relief='solid', bd=1)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="📊 Analysis Summary", 
                font=('Arial', 11, 'bold'), bg='#2b2b2b', fg='#FFFFFF').pack(pady=5)
        
        # Sentiment
        sentiment_frame = tk.Frame(left_frame, bg='#2b2b2b')
        sentiment_frame.pack(fill='x', padx=10, pady=3)
        tk.Label(sentiment_frame, text="Sentiment:", 
                font=('Arial', 9), bg='#2b2b2b', fg='#888888').pack(side='left')
        self.ai_sentiment_label = tk.Label(
            sentiment_frame, text="N/A", font=('Arial', 9, 'bold'),
            bg='#2b2b2b', fg='#FFFFFF'
        )
        self.ai_sentiment_label.pack(side='right')
        
        # Confidence
        conf_frame = tk.Frame(left_frame, bg='#2b2b2b')
        conf_frame.pack(fill='x', padx=10, pady=3)
        tk.Label(conf_frame, text="Confidence:", 
                font=('Arial', 9), bg='#2b2b2b', fg='#888888').pack(side='left')
        self.ai_confidence_label = tk.Label(
            conf_frame, text="0%", font=('Arial', 9, 'bold'),
            bg='#2b2b2b', fg='#FFFFFF'
        )
        self.ai_confidence_label.pack(side='right')
        
        # Block status
        block_frame = tk.Frame(left_frame, bg='#2b2b2b')
        block_frame.pack(fill='x', padx=10, pady=3)
        tk.Label(block_frame, text="Trading:", 
                font=('Arial', 9), bg='#2b2b2b', fg='#888888').pack(side='left')
        self.ai_block_label = tk.Label(
            block_frame, text="✓ Allowed", font=('Arial', 9, 'bold'),
            bg='#2b2b2b', fg='#4CAF50'
        )
        self.ai_block_label.pack(side='right')
        
        # Risk multiplier
        risk_frame = tk.Frame(left_frame, bg='#2b2b2b')
        risk_frame.pack(fill='x', padx=10, pady=3)
        tk.Label(risk_frame, text="Risk Factor:", 
                font=('Arial', 9), bg='#2b2b2b', fg='#888888').pack(side='left')
        self.ai_risk_label = tk.Label(
            risk_frame, text="1.0x", font=('Arial', 9, 'bold'),
            bg='#2b2b2b', fg='#FFFFFF'
        )
        self.ai_risk_label.pack(side='right')
        
        # Last update
        time_frame = tk.Frame(left_frame, bg='#2b2b2b')
        time_frame.pack(fill='x', padx=10, pady=3)
        tk.Label(time_frame, text="Updated:", 
                font=('Arial', 9), bg='#2b2b2b', fg='#888888').pack(side='left')
        self.ai_time_label = tk.Label(
            time_frame, text="Never", font=('Arial', 8),
            bg='#2b2b2b', fg='#666666'
        )
        self.ai_time_label.pack(side='right')
        
        # RIGHT: Active signals
        right_frame = tk.Frame(content_frame, bg='#2b2b2b', relief='solid', bd=1)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        tk.Label(right_frame, text="📍 Active Signals", 
                font=('Arial', 11, 'bold'), bg='#2b2b2b', fg='#FFFFFF').pack(pady=5)
        
        # Signals list with scrollbar
        signals_container = tk.Frame(right_frame, bg='#2b2b2b')
        signals_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(signals_container, bg='#3b3b3b')
        scrollbar.pack(side='right', fill='y')
        
        self.ai_signals_listbox = tk.Listbox(
            signals_container, yscrollcommand=scrollbar.set,
            bg='#1a1a1a', fg='#FFFFFF', font=('Consolas', 8),
            selectmode='single', height=5, relief='flat', bd=0
        )
        self.ai_signals_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.ai_signals_listbox.yview)
        
        # Bind click event to show signal details
        self.ai_signals_listbox.bind('<<ListboxSelect>>', self._on_signal_selected)
        
        # Initial update
        self._update_ai_display()
    
    def _trigger_ai_analysis(self):
        """Trigger AI analysis manually."""
        if not self.ai_scheduler:
            messagebox.showwarning("AI Unavailable", "AI Analysis system not initialized")
            return
        
        self.ai_status_label.config(text="● Running...", fg='#FFA500')
        self.ai_analyze_button.config(state='disabled')
        
        def run():
            try:
                result = self.ai_scheduler.run_now()
                self.root.after(0, lambda: self._on_ai_analysis_complete(result))
            except Exception as e:
                self.root.after(0, lambda: self._on_ai_analysis_error(str(e)))
        
        threading.Thread(target=run, daemon=True).start()
    
    def _on_ai_analysis_update(self, analysis: dict):
        """Callback when scheduled analysis completes."""
        self.root.after(0, lambda: self._on_ai_analysis_complete(analysis))
    
    def _on_ai_analysis_complete(self, analysis: dict):
        """Handle completed analysis."""
        self.ai_analyze_button.config(state='normal')
        self.ai_status_label.config(text="● Ready", fg='#4CAF50')
        
        # Force immediate update
        self._update_ai_display()
        
        # Log summary
        signals = analysis.get('signals', [])
        self.log(f"[AI] ═══════════ ANALYSIS COMPLETE ═══════════")
        self.log(f"[AI] Signals detected: {len(signals)}")
        
        # Log sentiment and blocks
        summary = analysis.get('summary', {})
        sentiment = summary.get('sentiment', 'N/A')
        confidence = summary.get('confidence', 0)
        self.log(f"[AI] Market Sentiment: {sentiment.upper()} | Confidence: {confidence}%")
        
        # Log block details from analysis
        blocks = analysis.get('trading_blocks', {})
        block_type_from_gpt = blocks.get('block_type', 'none')
        block_reason_from_gpt = blocks.get('reason', 'Not specified')
        
        self.log(f"[AI] ─────────────────────────────────────")
        self.log(f"[AI] GPT Analysis:")
        self.log(f"[AI]   Block Type: {block_type_from_gpt.upper()}")
        self.log(f"[AI]   Reason: {block_reason_from_gpt}")
        
        # Display detailed structured analysis (7 sections in Russian)
        analysis_sections = analysis.get('analysis', {})
        if isinstance(analysis_sections, dict) and len(analysis_sections) > 0:
            self.log(f"[AI] ─────────────────────────────────────")
            self.log(f"[AI] Подробный анализ (7 разделов):")
            
            if 'trend' in analysis_sections:
                self.log(f"[AI] {analysis_sections['trend']}")
            if 'support_resistance' in analysis_sections:
                self.log(f"[AI] {analysis_sections['support_resistance']}")
            if 'patterns' in analysis_sections:
                self.log(f"[AI] {analysis_sections['patterns']}")
            if 'entry_exit' in analysis_sections:
                self.log(f"[AI] {analysis_sections['entry_exit']}")
            if 'risk_assessment' in analysis_sections:
                self.log(f"[AI] {analysis_sections['risk_assessment']}")
            if 'news_impact' in analysis_sections:
                self.log(f"[AI] {analysis_sections['news_impact']}")
            if 'recommendation' in analysis_sections:
                self.log(f"[AI] {analysis_sections['recommendation']}")
        
        # Check actual permission from SignalManager
        if self.ai_signal_manager:
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission("XAUUSD")
            block_type_actual = self.ai_signal_manager.block_type.value if self.ai_signal_manager.block_type else "none"
            
            self.log(f"[AI] ─────────────────────────────────────")
            self.log(f"[AI] SignalManager Decision:")
            self.log(f"[AI]   Block Type: {block_type_actual.upper()}")
            self.log(f"[AI]   Status: {'✅ ALLOWED' if allowed else '🚫 BLOCKED'}")
            self.log(f"[AI]   Risk Multiplier: {multiplier:.2f}x")
            self.log(f"[AI]   Reason: {reason}")
            
            # Warn if mismatch
            if block_type_from_gpt != block_type_actual:
                self.log(f"[AI] ⚠️  WARNING: Block type mismatch!")
                self.log(f"[AI]   GPT said: {block_type_from_gpt}")
                self.log(f"[AI]   Manager has: {block_type_actual}")
        
        self.log(f"[AI] ─────────────────────────────────────")
        
        # Log each signal with reasoning
        for i, signal in enumerate(signals, 1):
            sig_type = signal.get('type', 'N/A').upper()
            entry = signal.get('entry_price', 0)
            sl = signal.get('stop_loss', 0)
            tp = signal.get('take_profit', 0)
            conf = signal.get('confidence', 0)
            reasoning = signal.get('reasoning', 'No reasoning provided')
            
            self.log(f"[AI] Signal #{i}: {sig_type} @ {entry:.2f} (SL:{sl:.2f} TP:{tp:.2f}) Conf:{conf}%")
            self.log(f"[AI] └─ Reason: {reasoning}")
        
        self.log(f"[AI] ═══════════════════════════════════════")
    
    def _on_ai_analysis_error(self, error: str):
        """Handle analysis error."""
        self.ai_analyze_button.config(state='normal')
        self.ai_status_label.config(text="● Error", fg='#F44336')
        self.log(f"[AI] Analysis failed: {error}")
    
    def _update_ai_display(self):
        """Update AI display with current state."""
        if not self.ai_signal_manager:
            return
        
        try:
            # Get current state
            allowed, multiplier, reason = self.ai_signal_manager.get_trading_permission("XAUUSD")
            signals = self.ai_signal_manager.get_active_signals("XAUUSD")
            block_type = self.ai_signal_manager.block_type.value if self.ai_signal_manager.block_type else "none"
            
            # Update sentiment
            sentiment_map = {
                "none": ("✓ Clear", "#4CAF50"),
                "bias": ("↗ Bullish Bias", "#2196F3"),
                "warning": ("⚠ Caution", "#FFA500"),
                "soft_block": ("⛔ Soft Block", "#FF5722"),
                "hard_block": ("🚫 Hard Block", "#F44336")
            }
            sentiment, color = sentiment_map.get(block_type, ("N/A", "#888888"))
            self.ai_sentiment_label.config(text=sentiment, fg=color)
            
            # Update confidence (from latest signal or 0)
            if signals:
                conf = max(s['confidence'] for s in signals)
                self.ai_confidence_label.config(text=f"{conf}%")
            else:
                self.ai_confidence_label.config(text="0%")
            
            # Update block status
            if allowed:
                self.ai_block_label.config(text="✓ Allowed", fg='#4CAF50')
            else:
                self.ai_block_label.config(text=f"⛔ {reason}", fg='#F44336')
            
            # Update risk multiplier
            self.ai_risk_label.config(text=f"{multiplier:.1f}x")
            
            # Update time
            if self.ai_signal_manager.latest_analysis_time:
                try:
                    if isinstance(self.ai_signal_manager.latest_analysis_time, str):
                        dt = datetime.fromisoformat(self.ai_signal_manager.latest_analysis_time)
                        time_str = dt.strftime("%H:%M")
                    else:
                        time_str = self.ai_signal_manager.latest_analysis_time.strftime("%H:%M")
                    self.ai_time_label.config(text=time_str)
                except:
                    pass
            
            # Update signals list
            self.ai_signals_listbox.delete(0, 'end')
            self.ai_signals_data = []  # Clear old data
            if signals:
                for sig in signals:
                    # Store full signal data
                    self.ai_signals_data.append(sig)
                    
                    # Calculate confidence with decay
                    created_at = datetime.fromisoformat(sig['created_at'])
                    expires_at = datetime.fromisoformat(sig['expires_at'])
                    lifetime = (expires_at - created_at).total_seconds()
                    age = (datetime.now() - created_at).total_seconds()
                    decay_factor = 1.0 - (age / lifetime) * 0.5 if lifetime > 0 else 1.0
                    decay_factor = max(0.5, min(1.0, decay_factor))
                    conf_with_decay = sig['confidence'] * decay_factor
                    
                    line = f"{sig['type'].upper():4} @ {sig['entry_price']:.2f} | SL:{sig['stop_loss']:.2f} TP:{sig['take_profit']:.2f} | {conf_with_decay:.0f}%"
                    self.ai_signals_listbox.insert('end', line)
            else:
                self.ai_signals_listbox.insert('end', "No active signals")
        except Exception as e:
            app_logger.error(f"[AI] Display update failed: {e}")
    
    def _schedule_ai_update(self):
        """Schedule periodic AI display update."""
        try:
            if self.ai_signal_manager:
                self._update_ai_display()
                # Schedule next update in 5 seconds
                self.root.after(5000, self._schedule_ai_update)
        except Exception as e:
            app_logger.error(f"[AI] Schedule update failed: {e}")
    
    def _on_signal_selected(self, event):
        """Handle signal selection - show reasoning in logs."""
        try:
            selection = self.ai_signals_listbox.curselection()
            if not selection:
                return
            
            idx = selection[0]
            if idx >= len(self.ai_signals_data):
                return
            
            signal = self.ai_signals_data[idx]
            
            # Log full signal details
            self.log(f"[AI] ═══════════════════════════════════════")
            self.log(f"[AI] Signal Details #{idx + 1}:")
            self.log(f"[AI] Type: {signal['type'].upper()}")
            self.log(f"[AI] Entry: {signal['entry_price']:.2f}")
            self.log(f"[AI] Stop Loss: {signal['stop_loss']:.2f}")
            self.log(f"[AI] Take Profit: {signal['take_profit']:.2f}")
            self.log(f"[AI] Confidence: {signal['confidence']}%")
            self.log(f"[AI] Risk/Reward: {signal.get('risk_reward', 'N/A')}")
            
            # Log trigger time if present
            trigger_time = signal.get('trigger_time')
            if trigger_time:
                self.log(f"[AI] Trigger Time: {trigger_time}")
            
            # Log reasoning
            reasoning = signal.get('reasoning', 'No reasoning provided')
            self.log(f"[AI] ─────────────────────────────────────")
            self.log(f"[AI] REASONING:")
            self.log(f"[AI] {reasoning}")
            self.log(f"[AI] ═══════════════════════════════════════")
            
        except Exception as e:
            app_logger.error(f"[AI] Signal selection error: {e}")


def main():
    app = BazaApp()
    app.run()


if __name__ == '__main__':
    main()
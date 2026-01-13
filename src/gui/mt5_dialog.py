#!/usr/bin/env python3
"""
MT5 Connection Dialog - Настройки подключения к MT5
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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


class MT5Dialog:
    """Диалог настроек MT5"""
    
    def __init__(self, parent, mt5_manager, on_save_callback):
        self.parent = parent
        self.mt5_manager = mt5_manager
        self.on_save_callback = on_save_callback
        self.config = {}
        
        # Создать окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🔌 MT5 Connection")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg=Colors.BG_DARK)
        self.dialog.resizable(False, False)
        
        # Сделать модальным
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Загрузить конфиг
        self._load_config()
        
        # Создать UI
        self._create_ui()
        
        # Центрировать окно
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _load_config(self):
        """Загрузить конфиг MT5"""
        try:
            config_path = Path('config') / 'mt5.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                self.config = {}
        except Exception as e:
            logger.error(f"[MT5] Failed to load config: {e}")
            messagebox.showerror("Error", f"Failed to load MT5 config: {e}")
    
    def _create_ui(self):
        """Создать UI"""
        # Header
        header = tk.Frame(self.dialog, bg=Colors.BG_PANEL, height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🔌 MT5 Connection",
                font=('Arial', 14, 'bold'),
                bg=Colors.BG_PANEL,
                fg=Colors.TEXT_PRIMARY).pack(side='left', padx=20, pady=15)
        
        # Status indicator
        self.status_label = tk.Label(header, 
                                     text="● Disconnected",
                                     font=('Arial', 10, 'bold'),
                                     bg=Colors.BG_PANEL,
                                     fg=Colors.ERROR)
        self.status_label.pack(side='right', padx=20)
        
        # Update status
        if self.mt5_manager and self.mt5_manager.is_connected():
            self.status_label.config(text="● Connected", fg=Colors.SUCCESS)
        
        # Separator
        tk.Frame(self.dialog, bg=Colors.BORDER, height=1).pack(fill='x')
        
        # Content
        content = tk.Frame(self.dialog, bg=Colors.BG_DARK)
        content.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Connection Settings
        self._create_section(content, "Connection Settings")
        
        # Получить connection данные из структуры
        connection_config = self.config.get('mt5', {}).get('connection', {})
        
        # Login
        login_frame = self._create_field_row(content, "Login:")
        self.login_entry = tk.Entry(login_frame, font=('Arial', 11), width=25)
        self.login_entry.insert(0, str(connection_config.get('login', '')))
        self.login_entry.pack(side='right')
        
        # Password
        password_frame = self._create_field_row(content, "Password:")
        self.password_entry = tk.Entry(password_frame, font=('Arial', 11), width=25, show='*')
        self.password_entry.insert(0, connection_config.get('password', ''))
        self.password_entry.pack(side='right')
        
        # Server
        server_frame = self._create_field_row(content, "Server:")
        self.server_entry = tk.Entry(server_frame, font=('Arial', 11), width=25)
        self.server_entry.insert(0, connection_config.get('server', ''))
        self.server_entry.pack(side='right')
        
        # MT5 Path
        self._create_section(content, "MT5 Installation")
        
        path_frame = tk.Frame(content, bg=Colors.BG_DARK)
        path_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(path_frame, text="MT5 Path:",
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY).pack(side='left')
        
        path_input_frame = tk.Frame(path_frame, bg=Colors.BG_DARK)
        path_input_frame.pack(side='right')
        
        self.path_entry = tk.Entry(path_input_frame, font=('Arial', 10), width=28)
        self.path_entry.insert(0, connection_config.get('path', 'C:\\Program Files\\MetaTrader 5'))
        self.path_entry.pack(side='left', padx=(0, 5))
        
        tk.Button(path_input_frame, text="Browse",
                 font=('Arial', 9),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 relief='flat',
                 padx=10, pady=3,
                 command=self._browse_mt5_path).pack(side='left')
        
        # Warning
        warning_frame = tk.Frame(content, bg=Colors.BG_CARD, 
                                highlightbackground=Colors.WARNING,
                                highlightthickness=1)
        warning_frame.pack(fill='x', pady=(20, 0))
        
        tk.Label(warning_frame, 
                text="⚠ Warning: Make sure MT5 terminal is running before testing connection!",
                font=('Arial', 9),
                bg=Colors.BG_CARD,
                fg=Colors.WARNING,
                wraplength=500).pack(padx=15, pady=10)
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg=Colors.BG_DARK)
        button_frame.pack(fill='x', padx=30, pady=(0, 30))
        
        tk.Button(button_frame, text="Cancel",
                 font=('Arial', 11),
                 bg=Colors.BG_CARD,
                 fg=Colors.TEXT_PRIMARY,
                 relief='flat',
                 padx=20, pady=10,
                 command=self.dialog.destroy).pack(side='right', padx=(10, 0))
        
        tk.Button(button_frame, text="Save",
                 font=('Arial', 11, 'bold'),
                 bg=Colors.SUCCESS,
                 fg='white',
                 relief='flat',
                 padx=20, pady=10,
                 command=self._save_config).pack(side='right', padx=(10, 0))
        
        tk.Button(button_frame, text="Test Connection",
                 font=('Arial', 11),
                 bg=Colors.WARNING,
                 fg='white',
                 relief='flat',
                 padx=20, pady=10,
                 command=self._test_connection).pack(side='right')
    
    def _create_section(self, parent, title):
        """Создать секцию"""
        frame = tk.Frame(parent, bg=Colors.BG_DARK)
        frame.pack(fill='x', pady=(20, 10))
        
        tk.Label(frame, text=title,
                font=('Arial', 11, 'bold'),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_PRIMARY).pack(anchor='w')
        
        tk.Frame(frame, bg=Colors.BORDER, height=1).pack(fill='x', pady=(5, 0))
    
    def _create_field_row(self, parent, label):
        """Создать строку с полем"""
        frame = tk.Frame(parent, bg=Colors.BG_DARK)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=label,
                font=('Arial', 10),
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_SECONDARY,
                width=12,
                anchor='w').pack(side='left')
        
        return frame
    
    def _browse_mt5_path(self):
        """Выбрать путь к MT5"""
        path = filedialog.askdirectory(
            title="Select MT5 Installation Directory",
            initialdir=self.path_entry.get()
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    def _test_connection(self):
        """Тестировать подключение"""
        try:
            login = self.login_entry.get().strip()
            password = self.password_entry.get().strip()
            server = self.server_entry.get().strip()
            path = self.path_entry.get().strip()
            
            if not login or not password or not server:
                messagebox.showwarning("Warning", "Please fill all connection fields!")
                return
            
            logger.info("[MT5] Testing connection...")
            
            # Попытка подключения
            from src.core.mt5_manager import MT5Manager
            
            test_manager = MT5Manager()
            
            # Инициализировать MT5
            if not test_manager.initialize(path):
                raise Exception("Failed to initialize MT5. Make sure MT5 terminal is running.")
            
            # Подключиться к счету
            success, message = test_manager.connect(
                login=int(login) if login.isdigit() else login,
                password=password,
                server=server
            )
            
            if success:
                account_info = test_manager.get_account_info()
                if account_info:
                    balance = account_info.get('balance', 0)
                    equity = account_info.get('equity', 0)
                    server_name = account_info.get('server', 'Unknown')
                    
                    self.status_label.config(text="● Connected", fg=Colors.SUCCESS)
                    
                    info_msg = f"✅ Connection successful!\n\n"
                    info_msg += f"Server: {server_name}\n"
                    info_msg += f"Balance: ${balance:.2f}\n"
                    info_msg += f"Equity: ${equity:.2f}"
                    
                    messagebox.showinfo("Connection Test", info_msg)
                    logger.info("[MT5] Connection test successful")
                    
                    # НЕ отключаемся! MT5 singleton - разрыв убьёт основное соединение
                    # test_manager просто освободится из памяти
                else:
                    raise Exception("Could not get account info")
            else:
                raise Exception(message)
                
        except Exception as e:
            self.status_label.config(text="● Disconnected", fg=Colors.ERROR)
            logger.error(f"[MT5] Connection test failed: {e}")
            messagebox.showerror("Connection Failed", 
                               f"Failed to connect to MT5:\n{e}\n\nMake sure:\n• MT5 terminal is running\n• Credentials are correct\n• Server is available")
    
    def _save_config(self):
        """Сохранить конфиг"""
        try:
            login = self.login_entry.get().strip()
            password = self.password_entry.get().strip()
            server = self.server_entry.get().strip()
            path = self.path_entry.get().strip()
            
            if not login or not server:
                messagebox.showwarning("Warning", "Login and Server are required!")
                return
            
            # Загрузить полный конфиг из файла
            config_path = Path('config') / 'mt5.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f) or {}
            else:
                full_config = {}
            
            # Обновить только connection поля
            if 'mt5' not in full_config:
                full_config['mt5'] = {}
            if 'connection' not in full_config['mt5']:
                full_config['mt5']['connection'] = {}
            
            # Обновить данные подключения
            full_config['mt5']['connection']['login'] = int(login) if login.isdigit() else login
            full_config['mt5']['connection']['password'] = password
            full_config['mt5']['connection']['server'] = server
            full_config['mt5']['connection']['path'] = path
            
            # Сохранить файл с сохранением всей структуры
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(full_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info("[MT5] Configuration saved")
            messagebox.showinfo("Success", "MT5 settings saved!\nRestart application to apply changes.")
            
            # Вызвать callback
            if self.on_save_callback:
                self.on_save_callback()
            
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"[MT5] Failed to save config: {e}")
            messagebox.showerror("Error", f"Failed to save MT5 settings:\n{e}")

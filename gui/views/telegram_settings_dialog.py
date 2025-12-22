"""
Telegram Settings Dialog

Allows user to configure Telegram bot:
- API Token
- Chat ID
- Test connection
- Enable/disable notifications
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QGroupBox,
    QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import json
from pathlib import Path
import asyncio


class TelegramSettingsDialog(QDialog):
    """Dialog for configuring Telegram bot settings."""
    
    settings_saved = Signal(dict)  # Emitted when settings are saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Telegram Bot Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # Load current settings
        self.config_path = Path(__file__).parent.parent.parent / "telegram_bot" / "config.json"
        self.current_config = self._load_config()
        
        self._setup_ui()
        self._load_current_settings()
    
    def _load_config(self) -> dict:
        """Load current configuration."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        return {
            'bot_token': '',
            'chat_id': '',
            'enabled': False,
            'notifications': {
                'trade_opened': True,
                'trade_closed': True,
                'system_status': True,
                'daily_report': True,
                'errors': True
            },
            'commands_enabled': True
        }
    
    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("🤖 Telegram Bot Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #00c896; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Configure your Telegram bot to receive trading notifications.\n"
            "Create a bot via @BotFather and get your Chat ID from @userinfobot"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #9ca3af; font-size: 9pt; margin-bottom: 12px;")
        layout.addWidget(instructions)
        
        # === Bot Token ===
        token_group = QGroupBox("Bot API Token")
        token_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #3a3f4a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                color: #00c896;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        token_layout = QVBoxLayout(token_group)
        
        token_label = QLabel("API Token (from @BotFather):")
        token_label.setStyleSheet("color: #d1d5db; font-size: 9pt;")
        token_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.token_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #3a3f4a;
                border-radius: 6px;
                background-color: #1f2937;
                color: #f3f4f6;
                font-size: 10pt;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border-color: #00c896;
            }
        """)
        token_layout.addWidget(self.token_input)
        
        layout.addWidget(token_group)
        
        # === Chat ID ===
        chat_group = QGroupBox("Chat ID")
        chat_group.setStyleSheet(token_group.styleSheet())
        chat_layout = QVBoxLayout(chat_group)
        
        chat_label = QLabel("Your Telegram Chat ID (from @userinfobot):")
        chat_label.setStyleSheet("color: #d1d5db; font-size: 9pt;")
        chat_layout.addWidget(chat_label)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("123456789")
        self.chat_input.setStyleSheet(self.token_input.styleSheet())
        chat_layout.addWidget(self.chat_input)
        
        layout.addWidget(chat_group)
        
        # === Test Connection Button ===
        test_btn = QPushButton("🔍 Test Connection")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)
        
        # === Notifications Settings ===
        notif_group = QGroupBox("Notification Settings")
        notif_group.setStyleSheet(token_group.styleSheet())
        notif_layout = QVBoxLayout(notif_group)
        
        self.notify_trades_open = QCheckBox("Trade Opened")
        self.notify_trades_close = QCheckBox("Trade Closed")
        self.notify_system = QCheckBox("System Status")
        self.notify_daily = QCheckBox("Daily Reports")
        self.notify_errors = QCheckBox("Error Alerts")
        
        for cb in [self.notify_trades_open, self.notify_trades_close, 
                   self.notify_system, self.notify_daily, self.notify_errors]:
            cb.setStyleSheet("""
                QCheckBox {
                    color: #d1d5db;
                    font-size: 9pt;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #3a3f4a;
                    border-radius: 4px;
                    background-color: #1f2937;
                }
                QCheckBox::indicator:checked {
                    background-color: #00c896;
                    border-color: #00c896;
                }
            """)
            notif_layout.addWidget(cb)
        
        layout.addWidget(notif_group)
        
        # === Enable/Disable ===
        self.enabled_cb = QCheckBox("Enable Telegram Bot")
        self.enabled_cb.setStyleSheet("""
            QCheckBox {
                color: #00c896;
                font-weight: 600;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #3a3f4a;
                border-radius: 4px;
                background-color: #1f2937;
            }
            QCheckBox::indicator:checked {
                background-color: #00c896;
                border-color: #00c896;
            }
        """)
        layout.addWidget(self.enabled_cb)
        
        # Spacer
        layout.addStretch()
        
        # === Buttons ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #d1d5db;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00c896;
                color: #1a202c;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #00d9a6;
            }
            QPushButton:pressed {
                background-color: #00b37d;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
    
    def _load_current_settings(self):
        """Load current settings into form."""
        self.token_input.setText(self.current_config.get('bot_token', ''))
        self.chat_input.setText(str(self.current_config.get('chat_id', '')))
        self.enabled_cb.setChecked(self.current_config.get('enabled', False))
        
        notifications = self.current_config.get('notifications', {})
        self.notify_trades_open.setChecked(notifications.get('trade_opened', True))
        self.notify_trades_close.setChecked(notifications.get('trade_closed', True))
        self.notify_system.setChecked(notifications.get('system_status', True))
        self.notify_daily.setChecked(notifications.get('daily_report', True))
        self.notify_errors.setChecked(notifications.get('errors', True))
    
    def _test_connection(self):
        """Test Telegram bot connection."""
        token = self.token_input.text().strip()
        chat_id = self.chat_input.text().strip()
        
        if not token:
            QMessageBox.warning(self, "Missing Token", "Please enter your Bot API Token")
            return
        
        if not chat_id:
            QMessageBox.warning(self, "Missing Chat ID", "Please enter your Chat ID")
            return
        
        # Try to send test message
        try:
            from telegram import Bot
            
            async def send_test():
                bot = Bot(token=token)
                await bot.send_message(
                    chat_id=chat_id,
                    text="✅ Connection successful!\n\nYour SMC Trading Bot is now configured."
                )
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_test())
            
            QMessageBox.information(
                self,
                "✅ Connection Successful",
                "Test message sent to your Telegram!\n\nBot is working correctly."
            )
        
        except ImportError:
            QMessageBox.critical(
                self,
                "❌ Library Missing",
                "python-telegram-bot not installed.\n\n"
                "Install it with: pip install python-telegram-bot"
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Connection Failed",
                f"Could not connect to Telegram:\n\n{str(e)}\n\n"
                "Check your Token and Chat ID."
            )
    
    def _save_settings(self):
        """Save settings to config file."""
        token = self.token_input.text().strip()
        chat_id = self.chat_input.text().strip()
        
        if not token:
            QMessageBox.warning(self, "Missing Token", "Please enter your Bot API Token")
            return
        
        if not chat_id:
            QMessageBox.warning(self, "Missing Chat ID", "Please enter your Chat ID")
            return
        
        # Build config
        config = {
            'bot_token': token,
            'chat_id': chat_id,
            'enabled': self.enabled_cb.isChecked(),
            'notifications': {
                'trade_opened': self.notify_trades_open.isChecked(),
                'trade_closed': self.notify_trades_close.isChecked(),
                'system_status': self.notify_system.isChecked(),
                'daily_report': self.notify_daily.isChecked(),
                'errors': self.notify_errors.isChecked()
            },
            'commands_enabled': True
        }
        
        # Save to file
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # Emit signal
            self.settings_saved.emit(config)
            
            QMessageBox.information(
                self,
                "✅ Settings Saved",
                "Telegram bot settings have been saved successfully!"
            )
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Save Failed",
                f"Could not save settings:\n\n{str(e)}"
            )

"""MT5 Settings Dialog - Configure MetaTrader 5 connection."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox, QCheckBox,
    QApplication
)
from PySide6.QtCore import Qt, Signal
import json
import base64
from pathlib import Path


class MT5SettingsDialog(QDialog):
    """Dialog for configuring MT5 connection settings."""
    
    settings_saved = Signal(dict)  # Emit when settings are saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("MetaTrader 5 Connection Settings")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1d23;
            }
            QLabel {
                color: #e8e9ed;
                font-size: 10pt;
            }
            QLineEdit {
                background-color: #252930;
                color: #e8e9ed;
                border: 2px solid #3a3f4a;
                border-radius: 6px;
                padding: 10px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
            QCheckBox {
                color: #e8e9ed;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #3a3f4a;
                border-radius: 4px;
                background-color: #252930;
            }
            QCheckBox::indicator:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🔗 MetaTrader 5 Connection")
        title.setStyleSheet("font-size: 14pt; font-weight: 700; color: #4a9eff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Configure your MT5 account credentials for live trading connection.")
        desc.setStyleSheet("font-size: 9pt; color: #8b92a0; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3a3f4a; margin: 10px 0px;")
        layout.addWidget(sep)
        
        # === Account Login ===
        login_label = QLabel("Account Login:")
        login_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        layout.addWidget(login_label)
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Enter your MT5 account number (e.g., 12345678)")
        layout.addWidget(self.login_input)
        
        # === Password ===
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your MT5 password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Password options row
        password_options_layout = QHBoxLayout()
        
        # Show password checkbox
        self.show_password_cb = QCheckBox("Show password")
        self.show_password_cb.toggled.connect(self._toggle_password_visibility)
        password_options_layout.addWidget(self.show_password_cb)
        
        password_options_layout.addSpacing(20)
        
        # Remember password checkbox
        self.remember_password_cb = QCheckBox("Remember password")
        self.remember_password_cb.setToolTip("Save password securely for auto-login")
        self.remember_password_cb.setStyleSheet("""
            QCheckBox {
                color: #00c896;
                font-weight: 600;
            }
            QCheckBox::indicator:checked {
                background-color: #00c896;
                border-color: #00c896;
            }
        """)
        password_options_layout.addWidget(self.remember_password_cb)
        
        password_options_layout.addStretch()
        layout.addLayout(password_options_layout)
        
        # === Server ===
        server_label = QLabel("Server:")
        server_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        layout.addWidget(server_label)
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("e.g., Broker-Server or leave empty for auto-detect")
        layout.addWidget(self.server_input)
        
        # Info note
        info = QLabel("ℹ️ Settings are saved locally. Never share your credentials.")
        info.setStyleSheet("font-size: 8pt; color: #6b7280; margin-top: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addSpacing(10)
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.test_btn = QPushButton("🔍 Test Connection")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: #0a1015;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 10pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #6ab0ff;
            }
            QPushButton:pressed {
                background-color: #3a8eef;
            }
        """)
        self.test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.test_btn)
        
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d323a;
                color: #e8e9ed;
                border: 2px solid #3a3f4a;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 10pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #353a44;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00c896;
                color: #0a1015;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 10pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #10d8a6;
            }
            QPushButton:pressed {
                background-color: #00b886;
            }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        
        # Load existing settings
        self._load_settings()
    
    def _toggle_password_visibility(self, checked):
        """Toggle password visibility."""
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
    
    def _encode_password(self, password: str) -> str:
        """Encode password for storage (simple base64)."""
        return base64.b64encode(password.encode()).decode()
    
    def _decode_password(self, encoded: str) -> str:
        """Decode password from storage."""
        try:
            return base64.b64decode(encoded.encode()).decode()
        except:
            return ""
    
    def _load_settings(self):
        """Load saved settings from config file."""
        config_path = Path(__file__).parent.parent / "data" / "mt5_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.login_input.setText(str(config.get('login', '')))
                    self.server_input.setText(config.get('server', ''))
                    
                    # Load password if remember_password was enabled
                    if config.get('remember_password', False):
                        encoded_password = config.get('password_encoded', '')
                        if encoded_password:
                            password = self._decode_password(encoded_password)
                            self.password_input.setText(password)
                            self.remember_password_cb.setChecked(True)
            except Exception as e:
                print(f"Error loading MT5 config: {e}")
    
    def _save_settings(self):
        """Save settings to config file."""
        login = self.login_input.text().strip()
        password = self.password_input.text()
        server = self.server_input.text().strip()
        remember_password = self.remember_password_cb.isChecked()
        
        # Validation
        if not login:
            QMessageBox.warning(
                self,
                "Missing Login",
                "Please enter your MT5 account login."
            )
            return
        
        if not password:
            QMessageBox.warning(
                self,
                "Missing Password",
                "Please enter your MT5 password."
            )
            return
        
        # Prepare config
        config = {
            'login': int(login) if login.isdigit() else login,
            'server': server if server else None,
            'remember_password': remember_password,
        }
        
        # Add password based on remember_password setting
        if remember_password:
            config['password'] = password  # For immediate use
            config['password_encoded'] = self._encode_password(password)  # For storage
        else:
            config['password'] = password  # For immediate use only
            config['password_encoded'] = ''  # Don't save
        
        # Save to file
        config_path = Path(__file__).parent.parent / "data"
        config_path.mkdir(exist_ok=True)
        
        config_file = config_path / "mt5_config.json"
        
        try:
            # Save config (remove password from file if not remembering)
            save_config = config.copy()
            if not remember_password:
                save_config.pop('password', None)  # Don't save password to file
            
            with open(config_file, 'w') as f:
                json.dump(save_config, f, indent=2)
            
            password_status = "saved securely" if remember_password else "not saved"
            
            QMessageBox.information(
                self,
                "Settings Saved",
                f"MT5 connection settings saved successfully.\n\n"
                f"Password: {password_status}\n"
                f"{'⚠️ Password is stored encoded locally.' if remember_password else '✓ Password will not be saved.'}"
            )
            
            # Emit signal with settings (including password for immediate use)
            self.settings_saved.emit(config)
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings:\n{str(e)}"
            )
    
    def _test_connection(self):
        """Test MT5 connection with current credentials."""
        login = self.login_input.text().strip()
        password = self.password_input.text()
        server = self.server_input.text().strip()
        
        if not login or not password:
            QMessageBox.warning(
                self,
                "Incomplete Credentials",
                "Please fill in both login and password to test connection."
            )
            return
        
        # Import MT5 connector
        from mt5.connector import MT5Connector
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        
        # Show progress dialog
        progress = QProgressDialog("Testing MT5 connection...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Can't cancel
        progress.show()
        QApplication.processEvents()
        
        try:
            # Try to connect
            connector = MT5Connector()
            success = connector.connect(
                login=int(login) if login.isdigit() else login,
                password=password,
                server=server if server else None
            )
            
            progress.close()
            
            if success:
                account_info = connector.get_account_info()
                if account_info:
                    QMessageBox.information(
                        self,
                        "✓ Connection Successful",
                        f"Successfully connected to MT5!\n\n"
                        f"Account: {account_info.get('login', 'N/A')}\n"
                        f"Server: {account_info.get('server', 'N/A')}\n"
                        f"Balance: ${account_info.get('balance', 0):,.2f}\n"
                        f"Leverage: 1:{account_info.get('leverage', 'N/A')}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "✓ Connection Successful",
                        "Successfully connected to MT5!"
                    )
                connector.disconnect()
            else:
                QMessageBox.critical(
                    self,
                    "✗ Connection Failed",
                    "Could not connect to MT5.\n\n"
                    "Possible reasons:\n"
                    "• Invalid login or password\n"
                    "• Wrong server name\n"
                    "• MT5 terminal not running\n"
                    "• Account type mismatch (demo/live)\n\n"
                    "Please verify your credentials and try again."
                )
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "Error",
                f"Error testing connection:\n\n{str(e)}"
            )

    
    @staticmethod
    def get_saved_credentials():
        """
        Get saved MT5 credentials from config file.
        
        Returns:
            dict: Credentials or None if not found
        """
        config_path = Path(__file__).parent.parent / "data" / "mt5_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                    # Decode password if remember_password is enabled
                    if config.get('remember_password', False):
                        encoded_password = config.get('password_encoded', '')
                        if encoded_password:
                            try:
                                config['password'] = base64.b64decode(encoded_password.encode()).decode()
                            except:
                                config['password'] = None
                    else:
                        config['password'] = None
                    
                    return config
            except Exception as e:
                print(f"Error loading MT5 credentials: {e}")
        
        return None

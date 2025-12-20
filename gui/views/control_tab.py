"""Control Tab - Trading execution control."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSlider, QFrame, QRadioButton, QButtonGroup, QMessageBox,
    QScrollArea
)
from PySide6.QtCore import Qt
from core import AppState, DataBridge, SystemStatus, TradingMode, SystemHealth


class ControlTab(QWidget):
    """Control panel tab with execution controls."""
    
    def __init__(self, app_state: AppState, data_bridge: DataBridge):
        super().__init__()
        self.app_state = app_state
        self.data_bridge = data_bridge
        
        # Settings file path
        import os
        self.settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'settings.json')
        
        # Main layout with scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Container widget for scrollable content
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # === Execution Control Section ===
        exec_group = self._create_group("⚡ EXECUTION CONTROL")
        exec_group.setMinimumWidth(800)  # Prevent text clipping
        exec_layout = QVBoxLayout()
        exec_group.setLayout(exec_layout)
        
        # Buttons row - LARGE, IMPOSING
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.start_btn = QPushButton("▶ START SYSTEM")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setMinimumHeight(70)  # BIGGER
        self.start_btn.setToolTip("Start the trading system in selected mode (Demo/Live)")
        self.start_btn.setStyleSheet("""
            QPushButton#startButton {
                font-size: 18pt;
                font-weight: 700;
                letter-spacing: 1.5px;
                background-color: #00c896;
                color: #000000;
                border: 2px solid #00e0a8;
            }
            QPushButton#startButton:hover {
                background-color: #00e0a8;
                border-color: #00ffc4;
            }
        """)
        self.start_btn.clicked.connect(self._start_trading)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ PAUSE SYSTEM")
        self.pause_btn.setObjectName("pauseButton")
        self.pause_btn.setMinimumHeight(70)
        self.pause_btn.setToolTip("Pause trading - no new positions, keep existing ones")
        self.pause_btn.setStyleSheet("""
            QPushButton#pauseButton {
                font-size: 18pt;
                font-weight: 700;
                letter-spacing: 1.5px;
                background-color: #ffc107;
                color: #000000;
                border: 2px solid #ffd740;
            }
            QPushButton#pauseButton:hover {
                background-color: #ffd740;
                border-color: #ffe066;
            }
        """)
        self.pause_btn.clicked.connect(self._pause_trading)
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("■ STOP SYSTEM")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setMinimumHeight(70)
        self.stop_btn.setToolTip("Stop trading completely and close all open positions")
        self.stop_btn.setStyleSheet("""
            QPushButton#stopButton {
                font-size: 18pt;
                font-weight: 700;
                letter-spacing: 1.5px;
                background-color: #ff5555;
                color: #ffffff;
                border: 2px solid #ff6b6b;
            }
            QPushButton#stopButton:hover {
                background-color: #ff6b6b;
                border-color: #ff8888;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_trading)
        btn_layout.addWidget(self.stop_btn)
        
        exec_layout.addLayout(btn_layout)
        
        # Apply settings button - separate row
        apply_layout = QHBoxLayout()
        apply_layout.setSpacing(12)
        
        self.apply_btn = QPushButton("🔄 APPLY SETTINGS && RESTART")
        self.apply_btn.setObjectName("applyButton")
        self.apply_btn.setMinimumHeight(50)
        self.apply_btn.setToolTip("Apply all current settings and restart the trading bot")
        self.apply_btn.setStyleSheet("""
            QPushButton#applyButton {
                font-size: 14pt;
                font-weight: 700;
                letter-spacing: 1px;
                background-color: #4a9eff;
                color: #ffffff;
                border: 2px solid #6ab0ff;
                border-radius: 6px;
            }
            QPushButton#applyButton:hover {
                background-color: #6ab0ff;
                border-color: #8ac4ff;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_and_restart)
        apply_layout.addWidget(self.apply_btn)
        
        exec_layout.addLayout(apply_layout)
        
        # Status indicator - PROMINENT
        self.status_label = QLabel("Status: STOPPED")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: 700; color: #ff5555; margin-top: 8px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        exec_layout.addWidget(self.status_label)
        
        layout.addWidget(exec_group)
        
        # === Mode Selection Section ===
        mode_group = self._create_group("🔄 TRADING MODE")
        mode_group.setMinimumWidth(800)
        mode_layout = QVBoxLayout()
        mode_group.setLayout(mode_layout)
        
        self.mode_button_group = QButtonGroup()
        
        self.demo_radio = QRadioButton("Demo Trading (Paper Trading)")
        self.demo_radio.setChecked(True)
        self.demo_radio.setStyleSheet("font-size: 12pt; color: #e8e9ed; padding: 8px;")
        self.demo_radio.setToolTip("Paper trading mode - no real money involved, perfect for testing")
        self.demo_radio.toggled.connect(lambda: self._change_mode(TradingMode.DEMO))
        self.mode_button_group.addButton(self.demo_radio)
        mode_layout.addWidget(self.demo_radio)
        
        self.live_radio = QRadioButton("Live Trading (Real Money)")
        self.live_radio.setStyleSheet("font-size: 12pt; color: #e8e9ed; padding: 8px;")
        self.live_radio.setToolTip("LIVE TRADING - uses real money! Be careful!")
        self.live_radio.toggled.connect(lambda: self._change_mode(TradingMode.LIVE))
        self.mode_button_group.addButton(self.live_radio)
        mode_layout.addWidget(self.live_radio)
        
        mode_warning = QLabel("⚠ Changing to LIVE mode requires confirmation")
        mode_warning.setStyleSheet("color: #ffc107; font-size: 11pt; font-weight: 600; padding: 4px;")
        mode_layout.addWidget(mode_warning)
        
        layout.addWidget(mode_group)
        
        # === Risk Management Section ===
        risk_group = self._create_group("⚙️ RISK MANAGEMENT")
        risk_group.setMinimumWidth(800)
        risk_layout = QVBoxLayout()
        risk_group.setLayout(risk_layout)
        
        # Risk per trade preset selection
        risk_per_trade_label = QLabel("Risk per trade (XAUUSD):")
        risk_per_trade_label.setStyleSheet("font-size: 13pt; color: #e8e9ed; font-weight: 700; padding: 6px;")
        risk_per_trade_label.setToolTip("Select risk percentage per single XAUUSD trade")
        risk_layout.addWidget(risk_per_trade_label)
        
        # Preset buttons in row
        risk_preset_layout = QHBoxLayout()
        risk_preset_layout.setSpacing(12)
        
        self.risk_button_group = QButtonGroup()
        risk_presets = [("0.5%", 50), ("0.75%", 75), ("1.0%", 100), ("1.25%", 125), ("1.5%", 150)]
        
        for label, value in risk_presets:
            btn = QRadioButton(label)
            btn.setStyleSheet("""
                QRadioButton {
                    font-size: 14pt;
                    font-weight: 700;
                    color: #e8e9ed;
                    padding: 12px 20px;
                    background-color: #3a3f4a;
                    border-radius: 6px;
                }
                QRadioButton:checked {
                    background-color: #00c896;
                    color: #000000;
                }
            """)
            if value == 100:  # Default 1.0%
                btn.setChecked(True)
            btn.toggled.connect(lambda checked, v=value: self._update_risk_preset(v) if checked else None)
            self.risk_button_group.addButton(btn)
            risk_preset_layout.addWidget(btn)
        
        risk_preset_layout.addStretch()
        risk_layout.addLayout(risk_preset_layout)
        
        # Max portfolio risk preset selection
        max_risk_label = QLabel("Max portfolio risk:")
        max_risk_label.setStyleSheet("font-size: 13pt; color: #e8e9ed; font-weight: 700; padding: 6px;")
        max_risk_label.setToolTip("Maximum total portfolio risk across all instruments")
        risk_layout.addWidget(max_risk_label)
        
        # Preset buttons in row
        max_risk_preset_layout = QHBoxLayout()
        max_risk_preset_layout.setSpacing(12)
        
        self.max_risk_button_group = QButtonGroup()
        max_risk_presets = [("1.0%", 100), ("1.5%", 150), ("2.0%", 200), ("2.5%", 250)]
        
        for label, value in max_risk_presets:
            btn = QRadioButton(label)
            btn.setStyleSheet("""
                QRadioButton {
                    font-size: 14pt;
                    font-weight: 700;
                    color: #e8e9ed;
                    padding: 12px 20px;
                    background-color: #3a3f4a;
                    border-radius: 6px;
                }
                QRadioButton:checked {
                    background-color: #00c896;
                    color: #000000;
                }
            """)
            if value == 150:  # Default 1.5%
                btn.setChecked(True)
            btn.toggled.connect(lambda checked, v=value: self._update_max_risk_preset(v) if checked else None)
            self.max_risk_button_group.addButton(btn)
            max_risk_preset_layout.addWidget(btn)
        
        max_risk_preset_layout.addStretch()
        risk_layout.addLayout(max_risk_preset_layout)
        
        # Warning
        frozen_warning = QLabel("⚠ Strategies are FROZEN\nRisk limits are the ONLY adjustable parameters")
        frozen_warning.setToolTip("Trading strategies are locked and validated. You can only adjust risk parameters.")
        frozen_warning.setStyleSheet("font-size: 11pt; font-weight: 600; color: #ffc107; background-color: #3a2f1a; padding: 12px; border-radius: 4px;")
        frozen_warning.setAlignment(Qt.AlignCenter)
        risk_layout.addWidget(frozen_warning)
        
        layout.addWidget(risk_group)
        
        # === System Health Section ===
        health_group = self._create_group("🏥 SYSTEM HEALTH")
        health_group.setMinimumWidth(800)
        health_layout = QVBoxLayout()
        health_group.setLayout(health_layout)
        
        # Health indicator
        self.health_label = QLabel("STABLE")
        self.health_label.setToolTip("Overall system health based on drawdown, risk usage, and losing streaks")
        self.health_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #00c896;")
        self.health_label.setAlignment(Qt.AlignCenter)
        health_layout.addWidget(self.health_label)
        
        # Health metrics
        self.health_dd_label = QLabel("Current DD: 0.0%")
        self.health_dd_label.setStyleSheet("font-size: 12pt; color: #e8e9ed; font-weight: 600; padding: 4px;")
        self.health_dd_label.setToolTip("Current drawdown - distance from peak equity")
        self.health_dd_label.setAlignment(Qt.AlignCenter)
        health_layout.addWidget(self.health_dd_label)
        
        self.health_risk_label = QLabel("Risk usage: 0%")
        self.health_risk_label.setStyleSheet("font-size: 12pt; color: #e8e9ed; font-weight: 600; padding: 4px;")
        self.health_risk_label.setToolTip("Percentage of maximum allowed risk currently in use")
        self.health_risk_label.setAlignment(Qt.AlignCenter)
        health_layout.addWidget(self.health_risk_label)
        
        layout.addWidget(health_group)
        
        layout.addStretch()
        
        # Connect state signals
        app_state.status_changed.connect(self._update_status)
        app_state.mode_changed.connect(self._update_mode)
        app_state.health_changed.connect(self._update_health)
        app_state.metrics_updated.connect(self._update_health_metrics)
        
        # Initial update
        self._update_status(app_state.status)
        self._update_mode(app_state.mode)
        self._update_health(app_state.health)
        
        # Disable if readonly
        if app_state.is_readonly:
            self.setEnabled(False)
        
        # Load and apply saved settings
        self._apply_saved_settings()
    
    def _apply_and_restart(self):
        """Apply all current settings and restart the bot."""
        from PySide6.QtWidgets import QMessageBox
        
        # Get current settings
        current_settings = self._load_settings()
        
        # Show confirmation
        mode = current_settings.get('trading_mode', 'DEMO')
        risk = current_settings.get('risk_per_trade', 1.0)
        max_risk = current_settings.get('max_portfolio_risk', 1.5)
        
        msg = (
            f"Apply settings and restart bot?\\n\\n"
            f"Mode: {mode}\\n"
            f"Risk per trade: {risk:.2f}%\\n"
            f"Max portfolio risk: {max_risk:.2f}%\\n\\n"
            f"Bot will restart with these settings."
        )
        
        reply = QMessageBox.question(
            self,
            "Apply Settings",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Stop current bot if running
            if self.app_state.status == SystemStatus.RUNNING:
                self.data_bridge.stop_trading()
                self.app_state.set_status(SystemStatus.STOPPED)
            
            # Apply settings to data bridge
            self.data_bridge.set_risk(risk)
            self.data_bridge.send_command("set_max_risk", {"max_risk_pct": max_risk})
            self.data_bridge.send_command("set_mode", {"mode": mode})
            
            # Show success message
            self.status_label.setText("✅ Settings applied! Bot ready to start.")
            self.status_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #00c896;")
            
            print(f"[✓] Settings applied: Mode={mode}, Risk={risk}%, MaxRisk={max_risk}%")
    
    def _create_group(self, title: str) -> QFrame:
        """Create group frame with title."""
        group = QFrame()
        group.setObjectName("controlGroup")
        group.setStyleSheet("""
            QFrame#controlGroup {
                background-color: #252930;
                border: 1px solid #3a3f4a;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        # Only create title label, don't add layout yet
        title_label = QLabel(title, group)
        title_label.setStyleSheet("""
            font-size: 10pt; 
            font-weight: 700; 
            color: #8b92a0; 
            margin-bottom: 12px;
            letter-spacing: 1px;
        """)
        
        return group
    
    def _start_trading(self):
        """Start trading."""
        reply = QMessageBox.question(
            self,
            "Start Trading",
            f"Start trading in {self.app_state.mode.value} mode?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.data_bridge.start_trading()
            self.app_state.set_status(SystemStatus.RUNNING)
    
    def _pause_trading(self):
        """Pause trading."""
        self.data_bridge.pause_trading()
        self.app_state.set_status(SystemStatus.PAUSED)
    
    def _stop_trading(self):
        """Stop trading."""
        reply = QMessageBox.question(
            self,
            "Stop Trading",
            "Stop trading? Open positions will be closed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.data_bridge.stop_trading()
            self.app_state.set_status(SystemStatus.STOPPED)
    
    def _change_mode(self, mode: TradingMode):
        """Change trading mode."""
        if mode == TradingMode.LIVE:
            reply = QMessageBox.warning(
                self,
                "Switch to LIVE Trading",
                "⚠️ WARNING ⚠️\n\n"
                "You are about to switch to LIVE trading mode.\n"
                "This will use REAL MONEY.\n\n"
                "Make sure:\n"
                "✓ Demo results are satisfactory\n"
                "✓ Risk limits are set correctly\n"
                "✓ You understand the risks\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                self.demo_radio.setChecked(True)
                return
        
        self.app_state.set_mode(mode)
        self.data_bridge.send_command("set_mode", {"mode": mode.value})
        # Save to config
        self._save_settings({'trading_mode': mode.value})
    
    def _update_risk_preset(self, value):
        """Update risk from preset."""
        risk_pct = value / 100.0
        # Send to BAZA
        self.data_bridge.set_risk(risk_pct)
        # Save to config
        self._save_settings({'risk_per_trade': risk_pct})
    
    def _update_max_risk_preset(self, value):
        """Update max risk from preset."""
        max_risk_pct = value / 100.0
        # Send to BAZA
        self.data_bridge.send_command("set_max_risk", {"max_risk_pct": max_risk_pct})
        # Save to config
        self._save_settings({'max_portfolio_risk': max_risk_pct})
    
    def _load_settings(self):
        """Load settings from JSON file."""
        import json
        import os
        
        defaults = {
            'trading_mode': 'DEMO',
            'risk_per_trade': 1.0,
            'max_portfolio_risk': 1.5
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    return {**defaults, **settings}
        except Exception as e:
            print(f"[!] Error loading settings: {e}")
        
        return defaults
    
    def _save_settings(self, updates):
        """Save settings to JSON file."""
        import json
        import os
        
        # Load current settings
        current = self._load_settings()
        # Update with new values
        current.update(updates)
        
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            # Save to file
            with open(self.settings_file, 'w') as f:
                json.dump(current, f, indent=2)
            print(f"[✓] Settings saved: {updates}")
        except Exception as e:
            print(f"[!] Error saving settings: {e}")
    
    def _apply_saved_settings(self):
        """Apply saved settings to UI controls."""
        settings = self._load_settings()
        
        # Apply trading mode
        mode = settings.get('trading_mode', 'DEMO')
        if mode == 'LIVE':
            self.live_radio.setChecked(True)
        else:
            self.demo_radio.setChecked(True)
        
        # Apply risk per trade
        risk_value = int(settings.get('risk_per_trade', 1.0) * 100)
        for btn in self.risk_button_group.buttons():
            # Check if button text matches the saved value
            btn_text = btn.text().replace('%', '')
            btn_value = int(float(btn_text) * 100)
            if btn_value == risk_value:
                btn.setChecked(True)
                break
        
        # Apply max portfolio risk
        max_risk_value = int(settings.get('max_portfolio_risk', 1.5) * 100)
        for btn in self.max_risk_button_group.buttons():
            btn_text = btn.text().replace('%', '')
            btn_value = int(float(btn_text) * 100)
            if btn_value == max_risk_value:
                btn.setChecked(True)
                break
        
        print(f"[✓] Applied saved settings: Mode={mode}, Risk={settings.get('risk_per_trade')}%, MaxRisk={settings.get('max_portfolio_risk')}%")
    
    def _update_status(self, status: SystemStatus):
        """Update status display."""
        status_text = status.value
        
        color_map = {
            SystemStatus.STOPPED: "#ff5555",
            SystemStatus.RUNNING: "#00c896",
            SystemStatus.PAUSED: "#ffc107",
            SystemStatus.ERROR: "#ff5555",
        }
        
        color = color_map.get(status, "#8b92a0")
        
        self.status_label.setText(f"Status: {status_text}")
        self.status_label.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {color};")
        
        # Update button states
        if status == SystemStatus.RUNNING:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        elif status == SystemStatus.PAUSED:
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:  # STOPPED
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def _update_mode(self, mode: TradingMode):
        """Update mode display."""
        if mode == TradingMode.DEMO:
            self.demo_radio.setChecked(True)
        else:
            self.live_radio.setChecked(True)
    
    def _update_health(self, health: SystemHealth):
        """Update health indicator."""
        health_text = health.value
        
        color_map = {
            SystemHealth.STABLE: "#00c896",
            SystemHealth.CAUTION: "#ffc107",
            SystemHealth.RISKY: "#ff5555",
        }
        
        icon_map = {
            SystemHealth.STABLE: "✅",
            SystemHealth.CAUTION: "⚠️",
            SystemHealth.RISKY: "🚨",
        }
        
        color = color_map.get(health, "#8b92a0")
        icon = icon_map.get(health, "")
        
        self.health_label.setText(f"{icon} {health_text}")
        self.health_label.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {color};")
    
    def _update_health_metrics(self, metrics):
        """Update health metrics display."""
        # DD
        dd = metrics.current_drawdown
        dd_color = "#00c896" if dd < 10 else "#ffc107" if dd < 15 else "#ff5555"
        self.health_dd_label.setText(f"Current DD: {dd:.2f}%")
        self.health_dd_label.setStyleSheet(f"color: {dd_color};")
        
        # Risk usage
        risk = metrics.risk_used
        risk_color = "#00c896" if risk < 70 else "#ffc107" if risk < 90 else "#ff5555"
        self.health_risk_label.setText(f"Risk usage: {risk:.0f}%")
        self.health_risk_label.setStyleSheet(f"color: {risk_color};")

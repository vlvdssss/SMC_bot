"""
Main Window - Primary Application Window

The main window contains:
    - Status bar (top)
    - Dashboard area (equity card, portfolio cards, equity curve)
    - Tab widget (Analytics, Trades, Control, Logs)
    
All widgets are connected to AppState and update automatically
when state changes.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QTabWidget, QLabel, QPushButton,
    QFrame, QSplitter, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from core import AppState, DataBridge, SystemStatus, TradingMode
from core.mt5_manager import MT5ConnectionManager
from widgets.status_bar_widget import StatusBarWidget
from widgets.equity_card import EquityCard
from widgets.portfolio_overview import PortfolioOverview
from widgets.equity_curve import EquityCurve
from views.analytics_tab import AnalyticsTab
from views.trades_tab import TradesTab
from views.control_tab import ControlTab
from views.logs_tab import LogsTab


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Layout:
        ┌────────────────────────────────────┐
        │  Status Bar                        │
        ├────────────────────────────────────┤
        │  Dashboard (equity + portfolio)    │
        │  Equity Curve                      │
        ├────────────────────────────────────┤
        │  Tab Widget                        │
        │    - Analytics                     │
        │    - Trades                        │
        │    - Control                       │
        │    - Logs                          │
        └────────────────────────────────────┘
    """
    
    def __init__(self, app_state: AppState, data_bridge: DataBridge):
        """
        Initialize main window.
        
        Args:
            app_state: Application state manager
            data_bridge: Data bridge to BAZA system
        """
        super().__init__()
        
        self.app_state = app_state
        self.data_bridge = data_bridge
        
        # Create MT5 connection manager
        self.mt5_manager = MT5ConnectionManager()
        
        # Window configuration
        self.setWindowTitle("SMC Control Center")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        
        # Update display
        self._update_window_title()
        
        # Check for saved MT5 credentials
        self._check_mt5_credentials()
        
        # Connect MT5 manager signals to GUI (with short delay to ensure UI is ready)
        QTimer.singleShot(100, self._connect_mt5_signals)
        
        # Try to connect to MT5 automatically
        QTimer.singleShot(1000, self._auto_connect_mt5)  # Delay 1 sec for UI to load
        
        # Setup periodic market session check (every 5 minutes)
        self.session_check_timer = QTimer(self)
        self.session_check_timer.timeout.connect(self._check_market_session)
        self.session_check_timer.start(300000)  # 5 minutes = 300000 ms
    
    def _check_market_session(self):
        """Periodic check of market session status."""
        if self.mt5_manager:
            self.mt5_manager.check_market_session()
    
    def _connect_mt5_signals(self):
        """Connect MT5 manager callbacks to GUI."""
        # Set up callbacks
        self.mt5_manager.on_log = lambda level, msg: self.logs_tab.add_log(level, msg)
        self.mt5_manager.on_status_changed = lambda connected, account: self.status_widget.update_mt5_status(connected, account)
        self.mt5_manager.on_error = lambda err: self._handle_mt5_error(err)
    
    def _handle_mt5_log(self, level: str, message: str):
        """
        Handle log message from MT5 manager.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
            message: Log message
        """
        self.logs_tab.add_log(level, message)
    
    def _handle_mt5_error(self, error_message: str):
        """
        Handle MT5 connection error.
        
        Args:
            error_message: Error description
        """
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.critical(
            self,
            "MT5 Connection Error",
            f"{error_message}\n\nWould you like to configure MT5 settings now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self._open_mt5_settings()
    
    def _auto_connect_mt5(self):
        """Automatically connect to MT5 if credentials are available."""
        from pathlib import Path
        
        # Check if credentials file exists
        config_path = Path(__file__).parent.parent / "data" / "mt5_config.json"
        
        if not config_path.exists():
            self.logs_tab.add_log("WARNING", "No MT5 credentials found. Configure in File → MT5 Connection Settings")
            return
        
        self.logs_tab.add_log("INFO", "Checking MT5 configuration...")
        
        # Try to connect
        success = self.mt5_manager.connect()
        
        if not success:
            self.logs_tab.add_log("INFO", "MT5 auto-connect skipped (password not saved). You can connect manually via File → MT5 Connection Settings")
    
    def _check_mt5_credentials(self) -> None:
        """
        Check if MT5 credentials are saved. If not, prompt user to configure.
        """
        from PySide6.QtWidgets import QMessageBox
        from views.mt5_settings_dialog import MT5SettingsDialog
        
        credentials = MT5SettingsDialog.get_saved_credentials()
        
        if not credentials:
            self.logs_tab.add_log("WARNING", "No MT5 credentials found")
            
            # Ask user if they want to configure now
            reply = QMessageBox.question(
                self,
                "MT5 Setup",
                "No MT5 connection configured.\n\nWould you like to set up MT5 connection now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self._open_mt5_settings()
            else:
                self.logs_tab.add_log("INFO", "MT5 setup skipped. You can configure it later in File → MT5 Connection Settings")
        else:
            login = credentials.get('login', 'N/A')
            server = credentials.get('server', 'N/A')
            self.logs_tab.add_log("SUCCESS", f"MT5 credentials found - Login: {login}, Server: {server}")

    
    def _setup_ui(self) -> None:
        """Setup user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - NO MARGINS for fullscreen
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        
        # === Status Bar ===
        self.status_widget = StatusBarWidget(self.app_state)
        main_layout.addWidget(self.status_widget)
        
        # === Main Dashboard Layout ===
        dashboard_main = QHBoxLayout()
        dashboard_main.setSpacing(8)
        dashboard_main.setContentsMargins(4, 4, 4, 4)
        
        # Left column: Account card (taller, narrower)
        self.equity_card = EquityCard(self.app_state)
        self.equity_card.setFixedWidth(380)
        # NO fixed height - let it expand by content
        dashboard_main.addWidget(self.equity_card)
        
        # Center: Frozen badge
        self.frozen_badge = self._create_frozen_badge()
        self.frozen_badge.setFixedWidth(280)
        self.frozen_badge.setMinimumHeight(200)
        dashboard_main.addWidget(self.frozen_badge)
        
        # Spacer
        dashboard_main.addStretch(1)
        
        # Right column: Portfolio + Equity curve stacked
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        
        # Portfolio overview (GOLD + EUR/USD)
        self.portfolio_overview = PortfolioOverview(self.app_state)
        self.portfolio_overview.setMinimumHeight(120)
        self.portfolio_overview.setMaximumHeight(150)
        right_column.addWidget(self.portfolio_overview)
        
        # Equity curve
        self.equity_curve = EquityCurve(self.app_state)
        self.equity_curve.setMinimumHeight(120)
        self.equity_curve.setMaximumHeight(150)
        right_column.addWidget(self.equity_curve)
        
        dashboard_main.addLayout(right_column)
        
        main_layout.addLayout(dashboard_main)
        
        # === Tab Widget ===
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Create tabs
        self.analytics_tab = AnalyticsTab(self.app_state)
        self.trades_tab = TradesTab(self.app_state)
        self.control_tab = ControlTab(self.app_state, self.data_bridge)
        self.logs_tab = LogsTab()
        
        # Add tabs
        self.tabs.addTab(self.analytics_tab, "📊 Analytics")
        self.tabs.addTab(self.trades_tab, "📝 Trades")
        self.tabs.addTab(self.control_tab, "⚙️ Control")
        self.tabs.addTab(self.logs_tab, "📋 Logs")
        
        # Disable control tab if readonly
        if self.app_state.is_readonly:
            self.tabs.setTabEnabled(2, False)
        
        main_layout.addWidget(self.tabs, stretch=1)
    
    def _create_frozen_badge(self) -> QFrame:
        """Create PROMINENT frozen strategy indicator badge."""
        badge = QFrame()
        badge.setObjectName("frozenBadge")
        badge.setFrameShape(QFrame.StyledPanel)
        badge.setStyleSheet("""
            QFrame#frozenBadge {
                background-color: #2a2f38;
                border: 2px solid #ffc107;
                border-radius: 8px;
            }
        """)
        
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(12, 10, 12, 10)
        badge_layout.setSpacing(6)
        
        # Lock icon
        icon_label = QLabel("🔒")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 28pt; margin: 4px 0px;")
        badge_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("STRATEGIES FROZEN")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-weight: 700; 
            font-size: 10pt; 
            color: #ffc107;
            letter-spacing: 1px;
            margin: 4px 0px;
        """)
        badge_layout.addWidget(title_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3a3f4a; margin: 2px 8px;")
        sep.setMaximumHeight(1)
        badge_layout.addWidget(sep)
        
        # Description
        desc_label = QLabel("Logic is protected\nOnly risk adjustable")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 8pt; color: #9ca3af; line-height: 1.3;")
        badge_layout.addWidget(desc_label)
        
        # Version
        version_label = QLabel("Baseline v1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 7pt; color: #6b7280; margin-top: 2px;")
        badge_layout.addWidget(version_label)
        
        # Add stretch to center content vertically
        badge_layout.addStretch()
        
        # Tooltip
        badge.setToolTip("Strategies are frozen and validated.\nYou can only adjust risk parameters to control position sizing.")
        
        return badge
    
    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # MT5 Settings action
        mt5_settings_action = QAction("🔗 &MT5 Connection Settings...", self)
        mt5_settings_action.triggered.connect(self._open_mt5_settings)
        file_menu.addAction(mt5_settings_action)
        
        # Check Market Session action
        market_session_action = QAction("⏰ Check &Market Session", self)
        market_session_action.triggered.connect(self._check_market_session)
        file_menu.addAction(market_session_action)
        
        file_menu.addSeparator()
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.triggered.connect(self._refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        readonly_action = QAction("Read-Only Mode", self, checkable=True)
        readonly_action.setChecked(self.app_state.is_readonly)
        view_menu.addAction(readonly_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self) -> None:
        """Connect state signals to update methods."""
        # Update window title when status/mode changes
        self.app_state.status_changed.connect(self._update_window_title)
        self.app_state.mode_changed.connect(self._update_window_title)
        
        # Handle alerts
        self.app_state.alert_raised.connect(self._handle_alert)
        
        # Connection status
        self.data_bridge.connection_status.connect(self._handle_connection_status)
    
    def _update_window_title(self) -> None:
        """Update window title with current status."""
        status = self.app_state.status.value
        mode = self.app_state.mode.value
        
        title = f"SMC Control Center - [{status}] {mode}"
        
        if self.app_state.is_readonly:
            title += " [READ-ONLY]"
        
        self.setWindowTitle(title)
    
    def _refresh_data(self) -> None:
        """Manually refresh data from BAZA."""
        # Trigger immediate update check
        self.data_bridge._check_updates()
    
    def _open_mt5_settings(self) -> None:
        """Open MT5 connection settings dialog."""
        from views.mt5_settings_dialog import MT5SettingsDialog
        
        dialog = MT5SettingsDialog(self)
        dialog.settings_saved.connect(self._on_mt5_settings_saved)
        dialog.exec()
    
    def _on_mt5_settings_saved(self, settings: dict) -> None:
        """
        Handle MT5 settings saved.
        
        Args:
            settings: Saved MT5 credentials (includes password even if not saved to file)
        """
        # Log the configuration
        login = settings.get('login', 'Unknown')
        password = settings.get('password', '')
        server = settings.get('server')
        
        self.logs_tab.add_log("SUCCESS", f"MT5 settings saved for account: {login}")
        self.logs_tab.add_log("DEBUG", f"Password received: {'YES (' + str(len(password)) + ' chars)' if password else 'NO'}")
        self.logs_tab.add_log("DEBUG", f"Server: {server if server else 'Not specified'}")
        
        # Try to connect with new credentials (pass password directly from settings)
        self.logs_tab.add_log("INFO", "Attempting connection with new credentials...")
        success = self.mt5_manager.connect(
            login=settings.get('login'),
            password=settings.get('password'),  # Use password from dialog, even if not saved to file
            server=settings.get('server')
        )
        
        if not success:
            self.logs_tab.add_log("ERROR", "Connection failed. Check credentials and try again.")

    
    def _handle_alert(self, level: str, message: str) -> None:
        """
        Handle alert from app state.
        
        Args:
            level: Alert level ("info", "warning", "error")
            message: Alert message
        """
        # Forward to logs tab
        self.logs_tab.add_log(level.upper(), message)
        
        # Show in status bar
        status_color = {
            'info': '#4a9eff',
            'warning': '#ffc107',
            'error': '#ff5555'
        }.get(level, '#8b92a0')
        
        self.statusBar().showMessage(message, 5000)
        self.statusBar().setStyleSheet(f"color: {status_color};")
    
    def _handle_connection_status(self, connected: bool) -> None:
        """
        Handle connection status change.
        
        Args:
            connected: Whether connected to BAZA
        """
        if not connected:
            self.statusBar().showMessage("⚠ Connection to BAZA lost", 0)
            self.statusBar().setStyleSheet("color: #ff5555;")
        else:
            self.statusBar().showMessage("✓ Connected to BAZA", 3000)
            self.statusBar().setStyleSheet("color: #00c896;")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About SMC Control Center")
        about_dialog.setMinimumWidth(500)
        about_dialog.setModal(True)
        
        # Apply dark theme styling
        about_dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1d23;
            }
            QLabel {
                color: #e8e9ed;
            }
        """)
        
        layout = QVBoxLayout(about_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Logo/Icon
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 64pt;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title = QLabel("SMC Control Center")
        title.setStyleSheet("font-size: 20pt; font-weight: 700; color: #4a9eff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel("Version 1.0")
        version.setStyleSheet("font-size: 11pt; color: #8b92a0;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3a3f4a; margin: 10px 0px;")
        layout.addWidget(sep)
        
        # Description
        desc = QLabel("Professional control center for algorithmic trading system.\n\n"
                     "Built on SMC-framework with frozen, validated strategies.\n"
                     "Focus: Risk management and execution control.")
        desc.setStyleSheet("font-size: 10pt; color: #9ca3af; line-height: 1.5;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # Technology stack
        tech = QLabel("Framework: SMC-framework\nTechnology: PySide6 (Qt)")
        tech.setStyleSheet("font-size: 9pt; color: #6b7280;")
        tech.setAlignment(Qt.AlignCenter)
        layout.addWidget(tech)
        
        layout.addSpacing(10)
        
        # Copyright - BOBI
        copyright_label = QLabel("© 2025 BOBI")
        copyright_label.setStyleSheet("font-size: 12pt; font-weight: 700; color: #ffc107;")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        framework_label = QLabel("SMC-Framework")
        framework_label.setStyleSheet("font-size: 10pt; color: #8b92a0;")
        framework_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(framework_label)
        
        layout.addSpacing(10)
        
        # Close button
        close_btn = QPushButton("OK")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: #0a1015;
                border: none;
                border-radius: 6px;
                padding: 12px 40px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #6ab0ff;
            }
        """)
        close_btn.clicked.connect(about_dialog.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        about_dialog.exec_()
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Confirm if trading is active
        if self.app_state.status == SystemStatus.RUNNING:
            from PySide6.QtWidgets import QMessageBox
            
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Trading system is RUNNING. Are you sure you want to exit?\n\n"
                "(This will only close the GUI, not stop trading)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # Accept close
        event.accept()

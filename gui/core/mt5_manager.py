"""MT5 Connection Manager for GUI - handles MT5 connection with logging."""

import sys
from pathlib import Path
import base64

# Add project root to path (SMC-framework directory)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mt5.connector import MT5Connector
from core.market_sessions import MarketSessionChecker
import json


class MT5ConnectionManager:
    """
    MT5 Connection Manager with callback-based logging for GUI integration.
    
    Manages MT5 connection lifecycle and calls callbacks for GUI updates.
    """
    
    def __init__(self):
        self.connector = MT5Connector()
        self._connected = False
        self.session_checker = MarketSessionChecker()
        
        # Callbacks
        self.on_log = None  # Callback(level: str, message: str)
        self.on_status_changed = None  # Callback(connected: bool, account: str)
        self.on_error = None  # Callback(error: str)
    
    def load_credentials_from_file(self, config_path: str = None) -> dict:
        """
        Load MT5 credentials from GUI config file.
        
        Args:
            config_path: Path to config file (default: gui/data/mt5_config.json)
            
        Returns:
            dict: Credentials or None if not found
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "data" / "mt5_config.json"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            if self.on_log:
                self.on_log("WARNING", "No MT5 credentials found. Please configure in File → MT5 Connection Settings")
            return None
        
        try:
            with open(config_path, 'r') as f:
                credentials = json.load(f)
            
            # Decode password if it was saved encoded
            if credentials.get('remember_password', False):
                encoded_password = credentials.get('password_encoded', '')
                if encoded_password:
                    try:
                        credentials['password'] = base64.b64decode(encoded_password.encode()).decode()
                    except:
                        if self.on_log:
                            self.on_log("WARNING", "Failed to decode saved password")
                        credentials['password'] = None
            else:
                # Password not saved
                credentials['password'] = None
            
            if self.on_log:
                self.on_log("INFO", f"MT5 credentials loaded for account: {credentials.get('login', 'Unknown')}")
            return credentials
            
        except Exception as e:
            if self.on_log:
                self.on_log("ERROR", f"Failed to load MT5 credentials: {str(e)}")
            return None
    
    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """
        Connect to MT5 with provided credentials or from config file.
        
        Args:
            login: MT5 account login
            password: MT5 account password
            server: MT5 server (optional)
            
        Returns:
            bool: True if connected successfully
        """
        # Load from file if credentials not provided or empty
        if not login or not password:
            if self.on_log:
                self.on_log("INFO", "Loading MT5 credentials from config...")
            credentials = self.load_credentials_from_file()
            
            if credentials is None:
                if self.on_error:
                    self.on_error("No credentials configured. Please set up MT5 connection in File → MT5 Connection Settings")
                return False
            
            login = credentials.get('login')
            password = credentials.get('password')
            server = credentials.get('server')
            
            # Check if password was loaded successfully
            if not password:
                if self.on_log:
                    self.on_log("INFO", "Password not saved. Auto-connect skipped. Manual connection required.")
                return False
        
        # Start connection attempt
        if self.on_log:
            self.on_log("INFO", "=" * 60)
            self.on_log("INFO", "Starting MT5 connection...")
            self.on_log("INFO", f"Login: {login}")
            self.on_log("INFO", f"Password: {'*' * len(password) if password else 'NOT PROVIDED'}")
            self.on_log("INFO", f"Server: {server if server else 'Auto-detect'}")
            self.on_log("INFO", "=" * 60)
        
        # Check market session first
        market_status = self.check_market_session()
        if self.on_log:
            self.on_log("INFO", f"Server Time: {market_status['server_time']}")
            self.on_log("INFO", f"Day: {market_status['weekday']}")
        
        try:
            # Attempt connection
            success = self.connector.connect(
                login=int(login) if login else None,
                password=password,
                server=server if server else None
            )
            
            if success:
                self._connected = True
                account_info = self.connector.get_account_info()
                
                if account_info:
                    # Log success with details
                    if self.on_log:
                        self.on_log("SUCCESS", "✓ MT5 connection established!")
                        self.on_log("INFO", "-" * 60)
                        self.on_log("INFO", f"Account: {account_info['login']}")
                        self.on_log("INFO", f"Name: {account_info['name']}")
                        self.on_log("INFO", f"Server: {account_info['server']}")
                        self.on_log("INFO", f"Balance: ${account_info['balance']:,.2f}")
                        self.on_log("INFO", f"Equity: ${account_info['equity']:,.2f}")
                        self.on_log("INFO", f"Leverage: 1:{account_info['leverage']}")
                        self.on_log("INFO", f"Currency: {account_info['currency']}")
                        self.on_log("INFO", "-" * 60)
                    
                    # Update status
                    if self.on_status_changed:
                        self.on_status_changed(True, str(account_info['login']))
                    
                    return True
                else:
                    if self.on_log:
                        self.on_log("ERROR", "Connected but failed to retrieve account info")
                    if self.on_error:
                        self.on_error("Failed to retrieve account information")
                    return False
            else:
                self._connected = False
                if self.on_log:
                    self.on_log("ERROR", "✗ MT5 connection failed!")
                    self.on_log("ERROR", "Possible reasons:")
                    self.on_log("ERROR", "  • Invalid login or password")
                    self.on_log("ERROR", "  • Wrong server name")
                    self.on_log("ERROR", "  • MT5 terminal not installed")
                    self.on_log("ERROR", "  • Internet connection issues")
                
                if self.on_error:
                    self.on_error("Connection failed. Check credentials and MT5 installation.")
                if self.on_status_changed:
                    self.on_status_changed(False, "")
                
                return False
                
        except Exception as e:
            self._connected = False
            error_msg = f"Exception during connection: {str(e)}"
            if self.on_log:
                self.on_log("ERROR", error_msg)
            if self.on_error:
                self.on_error(error_msg)
            if self.on_status_changed:
                self.on_status_changed(False, "")
            
            return False
    
    def disconnect(self):
        """Disconnect from MT5."""
        if self._connected:
            if self.on_log:
                self.on_log("INFO", "Disconnecting from MT5...")
            self.connector.disconnect()
            self._connected = False
            if self.on_status_changed:
                self.on_status_changed(False, "")
            if self.on_log:
                self.on_log("INFO", "MT5 disconnected")
    
    def is_connected(self) -> bool:
        """Check if connected to MT5."""
        return self._connected
    
    def check_market_session(self) -> dict:
        """
        Check current market session status.
        
        Returns:
            dict: Market status information
        """
        status = self.session_checker.get_trading_status()
        
        # Log the status
        if self.on_log:
            if status['is_weekend']:
                self.on_log("WARNING", status['message'])
            elif status['market_open']:
                self.on_log("INFO", status['message'])
            else:
                self.on_log("INFO", status['message'])
        
        return status
    
    def get_account_info(self) -> dict:
        """Get current account information."""
        if self._connected:
            return self.connector.get_account_info()
        return None

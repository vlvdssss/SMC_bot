"""
Data Bridge - Connection to BAZA Trading System

This module provides the bridge between the GUI and the BAZA trading system.
It monitors BAZA output (files, sockets, or shared memory) and emits signals
when new data is available.

Communication Methods:
    1. File-based (default): Monitors state files
    2. Socket-based (future): Direct IPC connection
    3. Shared memory (future): High-performance data sharing

The bridge runs in a background thread/timer and periodically checks for updates.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QTimer


class DataBridge(QObject):
    """
    Bridge between GUI and BAZA trading system.
    
    Monitors BAZA output and emits signals when data changes.
    Currently implements file-based monitoring.
    """
    
    # Signals
    data_updated = Signal(dict)  # Emitted when new data available
    connection_status = Signal(bool)  # True if connected, False if lost
    error_occurred = Signal(str)  # Error message
    
    def __init__(self, baza_path: Path, update_interval: int = 1000):
        """
        Initialize data bridge.
        
        Args:
            baza_path: Path to BAZA system directory
            update_interval: Update interval in milliseconds (default: 1000ms)
        """
        super().__init__()
        
        self.baza_path = baza_path
        self.update_interval = update_interval
        
        # File paths
        self.state_file = baza_path / "data" / "gui_state.json"
        self.trades_file = baza_path / "data" / "gui_trades.json"
        self.logs_file = baza_path / "logs" / "trading.log"
        
        # State tracking
        self._last_state_mtime: Optional[float] = None
        self._last_trades_mtime: Optional[float] = None
        self._connected = False
        
        # Timer for polling
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_updates)
        
        # Create data directory if needed
        (baza_path / "data").mkdir(exist_ok=True)
    
    def start(self) -> None:
        """Start monitoring BAZA system."""
        self._timer.start(self.update_interval)
        self._set_connected(True)
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._timer.stop()
        self._set_connected(False)
    
    def is_connected(self) -> bool:
        """Check if connected to BAZA system."""
        return self._connected
    
    def _set_connected(self, connected: bool) -> None:
        """Update connection status."""
        if connected != self._connected:
            self._connected = connected
            self.connection_status.emit(connected)
    
    def _check_updates(self) -> None:
        """Check for updates from BAZA system."""
        try:
            # Check state file
            if self._check_file_updated(self.state_file):
                state_data = self._load_state_file()
                if state_data:
                    self.data_updated.emit(state_data)
            
            # Check trades file
            if self._check_file_updated(self.trades_file):
                trades_data = self._load_trades_file()
                if trades_data:
                    self.data_updated.emit(trades_data)
            
            # Update connection status
            self._set_connected(True)
            
        except Exception as e:
            self.error_occurred.emit(f"Error checking updates: {str(e)}")
            self._set_connected(False)
    
    def _check_file_updated(self, file_path: Path) -> bool:
        """
        Check if file has been modified since last check.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file was modified
        """
        if not file_path.exists():
            return False
        
        mtime = file_path.stat().st_mtime
        
        # Determine which mtime to compare
        if file_path == self.state_file:
            if self._last_state_mtime is None or mtime > self._last_state_mtime:
                self._last_state_mtime = mtime
                return True
        elif file_path == self.trades_file:
            if self._last_trades_mtime is None or mtime > self._last_trades_mtime:
                self._last_trades_mtime = mtime
                return True
        
        return False
    
    def _load_state_file(self) -> Optional[Dict[str, Any]]:
        """
        Load state data from file.
        
        Expected format:
        {
            "balance": 10000.0,
            "equity": 10234.56,
            "daily_pnl": 234.56,
            "total_pnl": 456.78,
            "max_drawdown": 5.75,
            "current_drawdown": 2.34,
            "risk_used": 75.0,
            "instruments": {
                "XAUUSD": {
                    "pnl": 123.45,
                    "open_positions": 1,
                    "risk_used": 50.0
                },
                "EURUSD": {
                    "pnl": 111.11,
                    "open_positions": 0,
                    "risk_used": 0.0
                }
            },
            "status": "RUNNING",
            "mode": "DEMO"
        }
        
        Returns:
            State dictionary or None if error
        """
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.error_occurred.emit(f"Error loading state file: {str(e)}")
            return None
    
    def _load_trades_file(self) -> Optional[Dict[str, Any]]:
        """
        Load trades data from file.
        
        Expected format:
        {
            "new_trade": {
                "id": 123,
                "symbol": "XAUUSD",
                "direction": "BUY",
                "entry_price": 2650.34,
                "tp": 2680.00,
                "sl": 2630.00,
                "lot_size": 0.05,
                "entry_time": "2025-12-20T14:23:45"
            },
            "closed_trade": {
                "trade_id": 122,
                "exit_price": 2675.50,
                "pnl": 125.50,
                "r_multiple": 2.5
            }
        }
        
        Returns:
            Trades dictionary or None if error
        """
        try:
            with open(self.trades_file, 'r') as f:
                data = json.load(f)
                
                # Convert timestamps
                if 'new_trade' in data and 'entry_time' in data['new_trade']:
                    data['new_trade']['entry_time'] = datetime.fromisoformat(
                        data['new_trade']['entry_time']
                    )
                
                return data
                
        except Exception as e:
            self.error_occurred.emit(f"Error loading trades file: {str(e)}")
            return None
    
    # === Control Methods (send commands to BAZA) ===
    
    def send_command(self, command: str, params: Optional[Dict] = None) -> bool:
        """
        Send command to BAZA system.
        
        Commands are written to a command file that BAZA monitors.
        
        Args:
            command: Command name ("start", "stop", "pause", etc.)
            params: Optional command parameters
            
        Returns:
            True if command sent successfully
        """
        try:
            command_file = self.baza_path / "data" / "gui_commands.json"
            
            data = {
                "command": command,
                "params": params or {},
                "timestamp": datetime.now().isoformat()
            }
            
            with open(command_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error sending command: {str(e)}")
            return False
    
    def start_trading(self) -> bool:
        """Send START command to BAZA."""
        return self.send_command("start")
    
    def stop_trading(self) -> bool:
        """Send STOP command to BAZA."""
        return self.send_command("stop")
    
    def pause_trading(self) -> bool:
        """Send PAUSE command to BAZA."""
        return self.send_command("pause")
    
    def set_risk(self, risk_pct: float) -> bool:
        """
        Update risk parameter.
        
        Args:
            risk_pct: New risk percentage
        """
        return self.send_command("set_risk", {"risk_pct": risk_pct})
    
    # === Demo/Mock Methods ===
    
    def generate_mock_data(self) -> Dict[str, Any]:
        """
        Generate mock data for testing GUI without BAZA running.
        
        Returns:
            Mock state data
        """
        import random
        
        return {
            "balance": 10000.0,
            "equity": 10000.0 + random.uniform(-500, 1000),
            "daily_pnl": random.uniform(-200, 500),
            "total_pnl": random.uniform(-1000, 3000),
            "max_drawdown": random.uniform(3, 15),
            "current_drawdown": random.uniform(0, 8),
            "risk_used": random.uniform(30, 90),
            "instruments": {
                "XAUUSD": {
                    "pnl": random.uniform(-300, 800),
                    "open_positions": random.randint(0, 2),
                    "risk_used": random.uniform(0, 75),
                },
                "EURUSD": {
                    "pnl": random.uniform(-100, 300),
                    "open_positions": random.randint(0, 1),
                    "risk_used": random.uniform(0, 50),
                }
            },
            "status": "RUNNING",
            "mode": "DEMO"
        }
    
    def enable_mock_mode(self) -> None:
        """Enable mock data generation for testing."""
        # Disconnect file monitoring
        self._timer.timeout.disconnect()
        
        # Connect mock data generator
        self._timer.timeout.connect(self._emit_mock_data)
    
    def _emit_mock_data(self) -> None:
        """Emit mock data."""
        mock_data = self.generate_mock_data()
        self.data_updated.emit(mock_data)

# 🎯 SMC Trading Control Center - GUI

Professional control center for algorithmic trading system.

## Overview

This is a **read-only control and monitoring interface** for the SMC trading system. It does NOT contain trading logic - that's in the BAZA system. This GUI provides:

- ✅ Real-time monitoring of trading activity
- ✅ Performance analytics and charts
- ✅ Trade history and logs
- ✅ Execution control (start/stop/pause)
- ✅ Risk management controls

## Technology Stack

- **Framework**: PySide6 (Qt for Python)
- **Charts**: matplotlib
- **Packaging**: PyInstaller (.exe)
- **Architecture**: Clean separation (UI / Core / Data)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Application

```bash
# Normal mode
python main.py

# Read-only mode (monitoring only)
python main.py --readonly

# Force demo mode
python main.py --mode demo

# Enable debug logging
python main.py --debug
```

### 3. First Launch

The GUI will look for BAZA system in `../BAZA/`. If not found, it will display mock data for testing.

## Project Structure

```
gui/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
│
├── core/                    # Core logic layer
│   ├── app_state.py        # Application state manager
│   ├── data_bridge.py      # Bridge to BAZA system
│   └── logger.py           # Logging configuration
│
├── views/                   # Main views
│   ├── main_window.py      # Main application window
│   ├── analytics_tab.py    # Analytics tab
│   ├── trades_tab.py       # Trades history tab
│   ├── control_tab.py      # Control panel tab
│   └── logs_tab.py         # Logs viewer tab
│
├── widgets/                 # Reusable widgets
│   ├── status_bar_widget.py    # Status bar
│   ├── equity_card.py          # Equity display card
│   ├── portfolio_overview.py  # Portfolio cards
│   └── equity_curve.py         # Equity chart
│
├── styles/                  # Styling
│   └── dark_theme.py       # Dark theme styles
│
└── resources/               # Assets (icons, images)
```

## Architecture

### Data Flow

```
BAZA System → Data Bridge → App State → UI Widgets
     ↓             ↓            ↓           ↓
  Trading      JSON/IPC    In-memory    Visual
  Engine                    State       Updates
```

### Layer Responsibilities

**1. BAZA System** (separate):
- Executes trades
- Manages positions
- Writes state to files

**2. Data Bridge** (`core/data_bridge.py`):
- Reads BAZA output
- Parses and validates data
- Emits signals to GUI

**3. App State** (`core/app_state.py`):
- Maintains current state
- Processes updates
- Notifies widgets

**4. UI Widgets**:
- Display state
- Handle user input
- Send commands back

### Communication

Currently implements **file-based** communication:

```
BAZA writes to: data/gui_state.json, data/gui_trades.json
GUI polls files every 1 second
```

**Future**: Socket-based (ZMQ) for real-time updates

## Key Features

### 1. Status Bar
- System status (RUNNING/STOPPED/PAUSED)
- Trading mode (DEMO/LIVE)
- Uptime counter
- Portfolio risk usage
- Alerts indicator

### 2. Dashboard
- **Equity Card**: Balance, Equity, P&L, Drawdown
- **Portfolio Overview**: Per-instrument cards (XAUUSD, EURUSD)
- **Equity Curve**: Live performance chart

### 3. Analytics Tab
- Full equity curve (zoomable)
- Drawdown chart
- Win rate progression
- Profit distribution

### 4. Trades Tab
- Sortable trade history table
- Filters by symbol, date, status
- Trade details popup
- Export to CSV

### 5. Control Tab
- Start/Stop/Pause buttons
- Demo/Live mode switch
- Risk sliders (per-trade, max portfolio)
- System health indicator

### 6. Logs Tab
- Live log stream
- Color-coded levels (INFO/WARNING/ERROR)
- Search and filters
- Copy last error button

## Unique Features

### System Health Indicator

Real-time health assessment:
- **STABLE**: DD < 10%, Risk < 80%
- **CAUTION**: DD 10-15%, Risk 80-100%
- **RISKY**: DD > 15%, Risk > 100%

### Frozen Strategy Badge

Visual indicator that strategies are protected and cannot be modified from GUI.

### Read-Only Mode

Launch with `--readonly` for monitoring without control buttons.

## Building .exe

### Development Build (one-folder)

```bash
pyinstaller --windowed --name "SMC-Control-Center" main.py
```

Output: `dist/SMC-Control-Center/`

### Production Build (one-file)

```bash
pyinstaller --onefile --windowed --icon=resources/icon.ico main.py
```

Output: `dist/SMC-Control-Center.exe`

### Distribution Package

```
SMC-Control-Center.exe
config/
  settings.json
  theme.qss
logs/
  (auto-created)
```

## Configuration

### GUI Config (`config/gui_config.json`)

```json
{
  "update_interval": 1000,
  "baza_path": "../BAZA",
  "theme": "dark",
  "window_size": [1400, 900],
  "enable_sound_alerts": false,
  "log_level": "INFO"
}
```

### BAZA Integration

GUI expects these files from BAZA:

**State file** (`BAZA/data/gui_state.json`):
```json
{
  "balance": 10000.0,
  "equity": 10234.56,
  "daily_pnl": 234.56,
  "instruments": {
    "XAUUSD": {"pnl": 123.45, "open_positions": 1},
    "EURUSD": {"pnl": 111.11, "open_positions": 0}
  },
  "status": "RUNNING",
  "mode": "DEMO"
}
```

**Trades file** (`BAZA/data/gui_trades.json`):
```json
{
  "new_trade": {
    "id": 123,
    "symbol": "XAUUSD",
    "direction": "BUY",
    "entry_price": 2650.34,
    "entry_time": "2025-12-20T14:23:45"
  }
}
```

## Development

### Running in Development

```bash
python main.py --debug
```

### Mock Mode (No BAZA)

```python
# In main.py, enable mock mode
data_bridge.enable_mock_mode()
```

### Adding New Widgets

1. Create widget in `widgets/`
2. Connect to `app_state` signals
3. Add to `main_window.py`

### Adding New Tabs

1. Create tab in `views/`
2. Inherit from `QWidget`
3. Add to tab widget in `main_window.py`

## Troubleshooting

### GUI doesn't show data
- Check BAZA is running
- Verify file paths in config
- Enable mock mode for testing

### High CPU usage
- Increase `update_interval` in config
- Check for excessive logging

### .exe doesn't run
- Check hidden imports in PyInstaller
- Include all resources in spec file

## Future Enhancements

- [ ] Socket-based communication (ZMQ)
- [ ] Telegram bot integration
- [ ] Email alerts
- [ ] PDF reports
- [ ] Multi-account support
- [ ] Advanced analytics (correlation, VaR)

## License

Part of SMC-framework project.

## Support

See [GUI_ARCHITECTURE.md](../GUI_ARCHITECTURE.md) for detailed architecture documentation.

---

**Version**: 1.0.0  
**Status**: Production Ready (Framework)  
**Next**: Complete widget implementations

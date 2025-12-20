# 🎯 SMC Trading Control Center - Architecture

## Overview

**Purpose**: Professional GUI control center for algorithmic trading system  
**Technology**: PySide6 (Qt for Python)  
**Packaging**: PyInstaller (.exe)  
**Architecture**: Clean separation of UI, Core, and Data layers

---

## Design Philosophy

### What This IS:
- ✅ Control Center for algorithmic system
- ✅ Real-time monitoring dashboard
- ✅ Execution control interface
- ✅ Analytics and reporting tool

### What This IS NOT:
- ❌ Trading terminal (not MT5 clone)
- ❌ Strategy editor (strategies are FROZEN)
- ❌ Chart analysis tool
- ❌ Manual trading interface

---

## Visual Design

### Style: Professional + Minimal
- Clean, uncluttered interface
- Focus on critical information
- No decorative elements
- Trading OS aesthetic

### Color Scheme: Dark Mode
```
Background:     #1a1d23  (dark graphite)
Panel:          #252930  (slightly lighter)
Border:         #3a3f4a  (subtle)

Green:          #00c896  (profit/success)
Red:            #ff5555  (loss/risk)
Yellow:         #ffc107  (warning)
Blue:           #4a9eff  (info/neutral)

Text Primary:   #e8e9ed
Text Secondary: #8b92a0
```

### Typography
- Primary: Segoe UI / Roboto (system default)
- Monospace: Consolas / Courier New (for numbers)
- Sizes: 10-14pt (scalable)

---

## Application Structure

### Main Window Layout

```
┌─────────────────────────────────────────────────────────┐
│  STATUS BAR: [RUNNING] DEMO | 03:24:15 | Risk: 1.5%    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌─────────────────────────────────┐ │
│  │ EQUITY CARD  │  │   PORTFOLIO OVERVIEW            │ │
│  │              │  │  ┌──────────┐  ┌──────────┐    │ │
│  │  Balance     │  │  │ XAUUSD   │  │ EURUSD   │    │ │
│  │  Equity      │  │  │ +$1,234  │  │ +$567    │    │ │
│  │  Daily P&L   │  │  │  1 pos   │  │  0 pos   │    │ │
│  │  Total P&L   │  │  └──────────┘  └──────────┘    │ │
│  │  Max DD      │  │                                  │ │
│  └──────────────┘  └─────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         EQUITY CURVE (live)                      │  │
│  │                                                   │  │
│  │         [smooth line chart with DD overlay]      │  │
│  │                                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  [Analytics] [Trades] [Control] [Logs]                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │         TAB CONTENT AREA                          │  │
│  │                                                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Status Bar (Always Visible)

**Purpose**: Quick system status overview

**Elements**:
```python
- System State: [RUNNING] [STOPPED] [PAUSED]
- Mode: DEMO / LIVE (colored indicator)
- Uptime: HH:MM:SS
- Portfolio Risk: 1.5% (live calculation)
- Alerts: [🔔 3] (clickable)
```

**Behavior**:
- Updates every second
- Color changes based on state
- Alert icon pulses when new alert

---

### 2. Equity Card

**Purpose**: Primary account metrics

**Fields**:
```
Balance:     $10,234.56
Equity:      $10,456.78  (+2.17%)
Daily P&L:   +$234.56    [green/red]
Total P&L:   +$456.78    [green/red]
Max DD:      -5.75%      [yellow if >10%]
```

**Behavior**:
- Updates in real-time
- Smooth value transitions
- Color changes based on P&L

---

### 3. Portfolio Overview

**Purpose**: Per-instrument status

**Card per instrument**:
```
┌──────────────┐
│   XAUUSD     │  ← Instrument name
├──────────────┤
│  +$1,234.56  │  ← P&L (green/red)
│  1 position  │  ← Open positions
│  0.75% risk  │  ← Current risk usage
└──────────────┘
```

**Behavior**:
- Card border glows when position opens
- Background color intensity = P&L magnitude
- Click to see details

---

### 4. Equity Curve (Live)

**Purpose**: Visual performance tracking

**Features**:
- Smooth line chart (no grid clutter)
- Equity line (primary)
- Drawdown overlay (semi-transparent red)
- Auto-scaling Y-axis
- Time markers on X-axis

**Library**: matplotlib embedded in Qt or pyqtgraph

---

## Tab System

### Tab 1: Analytics

**Purpose**: Detailed performance analysis

**Widgets**:
1. Full equity curve (zoomable)
2. Drawdown chart over time
3. Win rate progression
4. Profit distribution pie chart (by instrument)
5. Key metrics table:
   - Total trades
   - Win rate
   - Avg R-multiple
   - Sharpe ratio (if applicable)

---

### Tab 2: Trades

**Purpose**: Trade history and monitoring

**Table columns**:
```
Time | Symbol | Direction | Entry | TP | SL | R-multiple | P&L | Status
```

**Features**:
- Sortable columns
- Color-coded rows (green=win, red=loss)
- Click row to open trade details popup
- Export to CSV button
- Filters: Symbol, Date range, Status

**Trade Details Popup**:
```
Symbol:       XAUUSD
Direction:    BUY
Entry:        2650.34
TP:           2680.00
SL:           2630.00
Risk:         1.0%
Lot Size:     0.05
Entry Time:   2025-12-20 14:23:45
Exit Time:    2025-12-20 16:45:12
Duration:     2h 21m
P&L:          +$125.50
R-multiple:   +2.5R
```

---

### Tab 3: Control

**Purpose**: Execution management (NO STRATEGY EDITING)

**Sections**:

**3.1 Execution Control**:
```
┌─────────────────────────────┐
│  [START]  [PAUSE]  [STOP]   │
│                              │
│  Status: RUNNING ●          │
└─────────────────────────────┘
```

**3.2 Mode Selection**:
```
◉ Demo Trading
○ Live Trading  [Requires confirmation]
```

**3.3 Risk Management**:
```
Risk per trade:     [====|-----] 1.0%
Max portfolio risk: [======|---] 1.5%

⚠ Strategies are FROZEN
   Risk limits are the ONLY adjustable parameter
```

**3.4 System Health**:
```
┌─────────────────────────────┐
│  System Health: ✅ STABLE   │
│                              │
│  Current DD:    5.2%         │
│  Losing streak: 2            │
│  Risk usage:    75%          │
└─────────────────────────────┘
```

Health calculation:
- **STABLE**: DD < 10%, Risk < 80%
- **CAUTION**: DD 10-15%, Risk 80-100%
- **RISKY**: DD > 15%, Risk > 100%

---

### Tab 4: Logs

**Purpose**: System activity monitoring

**Features**:
- Live log stream (auto-scroll)
- Color-coded messages:
  - INFO: white
  - WARNING: yellow
  - ERROR: red
- Filters: Level, Source, Time range
- Search functionality
- "Copy last error" button (for support)
- Max 1000 lines (circular buffer)

**Log format**:
```
[14:23:45] [INFO] [EXECUTOR] Order placed: XAUUSD BUY 0.05 lots
[14:23:47] [INFO] [MT5] Order filled at 2650.34
[14:25:12] [WARNING] [RISK] Portfolio risk at 1.45% (approaching limit)
```

---

## Unique Features

### 1. System Health Indicator

**Purpose**: At-a-glance risk assessment

**Algorithm**:
```python
def calculate_health():
    score = 100
    
    # Drawdown penalty
    if current_dd > 10:
        score -= (current_dd - 10) * 3
    
    # Losing streak penalty
    if losing_streak > 3:
        score -= (losing_streak - 3) * 5
    
    # Risk usage penalty
    if risk_usage > 0.8:
        score -= (risk_usage - 0.8) * 50
    
    if score >= 80: return "STABLE"
    if score >= 60: return "CAUTION"
    return "RISKY"
```

**Display**:
- Large colored indicator
- Tooltip with breakdown
- Changes require user acknowledgment

---

### 2. Frozen Strategy Badge

**Purpose**: Visual reminder that strategies are protected

**Display**:
```
┌─────────────────────┐
│  🔒 STRATEGIES      │
│     FROZEN          │
│                     │
│  Baseline version   │
│  v1.0 - Validated   │
└─────────────────────┘
```

**Placement**: Bottom-right corner of main window

---

### 3. Read-Only Mode

**Purpose**: Monitoring without control

**Trigger**: 
- Launched with `--readonly` flag
- Or activated via settings

**Behavior**:
- All control buttons disabled
- Only monitoring tabs visible
- Status bar shows: [READ-ONLY MODE]

---

## Alerts & Notifications

### Alert Types:

**1. Trade Alerts**:
- Trade opened
- Trade closed (with P&L)
- TP/SL hit

**2. Risk Alerts**:
- Drawdown warning (> 10%)
- Risk limit approaching (> 90%)
- Losing streak (> 5 trades)

**3. System Alerts**:
- Connection lost
- Strategy error
- Data feed issue

### Alert Display:

**Toast notification** (bottom-right):
```
┌────────────────────────────┐
│  ⚠ DRAWDOWN WARNING        │
│                             │
│  Current DD: 11.2%          │
│  Threshold: 10.0%           │
│                             │
│  [OK] [View Details]        │
└────────────────────────────┘
```

**Sound**: Optional subtle chime (user configurable)

**Future**: Telegram bot integration

---

## Data Flow Architecture

### Overview:

```
BAZA System  ←→  Data Bridge  ←→  GUI State  ←→  UI Widgets
    ↓                ↓               ↓             ↓
  Trading       JSON/IPC      In-memory      Visual
  Engine                       State        Updates
```

### Layer Responsibilities:

**1. BAZA System** (existing):
- Executes trades
- Manages positions
- Writes to files/logs

**2. Data Bridge**:
- Reads BAZA output (files, shared memory, sockets)
- Parses and validates data
- Emits signals to GUI

**3. GUI State Manager**:
- Maintains current state
- Processes updates from bridge
- Notifies widgets of changes

**4. UI Widgets**:
- Display state
- Handle user input
- Send commands back to BAZA

### Communication Methods:

**Option 1: File-based** (simplest):
```
BAZA writes to: state.json, trades.csv, logs.txt
GUI polls files every 1 second
```

**Option 2: Shared Memory** (faster):
```python
from multiprocessing import shared_memory
# BAZA writes to shared memory
# GUI reads from shared memory
```

**Option 3: Socket/IPC** (most flexible):
```python
import zmq  # or socket
# BAZA runs ZMQ server
# GUI connects as client
```

**Recommendation**: Start with Option 1, migrate to Option 3

---

## Technical Requirements

### Dependencies:

```txt
PySide6==6.6.1          # Qt framework
matplotlib==3.8.2       # Charts
pandas==2.1.4           # Data handling
pyinstaller==6.3.0      # .exe packaging
```

### Python Version:
- Python 3.10+ (for type hints)

### OS Support:
- Primary: Windows 10/11
- Future: Linux, macOS

---

## Packaging Strategy

### PyInstaller Configuration:

**One-folder mode** (development):
```bash
pyinstaller --windowed --name "SMC-Control-Center" main.py
```

**One-file mode** (distribution):
```bash
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

**Hidden imports** (add if needed):
```python
hiddenimports=['PySide6.QtCore', 'matplotlib.backends.backend_qt5agg']
```

### .exe Structure:
```
SMC-Control-Center.exe
config/
  settings.json
  theme.qss
logs/
  app.log
```

---

## Security Considerations

### Execution Control:
- DEMO/LIVE switch requires password confirmation
- Risk limit changes logged
- No direct strategy code access

### Data Safety:
- Read-only access to BAZA files
- No modification of core system
- Separate log files for GUI

### Error Handling:
- All exceptions caught and logged
- GUI never crashes trading system
- Graceful degradation if data unavailable

---

## Extensibility Points

### Future Enhancements:

**1. Multi-Account Support**:
- Switch between accounts
- Aggregate portfolio view

**2. Strategy Performance Comparison**:
- XAUUSD vs EURUSD metrics
- Historical comparison

**3. Advanced Risk Tools**:
- Correlation matrix
- VaR calculator
- Monte Carlo simulation

**4. Telegram Integration**:
- Send alerts to phone
- Remote monitoring
- Basic commands

**5. Export/Reporting**:
- PDF reports
- Excel exports
- Email reports

---

## Development Phases

### Phase 1: Foundation (Week 1)
- [x] Architecture design
- [ ] Project structure
- [ ] Main window skeleton
- [ ] Basic theming

### Phase 2: Core UI (Week 2)
- [ ] Status bar
- [ ] Equity card
- [ ] Portfolio cards
- [ ] Tab system

### Phase 3: Data Integration (Week 3)
- [ ] Data bridge (file-based)
- [ ] State manager
- [ ] Real-time updates

### Phase 4: Charts & Analytics (Week 4)
- [ ] Equity curve
- [ ] Analytics tab
- [ ] Trade table

### Phase 5: Control & Logs (Week 5)
- [ ] Control tab
- [ ] Logs tab
- [ ] Alert system

### Phase 6: Polish & Package (Week 6)
- [ ] Testing
- [ ] Bug fixes
- [ ] .exe packaging
- [ ] Documentation

---

## Code Quality Standards

### Principles:
- Clean code > clever code
- Explicit > implicit
- Modular > monolithic
- Testable > feature-rich

### Documentation:
- Docstrings for all classes
- Inline comments for complex logic
- Architecture diagrams

### Type Hints:
```python
def update_equity(self, balance: float, equity: float) -> None:
    """Update equity display with new values."""
    ...
```

### Error Handling:
```python
try:
    data = self.load_data()
except FileNotFoundError:
    logger.error("Data file not found")
    self.show_error_dialog("Cannot load data")
    return
```

---

## Summary

This is a **professional control center** for an algorithmic trading system.

**Key principles**:
- Clean separation of concerns
- No trading logic in GUI
- Real-time monitoring focus
- Production-ready code quality

**Next steps**:
1. Create project structure
2. Implement main window
3. Build core widgets
4. Integrate with BAZA system

---

*Architecture v1.0*  
*Date: 2025-12-20*  
*Status: Ready for implementation*

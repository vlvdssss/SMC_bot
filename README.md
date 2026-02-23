#  BAZA Trading Bot - AI-Powered MT5 Automation

> **Automated trading bot for MetaTrader 5 powered by GPT-4 artificial intelligence**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![MT5](https://img.shields.io/badge/MetaTrader-5-green.svg)](https://www.metatrader5.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)
[![Status](https://img.shields.io/badge/Status-Production-success.svg)](https://github.com)
[![Version](https://img.shields.io/badge/Version-5.0-blue.svg)](https://github.com)

---

## 🚀 ONE-CLICK INSTALL & RUN

**Windows 10/11 - Ready in 2 minutes!**

```powershell
# 1. Clone repository
git clone <your-repo-url>
cd SMC_bot

# 2. Run setup & launch GUI
.\setup_and_run.ps1
```

**That's it!** The script will:
- ✅ Check Python 3.9+ installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Copy config templates
- ✅ Launch GUI automatically

**First-time setup:**
1. Script launches GUI automatically
2. Go to **Settings → General** and enter your GPT API key
3. Go to **Settings → MT5 Settings** and configure your MT5 account
4. *(Optional)* Configure Telegram in **Settings → Telegram**
5. Click **Save** - all settings save automatically!

**Requirements:** Windows 10/11, Python 3.9-3.12 (auto-detected by setup script)

---

## ⚙️ Project Status

- ✅ **Production Ready** - stable version for live trading
- 🤖 **Pure AI Mode** - 100% GPT-4 powered decision making
- 🔒 **Risk Management** - advanced risk controls & filters
- 📱 **Telegram Integration** - complete notification system
- 🎨 **Modern GUI** - customtkinter-based interface
- 🔧 **Zero Config** - all settings via GUI, no manual file editing

---

##  Key Features

###  Pure AI Trading
- **100% GPT-4 decisions** - no technical indicators
- **Every 5-60 minutes analysis** - continuous market monitoring
- **Chart screenshots** - visual analysis of M5, M15, H1
- **Real-time news** - fundamental analysis integration

###  Risk Management
- **Trade Filters** - confidence, spread, R/R quality checks
- **Cooldown System** - smart spacing between trades (15-180 min)
- **Circuit Breaker** - auto-block after consecutive losses
- **Daily Limits** - maximum trades per day protection

###  Telegram Integration
- **Trade notifications** - open/close with detailed stats
- **AI signals with buttons** - delete signal with one tap
- **Daily reports** - automatic performance summaries
- **Interactive bot** - command buttons for status & reports

###  Configuration Presets
- **SAFE (Default)** - Balanced: 75% confidence, 6 daily trades
- **STRICT** - Quality>Quantity: 82% confidence, 4 daily trades
- **ACTIVE** - More trades: 70% confidence, 8 daily trades

---

##  Quick Start Guide

### Option 1: Automated Setup (Recommended)

Run the **all-in-one installer**:

```powershell
.\setup_and_run.ps1
```

### Option 2: Manual Setup

<details>
<summary>Click to expand manual steps</summary>

1. **Create virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Copy config templates:**
   ```powershell
   Copy-Item config\examples\*.yaml config\
   ```

4. **Create .env file:**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env and add your API keys
   ```

5. **Launch GUI:**
   ```powershell
   python src\gui\app_v2.py
   ```

</details>

---

##  Configuration via GUI

**All settings are managed through the GUI - no manual file editing required!**

### 1. GPT API Key Setup
1. Open GUI → **Settings → General**
2. Enter your OpenAI API key (get from: https://platform.openai.com/api-keys)
3. Click **Test GPT Connection**
4. Click **Save**

### 2. MT5 Connection Setup
1. Open GUI → **Settings → MT5 Settings**
2. Enter your account login, password, server
3. Click **Test Connection** to verify
4. Click **Save**

### 3. Telegram Notifications (Optional)
1. Create bot with @BotFather on Telegram
2. Get your chat ID from @userinfobot
3. Open GUI → **Settings → Telegram**
4. Enter bot token and chat ID
5. Click **Save**

### 4. Trading Filters (Optional)
1. Open GUI → **Settings → Trade Filters**
2. Adjust confidence, spread, cooldowns, daily limit
3. Click **Save**

**Or use presets:** Click preset buttons in GUI (SAFE / STRICT / ACTIVE)

---

##  Folder Structure

```
SMC_bot/
├── src/                    # Source code
│   ├── ai/                # AI modules (GPT-4, analysis, signals)
│   ├── core/              # Core logic (BotManager, ConfigManager)
│   ├── gui/               # GUI (app_v2.py, dialogs, components)
│   ├── live/              # Live trading execution
│   ├── mt5/               # MT5 integration
│   └── monitoring/        # Monitoring & Telegram
│
├── config/                 # Configuration files
│   ├── examples/          # ✅ SAFE - Template configs (no secrets)
│   ├── ai.yaml            # ❌ GIT IGNORED - Your AI settings
│   ├── trading.yaml       # ❌ GIT IGNORED - Your trading rules
│   ├── mt5.yaml           # ❌ GIT IGNORED - Your MT5 credentials
│   └── telegram.yaml      # ❌ GIT IGNORED - Your Telegram bot
│
├── data/                   # Runtime data
│   ├── runs/              # Run sessions (logs, state, events)
│   ├── decision_logs.jsonl # Trading decisions log
│   └── screenshots/       # Chart screenshots
│
├── docs/                   # Documentation
│   ├── QUICK_START.md     # Detailed setup guide
│   ├── AI_SCHEDULE_GUIDE.md
│   └── ... (20+ guides)
│
├── tests/                  # Test scripts
│   ├── test_preflight.py  # Pre-flight checks
│   └── test_production_readiness.py # Production validation
│
├── .env                    # ❌ GIT IGNORED - API keys
├── .env.example           # ✅ SAFE - API key template
├── .gitignore             # Git exclusions (secrets protected)
├── requirements.txt       # Python dependencies
├── setup_and_run.ps1     # 🚀 ONE-CLICK INSTALLER
└── README.md              # You are here

📁 Root also contains test files & documentation for different systems
```

---

##  Documentation

### Setup & Configuration
- [config/examples/README.md](config/examples/README.md) - Configuration templates guide
- [PRESETS_GUIDE.md](../PRESETS_GUIDE.md) - Trading presets comparison
- [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md) - Pre-production validation

### Advanced Guides
- [docs/AI_SCHEDULE_GUIDE.md](docs/AI_SCHEDULE_GUIDE.md) - AI analysis scheduling
- [docs/LOT_SIZE_GUIDE.md](docs/LOT_SIZE_GUIDE.md) - Position sizing
- [docs/TELEGRAM_SIGNAL_BUTTONS.md](docs/TELEGRAM_SIGNAL_BUTTONS.md) - Telegram features

### Troubleshooting
- [docs/OPENAI_API_TROUBLESHOOTING.md](docs/OPENAI_API_TROUBLESHOOTING.md) - GPT API issues
- [docs/GIT_PULL_FIX.md](docs/GIT_PULL_FIX.md) - Git update problems

---

##  Pre-Production Validation

Before starting a production run, validate all systems:

```powershell
# 1. Automated validation (7 tests)
python test_production_readiness.py

# 2. Pre-flight checks
python test_preflight.py

# 3. Follow manual tests in PRODUCTION_CHECKLIST.md
```

**Validates:**
- ✅ Config hot-reload (GUI → Runtime)
- ✅ DRY_RUN mode check
- ✅ Signal protection (no orders without signal)
- ✅ MT5 connection & watchdog
- ✅ Position confirmation logic
- ✅ Circuit breaker (error spike protection)
- ✅ Log files structure

See [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md) for details.

---

##  Command Reference

### First-time Setup
```powershell
.\setup_and_run.ps1              # Install & run GUI
.\setup_and_run.ps1 -DevMode     # Install with dev dependencies
.\setup_and_run.ps1 -NoGUI       # Setup only, don't launch GUI
```

### Daily Usage
```powershell
.\.venv\Scripts\Activate.ps1     # Activate virtual environment
python src\gui\app_v2.py         # Launch GUI
```

### Testing
```powershell
python test_production_readiness.py  # Production validation
python test_preflight.py             # Pre-flight checks
python test_preset_xauusd_safe.py    # Preset comparison
```

### Development
```powershell
pip install -r requirements-dev.txt  # Dev dependencies
pytest                               # Run tests
black .                              # Format code
```

---

##  Updating the Bot

### Safe Update (Recommended)
```powershell
git pull
```

If you get conflicts:
```powershell
.\fix_git_tracking.ps1
```

**Note:** Your config files are safe! They're not tracked by Git.

---

##  Security & Privacy

### What's Tracked by Git:
- ✅ Source code (`src/`)
- ✅ Config templates (`config/examples/`)
- ✅ Documentation (`docs/`, `*.md`)
- ✅ Setup scripts (`*.ps1`)
- ✅ Requirements (`requirements.txt`)

### What's IGNORED by Git:
- ❌ Your config files (`config/*.yaml`)
- ❌ Your API keys (`.env`)
- ❌ Your trading data (`data/`)
- ❌ Virtual environment (`.venv/`)
- ❌ Logs & screenshots

**You can safely commit to Git** - no secrets will be exposed!

---

##  FAQ

**Q: Do I need to edit YAML files manually?**  
A: No! All settings are managed through GUI. Just click **Settings** → configure → **Save**.

**Q: Where are my API keys stored?**  
A: In `.env` (root) and `config/ai.yaml`. Both are excluded from Git via `.gitignore`.

**Q: How do I backup my settings?**  
A: Copy the `config/` folder to a safe location. This contains all your settings.

**Q: Can I run this on Linux/Mac?**  
A: Partially. MT5 requires Windows. You can run the bot on Linux with Wine/VirtualBox, but it's not officially supported.

**Q: Is this safe for live trading?**  
A: The bot is production-ready, but **always start with dry_run: true** for testing! Switch to live only after validation.

**Q: How do I get Python?**  
A: Download from https://www.python.org/downloads/ (3.9-3.12). Check "Add Python to PATH" during install.

---

##  System Requirements

- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.9 - 3.12
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 500MB for installation, 2GB for data
- **Internet:** Stable connection required (GPT API, MT5)
- **MetaTrader 5:** Installed and configured
- **OpenAI API:** Valid API key with credits

---

##  Changelog

### [v5.0] - 2026-02-23
-  **One-click installer** - setup_and_run.ps1 for easy deployment
-  **Config templates** - config/examples/ with safe templates
-  **Production validation** - test_production_readiness.py (7 tests)
-  **GUI-only settings** - zero manual config editing
-  **Complete .gitignore** - all secrets protected
-  **Fixed dependencies** - locked versions in requirements.txt

### [v4.0] - 2026-02-02
-  Fixed PnL calculation for XAUUSD
-  GPT request deduplication (60s protection)
-  Delete Signal button (GUI + Telegram)
-  Increased min_confidence to 75%

---

##  Support & Contributing

**Questions?** Open an issue on GitHub or check documentation in `docs/`

**Contributing?** Pull requests welcome! Please test changes before submitting.

---

**Made with  and AI**

*Ready to trade? Run `.\setup_and_run.ps1` and start in 2 minutes!* 🚀

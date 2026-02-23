# Configuration Templates

This folder contains **template configuration files** for BAZA Trading Bot. These files are **safe to commit to Git** because they don't contain any sensitive data.

## 📋 Files Overview

| File | Description | Edit in GUI |
|------|-------------|------------|
| `ai.yaml` | AI/GPT settings, analysis schedule | Settings → General |
| `trading.yaml` | Trading rules, filters, risk management | Settings → General / Trade Filters |
| `mt5.yaml` | MetaTrader 5 connection credentials | Settings → MT5 Settings |
| `telegram.yaml` | Telegram bot notifications | Settings → Telegram |
| `portfolio.yaml` | Portfolio allocation, instruments | Manual edit only |
| `instruments.yaml` | Instrument specifications | Manual edit only |

## 🚀 Quick Setup

### Automatic (Recommended)

The `setup_and_run.ps1` script automatically copies these templates to `config/` directory on first run.

```powershell
.\setup_and_run.ps1
```

### Manual Setup

1. **Copy templates to config directory:**
   ```powershell
   Copy-Item config\examples\*.yaml config\
   ```

2. **Edit `.env` file** (root directory):
   ```bash
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   MT5_LOGIN=12345678
   MT5_PASSWORD=YourPassword
   MT5_SERVER=YourBrokerServer
   ```

3. **Launch GUI and configure**:
   ```powershell
   python src\gui\app_v2.py
   ```

## ⚙️ Configuration via GUI

**All settings can be configured through the GUI - no manual file editing needed!**

### 1. GPT API Key
- Open: **Settings → General**
- Enter your OpenAI API key
- Click **Save**
- ✅ Auto-saves to `.env` and `config/ai.yaml`

### 2. MT5 Connection
- Open: **Settings → MT5 Settings**
- Enter login, password, server
- Click **Test Connection**
- Click **Save**
- ✅ Auto-saves to `config/mt5.yaml`

### 3. Telegram Notifications
- Open: **Settings → Telegram**
- Enter bot token and chat ID
- Click **Save**
- ✅ Auto-saves to `config/telegram.yaml`

### 4. Trading Filters
- Open: **Settings → Trade Filters**
- Adjust confidence, spread, cooldowns
- Click **Save**
- ✅ Auto-saves to `config/trading.yaml`

## 🔒 Security

### Files in `.gitignore`:
- `config/ai.yaml` ❌ (contains API key)
- `config/mt5.yaml` ❌ (contains login/password)
- `config/telegram.yaml` ❌ (contains bot token)
- `config/trading.yaml` ❌ (contains strategy settings)
- `config/portfolio.yaml` ❌ (contains allocation)
- `config/instruments.yaml` ❌ (contains instrument config)
- `.env` ❌ (contains all secrets)

### Files in Git:
- `config/examples/*.yaml` ✅ (templates only, no secrets)
- `.env.example` ✅ (template only)

## 📝 Important Notes

### After First Run:
1. **All settings save automatically** when you click "Save" in GUI
2. **No need to manually edit YAML files** unless you want advanced customization
3. **Config changes apply immediately** via hot-reload system
4. **Backups are NOT automatic** - backup `config/` manually if needed

### For Advanced Users:
- You can manually edit YAML files if needed
- Changes are detected automatically when bot is running
- Restart bot after manual config edits for safety
- See `PRESETS_GUIDE.md` for preset configurations

## 🆘 Troubleshooting

### "Config file not found" error:
```powershell
# Re-run setup script
.\setup_and_run.ps1
```

### Settings not saving:
1. Check file permissions in `config/` directory
2. Check GUI logs for errors
3. Ensure `.env` file exists
4. Try running GUI as administrator

### Invalid API key:
1. Open GUI → Settings → General
2. Enter valid OpenAI API key
3. Click "Test GPT Connection"
4. Click "Save"

## 🔗 Related Documentation

- [QUICK_START.md](../../docs/QUICK_START.md) - First-time setup guide
- [PRESETS_GUIDE.md](../../PRESETS_GUIDE.md) - Trading strategy presets
- [README.md](../../README.md) - Main documentation

---

**Remember:** Never commit your actual `config/*.yaml` files with secrets to Git!
Use GUI to manage all sensitive settings safely. 🔒

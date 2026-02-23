# 🚀 GitHub Setup & Deployment Guide

This guide will help you publish BAZA Trading Bot to GitHub safely and securely.

---

## ✅ Pre-Flight Checklist

Before pushing to GitHub, verify:

- [x] **setup_and_run.ps1** created and tested
- [x] **requirements.txt** with fixed versions
- [x] **.gitignore** updated (all secrets excluded)
- [x] **config/examples/** templates created
- [x] **README.md** updated with install instructions
- [x] No secrets in any tracked files

---

## 🔒 Security Verification

### Step 1: Check .gitignore Coverage

Run this to see what **will be tracked** by Git:

```powershell
git status --ignored
```

**Should be IGNORED (not tracked):**
- ❌ `config/ai.yaml`
- ❌ `config/mt5.yaml`
- ❌ `config/telegram.yaml`
- ❌ `config/trading.yaml`
- ❌ `.env`
- ❌ `data/` (logs, screenshots)
- ❌ `.venv/` (virtual environment)

**Should be TRACKED:**
- ✅ `config/examples/*.yaml` (templates only)
- ✅ `.env.example` (template only)
- ✅ `src/` (source code)
- ✅ `requirements.txt`
- ✅ `setup_and_run.ps1`
- ✅ `README.md`

### Step 2: Verify No Secrets in Staging

```powershell
git add .
git diff --cached
```

**Look for:**
- ❌ API keys (sk-proj-...)
- ❌ Passwords
- ❌ Login credentials
- ❌ Bot tokens

If you see any secrets, **STOP** and add those files to `.gitignore`.

---

## 📤 Pushing to GitHub

### Option 1: New Repository (First Time)

1. **Create GitHub repository:**
   - Go to https://github.com/new
   - Name: `baza-trading-bot` (or your choice)
   - **Select: Private** (recommended for trading bots)
   - **Don't initialize** (we have existing code)
   - Click "Create repository"

2. **Initialize local Git (if not done):**
   ```powershell
   cd SMC_bot
   git init
   ```

3. **Add all files:**
   ```powershell
   git add .
   ```

4. **Verify what will be committed:**
   ```powershell
   git status
   ```
   
   Should show:
   - ✅ Source code files
   - ✅ Config templates
   - ✅ Documentation
   - ❌ No config/*.yaml (except examples/)
   - ❌ No .env

5. **Create initial commit:**
   ```powershell
   git commit -m "Initial release: StateCore v5.0 + One-Click Installer + Config Presets"
   ```

6. **Add remote & push:**
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/baza-trading-bot.git
   git branch -M main
   git push -u origin main
   ```

### Option 2: Existing Repository (Update)

1. **Verify current changes:**
   ```powershell
   git status
   ```

2. **Stage changes:**
   ```powershell
   git add .
   ```

3. **Commit:**
   ```powershell
   git commit -m "v5.0: One-click installer + GUI-based config + Production validation"
   ```

4. **Push:**
   ```powershell
   git push origin main
   ```

---

## 🎯 Post-Push Verification

After pushing, verify on GitHub:

### 1. Check Repository Files

Go to your GitHub repo and verify:

**✅ Should see:**
- `README.md` (with setup instructions)
- `setup_and_run.ps1` (installer)
- `requirements.txt` (dependencies)
- `src/` folder (source code)
- `config/examples/` folder (templates)
- `.env.example`
- `.gitignore`

**❌ Should NOT see:**
- `config/ai.yaml`
- `config/mt5.yaml`
- `config/telegram.yaml`
- `.env`
- `data/` folder
- `.venv/` folder

### 2. Test Contents of Template Files

Click on `config/examples/mt5.yaml` and verify:
- ❌ No real login/password
- ✅ Only placeholders (0, '', etc.)

Click on `.env.example` and verify:
- ❌ No real API keys
- ✅ Only `your_api_key_here` placeholders

### 3. Search for Secrets (GitHub)

Use GitHub search in your repo:
1. Search for: `sk-proj-` (OpenAI keys)
2. Search for: `bot_token` (Telegram)
3. Search for: your MT5 login number

**All searches should return 0 results** (or only in templates).

---

## 👥 Sharing with Team Members

### For Fresh Install (New User):

Send these instructions:

```
1. Clone repository:
   git clone https://github.com/YOUR_USERNAME/baza-trading-bot.git
   cd baza-trading-bot/SMC_bot

2. Run installer:
   .\setup_and_run.ps1

3. Configure in GUI:
   - Settings → General → Enter GPT API key
   - Settings → MT5 Settings → Enter credentials
   - Settings → Telegram → Enter bot token (optional)
   - Click Save

4. Start trading:
   - Check "Pre-Flight Check" passes
   - Set dry_run: true for testing
   - Click "START BOT"
```

### For Updates (Existing User):

```powershell
# Pull latest changes
git pull origin main

# Config files are preserved (not tracked by Git)
# Dependencies may need update:
pip install -r requirements.txt --upgrade

# Launch GUI
python src/gui/app_v2.py
```

---

## 🔐 Security Best Practices

### DO:
- ✅ Use **private repository** for trading bots
- ✅ Keep `.gitignore` up to date
- ✅ Review `git diff` before every commit
- ✅ Use `.env` for all secrets
- ✅ Store config templates in `config/examples/`
- ✅ Test fresh install from GitHub clone

### DON'T:
- ❌ Never commit real API keys
- ❌ Never commit passwords/logins
- ❌ Never commit `config/*.yaml` (except examples/)
- ❌ Never commit `.env` file
- ❌ Never commit trading data (`data/` folder)
- ❌ Don't share repository with untrusted users

---

## 🆘 Emergency: Secrets Leaked

If you accidentally committed secrets:

### Immediate Actions:

1. **Invalidate compromised credentials:**
   - OpenAI: Revoke API key at https://platform.openai.com/api-keys
   - MT5: Change password in MetaTrader
   - Telegram: Revoke bot token with @BotFather

2. **Remove from Git history:**
   ```powershell
   # WARNING: This rewrites history!
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch config/ai.yaml" \
   --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all
   ```

3. **Update .gitignore:**
   - Add the leaked file to `.gitignore`
   - Commit and push

4. **Inform team members:**
   - All members need to re-clone (history changed)

---

## 📊 GitHub Repository Settings

### Recommended Settings:

1. **Visibility:**
   - Set to **Private** (Settings → Danger Zone → Change visibility)

2. **Branch Protection:**
   - Go to Settings → Branches → Add rule
   - Branch name: `main`
   - Enable: "Require pull request reviews before merging"

3. **Secrets Management:**
   - Use GitHub Secrets for CI/CD (if applicable)
   - Settings → Secrets and variables → Actions

4. **Collaborators:**
   - Settings → Collaborators
   - Add only trusted team members
   - Use read-only access for reviewers

---

## ✅ Final Checklist

Before sharing repository URL:

- [ ] Pushed to GitHub successfully
- [ ] Verified no secrets in any tracked files
- [ ] Tested fresh clone and install on clean machine
- [ ] README.md has clear setup instructions
- [ ] setup_and_run.ps1 works end-to-end
- [ ] Config templates have no real credentials
- [ ] .gitignore covers all sensitive files
- [ ] Repository is set to Private
- [ ] Team members have access (if applicable)

---

## 🎉 Success!

Your repository is now ready for deployment!

**Repository URL:**
```
https://github.com/YOUR_USERNAME/baza-trading-bot
```

**Installation for new users:**
```powershell
git clone https://github.com/YOUR_USERNAME/baza-trading-bot.git
cd baza-trading-bot/SMC_bot
.\setup_and_run.ps1
```

---

**Need help?** Check:
- [README.md](README.md) - Main documentation
- [config/examples/README.md](config/examples/README.md) - Config guide
- [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md) - Pre-production tests

**Happy trading! 🚀**

# ========================================================================
# 🚀 BAZA Trading Bot - Setup & Run (One-Click Installer)
# ========================================================================
# Automatically sets up environment and launches GUI
# For Windows 10/11 with PowerShell 5.1+
# ========================================================================

param(
    [switch]$SkipVenv,      # Skip venv creation if already exists
    [switch]$DevMode,       # Install dev dependencies
    [switch]$NoGUI          # Setup only, don't launch GUI
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "BAZA Trading Bot - Setup"

# ========================================================================
# COLORS & HELPERS
# ========================================================================

function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "ℹ️  $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n▶️  $msg" -ForegroundColor Magenta }

# ========================================================================
# STEP 1: Check Execution Policy
# ========================================================================

Write-Step "Checking PowerShell Execution Policy..."
$policy = Get-ExecutionPolicy -Scope CurrentUser

if ($policy -eq "Restricted" -or $policy -eq "Undefined") {
    Write-Warning "Current policy: $policy (too restrictive)"
    Write-Info "Recommended: RemoteSigned"
    Write-Host ""
    Write-Host "Run this command in PowerShell (as admin or current user):" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" -ForegroundColor Cyan
    Write-Host ""
    
    $response = Read-Host "Do you want me to try fixing it now? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        try {
            Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
            Write-Success "Execution policy updated to RemoteSigned"
        } catch {
            Write-Error "Failed to update policy. Please run as administrator or manually."
            exit 1
        }
    } else {
        Write-Info "Skipping policy update. If script fails, update manually."
    }
} else {
    Write-Success "Execution policy OK: $policy"
}

# ========================================================================
# STEP 2: Check Python Installation
# ========================================================================

Write-Step "Checking Python installation..."

$pythonCmd = $null
$pythonVersion = $null

# Try python3 first, then python
foreach ($cmd in @("python3", "python")) {
    try {
        $versionOutput = & $cmd --version 2>&1
        if ($versionOutput -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            $patch = [int]$matches[3]
            
            if ($major -eq 3 -and $minor -ge 9) {
                $pythonCmd = $cmd
                $pythonVersion = "$major.$minor.$patch"
                break
            }
        }
    } catch {
        # Command not found, try next
    }
}

if ($null -eq $pythonCmd) {
    Write-Error "Python 3.9+ not found!"
    Write-Host ""
    Write-Info "Please install Python 3.9-3.12 from:"
    Write-Host "  • Official: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "  • Or use winget: winget install Python.Python.3.11" -ForegroundColor Cyan
    Write-Host ""
    Write-Warning "Make sure to check 'Add Python to PATH' during installation!"
    exit 1
}

Write-Success "Python $pythonVersion found ($pythonCmd)"

# ========================================================================
# STEP 3: Create Virtual Environment
# ========================================================================

Write-Step "Setting up virtual environment..."

$venvPath = ".venv"
$venvActivateScript = "$venvPath\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    if ($SkipVenv) {
        Write-Info "Virtual environment already exists (skipping recreation)"
    } else {
        Write-Warning "Virtual environment exists. Skipping recreation."
        Write-Info "Use -SkipVenv flag to suppress this message"
    }
} else {
    Write-Info "Creating new virtual environment..."
    & $pythonCmd -m venv $venvPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    
    Write-Success "Virtual environment created: $venvPath"
}

# Activate venv
Write-Info "Activating virtual environment..."
& $venvActivateScript

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to activate virtual environment"
    exit 1
}

Write-Success "Virtual environment activated"

# ========================================================================
# STEP 4: Upgrade pip
# ========================================================================

Write-Step "Upgrading pip..."
& python -m pip install --upgrade pip --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Success "pip upgraded to latest version"
} else {
    Write-Warning "pip upgrade failed (non-critical, continuing...)"
}

# ========================================================================
# STEP 5: Install Dependencies
# ========================================================================

Write-Step "Installing dependencies..."

if (-not (Test-Path "requirements.txt")) {
    Write-Error "requirements.txt not found!"
    exit 1
}

Write-Info "Installing from requirements.txt..."
& pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies from requirements.txt"
    Write-Info "Try running manually: pip install -r requirements.txt"
    exit 1
}

Write-Success "Core dependencies installed"

# Install dev dependencies if requested
if ($DevMode -and (Test-Path "requirements-dev.txt")) {
    Write-Info "Installing dev dependencies..."
    & pip install -r requirements-dev.txt --quiet
    Write-Success "Dev dependencies installed"
}

# ========================================================================
# STEP 6: Check & Copy Config Templates
# ========================================================================

Write-Step "Checking configuration files..."

$configDir = "config"
$examplesDir = "$configDir/examples"

# Config files to check
$configFiles = @(
    @{Name="ai.yaml"; Required=$true},
    @{Name="trading.yaml"; Required=$true},
    @{Name="mt5.yaml"; Required=$false},
    @{Name="telegram.yaml"; Required=$false},
    @{Name="portfolio.yaml"; Required=$true},
    @{Name="instruments.yaml"; Required=$true}
)

$missingConfigs = @()
$copiedConfigs = @()

foreach ($cfg in $configFiles) {
    $targetPath = "$configDir/$($cfg.Name)"
    $templatePath = "$examplesDir/$($cfg.Name)"
    
    if (-not (Test-Path $targetPath)) {
        if (Test-Path $templatePath) {
            # Copy from examples
            Copy-Item $templatePath $targetPath
            $copiedConfigs += $cfg.Name
            Write-Info "Created $($cfg.Name) from template"
        } else {
            if ($cfg.Required) {
                $missingConfigs += $cfg.Name
                Write-Warning "Missing required config: $($cfg.Name)"
            }
        }
    } else {
        Write-Success "$($cfg.Name) exists"
    }
}

if ($copiedConfigs.Count -gt 0) {
    Write-Success "Copied $($copiedConfigs.Count) config files from templates"
}

# Check .env file
Write-Info "Checking .env file..."
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Info "Created .env from .env.example"
        Write-Warning "⚠️  IMPORTANT: Edit .env and add your API keys!"
    } else {
        Write-Warning ".env.example not found - creating minimal .env"
        @"
# BAZA Trading Bot - Environment Variables
# Add your API keys below

OPENAI_API_KEY=your_api_key_here
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=your_server
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
"@ | Out-File -FilePath ".env" -Encoding utf8
        Write-Success "Created minimal .env file"
    }
} else {
    Write-Success ".env file exists"
}

# ========================================================================
# STEP 7: Verify Critical Imports
# ========================================================================

Write-Step "Running smoke test..."

$testScript = @"
import sys
try:
    import yaml
    import MetaTrader5
    import customtkinter
    import openai
    print('OK')
except ImportError as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"@

$testResult = & python -c $testScript 2>&1

if ($testResult -eq "OK") {
    Write-Success "All critical imports successful"
} else {
    Write-Error "Import test failed: $testResult"
    Write-Info "Some dependencies may be missing. Try: pip install -r requirements.txt"
    exit 1
}

# ========================================================================
# STEP 8: Display Setup Summary
# ========================================================================

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✅ SETUP COMPLETE!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

if ($copiedConfigs.Count -gt 0) {
    Write-Warning "📝 Config files created from templates:"
    foreach ($cfg in $copiedConfigs) {
        Write-Host "   • $cfg" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "⚠️  NEXT STEPS:" -ForegroundColor Yellow
    Write-Host "   1. Edit .env and add your API keys (GPT, MT5, Telegram)" -ForegroundColor Cyan
    Write-Host "   2. Open GUI and configure settings (Settings → MT5, GPT, Telegram)" -ForegroundColor Cyan
    Write-Host "   3. All settings save automatically - no need to edit files manually!" -ForegroundColor Cyan
    Write-Host ""
}

if ($missingConfigs.Count -gt 0) {
    Write-Warning "Missing required configs: $($missingConfigs -join ', ')"
    Write-Info "Please create these files manually or copy from examples/"
    Write-Host ""
}

# ========================================================================
# STEP 9: Launch GUI (if requested)
# ========================================================================

if (-not $NoGUI) {
    Write-Step "Launching GUI..."
    Write-Host ""
    Write-Info "Starting BAZA Trading Bot GUI..."
    Write-Info "Configure your settings in: Settings → General / MT5 / Telegram"
    Write-Host ""
    
    # Launch GUI
    try {
        & python src/gui/app_v2.py
    } catch {
        Write-Error "Failed to launch GUI: $_"
        Write-Info "Try running manually: python src/gui/app_v2.py"
        exit 1
    }
} else {
    Write-Info "GUI launch skipped (-NoGUI flag)"
    Write-Host ""
    Write-Host "To start the bot manually, run:" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  python src/gui/app_v2.py" -ForegroundColor Yellow
}

Write-Host ""
Write-Success "All done! Happy trading! 🚀"
Write-Host ""

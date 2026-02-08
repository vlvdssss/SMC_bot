# ===================================================================
# BAZA Trading Bot - Installation Check
# ===================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BAZA Trading Bot Installation Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# ===================================================================
# 1. Python
# ===================================================================
Write-Host "1. Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   * $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "   X Python not found" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "   X Python not found" -ForegroundColor Red
    $allOk = $false
}

# ===================================================================
# 2. Virtual environment
# ===================================================================
Write-Host "2. Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "   * Virtual environment found" -ForegroundColor Green
    
    # Check activation script
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Host "   * Activation script found" -ForegroundColor Green
    } else {
        Write-Host "   X Activation script not found" -ForegroundColor Red
        $allOk = $false
    }
} else {
    Write-Host "   X Virtual environment not found" -ForegroundColor Red
    Write-Host "   -> Run: .\install.ps1" -ForegroundColor Yellow
    $allOk = $false
}

# Activate environment for further checks
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
}

# ===================================================================
# 3. Critical packages
# ===================================================================
Write-Host "3. Checking critical packages..." -ForegroundColor Yellow

$packages = @{
    "MetaTrader5" = "MT5 Connection"
    "pandas" = "Data Processing"
    "numpy" = "Math Calculations"
    "pyyaml" = "Configuration"
    "python-telegram-bot" = "Telegram Notifications"
    "openai" = "AI Analysis"
    "customtkinter" = "GUI"
    "lightgbm" = "Machine Learning"
    "scikit-learn" = "ML Models"
    "matplotlib" = "Charts"
}

foreach ($pkg in $packages.Keys) {
    try {
        pip show $pkg 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   * $pkg - $($packages[$pkg])" -ForegroundColor Green
        } else {
            Write-Host "   X $pkg - $($packages[$pkg])" -ForegroundColor Red
            $allOk = $false
        }
    } catch {
        Write-Host "   X $pkg - $($packages[$pkg])" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# 4. Configuration files
# ===================================================================
Write-Host "4. Checking configuration..." -ForegroundColor Yellow

$configs = @{
    "config/mt5.yaml" = "MT5 connection (required)"
    "config/telegram.yaml" = "Telegram bot (required)"
    "config/ai.yaml" = "OpenAI API (required)"
    "config/trading.yaml" = "Trading settings"
    "config/instruments.yaml" = "Instruments"
    "config/portfolio.yaml" = "Portfolio"
}

$missingConfigs = @()
foreach ($cfg in $configs.Keys) {
    if (Test-Path $cfg) {
        Write-Host "   * $cfg" -ForegroundColor Green
    } else {
        $exampleFile = "$cfg.example"
        if (Test-Path $exampleFile) {
            Write-Host "   ! $cfg (has .example)" -ForegroundColor Yellow
            $missingConfigs += $cfg
        } else {
            Write-Host "   X $cfg" -ForegroundColor Red
            $allOk = $false
        }
    }
}

# ===================================================================
# 5. Directories
# ===================================================================
Write-Host "5. Checking directories..." -ForegroundColor Yellow

$dirs = @("data", "data/ai_signals", "data/ai_analysis", "logs", "results")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "   * $dir" -ForegroundColor Green
    } else {
        Write-Host "   X $dir" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# 6. Main files
# ===================================================================
Write-Host "6. Checking main files..." -ForegroundColor Yellow

$files = @("main.py", "requirements.txt", "start_bot.ps1")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "   * $file" -ForegroundColor Green
    } else {
        Write-Host "   X $file" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# Summary
# ===================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allOk -and $missingConfigs.Count -eq 0) {
    Write-Host "* READY TO WORK!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To start the bot:" -ForegroundColor Yellow
    Write-Host "  .\start_bot.ps1" -ForegroundColor White
    Write-Host "or:" -ForegroundColor Yellow
    Write-Host "  python main.py" -ForegroundColor White
} elseif ($missingConfigs.Count -gt 0) {
    Write-Host "! CONFIGURATION NEEDED" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Need to create configuration files:" -ForegroundColor Yellow
    foreach ($cfg in $missingConfigs) {
        Write-Host "  -> $cfg" -ForegroundColor White
        Write-Host "    (copy $cfg.example and fill data)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "After configuration, start the bot:" -ForegroundColor Yellow
    Write-Host "  .\start_bot.ps1" -ForegroundColor White
} else {
    Write-Host "X PROBLEMS DETECTED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Recommendations:" -ForegroundColor Yellow
    Write-Host "  1. Run installer: .\install.ps1" -ForegroundColor White
    Write-Host "  2. Or reinstall: .\quick_install.ps1 --clean" -ForegroundColor White
    Write-Host "  3. See TROUBLESHOOTING.md for help" -ForegroundColor White
}

Write-Host ""

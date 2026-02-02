# ===================================================================
# BAZA Trading Bot - Automatic Installer
# ===================================================================
# This script automatically sets up the environment and installs dependencies
# ===================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BAZA Trading Bot - Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Functions for output
function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-SuccessMessage {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-InfoMessage {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Yellow
}

# ===================================================================
# 1. Check Python
# ===================================================================
Write-InfoMessage "Checking Python installation..."

try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "Python found: $pythonVersion"
        
        # Check Python version (need 3.9+)
        $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
        if ($versionMatch) {
            $majorVersion = [int]$Matches[1]
            $minorVersion = [int]$Matches[2]
            
            if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 9)) {
                Write-ErrorMessage "Python 3.9+ required. Current version: $pythonVersion"
                Write-InfoMessage "Download Python from https://www.python.org/downloads/"
                exit 1
            }
        }
    }
} catch {
    Write-ErrorMessage "Python not found!"
    Write-InfoMessage "Install Python 3.9+ from https://www.python.org/downloads/"
    Write-InfoMessage "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

Write-Host ""

# ===================================================================
# 2. Remove old virtual environment (if needed)
# ===================================================================
$venvPath = ".venv"

if (Test-Path $venvPath) {
    Write-InfoMessage "Found existing virtual environment..."
    $response = Read-Host "Recreate environment? (y/n) [recommended if you had errors]"
    
    if ($response -eq "y" -or $response -eq "Y") {
        Write-InfoMessage "Removing old environment..."
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-SuccessMessage "Old environment removed"
    }
}

Write-Host ""

# ===================================================================
# 3. Create virtual environment
# ===================================================================
if (-not (Test-Path $venvPath)) {
    Write-InfoMessage "Creating virtual environment..."
    
    try {
        python -m venv $venvPath
        if ($LASTEXITCODE -eq 0) {
            Write-SuccessMessage "Virtual environment created"
        } else {
            Write-ErrorMessage "Failed to create virtual environment"
            exit 1
        }
    } catch {
        Write-ErrorMessage "Error creating environment: $_"
        exit 1
    }
} else {
    Write-SuccessMessage "Using existing virtual environment"
}

Write-Host ""

# ===================================================================
# 4. Activate virtual environment
# ===================================================================
Write-InfoMessage "Activating virtual environment..."

$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-ErrorMessage "Activation script not found: $activateScript"
    exit 1
}

# Check execution policy
try {
    $executionPolicy = Get-ExecutionPolicy -Scope CurrentUser
    if ($executionPolicy -eq "Restricted" -or $executionPolicy -eq "AllSigned") {
        Write-InfoMessage "Setting execution policy..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Write-SuccessMessage "Execution policy configured"
    }
} catch {
    Write-ErrorMessage "Failed to set execution policy: $_"
    Write-InfoMessage "Try running PowerShell as Administrator"
    exit 1
}

try {
    & $activateScript
    Write-SuccessMessage "Virtual environment activated"
} catch {
    Write-ErrorMessage "Failed to activate environment: $_"
    Write-InfoMessage "Try running: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    exit 1
}

Write-Host ""

# ===================================================================
# 5. Update pip
# ===================================================================
Write-InfoMessage "Updating pip..."

try {
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "pip updated"
    } else {
        Write-ErrorMessage "Failed to update pip (continuing...)"
    }
} catch {
    Write-ErrorMessage "Error updating pip: $_"
}

Write-Host ""

# ===================================================================
# 6. Install dependencies
# ===================================================================
Write-InfoMessage "Installing dependencies from requirements.txt..."
Write-InfoMessage "This may take several minutes..."

if (-not (Test-Path "requirements.txt")) {
    Write-ErrorMessage "requirements.txt not found!"
    exit 1
}

try {
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "All dependencies installed successfully!"
    } else {
        Write-ErrorMessage "Error installing dependencies"
        Write-InfoMessage "Try manually: pip install -r requirements.txt"
        exit 1
    }
} catch {
    Write-ErrorMessage "Error installing dependencies: $_"
    exit 1
}

Write-Host ""

# ===================================================================
# 7. Check critical packages
# ===================================================================
Write-InfoMessage "Checking critical packages..."

$criticalPackages = @(
    "MetaTrader5",
    "pandas",
    "numpy",
    "pyyaml",
    "python-telegram-bot",
    "openai",
    "customtkinter"
)

$allInstalled = $true
foreach ($package in $criticalPackages) {
    try {
        pip show $package | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  * $package" -ForegroundColor Green
        } else {
            Write-Host "  X $package" -ForegroundColor Red
            $allInstalled = $false
        }
    } catch {
        Write-Host "  X $package" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""

if (-not $allInstalled) {
    Write-ErrorMessage "Not all critical packages are installed!"
    Write-InfoMessage "Try reinstalling: pip install -r requirements.txt --force-reinstall"
    exit 1
}

# ===================================================================
# 8. Check configuration files
# ===================================================================
Write-InfoMessage "Checking configuration files..."

$configFiles = @(
    @{Path="config/mt5.yaml.example"; Required=$false},
    @{Path="config/telegram.yaml.example"; Required=$false},
    @{Path="config/trading.yaml"; Required=$true},
    @{Path="config/instruments.yaml"; Required=$true}
)

$missingRequired = $false
foreach ($config in $configFiles) {
    if (Test-Path $config.Path) {
        Write-Host "  * $($config.Path)" -ForegroundColor Green
    } else {
        if ($config.Required) {
            Write-Host "  X $($config.Path) [REQUIRED]" -ForegroundColor Red
            $missingRequired = $true
        } else {
            Write-Host "  ! $($config.Path) [not critical]" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# ===================================================================
# 9. Create necessary directories
# ===================================================================
Write-InfoMessage "Creating necessary directories..."

$directories = @(
    "data",
    "data/ai_signals",
    "data/ai_analysis",
    "data/backtest",
    "data/screenshots",
    "logs",
    "results"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  * Created directory: $dir" -ForegroundColor Green
    }
}

Write-Host ""

# ===================================================================
# Completion
# ===================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($missingRequired) {
    Write-ErrorMessage "Warning! Required configuration files are missing"
    Write-InfoMessage "Configure settings before running the bot"
    Write-Host ""
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Configure files in 'config/' folder"
Write-Host "     - Copy .example files and fill with your data"
Write-Host "  2. To start the bot use: .\start_bot.ps1"
Write-Host "  3. Or run directly: python main.py"
Write-Host ""

Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  - Activate environment: .\.venv\Scripts\Activate.ps1"
Write-Host "  - Install package: pip install <name>"
Write-Host "  - Update dependencies: pip install -r requirements.txt --upgrade"
Write-Host ""

Write-SuccessMessage "Ready to work!"

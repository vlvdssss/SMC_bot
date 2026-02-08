# ===================================================================
# BAZA Trading Bot - Quick Install (one command)
# ===================================================================

Write-Host "Quick Install BAZA Trading Bot..." -ForegroundColor Cyan

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue

# Remove old environment if --clean
if ($args -contains "--clean") {
    Write-Host "Cleaning old environment..." -ForegroundColor Yellow
    Remove-Item -Path ".venv" -Recurse -Force -ErrorAction SilentlyContinue
}

# Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate
Write-Host "Activating environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Update pip
Write-Host "Updating pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "Installing dependencies (this will take a few minutes)..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Create directories
$dirs = @("data", "data/ai_signals", "data/ai_analysis", "logs", "results")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force -ErrorAction SilentlyContinue | Out-Null
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run bot: .\start_bot.ps1" -ForegroundColor Yellow
Write-Host "or: python main.py" -ForegroundColor Yellow

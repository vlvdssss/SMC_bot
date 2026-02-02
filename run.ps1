# BAZA Trading Bot - Run Script
# ===================================================================

Write-Host "Starting BAZA Trading Bot..." -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run installer first: .\install.ps1" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if python exists in venv
$pythonPath = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: Python not found in venv!" -ForegroundColor Red
    Write-Host "Reinstall environment: .\quick_install.ps1 --clean" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if main.py exists
if (-not (Test-Path "main.py")) {
    Write-Host "ERROR: main.py not found!" -ForegroundColor Red
    pause
    exit 1
}

# Run the bot
Write-Host "Starting bot..." -ForegroundColor Green
& $pythonPath main.py

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Bot stopped with errors!" -ForegroundColor Red
    pause
}

# Start BAZA Bot with clean environment
# This script ensures .env file is loaded correctly

Write-Host "Starting BAZA Trading Bot..." -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run installer first: .\install.ps1" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if activation script exists
$activateScript = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Host "ERROR: Activation script not found!" -ForegroundColor Red
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

# Clear any cached API key from environment
$env:OPENAI_API_KEY = $null

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $activateScript

# Run bot
Write-Host "Starting bot..." -ForegroundColor Green
python main.py

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Bot stopped with errors!" -ForegroundColor Red
    pause
}

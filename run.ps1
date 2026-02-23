# BAZA Trading Bot - Run Script
# ===================================================================

Write-Host "Starting BAZA Trading Bot..." -ForegroundColor Cyan

# Get script directory and change to it
$scriptPath = $PSScriptRoot
if ($scriptPath) {
    Set-Location $scriptPath
    Write-Host "Working directory: $scriptPath" -ForegroundColor Gray
}

# Check if venv exists (check both local and parent directory)
$pythonPath = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    # Try parent directory
    $pythonPath = "..\.venv\Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
        Write-Host "Run installer first: .\install.ps1" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Convert to absolute path
$pythonPath = Resolve-Path $pythonPath

# Check if main.py exists
if (-not (Test-Path "main.py")) {
    Write-Host "ERROR: main.py not found!" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
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

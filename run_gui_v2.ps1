# BAZA Trading Bot V2 GUI Launcher
# Quick launch script for the modern GUI

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host " BAZA Trading Bot V2 - Modern GUI     " -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if virtual environment exists
$VenvPath = "..\\.venv\\Scripts\\python.exe"
if (-not (Test-Path $VenvPath)) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup first." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Starting GUI V2..." -ForegroundColor Green
Write-Host ""

# Launch GUI
& $VenvPath "src\gui\app_v2.py"

Write-Host ""
Write-Host "GUI closed." -ForegroundColor Yellow
pause

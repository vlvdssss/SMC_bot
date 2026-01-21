# Start BAZA Bot with clean environment
# This script ensures .env file is loaded correctly

Write-Host "🚀 Starting BAZA Trading Bot..." -ForegroundColor Cyan
Write-Host ""

# Clear any cached API key from environment
$env:OPENAI_API_KEY = $null

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run bot
python main.py

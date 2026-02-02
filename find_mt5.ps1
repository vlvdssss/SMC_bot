# MT5 Path Finder - Find MetaTrader 5 installation
# ===================================================================

Write-Host "Searching for MetaTrader 5..." -ForegroundColor Cyan
Write-Host ""

$possiblePaths = @(
    "C:\Program Files\MetaTrader 5\terminal64.exe",
    "C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    "C:\Program Files\MetaTrader 5\terminal.exe",
    "C:\Program Files (x86)\MetaTrader 5\terminal.exe",
    "$env:LOCALAPPDATA\Programs\MetaTrader 5\terminal64.exe",
    "$env:APPDATA\MetaQuotes\Terminal\terminal64.exe"
)

$found = $false

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        Write-Host "FOUND: $path" -ForegroundColor Green
        Write-Host ""
        Write-Host "Copy this path to config/mt5.yaml:" -ForegroundColor Yellow
        Write-Host "path: `"$($path -replace '\\', '/')`"" -ForegroundColor White
        $found = $true
        break
    }
}

if (-not $found) {
    Write-Host "MetaTrader 5 not found in standard locations!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install MetaTrader 5 from:" -ForegroundColor Yellow
    Write-Host "https://www.metatrader5.com/en/download" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually find terminal64.exe and add path to config/mt5.yaml" -ForegroundColor Yellow
}

Write-Host ""
pause

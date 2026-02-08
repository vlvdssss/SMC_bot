# MT5 Path Finder - Find MetaTrader 5 installation and update config
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
$mt5Path = ""

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $mt5Path = $path -replace '\\', '/'
        Write-Host "FOUND: $path" -ForegroundColor Green
        Write-Host ""
        $found = $true
        break
    }
}

if ($found) {
    # Update config file
    $configPath = "config/mt5.yaml"
    
    if (Test-Path $configPath) {
        Write-Host "Updating $configPath..." -ForegroundColor Yellow
        
        try {
            # Read config
            $content = Get-Content $configPath -Raw
            
            # Update path
            if ($content -match 'path:\s*"[^"]*"') {
                $content = $content -replace 'path:\s*"[^"]*"', "path: `"$mt5Path`""
                Write-Host "Path updated in existing config" -ForegroundColor Green
            } elseif ($content -match 'path:\s*\S+') {
                $content = $content -replace 'path:\s*\S+', "path: `"$mt5Path`""
                Write-Host "Path updated in existing config" -ForegroundColor Green
            } else {
                # Add path if not exists
                $content = $content -replace '(connection:\s*\n)', "`$1    path: `"$mt5Path`"`n"
                Write-Host "Path added to config" -ForegroundColor Green
            }
            
            # Save config
            $content | Set-Content $configPath -NoNewline
            Write-Host ""
            Write-Host "Config updated successfully!" -ForegroundColor Green
            Write-Host "Path: $mt5Path" -ForegroundColor White
            
        } catch {
            Write-Host "Error updating config: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "Manually add this to config/mt5.yaml:" -ForegroundColor Yellow
            Write-Host "path: `"$mt5Path`"" -ForegroundColor White
        }
    } else {
        Write-Host "Config file not found: $configPath" -ForegroundColor Yellow
        Write-Host "Copy mt5.yaml.example to mt5.yaml first" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Then add this path:" -ForegroundColor Yellow
        Write-Host "path: `"$mt5Path`"" -ForegroundColor White
    }
} else {
    Write-Host "MetaTrader 5 not found in standard locations!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install MetaTrader 5 from:" -ForegroundColor Yellow
    Write-Host "https://www.metatrader5.com/en/download" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually find terminal64.exe and add path to config/mt5.yaml" -ForegroundColor Yellow
}

Write-Host ""
pause

# Create shortcut for BAZA Trading Bot
$projectRoot = Split-Path -Parent $PSScriptRoot
$target = Join-Path -Path $projectRoot -ChildPath "dist\BAZA_TradingBot.exe"

# Check if EXE exists
if (-not (Test-Path $target)) {
    Write-Host "ERROR: EXE file not found at: $target" -ForegroundColor Red
    Write-Host "Please build the EXE first: python build_exe.py" -ForegroundColor Yellow
    exit 1
}

$target = (Resolve-Path $target).ProviderPath
$desktop = [System.IO.Path]::Combine($env:USERPROFILE, 'Desktop')
$linkPath = [System.IO.Path]::Combine($desktop, 'BAZA Trading Bot.lnk')

# Create shortcut
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($linkPath)
$sc.TargetPath = $target
$sc.WorkingDirectory = $projectRoot
$sc.Description = 'BAZA Trading Bot - AI-Powered Forex Trading'
$sc.Save()

Write-Host "Success! Shortcut created on Desktop" -ForegroundColor Green
Write-Host "Location: $linkPath" -ForegroundColor Cyan

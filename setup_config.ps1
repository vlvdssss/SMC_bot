# Setup Configuration Files - Copy .example files
# ===================================================================

Write-Host "Setting up configuration files..." -ForegroundColor Cyan
Write-Host ""

$configs = @(
    @{Example="config/mt5.yaml.example"; Target="config/mt5.yaml"; Required=$true; Desc="MT5 connection"},
    @{Example="config/telegram.yaml.example"; Target="config/telegram.yaml"; Required=$true; Desc="Telegram bot"},
    @{Example="config/monitoring.yaml.example"; Target="config/monitoring.yaml"; Required=$false; Desc="Monitoring"}
)

$created = 0
$skipped = 0
$needSetup = @()

foreach ($cfg in $configs) {
    if (Test-Path $cfg.Target) {
        Write-Host "[SKIP] $($cfg.Target) - already exists" -ForegroundColor Yellow
        $skipped++
    } elseif (Test-Path $cfg.Example) {
        try {
            Copy-Item $cfg.Example $cfg.Target
            Write-Host "[OK] Created $($cfg.Target)" -ForegroundColor Green
            $created++
            if ($cfg.Required) {
                $needSetup += $cfg
            }
        } catch {
            Write-Host "[ERROR] Failed to create $($cfg.Target): $_" -ForegroundColor Red
        }
    } else {
        Write-Host "[WARN] Example not found: $($cfg.Example)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration Setup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Created: $created | Skipped: $skipped" -ForegroundColor White
Write-Host ""

if ($needSetup.Count -gt 0) {
    Write-Host "IMPORTANT: Edit these files with your data:" -ForegroundColor Yellow
    Write-Host ""
    foreach ($cfg in $needSetup) {
        Write-Host "  -> $($cfg.Target) - $($cfg.Desc)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "What to configure:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. config/mt5.yaml:" -ForegroundColor White
    Write-Host "   - login: Your MT5 login" -ForegroundColor Gray
    Write-Host "   - password: Your MT5 password" -ForegroundColor Gray
    Write-Host "   - server: Your broker server" -ForegroundColor Gray
    Write-Host "   - path: (auto-filled by find_mt5.ps1)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. config/telegram.yaml:" -ForegroundColor White
    Write-Host "   - bot_token: Get from @BotFather" -ForegroundColor Gray
    Write-Host "   - chat_id: Get from @userinfobot" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then run: .\find_mt5.ps1" -ForegroundColor Yellow
    Write-Host "To auto-configure MT5 path" -ForegroundColor Gray
} else {
    Write-Host "All config files ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Edit config files with your data" -ForegroundColor White
    Write-Host "2. Run: .\find_mt5.ps1" -ForegroundColor White
    Write-Host "3. Run: .\check_install.ps1" -ForegroundColor White
    Write-Host "4. Start bot: .\start_bot.ps1" -ForegroundColor White
}

Write-Host ""
pause

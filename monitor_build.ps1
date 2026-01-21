# Monitor EXE build progress
Write-Host "⏳ Monitoring EXE build..." -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date

while ($true) {
    Start-Sleep -Seconds 10
    
    $elapsed = (Get-Date) - $startTime
    $minutes = [math]::Floor($elapsed.TotalMinutes)
    $seconds = $elapsed.Seconds
    
    Write-Host "[${minutes}m ${seconds}s] Building..." -ForegroundColor Yellow
    
    # Check if EXE exists
    if (Test-Path "dist\BAZA_TradingBot.exe") {
        $exeSize = (Get-Item "dist\BAZA_TradingBot.exe").Length / 1MB
        Write-Host ""
        Write-Host "✅ BUILD COMPLETE!" -ForegroundColor Green
        Write-Host "📦 EXE Size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Cyan
        Write-Host "📁 Location: dist\BAZA_TradingBot.exe" -ForegroundColor Cyan
        break
    }
    
    # Safety timeout (15 minutes)
    if ($elapsed.TotalMinutes -gt 15) {
        Write-Host ""
        Write-Host "⏱️ Timeout reached (15 min)" -ForegroundColor Red
        break
    }
}

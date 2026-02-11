#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Исправить Git tracking для config файлов
.DESCRIPTION
    Удаляет config файлы из Git индекса (они останутся локально).
    После этого Git перестанет их трекать при pull.
    Запустите ОДИН РАЗ для исправления проблемы.
#>

Write-Host "`n╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Fix Git Tracking - Remove Config Files ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "⚠️  ВНИМАНИЕ!" -ForegroundColor Yellow
Write-Host "Этот скрипт удалит config файлы из Git, но оставит локально." -ForegroundColor White
Write-Host "После этого Git перестанет их трекать при pull." -ForegroundColor White
Write-Host "`nУдалятся из Git:" -ForegroundColor Yellow
Write-Host "  - config/trading.yaml" -ForegroundColor White
Write-Host "  - config/ai.yaml" -ForegroundColor White
Write-Host "  - config/portfolio.yaml" -ForegroundColor White
Write-Host "  - config/monitoring.yaml" -ForegroundColor White
Write-Host "  - data/ai_signals/*.json" -ForegroundColor White
Write-Host "`n❓ Продолжить? (Y/N): " -ForegroundColor Cyan -NoNewline

$response = Read-Host
if ($response -ne "Y" -and $response -ne "y") {
    Write-Host "Отменено." -ForegroundColor Yellow
    exit 0
}

Write-Host "`n🔧 Удаляю файлы из Git индекса..." -ForegroundColor Yellow

# Удалить из индекса, но оставить локально
$filesToUntrack = @(
    "config/trading.yaml",
    "config/ai.yaml",
    "config/portfolio.yaml",
    "config/monitoring.yaml",
    "data/ai_signals/active_signals.json",
    "data/ai_signals/*.json",
    "data/*.json"
)

foreach ($file in $filesToUntrack) {
    if (Test-Path $file -PathType Leaf) {
        Write-Host "  ➜ Untracking: $file" -ForegroundColor Gray
        git rm --cached $file 2>$null
    } elseif ($file -match '\*') {
        # Wildcard pattern
        Write-Host "  ➜ Untracking pattern: $file" -ForegroundColor Gray
        git rm --cached -r $file 2>$null
    }
}

Write-Host "`n✓ Файлы удалены из Git индекса" -ForegroundColor Green

Write-Host "`n📝 Коммит изменений..." -ForegroundColor Yellow
git add .gitignore
git commit -m "🔧 Remove config and data files from tracking

- Keep files locally but stop tracking changes
- Prevents conflicts on git pull
- Config files remain in .gitignore"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Коммит создан" -ForegroundColor Green
    
    Write-Host "`n📤 Отправить на GitHub? (Y/N): " -ForegroundColor Cyan -NoNewline
    $pushResponse = Read-Host
    
    if ($pushResponse -eq "Y" -or $pushResponse -eq "y") {
        Write-Host "`n📤 Отправка на GitHub..." -ForegroundColor Yellow
        git push
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Изменения отправлены" -ForegroundColor Green
        } else {
            Write-Host "❌ Ошибка при отправке" -ForegroundColor Red
            Write-Host "Попробуйте вручную: git push" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "⚠️  Нечего коммитить (возможно уже исправлено)" -ForegroundColor Yellow
}

Write-Host "`n╔═══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            Исправление готово! ✓          ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`nТеперь используйте для обновления:" -ForegroundColor Cyan
Write-Host "  .\update.ps1" -ForegroundColor White
Write-Host "`nИли обычный git pull без конфликтов!" -ForegroundColor White

Write-Host ""
pause

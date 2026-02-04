#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix git pull asking to commit configs
    
.DESCRIPTION
    Tells git to skip worktree (ignore local changes) for config files.
    После этого git pull НЕ будет пытаться перезаписать локальные конфиги.
#>

Write-Host "🔧 Fixing git config conflicts..." -ForegroundColor Cyan
Write-Host ""

# Конфигурационные файлы которые нужно игнорировать
$configFiles = @(
    "config/mt5.yaml",
    "config/telegram.yaml",
    "config/trading.yaml",
    "config/ai.yaml",
    "config/portfolio.yaml",
    "config/instruments.yaml",
    "config/monitoring.yaml",
    "config/mt5_credentials.enc"
)

Write-Host "Настройка git skip-worktree для конфигов..." -ForegroundColor Yellow

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        try {
            git update-index --skip-worktree $file
            Write-Host "✓ $file - локальные изменения будут игнорироваться" -ForegroundColor Green
        } catch {
            Write-Host "⚠ $file - ошибка: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "○ $file - файл не найден (пропуск)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "✅ Готово! Теперь git pull НЕ будет просить коммитить конфиги" -ForegroundColor Green
Write-Host ""
Write-Host "Что изменилось:" -ForegroundColor Cyan
Write-Host "  • Локальные изменения в конфигах НЕ видны для git" -ForegroundColor White
Write-Host "  • git pull НЕ перезапишет локальные настройки" -ForegroundColor White
Write-Host "  • Можно спокойно редактировать конфиги" -ForegroundColor White
Write-Host ""
Write-Host "Чтобы откатить (вернуть tracking):" -ForegroundColor Yellow
Write-Host "  git update-index --no-skip-worktree config/имя_файла.yaml" -ForegroundColor Gray
Write-Host ""
Write-Host "Чтобы посмотреть какие файлы skip-worktree:" -ForegroundColor Yellow
Write-Host "  git ls-files -v | Select-String '^S'" -ForegroundColor Gray
Write-Host ""

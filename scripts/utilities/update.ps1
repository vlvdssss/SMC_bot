#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Safe Git Pull Script - автоматически сохраняет и восстанавливает локальные изменения
.DESCRIPTION
    Этот скрипт безопасно обновляет репозиторий, сохраняя все локальные изменения:
    1. Сохраняет локальные изменения (git stash)
    2. Загружает обновления с GitHub (git pull)
    3. Восстанавливает локальные изменения (git stash pop)
#>

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   BAZA Trading Bot - Safe Update      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Проверка Git
$gitInstalled = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitInstalled) {
    Write-Host "❌ Git не установлен!" -ForegroundColor Red
    Write-Host "   Скачайте с https://git-scm.com/download/win" -ForegroundColor Yellow
    pause
    exit 1
}

# Проверка репозитория
if (-not (Test-Path ".git")) {
    Write-Host "❌ Не Git репозиторий!" -ForegroundColor Red
    Write-Host "   Запустите скрипт из корня проекта BAZA" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "📋 Проверка локальных изменений..." -ForegroundColor Yellow

# Проверить есть ли изменения
$status = git status --porcelain
if ($status) {
    Write-Host "✓ Найдены локальные изменения:" -ForegroundColor Green
    git status --short
    Write-Host "`n💾 Сохраняю локальные изменения..." -ForegroundColor Yellow
    git stash push -m "Auto stash before update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка при сохранении изменений!" -ForegroundColor Red
        pause
        exit 1
    }
    
    Write-Host "✓ Изменения сохранены в stash" -ForegroundColor Green
    $hasStash = $true
} else {
    Write-Host "✓ Нет локальных изменений" -ForegroundColor Green
    $hasStash = $false
}

Write-Host "`n📥 Загружаю обновления с GitHub..." -ForegroundColor Yellow
git pull --rebase

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Ошибка при обновлении!" -ForegroundColor Red
    
    if ($hasStash) {
        Write-Host "⚠️  Ваши изменения в stash, восстанавливаю..." -ForegroundColor Yellow
        git stash pop
    }
    
    Write-Host "`nВозможные причины:" -ForegroundColor Yellow
    Write-Host "  1. Нет интернета" -ForegroundColor White
    Write-Host "  2. Конфликт удалённых изменений" -ForegroundColor White
    Write-Host "  3. Проблемы с GitHub" -ForegroundColor White
    Write-Host "`nПопробуйте:" -ForegroundColor Cyan
    Write-Host "  git fetch origin" -ForegroundColor White
    Write-Host "  git reset --hard origin/main" -ForegroundColor White
    pause
    exit 1
}

Write-Host "✓ Обновления загружены" -ForegroundColor Green

# Восстановить изменения если были
if ($hasStash) {
    Write-Host "`n🔄 Восстанавливаю локальные изменения..." -ForegroundColor Yellow
    git stash pop
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n⚠️  Возможны конфликты при восстановлении!" -ForegroundColor Yellow
        Write-Host "Проверьте файлы вручную:" -ForegroundColor White
        git status
        Write-Host "`nДля отмены используйте:" -ForegroundColor Cyan
        Write-Host "  git checkout -- <файл>" -ForegroundColor White
    } else {
        Write-Host "✓ Изменения восстановлены" -ForegroundColor Green
    }
}

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        Обновление завершено! ✓         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Green

# Показать последние коммиты
Write-Host "📝 Последние обновления:" -ForegroundColor Cyan
git log --oneline --graph --decorate -5

Write-Host ""
pause

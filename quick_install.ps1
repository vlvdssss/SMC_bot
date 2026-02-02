# ===================================================================
# BAZA Trading Bot - Быстрая установка (одной командой)
# ===================================================================

Write-Host "Быстрая установка BAZA Trading Bot..." -ForegroundColor Cyan

# Проверка Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ОШИБКА: Python не найден!" -ForegroundColor Red
    Write-Host "Установите Python 3.9+ с https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Настройка политики выполнения
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue

# Удаление старого окружения при проблемах
if ($args -contains "--clean") {
    Write-Host "Очистка старого окружения..." -ForegroundColor Yellow
    Remove-Item -Path ".venv" -Recurse -Force -ErrorAction SilentlyContinue
}

# Создание venv
if (-not (Test-Path ".venv")) {
    Write-Host "Создание виртуального окружения..." -ForegroundColor Yellow
    python -m venv .venv
}

# Активация
Write-Host "Активация окружения..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Обновление pip
Write-Host "Обновление pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Установка зависимостей
Write-Host "Установка зависимостей (это займёт несколько минут)..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Создание директорий
$dirs = @("data", "data/ai_signals", "data/ai_analysis", "logs", "results")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force -ErrorAction SilentlyContinue | Out-Null
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "УСТАНОВКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Запуск бота: .\start_bot.ps1" -ForegroundColor Yellow
Write-Host "или: python main.py" -ForegroundColor Yellow

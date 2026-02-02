# ===================================================================
# BAZA Trading Bot - Проверка установки
# ===================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Проверка установки BAZA Trading Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# ===================================================================
# 1. Python
# ===================================================================
Write-Host "1. Проверка Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Python не найден" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "   ✗ Python не найден" -ForegroundColor Red
    $allOk = $false
}

# ===================================================================
# 2. Виртуальное окружение
# ===================================================================
Write-Host "2. Проверка виртуального окружения..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "   ✓ Виртуальное окружение найдено" -ForegroundColor Green
    
    # Проверка активации
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Host "   ✓ Скрипт активации найден" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Скрипт активации не найден" -ForegroundColor Red
        $allOk = $false
    }
} else {
    Write-Host "   ✗ Виртуальное окружение не найдено" -ForegroundColor Red
    Write-Host "   → Запустите: .\install.ps1" -ForegroundColor Yellow
    $allOk = $false
}

# Активация окружения для дальнейших проверок
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
}

# ===================================================================
# 3. Критические пакеты
# ===================================================================
Write-Host "3. Проверка критических пакетов..." -ForegroundColor Yellow

$packages = @{
    "MetaTrader5" = "Подключение к MT5"
    "pandas" = "Обработка данных"
    "numpy" = "Математические вычисления"
    "pyyaml" = "Конфигурация"
    "python-telegram-bot" = "Telegram уведомления"
    "openai" = "AI анализ"
    "customtkinter" = "Графический интерфейс"
    "lightgbm" = "Машинное обучение"
    "scikit-learn" = "ML модели"
    "matplotlib" = "Графики"
}

foreach ($pkg in $packages.Keys) {
    try {
        pip show $pkg 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ $pkg - $($packages[$pkg])" -ForegroundColor Green
        } else {
            Write-Host "   ✗ $pkg - $($packages[$pkg])" -ForegroundColor Red
            $allOk = $false
        }
    } catch {
        Write-Host "   ✗ $pkg - $($packages[$pkg])" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# 4. Конфигурационные файлы
# ===================================================================
Write-Host "4. Проверка конфигурации..." -ForegroundColor Yellow

$configs = @{
    "config/mt5.yaml" = "MT5 подключение (обязательно)"
    "config/telegram.yaml" = "Telegram бот (обязательно)"
    "config/ai.yaml" = "OpenAI API (обязательно)"
    "config/trading.yaml" = "Торговые настройки"
    "config/instruments.yaml" = "Инструменты"
    "config/portfolio.yaml" = "Портфель"
}

$missingConfigs = @()
foreach ($cfg in $configs.Keys) {
    if (Test-Path $cfg) {
        Write-Host "   ✓ $cfg" -ForegroundColor Green
    } else {
        $exampleFile = "$cfg.example"
        if (Test-Path $exampleFile) {
            Write-Host "   ⚠ $cfg (есть .example)" -ForegroundColor Yellow
            $missingConfigs += $cfg
        } else {
            Write-Host "   ✗ $cfg" -ForegroundColor Red
            $allOk = $false
        }
    }
}

# ===================================================================
# 5. Директории
# ===================================================================
Write-Host "5. Проверка директорий..." -ForegroundColor Yellow

$dirs = @("data", "data/ai_signals", "data/ai_analysis", "logs", "results")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "   ✓ $dir" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $dir" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# 6. Основные файлы
# ===================================================================
Write-Host "6. Проверка основных файлов..." -ForegroundColor Yellow

$files = @("main.py", "requirements.txt", "start_bot.ps1")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "   ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $file" -ForegroundColor Red
        $allOk = $false
    }
}

# ===================================================================
# Итоги
# ===================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allOk -and $missingConfigs.Count -eq 0) {
    Write-Host "✓ ВСЁ ГОТОВО К РАБОТЕ!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Для запуска бота:" -ForegroundColor Yellow
    Write-Host "  .\start_bot.ps1" -ForegroundColor White
    Write-Host "или:" -ForegroundColor Yellow
    Write-Host "  python main.py" -ForegroundColor White
} elseif ($missingConfigs.Count -gt 0) {
    Write-Host "⚠ ТРЕБУЕТСЯ НАСТРОЙКА" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Необходимо создать конфигурационные файлы:" -ForegroundColor Yellow
    foreach ($cfg in $missingConfigs) {
        Write-Host "  → $cfg" -ForegroundColor White
        Write-Host "    (скопируй $cfg.example и заполни данные)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "После настройки конфигурации запусти бота:" -ForegroundColor Yellow
    Write-Host "  .\start_bot.ps1" -ForegroundColor White
} else {
    Write-Host "✗ ОБНАРУЖЕНЫ ПРОБЛЕМЫ" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Рекомендации:" -ForegroundColor Yellow
    Write-Host "  1. Запусти установщик: .\install.ps1" -ForegroundColor White
    Write-Host "  2. Или переустанови: .\quick_install.ps1 --clean" -ForegroundColor White
    Write-Host "  3. См. TROUBLESHOOTING.md для помощи" -ForegroundColor White
}

Write-Host ""

# ===================================================================
# BAZA Trading Bot - Автоматический установщик
# ===================================================================
# Этот скрипт автоматически настраивает окружение и устанавливает зависимости
# ===================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BAZA Trading Bot - Установщик" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Функция для вывода ошибок
function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "[ОШИБКА] $Message" -ForegroundColor Red
}

# Функция для вывода успеха
function Write-SuccessMessage {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

# Функция для вывода информации
function Write-InfoMessage {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Yellow
}

# ===================================================================
# 1. Проверка Python
# ===================================================================
Write-InfoMessage "Проверка установки Python..."

try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "Python найден: $pythonVersion"
        
        # Проверка версии Python (нужен 3.9+)
        $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
        if ($versionMatch) {
            $majorVersion = [int]$Matches[1]
            $minorVersion = [int]$Matches[2]
            
            if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 9)) {
                Write-ErrorMessage "Требуется Python 3.9 или выше. Установленная версия: $pythonVersion"
                Write-InfoMessage "Скачайте Python с https://www.python.org/downloads/"
                exit 1
            }
        }
    }
} catch {
    Write-ErrorMessage "Python не найден!"
    Write-InfoMessage "Установите Python 3.9+ с https://www.python.org/downloads/"
    Write-InfoMessage "При установке обязательно отметьте 'Add Python to PATH'"
    exit 1
}

Write-Host ""

# ===================================================================
# 2. Удаление старого виртуального окружения (если есть проблемы)
# ===================================================================
$venvPath = ".venv"

if (Test-Path $venvPath) {
    Write-InfoMessage "Обнаружено существующее виртуальное окружение..."
    $response = Read-Host "Пересоздать окружение заново? (y/n) [рекомендуется при ошибках]"
    
    if ($response -eq "y" -or $response -eq "Y" -or $response -eq "д" -or $response -eq "Д") {
        Write-InfoMessage "Удаление старого окружения..."
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-SuccessMessage "Старое окружение удалено"
    }
}

Write-Host ""

# ===================================================================
# 3. Создание виртуального окружения
# ===================================================================
if (-not (Test-Path $venvPath)) {
    Write-InfoMessage "Создание виртуального окружения..."
    
    try {
        python -m venv $venvPath
        if ($LASTEXITCODE -eq 0) {
            Write-SuccessMessage "Виртуальное окружение создано"
        } else {
            Write-ErrorMessage "Не удалось создать виртуальное окружение"
            exit 1
        }
    } catch {
        Write-ErrorMessage "Ошибка при создании окружения: $_"
        exit 1
    }
} else {
    Write-SuccessMessage "Используется существующее виртуальное окружение"
}

Write-Host ""

# ===================================================================
# 4. Активация виртуального окружения
# ===================================================================
Write-InfoMessage "Активация виртуального окружения..."

$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-ErrorMessage "Скрипт активации не найден: $activateScript"
    exit 1
}

# Проверка политики выполнения скриптов
try {
    $executionPolicy = Get-ExecutionPolicy -Scope CurrentUser
    if ($executionPolicy -eq "Restricted" -or $executionPolicy -eq "AllSigned") {
        Write-InfoMessage "Настройка политики выполнения скриптов..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Write-SuccessMessage "Политика выполнения настроена"
    }
} catch {
    Write-ErrorMessage "Не удалось настроить политику выполнения: $_"
    Write-InfoMessage "Попробуйте запустить PowerShell от имени администратора"
    exit 1
}

try {
    & $activateScript
    Write-SuccessMessage "Виртуальное окружение активировано"
} catch {
    Write-ErrorMessage "Не удалось активировать окружение: $_"
    Write-InfoMessage "Попробуйте запустить: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    exit 1
}

Write-Host ""

# ===================================================================
# 5. Обновление pip
# ===================================================================
Write-InfoMessage "Обновление pip..."

try {
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "pip обновлён"
    } else {
        Write-ErrorMessage "Не удалось обновить pip (продолжаем...)"
    }
} catch {
    Write-ErrorMessage "Ошибка при обновлении pip: $_"
}

Write-Host ""

# ===================================================================
# 6. Установка зависимостей
# ===================================================================
Write-InfoMessage "Установка зависимостей из requirements.txt..."
Write-InfoMessage "Это может занять несколько минут..."

if (-not (Test-Path "requirements.txt")) {
    Write-ErrorMessage "Файл requirements.txt не найден!"
    exit 1
}

try {
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMessage "Все зависимости установлены успешно!"
    } else {
        Write-ErrorMessage "Ошибка при установке зависимостей"
        Write-InfoMessage "Попробуйте установить вручную: pip install -r requirements.txt"
        exit 1
    }
} catch {
    Write-ErrorMessage "Ошибка при установке зависимостей: $_"
    exit 1
}

Write-Host ""

# ===================================================================
# 7. Проверка установки критических пакетов
# ===================================================================
Write-InfoMessage "Проверка установки критических пакетов..."

$criticalPackages = @(
    "MetaTrader5",
    "pandas",
    "numpy",
    "pyyaml",
    "python-telegram-bot",
    "openai",
    "customtkinter"
)

$allInstalled = $true
foreach ($package in $criticalPackages) {
    try {
        pip show $package | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $package" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $package" -ForegroundColor Red
            $allInstalled = $false
        }
    } catch {
        Write-Host "  ✗ $package" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""

if (-not $allInstalled) {
    Write-ErrorMessage "Не все критические пакеты установлены!"
    Write-InfoMessage "Попробуйте переустановить: pip install -r requirements.txt --force-reinstall"
    exit 1
}

# ===================================================================
# 8. Проверка конфигурационных файлов
# ===================================================================
Write-InfoMessage "Проверка конфигурационных файлов..."

$configFiles = @(
    @{Path="config/mt5.yaml.example"; Required=$false},
    @{Path="config/telegram.yaml.example"; Required=$false},
    @{Path="config/trading.yaml"; Required=$true},
    @{Path="config/instruments.yaml"; Required=$true}
)

$missingRequired = $false
foreach ($config in $configFiles) {
    if (Test-Path $config.Path) {
        Write-Host "  ✓ $($config.Path)" -ForegroundColor Green
    } else {
        if ($config.Required) {
            Write-Host "  ✗ $($config.Path) [ОБЯЗАТЕЛЬНЫЙ]" -ForegroundColor Red
            $missingRequired = $true
        } else {
            Write-Host "  ⚠ $($config.Path) [не критично]" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# ===================================================================
# 9. Создание необходимых директорий
# ===================================================================
Write-InfoMessage "Создание необходимых директорий..."

$directories = @(
    "data",
    "data/ai_signals",
    "data/ai_analysis",
    "data/backtest",
    "data/screenshots",
    "logs",
    "results"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ Создана директория: $dir" -ForegroundColor Green
    }
}

Write-Host ""

# ===================================================================
# Завершение
# ===================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "УСТАНОВКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($missingRequired) {
    Write-ErrorMessage "Внимание! Отсутствуют обязательные конфигурационные файлы"
    Write-InfoMessage "Настройте конфигурацию перед запуском бота"
    Write-Host ""
}

Write-Host "Следующие шаги:" -ForegroundColor Yellow
Write-Host "  1. Настройте конфигурационные файлы в папке 'config/'"
Write-Host "     - Скопируйте .example файлы и заполните своими данными"
Write-Host "  2. Для запуска бота используйте: .\start_bot.ps1"
Write-Host "  3. Или запустите напрямую: python main.py"
Write-Host ""

Write-Host "Полезные команды:" -ForegroundColor Yellow
Write-Host "  - Активировать окружение: .\.venv\Scripts\Activate.ps1"
Write-Host "  - Установить пакет: pip install <название>"
Write-Host "  - Обновить зависимости: pip install -r requirements.txt --upgrade"
Write-Host ""

Write-SuccessMessage "Готово к работе! 🚀"

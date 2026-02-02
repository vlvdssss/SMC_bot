@echo off
chcp 65001 >nul
echo ========================================
echo BAZA Trading Bot - Установка
echo ========================================
echo.

REM Проверка PowerShell
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: PowerShell не найден!
    pause
    exit /b 1
)

REM Запуск PowerShell установщика
echo Запуск установщика...
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"

echo.
pause

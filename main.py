#!/usr/bin/env python3
"""
BAZA Trading Bot v3.0

Запуск GUI: python main.py
Запуск бэктеста: python main.py --backtest --year 2024
"""

import argparse
import sys
import warnings
import os
from pathlib import Path
from dotenv import load_dotenv

# Подавить устаревшее предупреждение pkg_resources от apscheduler
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*')

# Настройка UTF-8 для консоли (только если stdout доступен)
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

# Определить базовую директорию (для PyInstaller)
if getattr(sys, 'frozen', False):
    # Если запущено из EXE
    BASE_DIR = Path(sys.executable).parent
else:
    # Если запущено из Python
    BASE_DIR = Path(__file__).parent

# Создать необходимые директории рядом с EXE/скриптом
for folder in ['config', 'data', 'logs', 'models', 'results', 'data/ai_analysis', 'data/ai_signals', 'data/backtest', 'data/screenshots']:
    folder_path = BASE_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

# Сменить рабочую директорию на базовую
os.chdir(BASE_DIR)

# Инициализация конфигов (для EXE)
if getattr(sys, 'frozen', False):
    from src.core.startup import init_exe_environment
    init_exe_environment()

# Загружаем переменные окружения
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='BAZA Trading Bot')
    parser.add_argument('--backtest', action='store_true', help='Режим бэктеста')
    parser.add_argument('--year', type=int, default=2024, help='Год для бэктеста')
    
    args = parser.parse_args()
    
    if args.backtest:
        # Бэктест - полная реальная логика стратегии
        from src.backtest.portfolio_backtester import run_backtest
        run_backtest(args.year)
    else:
        # GUI приложение
        from src.gui.app import main as gui_main
        gui_main()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
BAZA Trading Bot v3.0

Запуск GUI: python main.py
Запуск бэктеста: python main.py --backtest --year 2024
"""

import argparse
import sys
from dotenv import load_dotenv

# Настройка UTF-8 для консоли
sys.stdout.reconfigure(encoding='utf-8')

# Загружаем переменные окружения
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='BAZA Trading Bot')
    parser.add_argument('--backtest', action='store_true', help='Режим бэктеста')
    parser.add_argument('--year', type=int, default=2024, help='Год для бэктеста')
    
    args = parser.parse_args()
    
    if args.backtest:
        # Бэктест
        from src.backtest.portfolio_backtester import run_backtest
        run_backtest(args.year)
    else:
        # GUI приложение
        from src.gui.app import main as gui_main
        gui_main()


if __name__ == '__main__':
    main()

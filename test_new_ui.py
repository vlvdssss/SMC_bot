#!/usr/bin/env python3
"""
Тестовый запуск нового UI
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.gui.app_new import main

if __name__ == '__main__':
    main()

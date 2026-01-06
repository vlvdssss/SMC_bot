"""
Integration tests for BAZA Trading Bot

Полный цикл интеграционных тестов от загрузки данных до выполнения торгов.
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

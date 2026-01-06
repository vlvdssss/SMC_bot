# Быстрый запуск тестов (Windows)

# Все тесты
.\.venv\Scripts\python.exe -m pytest

# С подробным выводом
.\.venv\Scripts\python.exe -m pytest -v

# С покрытием кода
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=html

# Конкретный файл
.\.venv\Scripts\python.exe -m pytest tests/test_risk_manager.py -v

# HTML отчет покрытия откроется в htmlcov/index.html

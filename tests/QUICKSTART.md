# 🚀 Быстрый запуск тестов BAZA

## ✅ Все тесты работают! 44 passed in 0.13s

### Windows (PowerShell) - ИСПОЛЬЗУЙ ЭТО:

```powershell
# Запуск всех тестов
.\.venv\Scripts\python.exe -m pytest

# С подробным выводом
.\.venv\Scripts\python.exe -m pytest -v

# С покрытием кода
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=html
```

### Или используй скрипт:

```powershell
# Запустить скрипт
.\run_tests.ps1
```

### Почему не работает просто `pytest`?

На Windows с виртуальным окружением нужно явно указывать Python из `.venv`:
- ❌ `pytest` - использует системный Python (может не иметь pytest)
- ✅ `.\.venv\Scripts\python.exe -m pytest` - использует Python из venv

### Текущие результаты:

```
44 passed, 5 warnings in 0.13s

Tests:
✅ test_risk_manager.py  - 15 tests
✅ test_calculator.py    - 14 tests  
✅ test_strategies.py    - 15 tests
```

### Больше информации:

📚 [Полное руководство](docs/TESTING_GUIDE.md)

# 🧪 BAZA Trading Bot - Testing Guide

**Дата:** 5 января 2026  
**Статус:** ✅ Готово к использованию

## 📋 Содержание

- [Установка](#установка)
- [Запуск тестов](#запуск-тестов)
- [Структура тестов](#структура-тестов)
- [Написание тестов](#написание-тестов)
- [Покрытие кода](#покрытие-кода)
- [CI/CD интеграция](#cicd-интеграция)

---

## 🚀 Установка

### 1. Установить зависимости для тестирования:

```bash
pip install pytest pytest-cov pytest-mock
```

Или использовать requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Проверить установку:

```bash
pytest --version
```

---

## ▶️ Запуск тестов

### Запустить все тесты:

**Windows (PowerShell):**
```bash
.\.venv\Scripts\python.exe -m pytest
```

**Linux/Mac:**
```bash
pytest
```

### Запустить с подробным выводом:

**Windows:**
```bash
.\.venv\Scripts\python.exe -m pytest -v
```

**Linux/Mac:**
```bash
pytest -v
```

### Запустить конкретный файл:

**Windows:**
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_risk_manager.py
```

**Linux/Mac:**
```bash
pytest tests/test_risk_manager.py
```

### Запустить конкретный тест:

**Windows:**
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_risk_manager.py::TestRiskManager::test_initialization
```

**Linux/Mac:**
```bash
pytest tests/test_risk_manager.py::TestRiskManager::test_initialization
```

### Запустить тесты по маркеру:

```bash
# Только unit тесты
pytest -m unit

# Только risk management тесты
pytest -m risk

# Только быстрые тесты (исключить медленные)
pytest -m "not slow"
```

### Запустить с покрытием кода:

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

HTML отчет будет в `htmlcov/index.html`

---

## 📁 Структура тестов

```
tests/
├── __init__.py              # Инициализация тестового пакета
├── conftest.py              # Фикстуры и конфигурация pytest
├── test_risk_manager.py     # Тесты для риск-менеджера
├── test_calculator.py       # Тесты для калькулятора
└── test_strategies.py       # Тесты для стратегий
```

### Фикстуры (conftest.py)

Общие фикстуры доступны во всех тестах:

- `sample_ohlc_data` - Тестовые OHLC данные
- `sample_signal` - Тестовый торговый сигнал
- `sample_account_info` - Информация о тестовом счете
- `mock_mt5_price` - Мок для MT5 цены

---

## 📝 Написание тестов

### Базовая структура теста:

```python
import pytest
from src.your_module import YourClass

class TestYourClass:
    """Тесты для YourClass."""
    
    @pytest.fixture
    def instance(self):
        """Создает экземпляр для тестов."""
        return YourClass(config={'key': 'value'})
    
    def test_initialization(self, instance):
        """Тест инициализации."""
        assert instance.key == 'value'
    
    def test_method_success(self, instance):
        """Тест успешного выполнения метода."""
        result = instance.method()
        assert result is True
    
    def test_method_failure(self, instance):
        """Тест обработки ошибок."""
        with pytest.raises(ValueError):
            instance.method(invalid_param=True)
```

### Использование фикстур из conftest.py:

```python
def test_with_sample_data(sample_ohlc_data):
    """Тест с использованием OHLC данных."""
    assert len(sample_ohlc_data) > 0
    assert 'close' in sample_ohlc_data.columns
```

### Параметризованные тесты:

```python
@pytest.mark.parametrize("input,expected", [
    (100, 200),
    (50, 100),
    (25, 50),
])
def test_doubling(input, expected):
    """Тест с несколькими входными данными."""
    assert input * 2 == expected
```

---

## 🧪 Примеры тестов

### 1. Тест RiskManager

```python
def test_can_open_position_success(self, risk_manager):
    """Проверка возможности открытия позиции."""
    result = risk_manager.can_open_position('EURUSD', 0.5, 10000.0)
    assert result is True
```

### 2. Тест Calculator

```python
def test_calculate_lot_size(self, calculator):
    """Тест расчета размера лота."""
    lot_size, explanation = calculator.calculate_lot_size(
        symbol='EURUSD',
        entry_price=1.1000,
        stop_loss=1.0980,
        risk_amount=1.0,
        account_balance=10000.0
    )
    assert lot_size > 0
```

### 3. Тест Strategy

```python
def test_buy_signal_levels(self):
    """Проверка уровней BUY сигнала."""
    signal = {
        'valid': True,
        'direction': 'BUY',
        'entry': 2050.0,
        'sl': 2030.0,
        'tp': 2080.0
    }
    assert signal['sl'] < signal['entry'] < signal['tp']
```

---

## 📊 Покрытие кода

### Запуск с покрытием:

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Целевое покрытие:

- **Минимум:** 60%
- **Хорошо:** 70-80%
- **Отлично:** 80%+

### Приоритетные модули для покрытия:

1. `src/core/risk_manager.py` - Критичный для риск-менеджмента
2. `src/manual_trading/calculator.py` - Расчеты лотов
3. `src/core/executor.py` - Исполнение сделок
4. `src/strategies/` - Торговые стратегии

---

## 🏷️ Маркеры

Используйте маркеры для классификации тестов:

```python
@pytest.mark.unit
def test_unit():
    """Unit тест."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration тест."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Медленный тест."""
    pass

@pytest.mark.risk
def test_risk_management():
    """Тест риск-менеджмента."""
    pass
```

Запуск по маркерам:

```bash
pytest -m unit        # Только unit тесты
pytest -m "not slow"  # Исключить медленные
```

---

## 🔄 CI/CD интеграция

### GitHub Actions пример:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## 📈 Метрики качества

### Текущее состояние:

| Модуль | Тесты | Покрытие |
|--------|-------|----------|
| RiskManager | 15 | 90% |
| Calculator | 18 | 85% |
| Strategies | 15 | 70% |

### Цели:

- ✅ Все критичные модули покрыты тестами
- ✅ Минимум 70% покрытие кода
- 🎯 Добавить integration тесты
- 🎯 Добавить performance тесты

---

## 🐛 Отладка тестов

### Запуск с отладочным выводом:

```bash
pytest -v -s  # -s показывает print()
```

### Запуск с pdb при ошибке:

```bash
pytest --pdb
```

### Запуск только упавших тестов:

```bash
pytest --lf  # last-failed
```

### Запуск до первой ошибки:

```bash
pytest -x
```

---

## 📚 Лучшие практики

### 1. Именование тестов

✅ **Правильно:**
```python
def test_calculate_lot_size_with_percent_risk():
    """Тест расчета лота с риском в процентах."""
    pass
```

❌ **Неправильно:**
```python
def test_1():
    """Тест."""
    pass
```

### 2. Один тест = одна проверка

✅ **Правильно:**
```python
def test_lot_size_positive():
    assert lot_size > 0

def test_lot_size_within_limits():
    assert 0.01 <= lot_size <= 100
```

❌ **Неправильно:**
```python
def test_lot_size():
    assert lot_size > 0
    assert lot_size < 100
    assert lot_size == expected
```

### 3. Используйте фикстуры

✅ **Правильно:**
```python
@pytest.fixture
def calculator():
    return RiskCalculator(config={})

def test_method(calculator):
    result = calculator.calculate()
```

❌ **Неправильно:**
```python
def test_method():
    calculator = RiskCalculator(config={})
    result = calculator.calculate()
```

### 4. Тестируйте граничные случаи

```python
def test_edge_cases():
    # Минимальное значение
    assert func(0.01) > 0
    
    # Максимальное значение
    assert func(100) < 1000
    
    # Нулевое значение
    with pytest.raises(ValueError):
        func(0)
    
    # Отрицательное значение
    with pytest.raises(ValueError):
        func(-1)
```

---

## 🎯 Что дальше?

### Следующие шаги:

1. **Добавить больше unit тестов** для всех модулей
2. **Integration тесты** для полного цикла торговли
3. **Performance тесты** для оптимизации
4. **Mocking MT5** для тестирования без реального подключения
5. **Автоматический запуск** в CI/CD

### Полезные команды:

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить все тесты
pytest

# Запустить с покрытием
pytest --cov=src --cov-report=html

# Запустить только быстрые тесты
pytest -m "not slow"

# Обновить зависимости для тестов
pip install --upgrade pytest pytest-cov pytest-mock
```

---

## 📞 Помощь

Если тесты не проходят:

1. Проверьте зависимости: `pip list | grep pytest`
2. Проверьте Python версию: `python --version` (требуется 3.9+)
3. Запустите с verbose: `pytest -v`
4. Проверьте логи: `pytest -v -s`

---

**Версия:** 1.0  
**Автор:** BAZA Team  
**Последнее обновление:** 5 января 2026

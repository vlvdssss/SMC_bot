# Тесты

## Описание

Папка для **тестов и прогонов** стратегий.

Здесь:
- Скрипты для запуска бэктестов
- Unit tests (если будут)
- Валидационные тесты
- Smoke tests

## Структура

```
tests/
├── backtests/
│   └── README.md       # Информация о бэктестах
└── README.md           # Этот файл
```

## Типы тестов

### 1. Бэктесты
Прогон стратегии на исторических данных:
```python
python tests/backtests/run_xauusd_2023.py
```

### 2. Unit tests (будущее)
Тестирование отдельных компонентов:
- Тест HTF анализа
- Тест детекции BOS
- Тест расчета SL/TP

### 3. Валидационные тесты
Проверка на известных данных:
- Smoke test на Q1 2023
- Валидация на коротком периоде

## Запуск бэктестов

Все бэктесты запускаются из корневой папки проекта:

```powershell
# Бэктест для XAUUSD на 2023 год
python tests/backtests/run_xauusd_2023.py

# Бэктест для US30 на Q1 2025
python tests/backtests/run_us30_q1_2025.py
```

## Результаты

Результаты бэктестов сохраняются в `results/<instrument>/<year>/`:
```
results/xauusd/2023/backtest_2023_12_17.csv
```

## Статус

- ⏳ backtests/ — скриптов нет
- ⏳ unit tests — не реализованы

## TODO

- [ ] Создать скрипты для бэктестов XAUUSD
- [ ] Создать скрипты для бэктестов US30
- [ ] Добавить валидационные тесты (smoke tests)
- [ ] Добавить unit tests для ключевых компонентов
- [ ] Настроить CI/CD (если нужно)

## Примеры

### Базовый бэктест

```python
# tests/backtests/run_xauusd_2023.py

from strategies.xauusd.strategy import XAUUSDStrategy
from mt5.data_loader import MT5DataLoader

def main():
    # Загрузить данные
    loader = MT5DataLoader()
    h1 = loader.load_date_range("XAUUSD", "H1", "2023-01-01", "2023-12-31")
    m15 = loader.load_date_range("XAUUSD", "M15", "2023-01-01", "2023-12-31")
    
    # Запустить стратегию
    strategy = XAUUSDStrategy()
    results = strategy.backtest(h1, m15)
    
    # Сохранить результаты
    results.to_csv("results/xauusd/2023/full_2023.csv")
    print(f"Backtest complete: {len(results)} trades")

if __name__ == "__main__":
    main()
```

## Рекомендации

1. **Начинайте с коротких периодов** (1 квартал)
2. **Проверяйте качество данных** перед бэктестом
3. **Сохраняйте все результаты** (даже неудачные)
4. **Документируйте параметры** бэктеста в названии файла

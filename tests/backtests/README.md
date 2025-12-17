# Бэктесты

## Описание

Скрипты для запуска бэктестов стратегий на исторических данных.

Каждый скрипт:
- Загружает данные из MT5 или CSV
- Запускает стратегию на данных
- Сохраняет результаты в `results/<instrument>/<year>/`
- Выводит метрики (WR, DD, PnL и т.д.)

## Структура

```
tests/backtests/
├── run_xauusd_2023.py      # Бэктест XAUUSD на 2023
├── run_xauusd_2024.py      # Бэктест XAUUSD на 2024
├── run_us30_2023.py        # Бэктест US30 на 2023
└── README.md               # Этот файл
```

## Шаблон бэктеста

```python
"""
Backtest: XAUUSD 2023

Прогон стратегии на всём 2023 году.
"""

from strategies.xauusd.strategy import XAUUSDStrategy
from mt5.data_loader import MT5DataLoader
import pandas as pd


def run_backtest():
    print("=" * 80)
    print("BACKTEST: XAUUSD 2023")
    print("=" * 80)
    
    # 1. Загрузить данные
    loader = MT5DataLoader()
    h1_data = loader.load_date_range("XAUUSD", "H1", "2023-01-01", "2023-12-31")
    m15_data = loader.load_date_range("XAUUSD", "M15", "2023-01-01", "2023-12-31")
    
    print(f"Загружено: {len(h1_data)} баров H1, {len(m15_data)} баров M15")
    
    # 2. Инициализировать стратегию
    strategy = XAUUSDStrategy()
    
    # 3. Запустить бэктест
    results = []
    balance = 100.0  # начальный баланс
    
    for i in range(len(h1_data)):
        # Получить данные до текущего момента
        h1_window = h1_data[:i+1]
        m15_window = m15_data[...соответствующий диапазон...]
        
        # Анализ стратегии
        signal = strategy.analyze(h1_window, m15_window)
        
        if signal['signal'] != 'NONE':
            # Симулировать сделку
            # ... логика симуляции ...
            results.append({
                'time': h1_data.iloc[i]['time'],
                'signal': signal['signal'],
                'entry': signal['entry'],
                'sl': signal['sl'],
                'tp': signal['tp'],
                # ... результат сделки ...
            })
    
    # 4. Сохранить результаты
    df_results = pd.DataFrame(results)
    output_path = "results/xauusd/2023/full_2023.csv"
    df_results.to_csv(output_path, index=False)
    
    # 5. Вывести метрики
    print(f"\nВсего сделок: {len(df_results)}")
    print(f"Финальный баланс: ${balance:.2f}")
    # ... другие метрики ...
    
    print(f"\nРезультаты сохранены: {output_path}")


if __name__ == "__main__":
    run_backtest()
```

## Параметры бэктеста

Для каждого бэктеста укажите:
- **Период**: Начальная и конечная дата
- **Инструмент**: XAUUSD, US30 и т.д.
- **Таймфреймы**: H1, M15, M5
- **Начальный баланс**: Обычно $100
- **Risk per trade**: Обычно 1.0R

## Запуск

```powershell
# Из корня проекта
python tests/backtests/run_xauusd_2023.py
```

## Статус

- ⏳ Скрипты не созданы

## TODO

- [ ] Создать run_xauusd_2023.py
- [ ] Создать run_xauusd_2024.py
- [ ] Создать run_us30_2023.py
- [ ] Добавить расчет метрик в скрипты
- [ ] Добавить прогресс бар (tqdm)
- [ ] Добавить экспорт equity curve

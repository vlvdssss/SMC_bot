# MT5 Integration

## Описание

Все компоненты, связанные с MetaTrader 5:
- Подключение к терминалу
- Загрузка исторических данных
- Получение котировок в реальном времени
- Исполнение ордеров (для live trading)

## Структура

```
mt5/
├── connector.py        # Подключение к MT5
├── data_loader.py      # Загрузка исторических данных
└── README.md           # Этот файл
```

## Компоненты

### connector.py
Управление подключением к MT5:
- Инициализация соединения
- Проверка статуса подключения
- Получение информации о символах
- Закрытие соединения

### data_loader.py
Загрузка данных для бэктеста и live trading:
- Исторические данные по символам
- Мульти-таймфрейм загрузка (H1, M15, M5)
- Кэширование данных
- Обработка ошибок MT5

## Использование

### Базовое подключение

```python
from mt5.connector import MT5Connector

connector = MT5Connector()
if connector.connect():
    print("Подключение успешно")
else:
    print("Ошибка подключения")
```

### Загрузка данных

```python
from mt5.data_loader import MT5DataLoader

loader = MT5DataLoader()
h1_data = loader.load_history("XAUUSD", "H1", bars=100)
m15_data = loader.load_history("XAUUSD", "M15", bars=400)
```

## Требования

- MetaTrader 5 должен быть установлен
- Python пакет `MetaTrader5` должен быть установлен
  ```powershell
  pip install MetaTrader5
  ```

## Статус

- ⏳ connector.py — не реализован
- ⏳ data_loader.py — не реализован

## TODO

- [ ] Реализовать MT5Connector с error handling
- [ ] Реализовать MT5DataLoader с кэшированием
- [ ] Добавить поддержку нескольких символов
- [ ] Добавить валидацию данных (пропуски, аномалии)
- [ ] Добавить экспорт в CSV для бэктеста

# BAZA Trading Bot - Архитектура 2.0

## Обзор

Полностью переработанная архитектура с централизованным управлением состоянием, MT5 и логированием.

## Архитектурные Компоненты

### 1. AppState (`src/core/app_state.py`)
Централизованное состояние приложения.

**Функции:**
- Хранение MT5 Manager
- Управление статусом MT5
- Статистика приложения
- Настройки
- Состояние бота

**Ключевые методы:**
```python
app_state = AppState()
app_state.update_mt5_status(connected, account_info)
app_state.can_execute_trades()  # Проверка готовности к торгам
```

### 2. MT5Manager (`src/core/mt5_manager.py`)
Единственный менеджер MT5 подключения.

**Функции:**
- Инициализация MT5
- Подключение к счету
- Мониторинг статуса
- Получение информации о счете

**Ключевые методы:**
```python
mt5_manager = MT5Manager()
mt5_manager.initialize(terminal_path)
mt5_manager.connect(login, password, server)
mt5_manager.is_connected()
```

### 3. Logger (`src/core/logger.py`)
Централизованная система логирования.

**Функции:**
- Логирование в файл и консоль
- GUI интеграция
- Автоматическая ротация логов

**Использование:**
```python
from src.core.logger import logger
logger.info("Message")
logger.error("Error message")
```

## GUI Архитектура

### Основные Изменения

#### 1. Кнопка MT5
- Расположена между "Ключ" и "Настройки"
- Открывает окно настроек MT5
- Показывает статус подключения

#### 2. Окно Настроек MT5
**Поля:**
- Login (числовой)
- Password (скрытый)
- Server
- Terminal Path (с кнопкой выбора файла)

**Кнопки:**
- Подключиться
- Переподключиться
- Закрыть

**Статус:**
- Реальное время обновления
- Показывает баланс и свободную маржу

#### 3. Централизованное Логирование
- Все логи пишутся в файл `logs/baza_YYYYMMDD.log`
- Отображаются в GUI
- Логируются все операции

## Безопасность и Валидация

### MT5 Подключение
- Один MT5Manager на приложение
- Проверка подключения перед сделками
- Cooldown между попытками подключения

### Ручная Торговля
- Блокировка при работе бота
- Проверка MT5 статуса
- Валидация всех параметров

### Логирование
- Все действия логируются
- Ошибки записываются в файл
- GUI показывает логи в реальном времени

## Интеграция Компонентов

### Инициализация
```python
# 1. AppState
app_state = AppState()

# 2. MT5 Manager
app_state.mt5_manager = MT5Manager()
app_state.mt5_manager.initialize()

# 3. GUI
app = BazaApp()
app.app_state = app_state
```

### Работа с MT5
```python
# Подключение
config = app_state.get_mt5_config()
success, message = app_state.mt5_manager.connect(
    config['login'], config['password'], config['server']
)

# Обновление статуса
app_state.update_mt5_status(success, account_info)
```

### Ручная Торговля
```python
# Проверка готовности
if app_state.can_execute_trades():
    # Выполнение сделки
    success, message = manual_controller.execute_trade()
```

## Файловая Структура

```
src/
├── core/
│   ├── app_state.py      # Централизованное состояние
│   ├── mt5_manager.py    # MT5 менеджер
│   └── logger.py         # Логгер
├── gui/
│   └── app.py           # GUI с новой архитектурой
└── manual_trading/      # Ручная торговля
```

## Конфигурация

### MT5 Настройки (`data/mt5_config.json`)
```json
{
  "login": 123456,
  "password": "password",
  "server": "Broker-Server",
  "terminal_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
}
```

### Portfolio Настройки (`config/portfolio.yaml`)
```yaml
manual_trading:
  enabled: true
  ai_predict_enabled: false
  min_rr_warning: 1.5
  max_risk_percent: 5.0
```

## Мониторинг и Логи

### Логи
- **Файл:** `logs/baza_YYYYMMDD.log`
- **Формат:** `HH:MM:SS [LEVEL] MODULE: MESSAGE`
- **Ротация:** 10MB, 5 файлов

### Мониторинг MT5
- Автоматическая проверка каждые 5 секунд
- Обновление GUI статуса
- Логирование подключений/отключений

## Безопасность

### MT5
- Валидация всех параметров подключения
- Защита от множественных подключений
- Корректное отключение при выходе

### GUI
- Блокировка ручной торговли при работе бота
- Проверка MT5 статуса перед сделками
- Валидация входных данных

## Тестирование

### Базовое Тестирование
```bash
# Тест архитектуры
python -c "from src.core.app_state import AppState; from src.core.mt5_manager import MT5Manager; print('OK')"

# Тест GUI
python -m src.gui.app
```

### Проверка MT5
1. Открыть окно MT5 настроек
2. Ввести корректные данные
3. Нажать "Подключиться"
4. Проверить статус в GUI

## Производственная Готовность

✅ **AppState** - централизованное состояние  
✅ **MT5Manager** - единый менеджер MT5  
✅ **Logger** - централизованное логирование  
✅ **GUI MT5 Button** - управление подключением  
✅ **MT5 Settings Window** - конфигурация  
✅ **Real-time Status** - мониторинг статуса  
✅ **Manual Trading Integration** - интеграция с ручной торговлей  
✅ **Security** - безопасность и валидация  
✅ **Logging** - полное логирование  

## Следующие Шаги

1. **Тестирование на реальном MT5**
2. **Интеграция с Live Trading**
3. **Добавление дополнительных метрик**
4. **UI улучшения**
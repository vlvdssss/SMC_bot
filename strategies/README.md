# Стратегии

## Описание

В этой папке хранится **ТОЛЬКО КОД СТРАТЕГИЙ** для каждого инструмента.

Каждый инструмент имеет свою отдельную стратегию, основанную на его уникальных характеристиках.

## Структура

```
strategies/
├── xauusd/
│   ├── strategy.py        # Стратегия для золота
│   ├── config.yaml        # Параметры стратегии XAUUSD
│   └── README.md          # Документация стратегии
├── us30/
│   ├── strategy.py        # Стратегия для Dow Jones (планируется)
│   ├── config.yaml        # Параметры стратегии US30
│   └── README.md          # Документация стратегии
└── README.md              # Этот файл
```

## Правила

### ✅ Что МОЖНО хранить здесь:
- Код стратегии (`strategy.py`)
- Конфигурация стратегии (`config.yaml`)
- Документация стратегии (`README.md`)
- Вспомогательные модули для стратегии (если нужны)

### ❌ Что НЕЛЬЗЯ хранить здесь:
- Эксперименты (они в `experiments/`)
- Гипотезы (они в `docs/05_experiments.md`)
- Результаты бэктестов (они в `results/`)
- Данные для бэктестинга
- Общую документацию (она в `docs/`)

## Добавление новой стратегии

Чтобы добавить стратегию для нового инструмента:

1. **Создать папку** с названием инструмента (маленькими буквами):
   ```
   strategies/eurusd/
   ```

2. **Создать файл `strategy.py`**:
   ```python
   class StrategyEURUSD:
       def __init__(self):
           self.instrument = "EURUSD"
           # ...
       
       def load_data(self, h1_data, m15_data):
           """Загрузка данных"""
           pass
       
       def build_context(self, current_h1_idx):
           """Анализ HTF"""
           pass
       
       def generate_signal(self, current_m15_idx, current_price):
           """Генерация сигнала LTF"""
           pass
   ```

3. **Создать файл `config.yaml`**:
   ```yaml
   instrument:
     symbol: "EURUSD"
     name: "Euro/US Dollar"
   
   timeframes:
     htf: "H4"
     ltf: "M15"
   
   # ... параметры стратегии
   ```

4. **Создать файл `README.md`** с описанием:
   - Торговая логика (концептуально)
   - Параметры
   - Производительность (если протестирована)
   - Статус (EXPERIMENTAL / TESTING / STABLE)

5. **Добавить документацию** в `docs/03_instruments.md`

## Текущие стратегии

### XAUUSD (Gold) - StrategyXAUUSD

**Статус:** ✅ STABLE (Phase 2 Baseline)

- **Версия:** Final v1.0
- **Дата миграции:** 17 декабря 2025
- **Файлы:**
  - [strategy.py](xauusd/strategy.py) — код стратегии
  - [config.yaml](xauusd/config.yaml) — параметры
  - [README.md](xauusd/README.md) — полная документация

**Производительность (2023-2025):**
- Avg Trades: 148/year
- Avg Win Rate: 60.76%
- Avg Max DD: 11.51%
- Avg ROI: +952%

**Источник:** `bobi_bot` Phase 2 Baseline (перенесена без изменений)

---

### US30 (Dow Jones) - StrategyUS30

**Статус:** ⏳ ПЛАНИРУЕТСЯ

- Стратегия в разработке
- Шаблон создан
- Торговая логика не реализована

---

## Принцип работы стратегии

Каждая стратегия должна иметь:

- **Класс стратегии** с методом `analyze()`
- **Входные данные**: H1 и M15 timeframes
- **Выходные данные**: Сигнал (BUY/SELL/NONE) с параметрами (entry, SL, TP)

Базовая структура:

```python
class InstrumentStrategy:
    def __init__(self):
        """Инициализация стратегии"""
        pass
    
    def analyze(self, h1_data, m15_data):
        """
        Анализ рынка по Smart Money Concepts
        
        Args:
            h1_data: DataFrame с H1 барами (HTF)
            m15_data: DataFrame с M15 барами (Setup/Trigger)
            
        Returns:
            dict: {'signal': 'BUY'/'SELL'/'NONE', 'entry': float, 'sl': float, 'tp': float}
        """
        pass
```

## Текущий статус

- **XAUUSD**: Структура создана, стратегия не реализована
- **US30**: Структура создана, стратегия не реализована

## Примечания

- Стратегии изолированы — код для XAUUSD не должен влиять на US30
- Каждая стратегия имеет свои параметры и логику
- Общие утилиты (если нужны) выносятся в отдельные модули

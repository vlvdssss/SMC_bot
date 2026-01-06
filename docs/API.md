# 📚 BAZA Trading Bot - API Documentation

**Версия:** 1.2.0  
**Дата:** 5 января 2026  
**Статус:** Production Ready

---

## 📋 Содержание

1. [Core Modules](#core-modules)
   - [AppState](#appstate)
   - [BotManager](#botmanager)
   - [RiskManager](#riskmanager)
   - [Executor](#executor)
   - [Logger](#logger)
   - [MT5Manager](#mt5manager)

2. [Strategies](#strategies)
   - [EURUSD Strategy](#eurusd-strategy)
   - [XAUUSD Strategy](#xauusd-strategy)

3. [Manual Trading](#manual-trading)
   - [RiskCalculator](#riskcalculator)
   - [Validator](#validator)
   - [AIAnalyzer](#aianalyzer)

4. [ML & AI](#ml--ai)
   - [TradePredictor](#tradepredictor)
   - [FeatureExtractor](#featureextractor)
   - [GPTNewsFilter](#gptnewsfilter)

5. [Backtest](#backtest)
   - [Backtester](#backtester)
   - [PortfolioBacktester](#portfoliobacktester)

6. [Examples](#examples)

---

## Core Modules

### AppState

**Путь:** `src/core/app_state.py`

Централизованное состояние приложения. Синглтон для управления глобальным состоянием.

#### Основные методы:

```python
from src.core.app_state import AppState

# Получить экземпляр (синглтон)
app_state = AppState()

# Обновить статус MT5
app_state.update_mt5_status(
    connected=True,
    account_info={'balance': 10000, 'equity': 10000}
)

# Проверить возможность торговли
can_trade = app_state.can_execute_trades()  # -> bool

# Получить MT5 Manager
mt5_manager = app_state.get_mt5_manager()

# Получить статус подключения
is_connected = app_state.is_mt5_connected()  # -> bool
```

#### Свойства:

| Свойство | Тип | Описание |
|----------|-----|----------|
| `mt5_connected` | `bool` | Статус подключения к MT5 |
| `mt5_account_info` | `dict` | Информация о счете |
| `bot_running` | `bool` | Статус работы бота |
| `stats` | `dict` | Статистика приложения |

---

### BotManager

**Путь:** `src/core/bot_manager.py`

Управление состоянием и логикой бота.

#### Инициализация:

```python
from src.core.bot_manager import BotManager, BotStatus

bot_manager = BotManager()
```

#### Основные методы:

```python
# Запуск бота
bot_manager.start()

# Остановка бота
bot_manager.stop()

# Пауза
bot_manager.pause()

# Получить статус
status = bot_manager.get_status()  # -> BotStatus

# Добавить лог
bot_manager.add_log("Trading signal detected", level="info")

# Получить логи
logs = bot_manager.get_logs(limit=100)  # -> List[dict]

# Добавить сделку
bot_manager.add_trade({
    'symbol': 'EURUSD',
    'direction': 'BUY',
    'profit': 100.0
})

# Получить статистику
stats = bot_manager.get_stats()  # -> dict
```

#### Статусы бота:

```python
BotStatus.STOPPED   # Бот остановлен
BotStatus.RUNNING   # Бот работает
BotStatus.PAUSED    # Бот на паузе
```

---

### RiskManager

**Путь:** `src/core/risk_manager.py`

Управление рисками портфеля.

#### Инициализация:

```python
from src.core.risk_manager import RiskManager

config = {
    'max_daily_loss_percent': 5.0,
    'max_open_positions': 4,
    'max_lot_size': 1.0,
    'max_daily_trades': 10
}

risk_manager = RiskManager(config)
```

#### Основные методы:

```python
# Проверка возможности открытия позиции
can_open = risk_manager.can_open_position(
    instrument='EURUSD',
    lot_size=0.5,
    account_balance=10000.0
)  # -> bool

# Валидация торгового сигнала
is_valid = risk_manager.validate_signal(
    signal={
        'direction': 'BUY',
        'sl': 2030.0,
        'tp': 2080.0,
        'risk_percent': 1.0,
        'instrument': 'XAUUSD'
    },
    current_price=2050.0,
    account_balance=10000.0
)  # -> bool

# Обновление дневной статистики
risk_manager.update_daily_stats(pnl=100.0)

# Уведомления о позициях
risk_manager.position_opened()
risk_manager.position_closed()
```

#### Конфигурация:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `max_daily_loss_percent` | `float` | 5.0 | Макс. дневной убыток (%) |
| `max_open_positions` | `int` | 4 | Макс. открытых позиций |
| `max_lot_size` | `float` | 1.0 | Макс. размер лота |
| `max_daily_trades` | `int` | 10 | Макс. сделок в день |

---

### Executor

**Путь:** `src/core/executor.py`

Исполнение торговых сигналов.

#### Инициализация:

```python
from src.core.executor import Executor

executor = Executor(app_state, live_mode=False)
```

#### Основные методы:

```python
# Исполнить сигнал
result = executor.execute_signal(
    symbol='EURUSD',
    signal={
        'valid': True,
        'direction': 'BUY',
        'entry': 1.1000,
        'sl': 1.0980,
        'tp': 1.1030,
        'lot_size': 0.1
    }
)  # -> bool

# Закрыть позицию
closed = executor.close_position(
    ticket=12345,
    symbol='EURUSD'
)  # -> bool
```

#### Параметры сигнала:

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `valid` | `bool` | ✅ | Валидность сигнала |
| `direction` | `str` | ✅ | 'BUY' или 'SELL' |
| `entry` | `float` | ✅ | Цена входа |
| `sl` | `float` | ✅ | Стоп-лосс |
| `tp` | `float` | ✅ | Тейк-профит |
| `lot_size` | `float` | ✅ | Размер лота |

---

### Logger

**Путь:** `src/core/logger.py`

Централизованная система логирования.

#### Использование:

```python
from src.core.logger import logger

# Уровни логирования
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
logger.debug("Отладочная информация")

# С дополнительными данными
logger.error("Trade execution failed", exc_info=True)  # С traceback
```

#### Конфигурация:

Логи записываются в:
- Файл: `logs/baza_YYYYMMDD.log`
- Консоль: с цветным выводом
- GUI: автоматически отображаются в интерфейсе

---

### MT5Manager

**Путь:** `src/core/mt5_manager.py`

Управление подключением к MetaTrader 5.

#### Инициализация:

```python
from src.core.mt5_manager import MT5Manager

mt5_manager = MT5Manager()
```

#### Основные методы:

```python
# Инициализация MT5
success = mt5_manager.initialize(
    terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe"
)  # -> bool

# Подключение к счету
connected = mt5_manager.connect(
    login=12345678,
    password="password",
    server="MetaQuotes-Demo"
)  # -> bool

# Проверка подключения
is_connected = mt5_manager.is_connected()  # -> bool

# Получение информации о счете
account_info = mt5_manager.get_account_info()  # -> dict

# Отключение
mt5_manager.shutdown()
```

#### Информация о счете:

```python
{
    'balance': 10000.0,
    'equity': 10000.0,
    'margin': 0.0,
    'free_margin': 10000.0,
    'margin_level': 0.0,
    'profit': 0.0,
    'currency': 'USD',
    'login': 12345678,
    'server': 'MetaQuotes-Demo'
}
```

---

## Strategies

### EURUSD Strategy

**Путь:** `src/strategies/eurusd_strategy.py`

SMC Retracement стратегия для EUR/USD.

#### Инициализация:

```python
from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement

strategy = StrategyEURUSD_SMC_Retracement()
```

#### Основные методы:

```python
# Загрузка данных
strategy.load_data(h1_data, m15_data)

# Построение контекста
strategy.build_context(h1_idx=50)

# Генерация сигнала
signal = strategy.generate_signal(
    m15_idx=200,
    analysis_price=1.1000,
    entry_price=1.1005,
    current_time=datetime.now()
)

# Проверка сигнала (для live торговли)
signal = strategy.check_signal(
    h1_data=h1_data,
    m15_data=m15_data,
    current_h1_idx=50,
    current_m15_idx=200
)
```

#### Структура сигнала:

```python
{
    'valid': True,
    'direction': 'BUY',  # или 'SELL'
    'entry': 1.1005,
    'sl': 1.0985,
    'tp': 1.1035,
    'lot_size': 0.1,
    'risk_reward': 1.5,
    'confidence': 'HIGH',  # HIGH, MEDIUM, LOW
    'context': {
        'trend': 'UP',
        'structure': 'BULLISH',
        'fvg_present': True
    }
}
```

---

### XAUUSD Strategy

**Путь:** `src/strategies/xauusd_strategy.py`

Стратегия для золота (XAU/USD).

#### Использование:

```python
from src.strategies.xauusd_strategy import StrategyXAUUSD

strategy = StrategyXAUUSD()
strategy.load_data(h1_data, m15_data)
strategy.build_context(h1_idx=50)

signal = strategy.generate_signal(
    m15_idx=200,
    analysis_price=2050.0,
    entry_price=2051.0
)
```

Интерфейс аналогичен EURUSD Strategy.

---

## Manual Trading

### RiskCalculator

**Путь:** `src/manual_trading/calculator.py`

Калькулятор риск-менеджмента для ручной торговли.

#### Инициализация:

```python
from src.manual_trading.calculator import RiskCalculator

config = {
    'PIP_VALUE': 0.0001,      # Для EURUSD
    'CONTRACT_SIZE': 100000
}

calculator = RiskCalculator(config)
```

#### Основные методы:

```python
# Расчет размера лота
lot_size, explanation = calculator.calculate_lot_size(
    symbol='EURUSD',
    entry_price=1.1000,
    stop_loss=1.0980,
    risk_amount=1.0,          # 1% или фиксированная сумма
    account_balance=10000.0
)

# Расчет Risk/Reward
rr_ratio = calculator.calculate_rr_ratio(
    entry_price=1.1000,
    stop_loss=1.0980,
    take_profit=1.1030,
    direction='BUY'
)  # -> 1.5

# Валидация параметров
is_valid, message = calculator.validate_risk_parameters(
    lot_size=0.5,
    risk_amount=100.0,
    account_balance=10000.0
)
```

#### Примеры для разных инструментов:

```python
# XAUUSD (Золото)
config_gold = {
    'PIP_VALUE': 0.01,
    'CONTRACT_SIZE': 100
}
calc_gold = RiskCalculator(config_gold)

# GBPUSD
config_gbp = {
    'PIP_VALUE': 0.0001,
    'CONTRACT_SIZE': 100000
}
calc_gbp = RiskCalculator(config_gbp)
```

---

### Validator

**Путь:** `src/manual_trading/validator.py`

Валидация параметров ручной торговли.

#### Использование:

```python
from src.manual_trading.validator import TradeValidator

validator = TradeValidator()

# Валидация сделки
is_valid, errors = validator.validate_trade(
    symbol='EURUSD',
    direction='BUY',
    entry=1.1000,
    stop_loss=1.0980,
    take_profit=1.1030,
    lot_size=0.1
)

if not is_valid:
    print(f"Validation errors: {errors}")
```

---

### AIAnalyzer

**Путь:** `src/manual_trading/ai_analyzer.py`

AI анализ торговых идей через GPT-4.

#### Использование:

```python
from src.manual_trading.ai_analyzer import AITradeAnalyzer

analyzer = AITradeAnalyzer()

# Анализ сделки
analysis = analyzer.analyze_trade(
    symbol='EURUSD',
    direction='BUY',
    entry=1.1000,
    stop_loss=1.0980,
    take_profit=1.1030,
    timeframe='H1'
)

print(analysis['recommendation'])  # BUY, SELL, HOLD
print(analysis['confidence'])       # HIGH, MEDIUM, LOW
print(analysis['reasoning'])        # Текстовое объяснение
```

---

## ML & AI

### TradePredictor

**Путь:** `src/ml/predictor.py`

ML модель для предсказания успеха сделки.

#### Инициализация:

```python
from src.ml.predictor import TradePredictor

predictor = TradePredictor(model_path='models/trade_predictor.pkl')
```

#### Основные методы:

```python
# Предсказание вероятности успеха
probability, confidence = predictor.predict_success(
    h1_data=h1_data,
    m15_data=m15_data,
    m15_idx=200,
    signal={
        'direction': 'BUY',
        'entry': 2050.0,
        'sl': 2030.0,
        'tp': 2080.0
    }
)  # -> (0.75, 'HIGH')

# Решение о сделке
should_take = predictor.should_take_trade(
    probability=0.75,
    min_probability=0.55
)  # -> bool

# Обучение модели
results = predictor.train(
    trades_data=trades_df,      # DataFrame со сделками
    features_data=features_df   # DataFrame с фичами
)

# Сохранение модели
predictor.save_model()

# Загрузка модели
predictor.load_model()
```

#### Формат данных для обучения:

```python
# trades_data
{
    'time': datetime,
    'instrument': str,
    'direction': str,
    'entry': float,
    'sl': float,
    'tp': float,
    'result': int  # 1 = win, 0 = loss
}

# features_data - извлекаются автоматически FeatureExtractor
```

---

### FeatureExtractor

**Путь:** `src/ml/features.py`

Извлечение фичей для ML модели.

#### Использование:

```python
from src.ml.features import FeatureExtractor

extractor = FeatureExtractor()

features = extractor.extract_features(
    h1_data=h1_data,
    m15_data=m15_data,
    m15_idx=200,
    signal={
        'direction': 'BUY',
        'entry': 2050.0,
        'sl': 2030.0,
        'tp': 2080.0
    }
)  # -> dict с ~30-50 фичами
```

#### Типы фичей:

- Ценовые индикаторы (EMA, RSI, MACD)
- Волатильность (ATR)
- Структура рынка (свинги, уровни)
- Параметры сигнала (RR, размер стопа)
- Временные паттерны

---

### GPTNewsFilter

**Путь:** `src/ai/news_filter.py`

Фильтр новостей через GPT для безопасности торговли.

#### Инициализация:

```python
from src.ai.news_filter import GPTNewsFilter

gpt_filter = GPTNewsFilter()
```

#### Основные методы:

```python
# Проверка безопасности торговли
safe, risk_level, reason = gpt_filter.check_trading_safety(
    instrument='EURUSD'
)

print(f"Safe to trade: {safe}")
print(f"Risk level: {risk_level}")  # HIGH, MEDIUM, LOW, UNKNOWN
print(f"Reason: {reason}")

# Проверка необходимости снижения риска
reduce, multiplier = gpt_filter.should_reduce_risk(
    instrument='XAUUSD'
)

if reduce:
    new_lot_size = original_lot * multiplier
```

#### Стоимость:

~$0.001 за запрос (GPT-4o-mini)

---

## Backtest

### Backtester

**Путь:** `src/backtest/backtester.py`

Бэктестинг торговой стратегии.

#### Использование:

```python
from src.backtest.simple_backtester import run_backtest

# Запуск бэктеста
results = run_backtest(year=2024)

print(f"Final Balance: ${results['final_balance']}")
print(f"ROI: {results['roi']}%")
print(f"Win Rate: {results['win_rate']}%")
print(f"Max Drawdown: {results['max_dd']}%")
```

#### Результаты:

```python
{
    'initial_balance': 10000.0,
    'final_balance': 12500.0,
    'total_profit': 2500.0,
    'roi': 25.0,
    'trades': 150,
    'wins': 90,
    'losses': 60,
    'win_rate': 60.0,
    'max_dd': -8.5,
    'max_dd_amount': -850.0,
    'sharpe_ratio': 1.8
}
```

---

### PortfolioBacktester

**Путь:** `src/backtest/portfolio_backtester.py`

Бэктест портфеля инструментов.

#### Использование:

```python
from src.backtest.portfolio_backtester import run_backtest

results = run_backtest(year=2024)

# Результаты по портфелю (EURUSD + XAUUSD)
```

---

## Examples

### Пример 1: Полный цикл торговли

```python
from src.core.app_state import AppState
from src.core.mt5_manager import MT5Manager
from src.core.risk_manager import RiskManager
from src.core.executor import Executor
from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement

# 1. Инициализация
app_state = AppState()
mt5_manager = MT5Manager()

# 2. Подключение к MT5
mt5_manager.initialize()
mt5_manager.connect(login=12345, password="pass", server="Demo")
app_state.update_mt5_status(True, mt5_manager.get_account_info())

# 3. Настройка риск-менеджмента
risk_config = {
    'max_daily_loss_percent': 5.0,
    'max_open_positions': 4,
    'max_lot_size': 1.0
}
risk_manager = RiskManager(risk_config)

# 4. Инициализация стратегии
strategy = StrategyEURUSD_SMC_Retracement()
strategy.load_data(h1_data, m15_data)

# 5. Получение сигнала
signal = strategy.check_signal(h1_data, m15_data, h1_idx, m15_idx)

# 6. Валидация риска
if signal['valid']:
    can_trade = risk_manager.validate_signal(
        signal, 
        current_price=1.1000,
        account_balance=10000.0
    )
    
    if can_trade:
        # 7. Исполнение
        executor = Executor(app_state, live_mode=True)
        success = executor.execute_signal('EURUSD', signal)
        
        if success:
            risk_manager.position_opened()
```

### Пример 2: Ручная торговля с калькулятором

```python
from src.manual_trading.calculator import RiskCalculator

# Инициализация
calc = RiskCalculator({'PIP_VALUE': 0.0001, 'CONTRACT_SIZE': 100000})

# Расчет лота
lot_size, explanation = calc.calculate_lot_size(
    symbol='EURUSD',
    entry_price=1.1000,
    stop_loss=1.0980,  # 20 пипсов
    risk_amount=1.0,    # 1%
    account_balance=10000.0
)

print(f"Lot Size: {lot_size}")
print(f"Explanation: {explanation}")

# Расчет RR
rr = calc.calculate_rr_ratio(
    entry_price=1.1000,
    stop_loss=1.0980,
    take_profit=1.1030,
    direction='BUY'
)

print(f"Risk/Reward: {rr}")  # 1.5
```

### Пример 3: ML предиктор

```python
from src.ml.predictor import TradePredictor

# Загрузка модели
predictor = TradePredictor()

# Предсказание
probability, confidence = predictor.predict_success(
    h1_data, m15_data, m15_idx, signal
)

print(f"Win Probability: {probability:.2%}")
print(f"Confidence: {confidence}")

# Решение
if predictor.should_take_trade(probability, min_probability=0.60):
    print("✅ Take the trade!")
else:
    print("❌ Skip this trade")
```

### Пример 4: GPT фильтр новостей

```python
from src.ai.news_filter import GPTNewsFilter

gpt = GPTNewsFilter()

# Проверка перед сделкой
safe, risk, reason = gpt.check_trading_safety('EURUSD')

if not safe:
    print(f"⚠️ Don't trade: {reason}")
else:
    print(f"✅ Safe to trade (Risk: {risk})")
    
    # Проверка необходимости снижения риска
    reduce, mult = gpt.should_reduce_risk('EURUSD')
    if reduce:
        adjusted_lot = original_lot * mult
        print(f"Reduce lot size by {(1-mult)*100}%")
```

---

## 📝 Заметки

### Соглашения:

- Все цены в формате `float`
- Направления: `'BUY'` или `'SELL'`
- Таймфреймы: `'M15'`, `'H1'`, `'H4'`, `'D1'`
- Риск: в процентах (1.0 = 1%) или долларах

### Безопасность:

- Всегда валидируйте сигналы через `RiskManager`
- Используйте `Validator` для ручной торговли
- Включайте `GPTNewsFilter` перед важными сделками

### Best Practices:

1. Инициализируйте `AppState` в начале
2. Всегда проверяйте `app_state.can_execute_trades()` перед сделками
3. Используйте `Logger` для всех операций
4. Обрабатывайте исключения правильно
5. Тестируйте на demo перед live

---

**Версия документации:** 1.0  
**Последнее обновление:** 5 января 2026  
**Поддержка:** [GitHub Issues](https://github.com/yourusername/baza-bot/issues)

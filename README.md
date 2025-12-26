# 🤖 BAZA Trading Bot

Автоматическая торговая система на основе Smart Money Concepts (SMC).

---

## 📊 Результаты бэктеста (2024)

| Инструмент | ROI | Max Drawdown | Win Rate | Сделок |
|------------|-----|--------------|----------|--------|
| XAUUSD (Золото) | +45.86% | 16.27% | ~45% | 315 |
| EURUSD | +340.75% | 5.32% | 72% | 189 |

---

## 📁 Структура проекта
```
BAZA/
├── main.py              # 🚀 ГЛАВНЫЙ ФАЙЛ - запуск бота
├── requirements.txt     # 📦 Зависимости Python
├── README.md           # 📖 Эта документация
│
├── config/             # ⚙️ Настройки
│   ├── mt5.yaml.example    # Пример конфига MT5
│   ├── instruments.yaml    # Параметры инструментов
│   └── portfolio.yaml      # Настройки портфеля
│
├── src/                # 💻 Исходный код
│   ├── strategies/         # Торговые стратегии
│   │   ├── xauusd_strategy.py  # Стратегия для золота
│   │   └── eurusd_strategy.py  # Стратегия для EUR/USD
│   │
│   ├── core/              # Ядро системы
│   │   ├── broker_sim.py      # Симулятор брокера
│   │   ├── executor.py        # Исполнение ордеров
│   │   └── data_loader.py     # Загрузка данных
│   │
│   ├── mt5/               # Интеграция с MetaTrader 5
│   │   └── connector.py       # Подключение к MT5
│   │
│   ├── backtest/          # Бэктестирование
│   │   ├── backtester.py      # Реалистичный бэктестер
│   │   └── metrics.py         # Расчёт метрик
│   │
│   └── live/              # Live торговля
│       └── live_trader.py     # Трейдер реального времени
│
├── data/               # 📈 Данные (не в Git)
│   └── backtest/           # CSV файлы для бэктеста
│
├── results/            # 📋 Результаты (не в Git)
│
└── logs/               # 📝 Логи (не в Git)
 Быстрый старт
1. Установка
bashgit clone https://github.com/YOUR_USERNAME/BAZA.git
cd BAZA
pip install -r requirements.txt
2. Настройка MT5
bash# Создай свой конфиг
cp config/mt5.yaml.example config/mt5.yaml

# Отредактируй config/mt5.yaml - укажи свои данные:
# - login: твой логин MT5
# - password: твой пароль
# - server: сервер брокера
3. Запуск
bash# Демо режим (только мониторинг, без реальных сделок)
python main.py --mode demo

# Бэктест за 2024 год
python main.py --mode backtest --year 2024

# Бэктест только XAUUSD
python main.py --mode backtest --year 2024 --instrument xauusd

# Live торговля (осторожно!)
python main.py --mode live
```

---

## ⚙️ Настройки

### config/instruments.yaml

Параметры для каждого инструмента:
- `risk_per_trade` - риск на сделку (%)
- `max_trades_per_day` - макс. сделок в день
- `spread_points` - спред в пунктах

### config/portfolio.yaml

Настройки портфеля:
- `max_total_exposure` - макс. общий риск
- `instruments` - активные инструменты

---

## 📈 Стратегии

### XAUUSD (Золото)
- **Логика**: BOS (Break of Structure) + Order Blocks + Premium/Discount зоны
- **Таймфреймы**: H1 (тренд) + M15 (вход)
- **Risk**: 0.75% на сделку
- **RR**: 1:2

### EURUSD
- **Логика**: SMC Retracement в Order Blocks
- **Таймфреймы**: H1 (тренд) + M15 (вход)
- **Risk**: 0.5% на сделку
- **RR**: 1:2

---

## ⚠️ Важно

1. **Сначала тестируй на демо!** Минимум 1-2 месяца
2. **Не рискуй больше чем можешь потерять**
3. **Прошлые результаты не гарантируют будущих**

---

## 🔧 Требования

- Python 3.9+
- MetaTrader 5
- Windows (для MT5) или Linux + Wine

---

## 📝 Лицензия

MIT License - используй как хочешь, но на свой риск.

---

## 👨‍💻 Автор

Создано с помощью 4 месяцев работы и тестирования.
Отредактировать `config/instruments.yaml`:

```yaml
GBPUSD:
  name: "GBP/USD"
  type: "Forex"
  contract_size: 100000
  pip_value: 10.0
  spread: 1.8
  risk_per_trade: 0.5
  price_decimals: 5
```

### Шаг 2: Создать стратегию
Создать файл `strategies/gbpusd_strategy.py` с классом `StrategyGBPUSD`.

### Шаг 3: Обновить портфель
Добавить в `config/portfolio.yaml`:

```yaml
instruments:
  - XAUUSD
  - EURUSD
  - GBPUSD  # новый
```

### Шаг 4: Запустить
```bash
python BAZA/bot.py --mode backtest --start 2024-01-01 --end 2024-12-31
```

**ВСЁ**. Никаких изменений в core коде не требуется.

---

## Режимы работы

### 1. Backtest Mode
```bash
python BAZA/bot.py --mode backtest --start 2023-01-01 --end 2023-12-31
```

### 2. Demo Mode (будущее)
```bash
python BAZA/bot.py --mode demo --mt5-config mt5_demo.ini
```

### 3. Live Mode (будущее)
```bash
python BAZA/bot.py --mode live --mt5-config mt5_live.ini
```

---

## Текущий статус

✅ **Backtest validated (2023-2025)**
- XAUUSD Phase 2 Baseline: WR 60.8%, DD 11.5%, ROI +952%
- EURUSD SMC Retracement: WR 70.7%, DD 5.4%, ROI +324%
- Portfolio (XAUUSD + EURUSD): WR 66.65%, DD 7.62%, ROI +2,382%

⏳ **Pending**: MT5 integration for demo/live trading

---

## Конфигурация портфеля

### Risk Model (по умолчанию)
```
XAUUSD: 0.75% risk per trade
EURUSD: 0.5% risk per trade
Max Total Exposure: 1.25%
```

### Allocation (рекомендуемое)
```
70% capital → EURUSD (stable anchor)
30% capital → XAUUSD (aggressive growth)
```

---

## Важные файлы baseline (НЕ ТРОГАТЬ)

Оригинальные протестированные стратегии:
- `../strategies/xauusd/strategy.py` - XAUUSD Phase 2 Baseline
- `../strategies/eurusd/strategy.py` - EURUSD SMC Retracement v1.0

Результаты:
- `../results/xauusd/` - Backtest результаты XAUUSD
- `../results/eurusd/` - Backtest результаты EURUSD
- `../results/portfolio/` - Portfolio backtests

Документация:
- `../PORTFOLIO_vs_SINGLE_COMPARISON_2023-2025.md` - Полный анализ
- `../PORTFOLIO_VERDICT_2024.md` - Детальный отчёт 2024

---

## Разработка

### Правила
1. ❌ НЕ менять логику в `strategies/` без тестирования
2. ✅ Добавлять новые инструменты через config
3. ✅ Расширять core только если действительно нужно
4. ✅ Документировать все изменения

### Testing
```bash
# Backtest single instrument
python BAZA/bot.py --mode backtest --instrument xauusd --start 2024-01-01 --end 2024-12-31

# Backtest portfolio
python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31
```

---

## Changelog

**v1.0 (Dec 19, 2025)**
- ✅ Initial structure created
- ✅ Core modules ported from backtest
- ✅ XAUUSD + EURUSD strategies integrated
- ✅ Portfolio manager implemented
- ✅ Modular config system
- ⏳ MT5 integration pending

---

**NOTE**: Все baseline стратегии FROZEN до получения demo результатов.

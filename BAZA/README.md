# BAZA - Production Trading Bot

## Назначение

**BAZA** - это production-ready торговый бот, основанный на протестированных baseline стратегиях.

Все стратегии FROZEN и перенесены из backtest environment без изменений в логике.

---

## Структура

```
BAZA/
├── bot.py                      # Главный файл запуска бота
├── portfolio_manager.py        # Управление портфелем (multi-instrument)
├── README.md                   # Этот файл
│
├── core/                       # Ядро системы (модульное)
│   ├── __init__.py
│   ├── broker_sim.py          # Симулятор брокера (или реальная интеграция)
│   ├── executor.py            # Управление позициями
│   ├── data_loader.py         # Загрузка данных (backtest или live)
│   └── risk_manager.py        # Управление рисками портфеля
│
├── strategies/                 # FROZEN стратегии (копии из baseline)
│   ├── __init__.py
│   ├── xauusd_strategy.py     # XAUUSD Phase 2 Baseline
│   └── eurusd_strategy.py     # EURUSD SMC Retracement
│
└── config/                     # Конфигурация инструментов
    ├── __init__.py
    ├── instruments.yaml        # Спецификации всех инструментов
    └── portfolio.yaml          # Настройки портфеля
```

---

## Принципы

1. **МОДУЛЬНОСТЬ**: Легко добавить новый инструмент без изменения core
2. **FROZEN STRATEGIES**: Логика стратегий НЕ изменяется
3. **РАСШИРЯЕМОСТЬ**: Новые инструменты добавляются через config
4. **SINGLE RESPONSIBILITY**: Каждый модуль отвечает за одну задачу

---

## Как добавить новый инструмент

### Шаг 1: Добавить спецификацию
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

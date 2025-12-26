# SMC-framework - Project Structure

## Обзор

Проект разделён на две основные части:

1. **Root (baseline testing)** - Тестовая среда для backtest и анализа
2. **BAZA/** - Production-ready бот с модульной архитектурой

---

## 📁 Структура проекта

```
SMC-framework/
│
├── BAZA/                           # 🔥 PRODUCTION BOT (новое)
│   ├── bot.py                      # Главный файл запуска
│   ├── portfolio_manager.py        # Менеджер портфеля
│   ├── core/                       # Ядро системы
│   │   ├── broker_sim.py          # Симулятор брокера
│   │   ├── executor.py            # Управление позициями
│   │   └── data_loader.py         # Загрузка данных
│   ├── strategies/                 # FROZEN стратегии
│   │   ├── xauusd_strategy.py     # XAUUSD Phase 2
│   │   └── eurusd_strategy.py     # EURUSD SMC Retracement
│   └── config/                     # Конфигурации
│       ├── instruments.yaml        # Спецификации инструментов
│       └── portfolio.yaml          # Настройки портфеля
│
├── strategies/                     # ⚠️ BASELINE (НЕ ТРОГАТЬ)
│   ├── xauusd/
│   │   ├── strategy.py            # XAUUSD Phase 2 Baseline v1.0 FROZEN
│   │   ├── config.yaml
│   │   └── README.md
│   └── eurusd/
│       ├── strategy.py            # EURUSD SMC Retracement v1.0 FROZEN
│       ├── config.yaml
│       └── README.md
│
├── results/                        # ⚠️ BACKTEST RESULTS (НЕ ТРОГАТЬ)
│   ├── xauusd/{2023,2024,2025}/   # XAUUSD baseline results
│   ├── eurusd/{2023,2024,2025}/   # EURUSD baseline results
│   └── portfolio/{2023,2024,2025}/ # Portfolio backtest results
│
├── data/                           # Historical data
│   └── backtest/
│       ├── XAUUSD_H1_*.csv
│       ├── XAUUSD_M15_*.csv
│       ├── EURUSD_H1_*.csv
│       └── EURUSD_M15_*.csv
│
├── docs/                           # Documentation
│   ├── 01_overview.md
│   ├── 02_architecture.md
│   └── ...
│
├── logging/                        # Logging system
│
├── mt5/                            # MT5 integration (future)
│   ├── connector.py
│   └── data_loader.py
│
├── tests/                          # Tests
│
├── run_backtest.py                 # ⚠️ Original single backtest runner
├── run_portfolio_backtest.py      # ⚠️ Original portfolio backtest runner
├── broker_sim.py                   # ⚠️ Original broker simulator
├── executor.py                     # ⚠️ Original executor
├── data_loader.py                  # ⚠️ Original data loader
│
├── PORTFOLIO_vs_SINGLE_COMPARISON_2023-2025.md  # ⚠️ Full 3-year analysis
├── PORTFOLIO_VERDICT_2024.md                     # ⚠️ 2024 detailed report
├── EURUSD_BASELINE_VERDICT.md                    # ⚠️ EURUSD analysis
│
└── README.md                       # Main project README
```

---

## 🔴 КРИТИЧЕСКИ: Что НЕ ТРОГАТЬ

### 1. Baseline Strategies (FROZEN)
```
strategies/xauusd/strategy.py      ❌ НЕ МЕНЯТЬ
strategies/eurusd/strategy.py      ❌ НЕ МЕНЯТЬ
```

**Причина**: Протестированы 3 года (2023-2025), логика подтверждена.

### 2. Backtest Results
```
results/xauusd/                    ❌ НЕ УДАЛЯТЬ
results/eurusd/                    ❌ НЕ УДАЛЯТЬ
results/portfolio/                 ❌ НЕ УДАЛЯТЬ
```

**Причина**: Исторические результаты для сравнения и валидации.

### 3. Analysis Reports
```
PORTFOLIO_vs_SINGLE_COMPARISON_2023-2025.md  ❌ НЕ УДАЛЯТЬ
PORTFOLIO_VERDICT_2024.md                     ❌ НЕ УДАЛЯТЬ
EURUSD_BASELINE_VERDICT.md                    ❌ НЕ УДАЛЯТЬ
```

**Причина**: Полный анализ baseline производительности.

---

## ✅ Что можно менять

### 1. BAZA/ (Production Bot)
```
BAZA/                              ✅ МОЖНО РАЗВИВАТЬ
```

**Разрешено**:
- Добавлять новые инструменты через config
- Улучшать portfolio_manager.py
- Добавлять MT5 integration
- Расширять core модули (если нужно)

### 2. Config Files
```
BAZA/config/instruments.yaml       ✅ МОЖНО РЕДАКТИРОВАТЬ
BAZA/config/portfolio.yaml         ✅ МОЖНО РЕДАКТИРОВАТЬ
```

**Для добавления нового инструмента**:
1. Добавить в `instruments.yaml`
2. Создать стратегию в `BAZA/strategies/`
3. Добавить в `portfolio.yaml`

---

## 🚀 Как использовать BAZA

### Запуск portfolio backtest
```bash
python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31 --balance 100
```

### Запуск single instrument backtest
```bash
python BAZA/bot.py --mode backtest --instrument xauusd --start 2024-01-01 --end 2024-12-31 --balance 100
```

### Demo trading (будущее)
```bash
python BAZA/bot.py --mode demo --mt5-config config/mt5_demo.ini
```

---

## 📊 Baseline Performance (НЕ МЕНЯТЬ)

### XAUUSD Phase 2 Baseline
- **Win Rate**: 60.8%
- **Max DD**: 11.5%
- **ROI**: +952% (3-year avg)
- **Status**: ✅ FROZEN

### EURUSD SMC Retracement
- **Win Rate**: 70.7%
- **Max DD**: 5.4%
- **ROI**: +324% (3-year avg)
- **Status**: ✅ FROZEN

### Portfolio (XAUUSD + EURUSD)
- **Win Rate**: 66.65%
- **Max DD**: 7.62%
- **ROI**: +2,382% (3-year avg)
- **Status**: ✅ FROZEN

**Verdict**: Portfolio approved for demo trading.

---

## 🔧 Добавление нового инструмента

### Пример: GBPUSD

#### Шаг 1: Спецификация
Добавить в `BAZA/config/instruments.yaml`:

```yaml
GBPUSD:
  name: "British Pound/US Dollar"
  type: "Forex"
  enabled: true
  contract_size: 100000
  pip_value: 10.0
  spread_points: 2.0
  spread_multiplier: 0.0001
  price_decimals: 5
  risk_per_trade: 0.5
  strategy_class: "StrategyGBPUSD"
```

#### Шаг 2: Стратегия
Создать `BAZA/strategies/gbpusd_strategy.py`:

```python
class StrategyGBPUSD:
    def __init__(self):
        # YOUR STRATEGY LOGIC
        pass
    
    def load_data(self, h1_data, m15_data):
        # LOAD DATA
        pass
    
    def generate_signal(self, ...):
        # SIGNAL GENERATION
        pass
```

#### Шаг 3: Портфель
Добавить в `BAZA/config/portfolio.yaml`:

```yaml
portfolio:
  instruments:
    - XAUUSD
    - EURUSD
    - GBPUSD  # новый
```

#### Шаг 4: Обновить imports
В `BAZA/strategies/__init__.py`:

```python
from .gbpusd_strategy import StrategyGBPUSD
__all__ = [..., 'StrategyGBPUSD']
```

#### Шаг 5: Запустить
```bash
python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31
```

**ВСЁ**. Никаких изменений в core коде.

---

## 📝 Changelog

### v1.0 (Dec 19, 2025)
- ✅ BAZA production structure created
- ✅ Modular architecture implemented
- ✅ XAUUSD + EURUSD strategies integrated
- ✅ Portfolio manager with risk management
- ✅ Config-based instrument management
- ✅ Full documentation
- ⏳ MT5 integration pending

---

## 🎯 Next Steps

1. **Demo Trading**: Интеграция с MT5 для demo торговли
2. **Monitoring**: Dashboard для real-time мониторинга
3. **Alerts**: Telegram/Email уведомления
4. **Risk Manager**: Расширенное управление рисками
5. **New Instruments**: Добавление GBPUSD, USDJPY и др.

---

## ⚠️ ВАЖНО

**Перед любыми изменениями в baseline стратегиях - СПРОСИ!**

Все изменения в `strategies/xauusd/` и `strategies/eurusd/` должны быть протестированы и задокументированы.

BAZA создана как расширяемая база. Добавляй новые инструменты через конфигурацию, не меняя core логику.

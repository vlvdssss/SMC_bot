# SMC-framework

Production-ready торговый фреймворк на основе Smart Money Concepts (SMC).

## 🎯 Портфель (Production)

| Инструмент | Risk | WR | DD | ROI (3 года) | Статус |
|------------|------|----|----|--------------|--------|
| **XAUUSD** | 0.75% | 60.8% | 11.5% | +952% | ✅ FROZEN |
| **EURUSD** | 0.5% | 70.7% | 5.4% | +324% | ✅ FROZEN |

**Total exposure**: 1.25%  
**Backtest period**: 2023-2025 (3 года)

## 📁 Структура проекта

```
SMC-framework/
├── BAZA/                   # 🚀 Production система (backtest + demo modes)
│   ├── bot.py              # Главный entry point
│   ├── live_trader.py      # Real-time signal monitoring
│   ├── portfolio_manager.py # Multi-instrument execution
│   ├── core/               # Backtesting engine
│   ├── strategies/         # XAUUSD + EURUSD (frozen copies)
│   └── config/             # MT5, instruments, portfolio settings
│
├── strategies/             # 💎 Baseline стратегии (FROZEN)
│   ├── xauusd/             # XAUUSD Trend Following
│   └── eurusd/             # EURUSD Pullback/Retracement
│
├── run_backtest.py         # Backtest runner (single instrument)
├── run_portfolio_backtest.py # Portfolio backtest runner
│
├── data/backtest/          # Исторические данные (MT5)
├── results/                # Результаты backtests по годам
├── mt5/                    # MT5 connector
├── docs/                   # Документация + архив
└── experiments/            # 🧪 Archived experiments
    ├── gbpusd_rejected/    # GBPUSD Mean Reversion + Retracement (FAIL)
    └── market_screening/   # Multi-instrument screening (incomplete)
```

## 🚀 Режимы работы

### 1. Backtest Mode
```bash
# Single instrument
python run_backtest.py --instrument xauusd --start 2023-01-01 --end 2025-12-17

# Portfolio
python run_portfolio_backtest.py --start 2023-01-01 --end 2025-12-17
```

### 2. Demo Mode (MT5)
```bash
# BAZA system
cd BAZA
python bot.py --mode demo
```

## 📊 Результаты

**XAUUSD** (Trend Following):
- Trades/year: 148
- Win Rate: 60.8%
- Max DD: 11.5%
- ROI: +317% (avg/year)

**EURUSD** (Pullback):
- Trades/year: 176
- Win Rate: 70.7%
- Max DD: 5.4%
- ROI: +108% (avg/year)

**Portfolio** (XAUUSD 0.75% + EURUSD 0.5%):
- Total exposure: 1.25%
- Stable growth
- Diversification через разные approaches

## ✅ Production Ready

- ✅ 2 baseline стратегии (FROZEN)
- ✅ 3 года backtest validation
- ✅ BAZA system (backtest + demo modes)
- ✅ MT5 integration (full connector)
- ✅ Portfolio management
- ✅ Real-time monitoring
## 📖 Документация

- `docs/` - Полная документация фреймворка
- `docs/decisions/` - Важные решения и verdicts
- `docs/archive/` - Архив старых документов

## 🧪 Experiments (Archived)

**GBPUSD** - REJECTED:
- Mean Reversion: 0 trades
- SMC Retracement: 0 trades  
- Verdict: Инструмент исключён

**Market Screening** - INCOMPLETE:
- 6 инструментов (USDCHF, EURGBP, NZDUSD, USDJPY, AUDCAD, XAGUSD)
- Результаты: слабые сигналы, медленный backtest
- Архивировано для future reference

---

**Baseline**: XAUUSD + EURUSD (FROZEN)  
**Status**: Production Ready  
**Next**: Live trading на demo счёте
- [03. Инструменты](docs/03_instruments.md)
- [04. Стратегии](docs/04_strategies.md)
- [05. Эксперименты](docs/05_experiments.md)
- [06. Результаты](docs/06_results.md)
✅
- [x] Создание структуры проекта
- [x] Документация
- [x] Backtesting framework
- [x] Логирование

### Фаза 2: XAUUSD Baseline ✅
- [x] Перенос стратегии Phase 2 Baseline
- [x] Бэктест на 2023-2025
- [x] Validation (результаты совпадают с baseline)
- [ ] MT5 интеграция
- [ ] Demo trading

### Фаза 3: US30 Baseline 🟡
- [x] Создание новой стратегии (Continuation)
- [ ] ПодготForex Pairs 🔄
- [ ] Выбор валютных пар (EUR/USD, GBP/USD)
- [ ] Подготовка данных (H1, M15)
- [ ] Разработка baseline стратегий
- [ ] Backtest 2023-2025
- [ ] Оценка и выбор лучшей пары
- [ ] MT5 live trading
- [ ] Multi-instrument portfolio
- [ ] Advanced risk management
- [ ] Monitoring dashboarduction
- [ ] Demo trading
- [ ] Risk management
- [ ] Monitoring

## Контакты

Проект: SMC-framework

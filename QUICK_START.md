# Quick Start Guide

## 🚀 Быстрый запуск

### 1. Backtest (Single Instrument)

```bash
# XAUUSD
python run_backtest.py --instrument xauusd --start 2023-01-01 --end 2025-12-17 --balance 10000

# EURUSD
python run_backtest.py --instrument eurusd --start 2023-01-01 --end 2025-12-17 --balance 10000
```

### 2. Portfolio Backtest

```bash
python run_portfolio_backtest.py --start 2023-01-01 --end 2025-12-17
```

### 3. Demo Mode (MT5)

```bash
cd BAZA
python bot.py --mode demo
```

---

## 📁 Важные файлы

- `README.md` - Главное описание проекта
- `PROJECT_STATUS.md` - Текущий статус проекта
- `BAZA/README.md` - Документация BAZA системы
- `BAZA/DEMO_STATUS.md` - Статус demo mode

---

## 🎯 Baseline Strategies

**XAUUSD** (Trend Following):
- Risk: 0.75% per trade
- WR: 60.8%
- ROI: +952% (3 года)

**EURUSD** (Pullback):
- Risk: 0.5% per trade
- WR: 70.7%
- ROI: +324% (3 года)

---

## 📊 Структура результатов

```
results/
├── xauusd/
│   ├── 2023/
│   ├── 2024/
│   └── 2025/
└── eurusd/
    ├── 2023/
    ├── 2024/
    └── 2025/
```

Каждый год содержит:
- `trades.csv` - Все сделки
- `metrics.json` - Финальные метрики

---

## 🔧 Конфигурация

### MT5 Settings
`BAZA/config/mt5.yaml` - Параметры подключения к MT5

### Instruments
`BAZA/config/instruments.yaml` - Настройки инструментов

### Portfolio
`BAZA/config/portfolio.yaml` - Портфельное распределение

---

## ⚠️ Важно

- ✅ Baseline стратегии **FROZEN** - не менять
- ✅ Используй `experiments/` для новых идей
- ✅ Все изменения тестируй отдельно

---

**Ready to go!** 🚀

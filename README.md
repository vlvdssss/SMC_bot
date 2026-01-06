# BAZA Trading Bot 🤖

Автоматический торговый бот для MetaTrader 5 с AI-аналитикой и Smart Money Concept стратегией.

## 🚀 Быстрый старт

1. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

2. **Настройка MT5:**
- Скопировать `config/mt5.yaml.example` → `config/mt5.yaml`
- Заполнить credentials для MT5

3. **Запуск бота:**
```bash
python main.py
```

## 📂 Структура проекта

```
BAZA/
├── main.py                 # 🎯 Основной запуск бота (GUI)
├── requirements.txt        # Зависимости Python
├── README.md              # Документация
│
├── config/                # ⚙️ Конфигурация
│   ├── mt5.yaml          # MT5 credentials
│   ├── instruments.yaml  # Настройки XAUUSD
│   ├── portfolio.yaml    # Параметры портфолио
│   └── ai.yaml           # OpenAI API settings
│
├── scripts/              # 🛠️ Утилиты
│   ├── run_backtest.py  # Backtest запуск
│   ├── dashboard.py     # Streamlit dashboard
│   └── setup.py         # Установка dev mode
│
├── src/                  # 📦 Исходный код
│   ├── strategies/      # Торговые стратегии
│   ├── gui/             # GUI интерфейс
│   ├── backtest/        # Backtesting система
│   ├── live/            # Live trading
│   ├── ml/              # Machine Learning
│   └── core/            # Ядро системы
│
├── data/                 # 💾 Данные
│   ├── trades_history.json
│   ├── bot_stats.json
│   └── backtest/        # Исторические данные
│
├── results/              # 📊 Результаты backtests
├── logs/                 # 📝 Логи
└── docs/                 # 📚 Документация
    └── archive/         # Старые .md файлы
```

## 🎯 Возможности

- **Автоматическая торговля** XAUUSD (Gold) с SMC стратегией
- **Manual Trading Panel** с AI-аналитиком
- **Backtesting** на исторических данных
- **Risk Management** с автоматическим расчетом лотов
- **AI News Analysis** с OpenAI GPT-4
- **Real-time Dashboard** для мониторинга

## 🛠️ Утилиты

### Backtest
```bash
python scripts/run_backtest.py
```

### Dashboard
```bash
streamlit run scripts/dashboard.py
```

### Dev Install
```bash
pip install -e scripts/
```

## 📊 Стратегия: XAUUSD Phase 2 v1.1

- **Win Rate:** 52.6%
- **ROI (2024):** +243%
- **Max Drawdown:** 9.43%
- **Risk per trade:** 2%
- **Max trades/day:** 3

**Логика:**
- Smart Money Concept (SMC)
- Supply & Demand Zones
- Order Block Detection
- Premium/Discount Zones
- News Filter Integration

## 🔒 Безопасность

- MT5 credentials хранятся в `config/mt5.yaml` (не в git)
- API keys в `.env` файле (не в git)
- Encrypted credentials поддерживается

## 📝 Лицензия

Free version - лицензионная система удалена.

## 🤝 Контрибуция

См. `docs/archive/CONTRIBUTING.md`

---
**Made with ❤️ for automated trading**

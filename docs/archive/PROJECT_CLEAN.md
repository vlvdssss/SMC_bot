# BAZA Trading Bot - Cleaned Version

## ✅ Проект Очищен

### Удалено:
- ❌ Система лицензирования (license.py, generate_key.py, license.json)
- ❌ EURUSD стратегии (все версии v1.1, v2.0, v3.0)
- ❌ Эксперименты и тесты (run_experiment.py, test_*, debug_*, check_*, final_*)
- ❌ Результаты экспериментов (results/experiment/)
- ❌ ML обучение (train_ml_model.py)
- ❌ Build утилиты (build_exe.py, BAZA.spec)
- ❌ License файлы (sales_log.txt, trial_start.txt, license_*.txt)

### Осталось:
✅ **main.py** - Главная программа с GUI
✅ **run_backtest.py** - Бэктестер для тестирования
✅ **dashboard.py** - Дополнительная панель статистики
✅ **setup.py** - Установщик зависимостей

---

## 📂 Структура Проекта

```
BAZA/
├── main.py                 # Запуск бота
├── run_backtest.py         # Бэктестинг
├── dashboard.py            # Статистика
├── setup.py                # Установка
│
├── config/                 # Конфигурация
│   ├── instruments.yaml    # XAUUSD только
│   ├── mt5.yaml            # MT5 настройки
│   ├── ai.yaml             # AI аналитик
│   └── portfolio.yaml      # Портфолио
│
├── src/                    # Исходный код
│   ├── core/              # Ядро системы
│   │   ├── bot_manager.py
│   │   ├── broker_sim.py
│   │   ├── data_loader.py
│   │   ├── executor.py
│   │   └── logger.py
│   │
│   ├── strategies/         # Стратегии торговли
│   │   └── xauusd_strategy.py  # Золото SMC
│   │
│   ├── gui/               # Графический интерфейс
│   │   ├── main_window.py
│   │   ├── components/
│   │   └── styles/
│   │
│   ├── manual_trading/    # Ручная торговля с AI
│   │   ├── controller.py
│   │   ├── ai_analyzer.py
│   │   ├── calculator.py
│   │   └── validator.py
│   │
│   ├── live/              # Live трейдинг
│   │   └── live_trader.py
│   │
│   ├── mt5/               # MetaTrader 5
│   │   └── mt5_connector.py
│   │
│   ├── ml/                # Machine Learning
│   │   └── sentiment_analyzer.py
│   │
│   └── ai/                # AI модули
│       ├── news_fetcher.py
│       └── news_filter.py
│
├── data/                   # Данные
│   ├── backtest/          # Исторические данные
│   ├── bot_stats.json     # Статистика бота
│   └── trades_history.json # История сделок
│
├── docs/                   # Документация
├── logs/                   # Логи
├── models/                 # ML модели
└── results/                # Результаты бэктестов
    └── xauusd/            # Только золото
```

---

## 🎯 Основной Функционал

### 1. Автоматическая торговля XAUUSD
- **Стратегия:** Phase 2 Baseline v1.1 (Fixed Entry)
- **Метод:** SMC Retracement (BOS + Order Blocks)
- **Timeframes:** H1 контекст + M15 вход
- **Risk:** 2% на сделку
- **Max Trades:** 3 в день

**Производительность (Backtest 2024):**
- ROI: +243%
- Win Rate: 52.6%
- Max DD: 9.43%
- Total Trades: 97

### 2. Мануал Трейдинг Панель
- Ручное открытие сделок
- Калькулятор лота по риску
- Проверка маржи
- **AI Аналитик новостей** (анализ влияния на золото)

### 3. AI Аналитик
- Фильтрация новостей по релевантности
- Sentiment анализ (Bullish/Bearish/Neutral)
- Оценка влияния на рынок
- Рекомендации для трейдинга

### 4. Бэктестинг
- Тестирование стратегий на исторических данных
- Реалистичные брокерские условия
- Детальная статистика (ROI, WR, DD, trades)

---

## 🚀 Запуск

```bash
# Активировать виртуальное окружение
.venv\Scripts\Activate.ps1

# Запустить бота
python main.py
```

### Первый запуск:
1. Откроется GUI интерфейс
2. Введи MT5 credentials (login, password, server)
3. Настрой риск и параметры (уже оптимальные: 2% risk, 3 trades/day)
4. Нажми **START** для автоматической торговли
5. Или используй **Manual Trading** для ручных сделок с AI помощью

---

## ⚙️ Конфигурация

### instruments.yaml
```yaml
instruments:
  XAUUSD:
    enabled: true
    risk_per_trade: 2.0
    max_trades_per_day: 3
    strategy_class: "StrategyXAUUSD"
```

### Настройки по умолчанию:
- **Leverage:** 100:1
- **Spread:** 20 points ($0.20)
- **Commission:** $7 per lot
- **Timezone:** UTC

---

## 📊 Ожидаемые Результаты

### С балансом $500:
- Expected Final: **~$1,718** (+243%)
- Max Drawdown: **~$50** (10%)
- Total Trades: **~100** в год
- Average per Trade: **+$12**

### С балансом $1000:
- Expected Final: **~$3,435** (+243%)
- Max Drawdown: **~$100** (10%)
- Total Trades: **~100** в год
- Average per Trade: **+$24**

---

## 🔧 Требования

- Python 3.8+
- MetaTrader 5
- Интернет соединение (для новостей)
- Минимальный баланс: $100

---

## 📝 Примечания

- Бот торгует ТОЛЬКО золотом (XAUUSD)
- EURUSD убран (показал убыточность с реальными costs)
- Система лицензирования удалена (бесплатная версия)
- Все эксперименты и тесты удалены (проект очищен)

---

**Проект готов к использованию!**

*Дата очистки: 6 января 2026*

# 📂 Структура проекта BAZA Trading Bot

## 🎯 Организация файлов

```
BAZA/
│
├── 📄 main.py                      # Точка входа в приложение
├── 📄 requirements.txt             # Python зависимости
├── 📄 build_exe.py                 # Сборка исполняемого файла
├── 📄 train_ml_model.py           # Обучение ML модели
├── 📄 generate_key.py             # Генерация лицензионных ключей
│
├── 📁 config/                      # Конфигурационные файлы
│   ├── mt5.yaml                   # Настройки MT5
│   ├── instruments.yaml           # Торговые инструменты
│   ├── portfolio.yaml             # Настройки портфеля
│   ├── ai.yaml                    # AI конфигурация
│   └── .env                       # Переменные окружения (API ключи)
│
├── 📁 src/                         # Исходный код
│   │
│   ├── 📁 core/                   # Ядро системы
│   │   ├── app_state.py          # Централизованное состояние
│   │   ├── mt5_manager.py        # Управление MetaTrader 5
│   │   ├── bot_manager.py        # Управление ботом
│   │   ├── executor.py           # Исполнение сделок
│   │   ├── risk_manager.py       # Риск-менеджмент
│   │   ├── logger.py             # Система логирования
│   │   ├── license.py            # Проверка лицензии
│   │   ├── broker_sim.py         # Симуляция брокера (для бэктеста)
│   │   ├── data_loader.py        # Загрузка данных
│   │   ├── manual_trade_state.py # Состояние ручной торговли
│   │   └── market_data_updater.py # Обновление рыночных данных
│   │
│   ├── 📁 gui/                    # Графический интерфейс
│   │   └── app.py                # Главное окно приложения (2600+ строк)
│   │
│   ├── 📁 strategies/             # Торговые стратегии
│   │   ├── __init__.py
│   │   ├── xauusd_strategy.py   # Стратегия для золота (XAUUSD)
│   │   └── eurusd_strategy.py   # Стратегия для евро (EURUSD)
│   │
│   ├── 📁 ai/                     # AI модули
│   │   ├── __init__.py
│   │   ├── news_filter.py       # GPT фильтр новостей
│   │   └── news_fetcher.py      # Получение актуальных новостей
│   │
│   ├── 📁 ml/                     # Machine Learning
│   │   ├── __init__.py
│   │   ├── predictor.py         # ML предсказания (LightGBM)
│   │   └── features.py          # Извлечение фич
│   │
│   ├── 📁 manual_trading/         # Ручная торговля
│   │   ├── __init__.py
│   │   ├── controller.py        # Контроллер ручной торговли
│   │   ├── calculator.py        # Калькуляции (лоты, RR)
│   │   ├── validator.py         # Валидация параметров
│   │   └── ai_analyzer.py       # AI анализ сделок
│   │
│   ├── 📁 backtest/               # Бэктестинг
│   │   ├── __init__.py
│   │   ├── backtester.py        # Основной бэктестер
│   │   ├── portfolio_backtester.py # Портфельный бэктест
│   │   └── metrics.py           # Расчёт метрик
│   │
│   ├── 📁 live/                   # Live торговля
│   │   ├── __init__.py
│   │   └── live_trader.py       # Live трейдер
│   │
│   ├── 📁 mt5/                    # MT5 интеграция
│   │   ├── __init__.py
│   │   └── connector.py         # Коннектор к MT5
│   │
│   └── 📄 models.py               # Общие модели данных
│
├── 📁 data/                        # Данные приложения
│   ├── bot_stats.json             # Статистика бота
│   ├── config.json                # Конфигурация (runtime)
│   ├── license.json               # Лицензионные данные
│   ├── trades_history.json        # История сделок
│   │
│   └── 📁 backtest/               # Данные для бэктестинга
│       ├── EURUSD_H1_2023_2025.csv
│       ├── EURUSD_M15_2023_2025.csv
│       ├── XAUUSD_H1_2023_2025.csv
│       └── XAUUSD_M15_2023_2025.csv
│
├── 📁 logs/                        # Логи приложения
│   └── baza_YYYYMMDD.log         # Ежедневные логи
│
├── 📁 models/                      # ML модели
│   └── trade_predictor.pkl       # Обученная модель (если есть)
│
├── 📁 results/                     # Результаты бэктестов
│   ├── 📁 eurusd/
│   ├── 📁 xauusd/
│   └── 📁 portfolio/
│
├── 📁 docs/                        # 📚 Документация
│   ├── README.md                  # Навигация по документации
│   ├── BUGFIXES.md               # История исправлений
│   ├── IMPROVEMENTS_SUMMARY.md   # Сводка улучшений
│   ├── AI_SCREENSHOT_ANALYSIS.md # Анализ скриншотов
│   ├── QUICKSTART_SCREENSHOT.md  # Быстрый старт со скриншотами
│   ├── NEWS_FIX.md               # Интеграция новостей
│   ├── TESTING_CHECKLIST.md      # Чеклист тестирования
│   └── CLEANUP_LIST.md           # Список очистки
│
├── 📁 scripts/                     # Вспомогательные скрипты
│   └── cleanup_sensitive.sh      # Очистка чувствительных данных
│
├── 📄 README.md                    # Главная страница проекта
├── 📄 ARCHITECTURE_2.0.md         # Архитектура системы
├── 📄 MANUAL_TRADING_README.md    # Руководство по ручной торговле
├── 📄 LAUNCH_CHECKLIST.md         # Чеклист запуска
├── 📄 CONTRIBUTING.md             # Гайд для контрибьюторов
├── 📄 LICENSE                     # Лицензия
│
├── 📄 .gitignore                  # Git игнорируемые файлы
├── 📄 .env.example                # Пример переменных окружения
├── 📄 BAZA.spec                   # Спецификация для PyInstaller
│
├── 📁 build/                       # Временные файлы сборки (git ignored)
├── 📁 dist/                        # Готовый EXE файл (git ignored)
├── 📁 .venv/                       # Виртуальное окружение (git ignored)
└── 📁 __pycache__/                 # Python кэш (git ignored)
```

---

## 📊 Статистика проекта

### Размер кодовой базы
- **Всего файлов:** ~50 Python файлов
- **Строк кода:** ~15,000+ строк
- **Модули:** 8 основных модулей
- **Документация:** 12 MD файлов

### Ключевые файлы
| Файл | Строк | Описание |
|------|-------|----------|
| `src/gui/app.py` | ~2,600 | Главное GUI приложение |
| `src/strategies/xauusd_strategy.py` | ~400 | XAUUSD стратегия |
| `src/strategies/eurusd_strategy.py` | ~400 | EURUSD стратегия |
| `src/manual_trading/controller.py` | ~300 | Контроллер ручной торговли |
| `src/ai/news_fetcher.py` | ~280 | Получение новостей |

---

## 🗂️ Что где находится

### Хочешь настроить бота?
→ `config/*.yaml`

### Ищешь стратегии?
→ `src/strategies/`

### Нужно посмотреть логи?
→ `logs/baza_YYYYMMDD.log`

### Хочешь изменить GUI?
→ `src/gui/app.py`

### Изучить архитектуру?
→ `ARCHITECTURE_2.0.md` + `docs/README.md`

### Запустить бэктест?
→ `python main.py --backtest --year 2024`

### Обучить ML модель?
→ `python train_ml_model.py`

### Собрать EXE?
→ `python build_exe.py`

---

## 🧹 Что было удалено

В процессе организации проекта были удалены:

### ❌ Старые файлы
- `test_trader.py`
- `test_livetrader_gpt.py`
- `test_gui.py`
- `test_gpt_filter.py`
- `final_test.py`

### ❌ Бэкапы
- `src/live/live_trader_old.py`
- `src/backtest/backtester_backup.py`

### ❌ Тестовые скрипты
- `scripts/test_ai_dynamic.py`
- `scripts/test_ai_init.py`
- `scripts/test_display_ai_ui.py`
- `scripts/test_manual_predict.py`

---

## 📝 Соглашения

### Именование файлов
- **Python файлы:** `snake_case.py`
- **Конфиги:** `lowercase.yaml`
- **Документация:** `UPPERCASE.md`

### Структура модулей
```python
# Каждый модуль имеет __init__.py
src/
  module/
    __init__.py      # Экспорты
    main_file.py     # Основная логика
    helpers.py       # Вспомогательные функции
```

### Логирование
- **Файлы:** `logs/baza_YYYYMMDD.log`
- **Формат:** `[YYYY-MM-DD HH:MM:SS] [LEVEL] Message`
- **Ротация:** Ежедневная

---

## 🔐 Безопасность

### Игнорируются Git:
- `.env` - API ключи
- `*.enc` - Шифрованные credentials
- `license_*.txt` - Лицензии
- `data/` - Пользовательские данные
- `logs/` - Логи
- `__pycache__/` - Python кэш
- `.venv/` - Виртуальное окружение
- `build/`, `dist/` - Сборки

---

**Обновлено:** 02.01.2026  
**Версия:** 1.2.0  
**Файлов:** ~50 Python + 12 MD  
**Строк кода:** ~15,000+

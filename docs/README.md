# 📚 BAZA Trading Bot - Документация

Полная документация проекта BAZA Trading Bot.

---

## 📖 Содержание

### 🚀 Начало работы
1. **[README.md](../README.md)** - Главная страница проекта
2. **[ARCHITECTURE_2.0.md](../ARCHITECTURE_2.0.md)** - Архитектура системы
3. **[LAUNCH_CHECKLIST.md](../LAUNCH_CHECKLIST.md)** - Чеклист перед запуском

### 🛠️ Разработка
4. **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Как внести свой вклад
5. **[BUGFIXES.md](BUGFIXES.md)** - История исправлений багов
6. **[IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)** - Сводка улучшений

### ✨ Новые функции
7. **[AI_SCREENSHOT_ANALYSIS.md](AI_SCREENSHOT_ANALYSIS.md)** - Анализ скриншотов MT5 через GPT-4 Vision
8. **[QUICKSTART_SCREENSHOT.md](QUICKSTART_SCREENSHOT.md)** - Быстрый старт работы со скриншотами
9. **[NEWS_FIX.md](NEWS_FIX.md)** - Интеграция актуальных новостей

### 📊 Торговля
10. **[MANUAL_TRADING_README.md](../MANUAL_TRADING_README.md)** - Руководство по ручной торговле

### 🧪 Тестирование
11. **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - Чеклист тестирования

### 🗑️ Обслуживание
12. **[CLEANUP_LIST.md](CLEANUP_LIST.md)** - Список файлов для очистки

---

## 🎯 Быстрый доступ

### Для пользователей:
- **Установка:** [README.md](../README.md#установка)
- **Первый запуск:** [LAUNCH_CHECKLIST.md](../LAUNCH_CHECKLIST.md)
- **Ручная торговля:** [MANUAL_TRADING_README.md](../MANUAL_TRADING_README.md)
- **AI Аналитик:** [QUICKSTART_SCREENSHOT.md](QUICKSTART_SCREENSHOT.md)

### Для разработчиков:
- **Архитектура:** [ARCHITECTURE_2.0.md](../ARCHITECTURE_2.0.md)
- **История изменений:** [BUGFIXES.md](BUGFIXES.md)
- **Тестирование:** [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
- **Вклад в проект:** [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📂 Структура проекта

```
BAZA/
├── main.py                      # Точка входа
├── requirements.txt             # Зависимости
├── build_exe.py                 # Сборка EXE
├── train_ml_model.py           # Обучение ML модели
│
├── config/                      # Конфигурация
│   ├── mt5.yaml                # MT5 настройки
│   ├── instruments.yaml        # Торговые инструменты
│   ├── portfolio.yaml          # Портфель
│   └── ai.yaml                 # AI настройки
│
├── src/                         # Исходный код
│   ├── core/                   # Ядро системы
│   │   ├── app_state.py       # Состояние приложения
│   │   ├── mt5_manager.py     # Управление MT5
│   │   ├── bot_manager.py     # Управление ботом
│   │   ├── executor.py        # Исполнение сделок
│   │   ├── risk_manager.py    # Риск-менеджмент
│   │   └── logger.py          # Логирование
│   │
│   ├── gui/                    # Графический интерфейс
│   │   └── app.py             # Главное окно
│   │
│   ├── strategies/             # Торговые стратегии
│   │   ├── xauusd_strategy.py # XAUUSD стратегия
│   │   └── eurusd_strategy.py # EURUSD стратегия
│   │
│   ├── ai/                     # AI модули
│   │   ├── news_filter.py     # GPT фильтр новостей
│   │   └── news_fetcher.py    # Получение новостей
│   │
│   ├── ml/                     # Machine Learning
│   │   ├── predictor.py       # ML предиктор
│   │   └── features.py        # Фичи для ML
│   │
│   ├── manual_trading/         # Ручная торговля
│   │   ├── controller.py      # Контроллер
│   │   ├── calculator.py      # Калькулятор
│   │   ├── validator.py       # Валидатор
│   │   └── ai_analyzer.py     # AI анализ
│   │
│   ├── backtest/               # Бэктестинг
│   │   ├── backtester.py      # Бэктестер
│   │   ├── portfolio_backtester.py
│   │   └── metrics.py         # Метрики
│   │
│   └── live/                   # Live торговля
│       └── live_trader.py     # Live трейдер
│
├── data/                        # Данные
│   ├── bot_stats.json          # Статистика бота
│   ├── trades_history.json     # История сделок
│   └── backtest/               # Данные для бэктеста
│
├── logs/                        # Логи
├── models/                      # ML модели
├── results/                     # Результаты бэктестов
│
└── docs/                        # 📚 Документация
    ├── README.md               # Этот файл
    ├── BUGFIXES.md            # Исправления
    ├── IMPROVEMENTS_SUMMARY.md # Улучшения
    ├── AI_SCREENSHOT_ANALYSIS.md
    ├── NEWS_FIX.md
    └── TESTING_CHECKLIST.md
```

---

## 🔥 Ключевые функции

### ⚡ Автоматическая торговля
- Smart Money Concepts (SMC) стратегии
- ML-powered предсказания
- GPT фильтр новостей
- Автоматический риск-менеджмент

### 💼 Ручная торговля
- AI-анализ сделок
- Автоматический расчет лотов
- Валидация параметров
- GPT-4 Vision анализ графиков

### 📊 Бэктестинг
- Исторические данные 2023-2025
- Портфельный бэктестинг
- Детальные метрики
- Экспорт результатов

### 🤖 AI Интеграция
- **GPT-4o Vision** - анализ скриншотов MT5
- **GPT-4o-mini** - текстовый анализ
- **Актуальные новости** - экономический календарь
- **ML предиктор** - LightGBM модель

---

## 📈 Результаты

| Год | XAUUSD ROI | EURUSD ROI | Portfolio ROI | Max DD |
|-----|------------|------------|---------------|--------|
| 2023 | 42.5% | 285.3% | 163.9% | 18.5% |
| 2024 | 45.86% | 340.75% | 193.31% | 20.8% |
| 2025 | 48.2% | 52.8% | 50.5% | 16.8% |
| **AVG** | **45.5%** | **226%** | **136%** | **18.7%** |

---

## 🛠️ Технологии

- **Python 3.9+**
- **MetaTrader 5** - торговая платформа
- **OpenAI GPT-4** - AI анализ
- **LightGBM** - машинное обучение
- **Tkinter/CustomTkinter** - GUI
- **Pandas/Numpy** - обработка данных

---

## 📞 Поддержка

- **Email:** kamsaaaimpa@gmail.com
- **Issues:** GitHub Issues
- **Документация:** Этот файл

---

## 📝 Версии

### v1.2.0 (02.01.2026) - Актуальная
- ✅ Добавлен анализ скриншотов MT5 через GPT-4 Vision
- ✅ Интеграция актуальных экономических новостей
- ✅ Исправлены критические баги (race conditions, memory leaks)
- ✅ Улучшена обработка ошибок
- ✅ Добавлены type hints

### v1.1.0 (30.12.2025)
- Добавлена ручная торговля с AI
- ML предиктор
- Портфельный бэктестинг

### v1.0.0 (01.12.2025)
- Первый релиз
- Базовые стратегии SMC
- GUI приложение

---

## 📄 Лицензия

Proprietary License - см. [LICENSE](../LICENSE)

---

**Обновлено:** 02.01.2026  
**Версия:** 1.2.0  
**Статус:** ✅ Production Ready

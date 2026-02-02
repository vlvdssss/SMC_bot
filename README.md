#  BAZA Trading Bot - Pure AI Mode

> **Автоматический торговый бот для MetaTrader 5 с искусственным интеллектом GPT-4**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![MT5](https://img.shields.io/badge/MetaTrader-5-green.svg)](https://www.metatrader5.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)

---

##  Особенности

###  Pure AI Trading
- **100% GPT-4 решения** - нет технических индикаторов
- **Анализ каждые 5 минут** - постоянный мониторинг рынка
- **Скриншоты графиков** - визуальный анализ M5, M15, H1
- **Новости в реальном времени** - фундаментальный анализ

###  Управление рисками
- **Signal Quality V3** - оценка точности и качества сигналов
- **Адаптивный лот** - автоматическая корректировка объема (0.5x - 1.5x)
- **Trailing Stop V4** - защита прибыли (активация 60%, стоп 50%)
- **Fixed SL/TP** - фиксированные уровни риска ($2-$5)

###  Telegram интеграция
- **Уведомления о сделках** - открытие, закрытие с детальной статистикой
- **AI сигналы с кнопками** - удаление сигнала одним нажатием
- **Ежедневные отчеты** - автоматическая отправка статистики
- **Интерактивный бот** - кнопки для запросов отчетов и статуса

---

##  Быстрый старт

### Windows:
```powershell
.\run.ps1
```

### Или напрямую:
```bash
python main.py
```

---

##  Документация

### Основные руководства
- [AI Schedule Guide](docs/AI_SCHEDULE_GUIDE.md) - настройка расписания анализа
- [Lot Size Guide](docs/LOT_SIZE_GUIDE.md) - управление размером позиции
- [V4 Changes](docs/V4_CHANGES.md) - изменения в версии 4.0

### Функционал
- [Delete Signal Feature](docs/DELETE_SIGNAL_FEATURE.md) - удаление сигналов
- [Telegram Buttons](docs/TELEGRAM_SIGNAL_BUTTONS.md) - интерактивные кнопки
- [Auto Cleanup](docs/AUTO_CLEANUP.md) - автоочистка данных

### Troubleshooting
- [OpenAI API](docs/OPENAI_API_TROUBLESHOOTING.md) - решение проблем с API
- [Quick Fix](docs/QUICK_FIX_API.md) - быстрые исправления
- [News API](docs/NEWS_API.md) - настройка новостей

---

##  Структура

```
BAZA/
  src/           # Исходный код
  config/        # Конфигурация (YAML)
  data/          # Данные (JSON, логи)
  docs/          # Документация
  scripts/       # Утилиты и скрипты
  main.py       # Точка входа
```

---

##  Статистика

-  **Баланс:** $293.01
-  **Total PnL:** $126.67
-  **Сделок:** 234 (48W / 186L)
-  **Winrate:** 20.5%

---

##  Changelog

### [v4.0] - 2026-02-02
-  Исправлен расчет PnL для XAUUSD
-  Защита от дублирования GPT запросов (60 сек)
-  Кнопка Delete Signal в GUI и Telegram
-  Увеличен min_confidence до 75%

---

**Made with  and AI**

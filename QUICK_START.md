# ⚡ Быстрый старт BAZA Trading Bot

## Для нового пользователя (5 минут)

### Шаг 1: Установка (2-3 минуты)
```powershell
.\install.ps1
```
или просто двойной клик по `install.bat`

### Шаг 2: Настройка конфигурации (2 минуты)

1. **MT5 подключение:**
   ```powershell
   cd config
   copy mt5.yaml.example mt5.yaml
   notepad mt5.yaml
   ```
   Заполни: логин, пароль, сервер

2. **Telegram бот:**
   ```powershell
   copy telegram.yaml.example telegram.yaml
   notepad telegram.yaml
   ```
   Заполни: bot_token (от @BotFather), chat_id (от @userinfobot)

3. **OpenAI API:**
   Файл `ai.yaml` уже существует, проверь API ключ

### Шаг 3: Проверка
```powershell
.\check_install.ps1
```

### Шаг 4: Запуск!
```powershell
.\start_bot.ps1
```

---

## Для опытного пользователя (1 минута)

```powershell
# Установка
.\quick_install.ps1

# Конфигурация
cd config
copy mt5.yaml.example mt5.yaml
copy telegram.yaml.example telegram.yaml
# Отредактируй файлы

# Запуск
python main.py
```

---

## Что делает бот?

✅ **Каждые 5 минут:**
- Анализирует XAUUSD, EURUSD, GBPUSD через GPT-4
- Делает скриншоты графиков M5, M15, H1
- Читает новости и экономический календарь
- Генерирует торговые сигналы

✅ **При сигнале:**
- Оценивает качество (Signal Quality V3)
- Адаптирует размер лота (0.5x - 1.5x)
- Открывает сделку в MT5
- Отправляет уведомление в Telegram

✅ **Управление сделками:**
- Trailing Stop (активация 60%, стоп 50%)
- Fixed SL/TP ($2-$5)
- Защита от проскальзываний
- Автоматическое закрытие

---

## Полезные команды

```powershell
# Проверка установки
.\check_install.ps1

# Переустановка (если проблемы)
.\quick_install.ps1 --clean

# Активация окружения
.\.venv\Scripts\Activate.ps1

# Обновление зависимостей
pip install -r requirements.txt --upgrade

# Просмотр логов
Get-Content logs\baza_*.log -Tail 50
```

---

## Структура проекта

```
BAZA/
├── install.ps1          ← Полный установщик
├── quick_install.ps1    ← Быстрая установка
├── check_install.ps1    ← Проверка установки
├── start_bot.ps1        ← Запуск бота
├── main.py              ← Точка входа
├── config/              ← Настройки
│   ├── mt5.yaml         ← MT5 подключение
│   ├── telegram.yaml    ← Telegram бот
│   ├── ai.yaml          ← OpenAI API
│   └── trading.yaml     ← Торговые параметры
├── data/                ← Данные бота
├── logs/                ← Логи
└── .venv/               ← Виртуальное окружение
```

---

## Основные настройки

### trading.yaml - торговля
```yaml
risk_percent: 1.0          # Риск на сделку (%)
max_daily_trades: 10       # Макс сделок в день
trailing_stop_pips: 50     # Трейлинг стоп
```

### ai.yaml - AI анализ
```yaml
min_confidence: 75         # Мин уверенность (%)
analysis_interval: 300     # Интервал анализа (сек)
model: "gpt-4"            # Модель GPT
```

### portfolio.yaml - инструменты
```yaml
XAUUSD:
  enabled: true
  lot_multiplier: 1.0      # 0.5-1.5 (адаптивный)
```

---

## Мониторинг

### Telegram команды:
- `/start` - Активация бота
- `/status` - Текущий статус
- `/stats` - Статистика сделок
- `/report` - Дневной отчёт
- Кнопка **Delete Signal** - отмена сигнала

### Логи:
```powershell
# Последние 50 строк
Get-Content logs\baza_*.log -Tail 50

# Мониторинг в реальном времени
Get-Content logs\baza_*.log -Wait -Tail 10
```

---

## Требования

- ✅ Windows 10/11
- ✅ Python 3.9+
- ✅ MetaTrader 5
- ✅ OpenAI API ключ (с балансом)
- ✅ Telegram бот токен
- ✅ Интернет соединение

---

## Помощь

📖 **Документация:**
- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - Установка
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Решение проблем
- [README.md](README.md) - Полное описание
- [docs/](docs/) - Детальные гайды

💬 **Нужна помощь?** Напиши разработчику!

---

🚀 **Готов к торговле!**

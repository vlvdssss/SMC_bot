# 🚀 Инструкция по настройке BAZA Trading Bot

## ✅ Исправлена критическая ошибка

**Проблема**: `'ConfigManager' object has no attribute 'get_config'`  
**Статус**: ✅ **ИСПРАВЛЕНО и запушено на GitHub**

---

## 📋 Что нужно сделать для запуска бота

### 1️⃣ Настроить OpenAI API ключ

**Файл**: `config/ai.yaml`

Сейчас:
```yaml
gpt:
  api_key: null  # ❌ Нужно заменить
```

**Нужно сделать**:
1. Получить API ключ на https://platform.openai.com/api-keys
2. Открыть файл `config/ai.yaml`
3. Найти строку `api_key: null`
4. Заменить на:
```yaml
gpt:
  api_key: sk-proj-ваш_реальный_ключ_здесь
```

---

### 2️⃣ Проверить настройки MT5

**Файл**: `config/mt5.yaml`

Текущие настройки:
```yaml
mt5:
  connection:
    login: 5046623512
    password: '*y7fQpIq'
    server: MetaQuotes-Demo
    path: "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
```

**Что проверить**:
- ✅ Терминал MT5 **запущен и подключен**
- ✅ Путь к `terminal64.exe` правильный
- ✅ Логин/пароль/сервер верные
- ✅ В терминале зелёная надпись "Connected to [server]"

**Если путь к MT5 другой**:
Замените путь на правильный, например:
```yaml
path: "C:\\MT5\\terminal64.exe"
```

---

### 3️⃣ Telegram бот (опционально)

**Файл**: `config/telegram.yaml`

Если хотите уведомления в Telegram:
1. Создайте бота через @BotFather
2. Получите токен
3. Настройте в `config/telegram.yaml`:
```yaml
telegram:
  enabled: true
  bot_token: ваш_токен_от_BotFather
  chat_id: ваш_chat_id
```

---

## 🎯 Запуск бота

### Вариант 1: Быстрый старт (рекомендуется)
```powershell
.\setup_and_run.ps1
```
Этот скрипт:
- ✅ Проверит Python 3.9+
- ✅ Создаст виртуальное окружение
- ✅ Установит все зависимости
- ✅ Скопирует примеры конфигов (если нужно)
- ✅ Запустит GUI

### Вариант 2: Запуск GUI напрямую
```powershell
.\run_gui_v2.ps1
```

---

## ❌ Разбор ошибок из скриншота

### Ошибка 1: CONFIG/GPT: 'ConfigManager' object has no attribute 'get_config'
**Статус**: ✅ **ИСПРАВЛЕНО**  
**Что было**: Отсутствовал метод `get_config()` в классе ConfigManager  
**Что сделано**: Добавлен метод, запушено на GitHub (коммит c4c1222)

### Ошибка 2: MT5: Failed to get MT5 info
**Причина**: Терминал MT5 не подключен или не запущен  
**Решение**:
1. Откройте MetaTrader 5
2. Войдите в демо-счёт (или реальный)
3. Дождитесь подключения (зелёная надпись в нижнем углу)
4. Повторите запуск бота

---

## 🔍 Проверка конфигурации

После настройки проверьте:

```powershell
# Проверка Git статуса
git status

# Проверка последнего коммита
git log -1

# Обновление с GitHub
git pull origin main
```

---

## 📁 Структура важных файлов

```
SMC_bot/
├── setup_and_run.ps1       # ⭐ Основной установщик (один клик)
├── run_gui_v2.ps1          # ⭐ Запуск GUI
├── README.md               # Основная документация
├── config/
│   ├── ai.yaml             # ⚠️ OpenAI API ключ
│   ├── mt5.yaml            # ⚠️ MT5 учетные данные
│   ├── trading.yaml        # Правила торговли
│   ├── portfolio.yaml      # Портфель и риски
│   └── telegram.yaml       # Telegram уведомления
├── docs/                   # Вся документация
├── tests/                  # Все тесты
└── scripts/                # Утилиты
```

---

## ⚙️ Следующие шаги

1. ✅ Код исправлен и запушен на GitHub
2. 🔧 **Настройте OpenAI API ключ** в `config/ai.yaml`
3. 🔧 **Запустите и подключите MT5**
4. 🚀 **Запустите бота**: `.\setup_and_run.ps1`

---

## 🆘 Если всё равно не работает

Создайте Issue на GitHub: https://github.com/vlvdssss/SMC_bot/issues

Укажите:
- Текст ошибки
- Скриншот
- Версию Python (`python --version`)
- Статус MT5 (подключен/отключен)

---

## 📌 Полезные ссылки

- 🌐 GitHub репозиторий: https://github.com/vlvdssss/SMC_bot
- 📖 Основная документация: [README.md](README.md)
- 🔧 Документация по деплою: [docs/DEPLOYMENT_READY.md](docs/DEPLOYMENT_READY.md)
- ❓ GitHub Setup: [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md)

---

**Версия**: 2.0  
**Дата**: 23.02.2026  
**Последний коммит**: c4c1222 (Fix: Added missing get_config() method)

# 🚀 Инструкция по настройке BAZA Trading Bot

## ✅ Исправлена критическая ошибка

**Проблема 1**: `'ConfigManager' object has no attribute 'get_config'`  
**Статус**: ✅ **ИСПРАВЛЕНО** (коммит c4c1222)

**Проблема 2**: OpenAI API ключ не считывался из `.env`  
**Статус**: ✅ **ИСПРАВЛЕНО** (коммит 43c1631)

---

## 🚀 БЫСТРАЯ ДИАГНОСТИКА

### Проверить MT5 подключение:
```powershell
.\test_mt5_connection.ps1
```

Этот скрипт покажет:
- ✅ MT5 установлен и работает
- ✅ Терминал подключен к серверу
- ✅ Аккаунт активен
- ✅ Доступны нужные символы (XAUUSD, EURUSD и т.д.)

### Проверить все настройки:
```powershell
.\setup_and_run.ps1
```

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

**ЧТО ВАЖНО ДЛЯ MT5**:

#### ⚡ Терминал ДОЛЖЕН быть запущен и подключен!

**Пошаговая проверка**:

1. **Запустите MetaTrader 5**
   - Найдите на рабочем столе или в меню Пуск
   - Дождитесь полной загрузки терминала

2. **Проверьте подключение**
   - Посмотрите в правый нижний угол MT5
   - Должна быть **зелёная надпись** с указанием пинга (например: "96/1232 ms")
   - Если красная надпись "No connection" - нужно подключиться

3. **Если отключен - подключитесь**:
   ```
   File → Login to Trade Account
   Введите логин/пароль/сервер
   Нажмите Login
   ```

4. **Проверьте права на торговлю**:
   - Правой кнопкой на аккаунт в окне "Toolbox → Trade"
   - Убедитесь что "Trading" разрешено

5. **Добавьте инструменты в Market Watch**:
   - Ctrl+U → открыть список всех символов
   - Найдите: XAUUSD, EURUSD, GBPUSD
   - Убедитесь что галочки включены (символы видимы)

**🔍 Тест подключения**:
```powershell
.\test_mt5_connection.ps1
```

Этот скрипт автоматически проверит:
- ✅ MT5 установлен
- ✅ Терминал работает
- ✅ Подключён к серверу  
- ✅ Аккаунт активен
- ✅ Символы доступны

**Типичные ошибки MT5**:

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `MT5 initialization failed` | Терминал не запущен | Откройте MT5 |
| `Failed to get MT5 info` | Терминал не подключен | File → Login to Trade Account |
| `Terminal not connected` | Нет соединения с сервером | Проверьте интернет, перезапустите MT5 |
| `Symbol not available` | Инструмент не добавлен | Ctrl+U → включите нужные символы |
| `Trading not allowed` | Запрет торговли | Права аккаунта или Demo только для тестов |

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

**Версия**: 2.1  
**Дата**: 23.02.2026  
**Последние коммиты**:
- 43c1631 - Fix: Correct API key path in preflight checks
- 2ef6930 - Add: Complete setup guide
- c4c1222 - Fix: Added missing get_config() method

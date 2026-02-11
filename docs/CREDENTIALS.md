# 🔐 Credentials - Как использовать

## Где файл?

Все чувствительные данные находятся в файле:
```
C:\Users\kamsa\Desktop\baza_credentials.txt
```

## Что там внутри?

```text
# OpenAI GPT API
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# MT5 Trading Account  
MT5_LOGIN=99538704
MT5_PASSWORD=-4ZwEoIx
MT5_SERVER=MetaQuotes-Demo

# Telegram Bot
TELEGRAM_BOT_TOKEN=8531407014:AAFsKnKlt5w05cL4zRv5771ZbuZJY1gmQHU
TELEGRAM_CHAT_ID=543258309
```

## Как настроить?

### 1. Открой файл

```powershell
notepad C:\Users\kamsa\Desktop\baza_credentials.txt
```

### 2. Замени данные

- **OPENAI_API_KEY** - получи на https://platform.openai.com/api-keys
  - Формат: `sk-proj-...` (начинается с `sk-`)
  
- **MT5_LOGIN** - твой логин в MetaTrader 5
  - Формат: число (например `12345678`)
  
- **MT5_PASSWORD** - твой пароль от MT5
  - Формат: строка (может быть `-4ZwEoIx` или любой другой)
  
- **MT5_SERVER** - сервер твоего брокера
  - Формат: `BrokerName-Server` (например `MetaQuotes-Demo`)
  
- **TELEGRAM_BOT_TOKEN** - токен от @BotFather
  - Формат: `1234567890:ABC...` (число:строка)
  
- **TELEGRAM_CHAT_ID** - твой chat ID от @userinfobot
  - Формат: число (например `543258309`)

### 3. Сохрани файл

Нажми `Ctrl+S` в блокноте и закрой.

### 4. Перезапусти бота

Бот автоматически загрузит новые данные при запуске.

## Как это работает?

Бот читает credentials в таком порядке:

**Для MT5:**
1. Сначала проверяет `baza_credentials.txt` (приоритет!)
2. Если не найдено → проверяет `config/mt5.yaml` (fallback)

**Для Telegram:**
1. Сначала проверяет `baza_credentials.txt` (приоритет!)
2. Если не найдено → проверяет `config/telegram.yaml` (fallback)

**Для OpenAI:**
1. Сначала проверяет `baza_credentials.txt` (приоритет!)
2. Если не найдено → проверяет переменную окружения `OPENAI_API_KEY`
3. Если не найдено → проверяет `.env` файл (fallback)

## Безопасность 🔒

- ✅ Файл находится НА РАБОЧЕМ СТОЛЕ, не в проекте
- ✅ Добавлен в `.gitignore` (не попадет в GitHub)
- ✅ Не синхронизируется с git
- ⚠️ **НЕ ПОКАЗЫВАЙ ЭТОТ ФАЙЛ НИКОМУ!**
- ⚠️ **НЕ ВЫКЛАДЫВАЙ СКРИНШОТЫ С ДАННЫМИ!**

## Если файл потерялся

Бот автоматически создает файл с шаблоном при первом запуске:
```
C:\Users\kamsa\Desktop\baza_credentials.txt
```

Если его нет - запусти бота, и он создаст шаблон.

## Проверка

Запусти бота и посмотри в логи:

✅ **Успешно:**
```
[Credentials] ✅ Loaded 6 credentials from external file
[Credentials] Keys: OPENAI_API_KEY, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

❌ **Ошибка:**
```
[Credentials] File not found: C:\Users\kamsa\Desktop\baza_credentials.txt
Please create this file with your credentials!
```

## Частые ошибки

### "OpenAI API key not found"
**Решение:** 
1. Открой `baza_credentials.txt`
2. Замени `YOUR_OPENAI_API_KEY_HERE` на настоящий ключ от OpenAI
3. Проверь что ключ начинается с `sk-`

### "MT5 Connection failed"
**Решение:**
1. Проверь что MT5 запущен
2. Проверь логин/пароль/сервер в `baza_credentials.txt`
3. Убедись что нет пробелов в начале/конце строк

### "Telegram connection error"
**Решение:**
1. Проверь что токен правильный (от @BotFather)
2. Проверь что chat_id правильный (от @userinfobot) 
3. Убедись что бот не заблокирован в чате

## Альтернатива

Если не хочешь использовать credentials файл, можешь продолжать использовать старый способ:

- MT5: `config/mt5.yaml`
- Telegram: `config/telegram.yaml`
- OpenAI: `.env` файл или переменные окружения

Но credentials файл **БЕЗОПАСНЕЕ** т.к. находится вне проекта!

## Помощь

Если что-то не работает:
1. Проверь логи в `logs/baza_YYYYMMDD.log`
2. Поищи строки с `[Credentials]`
3. Посмотри что именно не загрузилось
4. Исправь в `baza_credentials.txt`

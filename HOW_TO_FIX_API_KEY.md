# 🔑 Как настроить API ключ OpenAI

## Проблема
Бот показывает ошибку 401 "Incorrect API key provided"

## Причина
В файле `.env` установлен старый/недействительный API ключ

## ✅ Решение за 2 минуты

### Шаг 1: Получи новый API ключ
1. Открой: https://platform.openai.com/api-keys
2. Войди в аккаунт OpenAI
3. Нажми "Create new secret key"
4. Скопируй ключ (выглядит так: `sk-proj-...` или `sk-...`)

### Шаг 2: Добавь ключ в .env
1. Открой файл `.env` в корне проекта `SMC_bot`
2. Найди строку: `OPENAI_API_KEY=YOUR_WORKING_API_KEY_HERE`
3. Замени `YOUR_WORKING_API_KEY_HERE` на свой ключ
4. Сохрани файл

**Пример:**
```env
OPENAI_API_KEY=sk-proj-AbC123XyZ... (твой настоящий ключ)
```

**ВАЖНО:** 
- Ключ должен быть БЕЗ пробелов
- Ключ должен быть БЕЗ кавычек
- Ключ должен быть на ОДНОЙ строке

### Шаг 3: Перезапусти бота
```powershell
python main.py
# или
.\run_gui_v2.ps1
```

## ✅ Проверка что работает
После запуска должно быть:
```
✅ API Key loaded: sk-proj-AbC123...xyZ
✅ OpenAI client initialized
```

Вместо:
```
❌ OpenAI API key not configured
⚠️ Bot will work in MANUAL mode without AI analysis
```

---

## 🆘 Если всё ещё не работает

### Проблема: "API key not configured"
**Решение:** Проверь что файл `.env` находится в корне `SMC_bot/`, а не в подпапке

### Проблема: "401 Incorrect API key"
**Решение:** Ключ неверный или истёк, создай новый на https://platform.openai.com/api-keys

### Проблема: Ключ правильный, но всё равно ошибка
**Решение:** Убери лишние символы (пробелы, \n, кавычки) из .env файла

### Проблема: Не хочу использовать AI
**Решение:** Это ОК! Бот работает в ручном режиме без AI:
- Открой `config/ai.yaml`
- Установи `manual_overrides.enabled: true`
- Все сделки будут открываться с фиксированными SL/TP

---

## 📁 Где хранится ключ?

Бот ищет API ключ в порядке приоритета:

1. **config/ai.yaml** → `market_analyst.gpt.api_key`
2. **.env файл** → `OPENAI_API_KEY=sk-proj-...`
3. **Переменные Windows** → System Environment Variables

**Рекомендую:** Использовать `.env` файл (вариант 2)

---

**Готово!** После правильной настройки бот сможет анализировать рынок с помощью GPT-4o ✨

# 📦 BAZA Trading Bot - Инструкция по установке

## 🎯 Требования

- **Windows 10/11** (64-bit)
- **Python 3.12.7** (или выше)
- **MetaTrader 5** установлен и настроен
- **Git** для клонирования репозитория
- **OpenAI API ключ** для GPT-4o (получить на https://platform.openai.com/)

---

## 🚀 Установка (шаг за шагом)

### 1️⃣ Клонировать репозиторий

```powershell
cd C:\Users\ИМЯ_ПОЛЬЗОВАТЕЛЯ\Desktop
git clone https://github.com/vlvdssss/SMC_bot.git BAZA
cd BAZA
```

### 2️⃣ Создать виртуальное окружение

```powershell
python -m venv .venv
```

### 3️⃣ Активировать виртуальное окружение

```powershell
.\.venv\Scripts\Activate.ps1
```

**Если появляется ошибка "script execution is disabled":**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4️⃣ Установить зависимости

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Важно!** Установка займёт 2-5 минут (много ML библиотек).

### 5️⃣ Настроить конфигурацию

#### A. Создать `.env` файл с API ключом

Создай файл `.env` в корне проекта:
```
OPENAI_API_KEY=sk-proj-ВАШ_КЛЮЧ_ОТ_OPENAI
```

#### B. Настроить MT5 credentials

**Вариант 1: Через GUI (рекомендуется)**
1. Запусти бота: `.\.venv\Scripts\python.exe main.py`
2. Нажми **"MT5 Settings"**
3. Введи логин и пароль от MT5
4. Нажми **"Save & Connect"**

**Вариант 2: Вручную**
```powershell
copy config\mt5.yaml.example config\mt5.yaml
```
Отредактируй `config/mt5.yaml`:
```yaml
mt5:
  login: ВАШ_ЛОГИН
  password: "ВАШ_ПАРОЛЬ"
  server: "ИМЯ_СЕРВЕРА"
  timeout: 60000
```

#### C. Настроить Telegram (опционально)

```powershell
copy config\telegram.yaml.example config\telegram.yaml
```

Получи токен у @BotFather в Telegram:
1. Напиши `/newbot` в @BotFather
2. Скопируй токен
3. Получи chat_id у @userinfobot
4. Заполни в `config/telegram.yaml`:

```yaml
telegram:
  bot_token: 'ТОКЕН_ОТ_BOTFATHER'
  chat_id: 'ТВОЙ_CHAT_ID'
  enabled: true
```

### 6️⃣ Запустить бота

```powershell
.\.venv\Scripts\python.exe main.py
```

**⚠️ ВАЖНО:** Всегда запускай через `.venv\Scripts\python.exe`, НЕ через `python`!

---

## 🔧 Режимы работы

### 1. **Strategy + AI** (рекомендуется для начала)
- Стратегия генерирует сигналы (SMC, EMA, RSI)
- GPT фильтрует качество сигналов
- Безопаснее для обучения

### 2. **Pure AI Trading**
- Только GPT-4o Vision анализирует графики
- Автоматические сигналы на основе AI
- Требует опыт и тестирование

---

## 📝 Первый запуск (чек-лист)

- [ ] Python 3.12.7+ установлен
- [ ] Виртуальное окружение создано (`.venv`)
- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] `.env` файл создан с OpenAI ключом
- [ ] MT5 запущен и подключён
- [ ] `config/mt5.yaml` настроен (или через GUI)
- [ ] Бот запущен через `.venv\Scripts\python.exe main.py`
- [ ] MT5 статус показывает **"MT5: Connected"** (зелёный)

---

## 🐛 Частые проблемы

### ❌ "No module named 'bs4'" / "No module named 'openai'"

**Причина:** Запускаешь через системный Python, а не venv.

**Решение:**
```powershell
.\.venv\Scripts\python.exe main.py
```

### ❌ "AI Analysis not available"

**Причина:** Не установлен `beautifulsoup4`.

**Решение:**
```powershell
.\.venv\Scripts\pip.exe install beautifulsoup4
```

### ❌ MT5 не подключается

**Причина:** Неправильные credentials или MT5 не запущен.

**Решение:**
1. Запусти MetaTrader 5
2. Проверь логин/пароль в **MT5 Settings**
3. Проверь имя сервера (Tools → Options → Server)

### ❌ "OpenAI API key not found"

**Причина:** `.env` файл не создан или ключ неправильный.

**Решение:**
1. Создай файл `.env` в корне проекта
2. Добавь строку: `OPENAI_API_KEY=sk-proj-ВАШ_КЛЮЧ`

### ❌ "Settings dialog: type object 'Colors' has no attribute 'INFO'"

**Причина:** Старая версия кода.

**Решение:**
```powershell
git pull origin main
```

---

## 📚 Документация

- [README.md](README.md) - Описание проекта
- [docs/QUICKSTART_SCREENSHOT.md](docs/QUICKSTART_SCREENSHOT.md) - Быстрый старт
- [docs/AI_MARKET_ANALYST.md](docs/AI_MARKET_ANALYST.md) - AI функции
- [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) - Настройка уведомлений
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Тестирование

---

## 🔄 Обновление бота

```powershell
git pull origin main
.\.venv\Scripts\pip.exe install -r requirements.txt --upgrade
```

---

## 💬 Поддержка

- **GitHub Issues**: https://github.com/vlvdssss/SMC_bot/issues
- **Telegram**: @vlvdssss (если настроен)

---

## ⚠️ Важные замечания

1. **Виртуальное окружение обязательно!** Всегда используй `.venv\Scripts\python.exe`
2. **OpenAI API стоит денег** - отслеживай использование на https://platform.openai.com/usage
3. **Начни с демо-счёта MT5** для тестирования
4. **Не торгуй на реальные деньги** без тестирования (минимум 1-2 недели на демо)
5. **Проверяй логи** в `logs/baza_YYYYMMDD.log` при ошибках

---

## 🎉 Готово!

Бот установлен и готов к работе. Начни с режима **Strategy + AI** для обучения, затем переходи на **Pure AI** после тестирования.

**Удачной торговли!** 🚀

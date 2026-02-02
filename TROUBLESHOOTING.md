# 🔧 Решение проблем при установке

## Проблема: "Не удается запустить скрипт" / "execution of scripts is disabled"

### Причина
Windows блокирует выполнение PowerShell скриптов по умолчанию.

### Решение 1 (рекомендуется):
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Решение 2 (запуск напрямую):
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### Решение 3 (используй .bat файл):
Просто двойной клик по `install.bat`

---

## Проблема: "Python не найден" / "python is not recognized"

### Причина
Python не установлен или не добавлен в PATH.

### Решение:
1. Скачай Python 3.9+ с https://www.python.org/downloads/
2. **ОБЯЗАТЕЛЬНО** отметь галочку "Add Python to PATH" при установке
3. Перезапусти PowerShell/CMD
4. Проверь: `python --version`

### Если уже установлен, но не работает:
1. Найди где установлен Python (обычно `C:\Users\<user>\AppData\Local\Programs\Python\`)
2. Добавь в PATH вручную:
   - Windows Search → "Переменные среды"
   - Переменные среды → Path → Изменить
   - Добавить → вставь путь к Python и Python\Scripts

---

## Проблема: "Access denied" / "Отказано в доступе"

### Решение 1 (PowerShell от администратора):
1. Найди PowerShell в меню Пуск
2. ПКМ → "Запуск от имени администратора"
3. Перейди в папку проекта: `cd C:\путь\к\BAZA`
4. Запусти: `.\install.ps1`

### Решение 2 (установка в другую папку):
Скопируй проект в папку без ограничений (например, `C:\Projects\BAZA`)

---

## Проблема: Ошибки при создании venv

### Причина
Модуль venv не установлен или повреждён.

### Решение:
```powershell
# Переустановить Python с галочкой "pip" и "venv"
# Или попробуй:
python -m ensurepip --upgrade
python -m pip install --upgrade pip virtualenv
```

---

## Проблема: pip не устанавливает пакеты

### Timeout ошибки:
```powershell
pip install -r requirements.txt --timeout 300
```

### Проблемы с SSL:
```powershell
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### Отсутствует Microsoft Visual C++:
Некоторые пакеты требуют компилятор:
- Скачай "Microsoft C++ Build Tools" 
- https://visualstudio.microsoft.com/visual-cpp-build-tools/

---

## Проблема: Долгая установка зависимостей

### Это нормально! 
Пакеты машинного обучения (numpy, pandas, scikit-learn, lightgbm) очень большие.

**Среднее время установки:**
- Быстрый интернет: 5-10 минут
- Медленный интернет: 15-30 минут

### Ускорить установку:
```powershell
# Используй бинарные пакеты вместо компиляции
pip install -r requirements.txt --only-binary :all:
```

---

## Проблема: Конфликты версий пакетов

### Решение:
```powershell
# Удали venv и создай заново
Remove-Item -Path .venv -Recurse -Force
.\quick_install.ps1 --clean
```

---

## Проблема: MetaTrader5 не устанавливается

### Для Windows:
```powershell
pip install MetaTrader5 --upgrade
```

### Для Linux/Mac:
MetaTrader5 пакет работает только на Windows через wine или виртуализацию.

---

## Проблема: Telegram bot не работает

### Проверь:
1. Файл `config/telegram.yaml` существует (скопируй из `.example`)
2. Токен правильный (от @BotFather)
3. Chat ID правильный (получи от @userinfobot)

### Тест подключения:
```python
import yaml
from telegram import Bot

with open('config/telegram.yaml') as f:
    config = yaml.safe_load(f)
    
bot = Bot(token=config['bot_token'])
print(bot.get_me())
```

---

## Проблема: OpenAI API не работает

### Проверь:
1. Файл `config/ai.yaml` существует
2. API ключ правильный (от https://platform.openai.com/api-keys)
3. На счету есть деньги
4. Используется правильная модель (gpt-4 или gpt-4-turbo)

### Тест:
```python
import openai
import yaml

with open('config/ai.yaml') as f:
    config = yaml.safe_load(f)

openai.api_key = config['openai_api_key']
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "test"}]
)
print("OK!")
```

---

## Проблема: MT5 не подключается / Ошибка -10003

### Ошибка: "MetaTrader initialization failed: Process create failed"

**Причина:** Бот не может найти MetaTrader 5 на компьютере.

### Решение 1: Найти путь к MT5 автоматически
```powershell
.\find_mt5.ps1
```

Скрипт найдёт MetaTrader 5 и покажет правильный путь.

### Решение 2: Проверить вручную

1. **Найди terminal64.exe:**
   - Обычно в `C:\Program Files\MetaTrader 5\`
   - Или `C:\Program Files (x86)\MetaTrader 5\`
   - Или через поиск Windows

2. **Добавь путь в config/mt5.yaml:**
   ```yaml
   mt5:
     connection:
       path: "C:/Program Files/MetaTrader 5/terminal64.exe"
   ```
   
   ⚠️ Используй `/` (слэш), а не `\` (бэкслэш)!

3. **Или запусти MT5 вручную перед ботом:**
   - Открой MetaTrader 5
   - Войди в аккаунт
   - Запусти бота

### Решение 3: Переустановить MT5

Если MT5 не установлен:
```
https://www.metatrader5.com/en/download
```

После установки:
1. Запусти `.\find_mt5.ps1`
2. Скопируй путь в `config/mt5.yaml`

### Проверка подключения:
```python
import MetaTrader5 as mt5
import yaml

with open('config/mt5.yaml') as f:
    config = yaml.safe_load(f)

path = config['mt5']['connection'].get('path')
if path:
    if not mt5.initialize(path=path):
        print(f"Failed to initialize with path: {path}")
        print(f"Error code: {mt5.last_error()}")
    else:
        print("MT5 connected:", mt5.account_info())
        mt5.shutdown()
else:
    if not mt5.initialize():
        print("Failed to initialize MT5")
        print(f"Error code: {mt5.last_error()}")
    else:
        print("MT5 connected:", mt5.account_info())
        mt5.shutdown()
```

---

## Проблема: MT5 запускается, но не подключается к аккаунту

### Проверь:
1. MetaTrader 5 запущен
2. Логин/пароль/сервер правильные в `config/mt5.yaml`
3. Разрешена автоматическая торговля (Инструменты → Настройки → Алготрейдинг)

---

## Проблема: Отсутствуют конфигурационные файлы

### Решение:
```powershell
# В папке config/ скопируй .example файлы:
cd config
copy mt5.yaml.example mt5.yaml
copy telegram.yaml.example telegram.yaml
copy monitoring.yaml.example monitoring.yaml

# Заполни свои данные в скопированных файлах
```

---

## Полная переустановка (если ничего не помогло)

```powershell
# 1. Удали виртуальное окружение
Remove-Item -Path .venv -Recurse -Force

# 2. Очисти pip cache
pip cache purge

# 3. Обнови pip
python -m pip install --upgrade pip

# 4. Запусти установщик заново
.\install.ps1
```

---

## Всё ещё не работает?

1. Проверь логи в папке `logs/`
2. Запусти с дополнительным логированием:
   ```powershell
   python main.py --debug
   ```
3. Напиши разработчику с описанием проблемы и логами

---

## Полезные команды для диагностики

```powershell
# Версия Python
python --version

# Список установленных пакетов
pip list

# Информация о конкретном пакете
pip show MetaTrader5

# Проверка окружения
Get-Command python
Get-ExecutionPolicy

# Активация venv
.\.venv\Scripts\Activate.ps1

# Деактивация venv
deactivate
```

# 📁 Какой файл использовать?

## Я новичок, что мне делать?

👉 **Двойной клик на `install.bat`** - это всё что нужно!

---

## Я хочу понять что к чему

### Установка:
- **`install.bat`** - Для тех кто не хочет разбираться, просто кликни
- **`install.ps1`** - Полный установщик с диагностикой (рекомендуется)
- **`quick_install.ps1`** - Быстрая установка если знаешь что делаешь

### Проверка:
- **`check_install.ps1`** - Проверить что всё установлено правильно

### Запуск бота:
- **`start_bot.ps1`** - Запустить бота (после установки)
- **`run.ps1`** - Альтернативный способ запуска
- **`main.py`** - Прямой запуск: `python main.py`

### Документация:
- **`START_HERE.md`** - 👈 **НАЧНИ С ЭТОГО** - для друзей
- **`QUICK_START.md`** - Быстрый старт за 5 минут
- **`INSTALL_GUIDE.md`** - Подробная инструкция по установке
- **`TROUBLESHOOTING.md`** - Решение проблем
- **`README.md`** - Полное описание проекта

---

## Сценарии использования

### Сценарий 1: "Я получил проект от друга"
```
1. Открой START_HERE.md
2. Двойной клик на install.bat
3. Настрой config файлы (инструкция в START_HERE.md)
4. Запусти start_bot.ps1
```

### Сценарий 2: "У меня проблемы с установкой"
```
1. Открой TROUBLESHOOTING.md
2. Найди свою проблему
3. Или запусти: .\quick_install.ps1 --clean
4. Проверь: .\check_install.ps1
```

### Сценарий 3: "Я опытный пользователь"
```powershell
.\quick_install.ps1
# настрой config/
.\check_install.ps1
python main.py
```

### Сценарий 4: "Хочу обновить зависимости"
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

### Сценарий 5: "Нужна переустановка"
```powershell
.\quick_install.ps1 --clean
```

---

## Быстрая навигация

| Задача | Файл/Команда |
|--------|--------------|
| 🆕 Первая установка | `install.bat` или `.\install.ps1` |
| ⚡ Быстрая установка | `.\quick_install.ps1` |
| ✅ Проверка | `.\check_install.ps1` |
| 🚀 Запуск бота | `.\start_bot.ps1` |
| 📖 Инструкция для друга | `START_HERE.md` |
| 🔧 Решение проблем | `TROUBLESHOOTING.md` |
| 📚 Детальная документация | `README.md` |
| ⏱️ Быстрый старт | `QUICK_START.md` |
| 🔄 Переустановка | `.\quick_install.ps1 --clean` |
| 📝 Что нового | `CHANGELOG.md` |

---

## Структура документации

```
BAZA/
├── START_HERE.md              ← 👈 Начни здесь (для друзей)
├── QUICK_START.md             ← Быстрый старт (5 мин)
├── INSTALL_GUIDE.md           ← Подробная установка
├── TROUBLESHOOTING.md         ← Решение проблем
├── README.md                  ← Описание проекта
├── CHANGELOG.md               ← История изменений
│
├── install.bat                ← Двойной клик установка
├── install.ps1                ← Полный установщик
├── quick_install.ps1          ← Быстрая установка
├── check_install.ps1          ← Проверка установки
├── start_bot.ps1              ← Запуск бота
│
└── docs/                      ← Детальная документация
    ├── INSTALLATION_FILES.md  ← Описание установочных файлов
    ├── AI_SCHEDULE_GUIDE.md   ← Настройка AI
    ├── LOT_SIZE_GUIDE.md      ← Управление лотом
    └── ...                    ← Другие гайды
```

---

## Рекомендуемый порядок чтения

### Для новичков:
1. **START_HERE.md** - прочитай это первым
2. **INSTALL_GUIDE.md** - если нужны детали
3. **TROUBLESHOOTING.md** - если возникли проблемы
4. **QUICK_START.md** - краткая шпаргалка

### Для опытных:
1. **README.md** - обзор проекта
2. **QUICK_START.md** - команды и настройки
3. **docs/** - детальные гайды по функциям

---

## FAQ

**Q: Какой файл запускать для установки?**  
A: `install.bat` (двойной клик) или `.\install.ps1` (PowerShell)

**Q: Где настройки бота?**  
A: В папке `config/` - скопируй `.example` файлы

**Q: Как проверить что всё работает?**  
A: Запусти `.\check_install.ps1`

**Q: Бот не запускается, что делать?**  
A: Открой `TROUBLESHOOTING.md` и найди свою проблему

**Q: Как обновить зависимости?**  
A: `pip install -r requirements.txt --upgrade`

**Q: Как переустановить всё с нуля?**  
A: `.\quick_install.ps1 --clean`

**Q: Где логи?**  
A: В папке `logs/`

**Q: Как отправить проект другу?**  
A: Отправь папку и скажи открыть `START_HERE.md`

---

## Полезные команды (шпаргалка)

```powershell
# Установка
.\install.ps1                    # Полная
.\quick_install.ps1              # Быстрая
.\quick_install.ps1 --clean      # С очисткой

# Проверка
.\check_install.ps1              # Проверка установки
python --version                 # Версия Python
pip list                         # Список пакетов

# Запуск
.\start_bot.ps1                  # Запуск бота
python main.py                   # Прямой запуск

# Работа с venv
.\.venv\Scripts\Activate.ps1     # Активация
deactivate                       # Деактивация

# Обслуживание
pip install -r requirements.txt --upgrade  # Обновить всё
pip cache purge                  # Очистить кэш
Remove-Item .venv -Recurse       # Удалить venv

# Логи
Get-Content logs\baza_*.log -Tail 50     # Последние 50 строк
Get-Content logs\baza_*.log -Wait        # Мониторинг
```

---

## Цветовая маркировка важности

🟢 **Обязательно для начала:**
- START_HERE.md
- install.bat / install.ps1
- check_install.ps1

🟡 **Полезно знать:**
- QUICK_START.md
- INSTALL_GUIDE.md
- TROUBLESHOOTING.md

🔵 **Для продвинутых:**
- docs/INSTALLATION_FILES.md
- docs/AI_SCHEDULE_GUIDE.md
- docs/LOT_SIZE_GUIDE.md

---

**Не знаешь с чего начать? → Открой `START_HERE.md` 👈**

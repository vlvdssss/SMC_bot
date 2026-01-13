# 🚀 Быстрый старт: Система обновлений

## Для разработчика (выпуск новой версии)

### 1. Измените версию
```python
# version.py
APP_VERSION = "1.1.0"  # Было 1.0.0
```

### 2. Соберите EXE
```bash
python build_exe.py
```

### 3. Создайте GitHub Release
- Tag: `v1.1.0`
- Загрузите: `BAZA_TradingBot_v1.1.0.exe`

### 4. Обновите version.json
```json
{
  "latest_version": "1.1.0",
  "download_url": "https://github.com/USER/REPO/releases/download/v1.1.0/BAZA_TradingBot_v1.1.0.exe",
  "size_mb": 218,
  "changelog": [
    "Новая фича",
    "Исправлен баг"
  ]
}
```

### 5. Закоммитьте version.json
```bash
git add version.json
git commit -m "Release v1.1.0"
git push
```

✅ Готово! Пользователи могут обновиться.

---

## Для пользователя

### Как обновить бот?

1. Запустите BAZA Trading Bot
2. Нажмите кнопку **"🔄 Проверить обновления"**
3. Если доступно обновление - нажмите **"Обновить"**
4. Дождитесь загрузки (показывается прогресс-бар)
5. Нажмите **"Перезапустить"**

🎉 Бот обновлен и перезапущен!

---

## Структура файлов

```
BAZA/
├── version.py                    # APP_VERSION = "1.0.0"
├── updater/                      # Модуль обновлений
│   ├── update_checker.py        # Проверка версий
│   ├── downloader.py            # Загрузка EXE
│   └── ui_update_window.py      # Окно обновления
└── version.json.example          # Шаблон для GitHub
```

---

## FAQ

**Q: Почему не перезаписывается текущий EXE?**  
A: Windows блокирует запущенные файлы. Мы загружаем с другим именем.

**Q: Где хранится version.json?**  
A: На GitHub в корне репозитория (`main` branch).

**Q: Нужен ли интернет для обновления?**  
A: Да, для проверки и загрузки.

**Q: Что делать если антивирус блокирует?**  
A: Добавьте папку BAZA в исключения антивируса.

---

📖 **Полная документация**: См. [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md)

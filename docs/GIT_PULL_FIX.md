# 🔧 Исправление проблемы Git Pull

## Проблема
При выполнении `git pull` появляется ошибка:
```
error: Your local changes to the following files would be overwritten by merge:
    config/trading.yaml
    data/ai_signals/active_signals.json
Please commit your changes or stash them before you merge.
```

## Причина
Git трекает конфиг файлы, которые изменяются локально во время работы бота.

## Решение

### Вариант 1: Автоматическое исправление (РЕКОМЕНДУЕТСЯ)

Запустите ОДИН РАЗ:
```powershell
.\fix_git_tracking.ps1
```

Этот скрипт:
- ✅ Удалит config файлы из Git (останутся локально)
- ✅ Создаст коммит с исправлениями
- ✅ Спросит о push на GitHub

### Вариант 2: Безопасное обновление

Вместо `git pull` используйте:
```powershell
.\update.ps1
```

Этот скрипт автоматически:
1. 💾 Сохранит ваши изменения (stash)
2. 📥 Загрузит обновления (pull)
3. 🔄 Восстановит ваши изменения (stash pop)

### Вариант 3: Ручное исправление

```powershell
# Сохранить изменения
git stash

# Обновить
git pull --rebase

# Восстановить
git stash pop
```

## Для друга на другом компьютере

1. **Установи Git** (если еще не установлен):
   - Скачай: https://git-scm.com/download/win
   - Установи с настройками по умолчанию

2. **Клонируй репозиторий**:
   ```powershell
   git clone https://github.com/vlvdssss/SMC_bot.git BAZA
   cd BAZA
   ```

3. **Настрой Git** (ВАЖНО!):
   ```powershell
   git config pull.rebase false
   git config core.autocrlf true
   ```

4. **При обновлении всегда используй**:
   ```powershell
   .\update.ps1
   ```

## Что делать при конфликтах

Если после `git stash pop` есть конфликты:

```powershell
# Посмотреть конфликтные файлы
git status

# Вариант 1: Оставить свои изменения
git checkout --ours config/trading.yaml

# Вариант 2: Взять новые изменения
git checkout --theirs config/trading.yaml

# Вариант 3: Отменить все и начать заново
git reset --hard HEAD
git stash drop
git pull
```

## Файлы которые НЕ трекаются

Эти файлы изменяются во время работы бота и НЕ должны синхронизироваться:
- `config/trading.yaml`
- `config/ai.yaml`
- `config/portfolio.yaml`
- `config/monitoring.yaml`
- `config/telegram.yaml`
- `data/**/*.json`
- `logs/**/*.log`

## Настройка для нового пользователя

После клонирования скопируйте примеры:
```powershell
copy config\mt5.yaml.example config\mt5.yaml
copy config\telegram.yaml.example config\telegram.yaml
```

Затем отредактируйте свои учетные данные в:
- `config/mt5.yaml` - MT5 логин/пароль
- `config/telegram.yaml` - Telegram токен/чат

Эти файлы останутся локальными и не будут синхронизироваться!

## Автоматизация

Добавьте в PowerShell профиль alias для быстрого обновления:

```powershell
# Открыть профиль
notepad $PROFILE

# Добавить строку
Set-Alias -Name update-baza -Value C:\Users\<USER>\Desktop\BAZA\update.ps1
```

Теперь можно обновлять просто командой:
```powershell
update-baza
```

## Получить последнюю версию (force update)

Если совсем все сломалось:

```powershell
# Сохранить конфиги
copy config C:\temp\baza_config_backup -Recurse

# Жёсткий reset
git fetch origin
git reset --hard origin/main

# Восстановить конфиги
copy C:\temp\baza_config_backup\* config\
```

⚠️ **ВНИМАНИЕ:** Это удалит ВСЕ локальные изменения!

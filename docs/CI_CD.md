# CI/CD и Современная Конфигурация Проекта

## 📦 pyproject.toml

Проект теперь использует современный стандарт конфигурации Python через `pyproject.toml` (PEP 518, 621).

### Основные секции

#### `[project]`
- **Метаданные**: имя, версия, описание, авторы
- **Зависимости**: все основные пакеты для работы бота
- **Python**: требуется >= 3.9

#### `[project.optional-dependencies]`
- **dev**: pytest, black, flake8, mypy для разработки
- **build**: pyinstaller для сборки exe

#### `[tool.pytest.ini_options]`
- Конфигурация pytest из `pytest.ini` перенесена сюда
- Маркеры для категоризации тестов
- Настройки запуска

#### `[tool.black]`
- Автоматическое форматирование кода
- Длина строки: 100 символов
- Совместимость с Python 3.9-3.12

#### `[tool.flake8]`
- Проверка стиля кода (PEP 8)
- Игнорирование конфликтов с black (E203, W503)

#### `[tool.mypy]`
- Статическая типизация
- Игнорирование отсутствующих типов для сторонних библиотек

### Установка проекта

```bash
# Установка в режиме разработки
pip install -e .

# Установка с dev-зависимостями
pip install -e ".[dev]"

# Установка с build-зависимостями
pip install -e ".[build]"
```

---

## 🚀 GitHub Actions CI/CD

Создан workflow `.github/workflows/tests.yml` для автоматического тестирования.

### Когда запускается

- **Push** в ветки `main` или `develop`
- **Pull Request** в эти ветки
- **Вручную** через GitHub UI (workflow_dispatch)

### Jobs

#### 1. `test` - Тестирование
Матричная сборка для проверки совместимости:
- **OS**: Ubuntu, Windows
- **Python**: 3.9, 3.10, 3.11, 3.12
- Всего: **8 комбинаций**

**Шаги:**
1. Checkout кода
2. Установка Python
3. Установка зависимостей (`pip install -e ".[dev]"`)
4. Запуск pytest с покрытием кода
5. Отправка coverage в Codecov (опционально)

#### 2. `lint` - Проверка качества кода
- **Black**: форматирование кода
- **Flake8**: проверка стиля (PEP 8)
- **Mypy**: статическая типизация

**Примечание:** Ошибки линтинга не блокируют CI (`continue-on-error: true`)

### Codecov (опционально)

Для отчетов о покрытии кода:
1. Зарегистрируйтесь на [codecov.io](https://codecov.io)
2. Добавьте репозиторий
3. Создайте токен в настройках Codecov
4. Добавьте секрет `CODECOV_TOKEN` в настройки репозитория GitHub

---

## 🔧 Pre-commit Hooks

Файл `.pre-commit-config.yaml` настраивает автоматические проверки перед коммитом.

### Установка

```bash
# Установка pre-commit
pip install pre-commit

# Установка hooks в репозиторий
pre-commit install
```

### Что проверяется

1. **Базовые проверки**:
   - Удаление пробелов в конце строк
   - Пустая строка в конце файлов
   - Валидация YAML, JSON, TOML
   - Проверка больших файлов (>1MB)
   - Поиск конфликтов слияния
   - Поиск debug statements

2. **Black**: автоформатирование кода

3. **Flake8**: проверка стиля

4. **isort**: сортировка импортов

5. **Mypy**: проверка типов

### Запуск вручную

```bash
# Проверить все файлы
pre-commit run --all-files

# Проверить конкретные файлы
pre-commit run --files src/core/bot_manager.py
```

---

## 📊 Команды разработчика

### Тестирование

```bash
# Все тесты
pytest tests/ -v

# С покрытием
pytest tests/ --cov=src --cov-report=html

# Конкретная категория
pytest tests/ -v -m unit
pytest tests/ -v -m strategy
```

### Форматирование

```bash
# Проверить форматирование
black --check src/ tests/

# Применить форматирование
black src/ tests/
```

### Линтинг

```bash
# Критические ошибки
flake8 src/ tests/ --select=E9,F63,F7,F82

# Все проверки
flake8 src/ tests/ --max-line-length=100
```

### Типизация

```bash
# Проверка типов
mypy src/
```

---

## 🎯 Преимущества

### pyproject.toml
✅ Единый файл конфигурации для всех инструментов  
✅ Стандарт PEP 518/621  
✅ Упрощенная установка (`pip install -e .`)  
✅ Четкое разделение dev/prod зависимостей

### GitHub Actions
✅ Автоматическое тестирование на каждый push  
✅ Проверка совместимости с разными версиями Python  
✅ Проверка на Windows и Linux  
✅ Отчеты о покрытии кода

### Pre-commit
✅ Автоматическая проверка перед коммитом  
✅ Единый стиль кода в команде  
✅ Меньше ошибок в PR  
✅ Экономия времени на код-ревью

---

## 🔄 Миграция с requirements.txt

Старый `requirements.txt` все еще работает, но рекомендуется использовать:

```bash
# Вместо
pip install -r requirements.txt

# Используйте
pip install -e ".[dev]"
```

Файл `requirements.txt` можно оставить для обратной совместимости или сгенерировать:

```bash
pip freeze > requirements.txt
```

---

## 📝 Следующие шаги

1. **Отправьте код в GitHub**:
   ```bash
   git add .
   git commit -m "Add CI/CD and pyproject.toml"
   git push origin main
   ```

2. **Проверьте GitHub Actions**:
   - Откройте вкладку "Actions" в репозитории
   - Убедитесь, что все тесты проходят

3. **Настройте Codecov** (опционально):
   - Добавьте токен в секреты
   - Получайте отчеты о покрытии

4. **Установите pre-commit**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

5. **Добавьте бейджи в README**:
   ```markdown
   ![Tests](https://github.com/yourusername/baza-trading-bot/workflows/Tests/badge.svg)
   ![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
   ```

---

## ⚠️ Примечания

- **MetaTrader5** не устанавливается на Linux - тесты с MT5 будут пропущены на Ubuntu
- **Линтинг** настроен с `continue-on-error: true` - не блокирует CI
- **Pre-commit** можно пропустить с флагом `--no-verify` при коммите
- **pyproject.toml** заменяет `pytest.ini`, `setup.py`, `setup.cfg`

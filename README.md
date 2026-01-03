# 🤖 BAZA Trading Bot v1.2.0

Автоматическая торговая система на основе Smart Money Concepts (SMC).

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)
![Version](https://img.shields.io/badge/Version-1.2.0-blue.svg)

---

## 📚 Документация

**📖 [Полная документация](docs/README.md)** - структурированная документация всего проекта

### Быстрые ссылки:
- 🚀 [Установка и запуск](#-запуск)
- 📊 [Результаты бэктеста](#-результаты-бэктеста-2023-2025)
- 🤖 [AI функции](docs/QUICKSTART_SCREENSHOT.md)
- 💼 [Ручная торговля](MANUAL_TRADING_README.md)
- 🏗️ [Архитектура](ARCHITECTURE_2.0.md)
- 🐛 [История изменений](docs/BUGFIXES.md)

---

## 🚀 Запуск

### Вариант 1: Python
```bash
python main.py
```

### Вариант 2: EXE файл
```bash
# Сборка exe
python build_exe.py

# Запуск
dist/BAZA.exe
```

### Бэктест
```bash
python main.py --backtest --year 2024
```

---

## �💰 Поддержка проекта

Этот проект является результатом **4 месяцев** интенсивной разработки и тестирования. Если код оказался полезным:

### 📧 Связаться с разработчиком
**Email**: kamsaaaimpa@gmail.com

По всем вопросам: лицензии, поддержка, коммерческое использование, предложения.

---

## 📊 Результаты бэктеста (2023-2025)

| Год | XAUUSD ROI | EURUSD ROI | Portfolio ROI | Max DD |
|-----|------------|------------|---------------|--------|
| 2023 | 42.5% | 285.3% | 163.9% | 18.5% |
| 2024 | 45.86% | 340.75% | 193.31% | 20.8% |
| 2025 | 48.2% | 52.8% | 50.5% | 16.8% |
| **AVG** | **45.5%** | **226%** | **136%** | **18.7%** |

✅ Все годы прибыльные
✅ Max Drawdown < 25%
✅ Стабильность подтверждена

---

## � Быстрый старт

### Установка зависимостей:
```bash
pip install -r requirements.txt
```

## 📦 Установка

```bash
pip install -r requirements.txt
```

### 🤖 Настройка GPT фильтра (опционально)

GPT фильтр проверяет экономические новости перед открытием сделок.

### 🆕 NEW: AI Analyst с анализом скриншотов! 📸

**Загружайте скриншоты графиков MT5 прямо в чат с AI аналитиком!**

- 📊 Детальный технический анализ графиков
- 🎯 Определение трендов и паттернов
- 📈 Рекомендации по точкам входа/выхода
- ⚠️ Оценка рисков

**Подробнее:** [AI_SCREENSHOT_ANALYSIS.md](AI_SCREENSHOT_ANALYSIS.md)

---

### Настройка GPT

1. **Получите API ключ OpenAI:**
   - Перейдите на [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Создайте новый API ключ

2. **Настройте ключ:**
   - Скопируйте `.env.example` в `.env`
   - Добавьте ваш ключ: `OPENAI_API_KEY=your_key_here`
   
   Или используйте GUI: `python main.py` → ⚙ Настройки

3. **Установите дополнительные зависимости:**
   ```bash
   pip install openai python-dotenv
   ```

**Стоимость:** 
- GPT-4o-mini (фильтр новостей): ~$0.001 за запрос
- GPT-4o (анализ скриншотов): ~$0.01-0.03 за запрос

## 🎮 Использование

### GUI приложение (по умолчанию):
```bash
python main.py
```

### Бэктест:
```bash
python main.py --backtest --year 2024
```

### Сборка exe:
```bash
pip install pyinstaller
python build_exe.py
# Результат: dist/BAZA.exe
```

### 🤖 AI GPT Фильтр новостей:
- **Умный анализ** экономических событий через GPT-4o-mini
- **Автоматическая оценка риска**: LOW/MEDIUM/HIGH/EXTREME
- **Динамическое управление рисками**: уменьшение размера позиций при высокой волатильности
- **Блокировка сигналов**: пропуск торговли во время major news (FOMC, NFP, ECB)
- **Кэширование**: анализ обновляется каждый час для экономии API
- **Стоимость**: ~$0.001 за запрос (дешёвый GPT-4o-mini)

### Как получить лицензию:
1. Напиши на **kamsaaaimpa@gmail.com** с темой "Лицензия BAZA"
2. Укажи: email, срок (месяц/год), метод оплаты (PayPal)
3. Получи персональный лицензионный ключ в ответ

### Преимущества платной лицензии:
- ✅ Неограниченная live торговля
- ✅ Обновления и поддержка
- ✅ Приоритетная помощь

---

## 🚀 Быстрый старт

## 🚀 Быстрый старт

### Установка
```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/BAZA.git
cd BAZA

# Установить зависимости
pip install -r requirements.txt

# Или установить как пакет
pip install -e .
```

### Настройка
```bash
# Скопировать пример конфига
cp config/mt5.yaml.example config/mt5.yaml

# Отредактировать свои данные MT5
nano config/mt5.yaml
```

### Запуск
```bash
# Демо режим (мониторинг без торговли) - БЕСПЛАТНО
python main.py --mode demo

# Бэктест - БЕСПЛАТНО
python main.py --mode backtest --year 2024

# Бэктест портфеля - БЕСПЛАТНО
python main.py --mode backtest --year 2024 --portfolio

# Live торговля (осторожно!) - ТРЕБУЕТСЯ ЛИЦЕНЗИЯ или ПРОБНЫЙ ПЕРИОД
python main.py --mode live
```

### Как вставить лицензию:
После запуска live режима:
1. Введите лицензионный ключ (купленный)
2. Или введите "TRIAL" для бесплатного пробного периода (3 дня)
3. Бот активируется и начнёт торговлю

---

## 📁 Структура проекта
```
BAZA/
├── main.py              # 🚀 Главный файл запуска
├── requirements.txt     # 📦 Зависимости
├── README.md            # 📖 Документация
├── LICENSE              # 📜 Proprietary License
│
├── config/              # ⚙️ Настройки
│   ├── mt5.yaml.example     # Пример конфига MT5
│   ├── instruments.yaml     # Параметры инструментов
│   └── portfolio.yaml       # Настройки портфеля
│
├── src/                 # 💻 Исходный код
│   ├── strategies/          # Торговые стратегии
│   ├── core/                # Ядро системы
│   ├── mt5/                 # MT5 интеграция
│   ├── backtest/            # Бэктестирование
│   └── live/                # Live торговля
│
├── data/                # 📈 Данные (не в Git)
├── results/             # 📋 Результаты (не в Git)
└── logs/                # 📝 Логи (не в Git)
```

## Стратегии

### XAUUSD (Золото)

Тип: SMC Trend Following
Таймфреймы: H1 + M15
Risk: 0.75% на сделку
Avg ROI: 45.5% годовых
Стабильность: ±5% между годами

### EURUSD

Тип: SMC Retracement
Таймфреймы: H1 + M15
Risk: 0.5% на сделку
Avg ROI: 226% годовых
Стабильность: ±55% между годами

### Portfolio

Инструменты: XAUUSD + EURUSD
Max Exposure: 1.25%
Avg ROI: 136% годовых
Max DD: < 21%

---

## ⚙️ Конфигурация

### config/mt5.yaml.example
```yaml
mt5:
  connection:
    login: YOUR_LOGIN
    password: "YOUR_PASSWORD"
    server: "YOUR_BROKER_SERVER"
    path: "C:/Program Files/MetaTrader 5/terminal64.exe"
    
  settings:
    enable_trade: false  # true для реальной торговли
    
  safety:
    max_lot_size: 1.0
    max_daily_loss_percent: 5.0
```

### config/instruments.yaml
```yaml
XAUUSD:
  risk_per_trade: 0.75
  max_daily_trades: 2
  
EURUSD:
  risk_per_trade: 0.5
  max_daily_trades: 2
```

---

## 🔧 Требования

- Python 3.9+
- MetaTrader 5 (Windows или Wine на Linux)
- 4GB RAM минимум
- Стабильное интернет-соединение

---

## ⚠️ Дисклеймер

**Торговля на финансовых рынках связана с высоким риском.**

- Прошлые результаты НЕ гарантируют будущих
- Не инвестируй больше, чем можешь потерять
- Сначала тестируй на демо минимум 4-8 недель
- Автор не несёт ответственности за финансовые потери

---

## 📝 Changelog

### v1.0.0 (Декабрь 2025)
- ✅ Стабилизированные стратегии XAUUSD и EURUSD
- ✅ Портфельный бэктест
- ✅ MT5 интеграция
- ✅ Реалистичный бэктестер (slippage, spread, commission)
- ✅ Готово к демо торговле

---

## � Контрибуция

**Хочешь улучшить BAZA?** Присоединяйся к разработке!

### Как помочь:
- 🐛 Найти и исправить баги
- ✨ Добавить новые стратегии
- 📊 Улучшить аналитику результатов
- 🌐 Перевести на другие языки
- 📚 Написать документацию

### Связаться:
**Email**: kamsaaaimpa@gmail.com

Опиши свои идеи, опыт и как хочешь помочь. Все контрибьюторы приветствуются! 🤝

Подробные инструкции: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## ⚙️ Настройка GPT фильтра новостей

### 1. Получите OpenAI API ключ
Перейдите на [platform.openai.com/api-keys](https://platform.openai.com/api-keys) и создайте новый ключ.

### 2. Настройте переменные окружения
```bash
# Скопируйте пример
cp config/.env.example config/.env

# Вставьте ваш API ключ в config/.env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Установите зависимости
```bash
pip install openai python-dotenv
```

### 4. Протестируйте фильтр
```bash
python test_gpt_filter.py
```

### 5. Запустите бота с AI
```bash
python main.py --mode demo  # GPT фильтр активен
```

**Стоимость**: ~$0.001 за запрос (GPT-4o-mini). Примерно $0.72 в месяц при активной торговле.

---

## 📄 Лицензия

**Proprietary License** - Все права защищены.

- ✅ Личное использование для бэктестинга и демо торговли
- ❌ Коммерческое использование без разрешения
- ❌ Продажа или распространение кода

Для коммерческого использования свяжитесь с автором.

---

## 💰 Поддержка

Если проект оказался полезным, поддержи разработчика:
**Email**: kamsaaaimpa@gmail.com

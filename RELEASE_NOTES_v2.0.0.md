# 🚀 BAZA Trading Bot v2.0.0 - GPT Decision Engine Event-Driven

## 🎯 MAJOR RELEASE: Event-Driven Architecture

Полная переработка архитектуры бота на **event-driven** модель. Вместо расписания (cron schedule) теперь используются **события** для запуска анализа.

---

## ⚡ КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ

### 🔄 GPT Decision Engine v2.0
- **Event-Driven Architecture**: Анализ запускается по событиям, а не по расписанию
- **TTL System**: Каждый сигнал имеет TTL (Time To Live) = 60 минут по умолчанию
- **Auto-Requery**: Автоматический запрос нового анализа при истечении TTL или закрытии позиции
- **Position-Based Triggers**: Закрытие позиции → Автоматический запрос нового анализа

### 🧹 Schedule Removed (300+ строк удалено)
- ❌ Удалён **Schedule Tab** из GUI
- ❌ Удалены все методы планирования: `_create_schedule_tab()`, `_add_time()`, `_remove_time()`, etc.
- ✅ Чистая event-driven логика без cron

### 📰 Live News Feed
- **TODAY'S HIGH-IMPACT NEWS**: Real-time новости из Trading Economics API
- Показывает до **5 HIGH/EXTREME** новостей сегодня
- Формат: **Время | Валюта | Impact Badge | Заголовок**
- Счётчик всех высокоимпактных событий дня
- **Заменил Market Bias** (который был удалён)

### 🛠️ Settings Dialog: TTL Controls
**AI Tab** теперь содержит 3 новых контрола:
1. **Signal TTL (minutes)**: Время жизни сигнала (по умолчанию 60 мин)
2. **Auto-requery on expire** ☑️: Автоматический запрос при истечении TTL
3. **Auto-requery on close** ☑️: Автоматический запрос при закрытии позиции

---

## 🐛 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ

### ✅ TTL Config Path (MAJOR BUG)
- **Было**: TTL читался из `ai.yaml.signals.validity_minutes` ❌
- **Стало**: TTL читается из `trading.yaml.signal_ttl.ttl_minutes` ✅
- **Результат**: Настройки TTL теперь сохраняются и загружаются корректно

### ✅ API Key Loading
- **Было**: API ключ не загружался из `.env` ❌
- **Стало**: `load_dotenv(override=True)` с приоритетом `.env` файлу ✅
- **Результат**: OpenAI API ключ всегда загружается из `.env`

### ✅ Import Errors (3 файла)
- **Исправлено**: `test_news_parser.py`, `test_news_tomorrow.py`, `test_ttl_logic.py`
- **Было**: Относительные импорты с неправильным `sys.path` ❌
- **Стало**: Абсолютные импорты `from src.*` ✅
- **Результат**: Pylance: 0 ошибок, правильное разрешение модулей

### ✅ Settings Save Method
- **Исправлено**: `_save_settings()` больше не обращается к удалённым переменным Schedule
- **Было**: `self.schedule_enabled.get()` вызывал AttributeError ❌
- **Стало**: Hardcoded `schedule.enabled = False`, `schedule.times = []` ✅
- **Результат**: Настройки сохраняются без ошибок

---

## 📊 ARCHITECTURE IMPROVEMENTS

### Event-Driven Flow
```
┌─────────────────────────────────────────┐
│  СОБЫТИЯ (Triggers)                     │
├─────────────────────────────────────────┤
│  • Истечение TTL (60 мин)               │
│  • Закрытие позиции                     │
│  • Ручной запрос анализа (Manual)       │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  GPT DECISION ENGINE                    │
├─────────────────────────────────────────┤
│  1. GPT-4o Vision Screenshot Analysis   │
│  2. Technical Indicators (SMC, EMA, RSI)│
│  3. News Integration (High Impact)      │
│  4. Signal Generation with TTL          │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  SIGNAL LIFECYCLE                       │
├─────────────────────────────────────────┤
│  • Created: TTL = 60 min                │
│  • Active: Displayed in GUI             │
│  • Expired: Auto-requery (if enabled)   │
│  • Archived: Moved to history           │
└─────────────────────────────────────────┘
```

### Signal TTL System
- **TTL Minutes**: Configurable (default 60)
- **Auto-Requery on Expire**: Boolean toggle
- **Auto-Requery on Close**: Boolean toggle
- **TTL Enabled**: Master switch

---

## 📁 SETTINGS VERIFICATION

### ✅ Все 6 вкладок работают корректно (47 настроек):

1. **Instruments Tab**: XAUUSD, EURUSD (enabled, analysis_enabled, trading_enabled)
2. **Trading Tab**: Risk, Trailing Stop, Trading Hours
3. **AI Tab**: Model, Temperature, Filters, **TTL (3 controls)**, Time Restrictions
4. **Strategy Tab**: Timeframes, Indicators (EMA, RSI, ATR), SMC, Trend Filter
5. **GPT API Tab**: API Key → `.env`
6. **Telegram Tab**: All Notify Settings

### Config Files:
- `ai.yaml`: 9 настроек
- `trading.yaml`: 21 настройка (включая **4 TTL** ✨)
- `portfolio.yaml`: 1 настройка
- `instruments.yaml`: 6 настроек
- `telegram.yaml`: 10 настроек
- `.env`: OPENAI_API_KEY

---

## 🧪 TESTING

### ✅ Test Suite Passed
- **test_ttl_logic.py**: 4/4 tests ✅
  - Expired signal detection
  - Expired signal removal
  - Fresh signal validation
  - Fresh signal persistence

### ✅ Import Validation
- All Pylance errors: **0** ✅
- Settings import: **OK** ✅
- Module resolution: **Correct** ✅

---

## 📦 RELEASE INFO

- **Version**: 2.0.0
- **Date**: 2026-01-22
- **EXE Size**: 206.2 MB
- **Python**: 3.12.7
- **Platform**: Windows x64

---

## 🔧 MIGRATION GUIDE

### From v1.3.2 → v2.0.0

1. **No Schedule Tab**: Вкладка "Schedule" удалена из Settings
2. **TTL Settings**: Новые настройки в AI Tab (Signal TTL section)
3. **Auto-Requery**: По умолчанию включено (можно отключить в Settings)
4. **News Feed**: Заменяет Market Bias в GUI
5. **API Key**: Всегда берётся из `.env` (не из системных переменных)

### Config Updates:
```yaml
# trading.yaml - NEW SECTION
signal_ttl:
  ttl_minutes: 60
  auto_requery_on_expire: true
  auto_requery_on_close: true
  enabled: true

# ai.yaml - ENFORCED
market_analyst:
  schedule:
    enabled: false  # Hardcoded
    times: []       # Hardcoded
```

---

## 🎉 CREDITS

**GPT Decision Engine v2.0** - полная переработка архитектуры бота с фокусом на:
- Event-driven logic (вместо schedule)
- Smart signal lifecycle (TTL + auto-requery)
- Real-time news integration (Trading Economics)
- Clean codebase (300+ строк мёртвого кода удалено)

---

## 📥 DOWNLOAD

**BAZA_TradingBot.exe** - [Download from Releases](https://github.com/vlvdssss/SMC_bot/releases/tag/v2.0.0)

**Size**: 206.2 MB  
**SHA256**: `<будет добавлен после загрузки>`

---

## 🐛 KNOWN ISSUES

None. All critical bugs from v1.3.2 fixed.

---

## 📚 DOCUMENTATION

- [README.md](../README.md)
- [AI_MARKET_ANALYST.md](../docs/AI_MARKET_ANALYST.md)
- [TELEGRAM_SETUP.md](../docs/TELEGRAM_SETUP.md)
- [TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)

---

## 💬 SUPPORT

Issues: https://github.com/vlvdssss/SMC_bot/issues  
Telegram: [Your Telegram]

---

**Enjoy BAZA Trading Bot v2.0.0!** 🚀

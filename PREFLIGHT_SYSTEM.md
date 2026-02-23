# Pre-Flight Check System для 5-Day Production Run

## 📋 Обзор

Система Pre-Flight Checks обеспечивает полную готовность бота к production run перед запуском.

## ✨ Новые возможности

### 1. Pre-Flight Check Module
**Файл**: `src/core/preflight_checks.py`

Проверяет:
- ✅ MT5 соединение и account info
- ✅ GPT API доступность и конфигурацию
- ✅ Telegram bot настройки
- ✅ Config conflicts (0 conflicts required)
- ✅ TradeFilters читают trading.yaml
- ✅ Валидация критических параметров

### 2. Enhanced BotStatus
**Файл**: `src/core/bot_manager.py`

Новые статусы:
- `WAITING` - бот ожидает следующий анализ
- `ANALYZING` - GPT анализ в процессе
- `BLOCKED` - сделка заблокирована фильтрами
- `ORDERING` - размещение ордера в MT5
- `ERROR` - состояние ошибки

### 3. Run Session Manager
**Файл**: `src/core/run_session_manager.py`

Расширен методом `save_run_config()` для сохранения:
- `run_effective_config_start.yaml` - baseline конфигурация
- `preflight_report.json` - результаты проверок

Структура папки прогона:
```
data/runs/run_YYYYMMDD_HHMMSS/
├── run_effective_config_start.yaml  # ← NEW
├── preflight_report.json            # ← NEW
├── run_state.json
├── run_events.jsonl
└── decision_logs.jsonl (copy)
```

### 4. NOW Status Dashboard
**Файл**: `src/gui/app_v2.py` → ControlPanel

Отображает в реальном времени:
- **Bot Status**: STOPPED/WAITING/ANALYZING/BLOCKED/ORDERING/ERROR
- **Active Signal**: BUY/SELL + confidence + age
- **Block Reason**: причина блокировки
- **Cooldown**: оставшееся время cooldown
- **Next Check**: таймер до следующего анализа
- **Last Decision**: краткое резюме последнего решения

### 5. UI Buttons

#### ✈️ Pre-Flight Check
Запускает все acceptance checks:
- MT5 connection
- GPT API
- Telegram bot
- Config validation

Показывает диалог с результатами и критическими параметрами.

#### 📱 Test Telegram
Проверяет Telegram bot конфигурацию без отправки сообщения.

### 6. Acceptance Checks при START

При нажатии `▶ START BOT` автоматически:
1. ✅ Запускает Pre-Flight checks
2. ⚠️ Блокирует старт если checks failed
3. ⚠️ Показывает warning для LIVE mode
4. ✅ Экспортирует effective config в run folder
5. ✅ Создаёт новую run session
6. ✅ Логирует ключевые параметры

## 🚀 Использование

### Quick Test: Pre-Flight Checks
```powershell
cd C:\Users\kamsa\OneDrive\Рабочий стол\bobi
python test_preflight.py
```

**Ожидаемый вывод**:
```
======================================================================
🎯 OVERALL STATUS: ✅ PASS
======================================================================

📋 CHECKS RESULTS:

  MT5                  ✅ PASS
    └─ Account: 12345678, Balance: $10000.00
  GPT                  ✅ PASS
    └─ Model: gpt-4o
  TELEGRAM             ✅ PASS
  CONFIG               ✅ PASS

🔑 CRITICAL PARAMETERS:
  Trading:
    • Symbol: XAUUSD
    • Timeframe: M15
  Filters:
    • Min Confidence: 75%
    • Daily Limit: 6
    • Max Spread: 3.0 pips
    ...
```

### GUI Workflow

1. **Запуск GUI**:
   ```powershell
   python SMC_bot/run_gui_v2.ps1
   ```

2. **Pre-Flight Check** (опционально):
   - Нажмите `✈️ Pre-Flight Check`
   - Проверьте все checks PASS
   - Убедитесь DRY_RUN mode для теста

3. **Test Telegram** (опционально):
   - Нажмите `📱 Test Telegram`
   - Проверьте конфигурацию

4. **START Bot**:
   - Нажмите `▶ START BOT`
   - **Автоматически** запустятся acceptance checks
   - Если LIVE mode → подтвердите warning
   - Effective config сохранится в `data/runs/run_[timestamp]/`

5. **Мониторинг NOW Status**:
   - Наблюдайте Bot Status (WAITING → ANALYZING → ...)
   - Проверяйте Active Signal
   - Смотрите Last Decision summary

## 📊 Production Run Settings (рекомендовано)

**config/trading.yaml**:
```yaml
trading:
  dry_run: true  # ← true для тестового прогона, false для LIVE
  filters:
    daily_limit: 6
    min_confidence: 75
    max_spread_pips: 0.5  # или 1.0 если часто блокирует
    cooldown_after_win: 15
    cooldown_after_loss: 90
    cooldown_after_2_losses: 240
  risk:
    risk_percent: 1.0
    fixed_lot_size: 0.01
    default_sl_pips: 40
    default_tp_pips: 100
```

## 🔍 Troubleshooting

### ❌ Pre-Flight Failed: MT5
**Проблема**: MT5 not connected

**Решение**:
1. Убедитесь MT5 terminal запущен
2. Проверьте `config/mt5.yaml` (login, password, server)
3. В GUI: Settings → MT5 → Test Connection

### ❌ Pre-Flight Failed: GPT
**Проблема**: AI modules not available

**Решение**:
1. Проверьте `config/ai.yaml` → openai.api_key
2. API key должен начинаться с "sk-"
3. Проверьте `.env` файл

### ❌ Pre-Flight Failed: Config
**Проблема**: Missing critical filter parameters

**Решение**:
1. Откройте `config/trading.yaml`
2. Убедитесь секция `trading.filters` содержит:
   - min_confidence (50-100)
   - daily_limit (1-50)
   - max_spread_pips (0.1-10.0)

### ⚠️ Conflicts Detected
**Проблема**: Duplicate parameters in configs

**Решение**:
1. В GUI: `🔍 Show Effective Config`
2. Проверьте секцию CONFLICTS
3. Удалите дубликаты (должно быть 0 conflicts)

## 📝 Logs & Debug

### Run Folder Structure
После старта создаётся папка:
```
data/runs/run_20260223_010530/
```

**Файлы**:
- `run_effective_config_start.yaml` - baseline config
- `preflight_report.json` - результаты checks
- `run_state.json` - состояние прогона
- `run_events.jsonl` - события (mt5_disconnect, circuit_breaker, etc)

### Decision Logs
Все решения бота логируются в:
- `data/decision_logs.jsonl` (основной файл)
- Копируется в run folder

**Пример записи**:
```json
{
  "timestamp": "2026-02-23T01:05:45.123",
  "signal_id": "abc123",
  "symbol": "XAUUSD",
  "final_decision": "BLOCK",
  "block_reason": "Low confidence: 68% < 75%",
  "confidence": 68,
  "filters_passed": false
}
```

## 🎯 5-Day Run Checklist

### Before Start
- [ ] `python test_preflight.py` → ✅ PASS
- [ ] MT5 connected
- [ ] GPT API key valid
- [ ] Telegram bot configured (опционально)
- [ ] 0 config conflicts
- [ ] DRY_RUN=true (для теста) или LIVE (для production)

### During Run
- [ ] Мониторить NOW Status dashboard
- [ ] Проверять decision_logs.jsonl
- [ ] Смотреть run_events.jsonl для ошибок
- [ ] Отслеживать circuit_breaker triggers

### After Run
- [ ] Проанализировать `data/runs/run_[timestamp]/`
- [ ] Проверить decision stats (ENTER/HOLD/BLOCK ratio)
- [ ] Сравнить run_effective_config_start.yaml с фактическим
- [ ] Проверить метрики (mt5_disconnected, invariants, etc)

## 🛡️ Safety Features

1. **Acceptance Checks**: Блокировка старта при failed checks
2. **LIVE Mode Warning**: Подтверждение перед real trading
3. **Config Export**: Baseline для анализа after run
4. **Event Logging**: Полная история для debugging
5. **Circuit Breaker**: Auto-stop при critical errors

## 📚 Related Files

- `src/core/preflight_checks.py` - Pre-Flight checker
- `src/core/run_session_manager.py` - Run sessions
- `src/core/bot_manager.py` - Enhanced BotStatus
- `src/gui/app_v2.py` - UI + NOW dashboard
- `test_preflight.py` - Test script

## ✅ Status

**All features implemented and tested.**
- ✅ Pre-Flight Checks module
- ✅ Enhanced BotStatus enum
- ✅ Run Session config export
- ✅ NOW Status dashboard
- ✅ UI buttons (Pre-Flight, Test Telegram)
- ✅ Acceptance checks on START
- ✅ Test script

**Ready for production testing.**

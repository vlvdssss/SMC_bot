# 🔧 Изменения: Торговля только золотом (XAUUSD)

## ✅ Что сделано (2026-02-17)

### 1. Отключен EURUSD - оставлено только золото (XAUUSD)

**Причина**: EURUSD давал постоянные ошибки [Invalid stops] несмотря на множество попыток исправления. Бот выполнил только 1 сделку утром. Решение - временно отключить проблемный инструмент.

### 2. Файлы изменены:

#### `src/ai/pure_ai_trader.py` (строка 41)
```python
# БЫЛО:
SYMBOLS = ["XAUUSD", "EURUSD"]

# СТАЛО:
SYMBOLS = ["XAUUSD"]  # TEMPORARY: Только золото, EURUSD отключен
```

#### `config/ai.yaml` (строки 27, 70-71)
```yaml
# БЫЛО:
  schedule:
    enabled: false

# СТАЛО:
  schedule:
    enabled: true  # ВКЛЮЧЕНО для Pure AI режима

---

# БЫЛО:
  symbols:
  - XAUUSD
  - EURUSD

# СТАЛО:
  symbols:
  - XAUUSD
  # - EURUSD  # TEMPORARY: Отключен
```

#### `config/instruments.yaml` (строки 7, 11, 19)
```yaml
# БЫЛО:
  EURUSD:
    analysis_enabled: true
    enabled: true
    trading_enabled: true

# СТАЛО:
  EURUSD:
    analysis_enabled: false  # TEMPORARY: Отключен анализ
    enabled: false  # TEMPORARY: Отключен
    trading_enabled: false  # TEMPORARY: Отключена торговля
```

#### `src/gui/app.py` (строки 1499-1509)
```python
# БЫЛО (жестко закодированные инструменты):
for symbol in ['XAUUSD', 'EURUSD']:
    scheduler.trigger_immediate_analysis(...)

# СТАЛО (загрузка из PureAITrader.SYMBOLS):
from src.ai.pure_ai_trader import PureAITrader
symbols = getattr(PureAITrader, 'SYMBOLS', ['XAUUSD'])
for symbol in symbols:
    scheduler.trigger_immediate_analysis(...)
```

### 3. Что ожидается после перезапуска:

✅ **Бот анализирует только XAUUSD (золото)**
✅ **EURUSD полностью отключен** (анализ, торговля, сигналы)
✅ **AI Scheduler запускается** (исправлена ошибка `schedule.enabled: false`)
✅ **Анализ каждые 30 минут** (как настроено в конфиге)
✅ **Cooldown 30 минут** после каждой сделки
✅ **Нет проблем с [Invalid stops]** для EURUSD (отключен)

### 4. Логи, которые должны появиться:

```
[AI-Scheduler] v2.0 initialized in INTERVAL mode: every 30 minutes
[AI-Scheduler] ✅ Analysis completed for XAUUSD
[AI-Scheduler] EURUSD analysis disabled in config
[Executor] ✅ Stops validated: SL=XXXX.XX, TP=XXXX.XX (XAUUSD)
[Executor] Order executed: XAUUSD BUY 0.01 lots at XXXX.XX
```

### 5. Как вернуть EURUSD обратно (когда исправим):

1. В `src/ai/pure_ai_trader.py`: вернуть `SYMBOLS = ["XAUUSD", "EURUSD"]`
2. В `config/ai.yaml`: раскомментировать `- EURUSD`
3. В `config/instruments.yaml`: вернуть все `true` для EURUSD
4. Перезапустить бота

---

## 🐛 История проблем (контекст)

### Попытка #1: Уменьшение SL/TP (30→20 pips)
- Результат: ❌ Все равно [Invalid stops]

### Попытка #2: Увеличение до 25/50 pips (минимум брокера 5$)
- Результат: ❌ Все равно [Invalid stops]

### Попытка #3: Entry drift detection + recalculation
- Результат: ❌ Все равно [Invalid stops]

### Попытка #4: Stops_level validation + fallback
- Результат: ❌ Все равно [Invalid stops] (10:07:01 - sl: 1.18331 tp: 1.17250)

### РЕШЕНИЕ: Временно отключить EURUSD, сосредоточиться на XAUUSD

---

## 📊 Текущие параметры (XAUUSD)

- **SL/TP**: $4.5 / $12 (работает без проблем)
- **Анализ**: Каждые 30 минут
- **Cooldown**: 30 минут после сделки
- **Max trades/day**: 3
- **Лот**: 0.01 (может увеличиваться по сигналу)

---

## 🔄 Перезапуск бота

```powershell
# Остановить бота (если запущен)
# Через GUI: Нажать "Stop"

# Или через терминал:
taskkill /F /IM python.exe

# Запустить заново:
cd "C:\Users\kamsa\OneDrive\Рабочий стол\bobi\SMC_bot"
.\run.ps1
```

---

## ✅ Чеклист после запуска

- [ ] Логи показывают "XAUUSD" только (нет "EURUSD")
- [ ] AI Scheduler запустился ("v2.0 initialized")
- [ ] Анализ проходит каждые 30 минут
- [ ] XAUUSD сделки открываются без ошибок
- [ ] Нет ошибок [Invalid stops]
- [ ] Позиции закрываются корректно + логи cooldown

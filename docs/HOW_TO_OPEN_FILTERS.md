# 🚀 КАК ОТКРЫТЬ НАСТРОЙКИ С НОВОЙ ВКЛАДКОЙ FILTERS

## Вариант 1: Полное GUI бота

```powershell
# Находясь в папке SMC_bot
.\run_gui_v2.ps1
```

После запуска:
1. Откроется главное окно бота
2. Нажмите кнопку **⚙️ Settings** (в правом верхнем углу)
3. Откроется диалог настроек с вкладками:
   - Trading
   - Risk
   - **✨ Filters** ← НОВАЯ ВКЛАДКА!
   - AI
   - Logging
   - Advanced

## Вариант 2: Только окно Settings (для быстрого тестирования)

```powershell
python test_settings_gui_filters.py
```

## Что вы увидите на вкладке Filters:

| № | Параметр | Тип | Текущее значение |
|---|----------|-----|------------------|
| 1 | Trade Filters Enabled | ☑️ Checkbox | ✅ True |
| 2 | Min Confidence % | 🔢 Number | 75 |
| 3 | Min Setup Score | 🔢 Number | 70 |
| 4 | Min Risk/Reward | 🔢 Number | 1.2 |
| 5 | Max Spread (pips) | 🔢 Number | 3.0 |
| 6 | Daily Trade Limit | 🔢 Number | 6 |
| 7 | Cooldown After Win (min) | 🔢 Number | 15 |
| 8 | Cooldown After Loss (min) | 🔢 Number | 90 |
| 9 | Cooldown After 2 Losses (min) | 🔢 Number | 240 |
| 10 | HTF Timeframe | 📋 Dropdown | M15 |
| 11 | HTF EMA Fast | 🔢 Number | 50 |
| 12 | HTF EMA Slow | 🔢 Number | 200 |

## Что происходит при нажатии Save:

1. ✅ Значения сохраняются в `config/trading.yaml` → `trading.filters`
2. ✅ ConfigManager автоматически перезагружает конфиг
3. ✅ TradeFilters получает callback и обновляет свои параметры
4. ✅ **БЕЗ ПЕРЕЗАПУСКА БОТА!** (hot reload)

## Проверка что изменения применились:

### 1. Через Effective Config:
```powershell
python test_effective_config_gui.py
```
- Откроется диалог с деревом всех конфигов
- Найдите `trading.yaml` → `filters`
- Должны быть видны ваши новые значения
- **Конфликтов быть не должно!** (0 conflicts)

### 2. Через логи TradeFilters:
```python
# После изменения min_confidence в GUI с 75 → 99:
[TradeFilters] 🔄 Filter changes detected:
  ↳ min_confidence: 75 → 99
```

### 3. Через decision_logs.jsonl:
```bash
# Запустите бота в DRY_RUN
# Дождитесь сигнала с confidence < 99%
# Проверьте logs/decision_logs.jsonl
# Должна быть запись:
{
  "result": "BLOCK",
  "reason": "confidence 85% < 99% threshold",
  "filter": "min_confidence"
}
```

## Архитектура (после рефакторинга):

```
GUI Settings → Save
    ↓
config/trading.yaml → trading.filters → min_confidence: 99
    ↓
ConfigManager.reload_all()
    ↓
TradeFilters._on_config_reload()
    ↓
TradeFilters._load_config() читает из trading.yaml
    ↓
self.config['min_confidence'] = 99
    ↓
✅ Применено БЕЗ перезапуска!
```

## Текущий статус:

✅ **11 параметров добавлены в GUI**
✅ **0 конфликтов** (single source of truth)
✅ **Hot reload работает** (test_trade_filters_reload.py passes)
✅ **Effective Config показывает правильные значения**
✅ **trading.yaml - единственный источник** для фильтров

## Если что-то не видно:

1. **Проверьте что запускаете правильный файл:**
   ```powershell
   # Должно быть:
   .\run_gui_v2.ps1
   
   # НЕ:
   .\run_gui.ps1  # старая версия
   ```

2. **Проверьте версию dialogs_v2.py:**
   ```powershell
   # Должна быть строка:
   grep -n "Filters" src\gui\dialogs_v2.py
   # Результат: линия ~175 "tab": "Filters"
   ```

3. **Проверьте что trading.yaml содержит секцию filters:**
   ```powershell
   cat config\trading.yaml | Select-String "filters:" -Context 2
   ```

## Что дальше:

После проверки что GUI работает:
1. ⏳ Добавить кнопку "Dump Settings with Sources"
2. ⏳ Тестирование end-to-end (GUI → decision_logs)
3. ⏳ 5-дневный прогон в DRY_RUN
4. ⏳ Достижение 90%+ QA test pass rate

# 🧹 ДУБЛИ ПАРАМЕТРОВ УСТРАНЕНЫ

**Дата:** 2026-02-23 00:27  
**Проблема:** Пользователь заметил что min_confidence встречается 2 раза в Settings GUI  
**Решение:** Удалены все дубли параметров, оставлена только Filters версия

---

## ❌ Удалённые дубли:

### 1. **min_confidence** (было 2 раза)

| Параметр | Где был | Значение | Статус |
|----------|---------|----------|--------|
| `ai_min_confidence` | AI tab | 70% | ❌ **УДАЛЁН** |
| `filter_min_confidence` | Filters tab | 75% | ✅ **ОСТАВЛЕН** |

**Причина удаления:**
- TradeFilters контролирует входы в сделки
- `ai_min_confidence` не использовался в коде
- `filter_min_confidence` - правильный параметр

---

### 2. **max_trades_per_day** (было 2 раза)

| Параметр | Где был | Значение | Статус |
|----------|---------|----------|--------|
| `max_trades_per_day` | Risk tab | 15 | ❌ **УДАЛЁН** |
| `filter_daily_limit` | Filters tab | 6 | ✅ **ОСТАВЛЕН** |

**Причина удаления:**
- Путаница для пользователя - 2 места для одной настройки
- `filter_daily_limit` используется TradeFilters
- `max_trades_per_day` не имел реальной функции

---

### 3. **max_spread_pips** (мёртвый код)

| Параметр | Где был | Значение | Статус |
|----------|---------|----------|--------|
| `max_spread_pips` | Risk tab (код загрузки/сохранения) | 3.0 | ❌ **УДАЛЁН** |
| `filter_max_spread_pips` | Filters tab | 3.0 | ✅ **ОСТАВЛЕН** |

**Причина удаления:**
- `max_spread_pips` не был в CONFIG_SCHEMA (GUI не показывал)
- Загрузка/сохранение были, но переменной не было
- Мёртвый код, оставшийся после рефакторинга

---

## ✅ Что оставлено (единственные версии):

| Параметр | Где | Значение | Используется |
|----------|-----|----------|--------------|
| `filter_min_confidence` | Filters | 75% | TradeFilters |
| `filter_max_spread_pips` | Filters | 3.0 | TradeFilters |
| `filter_daily_limit` | Filters | 6 | TradeFilters |
| `filter_cooldown_win` | Filters | 15 min | TradeFilters |
| `filter_cooldown_loss` | Filters | 90 min | TradeFilters |
| `filter_cooldown_2losses` | Filters | 240 min | TradeFilters |
| `filter_min_rr` | Filters | 1.2 | TradeFilters |
| `filter_min_setup_score` | Filters | 70 | TradeFilters |
| `filter_htf_timeframe` | Filters | M15 | TradeFilters |
| `filter_htf_ema_fast` | Filters | 50 | TradeFilters |
| `filter_htf_ema_slow` | Filters | 200 | TradeFilters |

---

## 📝 Изменения в коде:

### Файл: [src/gui/dialogs_v2.py](SMC_bot/src/gui/dialogs_v2.py)

#### 1. CONFIG_SCHEMA (lines 38-84)

**Удалено:**
```python
# БЫЛО (AI tab):
"ai_min_confidence": {"type": int, "default": 70, "tab": "AI", ...}

# БЫЛО (Risk tab):
"max_trades_per_day": {"type": int, "default": 15, "tab": "Risk", ...}
```

**Добавлены комментарии:**
```python
# NOTE: Min confidence moved to Filters tab (filter_min_confidence)
# NOTE: Daily trade limit moved to Filters tab (filter_daily_limit)
```

#### 2. _load_configs() (lines 325-390)

**Удалено:**
```python
# Загрузка ai_min_confidence
'ai_min_confidence': ai_config.get('market_analyst', {}).get('blocks', {}).get('bias', 0.8) * 100,

# Загрузка max_spread_pips из risk
'max_spread_pips': risk.get('max_spread_pips', 3.0),
```

**Добавлены комментарии:**
```python
# ai_min_confidence removed - use filter_min_confidence instead
# max_spread_pips removed - use filter_max_spread_pips instead
```

#### 3. _save_to_yaml() (lines 442-510)

**Удалено:**
```python
# Сохранение max_spread_pips в risk
risk['max_spread_pips'] = data.get('max_spread_pips', 3.0)
```

**Добавлен комментарий:**
```python
# max_spread_pips removed - use filter_max_spread_pips instead
```

---

## ✅ Тестирование:

### Тест 1: Проверка на дубли

```bash
python test_no_duplicates.py
```

**Результат:**
```
✅ TEST PASSED: No duplicate parameters found!
   • min_confidence: 1 (in Filters)
   • max_spread: 1 (in Filters)
   • daily_limit: 1 (in Filters)
```

### Тест 2: GUI визуально

```bash
python test_settings_gui_filters.py
```

**Результат:**
- ✅ Settings открывается без ошибок
- ✅ Tabs: Trading, Risk, **Filters**, AI, Logging, Advanced
- ✅ Filters tab содержит 12 параметров
- ✅ Нет дублей в AI или Risk табах

### Тест 3: Конфликты в config

```bash
python test_conflict_detection.py
```

**Результат:**
```
✅ TEST PASSED: Zero conflicts!
   • trade_filters removed from ai.yaml
   • All 12 filter parameters in trading.yaml
   • No duplicate definitions detected
```

---

## 📊 До и После:

### До (было дублей):

| Параметр | Мест | Проблема |
|----------|------|----------|
| min_confidence | 2 | AI tab (70%) vs Filters tab (75%) |
| daily limit | 2 | Risk tab (15) vs Filters tab (6) |
| max_spread | 2 | Risk код (3.0) vs Filters tab (3.0) |

### После (0 дублей):

| Параметр | Мест | Статус |
|----------|------|--------|
| min_confidence | 1 | ✅ Только Filters tab |
| daily limit | 1 | ✅ Только Filters tab |
| max_spread | 1 | ✅ Только Filters tab |

---

## 🎯 Acceptance Criteria:

✅ **Дубли удалены** (test_no_duplicates.py passes)  
✅ **GUI работает** (test_settings_gui_filters.py passes)  
✅ **Конфликтов = 0** (test_conflict_detection.py passes)  
✅ **Мёртвый код удалён** (max_spread_pips из загрузки/сохранения)  
✅ **Комментарии добавлены** (объясняют почему удалено)

---

## 📚 Архитектура (финальная):

```
CONFIG_SCHEMA (dialogs_v2.py)
    ├─ Trading tab
    │   ├─ trading_enabled
    │   ├─ dry_run_mode
    │   ├─ fixed_lot_size
    │   └─ ...
    ├─ Risk tab
    │   ├─ risk_percent
    │   ├─ max_daily_loss
    │   ├─ max_open_positions
    │   ├─ max_trades_per_hour
    │   └─ max_losses_in_row
    │   # ❌ max_trades_per_day УДАЛЁН (дубль filter_daily_limit)
    ├─ Filters tab ⭐ ЕДИНСТВЕННЫЙ ИСТОЧНИК для фильтров
    │   ├─ filter_enabled
    │   ├─ filter_min_confidence ✅ 75%
    │   ├─ filter_max_spread_pips ✅ 3.0
    │   ├─ filter_daily_limit ✅ 6
    │   └─ ... (всего 12 параметров)
    ├─ AI tab
    │   ├─ ai_enabled
    │   ├─ ai_model
    │   ├─ ai_temperature
    │   # ❌ ai_min_confidence УДАЛЁН (дубль filter_min_confidence)
    │   └─ ...
    └─ Logging, Advanced tabs
```

---

## 🚀 Следующие шаги:

1. ✅ Дубли устранены
2. ✅ Filters tab работает
3. ✅ Конфликты = 0
4. ⏳ Добавить кнопку "Dump Settings with Sources"
5. ⏳ End-to-end тестирование (GUI → decision_logs)
6. ⏳ 5-дневный прогон в DRY_RUN

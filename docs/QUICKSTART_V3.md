# ⚡ QUICKSTART: Signal Quality V3.0

## 🎯 ЧТО СДЕЛАНО

### ✅ Создано 4 новых модуля:

1. **`src/ai/signal_quality.py`** - Система Accuracy/Quality/RiskMode
2. **`src/ai/gold_news_filter.py`** - Фильтр HIGH IMPACT новостей для золота
3. **`src/ai/signal_manager_v3.py`** - Интеграция с существующим Signal Manager
4. **`src/ai/activate_v3.py`** - Простой активатор V3

### ✅ Интегрировано в LiveTrader

- `src/live/live_trader.py` обновлён для автоматической активации V3
- Используется флаг `ENABLE_SIGNAL_QUALITY_V3` для вкл/выкл

### ✅ Документация

- **`docs/SIGNAL_QUALITY_V3.md`** - Полная документация архитектуры

---

## 🚀 КАК ВКЛЮЧИТЬ V3

### Вариант 1: АВТОМАТИЧЕСКАЯ активация (рекомендуется)

V3 **УЖЕ АКТИВИРОВАНА** в LiveTrader! Просто запусти бота:

```bash
python main.py
```

В логах увидишь:
```
[V3 Config] Signal Quality V3.0 is ENABLED
[V3 Activator] ✅ Signal Quality V3.0 ACTIVATED
  - Accuracy/Quality separation enabled
  - Gold news filter active (HIGH IMPACT only)
  - Risk mode: BALANCED (configurable)
```

### Вариант 2: ВЫКЛЮЧИТЬ V3 (вернуться на V2)

Открой `src/ai/activate_v3.py` и измени:

```python
ENABLE_SIGNAL_QUALITY_V3 = False  # Было: True
```

---

## 📊 КАК ЭТО РАБОТАЕТ

### Старая логика V2 (БЫЛО):
```
GPT Decision → block_level (SOFT/HARD) → risk_multiplier → Вход + Лот
```
**Проблема**: block_level влиял И на вход, И на лот одновременно.

### Новая логика V3 (СТАЛО):
```
GPT Decision → Accuracy → Проверка входа → Разрешён/Запрещён
                    ↓
              Quality → Размер лота (0.5x-2.0x)
```
**Решение**: Вход и лот — НЕЗАВИСИМЫЕ параметры.

---

## 🔍 ПРИМЕРЫ

### Пример 1: Высокая точность, среднее качество

```python
Input:
  - confidence: 80% → Accuracy: VERY_HIGH ✅
  - R:R: 2.0 → Quality: NORMAL (лот 1.0x)
  - news: Нет HIGH IMPACT ✅

Result:
  ✅ ВХОД РАЗРЕШЁН
  📦 ЛОТ: 1.0x (базовый)
```

### Пример 2: Средняя точность, отличное качество

```python
Input:
  - confidence: 60% → Accuracy: MEDIUM (требует подтверждения)
  - R:R: 4.5 + подтверждение → Quality: EXCELLENT (лот 2.0x)
  - news: Нет HIGH IMPACT ✅

Result:
  ✅ ВХОД РАЗРЕШЁН (MEDIUM + подтверждение)
  📦 ЛОТ: 1.5x (EXCELLENT 2.0x ограничен BALANCED режимом до 1.5x)
```

### Пример 3: Высокая точность, но HIGH IMPACT новости

```python
Input:
  - confidence: 85% → Accuracy: VERY_HIGH ✅
  - R:R: 3.0 → Quality: GOOD (лот 1.5x)
  - news: NFP через 30 минут 🚫

Result:
  ❌ ВХОД ЗАБЛОКИРОВАН
  Причина: "HIGH IMPACT news for GOLD - entry blocked"
  📦 ЛОТ: 0.0x (не важно, вход запрещён)
```

---

## 📰 ФИЛЬТР НОВОСТЕЙ

### Что фильтруется:

✅ **УЧИТЫВАЮТСЯ:**
- USD новости: NFP, FOMC, CPI, GDP, Interest Rate
- Прямые новости по золоту
- Геополитика (war, conflict)

❌ **ИГНОРИРУЮТСЯ:**
- EUR, GBP, JPY новости
- MEDIUM/LOW impact
- Индексы (S&P, Dow)

### Окно блокировки:
- **±2 часа** от HIGH IMPACT события
- Пример: NFP в 13:30 → Блок 11:30-15:30

---

## ⚙️ НАСТРОЙКА РИСКА

### Risk Modes (в `src/ai/signal_quality.py`):

```python
RiskMode.CONSERVATIVE  # Только HIGH+ точность, макс 1.0x лот
RiskMode.BALANCED      # MEDIUM+ точность, макс 1.5x лот (по умолчанию)
RiskMode.AGGRESSIVE    # LOW+ точность, макс 2.0x лот
```

### Изменить режим:

```python
# В src/ai/activate_v3.py или прямо в коде
from src.ai.signal_quality import RiskMode

evaluator.set_risk_mode(RiskMode.AGGRESSIVE)
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Проверить работу V3:

```bash
# Запустить unit-тесты
python src/ai/signal_quality.py
python src/ai/gold_news_filter.py
```

### Проверить в боте:

1. Запусти бота
2. Включи "Pure AI Trading" режим
3. Смотри в логах:
```
[Signal V3] ✅ ENTRY ALLOWED | BUY XAUUSD |
  Accuracy: HIGH | Quality: GOOD | Lot: 1.5x
```

---

## 🔄 ПЕРЕКЛЮЧЕНИЕ V2 ↔ V3

### Динамическое переключение:

```python
from src.ai.activate_v3 import switch_to_v2, switch_to_v3

# Переключить на V2 (старая логика)
switch_to_v2(signal_manager)

# Вернуться на V3
switch_to_v3(signal_manager)
```

### Проверить текущий режим:

```python
from src.ai.activate_v3 import get_v3_status

if get_v3_status(signal_manager):
    print("V3 активна")
else:
    print("V2 активна")
```

---

## 📁 СТРУКТУРА ФАЙЛОВ

```
src/ai/
  ├── signal_quality.py         # ⭐ Accuracy/Quality/RiskMode
  ├── gold_news_filter.py       # ⭐ Фильтр новостей для золота
  ├── signal_manager_v3.py      # ⭐ Интеграция с Signal Manager
  ├── activate_v3.py            # ⭐ Активатор V3
  ├── signal_manager.py         # Существующий (патчится V3)
  └── news_fetcher.py           # Существующий (используется)

docs/
  └── SIGNAL_QUALITY_V3.md      # ⭐ Полная документация

src/live/
  └── live_trader.py            # Обновлён для V3
```

---

## ❓ FAQ

### Q: V3 активна по умолчанию?
A: **Да**, если `ENABLE_SIGNAL_QUALITY_V3 = True` в `activate_v3.py`

### Q: Как вернуться на старую логику?
A: Измени `ENABLE_SIGNAL_QUALITY_V3 = False` или вызови `switch_to_v2()`

### Q: V3 работает в backtest?
A: Пока нет, нужно добавить интеграцию в backtest модуль

### Q: Как изменить порог Accuracy?
A: Отредактируй `SignalAccuracy.from_confidence()` в `signal_quality.py`

### Q: Новости кэшируются?
A: Да, на 1 час (в `GPTNewsFilter`)

### Q: Можно добавить свои градации Quality?
A: Да, добавь новые значения в `SignalQuality` enum

---

## 📌 СЛЕДУЮЩИЕ ШАГИ

### Для тестирования:
1. ✅ Запусти бота с V3
2. ✅ Проверь логи на наличие `[Signal V3]`
3. ✅ Сравни решения V2 vs V3 (используй `_process_analysis_v2()`)

### Для production:
1. ⏳ Протестировать на демо-счёте 1-2 недели
2. ⏳ Собрать статистику сигналов V3 vs V2
3. ⏳ Настроить оптимальный RiskMode
4. ⏳ Добавить GUI для переключения режимов

---

## ⚠️ ВАЖНО

- V2 логика **СОХРАНЕНА** как fallback (`_process_analysis_v2()`)
- При ошибке V3 → автоматически fallback на V2
- News filter при ошибке → **разрешает** торговлю (fail-safe)
- Все изменения **обратно совместимы**

---

## 📞 ПОДДЕРЖКА

Если что-то не работает:

1. Проверь логи: `logs/baza_YYYYMMDD.log`
2. Ищи ошибки с тегом `[V3 Activator]` или `[Signal V3]`
3. Попробуй выключить V3: `ENABLE_SIGNAL_QUALITY_V3 = False`
4. Открой Issue на GitHub с логами

---

**Enjoy Signal Quality V3.0!** 🚀

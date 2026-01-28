# BAZA Trading Bot V4 - Изменения логики

## ✅ Что реализовано

### 1. **M5 Single Timeframe Analysis**
- ❌ Удалено: M15, M30, H1 (3 таймфрейма)
- ✅ Добавлено: Только M5 (1 таймфрейм)
- **Бары**: 200 M5 свечей = ~16 часов данных
- **Фокус**: Последние 20-30 свечей для скальпинга

**Файлы:**
- `src/ai/market_analyst.py` - метод `_capture_charts()`
- `src/ai/market_analyst.py` - метод `_calculate_metrics()`

---

### 2. **Fixed SL/TP Parameters**
- **SL**: Фиксированный $5 от входа
- **TP**: Фиксированный $10 от входа
- **R:R**: Всегда 2:1 (10/5)

**Логика:**
```python
# BUY signal
entry = 2665.0
stop_loss = 2660.0  # entry - $5
take_profit = 2675.0  # entry + $10

# SELL signal
entry = 2665.0
stop_loss = 2670.0  # entry + $5
take_profit = 2655.0  # entry - $10
```

**Файлы:**
- `src/ai/market_analyst.py` - метод `_validate_analysis()` (lines 515-545)
- GPT ответы **игнорируются** - система сама рассчитывает SL/TP

---

### 3. **Trailing Stop V4**
**Параметры:**
- **Активация**: 60% от TP ($6 profit)
- **Новый SL**: 50% от TP ($5 profit = breakeven+)
- **Частота**: ОДИН раз за сделку

**Пример работы:**
```
Entry: $2665.0
SL: $2660.0 (-$5)
TP: $2675.0 (+$10)

Сценарий:
1. Цена → $2671.0 (+$6) → ТРИГГЕР АКТИВАЦИИ
2. Система переносит SL → $2670.0 (+$5 от entry)
3. Цена откатывается → $2670.0 → Закрытие с +$5 profit
4. Флаг v4_trailing_activated = True → больше не двигается
```

**Файлы:**
- `src/live/trailing_stop_v4.py` - новый модуль
- `src/live/live_trader.py` - интеграция (line 106-108, 704-722)

---

### 4. **Updated GPT Prompt**
**Изменения:**
- Фокус на M5 скальпинге
- Упрощенные инструкции (короче v3 промпта)
- Упоминание фиксированных SL/TP
- Примеры M5 сетапов

**Ключевые секции:**
```
- Look at LAST 20-30 M5 candles
- Quick reversals and momentum
- BUY if: price bounced from support + 2-3 green candles
- SELL if: price rejected resistance + 2-3 red candles
- WAIT if: no clear setup or consolidation
```

**Файлы:**
- `src/ai/market_analyst.py` - метод `_build_analysis_prompt()` (lines 240-340)

---

### 5. **Higher Confidence Threshold**
- **V3**: 60% confidence minimum
- **V4**: 70% confidence minimum (для M5 скальпинга)

**Причина:** M5 более шумный таймфрейм, нужны более качественные сигналы

**Файлы:**
- `src/ai/signal_manager.py` - метод `_validate_signal()` (line 484)

---

### 6. **Metadata Updates**
```python
analysis_version = "4.0"  # Was: 2.0
prompt_version = "2026-01-V4"  # Was: 2026-01
```

**Файлы:**
- `src/ai/market_analyst.py` - метод `_validate_analysis()` (lines 548-550)

---

## 📁 Измененные файлы

### Основные:
1. **src/ai/market_analyst.py**
   - M5 analysis (single timeframe)
   - Fixed SL/TP validation
   - Simplified GPT prompt
   - V4 metadata

2. **src/ai/signal_manager.py**
   - 70% confidence threshold
   - Fixed 2:1 R:R validation

3. **src/live/trailing_stop_v4.py** ⭐ NEW
   - Fixed trailing logic (60%/50%)
   - One-time activation
   - Clean implementation

4. **src/live/live_trader.py**
   - TrailingStopV4 initialization
   - Simplified check_trailing_stop() method

---

## 🔄 Что еще нужно сделать

### ⚠️ PENDING (не реализовано)

#### 1. **Signal Scheduling (3 hours)**
- ❌ Текущее: Сигналы могут генерироваться каждый раз
- ✅ Требуется: Раз в 3 часа (00:00, 03:00, 06:00...)
- ✅ Требуется: Пропускать если позиция открыта
- ✅ Требуется: Первый запуск = immediate signal

**Где реализовать:**
- `src/ai/signal_manager.py` или `src/live/live_trader.py`
- Добавить метод `should_generate_signal()`:
  ```python
  def should_generate_signal():
      # Check if position open
      if executor.has_open_positions():
          return False
      
      # Check if 3 hours passed
      if time_since_last_signal < 3_hours:
          return False
      
      return True
  ```

#### 2. **AI Analysis Trigger Logic**
- Текущее: Может быть любое расписание
- Требуется: Интеграция с 3-часовым расписанием

**Где реализовать:**
- `src/live/live_trader.py` - метод `run()` или scheduler

---

## ⚡ Быстрый тест V4

```python
# 1. Запуск бота
python main.py

# Проверь логи:
# [AI] Captured M5 screenshot for V4 analysis (1/1)
# [AI] ✅ V4 FIXED SL/TP Applied:
# [AI]    Entry: $2665.00
# [AI]    SL: $2660.00 (fixed $5)
# [AI]    TP: $2675.00 (fixed $10)
# [V4-Trailing] ✅ BUY #12345 XAUUSD
# [V4-Trailing]    Profit: $6.50 >= $6.00
# [V4-Trailing]    SL: $2660.00 → $2670.00 (BE + $5.00)
```

---

## 📊 Сравнение версий

| Параметр | V3 (Старая) | V4 (Новая) |
|----------|-------------|------------|
| **Таймфреймы** | M15, M30, H1 | M5 |
| **Скриншоты** | 3 | 1 |
| **SL** | Динамический $5-$15 | Фиксированный $5 |
| **TP** | Динамический (S/R) | Фиксированный $10 |
| **R:R** | 2:1+ | Всегда 2:1 |
| **Confidence** | 60% | 70% |
| **Trailing Activation** | Динамический % | Фиксированный 60% ($6) |
| **Trailing Stop** | Динамический | Фиксированный 50% ($5) |
| **Расписание сигналов** | ❓ Не определено | ⚠️ TODO: Каждые 3 часа |

---

## 🎯 Преимущества V4

1. **Простота**: Фиксированные параметры = меньше ошибок
2. **Скорость**: M5 = быстрые решения, скальпинг
3. **Контроль риска**: Всегда известный SL/TP
4. **Trailing**: Гарантированный BE+ при $6 profit
5. **Consistency**: Одинаковые параметры для всех сделок

---

## 🔧 Конфигурация

V4 использует **хардкод параметры** (не из config/):

```python
# В коде (НЕ МЕНЯЙ без полного понимания):
FIXED_SL_DISTANCE = 5.0   # $5
FIXED_TP_DISTANCE = 10.0  # $10
TRAILING_ACTIVATION_PERCENT = 0.6  # 60%
TRAILING_STOP_PERCENT = 0.5  # 50%
MIN_CONFIDENCE_V4 = 70  # 70%
```

Если нужно изменить - редактируй исходники.

---

## ❓ FAQ

**Q: Почему M5 вместо H1?**
A: M5 дает больше торговых возможностей (скальпинг), подходит для быстрых входов/выходов.

**Q: Почему фиксированные SL/TP?**
A: Упрощение логики, предсказуемый риск, консистентность.

**Q: Что если GPT даст SL=$3?**
A: Система **игнорирует** GPT SL/TP и применяет фиксированные $5/$10.

**Q: Трейлинг двигается больше одного раза?**
A: Нет! Флаг `v4_trailing_activated` блокирует повторные переносы.

**Q: Можно ли вернуть v3 логику?**
A: Да, откатись в git на коммит до v4 или восстанови старые файлы.

---

**Статус:** ✅ V4 Core Logic Implemented  
**Pending:** ⚠️ 3-Hour Signal Scheduling  
**Дата:** 2026-01-27  
**Версия:** BAZA Trading Bot V4.0

# Signal Quality System V3.0 - Architecture Documentation

## 🎯 КОНЦЕПЦИЯ

Полное разделение логики сигнала на **ДВА НЕЗАВИСИМЫХ ПАРАМЕТРА**:

### 1️⃣ **Signal Accuracy** (Точность)
- ✅ Влияет ТОЛЬКО на **разрешение входа**
- ❌ НЕ влияет на размер лота

### 2️⃣ **Signal Quality** (Качество)
- ✅ Влияет ТОЛЬКО на **размер лота**
- ❌ НЕ влияет на решение о входе

### 3️⃣ **Risk Mode** (Режим риска)
- Модифицирует **пороги** Accuracy и **максимальный** лот Quality
- НЕ принимает прямого решения о входе

---

## 📊 ГРАДАЦИИ

### Signal Accuracy
```python
VERY_LOW    (0-40%)    → Вход запрещён категорически
LOW         (40-50%)   → Вход запрещён - низкая точность
MEDIUM      (50-65%)   → Вход возможен при доп. фильтрах
HIGH        (65-80%)   → Вход разрешён - хорошая точность
VERY_HIGH   (80-100%)  → Вход приоритетный - отличная точность
```

### Signal Quality
```python
POOR        (R:R < 1.5)              → Лот 0.5x (минимальный)
NORMAL      (R:R 1.5-2.5)            → Лот 1.0x (базовый)
GOOD        (R:R 2.5-4.0)            → Лот 1.5x (увеличенный)
EXCELLENT   (R:R > 4.0 + подтв.)     → Лот 2.0x (максимальный)
```

### Risk Mode
```python
CONSERVATIVE  → Только HIGH+ accuracy, макс 1.0x лот
BALANCED      → MEDIUM+ accuracy, макс 1.5x лот
AGGRESSIVE    → LOW+ accuracy, макс 2.0x лот
```

---

## 🔄 WORKFLOW

```
┌─────────────────────────────────────────────────────────────┐
│  GPT Decision                                               │
│  confidence: 75%, R:R: 3.0, has_confirmation: true         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  1. ПРОВЕРКА НОВОСТЕЙ (только для GOLD)                     │
│     - HIGH IMPACT события в ±2 часа → БЛОК                 │
│     - Фильтруются только USD/GOLD/ФРС новости              │
└──────────────────────┬──────────────────────────────────────┘
                       │ ✅ News OK
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. ОЦЕНКА ACCURACY                                         │
│     confidence 75% → Accuracy: HIGH                         │
│     allows_entry() → TRUE ✅                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. ПРОВЕРКА RISK MODE                                      │
│     BALANCED mode → requires MEDIUM+ → PASS ✅              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ОЦЕНКА QUALITY                                          │
│     R:R 3.0 + confirmation → Quality: GOOD                  │
│     base_multiplier: 1.5x                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. ПРИМЕНЕНИЕ RISK MODE CAP                                │
│     BALANCED max: 1.5x → lot: 1.5x (no cap) ✅             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  ИТОГОВОЕ РЕШЕНИЕ                                           │
│  ✅ ENTRY ALLOWED | Lot: 1.5x                              │
│  Accuracy: HIGH | Quality: GOOD | Mode: BALANCED            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📰 ФИЛЬТРАЦИЯ НОВОСТЕЙ ДЛЯ ЗОЛОТА

### Правила фильтрации

**✅ УЧИТЫВАЮТСЯ:**
- HIGH/EXTREME impact новости по USD
- NFP, FOMC, CPI, GDP, Interest Rate Decisions
- Прямые новости по золоту (Gold Inventories, etc.)
- Геополитика (war, sanctions, conflict)

**❌ ИГНОРИРУЮТСЯ:**
- EUR, GBP, JPY, AUD новости (если не влияют на USD)
- MEDIUM/LOW impact новости
- Технические индексы (S&P, Dow, Nasdaq)
- Корпоративные новости

### Окно блокировки
- **±2 часа** от HIGH IMPACT события по золоту
- Пример: Если NFP в 13:30 → Блокировка 11:30-15:30

### Пример фильтрации
```python
События сегодня:
1. "US Non-Farm Payrolls" 13:30 UTC (HIGH, USD) → ✅ БЛОКИРУЕТ
2. "Eurozone CPI" 10:00 UTC (HIGH, EUR)         → ❌ Игнор (не USD)
3. "UK GDP" 09:00 UTC (HIGH, GBP)               → ❌ Игнор (не USD)
4. "Gold Inventories" 15:00 UTC (MEDIUM, GOLD)  → ❌ Игнор (не HIGH)
5. "FOMC Rate Decision" 19:00 UTC (EXTREME, USD)→ ✅ БЛОКИРУЕТ

Результат: Блокировка в 11:30-15:30 и 17:00-21:00
```

---

## 🔧 ИНТЕГРАЦИЯ

### Вариант 1: Monkey Patch (рекомендуется для тестирования)

```python
from src.ai.signal_manager import AISignalManager
from src.ai.signal_manager_v3 import patch_signal_manager
from src.ai.news_fetcher import NewsFetcher

# Существующий signal_manager
signal_manager = AISignalManager()

# Патчим с V3 логикой
news_fetcher = NewsFetcher()
patch_signal_manager(signal_manager, news_fetcher)

# Теперь доступен метод process_analysis_v3()
result = signal_manager.process_analysis_v3(analysis)
```

### Вариант 2: Полная миграция (для продакшена)

```python
from src.ai.signal_manager_v3 import migrate_to_v3

signal_manager = AISignalManager()
news_fetcher = NewsFetcher()

# Мигрируем на V3 (заменяет process_analysis на V3)
migrate_to_v3(signal_manager, news_fetcher, enable_v3=True)

# Теперь process_analysis() использует V3 логику
result = signal_manager.process_analysis(analysis)

# Старая V2 логика сохранена как fallback
result_v2 = signal_manager._process_analysis_v2(analysis)
```

### Вариант 3: Прямое использование SignalEvaluator

```python
from src.ai.signal_quality import SignalEvaluator, RiskMode
from src.ai.gold_news_filter import GoldNewsFetcher

evaluator = SignalEvaluator(risk_mode=RiskMode.BALANCED)
gold_news = GoldNewsFetcher(news_fetcher)

# Проверка новостей
news_block, reason = gold_news.check_trading_safety_for_gold()

# Оценка сигнала
decision = evaluator.evaluate(
    confidence=75,
    risk_reward=3.0,
    has_confirmation=True,
    news_block=news_block
)

print(decision)  # SignalDecision(entry_allowed=True, lot_multiplier=1.5, ...)
```

---

## 📈 ПРИМЕРЫ РЕШЕНИЙ

### Case 1: Отличный сигнал без новостей
```
Input:
  - confidence: 85% → Accuracy: VERY_HIGH
  - R:R: 4.5 + confirmation → Quality: EXCELLENT
  - news_block: False
  - risk_mode: BALANCED

Output:
  ✅ ENTRY ALLOWED
  - Accuracy: VERY_HIGH (85%)
  - Quality: EXCELLENT (base: 2.0x)
  - Mode cap: BALANCED (max 1.5x)
  - Final lot: 1.5x (capped)
```

### Case 2: Средний сигнал, HIGH IMPACT новости
```
Input:
  - confidence: 60% → Accuracy: MEDIUM
  - R:R: 2.0 → Quality: NORMAL
  - news_block: True (NFP in 1 hour)
  - risk_mode: BALANCED

Output:
  ❌ ENTRY BLOCKED
  - Block reason: "HIGH IMPACT news for GOLD - entry blocked"
  - Lot: 0.0x (не важно, вход запрещён)
```

### Case 3: Низкая точность, хорошее качество
```
Input:
  - confidence: 45% → Accuracy: LOW
  - R:R: 3.5 + confirmation → Quality: GOOD
  - news_block: False
  - risk_mode: BALANCED

Output:
  ❌ ENTRY BLOCKED
  - Block reason: "Accuracy too low: LOW (Вход запрещён - низкая точность)"
  - Lot: 0.0x (качество не имеет значения)
```

### Case 4: MEDIUM accuracy, CONSERVATIVE режим
```
Input:
  - confidence: 60% → Accuracy: MEDIUM
  - R:R: 3.0 → Quality: GOOD
  - news_block: False
  - risk_mode: CONSERVATIVE

Output:
  ❌ ENTRY BLOCKED
  - Block reason: "Risk mode conservative requires higher accuracy"
  - Conservative требует только HIGH/VERY_HIGH
```

### Case 5: AGGRESSIVE режим, низкая точность разрешена
```
Input:
  - confidence: 45% → Accuracy: LOW
  - R:R: 2.5 → Quality: GOOD
  - news_block: False
  - risk_mode: AGGRESSIVE

Output:
  ✅ ENTRY ALLOWED
  - Accuracy: LOW (но AGGRESSIVE разрешает)
  - Quality: GOOD (base: 1.5x)
  - Mode cap: AGGRESSIVE (max 2.0x)
  - Final lot: 1.5x
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Запуск unit-тестов

```bash
# Тест signal_quality.py
python src/ai/signal_quality.py

# Тест gold_news_filter.py
python src/ai/gold_news_filter.py

# Интеграционный тест
python tests/test_signal_quality_integration.py
```

### Ожидаемый output

```
=== TEST CASES ===

Case 1 (Good signal): ✅ ALLOWED | Accuracy: HIGH | Quality: GOOD (lot: 1.50x) | Mode: BALANCED
Case 2 (Medium signal): ✅ ALLOWED | Accuracy: MEDIUM | Quality: POOR (lot: 0.50x) | Mode: BALANCED
Case 3 (News block): ❌ BLOCKED | Accuracy: VERY_HIGH | Quality: EXCELLENT (lot: 0.00x) | Mode: BALANCED
Case 4 (Low accuracy): ❌ BLOCKED | Accuracy: LOW | Quality: NORMAL (lot: 0.00x) | Mode: BALANCED
Case 5 (Conservative mode): ❌ BLOCKED | Accuracy: MEDIUM | Quality: GOOD (lot: 0.00x) | Mode: CONSERVATIVE

=== GOLD NEWS FILTER TEST ===

Total events: 6
Gold-relevant HIGH IMPACT events: 2

🚫 BLOCKS | HIGH | USD | US Non-Farm Payrolls | 13:30 UTC
✅ OK | EXTREME | USD | FOMC Interest Rate Decision | 19:00 UTC

============================================================
⛔ TRADING BLOCKED by: US Non-Farm Payrolls
============================================================
```

---

## 🚀 ROADMAP

### Реализовано ✅
- [x] Разделение Accuracy и Quality
- [x] Фильтр новостей для GOLD (HIGH IMPACT only)
- [x] Risk Mode система
- [x] Monkey patch интеграция
- [x] Unit-тесты

### В разработке 🔄
- [ ] Автоопределение `has_confirmation` из индикаторов
- [ ] GUI настройки Risk Mode
- [ ] История решений в dashboard
- [ ] Backtesting с новой логикой

### Планируется 📋
- [ ] Machine Learning для оптимизации порогов
- [ ] Динамические пороги на основе волатильности
- [ ] Multi-symbol support (EURUSD)
- [ ] API для внешнего управления Risk Mode

---

## 📚 API REFERENCE

### SignalAccuracy
```python
class SignalAccuracy(Enum):
    VERY_LOW = ("very_low", 0, "Вход категорически запрещён")
    LOW = ("low", 1, "Вход запрещён - низкая точность")
    MEDIUM = ("medium", 2, "Вход возможен при дополнительных фильтрах")
    HIGH = ("high", 3, "Вход разрешён - хорошая точность")
    VERY_HIGH = ("very_high", 4, "Вход приоритетный - отличная точность")
    
    def allows_entry() -> bool
    @classmethod from_confidence(cls, confidence: float) -> SignalAccuracy
```

### SignalQuality
```python
class SignalQuality(Enum):
    POOR = ("poor", 0.5, "Минимальный лот - слабый сигнал")
    NORMAL = ("normal", 1.0, "Базовый лот - обычный сигнал")
    GOOD = ("good", 1.5, "Увеличенный лот - хороший сигнал")
    EXCELLENT = ("excellent", 2.0, "Максимальный лот - отличный сигнал")
    
    @classmethod from_rr_and_conditions(cls, risk_reward: float, has_confirmation: bool) -> SignalQuality
```

### RiskMode
```python
class RiskMode(Enum):
    CONSERVATIVE = ("conservative", 0.6, 1.0, "Только HIGH+ accuracy, макс 1.0x лот")
    BALANCED = ("balanced", 0.5, 1.5, "MEDIUM+ accuracy, макс 1.5x лот")
    AGGRESSIVE = ("aggressive", 0.4, 2.0, "LOW+ accuracy, макс 2.0x лот")
    
    def allows_entry(accuracy: SignalAccuracy) -> bool
    def adjust_lot_multiplier(quality_mult: float) -> float
```

### SignalEvaluator
```python
class SignalEvaluator:
    def __init__(risk_mode: RiskMode = RiskMode.BALANCED)
    
    def evaluate(
        confidence: float,
        risk_reward: float,
        has_confirmation: bool = False,
        news_block: bool = False
    ) -> SignalDecision
    
    def set_risk_mode(mode: RiskMode)
```

### GoldNewsFilter
```python
class GoldNewsFilter:
    def __init__(blocking_window_hours: int = 2)
    
    def is_relevant_to_gold(event_title: str, currency: str) -> bool
    def filter_gold_events(all_events: List[Dict]) -> List[GoldNewsEvent]
    def should_block_trading(all_events: List[Dict]) -> Tuple[bool, GoldNewsEvent]
    def get_upcoming_gold_events(all_events: List[Dict], hours_ahead: int = 24) -> List[GoldNewsEvent]
```

### GoldNewsFetcher
```python
class GoldNewsFetcher:
    def __init__(news_fetcher)
    
    def check_trading_safety_for_gold() -> Tuple[bool, str]
    def get_todays_gold_events() -> List[GoldNewsEvent]
```

---

## ⚠️ IMPORTANT NOTES

1. **Backwards Compatibility**: V2 логика сохранена как `_process_analysis_v2()`
2. **Fail-Safe**: При ошибке news filter → торговля РАЗРЕШЕНА (не блокируем)
3. **Performance**: Проверка новостей кэшируется на 1 час
4. **Extensibility**: Легко добавить новые градации Accuracy/Quality
5. **Testing**: Все изменения покрыты unit-тестами

---

## 📞 SUPPORT

Issues: `https://github.com/vlvdssss/SMC_bot/issues`

Автор: GitHub Copilot
Версия: 3.0.0
Дата: 2026-01-22

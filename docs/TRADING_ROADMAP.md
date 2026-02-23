# 🗺️ BAZA Trading Bot - Complete Trading Roadmap

> **Полная схема торговли от запуска до закрытия позиции**  
> Версия: V5.0 | Дата: 15.02.2026

---

## 📋 Оглавление

1. [Инициализация системы](#1-инициализация-системы)
2. [Анализ рынка (GPT-4)](#2-анализ-рынка-gpt-4)
3. [Генерация сигнала](#3-генерация-сигнала)
4. [Фильтрация сигнала (Multi-Layer)](#4-фильтрация-сигнала-multi-layer)
5. [V5 Improvements - Дополнительная фильтрация](#5-v5-improvements---дополнительная-фильтрация)
6. [Исполнение сделки в MT5](#6-исполнение-сделки-в-mt5)
7. [Управление открытой позицией](#7-управление-открытой-позицией)
8. [Закрытие позиции](#8-закрытие-позиции)
9. [Постобработка и логирование](#9-постобработка-и-логирование)
10. [Цикл повторяется](#10-цикл-повторяется)

---

## 1. Инициализация системы

### 1.1 Запуск бота
```
📂 run.ps1
  ↓
🐍 main.py
  ↓
🎮 GUI (src/gui/app.py)
  ↓
🤖 BotManager (src/core/bot_manager.py)
```

**Что происходит:**
- Загружаются конфиги из `config/*.yaml`
- Инициализируется GUI (CustomTkinter)
- Создается `BotManager` - главный оркестратор

---

### 1.2 Подключение к MT5
```python
📡 MT5Connector.connect()
  ├─ Подключение к MetaTrader 5 (terminal64.exe)
  ├─ Проверка соединения с сервером (MetaQuotes-Demo)
  ├─ Логин в аккаунт (5046623512)
  └─ ✅ Connected to MT5
```

**Что проверяется:**
- ✅ Terminal запущен?
- ✅ Аккаунт залогинен?
- ✅ Есть соединение с сервером?

---

### 1.3 Проверка OpenAI API
```python
🔑 OpenAI API Key
  ├─ Чтение из .env (OPENAI_API_KEY)
  ├─ Проверка валидности ключа
  └─ ✅ GPT-4 Available
```

**Модель:** `gpt-4o` (GPT-4 with vision)

---

### 1.4 Инициализация компонентов

#### **Core Components:**
```
LiveTrader (src/live/live_trader.py)
  ├─ RiskManager - управление рисками
  ├─ TradeExecutor - исполнение сделок
  ├─ MarketAnalyst - GPT-4 анализ
  ├─ AISignalManager - управление сигналами
  └─ TelegramNotifier - уведомления
```

#### **V4 Components:**
```
TrailingStopV4 (src/live/trailing_stop_v4.py)
  └─ Процентный trailing stop (активация 30%, шаг 10%)
```

#### **V5 Components (Новые!):**
```
🚀 V5 Improvements
  ├─ TechnicalConfirmation - гибридный фильтр (GPT + индикаторы)
  ├─ SessionAdapter - адаптация под торговые сессии
  ├─ AdaptiveLotSizing - умный расчет лота
  └─ RejectedSignalsLogger - логирование отклоненных сигналов
```

---

### 1.5 Статус "Bot Ready"
```
GUI показывает:
  🟢 MT5: Connected
  🟢 GPT-4: Available
  🟢 Status: Ready
  
→ Пользователь нажимает "▶ START BOT"
```

---

## 2. Анализ рынка (GPT-4)

### 2.1 Scheduler запускает анализ
```python
PureAITrader (src/ai/pure_ai_trader.py)
  ├─ Интервал: каждые 2 часа (IMPROVED: было 3 часа)
  ├─ Инструменты: XAUUSD, EURUSD
  └─ Условие: торговые часы (пн-пт, 01:00-23:00 UTC)
```

**Триггеры для анализа:**
1. ⏰ По расписанию (каждые 2 часа)
2. 🔄 После закрытия позиции (auto-requery)
3. ⏳ Истечение TTL сигнала (30 минут)
4. 📉 FALLBACK: нет позиций и сигналов = анализ через 5 минут

---

### 2.2 Захват скриншота MT5
```python
ChartCaptureService (src/ai/chart_service.py)
  ├─ Таймфреймы: M5, M15, M30, H1, H4
  ├─ Индикаторы: EMA(20, 50, 200), RSI(14), ATR(14)
  ├─ Формат: PNG, base64
  └─ Сохранение: data/charts/XAUUSD_*.png
```

**Что на скриншоте:**
- 📊 5 таймфреймов одновременно
- 📈 Свечи + индикаторы
- 🔍 SMC структуры (order blocks, FVG)

---

### 2.3 GPT-4 Vision анализирует график
```python
MarketAnalyst.analyze_with_vision()
  ├─ Prompt: "Analyze XAUUSD M5 chart for trading signal..."
  ├─ Context: Current price, spread, volatility, session
  ├─ Model: gpt-4o
  └─ Response: JSON with BUY/SELL/HOLD + entry/SL/TP/confidence
```

**Что анализирует GPT:**
- 📉 Тренд на всех таймфреймах
- 📊 Уровни поддержки/сопротивления
- 🔄 Паттерны (SMC, price action)
- 💹 Индикаторы (EMA, RSI, ATR)
- ⏰ Торговая сессия (Asian/European/US)

---

### 2.4 Адаптивные SL/TP (V5 Logic)
```python
Adaptive SL/TP by Volatility + Session
  
📊 Волатильность (ATR):
  ├─ Low volatility (ATR < $3):  SL = $3.5, TP = $9
  ├─ Normal (ATR $3-7):          SL = $4.5, TP = $12
  └─ High volatility (ATR > $7): SL = $5-8,  TP = $15

⏰ Торговая сессия:
  ├─ Asian (00:00-09:00):    SL ×0.85, TP ×0.9
  ├─ European (07:00-16:00): SL ×1.0,  TP ×1.0
  └─ US (13:00-22:00):       SL ×1.15, TP ×1.2
```

**Пример расчета:**
```
Условия: High volatility (ATR=$8), US Session
Base: SL=$5, TP=$12
  ↓
Volatility adaptation: SL=$8, TP=$15
  ↓
Session adaptation: SL=$8×1.15=$9.2, TP=$15×1.2=$18
  ↓
Final: SL=$9.2, TP=$18
```

---

### 2.5 Результат анализа
```json
{
  "direction": "BUY",
  "entry_price": 2650.50,
  "sl": 2641.30,  // $9.2 USD
  "tp": 2668.50,  // $18 USD
  "confidence": 78,
  "reason": "Strong bullish momentum on M15/M30, RSI oversold recovery...",
  "risk_reward": 1.95,
  "timeframe": "M5",
  "timestamp": "2026-02-15T14:30:00"
}
```

**Сигнал сохраняется в AISignalManager:**
- ✅ Status: ACTIVE
- ⏳ TTL: 30 минут
- 🔄 Can requery: Yes

---

## 3. Генерация сигнала

### 3.1 Создание AI Signal
```python
AISignalManager.add_signal()
  ├─ Signal ID: uuid4()
  ├─ Status: ACTIVE
  ├─ Created: timestamp
  ├─ Expires: created + 30min
  └─ Сохранение в data/signals/ai_signals.json
```

**Signal Object:**
```python
{
  "id": "abc123",
  "symbol": "XAUUSD",
  "direction": "BUY",
  "entry_price": 2650.50,
  "sl": 2641.30,
  "tp": 2668.50,
  "confidence": 78,
  "lot_size": 0.01,
  "status": "ACTIVE",
  "created_at": "2026-02-15T14:30:00",
  "expires_at": "2026-02-15T15:00:00",
  "triggered": false
}
```

---

### 3.2 Telegram уведомление (опционально)
```
Telegram Bot отправляет:
  
📊 XAUUSD - NEW SIGNAL
Direction: BUY 🟢
Entry: 2650.50
SL: 2641.30 (-$9.2)
TP: 2668.50 (+$18)
Confidence: 78%
R:R: 1.95
Session: US 🇺🇸
```

---

## 4. Фильтрация сигнала (Multi-Layer)

### 4.1 Главный цикл LiveTrader
```python
LiveTrader.check_signals()  # каждую секунду
  ├─ Получить активные AI signals
  ├─ Для каждого сигнала:
  │   └─ execute_trade(signal)
  └─ Return
```

---

### 4.2 Pre-execution checks
```python
execute_trade(signal):
  
  1️⃣ GPT доступен?
     ├─ ❌ Нет → skip signal
     └─ ✅ Да → continue
  
  2️⃣ Уже есть позиция по этому символу?
     ├─ ❌ Да → skip signal
     └─ ✅ Нет → continue
  
  3️⃣ Сигнал уже triggered?
     ├─ ❌ Да → skip signal
     └─ ✅ Нет → continue
  
  4️⃣ Торговля включена для инструмента?
     ├─ ❌ Нет (instruments.yaml) → skip signal
     └─ ✅ Да → continue
```

---

## 5. V5 Improvements - Дополнительная фильтрация

### 5.1 Technical Confirmation Filter 🔬
```python
TechnicalConfirmation.confirm_signal()
  
🎯 Цель: Гибридная стратегия (GPT + Technical)
  
📊 Логика фильтрации:
  
  Confidence > 80%:
    └─ ✅ SKIP FILTER (доверяем GPT)
  
  Confidence 60-80%:
    └─ 🔍 ТРЕБУЕТСЯ ТЕХНИЧЕСКОЕ ПОДТВЕРЖДЕНИЕ
        
        BUY Signal:
          ✅ EMA Trend: price > EMA20 > EMA50
          ✅ RSI: 40-70 (не перекуплен)
          ✅ Price Action: последняя свеча бычья
          
        SELL Signal:
          ✅ EMA Trend: price < EMA20 < EMA50
          ✅ RSI: 30-60 (не перепродан)
          ✅ Price Action: последняя свеча медвежья
  
  Confidence < 60%:
    └─ ❌ REJECT (слишком слабый сигнал)
```

**Режимы:**
- **BALANCED** (strict_mode=False): 2 из 3 условий = OK
- **STRICT** (strict_mode=True): 3 из 3 условий обязательны

**Rejection Examples:**
```
❌ "EMA trend bearish but GPT says BUY - rejected"
❌ "RSI overbought (82), avoid BUY - rejected"
❌ "Confidence too low (55%) - rejected"
```

---

### 5.2 Session Adapter ⏰
```python
SessionAdapter.adapt_signal_parameters()
  
🌏 Определение текущей сессии (UTC):
  
  Asian (00:00-09:00):
    ├─ Min Confidence: 80%
    ├─ Lot Multiplier: ×0.8
    ├─ SL Multiplier: ×0.85
    └─ TP Multiplier: ×0.9
    
  European (07:00-16:00):
    ├─ Min Confidence: 70%
    ├─ Lot Multiplier: ×1.0
    ├─ SL Multiplier: ×1.0
    └─ TP Multiplier: ×1.0
    
  US (13:00-22:00):
    ├─ Min Confidence: 65%
    ├─ Lot Multiplier: ×1.2
    ├─ SL Multiplier: ×1.15
    └─ TP Multiplier: ×1.2
    
  Overlap (07:00-09:00, 13:00-16:00):
    ├─ Min Confidence: 60%
    ├─ Lot Multiplier: ×1.5
    ├─ SL Multiplier: ×1.1
    └─ TP Multiplier: ×1.15
```

**Пример адаптации:**
```
Input:
  Session: US (20:00 UTC)
  Confidence: 75%
  Entry: 2650.50
  SL: 2641.30 (original)
  TP: 2668.50 (original)
  Lot: 0.01

Checks:
  ✅ US session requires 65% confidence → 75% OK
  
Adaptation:
  SL: 2641.30 → (adjusted already by MarketAnalyst)
  TP: 2668.50 → (adjusted already by MarketAnalyst)
  Lot: 0.01 → 0.01 × 1.2 = 0.012
  
Output:
  ✅ Signal ALLOWED
  New params: SL=2641.30, TP=2668.50, Lot=0.012
```

**Rejection Examples:**
```
❌ "Asian session requires 80% confidence, got 75% - rejected"
❌ "Weekend detected - rejected"
```

---

### 5.3 Adaptive Lot Sizing 📊
```python
AdaptiveLotSizing.calculate_lot()
  
🎯 Цель: Умный расчет лота на основе текущей статистики
  
📈 Анализ последних 10 сделок:
  
  1️⃣ Winrate Analysis:
     ├─ Winrate > 60%: Lot ×1.3 (агрессивно)
     ├─ Winrate 40-60%: Lot ×1.0 (стандарт)
     └─ Winrate < 40%: Lot ×0.7 (консервативно)
  
  2️⃣ Streak Analysis:
     ├─ Win streak ≥ 3: Lot ×1.2
     ├─ No streak: Lot ×1.0
     └─ Loss streak ≥ 3: Lot ×0.6
  
  3️⃣ Confidence Multiplier:
     ├─ Confidence > 85%: ×1.2
     ├─ Confidence 70-85%: ×1.0
     └─ Confidence < 70%: ×0.8
  
  4️⃣ Session Multiplier (from SessionAdapter):
     └─ US session: ×1.2
  
  Final Formula:
    adaptive_lot = base_lot × winrate_mult × streak_mult × confidence_mult × session_mult
    
    Clamping:
      min_lot = 0.01
      max_lot = 0.05
```

**Пример расчета:**
```
Входные данные:
  Base lot: 0.01
  Recent trades: [WIN, WIN, LOSS, WIN, WIN, WIN, WIN, LOSS, WIN, WIN]
  Winrate: 80% (8/10)
  Current streak: +2 wins
  Confidence: 78%
  Session: US

Расчет:
  base_lot = 0.01
  winrate_mult = 1.3 (winrate > 60%)
  streak_mult = 1.0 (streak < 3)
  confidence_mult = 1.0 (70-85%)
  session_mult = 1.2 (US session)
  
  adaptive_lot = 0.01 × 1.3 × 1.0 × 1.0 × 1.2 = 0.0156
  
  Clamped: 0.0156 → 0.01 (размер лота кратен 0.01)
  
Final Lot: 0.01
```

---

### 5.4 Rejected Signals Logger 📝
```python
RejectedSignalsLogger.log_rejection()
  
📁 Файл: data/rejected_signals/rejected_202602.csv
  
Структура CSV:
  timestamp, symbol, direction, confidence, entry, sl, tp, reason, filter_type, tech_data
  
Пример записи:
  2026-02-15 14:30:00, XAUUSD, BUY, 72, 2650.50, 2641.30, 2668.50, "EMA trend bearish", technical, {"ema_trend":"bearish","rsi":45}
```

**Когда логируются отклонения:**
- ❌ Technical Filter reject
- ❌ Session Adapter reject
- ❌ Spread too high
- ❌ ML Model reject
- ❌ Insufficient confidence

**Статистика:**
```python
get_rejection_stats():
  
  Total rejected: 45
  Rejection reasons:
    - technical: 18 (40%)
    - session: 12 (27%)
    - spread: 8 (18%)
    - confidence: 7 (15%)
```

---

## 6. Исполнение сделки в MT5

### 6.1 Final Execution
```python
TradeExecutor.execute_signal(symbol, signal)
  
  1️⃣ Spread Check:
     ├─ Current spread: 2.5 pips
     ├─ Max allowed: 3.0 pips (config)
     ├─ ✅ Spread OK → continue
     └─ ❌ Spread too high → reject + log
  
  2️⃣ Prepare Order:
     ├─ Symbol: XAUUSD
     ├─ Type: BUY (ORDER_TYPE_BUY)
     ├─ Volume: 0.01 lot
     ├─ Price: Ask (2650.50)
     ├─ SL: 2641.30
     ├─ TP: 2668.50
     ├─ Magic Number: 12345
     └─ Comment: "BAZA_AI_V5"
  
  3️⃣ Send to MT5:
     └─ mt5.order_send(request)
```

**MT5 Response:**
```python
{
  "retcode": 10009,  # TRADE_RETCODE_DONE
  "deal": 54321,
  "order": 54320,
  "volume": 0.01,
  "price": 2650.55,  # actual fill price
  "comment": "Request executed"
}
```

---

### 6.2 Trade Logging
```python
Сохранение сделки:
  
  1️⃣ Internal Database:
     └─ data/trades/trades.json
  
  2️⃣ MT5 History:
     └─ Автоматически через MT5
  
  3️⃣ Telegram Notification:
     
     📊 XAUUSD - TRADE OPENED
     Direction: BUY 🟢
     Entry: 2650.55 (actual)
     Volume: 0.01 lot
     SL: 2641.30 (-$9.25)
     TP: 2668.50 (+$17.95)
     Confidence: 78%
     Time: 14:30:15 UTC
```

---

### 6.3 Signal Status Update
```python
AISignalManager.mark_as_triggered(signal_id)
  
  Signal status:
    ACTIVE → TRIGGERED ✅
    
  Timestamp:
    triggered_at = now()
    
  Больше не будет обрабатываться в check_signals()
```

---

## 7. Управление открытой позицией

### 7.1 Trailing Stop V4 (Percentage-based)
```python
TrailingStopV4.check_positions()  # каждую секунду
  
  📊 Получить открытые позиции из MT5:
    └─ position_ticket = 54321
  
  💰 Position details:
    ├─ Symbol: XAUUSD
    ├─ Type: BUY
    ├─ Entry: 2650.55
    ├─ Current: 2660.00
    ├─ SL: 2641.30 (original)
    ├─ Volume: 0.01
    └─ Profit: +$9.45
  
  📈 Calculate profit %:
    profit_pct = (current - entry) / entry × 100
    profit_pct = (2660.00 - 2650.55) / 2650.55 × 100 = 0.36%
  
  ⚙️ Config:
    activation_profit_percent: 30%
    trailing_step_percent: 10%
  
  🔍 Check activation:
    0.36% < 30% → ❌ Not activated yet
```

**После активации (profit ≥ 30%):**
```python
Current: 2700.00
Entry: 2650.55
Profit %: 1.86% ✅ > 30% → ACTIVATE

Calculate trailing SL:
  profit_distance = 2700.00 - 2650.55 = $49.45
  trailing_distance = profit_distance × (100% - 10%) = $44.51
  new_sl = entry + trailing_distance = 2650.55 + 44.51 = 2695.06
  
Modify position:
  mt5.position_modify(
    ticket=54321,
    sl=2695.06,  # new trailing SL
    tp=2668.50   # keep original TP
  )
  
✅ Trailing Stop activated at 2695.06
```

**Последующие обновления:**
```
Price: 2710.00
  → new_sl = 2650.55 + (2710.00 - 2650.55) × 0.9 = 2704.06
  → Update SL to 2704.06
  
Price: 2705.00
  → new_sl = 2704.06 (не двигаем SL вниз)
  → Keep SL at 2704.06
```

---

### 7.2 Stop Loss Protection
```python
Config (trading.yaml):
  consecutive_stops: 2
  cooldown_minutes: 10
  enabled: true

Logic:
  IF последние 2 сделки = LOSS:
    └─ ⏸️ PAUSE trading на 10 минут
    └─ 📨 Telegram: "Stop Loss Protection activated"
```

---

### 7.3 Profit Protection
```python
Config (trading.yaml):
  consecutive_wins: 3
  cooldown_minutes: 20
  enabled: true

Logic:
  IF последние 3 сделки = WIN:
    └─ ⏸️ PAUSE trading на 20 минут
    └─ 📨 Telegram: "Profit Protection - Taking break after wins"
```

---

## 8. Закрытие позиции

### 8.1 Take Profit Hit ✅
```python
MT5 automatically closes position when price hits TP:

Position:
  Entry: 2650.55
  TP: 2668.50
  Current: 2668.50 ✅ HIT
  
MT5 Action:
  └─ Close position at 2668.50
  └─ Profit: +$17.95
```

---

### 8.2 Stop Loss Hit ❌
```python
MT5 automatically closes position when price hits SL:

Position:
  Entry: 2650.55
  SL: 2641.30
  Current: 2641.30 ❌ HIT
  
MT5 Action:
  └─ Close position at 2641.30
  └─ Loss: -$9.25
```

---

### 8.3 Trailing Stop Hit 🛑
```python
Price triggered trailing SL:

Position:
  Entry: 2650.55
  Trailing SL: 2704.06
  Current: 2704.00 → 2703.50 🛑 HIT
  
MT5 Action:
  └─ Close position at 2704.06
  └─ Profit: +$53.51 (locked profit)
```

---

### 8.4 Manual Close (через GUI)
```python
User clicks "Close Position" button in GUI:
  
  BotManager.close_position(ticket=54321)
    ↓
  TradeExecutor.close_position(ticket=54321)
    ↓
  mt5.order_send({
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "XAUUSD",
    "volume": 0.01,
    "type": ORDER_TYPE_SELL,  # opposite direction
    "position": 54321,
    "comment": "Manual close"
  })
```

---

## 9. Постобработка и логирование

### 9.1 Detect Position Closed
```python
LiveTrader.check_closed_positions()  # каждую секунду
  
  1️⃣ Получить tracked positions:
     └─ Position #54321 был в tracked_positions
  
  2️⃣ Проверить MT5:
     └─ mt5.positions_get(ticket=54321)
     └─ ❌ Position not found → CLOSED
  
  3️⃣ Получить историю:
     └─ mt5.history_deals_get(position_id=54321)
     └─ Find closing deal
```

---

### 9.2 Calculate Results
```python
Closing Deal:
  ticket: 54321
  symbol: XAUUSD
  type: SELL (closing BUY)
  volume: 0.01
  price: 2668.50  # actual close price
  profit: +17.95 USD
  commission: -0.10 USD
  swap: 0.00 USD
  net_profit: +17.85 USD
  
Duration:
  opened: 2026-02-15 14:30:15
  closed: 2026-02-15 18:45:30
  duration: 4h 15m 15s
  
Pips:
  price_diff = 2668.50 - 2650.55 = 17.95
  pips = 17.95 × 100 = 1795 pips (XAUUSD)
```

---

### 9.3 Telegram Report
```
📊 XAUUSD - POSITION CLOSED

Result: ✅ PROFIT (+$17.85)
Entry: 2650.55
Exit: 2668.50
Pips: +1795
Duration: 4h 15m
Volume: 0.01 lot

Initial:
  SL: 2641.30 (-$9.25)
  TP: 2668.50 (+$17.95)
  
Actual:
  Exit: 2668.50 (Take Profit Hit)
  
Balance: $10,017.85 (+0.18%)
```

---

### 9.4 Update Statistics
```python
TradeDatabase.save_trade({
  "ticket": 54321,
  "symbol": "XAUUSD",
  "direction": "BUY",
  "entry_price": 2650.55,
  "exit_price": 2668.50,
  "volume": 0.01,
  "profit": 17.85,
  "pips": 1795,
  "duration_seconds": 15315,
  "result": "WIN",
  "exit_reason": "take_profit",
  "confidence": 78,
  "session": "US",
  "timestamp": "2026-02-15T18:45:30"
})

Statistics Update:
  total_trades: 45 → 46
  wins: 18 → 19
  losses: 27 → 27
  winrate: 40.0% → 41.3% ✅
  total_profit: +$125.40 → +$143.25
```

---

### 9.5 Auto-Requery (if enabled)
```python
Config (trading.yaml):
  auto_requery_on_close: true
  requery_cooldown_minutes: 15

Logic:
  Position closed at 18:45:30
    ↓
  Wait cooldown: 15 minutes
    ↓
  Trigger immediate analysis at 19:00:30
    ↓
  PureAITrader.analyze_symbol('XAUUSD')
    ↓
  New signal generated (if conditions met)
```

---

### 9.6 Clean Up
```python
1️⃣ Remove from tracked_positions:
   del self.tracked_positions[54321]

2️⃣ Mark AI signal as CLOSED:
   AISignalManager.mark_as_closed(signal_id)
   
3️⃣ Update GUI:
   GUI shows:
     - Open Positions: 0
     - Today P&L: +$17.85
     - Total Trades: 46
```

---

## 10. Цикл повторяется

### 10.1 Следующий анализ
```
⏰ Scheduler ждет следующего интервала:
  
  Последний анализ: 14:30:00
  Интервал: 2 часа
  Следующий: 16:30:00
  
  ИЛИ
  
  Auto-requery после закрытия позиции:
    Closed at: 18:45:30
    Cooldown: 15 минут
    Next analysis: 19:00:30
```

---

### 10.2 Trading Hours Check
```python
Блокировка торговли в определенные часы:

Выходные:
  ├─ Saturday 00:00 - Sunday 23:59 → ❌ NO TRADING
  └─ Reason: Рынки закрыты

Ночь (будни):
  ├─ 23:30 - 01:10 UTC → ❌ NO TRADING
  └─ Reason: Низкая ликвидность

Разрешенные часы:
  ├─ Monday 01:10 - 23:30
  ├─ Tuesday-Thursday 00:00 - 23:30
  └─ Friday 00:00 - 23:00
```

---

### 10.3 System Monitoring
```python
Continuous checks:
  
  🔄 Every 1 second:
    ├─ check_signals() - проверка активных сигналов
    ├─ check_trailing_stop() - обновление trailing SL
    └─ check_closed_positions() - детект закрытия
  
  ⏰ Every 2 hours:
    └─ analyze_market() - GPT-4 анализ
  
  📊 Every 5 minutes:
    └─ FALLBACK check (если нет позиций/сигналов)
  
  📱 Every day at 23:55:
    └─ Send daily report to Telegram
```

---

## 📈 Визуальная схема полного цикла

```
  START BOT
      ↓
  ┌─────────────────────────────────────┐
  │  1. INITIALIZATION                  │
  │  - Connect MT5                      │
  │  - Check OpenAI API                 │
  │  - Load configs                     │
  │  - Init V5 modules                  │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  2. MARKET ANALYSIS (every 2h)      │
  │  - Capture MT5 screenshots          │
  │  - GPT-4 Vision analysis            │
  │  - Adaptive SL/TP calculation       │
  │  - Generate AI signal               │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  3. SIGNAL GENERATION               │
  │  - Create AI Signal                 │
  │  - Set TTL (30 min)                 │
  │  - Save to AISignalManager          │
  │  - Send Telegram notification       │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  4. PRE-EXECUTION FILTERS           │
  │  ✅ GPT available?                   │
  │  ✅ No existing position?            │
  │  ✅ Signal not triggered?            │
  │  ✅ Trading enabled for symbol?      │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  5. V5 IMPROVEMENTS FILTERS         │
  │                                     │
  │  ┌─ Technical Confirmation ────────┐│
  │  │  EMA, RSI, Price Action check  ││
  │  │  ✅ CONFIRMED / ❌ REJECTED     ││
  │  └────────────────────────────────┘│
  │           ↓                         │
  │  ┌─ Session Adapter ───────────────┐│
  │  │  Check session requirements    ││
  │  │  Adapt SL/TP/Lot by session    ││
  │  │  ✅ ALLOWED / ❌ REJECTED       ││
  │  └────────────────────────────────┘│
  │           ↓                         │
  │  ┌─ Adaptive Lot Sizing ───────────┐│
  │  │  Analyze recent 10 trades      ││
  │  │  Calculate optimal lot         ││
  │  │  Winrate/Streak/Confidence     ││
  │  └────────────────────────────────┘│
  │           ↓                         │
  │  ┌─ Rejected Logger ────────────────┐│
  │  │  Log rejection if any filter   ││
  │  │  fails (CSV + stats)           ││
  │  └────────────────────────────────┘│
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  6. EXECUTION IN MT5                │
  │  ✅ Spread check (< 3 pips)          │
  │  📤 Send order to MT5                │
  │  ✅ Order filled                     │
  │  💾 Save trade to database           │
  │  📱 Telegram: Trade Opened           │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  7. POSITION MANAGEMENT             │
  │                                     │
  │  ┌─ Trailing Stop V4 ──────────────┐│
  │  │  Monitor profit % (activate 30%)││
  │  │  Update SL every second         ││
  │  │  Trail by 10% of profit         ││
  │  └────────────────────────────────┘│
  │                                     │
  │  ┌─ Stop Loss Protection ──────────┐│
  │  │  Count consecutive stops        ││
  │  │  Pause if ≥2 stops              ││
  │  └────────────────────────────────┘│
  │                                     │
  │  ┌─ Profit Protection ─────────────┐│
  │  │  Count consecutive wins         ││
  │  │  Pause if ≥3 wins               ││
  │  └────────────────────────────────┘│
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  8. POSITION CLOSED                 │
  │  ✅ Take Profit hit                  │
  │  ❌ Stop Loss hit                    │
  │  🛑 Trailing Stop triggered         │
  │  👤 Manual close by user            │
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  9. POST-PROCESSING                 │
  │  - Detect close in MT5 history      │
  │  - Calculate profit/loss            │
  │  - Update statistics                │
  │  - Send Telegram report             │
  │  - Trigger auto-requery (if enabled)│
  └─────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────┐
  │  10. CYCLE REPEATS                  │
  │  ⏰ Wait for next analysis (2h)      │
  │  🔄 Or auto-requery (15min cooldown)│
  │  📊 FALLBACK: No positions (5min)   │
  └─────────────────────────────────────┘
      ↓
    (GOTO 2. MARKET ANALYSIS)
```

---

## 🎯 Ключевые метрики производительности

### V4.0 (До улучшений)
```
Winrate: 20.5%
Avg Profit/Win: $18.50
Avg Loss/Loss: -$8.20
Total Trades: 156
Net Profit: -$245.60
Проблемы:
  - Фиксированные SL/TP ($5/$10)
  - Нет технической фильтрации
  - Нет адаптации под сессии
```

### V5.0 (После улучшений)
```
Target Winrate: 35-40%
Improvements:
  ✅ Adaptive SL/TP (ATR + Session)
  ✅ Technical Confirmation Filter
  ✅ Session Adapter
  ✅ Adaptive Lot Sizing
  ✅ Rejected Signals Logging
  ✅ Spread filter (3 pips max)
  ✅ TTL increased (30 min)
  ✅ Analysis interval (2h)
```

---

## 📊 Файлы и директории

### Конфигурация
```
config/
  ├─ ai.yaml              - GPT-4 настройки
  ├─ trading.yaml         - Торговые параметры + V5 config
  ├─ instruments.yaml     - XAUUSD, EURUSD настройки
  ├─ mt5.yaml             - MetaTrader 5 подключение
  └─ telegram.yaml        - Telegram bot настройки
```

### Данные
```
data/
  ├─ charts/              - MT5 скриншоты
  ├─ signals/             - AI сигналы (JSON)
  ├─ trades/              - История сделок
  └─ rejected_signals/    - Отклоненные сигналы (CSV)
```

### Логи
```
logs/
  ├─ bot.log              - Основной лог
  ├─ trades.log           - Логи сделок
  └─ errors.log           - Ошибки
```

---

## 🚀 Команды управления

### Запуск
```powershell
# Windows PowerShell
.\run.ps1
```

### GUI Controls
```
▶ START BOT     - Запуск торгового цикла
■ STOP BOT      - Остановка бота
⚙ Settings      - Открыть настройки (включая V5)
📊 Statistics   - Просмотр статистики
```

### Настройки V5 в GUI
```
Settings → 🚀 V5 Improvements

1️⃣ Technical Filter:
   [✓] Включить
   [ ] Strict Mode

2️⃣ Session Adapter:
   [✓] Включить

3️⃣ Adaptive Lot:
   [✓] Включить
   Base Lot: [0.01]
   Max Lot:  [0.05]
   Lookback: [10]

4️⃣ Rejected Logger:
   [✓] Включить
   
[Apply & Restart] - Применить и перезапустить бота
```

---

## 📚 Дополнительная документация

- [V5_IMPROVEMENTS.md](V5_IMPROVEMENTS.md) - Детальное описание V5 модулей
- [LOT_SIZE_GUIDE.md](LOT_SIZE_GUIDE.md) - Руководство по размеру лота
- [README.md](../README.md) - Общая информация о проекте

---

## ⚠️ Важные замечания

### Risk Management
```
⚠️ ВСЕГДА используйте DEMO аккаунт для тестирования!
⚠️ Не рискуйте средствами, которые не можете потерять
⚠️ Установите max_lot в V5 Adaptive Lot для контроля рисков
⚠️ Мониторьте rejected_signals/ для анализа фильтрации
```

### Системные требования
```
✅ Windows 10/11
✅ MetaTrader 5 (terminal64.exe)
✅ Python 3.10+
✅ Stable internet connection
✅ OpenAI API key (with GPT-4 access)
```

### Известные ограничения
```
❌ Не торгует на выходных (рынки закрыты)
❌ Блокировка ночью 23:30-01:10 UTC
❌ Максимум 1 позиция на инструмент одновременно
❌ Stop Loss Protection: пауза после 2 стопов подряд
```

---

## 🎉 Заключение

Данный roadmap описывает **полный торговый цикл** BAZA Trading Bot V5.0 от момента запуска до закрытия позиции и начала нового цикла.

**Ключевые преимущества V5:**
- 🤖 Гибридная стратегия (AI + Technical)
- ⏰ Адаптация под торговые сессии
- 📊 Умный расчет размера лота
- 📝 Детальное логирование для анализа
- 🎯 Цель: увеличить winrate с 20% до 35-40%

**Удачной торговли! 🚀📈**

---

*Документ создан: 15.02.2026*  
*Версия: V5.0*  
*Автор: BAZA Development Team*

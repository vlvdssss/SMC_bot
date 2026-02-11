# 🤖 Полная информация об анализе GPT

## 📅 Последний анализ
- **Файл**: `analysis_20260210_085534.json`
- **Время**: 2026-02-10 08:55:34
- **Скриншот**: `XAUUSD_M5_20260210_085527.png`

---

## 📸 Последний скриншот
**Путь**: `C:\Users\kamsa\Desktop\BAZA\data\screenshots\XAUUSD_M5_20260210_085527.png`

**Характеристики**:
- Таймфрейм: M5 (5-минутные свечи)
- Количество баров: 200 (≈16 часов истории)
- Формат: PNG, base64 кодирование
- Передается в GPT API с параметром `detail: "high"`

---

## 📤 Что мы ОТПРАВЛЯЕМ в GPT

### 1. System Message
```
You are an expert forex/gold trader. Always respond in valid JSON format.
```

### 2. User Prompt (ПОЛНЫЙ ТЕКСТ)

```
You are an expert forex/gold scalper trading on M5 timeframe. Analyze ONLY the M5 chart and give a fast decision.

**SYMBOL:** XAUUSD
**TIMESTAMP:** 2026-02-10 08:55:27

**M5 TECHNICAL DATA:**
- Current Price: $5024.00
- ATR: $2.80 (0.06%)
- Trend (EMA 12/26): bearish
- Recent Range: $5011.42 - $5045.59 (last 50 M5 candles = ~4 hours)
- Premium/Discount: 0.632 (0=support, 1=resistance)
- Volatility: 0.15%
- EMA Fast: $5024.50
- EMA Slow: $5026.30

**M5 CHART:**
You will receive ONE screenshot of M5 timeframe (last 200 candles = ~16 hours).

**HIGH-IMPACT NEWS:**
No significant news in next 12 hours

**YOUR TASK:**
Look at the LAST 20-30 M5 candles. Find quick scalping setups based on:
- Recent support/resistance bounces
- 2-3 candle reversal patterns
- EMA crossovers
- Quick momentum shifts

**TRADING RULES (V4 M5 SCALPING - FIXED SL/TP FROM CONFIG):**
- **SL/TP are FIXED** by user config (you don't set them)
- **BUY ONLY if**: 
  - Strong bounce from recent low with 2-3 solid green candles
  - Clear upward momentum on M5 (not just single spike)
  - Price structure shows higher lows forming
- **SELL ONLY if**: 
  - Clear rejection at recent high with 2-3 solid red candles
  - Clear downward momentum on M5 (not just single drop)
  - Price structure shows lower highs forming
- **WAIT if**: 
  - Choppy/overlapping candles (consolidation)
  - No clear direction in last 10 candles
  - Price ping-ponging in tight range

**CRITICAL IMPROVEMENTS:**
1. **M5 MOMENTUM FOCUS**: Only trade when last 5-10 candles show clear direction
2. **AVOID CHOPPY MARKETS**: Skip if candles overlap/indecisive
3. **VOLATILITY CHECK**: Skip if ATR too high (>$7) - volatile spikes can hit stop then reverse
4. **STRUCTURE MATTERS**: Look for higher lows (BUY) or lower highs (SELL)
5. **PATIENCE**: Better to miss trade than force entry in unclear market
6. Entry quality MUST be "optimal" - skip "fair" or "good" setups

**RESPONSE FORMAT (JSON ONLY):**
{
  "timestamp": "2026-01-27T12:00:00",
  "symbol": "XAUUSD",
  "decision": {
    "action": "BUY|SELL|NONE",
    "confidence": 75,
    "block": "NONE",
    "reasoning": "Brief explanation (1-2 sentences max)"
  },
  "trade": {
    "entry": 2665.0,
    "stop_loss": 2660.0,
    "take_profit": 2675.0,
    "risk_reward": 2.0
  },
  "analysis": {
    "trend": "bullish|bearish|neutral",
    "key_level": "Support $2660 / Resistance $2670",
    "entry_quality": "optimal|good|fair"
  }
}

**CRITICAL (V4 REQUIREMENTS):**
1. **SL/TP will be calculated by system** - just provide entry price and direction
2. Entry must be close to current price (within $1)
3. **ALWAYS return BUY or SELL** - even in uncertain conditions, pick the most likely direction
4. Focus on LAST 20-30 candles only (not full chart history)
5. Look for quick reversals and momentum - this is scalping!
6. Return ONLY valid JSON, no extra text

**EXAMPLES OF GOOD M5 SETUPS:**
- Price touched recent low ($2660), bounced with 3+ strong green candles, forming higher low → BUY
- Price rejected recent high ($2670), dropped with 3+ strong red candles, forming lower high → SELL
- Last 5 candles show clear upward momentum, pullback to support → BUY
- Last 5 candles show clear downward momentum, rejection at resistance → SELL
- **SKIP WEAK SETUPS**: Single candle moves, overlapping candles, or choppy 10-candle range

**RISK MANAGEMENT PRIORITY:**
- **Preserve capital first**: Only take high-quality setups with clear directional bias
- **M5 SCALPING = MOMENTUM TRADING**: Need clear directional move, not guessing reversals
- **Better to miss a trade than take a bad one**
- Let trailing stop (40% activation) protect profits

Analyze the M5 chart NOW and give your decision!
```

### 3. Скриншот M5
- **Формат**: Base64-encoded PNG
- **Размер**: ~200 KB
- **Детали**: "high" (максимальное разрешение для анализа)

---

## 📥 Что GPT ОТВЕЧАЕТ

### Последний ответ (2026-02-10 08:55:34):

```json
{
  "timestamp": "2026-02-10T08:55:27",
  "symbol": "XAUUSD",
  "decision": {
    "action": "SELL",
    "confidence": 80.0,
    "block": "NONE",
    "reasoning": "Recent rejection at resistance with clear downward momentum and lower highs forming."
  },
  "trade": {
    "entry": 5024.0,
    "stop_loss": 5028.0,
    "take_profit": 5009.0,
    "risk_reward": 3.75
  },
  "analysis": {
    "trend": "bearish",
    "key_level": "Support $5011.42 / Resistance $5045.59",
    "entry_quality": "optimal"
  },
  "analyzed_at": "2026-02-10T08:55:33.790355",
  "analysis_version": "4.0",
  "prompt_version": "2026-01-V4",
  "signal_processing": {
    "action": "SELL",
    "confidence": 80.0,
    "symbol": "XAUUSD",
    "entry_allowed": true,
    "lot_multiplier": 1.5,
    "block_reason": null,
    "accuracy": "very_high",
    "quality": "good",
    "risk_mode": "balanced",
    "signals_created": 1,
    "signal_id": "XAUUSD_20260210_085533"
  }
}
```

---

## 🔧 Параметры API

### OpenAI API Call
```python
model = "gpt-4o"  # GPT-4 Omni (с Vision)
max_tokens = 4000
temperature = 0.4  # Консервативная (меньше креативности, больше точности)
```

### Retry Logic
- **Максимум попыток**: 3
- **Задержка**: 2 секунды (exponential backoff для rate limit)
- **Обрабатываемые ошибки**:
  - RateLimitError (квота исчерпана)
  - APIConnectionError (нет интернета)
  - Timeout (слишком долгий ответ)
  - APIError (серверные ошибки)

---

## 📊 Процесс анализа (пошагово)

### 1. Захват данных (5 сек)
```python
# Скриншот M5
screenshots = capture_chart(symbol="XAUUSD", timeframe=M5, bars=200)

# Метрики M5
metrics = {
    "current_price": 5024.0,
    "atr": 2.80,
    "trend": "bearish",  # EMA 12/26 cross
    "high_recent": 5045.59,  # Last 50 M5 (~4h)
    "low_recent": 5011.42,
    "premium_discount": 0.632,  # 0=support, 1=resistance
    "volatility_pct": 0.15,
    "ema_fast": 5024.50,
    "ema_slow": 5026.30
}

# Новости (высокий импакт только)
news = get_high_impact_events(hours_ahead=12)  # Top 5
```

### 2. Формирование промпта (1 сек)
```python
prompt = build_analysis_prompt(symbol, metrics, news)
# Содержит:
# - Текущие данные M5
# - Инструкции по скальпингу
# - Правила входа BUY/SELL
# - Примеры хороших сетапов
# - Формат JSON ответа
```

### 3. Вызов GPT API (2-5 сек)
```python
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Expert trader..."},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{screenshot}",
                "detail": "high"
            }}
        ]}
    ],
    max_tokens=4000,
    temperature=0.4
)
```

### 4. Парсинг ответа (1 сек)
```python
# Извлечение JSON из markdown (если обернут)
if content.startswith("```"):
    content = extract_json(content)

# Парсинг JSON
analysis = json.loads(content)

# Валидация полей
validated = validate_analysis(analysis, metrics)
```

### 5. Обработка сигнала (1 сек)
```python
# Проверка confidence (нужен >= 80%)
if analysis["decision"]["confidence"] < 80:
    skip_signal()

# Создание AI сигнала
signal = AISignal(
    symbol="XAUUSD",
    type=analysis["decision"]["action"],  # BUY/SELL
    entry_price=analysis["trade"]["entry"],
    sl=analysis["trade"]["stop_loss"],
    tp=analysis["trade"]["take_profit"],
    confidence=analysis["decision"]["confidence"],
    reasoning=analysis["decision"]["reasoning"],
    ttl_minutes=15  # Signal expires in 15 minutes
)

# Сохранение в SignalManager
signal_manager.add_signal(signal)
```

---

## 🎯 Ключевые моменты

### Что GPT видит:
1. ✅ **M5 скриншот** (200 баров ≈ 16 часов)
2. ✅ **Технические данные** (цена, ATR, EMA, тренд, S/R)
3. ✅ **Новости** (только высокий импакт)
4. ✅ **Четкие правила** (когда BUY, когда SELL, когда WAIT)
5. ✅ **Примеры** хороших сетапов

### Что GPT НЕ видит:
- ❌ Историю прошлых сделок
- ❌ Текущий депозит
- ❌ Открытые позиции (блокировка на уровне кода)
- ❌ Другие таймфреймы (только M5)

### Фильтры ПОСЛЕ GPT:
1. **Confidence >= 80%** (было 70%, усилено сегодня)
2. **Entry quality = "optimal"** (skip "fair", "good")
3. **Нет открытых позиций** (v2.0 logic)
4. **Не ночное время** (23:30-01:10)
5. **ATR не слишком высокий** (проверка в GPT промпте)

---

## 📁 Где найти данные

### Анализы GPT:
```
data/ai_analysis/analysis_YYYYMMDD_HHMMSS.json
```

### Скриншоты:
```
data/screenshots/XAUUSD_M5_YYYYMMDD_HHMMSS.png
```

### Последний скриншот (прямая ссылка):
```
C:\Users\kamsa\Desktop\BAZA\data\screenshots\XAUUSD_M5_20260210_085527.png
```

---

## 🔍 Как посмотреть последний анализ

### PowerShell:
```powershell
# Получить последний анализ
Get-ChildItem data\ai_analysis -Filter "analysis_*.json" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 | 
    ForEach-Object { Get-Content $_.FullName | ConvertFrom-Json | ConvertTo-Json -Depth 10 }

# Получить последний скриншот
Get-ChildItem data\screenshots -Filter "*.png" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 | 
    ForEach-Object { Start-Process $_.FullName }
```

### Python:
```python
import json
from pathlib import Path

# Последний анализ
analyses = sorted(Path("data/ai_analysis").glob("analysis_*.json"))
with open(analyses[-1]) as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))

# Последний скриншот
screenshots = sorted(Path("data/screenshots").glob("*.png"))
print(f"Latest screenshot: {screenshots[-1]}")
```

---

**Обновлено**: 2026-02-10 09:15

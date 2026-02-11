# V5 SAFE Architecture Guide

**Version:** 1.0  
**Date:** 2026-02-10  
**Status:** ✅ Implementation Complete

---

## 🎯 Overview

V5 SAFE is a **capital preservation upgrade** to the trading system. The core philosophy: **BLOCK trades in unclear markets** instead of forcing BUY/SELL decisions.

### Key Changes from V4

| Feature | V4 (Legacy) | V5 SAFE |
|---------|-------------|---------|
| **Trading Philosophy** | Always give BUY/SELL | Can BLOCK trades |
| **BLOCK States** | 3 (NONE, SOFT, HARD) | 8 (+ 5 V5 states) |
| **Mid-range Trading** | Allowed | Blocked if 30-70% |
| **Momentum Check** | Loose | Requires 4/5 candles |
| **WATCH Mode** | No | Yes (delayed entry) |
| **Default Bias** | Bearish | Neutral (no forced direction) |
| **Capital Priority** | Trade frequency | Preservation |

---

## 🚫 V5 SAFE BLOCK States

GPT can now **disqualify** trades using 6 new BLOCK states:

### 1. **MARKET_UNCLEAR**
- EMAs overlapping (< $0.50 apart)
- Both EMAs flat/horizontal
- **Example:** EMA12=$2665, EMA26=$2664.80 → BLOCK

### 2. **NO_MOMENTUM**
- Less than 4/5 last candles in same direction
- Average body size < previous 10-candle average
- Strong opposing wicks present
- **Example:** Last 5 candles: 3 green, 2 red → BLOCK (need 4/5)

### 3. **MID_RANGE**
- Price between 30% and 70% of recent M5 range
- **Calculation:** (current - low) / (high - low)
- **Confidence** forced ≤ 65% in mid-range
- **Example:** Range $2660-$2680, price $2670 (50%) → BLOCK

### 4. **CHOPPY_PRICE**
- Last 10 candles overlapping (no clear HH/LL)
- Price ping-ponging in tight range
- **Example:** 10 candles within $2 range with no trend → BLOCK

### 5. **LOW_QUALITY_SETUP**
- Entry quality rated "fair" or lower
- Forced/guessed signal (uncertainty)
- **Example:** "Could be BUY but setup is mediocre" → BLOCK

### 6. **NONE**
- No blocks detected
- Trade allowed (V4 behavior)

---

## 👁️ WATCH Mode

### Concept
Instead of immediate BUY/SELL, GPT can set a **WATCH** for delayed entry:

```json
{
  "decision": {
    "action": "NONE",  // Don't trade NOW
    "block": "NONE"
  },
  "watch": {
    "enabled": true,
    "key_level": 2665.0,  // Wait for this price
    "direction": "BUY",   // Direction when triggered
    "valid_minutes": 10   // Expires after 10 min
  }
}
```

### How It Works

1. **GPT sees setup forming** but not ready yet
2. **Sets WATCH** at key support/resistance
3. **System monitors** price every tick
4. **Executes trade** only if price confirms key level
5. **Expires** if not triggered within N minutes

### WATCH Example

**Scenario:** Price approaching support at $2665
- **Current:** $2668
- **GPT:** "Potential bounce if $2665 holds"
- **V4 behavior:** Force BUY now → Enters early → Loss
- **V5 SAFE behavior:** WATCH at $2665 for BUY → Waits → Confirms → Enters

---

## 📊 Market State Rules

V5 SAFE enforces strict market conditions:

### Mid-Range Check
```python
premium_discount = (current_price - low_recent) / (high_recent - low_recent)

if 0.30 <= premium_discount <= 0.70:
    # MID-RANGE DANGER ZONE
    → BLOCK = "MID_RANGE"
    → Confidence ≤ 65%
```

### Momentum Validation
```
Last 5 M5 candles:
- Count bullish/bearish candles
- Require 4/5 in same direction (80%)
- Check average body size vs previous 10

If momentum < 80%:
    → BLOCK = "NO_MOMENTUM"
```

### EMA Overlap Detection
```python
ema_fast = 2665.0
ema_slow = 2664.5
gap = abs(ema_fast - ema_slow)  # $0.50

if gap < 0.50:  # Too close
    → BLOCK = "MARKET_UNCLEAR"
```

---

## 🔧 Toggle V5 SAFE On/Off

### Enable V5 SAFE (Default)
```python
# src/ai/market_analyst.py, line 36
USE_V5_SAFE = True  # V5 SAFE mode
```

### Revert to V4 Legacy
```python
# src/ai/market_analyst.py, line 36
USE_V5_SAFE = False  # V4 legacy prompt
```

**No other changes needed** - system automatically routes to correct prompt.

---

## 🎯 V5 SAFE Prompt Structure

### Phase 1: TRY TO BLOCK (Priority)
```
1. Check mid-range (30-70%) → BLOCK?
2. Check momentum (4/5 candles) → BLOCK?
3. Check EMAs (overlap?) → BLOCK?
4. Check choppiness → BLOCK?
5. Check setup quality → BLOCK?
```

### Phase 2: Analyze (Only if no BLOCKS)
```
IF all checks pass:
    - Analyze BUY conditions
    - Analyze SELL conditions
    - Set WATCH if not ready
    - Generate signal
```

### Key Difference from V4
- **V4:** "Give me BUY or SELL"
- **V5:** "Try to disqualify first, trade only if clear"

---

## 📈 Expected Behavior Changes

### Trade Frequency
- **V4:** ~30-40 signals/day
- **V5:** ~15-25 signals/day (50% reduction)
- **Goal:** Quality > Quantity

### Win Rate
- **V4:** 38-45% (recent performance)
- **V5:** Target 55-65% (blocked bad trades)

### Confidence Distribution
- **V4:** Many 70-80% signals
- **V5:** More 80-90% signals (only high-quality)

### BLOCK Reasons (Expected)
- **MID_RANGE:** 30% of blocks
- **NO_MOMENTUM:** 25%
- **MARKET_UNCLEAR:** 20%
- **CHOPPY_PRICE:** 15%
- **LOW_QUALITY_SETUP:** 10%

---

## 🛠️ Implementation Details

### Files Modified

1. **src/ai/market_analyst.py**
   - Line 36: `USE_V5_SAFE = True` toggle
   - Lines 267-273: Prompt routing logic
   - Lines 381-520: `_build_v5_safe_prompt()` method
   - Lines 742-749: V5 BLOCK validation
   - Lines 757-795: WATCH validation

2. **src/ai/signal_manager.py**
   - Line 104: `active_watches: List[Dict]` storage
   - Lines 443-462: V5 BLOCK processing
   - Lines 300-323: WATCH registration logic
   - Lines 541-619: `check_watches()` method

3. **backup_v4/** (Safety backup)
   - `market_analyst_v4_backup.py`
   - `signal_manager_v4_backup.py`
   - `analyst_scheduler_v4_backup.py`

### Backward Compatibility
- V4 logic **fully preserved** in backup_v4/
- Toggle `USE_V5_SAFE = False` to revert instantly
- No breaking changes to existing code

---

## 🚀 Usage Examples

### Example 1: Mid-Range BLOCK
**Input:**
- Current: $2670
- Range: $2660-$2680 (premium 50%)

**V4 Response:**
```json
{
  "decision": {"action": "SELL", "confidence": 75},
  "reasoning": "Mid-range resistance"
}
```

**V5 SAFE Response:**
```json
{
  "decision": {
    "action": "NONE",
    "confidence": 60,
    "block": "MID_RANGE",
    "reasoning": "Price in mid-range - waiting for clear direction"
  }
}
```

### Example 2: WATCH Mode
**Input:**
- Current: $2668
- Support: $2665

**V4 Response:**
```json
{"decision": {"action": "BUY", "confidence": 72}}
```
→ Enters at $2668, stop hunted at $2665

**V5 SAFE Response:**
```json
{
  "decision": {"action": "NONE", "block": "NONE"},
  "watch": {
    "enabled": true,
    "key_level": 2665.0,
    "direction": "BUY",
    "valid_minutes": 10
  }
}
```
→ Waits for $2665 confirmation → Better entry

### Example 3: No Momentum BLOCK
**Last 5 candles:** +3, -2, +1, -4, +2 (mixed)

**V4 Response:**
```json
{"decision": {"action": "SELL", "confidence": 70}}
```
→ Forces direction despite no momentum

**V5 SAFE Response:**
```json
{
  "decision": {
    "action": "NONE",
    "block": "NO_MOMENTUM",
    "reasoning": "Only 3/5 candles directional (need 4/5)"
  }
}
```
→ Blocks uncertain trade

---

## 📊 Monitoring V5 SAFE

### Log Messages

**BLOCK Activated:**
```
[AI-Signal] 🚫 V5 SAFE BLOCK: MID_RANGE - Trading blocked (capital preservation)
```

**WATCH Registered:**
```
[AI-Signal] 👁️ Watching XAUUSD at $2665.0 for BUY (valid 10 min)
```

**WATCH Triggered:**
```
[AI-Signal] ✅ BUY WATCH triggered: Price $2664.50 <= $2665.00
[AI-Signal] 🎯 WATCH converted to signal: BUY XAUUSD @ $2664.50
```

**WATCH Expired:**
```
[AI-Signal] ⏰ WATCH expired for XAUUSD at $2665.0 (BUY)
```

### Dashboard (Future)
- BLOCK reason distribution chart
- WATCH conversion rate
- V5 vs V4 performance comparison
- Capital preservation metrics

---

## 🔬 Testing Plan

### Day 1-2: Monitor BLOCK Frequency
- Are too many trades blocked?
- Are BLOCKS preventing bad trades?
- Adjust thresholds if needed

### Day 3-5: WATCH Mode Analysis
- How many WATCHes convert to trades?
- WATCH vs immediate entry performance
- Optimal WATCH duration

### Week 1: Performance Comparison
- V5 winrate vs V4 baseline (38%)
- Drawdown reduction
- Capital preservation effectiveness

### Adjustments
If V5 too conservative:
- Relax mid-range from 30-70% to 25-75%
- Lower momentum requirement from 4/5 to 3/5
- Reduce EMA overlap threshold

If V5 still trading too much:
- Tighten mid-range to 35-65%
- Require 5/5 momentum unanimity
- Add volatility BLOCK (ATR > threshold)

---

## 🎓 Philosophy

### V4: Trade Machine
- Goal: Generate signals constantly
- Bias: Always have a position
- Risk: Over-trading, low-quality entries

### V5 SAFE: Capital Guardian
- Goal: Preserve capital first
- Bias: Trade only when clear
- Risk: Missing some opportunities (acceptable)

### Core Principle
> **"Better to miss a trade than lose capital."**

---

## 🔐 Safety Guarantees

1. **V4 Backup:** Full implementation in backup_v4/
2. **Instant Rollback:** `USE_V5_SAFE = False` reverts to V4
3. **No Data Loss:** All existing signals/history preserved
4. **Gradual Adoption:** Can test V5 for hours, revert if issues
5. **Logging:** All BLOCK reasons logged for analysis

---

## 📞 Support

### Toggle V5 SAFE
Edit [`src/ai/market_analyst.py`](../src/ai/market_analyst.py) line 36:
```python
USE_V5_SAFE = True   # V5 SAFE mode (capital preservation)
USE_V5_SAFE = False  # V4 legacy mode (trade frequency)
```

### Rollback to V4
```powershell
# Copy backup files back
Copy-Item backup_v4\market_analyst_v4_backup.py src\ai\market_analyst.py -Force
Copy-Item backup_v4\signal_manager_v4_backup.py src\ai\signal_manager.py -Force
```

### Monitor Logs
```powershell
Get-Content logs\baza_*.log -Tail 50 -Wait | Select-String "V5 SAFE|WATCH|BLOCK"
```

---

## ✅ Completion Checklist

- [x] Backup V4 implementation
- [x] Add USE_V5_SAFE toggle
- [x] Implement _build_v5_safe_prompt()
- [x] Update response validation (BLOCK + WATCH)
- [x] Add V5 BLOCK processing
- [x] Implement WATCH storage
- [x] Create check_watches() method
- [x] Document V5 SAFE architecture
- [ ] Test V5 vs V4 behavior (24-hour trial)
- [ ] Monitor BLOCK distribution
- [ ] Analyze WATCH conversion rate
- [ ] Create GUI controls (future)

---

## 🎉 Summary

V5 SAFE is **live and ready** to reduce losses by blocking low-quality trades. The system will now:
1. **Try to BLOCK first** before analyzing
2. **Enforce strict market conditions**
3. **Use WATCH mode** for delayed entries
4. **Preserve capital** over generating trades

**No restart needed** - changes are in `market_analyst.py` and `signal_manager.py`. Next GPT analysis cycle will use V5 SAFE logic automatically.

**Recommended:** Monitor for 24 hours, compare V5 vs V4 performance, adjust thresholds as needed.

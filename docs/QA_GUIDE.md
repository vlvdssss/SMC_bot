# Trading Bot QA & Verification Guide

## 📋 Overview

This guide explains how to use the comprehensive QA infrastructure to verify that GUI settings **actually affect trading logic** before going live.

**Goal:** Remove guesswork and provide evidence-based proof that configuration changes work as intended.

---

## 🧪 QA Tools Available

### 1. **DRY_RUN Mode**
- **Purpose:** Simulate all trading logic without sending real orders to MT5
- **Location:** Settings → Trading tab → "🧪 DRY RUN Mode"
- **Behavior:**
  - All analysis runs normally (GPT, filters, gates)
  - Instead of `order_send`, logs `WOULD_SEND_ORDER`
  - Status shows `SIMULATED` instead of `ORDERING/TRADING`
  - Decision logs capture all decisions without risk

### 2. **Show Effective Config** 🔍
- **Purpose:** Display actual runtime configuration values
- **Location:** Control Panel → "🔍 Show Effective Config" button
- **Features:**
  - Tree view of all config files
  - Search/filter specific settings
  - Export to YAML
  - Copy to clipboard
  - **Use this to verify settings actually changed after Save**

### 3. **Explain Last Decision** 💬
- **Purpose:** Detailed breakdown of the last trading decision
- **Location:** Control Panel → "💬 Explain Last Decision" button
- **Shows:**
  - Signal ID & timestamp
  - GPT analysis (action, confidence, reasoning)
  - Filter results (pass/fail for each filter)
  - Setup score
  - Final decision (ENTER/HOLD/BLOCK) + reason
  - **Use this to understand why bot acted/didn't act**

### 4. **Automated QA Test Suite**
- **Purpose:** Run comprehensive test matrix programmatically
- **Location:** `src/qa/qa_test_suite.py`
- **Run:** `python -m src.qa.qa_test_suite [--skip-integration]`
- **Output:** JSON + Markdown reports in `data/qa_reports/`

---

## 🎯 Pre-Trade Verification Workflow

### Step 1: Enable DRY_RUN Mode

1. Open GUI Settings (⚙️ button)
2. Go to **Trading** tab
3. Check **"🧪 DRY RUN Mode"**
4. Click **Save**
5. Verify in logs: `[SETTINGS] dry_run: false → true`

**Expected Result:** Bot runs normally but doesn't send real orders.

---

### Step 2: Verify Configuration Changes

**Test Matrix (run each test independently):**

#### T1: High Confidence Threshold
1. **Change:** Settings → AI → Min Confidence = 99%
2. **Save** → Check logs for `min_confidence: 70 → 99`
3. **Verify:** Click "🔍 Show Effective Config" → search "min_confidence" → confirm shows `99`
4. **Test:** Run 1-2 analysis cycles
5. **Check:** "💬 Explain Last Decision" → should show BLOCK due to confidence < 99

#### T2: Low Confidence Threshold
1. **Change:** Min Confidence = 50%
2. **Verify:** Effective Config shows `50`
3. **Test:** Run analysis
4. **Expected:** Signals with confidence >= 50% now allowed through

#### T3: Extreme Cooldown
1. **Change:** Settings → Risk → Stop Loss Protection → Cooldown = 999 minutes
2. **Verify:** Effective Config → `stop_loss_protection.cooldown_minutes = 999`
3. **Test:** Trigger 1 stop loss (or simulate)
4. **Expected:** Next 999 minutes, all trades BLOCKED with "cooldown active" reason

#### T4: Daily Limit
1. **Change:** Max Trades/Day = 1
2. **Verify:** Effective Config shows limit
3. **Test:** Run until 1 SIMULATED trade executes
4. **Expected:** All subsequent attempts BLOCKED by daily limit

#### T5: GPT Gate Toggle
1. **Change:** Settings → AI → AI Enabled = OFF
2. **Verify:** Effective Config → `ai_enabled: false`
3. **Test:** Run analysis cycle
4. **Expected:** Decision log shows GPT not consulted, or immediate HOLD

#### T6: Max Spread Rejection
1. **Change:** Settings → Risk → Max Spread = 0.5 pips
2. **Verify:** Effective Config → `max_spread_pips: 0.5`
3. **Test:** Pick symbol with known high spread (e.g., exotic pair)
4. **Expected:** BLOCK due to spread > 0.5 pips

---

### Step 3: Evidence Collection

For **each test**, document:

1. **Screenshot:** Effective Config showing new value
2. **Log Entry:** `[SETTINGS] old_value → new_value`
3. **Decision Log:** Entry from `data/decision_logs.jsonl` showing:
   - `final_decision: "BLOCK"` or `"ENTER"`
   - `block_reason` matching your changed setting
4. **UI Status:** Any visible changes in GUI panels

**Example Decision Log Entry:**
```json
{
  "signal_id": "abc123",
  "timestamp": "2026-02-22T15:30:45",
  "symbol": "EURUSD",
  "raw_signal": "BUY",
  "gpt_confidence": 85,
  "gpt_reasoning": "Strong bullish momentum",
  "filters": {
    "min_confidence": {
      "passed": false,
      "reason": "Confidence 85% < required 99%"
    }
  },
  "setup_score": 85,
  "final_decision": "BLOCK",
  "block_reason": "Failed min_confidence filter"
}
```

---

### Step 4: Long-Duration DRY_RUN Test

**Purpose:** Run bot for extended period (30-50 cycles) to verify stability

1. **Enable DRY_RUN:** Settings → Trading → DRY RUN Mode = ON
2. **Configure:** Set realistic settings (not extreme values)
3. **Start Bot:** Let it run for 2-4 hours
4. **Monitor:**
   - Check `data/decision_logs.jsonl` grows with entries
   - No ERROR status in GUI
   - All SIMULATED orders logged correctly
   - No real MT5 positions opened

5. **Review Logs:**
   ```bash
   # Count simulated orders
   grep "WOULD_SEND_ORDER" logs/app.log | wc -l
   
   # Check decision distribution
   jq -r '.final_decision' data/decision_logs.jsonl | sort | uniq -c
   ```

**Success Criteria:**
- ✅ No crashes or ERROR states
- ✅ Decision logs show variety: ENTER, HOLD, BLOCK with reasons
- ✅ BLOCK reasons match active filters
- ✅ No real orders on MT5 account

---

## 🔧 Integration Tests

### GPT Model Change (Without Restart)
1. Settings → GPT API tab
2. Change model: `gpt-4o` → `gpt-4-turbo`
3. Click **TEST** button → should show API response
4. Click **Save**
5. Check logs: `[SETTINGS] GPT model updated: gpt-4o → gpt-4-turbo`
6. Next GPT call should use new model (check logs for model name)

### MT5 Reconnect (Without Restart)
1. Settings → MT5 Settings
2. Modify any setting (e.g., magic number)
3. Click **TEST CONNECTION** → verify success
4. Click **SAVE**
5. Check logs: `[MT5] Reconnecting with new settings...`
6. Status bar should show updated connection

### Telegram Toggle
1. Settings → Telegram tab
2. Toggle enabled ON/OFF
3. Save
4. Check logs for `[Telegram] Notifications enabled/disabled`
5. Test with simulation: should send/not send based on setting

---

## 📊 Automated Test Suite

For comprehensive systematic testing:

```bash
# Run all tests (skips integration if no external services)
python -m src.qa.qa_test_suite --skip-integration

# Full test including GPT/Telegram/MT5
python -m src.qa.qa_test_suite

# Custom output directory
python -m src.qa.qa_test_suite --output reports/
```

**Output Files:**
- `data/qa_reports/qa_report_YYYYMMDD_HHMMSS.json` - Machine-readable
- `data/qa_reports/qa_report_YYYYMMDD_HHMMSS.md` - Human-readable

**Test Categories:**
1. Configuration verification (5 tests)
2. Filter behavior (3 tests)
3. Gate enforcement (2 tests)
4. Integration tests (3 tests)
5. DRY_RUN validation (1 test)

**Pass Rate Target:** ≥ 90% (allow some integration failures if services unavailable)

---

## ✅ Acceptance Criteria

Consider system **READY FOR LIVE TRADING** only if:

- ✅ **Config Verification:** All changes reflected in Effective Config
- ✅ **Runtime Application:** Decision logs prove settings affect logic
- ✅ **No Invisible Bypasses:** Single-gate enforcement proven (no active_signal = no order)
- ✅ **DRY_RUN Stability:** 30-50 cycles completed without crashes
- ✅ **Integration Tests:** GPT/MT5 changes apply without restart
- ✅ **Evidence Complete:** Each critical setting has logged proof of effect

---

## 🐛 Troubleshooting

### Problem: Settings Save but Don't Apply

**Symptoms:**
- GUI saves successfully
- Effective Config shows old value
- Decision logs don't reflect change

**Solution:**
1. Check logs for: `[ConfigManager] Reloading all configs...`
2. If missing, verify `dialogs_v2._save_to_yaml()` calls `config_manager.reload_all()`
3. Check for exceptions in logs during save
4. Restart bot as fallback (but this indicates bug in hot-reload)

### Problem: Decision Logs Empty

**Symptoms:**
- `data/decision_logs.jsonl` doesn't exist or empty
- "Explain Last Decision" shows "No decision log found"

**Solution:**
1. Verify `state_core.log_decision()` is being called
2. Check `data/` directory permissions (must be writable)
3. Run bot in DRY_RUN mode for at least 1 cycle
4. Check logs for errors during decision logging

### Problem: DRY_RUN Still Sends Orders

**Symptoms:**
- Real positions appear on MT5 during DRY_RUN
- No "WOULD_SEND_ORDER" logs

**Solution:**
1. Verify `trading.yaml` has `dry_run: true`
2. Check Effective Config: `trading.dry_run` should be `true`
3. Restart bot (config may have loaded before change)
4. Check `live_trader.execute_trade()` has DRY_RUN check before `executor.execute_signal()`

---

## 📈 Best Practices

1. **Always Test in DRY_RUN First**
   - New configurations → DRY_RUN for 1-2 hours minimum
   - Observe decision patterns before live

2. **Document Evidence**
   - Screenshot Effective Config after each change
   - Save decision log excerpts showing filter effects
   - Keep QA report for audit trail

3. **Incremental Testing**
   - Change ONE setting at a time
   - Verify effect before changing next
   - Don't combine multiple changes in single test

4. **Use Real Market Conditions**
   - Run QA tests during actual trading hours
   - Don't test on weekends if weekend block enabled
   - Use symbols you plan to trade live

5. **Verify Negative Cases**
   - Ensure BLOCK reasons are specific (not generic)
   - Confirm filters reject when they should
   - Test gate enforcement (disconnect MT5 deliberately)

---

## 📁 Files Generated

```
data/
├── decision_logs.jsonl          # All trading decisions (append-only)
├── qa_reports/
│   ├── qa_report_20260222_153045.json
│   ├── qa_report_20260222_153045.md
│   └── ...
└── logs/
    └── app.log                  # Main application log
```

**Retention:**
- `decision_logs.jsonl`: Keep indefinitely (audit trail)
- `qa_reports/`: Keep last 30 days
- `logs/`: Rotate daily, keep 7 days

---

## 🎓 Training Checklist

Before live trading, operator should be able to:

- [ ] Enable/disable DRY_RUN mode
- [ ] Open and interpret Effective Config dialog
- [ ] Use Explain Last Decision to diagnose behavior
- [ ] Change a setting and verify it applies (any setting)
- [ ] Run automated QA suite and interpret results
- [ ] Identify BLOCK reasons in decision logs
- [ ] Verify gate enforcement (no active_signal = no order)
- [ ] Confirm MT5/GPT changes apply without restart

---

## 📞 Support

If QA tests fail or behavior unexpected:

1. **Check Logs:** `logs/app.log` for errors
2. **Effective Config:** Verify runtime values match expectations
3. **Decision Log:** Last entry should explain behavior
4. **QA Report:** Review automated test results for systematic issues
5. **Github Issues:** Report with evidence (logs, screenshots, decision entries)

---

**Version:** 1.0  
**Last Updated:** 2026-02-22  
**Maintainer:** Development Team

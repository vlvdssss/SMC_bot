# 📋 SETTINGS INVENTORY (Full Bot Configuration)

**Generated:** 2026-02-22  
**Last Updated:** 2026-02-22 23:38 (Conflicts eliminated)  
**Purpose:** Complete inventory of all bot settings - config files, hardcodes, defaults  
**Status:** 🟢 TradeFilters fixed! Hot reload works! Conflicts = 0!

---

## ✅ RECENT CHANGES (Feb 22, 2026 23:38)

### 🔥 CRITICAL FIX: Config Conflicts Eliminated

**Problem:** Trade filter parameters existed in TWO places:
- `ai.yaml` → `market_analyst.trade_filters` (11 parameters)
- `trading.yaml` → `risk.max_spread_pips`, `signal_quality.min_confidence`

**Result:** Conflicts! GUI changes to one file ignored by runtime reading from other file.

**Solution Implemented:**
1. ✅ Moved ALL 11 filter parameters to `trading.yaml` → `trading.filters`
2. ✅ Removed `market_analyst.trade_filters` section from `ai.yaml`
3. ✅ Updated `TradeFilters._load_config()` to read from `trading.yaml` ONLY
4. ✅ Removed duplicate `risk.max_spread_pips` and `signal_quality.min_confidence`
5. ✅ Updated tests - all pass 100%
6. ✅ Updated conflict detection UI

**Verification:**
```bash
python test_conflict_detection.py
# ✅ TEST PASSED: Zero conflicts!
#    • trade_filters removed from ai.yaml
#    • All 12 filter parameters in trading.yaml
#    • No duplicate definitions detected

python test_trade_filters_reload.py
# ✅ TEST PASSED: TradeFilters hot reload works!
#    Source: trading.yaml (single source of truth)
```

**Architecture:**
- **ai.yaml** = GPT/AI parameters ONLY (model, temperature, tokens, timeouts)
- **trading.yaml** = ALL trading logic (filters, risk, execution, indicators)
- **Single source of truth** for each parameter - NO duplicates!

---

## 📊 SUMMARY

| Category | Total Params | In Config | Hardcoded | In GUI | Runtime Apply |
|----------|--------------|-----------|-----------|--------|---------------|
| Trading | 15 | 8 | 7 | 12 | ✅ Partial |
| Risk Management | 12 | 6 | 6 | 10 | ✅ Partial |
| AI/GPT | 18 | 12 | 6 | 8 | ❌ Needs reinit |
| **Filters** | **11** | **11** ✅ | **0** ✅ | **2** ❌ | ✅ **YES!** ✅ |
| MT5 Connection | 6 | 5 | 1 | 5 | ❌ Needs reconnect |
| Telegram | 8 | 8 | 0 | 5 | ✅ Yes |
| Monitoring | 5 | 3 | 2 | 3 | ✅ Partial |
| Indicators | 7 | 7 | 0 | 4 | ❌ Needs reload |
| **TOTALS** | **82** | **63** ✅ | **19** ⬇️ | **49** | **~55% Live** ⬆️ |

**Progress:**
- ✅ **11 hardcodes eliminated** (TradeFilters refactored)
- ✅ **0 config conflicts** (single source of truth)
- ✅ **Hot reload working** for all filter parameters
- ⏳ **33 params NOT in GUI** (next priority)
- ⏳ **19 hardcodes remain** (magic_number, telegram_timeout, MT5 cooldown, etc.)

---

## 🚨 CRITICAL FINDINGS

### 1. **Remaining Hardcoded Values (Need to Move to Config/GUI)**

| Parameter | File | Line | Current Value | Impact |
|-----------|------|------|---------------|--------|
| `magic_number` | live_trader.py | 150 | 123456 | 🔴 HIGH - Order identification |
| `connect_cooldown` | mt5_manager.py | 45 | 5 sec | 🟡 MED - MT5 reconnect delay |
| `telegram_timeout` | telegram_notifier.py | 20 | 30 sec | 🟡 MED - Message delivery |
| `telegram_retries` | telegram_notifier.py | 20 | 3 | 🟡 MED - Retry logic |
| `atr_fallback` | market_analyst.py | 744 | 5.0 (XAUUSD) / 0.003 (FX) | 🟡 MED - Default volatility |
| `gpt_confidence_default` | market_analyst.py | 618 | 100% | 🔴 **CRITICAL** - GPT didn't return confidence |
| `screenshot_bars` | ai.yaml → code | 200 | 🟡 MED - Chart context |
| `screenshot_dpi` | ai.yaml → code | 150 | 🟢 LOW - Image quality |

**Total Remaining:** 19 hardcodes (down from 30)

### 2. **Config Values NOT in GUI**

These exist in YAML but can't be changed through Settings dialog:

| Parameter | File | Current Value | Why Not in GUI? |
|-----------|------|---------------|-----------------|
| **Filters (CRITICAL)** | | | **❌ BLOCKING - Must add to GUI!** |
| `trading.filters.min_confidence` | trading.yaml | 75 | 🔴 **CRITICAL - Should be in GUI!** |
| `trading.filters.max_spread_pips` | trading.yaml | 3.0 | 🔴 **CRITICAL - Should be in GUI!** |
| `trading.filters.daily_limit` | trading.yaml | 6 | 🔴 **CRITICAL - Should be in GUI!** |
| `trading.filters.cooldown_after_win` | trading.yaml | 15 | 🔴 **Should be in GUI!** |
| `trading.filters.cooldown_after_loss` | trading.yaml | 90 | 🔴 **Should be in GUI!** |
| `trading.filters.cooldown_after_2_losses` | trading.yaml | 240 | 🔴 **CRITICAL - Should be in GUI!** |
| `trading.filters.min_rr` | trading.yaml | 1.2 | 🔴 **Should be in GUI!** |
| `trading.filters.min_setup_score` | trading.yaml | 70 | 🔴 **Should be in GUI!** |
| `trading.filters.htf_timeframe` | trading.yaml | M15 | 🔴 **Should be in GUI!** |
| `trading.filters.htf_ema_fast` | trading.yaml | 50 | 🔴 **Should be in GUI!** |
| `trading.filters.htf_ema_slow` | trading.yaml | 200 | 🔴 **Should be in GUI!** |
| | | | |
| **Other (Important)** | | | |
| `trading.check_interval_seconds` | trading.yaml | 1 | 🟡 Advanced - polling frequency |
| `trading.hours.start/end` | trading.yaml | 01:10 - 23:30 | ❌ **Should be in GUI!** |
| `trading.indicators.atr_period` | trading.yaml | 14 | ❌ **Should be in GUI!** |
| `trading.indicators.ema_periods` | trading.yaml | [20, 50, 200] | ❌ **Should be in GUI!** |
| `trading.indicators.rsi_period` | trading.yaml | 14 | ❌ **Should be in GUI!** |
| `trading.indicators.timeframes` | trading.yaml | [M15,M30,H1,H4] | ❌ **Should be in GUI!** |
| `trading.signal_ttl.*` | trading.yaml | Multiple | ❌ **Should be in GUI!** |
| `trading.smc.*` | trading.yaml | Multiple | 🟡 Can stay in config (advanced) |
| `trading.v5_improvements.*` | trading.yaml | Multiple | ❌ **Partially in GUI, incomplete** |
| `ai.market_analyst.schedule.*` | ai.yaml | Multiple | ❌ **Should be in GUI!** |
| `ai.market_analyst.safety.*` | ai.yaml | Multiple | 🔴 **CRITICAL - Should be in GUI!** |
| `ai.manual_overrides.*` | ai.yaml | Multiple | ❌ **Should be in GUI!** |
| `portfolio.instruments` | portfolio.yaml | [XAUUSD, EURUSD] | ❌ **Should be in GUI!** |
| `mt5.connection.path` | mt5.yaml | Terminal path | ❌ **Should be in GUI!** |

### 3. **~~Duplicate Parameters~~** ✅ **ELIMINATED!**

**Before (Feb 22, 2026 - Pre-Refactoring):**

| Parameter | Location 1 | Location 2 | Winner | Status |
|-----------|------------|------------|--------|--------|
| `min_confidence` | ai.yaml (75%) | trading.yaml (50%) | ⚠️ ai.yaml | ❌ CONFLICT |
| `max_spread_pips` | ai.yaml (3.0) | trading.yaml (0.5) | ⚠️ ai.yaml | ❌ CONFLICT |
| `daily_limit` | ai.yaml (6) | N/A | ai.yaml | ⚠️ Only in ai.yaml |

**After (Feb 22, 2026 23:38 - Post-Refactoring):**

✅ **ZERO CONFLICTS!** All parameters now have single source of truth:

| Parameter | Source | Value | Notes |
|-----------|--------|-------|-------|
| `min_confidence` | trading.yaml | 75% | ✅ Only in trading.filters |
| `max_spread_pips` | trading.yaml | 3.0 | ✅ Only in trading.filters |
| `daily_limit` | trading.yaml | 6 | ✅ Only in trading.filters |
| `cooldown_*` | trading.yaml | Multiple | ✅ Only in trading.filters |
| `htf_*` | trading.yaml | Multiple | ✅ Only in trading.filters |
| `min_rr` | trading.yaml | 1.2 | ✅ Only in trading.filters |
| `min_setup_score` | trading.yaml | 70 | ✅ Only in trading.filters |

**Architecture Confirmed:**
- **ai.yaml** = GPT/AI parameters ONLY
- **trading.yaml** = ALL trading logic parameters
- **NO duplicates** = NO conflicts = **Predictable behavior!**

---

## 📦 DETAILED INVENTORY

### 1️⃣ TRADING PARAMETERS

#### 1.1 Core Trading

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.enabled` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.dry_run` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.mode` | auto | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.check_interval_seconds` | 1 | trading.yaml | ❌ No | Scheduler | ❌ No | 🟡 Optional |
| `trading.hours.start` | 01:10 | trading.yaml | ❌ No | Scheduler | ❌ No | ✅ **YES!** |
| `trading.hours.end` | 23:30 | trading.yaml | ❌ No | Scheduler | ❌ No | ✅ **YES!** |

#### 1.2 Position Sizing

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.risk.fixed_lot_size` | 0.01 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.risk.default_sl_pips` | 40 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.risk.default_tp_pips` | 100 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.risk.max_spread_pips` | 0.5 | trading.yaml | ⚠️ **IGNORED** | TradeFilters | ❌ No | ✅ **YES!** |
| `risk_percent` | 1.0 | dialogs_v2 default | N/A (not used) | N/A | ✅ Yes | 🟡 If implemented |

#### 1.3 Signal Quality

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.signal_quality.min_confidence` | 50 | trading.yaml | ⚠️ **IGNORED** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `trading.signal_quality.invert_signals` | true | trading.yaml | ✅ Yes | None | ❌ No | ✅ **CRITICAL!** |
| `ai.market_analyst.trade_filters.min_confidence` | 75 | ai.yaml | ⚠️ **IGNORED** | TradeFilters | ❌ No | 🔴 **Conflict!** |
| `TradeFilters.config.min_confidence` | 75 | trade_filters.py:49 | ❌ HARDCODE | ✅ **This one wins!** | ❌ No | 🔴 **Move to config!** |

#### 1.4 Trailing Stop

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.trailing_stop.enabled` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.trailing_stop.activation_profit_percent` | 30 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.trailing_stop.trailing_step_percent` | 10 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |

#### 1.5 Stop Loss Protection

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.stop_loss_protection.enabled` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.stop_loss_protection.consecutive_stops` | 2 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.stop_loss_protection.cooldown_minutes` | 999 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |

#### 1.6 Profit Protection

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.profit_protection.enabled` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.profit_protection.consecutive_wins` | 3 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.profit_protection.cooldown_minutes` | 999 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |

#### 1.7 Signal TTL

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.signal_ttl.enabled` | true | trading.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `trading.signal_ttl.ttl_minutes` | 30 | trading.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `trading.signal_ttl.auto_requery_on_expire` | true | trading.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `trading.signal_ttl.requery_cooldown_minutes` | 15 | trading.yaml | ✅ Yes | None | ❌ No | ✅ Yes |

#### 1.8 Adaptive Lot

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.v5_improvements.adaptive_lot.enabled` | true | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.v5_improvements.adaptive_lot.base_lot` | 0.01 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.v5_improvements.adaptive_lot.max_lot` | 0.05 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `trading.v5_improvements.adaptive_lot.lookback_trades` | 10 | trading.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |

---

### 2️⃣ FILTERS & GATES (CRITICAL - Most Hardcoded!)

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `htf_timeframe` | M15 | trade_filters.py:40 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `htf_ema_fast` | 50 | trade_filters.py:41 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `htf_ema_slow` | 200 | trade_filters.py:42 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `min_rr` | 1.2 | trade_filters.py:42 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `max_spread_pips` | 3.0 | trade_filters.py:43 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `cooldown_after_win` | 15 min | trade_filters.py:44 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `cooldown_after_loss` | 90 min | trade_filters.py:45 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `cooldown_after_2_losses` | 240 min | trade_filters.py:46 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `daily_limit` | 6 | trade_filters.py:47 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `min_setup_score` | 70 | trade_filters.py:48 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |
| `min_confidence` | 75 | trade_filters.py:49 | ❌ **HARDCODE** | TradeFilters | ❌ No | ✅ **CRITICAL!** |

**🔥 ROOT CAUSE:** TradeFilters.__init__() creates self.config dict with hardcoded values and never checks trading.yaml or ai.yaml!

---

### 3️⃣ AI / GPT PARAMETERS

#### 3.1 GPT Client

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `ai.market_analyst.gpt.api_key` | null | ai.yaml | ❌ No | GPT client | ✅ Yes | ✅ Yes |
| `ai.market_analyst.gpt.model` | gpt-4o | ai.yaml | ❌ No | GPT client | ✅ Yes | ✅ Yes |
| `ai.market_analyst.gpt.temperature` | 0.3 | ai.yaml | ❌ No | GPT client | ✅ Yes | ✅ Yes |
| `ai.market_analyst.gpt.max_tokens` | 4000 | ai.yaml | ❌ No | GPT client | ✅ Yes | ✅ Yes |
| `ai_timeout` | 30 | dialogs_v2 default | ❌ No | GPT client | ✅ Yes | ✅ Yes |

#### 3.2 Analysis Schedule

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `ai.market_analyst.schedule.enabled` | true | ai.yaml | ✅ Yes | Scheduler | ❌ No | ✅ Yes |
| `ai.market_analyst.schedule.interval_minutes` | 60 | ai.yaml | ❌ No | Scheduler | ❌ No | ✅ Yes |
| `ai.market_analyst.schedule.mode` | interval | ai.yaml | ❌ No | Scheduler | ❌ No | 🟡 Advanced |
| `ai.market_analyst.schedule.restrictions.*` | Multiple | ai.yaml | ✅ Yes | None | ❌ No | ✅ Yes |

#### 3.3 Safety Limits

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `ai.market_analyst.safety.max_daily_calls` | 50 | ai.yaml | ✅ Yes | None | ❌ No | ✅ **YES!** |
| `ai.market_analyst.safety.max_monthly_cost` | $50 | ai.yaml | ✅ Yes | None | ❌ No | ✅ **YES!** |
| `ai.market_analyst.safety.min_minutes_between_calls` | 15 | ai.yaml | ✅ Yes | None | ❌ No | ✅ **YES!** |

#### 3.4 Signal Management

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `ai.market_analyst.signal_validity_minutes` | 30 | ai.yaml | ✅ Yes | None | ❌ No | 🟡 Optional |
| `ai.market_analyst.signals.auto_cleanup` | true | ai.yaml | ✅ Yes | None | ❌ No | 🟡 Optional |
| `ai.market_analyst.signals.confidence_decay` | true | ai.yaml | ✅ Yes | None | ❌ No | 🟡 Advanced |
| `ai.market_analyst.signals.default_ttl_hours` | 24 | ai.yaml | ✅ Yes | None | ❌ No | 🟡 Optional |

#### 3.5 Manual Overrides

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `ai.manual_overrides.enabled` | false | ai.yaml | ✅ Yes | None | ❌ No | ✅ **YES!** |
| `ai.manual_overrides.eurusd.sl_pips` | 30 | ai.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `ai.manual_overrides.eurusd.tp_pips` | 50 | ai.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `ai.manual_overrides.xauusd.sl_dollars` | 4.5 | ai.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `ai.manual_overrides.xauusd.tp_dollars` | 12.0 | ai.yaml | ✅ Yes | None | ❌ No | ✅ Yes |

---

### 4️⃣ MT5 CONNECTION

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `mt5.connection.login` | 5046623512 | mt5.yaml | ❌ No | MT5 reconnect | ✅ Yes | ✅ Yes |
| `mt5.connection.password` | ****** | mt5.yaml | ❌ No | MT5 reconnect | ✅ Yes | ✅ Yes |
| `mt5.connection.server` | MetaQuotes-Demo | mt5.yaml | ❌ No | MT5 reconnect | ✅ Yes | ✅ Yes |
| `mt5.connection.path` | C:\\Program Files\\... | mt5.yaml | ❌ No | MT5 reconnect | ❌ No | ✅ **YES!** |
| `mt5.connection.timeout` | 60000 | mt5.yaml | ❌ No | MT5 reconnect | ❌ No | 🟡 Advanced |
| `mt5.settings.magic_number` | 123456 | startup.py:62 | ❌ **HARDCODE** | Executor | ❌ No | ✅ **YES!** |
| `mt5_manager.connect_cooldown` | 5 sec | mt5_manager.py:45 | ❌ **HARDCODE** | MT5Manager | ❌ No | 🟡 Optional |

---

### 5️⃣ TELEGRAM

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `telegram.enabled` | false | telegram.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `telegram.bot_token` | '' | telegram.yaml | ❌ No | Telegram reinit | ✅ Yes | ✅ Yes |
| `telegram.chat_id` | '' | telegram.yaml | ❌ No | Telegram reinit | ✅ Yes | ✅ Yes |
| `telegram.enable_bot` | true | telegram.yaml | ✅ Yes | Telegram bot | ✅ Yes | ✅ Yes |
| `telegram.notify.startup` | true | telegram.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `telegram.notify.trade_opened` | true | telegram.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `telegram.notify.trade_closed` | true | telegram.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `telegram.alert_min_level` | WARNING | telegram.yaml | ✅ Yes | None | ❌ No | 🟡 Optional |
| `telegram_timeout` | 30 sec | telegram_notifier.py:20 | ❌ **HARDCODE** | Notifier | ❌ No | 🟡 Optional |
| `telegram_retry_attempts` | 3 | telegram_notifier.py:20 | ❌ **HARDCODE** | Notifier | ❌ No | 🟡 Optional |

---

### 6️⃣ INDICATORS & TECHNICAL ANALYSIS

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `trading.indicators.atr_period` | 14 | trading.yaml | ❌ No | Indicator reload | ❌ No | ✅ Yes |
| `trading.indicators.ema_periods` | [20, 50, 200] | trading.yaml | ❌ No | Indicator reload | ❌ No | ✅ Yes |
| `trading.indicators.rsi_period` | 14 | trading.yaml | ❌ No | Indicator reload | ❌ No | ✅ Yes |
| `trading.indicators.timeframes` | [M15,M30,H1,H4] | trading.yaml | ❌ No | Strategy reload | ✅ Yes | ✅ Yes |
| `trading.smc.enabled` | true | trading.yaml | ❌ No | Strategy reload | ❌ No | 🟡 Advanced |
| `trading.smc.order_blocks` | true | trading.yaml | ❌ No | Strategy reload | ❌ No | 🟡 Advanced |
| `trading.smc.fair_value_gaps` | true | trading.yaml | ❌ No | Strategy reload | ❌ No | 🟡 Advanced |

---

### 7️⃣ PORTFOLIO & INSTRUMENTS

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `portfolio.instruments` | [XAUUSD, EURUSD] | portfolio.yaml | ❌ No | Full restart | ❌ No | ✅ **YES!** |
| `portfolio.allocation.XAUUSD` | 30% | portfolio.yaml | ❌ No | Risk calc | ❌ No | 🟡 If multi-symbol |
| `portfolio.allocation.EURUSD` | 70% | portfolio.yaml | ❌ No | Risk calc | ❌ No | 🟡 If multi-symbol |
| `portfolio.risk_model.max_total_exposure` | 1.25 | portfolio.yaml | ✅ Yes | None | ❌ No | 🟡 If multi-symbol |

---

### 8️⃣ MONITORING & LOGGING

| Key | Current Value | Source | Runtime Apply | Needs Reinit | In GUI | Should Be in GUI |
|-----|---------------|--------|---------------|--------------|--------|------------------|
| `monitoring.log_level` | INFO | portfolio.yaml | ✅ Yes | Logger | ✅ Yes | ✅ Yes |
| `monitoring.save_trades` | true | portfolio.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `monitoring.save_equity_curve` | true | portfolio.yaml | ✅ Yes | None | ✅ Yes | ✅ Yes |
| `monitoring.alert_on_dd_threshold` | 15% | portfolio.yaml | ✅ Yes | None | ❌ No | ✅ Yes |
| `monitoring.alert_on_consecutive_losses` | 5 | portfolio.yaml | ✅ Yes: None | ❌ No | ✅ Yes |

---

## 🔧 REQUIRED ACTIONS

### Priority 1: FIX HARDCODES (Breaking Change)

**TradeFilters class must read from config!**

```python
# BEFORE (trade_filters.py lines 38-49)
self.config = {
    'htf_timeframe': mt5.TIMEFRAME_M15 if mt5 else None,
    'htf_ema_fast': 50,  # ❌ HARDCODE
    'htf_ema_slow': 200,  # ❌ HARDCODE
    'min_rr': 1.2,  # ❌ HARDCODE
    'max_spread_pips': 3.0,  # ❌ HARDCODE
    'cooldown_after_win': 15,  # ❌ HARDCODE
    'cooldown_after_loss': 90,  # ❌ HARDCODE
    'cooldown_after_2_losses': 240,  # ❌ HARDCODE
    'daily_limit': 6,  # ❌ HARDCODE
    'min_setup_score': 70,  # ❌ HARDCODE
    'min_confidence': 75  # ❌ HARDCODE
}

# AFTER (should be)
config_mgr = get_config_manager()
ai_config = config_mgr.load_config('ai.yaml')
filter_config = ai_config.get('market_analyst', {}).get('trade_filters', {})

self.config = {
    'htf_timeframe': filter_config.get('htf_timeframe', 'M15'),
    'htf_ema_fast': filter_config.get('htf_ema_fast', 50),
    'htf_ema_slow': filter_config.get('htf_ema_slow', 200),
    'min_rr': filter_config.get('min_rr', 1.2),
    'max_spread_pips': filter_config.get('max_spread_pips', 3.0),
    'cooldown_after_win': filter_config.get('cooldown_after_win', 15),
    'cooldown_after_loss': filter_config.get('cooldown_after_loss', 90),
    'cooldown_after_2_losses': filter_config.get('cooldown_after_2_losses', 240),
    'daily_limit': filter_config.get('daily_limit', 6),
    'min_setup_score': filter_config.get('min_setup_score', 70),
    'min_confidence': filter_config.get('min_confidence', 75)
}

# Register config reload callback
config_mgr.register_reload_callback('ai.yaml', self._reload_from_config)
```

### Priority 2: EXPAND GUI Settings

Add missing tabs/sections:

#### New Tab: "Filters & Gates"
- Min Confidence (75%)
- Min Setup Score (70)
- Min Risk/Reward (1.2)
- Max Spread (pips)
- Daily Limit (6)
- Cooldown after Win (15 min)
- Cooldown after Loss (90 min)
- Cooldown after 2 Losses (240 min)
- HTF Timeframe (M15)
- HTF EMA Fast (50)
- HTF EMA Slow (200)

#### Expand "Trading" Tab:
- Trading Hours (start/end)
- Invert Signals (true/false)
- Signal TTL & Auto-requery

#### Expand "AI" Tab:
- Analysis Interval (60 min)
- Max Daily GPT Calls (50)
- Max Monthly Cost ($50)
- Min Minutes Between Calls (15)
- Manual Overrides (enable + per-symbol SL/TP)

#### New Tab: "Indicators"
- ATR Period (14)
- EMA Periods ([20, 50, 200])
- RSI Period (14)
- Active Timeframes ([M15, M30, H1, H4])

#### Expand "MT5" Tab:
- Terminal Path
- Magic Number (123456)

#### New Tab: "Portfolio" (if multi-symbol)
- Active Instruments
- Allocation %
- Max Total Exposure

### Priority 3: "Dump Settings with Sources" Button

```python
def _dump_settings_with_sources(self):
    """Export ALL settings showing their sources"""
    config_mgr = get_config_manager()
    
    dump = {
        "timestamp": datetime.now().isoformat(),
        "settings": {}
    }
    
    # 1. From config files
    for config_name in ['trading.yaml', 'ai.yaml', 'mt5.yaml', 'telegram.yaml', 'portfolio.yaml']:
        cfg = config_mgr.load_config(config_name)
        dump["settings"][config_name] = {
            "source": "config_file",
            "values": cfg
        }
    
    # 2. From TradeFilters hardcodes
    dump["settings"]["TradeFilters_hardcodes"] = {
        "source": "HARDCODE - trade_filters.py:38",
        "values": {
            "htf_timeframe": "M15",
            "htf_ema_fast": 50,
            "htf_ema_slow": 200,
            "min_rr": 1.2,
            "max_spread_pips": 3.0,
            "cooldown_after_win": 15,
            "cooldown_after_loss": 90,
            "cooldown_after_2_losses": 240,
            "daily_limit": 6,
            "min_setup_score": 70,
            "min_confidence": 75
        },
        "WARNING": "These values OVERRIDE config files!"
    }
    
    # 3. From GUI CONFIG_SCHEMA defaults
    dump["settings"]["GUI_defaults"] = {
        "source": "dialogs_v2.py:28 CONFIG_SCHEMA",
        "values": {k: v["default"] for k, v in CONFIG_SCHEMA.items()}
    }
    
    # 4. Runtime effective values
    dump["settings"]["runtime_effective"] = {
        "source": "config_manager.get_all_configs()",
        "values": config_mgr.get_all_configs()
    }
    
    # Save
    path = f"data/settings_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    with open(path, 'w') as f:
        yaml.dump(dump, f, default_flow_style=False)
    
    messagebox.showinfo("Dump Complete", f"Settings exported to:\n{path}")
```

### Priority 4: Effective Config V2

Upgrade "Show Effective Config" to detect conflicts:

```python
def _show_effective_config_v2(self):
    """Enhanced version showing sources AND conflicts"""
    config_mgr = get_config_manager()
    
    conflicts = []
    
    # Detect: Config says X, but hardcode uses Y
    ai_config = config_mgr.load_config('ai.yaml')
    filter_config = ai_config.get('market_analyst', {}).get('trade_filters', {})
    
    if filter_config.get('min_confidence') != 75:
        conflicts.append(f"min_confidence: config={filter_config.get('min_confidence')} vs hardcode=75")
    
    if filter_config.get('daily_limit') != 6:
        conflicts.append(f"daily_limit: config={filter_config.get('daily_limit')} vs hardcode=6")
    
    # Show dialog with conflicts highlighted
    EffectiveConfigDialog(self.root, conflicts=conflicts)
```

---

## ✅ ACCEPTANCE CRITERIA

1. ✅ **All 82 parameters documented** with sources
2. ✅ **30 hardcodes identified** and marked for migration
3. ⏳ **TradeFilters reads from config** instead of hardcodes
4. ⏳ **GUI exposes 70+ parameters** (currently only 49)
5. ⏳ **"Dump Settings" button** works
6. ⏳ **"Effective Config" v2** shows conflicts
7. ⏳ **ConfigManager registered in TradeFilters** for hot reload
8. ⏳ **No more hidden/invisible values** - everything in Effective Config

---

## 📚 REFERENCES

- Config files: `config/*.yaml`
- GUI schema: `src/gui/dialogs_v2.py:28`
- Filter hardcodes: `src/core/trade_filters.py:38-49`
- MT5 hardcodes: `src/core/startup.py:62`, `src/live/live_trader.py:150`
- Telegram hardcodes: `src/monitoring/telegram_notifier.py:20`
- AI defaults: `src/ai/market_analyst.py:471-473`, `line:618`, `line:744`

---

**Next Steps:**  
1. **Review this inventory** - mark which settings you want in GUI
2. **Fix TradeFilters** - make it config-driven
3. **Expand Settings dialog** - add missing tabs
4. **Add "Dump Settings"** button
5. **Test end-to-end**: GUI change → Effective Config → decision_logs


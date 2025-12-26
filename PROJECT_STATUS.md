# SMC-framework - Project Status

**Last Updated**: 20 декабря 2025

---

## ✅ Production Status

### Baseline Strategies (FROZEN)

| Instrument | Version | Risk | WR | DD | ROI | Status |
|------------|---------|------|----|----|-----|--------|
| **XAUUSD** | v1.0 | 0.75% | 60.8% | 11.5% | +952% (3y) | ✅ FROZEN |
| **EURUSD** | v1.0 | 0.5% | 70.7% | 5.4% | +324% (3y) | ✅ FROZEN |

**Portfolio Exposure**: 1.25%  
**Backtest Period**: 2023-2025 (3 years)

### BAZA System

✅ **Backtest Mode** - Working  
✅ **Demo Mode** - Ready (MT5 connected)  
✅ **Portfolio Manager** - Multi-instrument support  
✅ **MT5 Integration** - Full connector implemented

---

## 📂 Project Structure

```
SMC-framework/
├── BAZA/                   # Production system
├── strategies/             # XAUUSD + EURUSD (frozen)
├── run_backtest.py         # Single instrument runner
├── run_portfolio_backtest.py # Portfolio runner
├── data/backtest/          # Historical data (MT5)
├── results/                # Backtest results by year
└── experiments/            # Archived experiments
    ├── gbpusd_rejected/    # GBPUSD (0 trades - excluded)
    └── market_screening/   # Multi-instrument screening (incomplete)
```

---

## 🎯 Current Focus

**Status**: Production Ready

**Next Steps**:
1. ✅ Baseline validated (3 years)
2. ✅ BAZA system complete
3. ✅ Demo mode ready
4. ⏳ Live trading on demo account

---

## 🚫 Excluded / Archived

### GBPUSD - PERMANENTLY EXCLUDED
- **Попытка #1**: Mean Reversion → 0 trades
- **Попытка #2**: SMC Retracement → 0 trades (even with simplifications)
- **Verdict**: Instrument doesn't fit SMC approach
- **Location**: `experiments/gbpusd_rejected/`

### Market Screening - INCOMPLETE
- **Instruments**: USDCHF, EURGBP, NZDUSD, USDJPY, AUDCAD, XAGUSD
- **Status**: Partial results (slow backtest, weak signals)
- **Location**: `experiments/market_screening/`

---

## 📊 Key Metrics

**Baseline Performance** (2023-2025 avg):
- XAUUSD: 148 trades/year, +317% ROI/year
- EURUSD: 176 trades/year, +108% ROI/year

**Portfolio**:
- Diversification: Trend Following + Pullback strategies
- Total exposure: 1.25%
- Stable growth, low correlation

---

## 📝 Documentation

- `README.md` - Main project overview
- `docs/` - Full framework documentation
- `docs/decisions/` - Important decisions & verdicts
- `docs/archive/` - Historical documents
- `BAZA/BAZA_STATUS.md` - BAZA system status
- `BAZA/DEMO_STATUS.md` - Demo mode documentation

---

**Project State**: ✅ STABLE  
**Baseline**: FROZEN  
**Production**: READY

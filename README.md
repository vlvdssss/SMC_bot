# BAZA Trading Bot

Автоматическая торговая система на основе Smart Money Concepts (SMC).

## Результаты бэктеста (2024)

| Инструмент | ROI | Max DD | Win Rate | Trades |
|------------|-----|--------|----------|--------|
| XAUUSD | 45.86% | 16.27% | ~45% | 315 |
| EURUSD | 340.75% | 5.32% | 72% | 189 |

## Установка
```bash
git clone https://github.com/YOUR_USERNAME/BAZA.git
cd BAZA
pip install -r requirements.txt
```

## Настройка

1. Скопируй пример конфига:
```bash
cp config/mt5.yaml.example config/mt5.yaml
```

2. Заполни свои данные MT5 в `config/mt5.yaml`

## Запуск
```bash
# Демо режим (мониторинг без торговли)
python main.py --mode demo

# Бэктест
python main.py --mode backtest --start 2024-01-01 --end 2024-12-31

# Live торговля (осторожно!)
python main.py --mode live
```

## Стратегии

### XAUUSD (Gold)
- Таймфрейм: H1 + M15
- Логика: BOS + Order Block + Premium/Discount zones
- Risk: 0.75% на сделку

### EURUSD
- Таймфрейм: H1 + M15
- Логика: SMC Retracement в Order Blocks
- Risk: 0.5% на сделку

## Disclaimer

Торговля на финансовых рынках связана с рисками.
Используйте на свой страх и риск.
Отредактировать `config/instruments.yaml`:

```yaml
GBPUSD:
  name: "GBP/USD"
  type: "Forex"
  contract_size: 100000
  pip_value: 10.0
  spread: 1.8
  risk_per_trade: 0.5
  price_decimals: 5
```

### Шаг 2: Создать стратегию
Создать файл `strategies/gbpusd_strategy.py` с классом `StrategyGBPUSD`.

### Шаг 3: Обновить портфель
Добавить в `config/portfolio.yaml`:

```yaml
instruments:
  - XAUUSD
  - EURUSD
  - GBPUSD  # новый
```

### Шаг 4: Запустить
```bash
python BAZA/bot.py --mode backtest --start 2024-01-01 --end 2024-12-31
```

**ВСЁ**. Никаких изменений в core коде не требуется.

---

## Режимы работы

### 1. Backtest Mode
```bash
python BAZA/bot.py --mode backtest --start 2023-01-01 --end 2023-12-31
```

### 2. Demo Mode (будущее)
```bash
python BAZA/bot.py --mode demo --mt5-config mt5_demo.ini
```

### 3. Live Mode (будущее)
```bash
python BAZA/bot.py --mode live --mt5-config mt5_live.ini
```

---

## Текущий статус

✅ **Backtest validated (2023-2025)**
- XAUUSD Phase 2 Baseline: WR 60.8%, DD 11.5%, ROI +952%
- EURUSD SMC Retracement: WR 70.7%, DD 5.4%, ROI +324%
- Portfolio (XAUUSD + EURUSD): WR 66.65%, DD 7.62%, ROI +2,382%

⏳ **Pending**: MT5 integration for demo/live trading

---

## Конфигурация портфеля

### Risk Model (по умолчанию)
```
XAUUSD: 0.75% risk per trade
EURUSD: 0.5% risk per trade
Max Total Exposure: 1.25%
```

### Allocation (рекомендуемое)
```
70% capital → EURUSD (stable anchor)
30% capital → XAUUSD (aggressive growth)
```

---

## Важные файлы baseline (НЕ ТРОГАТЬ)

Оригинальные протестированные стратегии:
- `../strategies/xauusd/strategy.py` - XAUUSD Phase 2 Baseline
- `../strategies/eurusd/strategy.py` - EURUSD SMC Retracement v1.0

Результаты:
- `../results/xauusd/` - Backtest результаты XAUUSD
- `../results/eurusd/` - Backtest результаты EURUSD
- `../results/portfolio/` - Portfolio backtests

Документация:
- `../PORTFOLIO_vs_SINGLE_COMPARISON_2023-2025.md` - Полный анализ
- `../PORTFOLIO_VERDICT_2024.md` - Детальный отчёт 2024

---

## Разработка

### Правила
1. ❌ НЕ менять логику в `strategies/` без тестирования
2. ✅ Добавлять новые инструменты через config
3. ✅ Расширять core только если действительно нужно
4. ✅ Документировать все изменения

### Testing
```bash
# Backtest single instrument
python BAZA/bot.py --mode backtest --instrument xauusd --start 2024-01-01 --end 2024-12-31

# Backtest portfolio
python BAZA/bot.py --mode backtest --portfolio --start 2024-01-01 --end 2024-12-31
```

---

## Changelog

**v1.0 (Dec 19, 2025)**
- ✅ Initial structure created
- ✅ Core modules ported from backtest
- ✅ XAUUSD + EURUSD strategies integrated
- ✅ Portfolio manager implemented
- ✅ Modular config system
- ⏳ MT5 integration pending

---

**NOTE**: Все baseline стратегии FROZEN до получения demo результатов.

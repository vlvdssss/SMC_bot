# GBPUSD - FINAL DECISION

## Дата: 20 декабря 2025

---

## ❌ ФИНАЛЬНОЕ РЕШЕНИЕ: EXCLUDE

**GBPUSD полностью исключается из портфеля SMC-framework.**

Протестированы ВСЕ возможные подходы. НИ ОДИН не сработал.

---

## Попытка #1: Mean Reversion

**Концепция**: Range trading, liquidity sweeps, rejection

**Результат**: **FAIL**
- Trades: **0**
- Причина: Range detection не находит подходящих зон
- Sweep + rejection слишком редкие
- Даже с мягкими параметрами - 0 сигналов

**Статус**: REJECTED

---

## Попытка #2: SMC Retracement (FINAL TEST)

**Концепция**: Классический SMC (как EURUSD)
- H1 BOS direction filter
- M15 Order Block retracement
- Premium/Discount zones
- RR 2:1

**Параметры**:
- Risk: 0.5%
- OB lookback: 20 bars
- Swing lookback: 10 bars
- Impulse threshold: 15-20 pips

**Результат**: **FAIL**
- Trades 2023: **0**
- Причина: OB detection не находит подходящих зон
- Либо нет импульсов, либо нет retracement в OB

**Попытки исправления**:
1. ❌ Упрощение OB detection (любая свеча перед импульсом)
2. ❌ Уменьшение impulse threshold (15 pips вместо 20)
3. ❌ Упрощение BOS detection

**Итог**: ВСЁ РАВНО 0 сигналов

**Статус**: FAILED (FINAL)

---

## Анализ причин

### Почему GBPUSD не работает?

**1. Поведение инструмента**:
- GBPUSD не показывает чёткие SMC паттерны
- OB зоны размыты или отсутствуют
- Retracement либо слишком мелкие, либо слишком глубокие
- Нет консистентного поведения для алгоритмической торговли

**2. Отличие от EURUSD**:
| Параметр | EURUSD | GBPUSD |
|----------|--------|--------|
| OB чёткость | ✅ Чёткие | ❌ Размытые |
| Retracement | ✅ Консистентные | ❌ Хаотичные |
| BOS | ✅ Явные | ❓ Неочевидные |
| Trades/year | 176 | **0** |

**3. Техническая проблема**:
- OB detection не срабатывает даже с мягкими параметрами
- Либо нет импульсов (маловероятно)
- Либо импульсы есть, но price action GBPUSD не создаёт tradeable OB zones

---

## Финальная метрика

| Метрика | Целевое значение | GBPUSD Result | Status |
|---------|------------------|---------------|--------|
| Trades/year | > 50 | **0** | ❌ FAIL |
| Win Rate | > 55% | N/A | ❌ N/A |
| ROI | > 100% | **0%** | ❌ FAIL |
| Max DD | < 10% | N/A | ❌ N/A |
| Profit Factor | > 1.4 | N/A | ❌ N/A |

**Все метрики**: ❌ FAIL

---

## Вердикт

### Mean Reversion: ❌ FAIL (0 сделок)
### SMC Retracement: ❌ FAIL (0 сделок)

### GBPUSD: ❌ **ПОЛНОСТЬЮ ИСКЛЮЧЁН**

---

## Итоговый портфель

**APPROVED стратегии**:
- ✅ XAUUSD (0.75% risk) - Phase 2 Baseline - Trend Following
- ✅ EURUSD (0.5% risk) - SMC Retracement Baseline - Pullback Trading

**REJECTED**:
- ❌ GBPUSD (любые варианты)

**Total exposure**: 1.25% (XAUUSD + EURUSD)

---

## Lessons Learned

**1. Не каждый инструмент подходит для SMC**:
- EURUSD работает отлично (176 trades/year, 70.7% WR)
- XAUUSD работает хорошо (148 trades/year, 60.8% WR)
- GBPUSD НЕ работает (0 trades/year)

**2. Price action важнее чем желание диверсификации**:
- Если инструмент не генерирует сигналы = он не подходит
- Лучше 2 рабочих стратегии чем 3 с одной мёртвой
- Quality > Quantity

**3. GBPUSD требует другого подхода**:
- Возможно GBPUSD подходит для breakout strategies
- Или для news trading
- Но НЕ для SMC Retracement или Mean Reversion
- Это НЕ наш style trading

**4. Окончательное решение лучше чем вечные попытки**:
- 2 попытки, 0 результатов = достаточно
- Нет смысла тратить время на 3-ю, 4-ю попытку
- Move on к более перспективным идеям

---

## Рекомендации

### Если захочется расширить портфель в будущем:

**НЕ рассматривать**:
- ❌ GBPUSD (протестирован и failed)
- ❌ Mean reversion на Forex (не работает)

**Рассмотреть**:
- ✅ Другие metal: XAGUSD (Silver) - trend following как XAUUSD
- ✅ Индексы: SPX500 / NAS100 - trend following
- ✅ Crypto: BTCUSD (если есть данные) - volatility trading
- ✅ USDJPY - pullback trading как EURUSD

**Подход**:
- Использовать ТОЛЬКО проверенные концепции (Trend Following / Pullback)
- НЕ пытаться Mean Reversion на Forex
- Тестировать быстро и принимать жёсткие решения

---

## Архив

**Код GBPUSD сохранён**:
- `strategies/gbpusd/strategy.py` - Mean Reversion (REJECTED)
- `strategies/gbpusd/strategy_retracement.py` - SMC Retracement (FAILED)
- `strategies/gbpusd/GBPUSD_VERDICT_REJECTED.md` - Вердикт Mean Reversion

**Данные**:
- `data/backtest/GBPUSD_H1_2023_2025.csv` - сохранить (18,462 bars)
- `data/backtest/GBPUSD_M15_2023_2025.csv` - сохранить (73,811 bars)

**Статус**: ARCHIVED (для reference, но не для использования)

---

## Final Statement

**GBPUSD testing is CLOSED.**

2 approaches tested, 2 approaches failed.  
0 trades generated across all tests.  
No further attempts will be made.  

**SMC-framework portfolio remains:**
- XAUUSD + EURUSD
- 1.25% total exposure
- STABLE and PROVEN

**GBPUSD = EXCLUDED PERMANENTLY**

---

**Решение принято**: 20 декабря 2025  
**Финальность**: ОКОНЧАТЕЛЬНОЕ  
**Статус**: CLOSED

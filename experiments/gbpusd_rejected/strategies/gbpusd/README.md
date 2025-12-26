# GBPUSD Mean Reversion Strategy

## ❌ Статус: REJECTED

**Стратегия отклонена 20 декабря 2025**  
**Причина**: 0 сигналов за год тестирования. Mean reversion концепция не работает на GBPUSD.

См. [GBPUSD_VERDICT_REJECTED.md](GBPUSD_VERDICT_REJECTED.md) для полного анализа.

---

## Оригинальная концепция (АРХИВ)

**Версия**: v0.1 (Candidate)  
**Дата создания**: 20 декабря 2025  
**Инструмент**: GBPUSD (British Pound / US Dollar)

---

## Зачем GBPUSD?

GBPUSD выбран как **третий инструмент** для портфеля по следующим причинам:

1. **Отличное поведение от EURUSD и XAUUSD**:
   - XAUUSD = агрессивный тренд (momentum)
   - EURUSD = стабильные откаты (pullback)
   - GBPUSD = range / mean reversion (возвраты к среднему)

2. **Высокая ликвидность**:
   - Один из самых торгуемых FX pairs
   - Низкий спред (~2 pips)
   - Стабильная корреляция с другими парами

3. **Специфика инструмента**:
   - GBP склонен к **false breakouts** (ложные пробои)
   - Четкие **equal highs/lows** (sweeps)
   - Отличные **range-bound** периоды (флэт)

---

## Роль в портфеле

**Тип**: Mean Reversion / Range Strategy

GBPUSD добавляет диверсификацию через:
- Противоположную логику (против импульса, а не по тренду)
- Заработок во флэте (когда XAUUSD/EURUSD стоят)
- Низкий риск (0.4% per trade)

**Комбинация портфеля**:
- XAUUSD: 0.75% risk → Trend Following
- EURUSD: 0.5% risk → Pullback/Retracement
- GBPUSD: 0.4% risk → Mean Reversion/Range
- **Total**: 1.65% max exposure

---

## Отличие от EURUSD и XAUUSD

| Параметр | XAUUSD | EURUSD | GBPUSD |
|----------|---------|---------|---------|
| **Тип** | Trend Following | Pullback | Mean Reversion |
| **Entry** | По тренду после BOS | Откат в OB | Против импульса после sweep |
| **Цель** | Ride momentum | Catch retracement | Return to range |
| **Risk** | 0.75% (агрессивно) | 0.5% (средне) | 0.4% (консервативно) |
| **WR Target** | 60-65% | 68-72% | 65-70% |
| **Max DD Target** | ~11% | ~5% | < 6% |
| **Trades/day** | 2-3 | 2-3 | 1 (селективно) |

**Ключевое отличие**:
- XAUUSD/EURUSD = торгуют **С трендом/откатом**
- GBPUSD = торгует **ПРОТИВ ложных пробоев** (fakeouts)

---

## Логика стратегии

### 1. HTF Context (H1)

**Range Detection**:
- Определяем Range High / Range Low (EH/EL)
- Проверяем наличие явного тренда
- Если тренд сильный → НЕ ТОРГОВАТЬ

**Условия для торговли**:
- Range должен быть чётким (минимум 2 EH/EL)
- Диапазон 30-80 pips (оптимально для mean reversion)
- Нет серии выше High или ниже Low (нет тренда)

### 2. LTF Setup (M15)

**Liquidity Sweep**:
- Ложный пробой range high/low
- Снятие equal highs/lows
- Быстрый возврат обратно в range

**Rejection Confirmation**:
- Длинная тень (wick > 50% bar)
- Закрытие обратно в диапазон
- Momentum against sweep direction

### 3. Entry Rules

**BUY Setup** (от Range Low):
- H1: Range detected
- M15: Sweep below Range Low (liquidity grab)
- M15: Strong rejection back into range
- Entry: на откате после rejection

**SELL Setup** (от Range High):
- H1: Range detected
- M15: Sweep above Range High (liquidity grab)
- M15: Strong rejection back into range
- Entry: на откате после rejection

### 4. Exit Rules

**Take Profit**:
- Option 1: Mid-range (50% диапазона)
- Option 2: Opposite range boundary (full range)

**Stop Loss**:
- За sweep high/low + buffer (~10 pips)

**Risk/Reward**:
- Target: 1.2 - 1.5 RR
- Консервативный подход

---

## Параметры риска

```yaml
risk_per_trade: 0.4%        # Консервативно (меньше чем EURUSD)
max_trades_per_day: 1       # Селективность
max_drawdown_target: 6%     # Цель
win_rate_target: 65%        # Цель
risk_reward: 1.2-1.5        # Консервативный RR
```

---

## Почему Mean Reversion?

1. **Диверсификация портфеля**:
   - XAUUSD/EURUSD зарабатывают в тренде
   - GBPUSD зарабатывает во флэте/возвратах
   - Снижает общую корреляцию

2. **Поведение GBPUSD**:
   - GBP склонен к false breakouts
   - Частые liquidity sweeps
   - Возвраты к среднему (mean reversion)

3. **Низкий риск**:
   - 0.4% per trade (самый низкий в портфеле)
   - 1 trade/day (селективность)
   - Target DD < 6% (консервативно)

---

## Timeline

### Phase 1: Implementation ✅
- [x] Создать структуру
- [x] Реализовать базовую логику
- [ ] Код без оптимизации

### Phase 2: Backtesting
- [ ] 2023: Полный год
- [ ] 2024: Полный год
- [ ] 2025: YTD

### Phase 3: Portfolio Analysis
- [ ] Сравнение с XAUUSD/EURUSD
- [ ] Корреляционный анализ
- [ ] Общий portfolio performance

### Phase 4: Decision
- [ ] Если WR > 65% и DD < 6% → APPROVE
- [ ] Если нет → REJECT или R&D

---

## Ожидания

**Минимальные требования** (для одобрения):
- Win Rate ≥ 65%
- Max Drawdown < 6%
- ROI > 200% за 3 года
- Trades: 80-120 в год (селективно)

**Если одобрят**:
- Добавить в production portfolio
- Risk: 0.4% per trade
- Max exposure: 1.65% (XAUUSD + EURUSD + GBPUSD)

**Если отклонят**:
- Вернуть в R&D
- Или исключить из портфеля

---

## Примечания

- Это **КАНДИДАТ**, не production
- Логика простая (без оптимизации)
- Цель: проверить концепцию mean reversion
- Бэктест покажет жизнеспособность

**Статус**: Ожидает бэктеста  
**Приоритет**: После XAUUSD/EURUSD validation

---

**Создано**: 20 декабря 2025  
**Автор**: SMC Framework Team

# 📰 Real-Time News Integration

## Overview

BAZA Trading Bot теперь использует **реальные экономические данные** вместо fallback-событий.

## Источники данных

### 1. Trading Economics API ✅ ОСНОВНОЙ
- **URL**: `https://api.tradingeconomics.com/calendar`
- **Доступ**: Публичный endpoint (guest:guest)
- **Лимиты**: Нет (для базового календаря)
- **Данные**: 
  - Экономические события в реальном времени
  - Importance level (1=LOW, 2=MEDIUM, 3=HIGH)
  - Actual, Forecast, Previous values
  - Страны: US, EU, GB, JP, CA, AU, NZ, CH, CN

### 2. Myfxbook (Резервный)
- **URL**: `https://www.myfxbook.com/api/get-economic-calendar.json`
- **Статус**: Резерв (если Trading Economics недоступен)

### 3. FXStreet (Резервный)
- **URL**: `https://calendar-api.fxstreet.com/en/api/v1/eventDates`
- **Статус**: Резерв (если оба предыдущих недоступны)

### 4. Fallback Events
- **Статус**: Используется только если все API недоступны
- **Данные**: Типичные события на основе дня недели

## Impact Levels

### EXTREME 🔴
Критические события, влияющие на все рынки:
- Non-Farm Payrolls (NFP)
- FOMC Meeting Decision
- GDP
- CPI / Core CPI
- Interest Rate Decisions (Fed, ECB, BOE)
- Monetary Policy Statements

### HIGH 🟠
Важные события, влияющие на валютные пары:
- Unemployment Rate
- Retail Sales
- Manufacturing PMI
- ECB Press Conference
- Average Hourly Earnings

### MEDIUM 🟡
Средний impact:
- Jobless Claims
- Services PMI
- Housing Data

### LOW ⚪
Низкий impact:
- Auctions
- Minor indicators

## Использование в боте

### GUI: Live News Feed
```python
# src/gui/app.py, строки 978-1057
events = self.news_fetcher.get_high_impact_events(hours_ahead=24)
```

Показывает:
- До 5 HIGH/EXTREME событий
- Время, валюта, impact badge, заголовок
- Total count высокоимпактных событий на сегодня

### GPT Decision Engine
```python
# Фильтрация: только HIGH/EXTREME
high_impact_news = self.news_fetcher.get_high_impact_events(hours_ahead=4)
```

Отправляется в GPT для анализа влияния на решение.

## Тестирование

### Проверить реальные данные:
```bash
python test_news_parser.py
```

### Проверить будущие события:
```bash
python test_news_tomorrow.py
```

### Проверить NFP день:
```bash
python check_nfp.py
```

## Примеры реальных данных

### Сегодня (22 января 2026):
```
1. 🟡 01:15 UTC | CNY | MEDIUM  | Loan Prime Rate 1Y
   └─ Forecast: 3.0% | Previous: 3% | Actual: 3.0%

2. 🟡 01:15 UTC | CNY | MEDIUM  | Loan Prime Rate 5Y
   └─ Forecast: 3.5% | Previous: 3.5% | Actual: 3.5%
```

### NFP День (первая пятница месяца):
```
🔴 12:30 UTC | USD | EXTREME | Non-Farm Payrolls (NFP)
🟠 12:30 UTC | USD | HIGH    | Unemployment Rate
🟠 12:30 UTC | USD | HIGH    | Average Hourly Earnings
```

### FOMC День (середина месяца):
```
🔴 18:00 UTC | USD | EXTREME | FOMC Meeting Decision
🔴 18:30 UTC | USD | EXTREME | FOMC Press Conference
```

## Конфигурация

### Кеш новостей:
- **Длительность**: 1 час (3600 сек)
- **Обновление**: Автоматически при истечении
- **Ключ кеша**: `events_{YYYY-MM-DD}`

### Таймауты:
- **Request timeout**: 10 секунд
- **Retry**: Автоматический переход к следующему источнику

## Зависимости

```requirements.txt
beautifulsoup4>=4.12.0  # HTML parsing (резерв)
lxml>=5.0.0             # Fast XML/HTML parser
requests>=2.31.0        # HTTP requests
```

## API Rate Limits

### Trading Economics (guest:guest)
- ✅ Нет лимитов для базового календаря
- ✅ Не требует регистрации
- ✅ Публичный доступ

## Логирование

```python
logger.info(f"Parsed {len(events)} events from Trading Economics")
logger.warning(f"Trading Economics returned status {response.status_code}")
logger.error(f"Trading Economics fetch error: {e}")
```

## Обновления

### v2.0 (22.01.2026)
- ✅ Trading Economics API integration
- ✅ Myfxbook backup API
- ✅ FXStreet backup API
- ✅ Улучшенный fallback с большим количеством событий
- ✅ EXTREME keyword expansion (12 ключевых слов)
- ✅ GUI Live News Feed

### v1.0 (Старая версия)
- ❌ Только fallback события
- ❌ Нет реальных данных
- ❌ Ограниченный набор событий

## Известные ограничения

1. **Будущие даты**: Trading Economics не имеет данных для далекого будущего (>1 месяц)
2. **Weekend**: В выходные данных минимум (рынки закрыты)
3. **Rate limits**: Guest access может быть ограничен при очень частых запросах
4. **Cloudflare**: Некоторые сайты блокируют автоматические запросы (403/404)

## Поддержка

Если API недоступны:
1. Проверьте интернет-соединение
2. Проверьте User-Agent в headers
3. Система автоматически переключится на fallback события
4. Лог покажет: "Using fallback typical events (Trading Economics API unavailable)"

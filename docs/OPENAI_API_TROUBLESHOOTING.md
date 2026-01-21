# 🔧 Диагностика ошибок OpenAI API

## Проблема: "ошибка по API GPT когда должен быть сигнал"

### Быстрая диагностика (30 секунд)

1. **Запусти диагностический скрипт:**
```bash
python scripts/test_openai_api.py
```

Скрипт проверит:
- ✅ API ключ найден
- ✅ Формат ключа корректный
- ✅ Соединение с OpenAI работает
- ✅ GPT-4o доступен
- ✅ Квота не исчерпана

---

## Типичные ошибки и решения

### ❌ Ошибка: "API key not found"
**Причина**: Нет файла `config/.env` или ключ не указан

**Решение**:
1. Открой `config/.env` (или создай если нет)
2. Добавь строку:
```
OPENAI_API_KEY=sk-proj-твой_ключ_здесь
```
3. Перезапусти бота

---

### ❌ Ошибка: "Invalid API Key"
**Причина**: Ключ неверный или устарел

**Решение**:
1. Открой https://platform.openai.com/api-keys
2. Создай новый ключ (скопируй полностью!)
3. Замени в `config/.env`:
```
OPENAI_API_KEY=sk-proj-новый_ключ
```
4. Перезапусти бота

---

### ❌ Ошибка: "Rate Limit Error"
**Причина**: Превышен лимит запросов (много запросов за короткое время)

**Решение**:
1. Проверь квоту: https://platform.openai.com/account/usage
2. Убедись, что есть кредиты/активный план
3. Увеличь `min_minutes_between_calls` в `config/ai.yaml`:
```yaml
market_analyst:
  safety:
    min_minutes_between_calls: 60  # Было 30, ставим 60
```
4. Подожди 10-15 минут и попробуй снова

---

### ❌ Ошибка: "Connection Failed"
**Причина**: Нет интернета или блокировка OpenAI

**Решение**:
1. Проверь интернет (открой google.com)
2. Отключи VPN/Proxy
3. Проверь firewall (должен пропускать api.openai.com)
4. Перезапусти роутер

---

### ❌ Ошибка: "Model not found" (gpt-4o)
**Причина**: У тебя нет доступа к GPT-4

**Решение 1** (рекомендуется):
Используй более дешёвую модель `gpt-4o-mini`:
1. Открой `config/ai.yaml`
2. Измени:
```yaml
market_analyst:
  gpt:
    model: gpt-4o-mini  # Было gpt-4o
```
3. Перезапусти бота

**Решение 2**:
Купи доступ к GPT-4:
- https://platform.openai.com/account/billing
- Добавь payment method
- Пополни баланс ($5-20)

---

### ❌ Ошибка: "Timeout"
**Причина**: Запрос к API занял слишком много времени

**Что делается автоматически**:
- Бот повторяет запрос 3 раза
- С увеличивающейся задержкой (2s → 4s → 8s)
- Если все попытки неудачны → используется fallback (безопасный режим)

**Если timeout частый**:
1. Проверь скорость интернета (speedtest.net)
2. Уменьши размер скриншотов в `config/ai.yaml`:
```yaml
market_analyst:
  screenshots:
    bars: 50  # Было 100
```

---

## Как читать логи с новой версией (v1.3.2+)

### Консоль - только важное
```
22:47:29 🔍 [AI] Starting analysis for XAUUSD
22:48:23 ❌ [AI] API ERROR: RateLimitError
22:48:23 💡 [AI] Проблема: превышен лимит запросов
```

### Файл (logs/baza_YYYYMMDD.log) - полная диагностика
```
[DEBUG] Calling OpenAI API...
[ERROR] ❌ RATE LIMIT ERROR (попытка 1/3)
[ERROR] Детали: Rate limit exceeded. Try again in 15s
[ERROR] 💡 Проблема: превышен лимит запросов API
[WARNING] ⏳ Жду 4 секунд перед повтором...
[DEBUG] Calling OpenAI API... (retry 2)
```

---

## Безопасные режимы (Fallback)

Если GPT API не работает, бот **НЕ УПАДЁТ**, а:

1. **Использует кэш** (последний успешный анализ, если < 6 часов)
   - Торговля продолжится по старому анализу
   - В логах: `[AI-Scheduler] Using cached analysis (age: 45min)`

2. **Safe mode** (если кэша нет)
   - НЕ будет новых сделок
   - Блок типа "warning" активируется
   - В логах: `[AI-Scheduler] No valid cache, using safe default`

**Это защищает от торговли без анализа!**

---

## Safety Limits (защита от перерасхода)

В `config/ai.yaml` есть защитные лимиты:

```yaml
market_analyst:
  safety:
    max_daily_calls: 10           # Макс. запросов в день
    max_monthly_cost: 20.0        # Макс. стоимость в месяц ($)
    min_minutes_between_calls: 30 # Мин. интервал между запросами
```

Если лимиты превышены:
- Бот пропустит анализ
- В логах: `[AI-Scheduler] Daily API limit reached (10/10)`
- Торговля продолжится по кэшу (если есть)

---

## Стоимость API

| Модель | Цена (за 1K токенов) | Средний анализ | Стоимость 1 анализа |
|--------|---------------------|----------------|---------------------|
| gpt-4o | $2.50 input / $10.00 output | ~1500 tokens | ~$0.05 |
| gpt-4o-mini | $0.15 input / $0.60 output | ~1500 tokens | ~$0.003 |

**Рекомендация**: Используй `gpt-4o-mini` для экономии (в 15 раз дешевле!)

---

## Проверка перед запуском

Контрольный чек-лист:

- [ ] Файл `config/.env` существует
- [ ] В `.env` есть строка `OPENAI_API_KEY=sk-proj-...`
- [ ] Ключ начинается с `sk-` или `sk-proj-`
- [ ] Скрипт `python scripts/test_openai_api.py` выдаёт ✅
- [ ] Есть интернет соединение
- [ ] На аккаунте OpenAI есть кредиты (https://platform.openai.com/account/usage)

Если все ✅ → всё должно работать!

---

## Логи для отладки

Отправь эти файлы разработчику если проблема не решается:

1. **Последний лог файл**:
   ```
   logs/baza_YYYYMMDD.log
   ```
   (найди строки с `[AI]` и `[ERROR]`)

2. **Конфиг AI**:
   ```
   config/ai.yaml
   ```

3. **Результат диагностики**:
   ```bash
   python scripts/test_openai_api.py > diagnosis.txt
   ```

---

## Полезные ссылки

- **API Keys**: https://platform.openai.com/api-keys
- **Usage & Billing**: https://platform.openai.com/account/usage
- **Status Page**: https://status.openai.com/
- **Pricing**: https://openai.com/api/pricing/

---

**Обновлено**: 21.01.2026 (v1.3.2)

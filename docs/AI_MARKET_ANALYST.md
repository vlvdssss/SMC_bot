# AI Market Analyst - Документация по Интеграции

## 📋 Обзор Системы

Система AI Market Analyst интегрирует ChatGPT в торговый бот для глубокого анализа рынка и генерации торговых сигналов.

## 🏗️ Архитектура

```
src/ai/
├── market_analyst.py      # 🧠 Главный сервис: анализ с GPT + скриншоты
├── signal_manager.py      # 📊 Управление AI-сигналами и блокировками
├── analyst_scheduler.py   # ⏰ Автозапуск в 06:00 и 18:00
└── screenshot_service.py  # 📸 Создание графиков для GPT

data/
├── ai_analysis/          # История анализов (JSON)
├── ai_signals/           # Активные сигналы
└── screenshots/          # Графики M15/H1
```

## 🔄 Логика Работы

```
06:00/18:00 → Scheduler triggers
     ↓
MarketAnalyst:
  - Захватывает M15 + H1 графики
  - Считает метрики (ATR, trend, Premium/Discount)
  - Получает новости
  - Отправляет в GPT-4 Vision
     ↓
GPT возвращает JSON:
  - sentiment, confidence, market_structure
  - signals: [{entry, SL, TP, trigger_time, confidence}]
  - trading_blocks: {block_trading, reason}
     ↓
SignalManager:
  - Создает триггеры для сигналов
  - Устанавливает блокировки
  - Мониторит цены
     ↓
LiveTrader:
  - Проверяет блокировки перед входом
  - Выполняет триггеры при достижении цены/времени
     ↓
GUI:
  - Отображает анализ
  - Показывает активные сигналы
  - Статус блокировок
```

## 📊 JSON Формат Ответа GPT

```json
{
  "timestamp": "2026-01-07T06:00:00",
  "symbol": "XAUUSD",
  "summary": {
    "market_structure": "bullish",
    "trend_strength": 75,
    "sentiment": "bullish",
    "confidence": 80
  },
  "key_levels": {
    "support": [2650.0, 2640.0],
    "resistance": [2680.0, 2690.0],
    "current_value_area": "discount"
  },
  "signals": [
    {
      "type": "BUY",
      "entry_price": 2665.0,
      "stop_loss": 2660.0,
      "take_profit": 2675.0,
      "trigger_time": "12:00",
      "reasoning": "Strong bullish structure, price in discount zone",
      "confidence": 75,
      "risk_reward": 2.0
    }
  ],
  "trading_blocks": {
    "block_trading": false,
    "block_until": null,
    "reason": null
  },
  "risk_factors": [
    "High impact news at 14:00"
  ],
  "analysis": {
    "M15": "Short timeframe shows...",
    "H1": "Hourly timeframe confirms...",
    "overall": "Market is in strong bullish trend..."
  }
}
```

## 🎯 Основные Возможности

### 1. Автоматический Анализ
- Запускается в 06:00 и 18:00 ежедневно
- Полностью автоматический pipeline
- Результаты сохраняются в JSON

### 2. Торговые Сигналы
- GPT предлагает конкретные уровни входа/SL/TP
- Указывает время входа ("immediate", "12:00", "15:00")
- SignalManager ставит триггеры
- При достижении цены+времени - сигнал активируется

### 3. Блокировки Торговли
- GPT может заблокировать торговлю при плохих новостях
- Блокировка автоматически проверяется в LiveTrader
- Блокировка может быть с таймаутом

### 4. GUI Интеграция
- Новая вкладка "AI Market Analysis"
- Кнопка ручного запуска
- Отображение sentiment/confidence/signals
- Статус блокировок

## 🚀 Установка и Запуск

### Шаг 1: Установить зависимости

```bash
pip install openai matplotlib pillow
```

### Шаг 2: Проверить API ключ

Убедись что в `.env` есть:
```
OPENAI_API_KEY=sk-...
```

### Шаг 3: Интегрировать в app.py

См. файл `src/gui/ai_analysis_section.py` - там весь код с комментариями где что добавлять.

### Шаг 4: Интегрировать с LiveTrader

В `src/live/live_trader.py` добавить проверку блокировок перед входом.

## 📝 Пример Использования

### Manual Trigger (из GUI):
```python
# Нажать кнопку "Запустить Анализ" в GUI
# Или из кода:
from src.ai.analyst_scheduler import get_scheduler

scheduler = get_scheduler()
result = scheduler.run_now("XAUUSD")
print(result['summary']['sentiment'])
```

### Programmatic:
```python
from src.ai.market_analyst import MarketAnalystService
from src.ai.signal_manager import AISignalManager

# 1. Run analysis
analyst = MarketAnalystService()
analysis = analyst.analyze_market("XAUUSD")

# 2. Process signals
signal_mgr = AISignalManager()
summary = signal_mgr.process_analysis(analysis)

# 3. Check blocks
allowed, reason = signal_mgr.is_trading_allowed()
if not allowed:
    print(f"Trading blocked: {reason}")

# 4. Get active signals
signals = signal_mgr.get_active_signals("XAUUSD")
for signal in signals:
    print(f"{signal['type']} @ {signal['entry_price']}")
```

## ⚙️ Конфигурация

### Изменить расписание:
```python
# src/ai/analyst_scheduler.py, line 30-34
self.schedule_times = [
    dt_time(6, 0),   # 06:00
    dt_time(12, 0),  # 12:00 (добавить)
    dt_time(18, 0)   # 18:00
]
```

### Изменить метрики:
Редактировать `market_analyst.py`, метод `_calculate_metrics()`.

### Изменить prompt:
Редактировать `market_analyst.py`, метод `_build_analysis_prompt()`.

## 🔒 Безопасность

### 1. Confidence Threshold
SignalManager автоматически отфильтровывает сигналы с confidence < 50%

### 2. Trading Blocks
GPT может заблокировать торговлю при:
- Высокоимпактных новостях
- Непонятной структуре рынка
- Высокой волатильности

### 3. Signal Expiration
Сигналы автоматически удаляются через 24 часа

### 4. Manual Override
Все блокировки и сигналы можно очистить вручную из GUI

## 📈 Интеграция с LiveTrader

Добавить в `src/live/live_trader.py`:

```python
from src.ai.signal_manager import AISignalManager

class LiveTrader:
    def __init__(self):
        # ... existing code ...
        self.ai_signal_manager = AISignalManager()
    
    def should_trade(self, symbol):
        """Check if trading is allowed."""
        # Check AI blocks
        allowed, reason = self.ai_signal_manager.is_trading_allowed(symbol)
        if not allowed:
            logger.warning(f"[AI] Trading blocked: {reason}")
            return False
        return True
    
    def check_ai_triggers(self, symbol, current_price):
        """Check if any AI signals should trigger."""
        triggered = self.ai_signal_manager.check_triggers(
            current_price, 
            symbol, 
            datetime.now()
        )
        
        for signal in triggered:
            logger.info(f"[AI] Signal triggered: {signal.type} @ {signal.entry_price}")
            # Execute trade based on signal
            self.execute_ai_signal(signal)
    
    def execute_ai_signal(self, signal):
        """Execute trade from AI signal."""
        # Convert AISignal to trade execution
        # Use signal.entry_price, signal.stop_loss, signal.take_profit
        pass
```

## 🧪 Тестирование

### Test 1: Run Analysis
```bash
python -m src.ai.market_analyst
```

### Test 2: Screenshot Service
```bash
python -m src.ai.screenshot_service
```

### Test 3: Signal Manager
```bash
python -m src.ai.signal_manager
```

### Test 4: Full Pipeline
```bash
python -m src.ai.analyst_scheduler
```

## 📊 Мониторинг

### Logs:
- Все операции логируются через `src.core.logger`
- Префикс `[AI]` для AI компонентов

### Files:
- `data/ai_analysis/latest.json` - последний анализ
- `data/ai_analysis/*.json` - история
- `data/ai_signals/active_signals.json` - активные сигналы
- `data/screenshots/*.png` - графики

## ⚠️ Риски и Ограничения

### 1. API Costs
- GPT-4 Vision ~$0.01-0.03 за запрос
- 2 запроса/день = ~$0.60/месяц
- Monitor usage через OpenAI dashboard

### 2. API Failures
- Fallback response блокирует торговлю при ошибке
- Сохраненный анализ используется если API недоступен

### 3. False Signals
- GPT может ошибаться
- Используй confidence threshold (>70%)
- Всегда проверяй reasoning

### 4. Latency
- Анализ занимает 10-30 секунд
- Не блокирует основную стратегию
- Работает параллельно

## 🔧 Расширения

### Добавить больше метрик:
Редактировать `_calculate_metrics()` в market_analyst.py

### Добавить другие символы:
```python
analyst.analyze_market("EURUSD")
signal_mgr.process_analysis(analysis)
```

### Добавить ML модель:
Заменить GPT на локальную модель в `_call_gpt_api()`

### Добавить multi-timeframe:
Добавить M5, H4, D1 в `_capture_charts()`

## 📚 Дополнительно

### Файлы проекта:
- `src/ai/market_analyst.py` - 400 строк
- `src/ai/signal_manager.py` - 300 строк
- `src/ai/analyst_scheduler.py` - 200 строк
- `src/ai/screenshot_service.py` - 150 строк
- `src/gui/ai_analysis_section.py` - 400 строк GUI кода

### Total: ~1450 строк кода

---
**Создано: 2026-01-07**
**Версия: 1.0**
**Статус: Ready for Integration**

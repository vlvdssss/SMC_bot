# BAZA Trading Bot

Автоматизированная торговая система с AI-анализом рынка для MetaTrader 5.

## 📋 Возможности

- **AI Market Analysis**: Анализ рыночных графиков через GPT-4o Vision API
- **Pure AI Trading Mode**: Торговля исключительно на основе AI-сигналов
- **Smart Order Management**: Управление позициями с trailing stop, partial TP
- **Risk Management**: Автоматический расчет позиции на основе риска
- **Telegram Integration**: Уведомления о сделках и состоянии бота
- **GUI Interface**: Удобный интерфейс на Tkinter
- **Multi-Instrument Support**: Торговля EURUSD, XAUUSD и других инструментов
- **AI Signal System v2.0**: Система управления сигналами с TTL, блокировками, мультипликаторами риска

## 🚀 Быстрый старт

### Требования

- Python 3.12+
- MetaTrader 5
- OpenAI API ключ

### Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте конфигурационные файлы:
   - `config/mt5.yaml` - настройки MT5
   - `config/ai.yaml` - настройки AI анализа
   - `config/telegram.yaml` - настройки Telegram бота
   - `config/portfolio.yaml` - настройки риск-менеджмента
   - `config/trading.yaml` - настройки торговли

4. Запустите бота:
```bash
python main.py
```

## ⚙️ Конфигурация

### AI Analysis (config/ai.yaml)

```yaml
openai:
  api_key: "your-api-key"
  model: "gpt-4o"
  vision_model: "gpt-4o"
  temperature: 0.7
  max_tokens: 2000

market_analyst:
  enabled: true
  schedule:
    - "03:00"
    - "06:00"
    - "09:00"
    - "12:00"
    - "15:00"
    - "18:00"
    - "21:00"
  
  signals:
    min_rr: 1.5  # Минимальный Risk/Reward
    min_confidence: 70  # Минимальная уверенность (%)
```

### Trading Settings (config/trading.yaml)

```yaml
risk:
  sl_pips: 30
  tp_pips: 60
  base_risk_percent: 1.0

trailing_stop:
  enabled: true
  activation_profit_pips: 20
  trailing_distance_pips: 15

hours:
  enabled: true
  start: "00:00"
  end: "23:59"
```

### MetaTrader 5 (config/mt5.yaml)

```yaml
account:
  login: your_login
  password: your_password
  server: "broker_server"
```

## 📊 Структура проекта

```
BAZA/
├── config/          # Конфигурационные файлы
├── src/
│   ├── ai/         # AI анализ и сигналы
│   ├── core/       # Ядро системы
│   ├── gui/        # Графический интерфейс
│   ├── mt5/        # Интеграция с MT5
│   ├── strategies/ # Торговые стратегии
│   └── monitoring/ # Мониторинг и логирование
├── data/           # Данные (анализы, сделки, статистика)
├── logs/           # Логи работы бота
├── dist/           # Скомпилированный EXE
└── main.py         # Точка входа

```

## 🤖 AI Market Analyst

AI Market Analyst использует GPT-4o Vision для анализа графиков:

1. **Screenshot Analysis**: Захват и анализ графика MT5
2. **Market Context**: Анализ текущей рыночной ситуации
3. **Signal Generation**: Создание торговых сигналов с RR и confidence
4. **Signal Management**: TTL (3 часа), блокировки, мультипликаторы риска

### Пример AI сигнала

```json
{
  "action": "buy",
  "entry": 1.08500,
  "stop_loss": 1.08200,
  "take_profit": 1.09100,
  "risk_reward": 2.0,
  "confidence": 85
}
```

## 🔐 Безопасность

- Чувствительные данные (пароли, API ключи) хранятся в `*.enc` файлах
- Файлы `*.yaml.example` - шаблоны для настройки
- Не коммитьте реальные учетные данные в Git

## 📝 Логирование

Логи сохраняются в `logs/baza_YYYYMMDD.log` с ротацией по дням.

Уровни логирования:
- INFO: Основная информация о работе
- WARNING: Предупреждения
- ERROR: Ошибки
- DEBUG: Детальная отладочная информация

## 🔨 Сборка EXE

```bash
python build_exe.py
```

Результат: `dist/BAZA_TradingBot.exe` (~218 MB)

## 📞 Telegram уведомления

Бот отправляет уведомления о:
- Запуске/остановке бота
- Новых сделках (открытие/закрытие)
- AI анализах рынка
- Критических ошибках

## ⚠️ Дисклеймер

Эта программа предоставляется "как есть". Торговля на финансовых рынках связана с риском потери капитала. Автор не несет ответственности за убытки.

## 📄 Лицензия

MIT License

## 🤝 Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

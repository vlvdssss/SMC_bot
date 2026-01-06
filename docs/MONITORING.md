# 🔔 Система Мониторинга и Уведомлений

Полнофункциональная система мониторинга торговли с Telegram, Email уведомлениями и сбором метрик.

---

## 📦 Модули

### 1. TelegramNotifier
**Файл:** [src/monitoring/telegram_notifier.py](../src/monitoring/telegram_notifier.py)

Отправка уведомлений в Telegram через Bot API.

**Возможности:**
- ✅ Уведомления об открытии/закрытии сделок
- ✅ Ежедневные отчеты
- ✅ Алерты разных уровней
- ✅ Уведомления о запуске/остановке бота
- ✅ HTML форматирование сообщений

**Пример использования:**
```python
from src.monitoring import TelegramNotifier

# Инициализация
telegram = TelegramNotifier(
    token="YOUR_BOT_TOKEN",
    chat_id="YOUR_CHAT_ID"
)

# Уведомление об открытии сделки
telegram.send_trade_opened(
    symbol="XAUUSD",
    direction="BUY",
    lot=0.1,
    entry=2650.50,
    sl=2645.00,
    tp=2660.00
)

# Дневной отчет
stats = {
    'balance': 10500.0,
    'profit': 500.0,
    'total_trades': 8,
    'winning_trades': 6,
    'losing_trades': 2,
    'winrate': 75.0,
    'roi': 5.0
}
telegram.send_daily_report(stats)

# Алерт
telegram.send_alert(
    alert_type="HIGH DRAWDOWN",
    message="Просадка превысила 15%",
    level="WARNING"
)
```

---

### 2. AlertManager
**Файл:** [src/monitoring/alert_manager.py](../src/monitoring/alert_manager.py)

Система управления алертами с автоматическими проверками лимитов.

**Типы алертов:**
- `DRAWDOWN` - Превышение максимальной просадки
- `DAILY_LOSS` - Превышение дневного лимита убытков
- `POSITION_SIZE` - Слишком большая позиция
- `CONNECTIVITY` - Проблемы с MT5
- `STRATEGY_ERROR` - Ошибки в стратегии
- `ML_ERROR` - Ошибки ML модели
- `NEWS_HIGH_IMPACT` - Важные новости
- `CONSECUTIVE_LOSSES` - Серия убытков
- `LOW_MARGIN` - Низкий уровень маржи

**Уровни критичности:**
- `INFO` - Информационные
- `WARNING` - Предупреждения
- `ERROR` - Ошибки
- `CRITICAL` - Критические

**Пример:**
```python
from src.monitoring import AlertManager
from src.monitoring.telegram_notifier import TelegramNotifier

# Инициализация
alert_manager = AlertManager()
telegram = TelegramNotifier(token="...", chat_id="...")

# Добавление обработчика
def telegram_handler(alert):
    if alert.level.value in ["WARNING", "ERROR", "CRITICAL"]:
        telegram.send_alert(
            alert_type=alert.type.value,
            message=alert.message,
            level=alert.level.value
        )

alert_manager.add_handler(telegram_handler)

# Настройка порогов
alert_manager.set_threshold('max_drawdown_pct', 15.0)
alert_manager.set_threshold('daily_loss_pct', 3.0)

# Автоматические проверки
alert_manager.check_drawdown(current_equity=9500, peak_equity=10000)
alert_manager.check_daily_loss(daily_pnl=-300, starting_balance=10000)
alert_manager.check_consecutive_losses(loss_count=5)

# Статистика
stats = alert_manager.get_stats()
print(f"Алертов за 24 часа: {stats['last_24h']}")
```

---

### 3. MetricsCollector
**Файл:** [src/monitoring/metrics_collector.py](../src/monitoring/metrics_collector.py)

Сбор и анализ метрик торговли.

**Типы метрик:**
- `TradeMetrics` - Метрики отдельной сделки
- `DailyMetrics` - Дневные метрики

**Возможности:**
- ✅ Сбор метрик по каждой сделке
- ✅ Агрегация дневной статистики
- ✅ Анализ производительности стратегий
- ✅ Расчет Winrate, ROI, Drawdown
- ✅ Экспорт в CSV/JSON

**Пример:**
```python
from src.monitoring import MetricsCollector
from src.monitoring.metrics_collector import TradeMetrics
from datetime import datetime

# Инициализация
metrics = MetricsCollector(data_dir="data/metrics")

# Добавление метрики сделки
trade = TradeMetrics(
    timestamp=datetime.now().isoformat(),
    symbol="EURUSD",
    direction="BUY",
    lot_size=0.1,
    entry_price=1.0850,
    exit_price=1.0900,
    profit=50.0,
    pips=50.0,
    duration_minutes=120,
    strategy="EURUSDStrategy",
    ml_confidence=0.75,
    gpt_filtered=True
)
metrics.add_trade_metrics(trade)

# Получение дневной статистики
daily_stats = metrics.get_daily_stats()
print(f"Сделок сегодня: {daily_stats['trades']}")
print(f"Профит: ${daily_stats['profit']:.2f}")
print(f"Winrate: {daily_stats['winrate']:.1f}%")

# Завершение дня
daily_metrics = metrics.finalize_day(ending_balance=10500.0)

# Статистика за период
period_stats = metrics.get_period_stats(days=30)
print(f"Профит за 30 дней: ${period_stats['total_profit']:.2f}")
print(f"Средний ROI: {period_stats['avg_daily_roi']:.2f}%")

# Анализ стратегий
strategy_perf = metrics.get_strategy_performance()
for name, stats in strategy_perf.items():
    print(f"{name}: Winrate={stats['winrate']:.1f}%")

# Экспорт
metrics.export_to_csv("data/exports/trades_2024.csv")
```

---

### 4. EmailNotifier
**Файл:** [src/monitoring/email_notifier.py](../src/monitoring/email_notifier.py)

Email уведомления для критических событий.

**Возможности:**
- ✅ Критические алерты
- ✅ Ежедневные отчеты
- ✅ Алерты о drawdown
- ✅ Ошибки подключения

**Пример:**
```python
from src.monitoring.email_notifier import EmailNotifier

# Инициализация (Gmail)
email = EmailNotifier(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    email_from="your.email@gmail.com",
    email_password="your_app_password",  # App Password!
    email_to=["recipient@example.com"]
)

# Критический алерт
email.send_critical_alert(
    alert_type="HIGH DRAWDOWN",
    message="Просадка достигла 18%! Требуется вмешательство."
)

# Дневной отчет
stats = {
    'balance': 10500.0,
    'profit': 500.0,
    'roi': 5.0,
    'total_trades': 8,
    'winning_trades': 6,
    'losing_trades': 2,
    'winrate': 75.0,
    'max_drawdown': 8.5,
    'current_drawdown': 2.3
}
email.send_daily_report(stats)
```

---

## ⚙️ Настройка

### 1. Создание конфигурации

```bash
# Скопируйте пример
cp config/monitoring.yaml.example config/monitoring.yaml

# Отредактируйте настройки
notepad config/monitoring.yaml
```

### 2. Telegram Bot

**Шаг 1:** Создайте бота
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Сохраните **Bot Token**

**Шаг 2:** Получите Chat ID
1. Найдите @userinfobot
2. Отправьте `/start`
3. Сохраните ваш **Chat ID**

**Шаг 3:** Настройте в `monitoring.yaml`
```yaml
telegram:
  enabled: true
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
  chat_id: "123456789"
```

### 3. Email (Gmail)

**Шаг 1:** Создайте App Password
1. Войдите в Google Account
2. Безопасность → Двухфакторная аутентификация
3. Пароли приложений → Выберите "Другое"
4. Создайте пароль

**Шаг 2:** Настройте в `monitoring.yaml`
```yaml
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  email_from: "your.email@gmail.com"
  email_password: "abcd efgh ijkl mnop"  # 16-символьный App Password
  email_to:
    - "recipient@example.com"
```

### 4. Настройка порогов алертов

```yaml
alerts:
  thresholds:
    max_drawdown_pct: 20.0
    daily_loss_pct: 5.0
    max_position_size: 10.0
    consecutive_losses: 5
    min_margin_level: 200.0
```

---

## 🚀 Интеграция в бота

### Вариант 1: Базовая интеграция

```python
# В main.py или bot_manager.py
from src.monitoring import TelegramNotifier, AlertManager, MetricsCollector
import yaml

# Загрузка конфигурации
with open('config/monitoring.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Инициализация
telegram = TelegramNotifier(
    token=config['telegram']['bot_token'],
    chat_id=config['telegram']['chat_id']
) if config['telegram']['enabled'] else None

alert_manager = AlertManager()
metrics = MetricsCollector()

# Связывание AlertManager с Telegram
if telegram:
    def telegram_alert_handler(alert):
        telegram.send_alert(
            alert_type=alert.type.value,
            message=alert.message,
            level=alert.level.value
        )
    alert_manager.add_handler(telegram_alert_handler)

# При запуске бота
if telegram and config['telegram']['notify_on']['startup']:
    telegram.send_startup(
        mode="LIVE",
        instruments=["XAUUSD", "EURUSD"]
    )

# При открытии сделки
if telegram and config['telegram']['notify_on']['trade_opened']:
    telegram.send_trade_opened(
        symbol=trade.symbol,
        direction=trade.type,
        lot=trade.volume,
        entry=trade.price_open,
        sl=trade.sl,
        tp=trade.tp
    )

# Добавление метрики
from src.monitoring.metrics_collector import TradeMetrics
trade_metric = TradeMetrics(
    timestamp=datetime.now().isoformat(),
    symbol=trade.symbol,
    direction=trade.type,
    lot_size=trade.volume,
    entry_price=trade.price_open,
    exit_price=trade.price_close,
    profit=trade.profit,
    pips=calculate_pips(trade),
    duration_minutes=calculate_duration(trade),
    strategy="EURUSDStrategy"
)
metrics.add_trade_metrics(trade_metric)

# Проверка алертов
alert_manager.check_drawdown(current_equity, peak_equity)
alert_manager.check_daily_loss(daily_pnl, starting_balance)
```

---

## 📊 Примеры уведомлений

### Telegram - Открытие сделки
```
🚀 Открыта сделка

📊 Инструмент: XAUUSD
📈 Направление: BUY
💰 Объем: 0.1 лот

💵 Вход: 2650.50
🛑 Stop Loss: 2645.00
🎯 Take Profit: 2660.00

⏰ Время: 2026-01-05 14:30:15
```

### Telegram - Дневной отчет
```
📊 Дневной отчет

💰 Баланс: $10,500.00
📈 Профит: $500.00

📊 Сделки: 8
✅ Прибыльных: 6
❌ Убыточных: 2

🎯 Winrate: 75.0%
📈 ROI: 5.00%

⏰ 2026-01-05
```

### Email - Критический алерт
```
КРИТИЧЕСКИЙ АЛЕРТ ОТ BAZA TRADING BOT

Тип: HIGH DRAWDOWN
Время: 2026-01-05 18:45:30

Сообщение:
Просадка достигла 18.5%! Лимит: 15.0%

---
Требуется немедленное внимание!
```

---

## 📈 Анализ метрик

### Команды для анализа

```python
# Дневная статистика
daily = metrics.get_daily_stats()
print(f"Profitability: {daily['winrate']:.1f}%")

# Статистика за месяц
monthly = metrics.get_period_stats(days=30)
print(f"Total profit: ${monthly['total_profit']:.2f}")
print(f"Avg daily ROI: {monthly['avg_daily_roi']:.2f}%")

# Производительность стратегий
strategies = metrics.get_strategy_performance()
for name, stats in strategies.items():
    print(f"{name}:")
    print(f"  Trades: {stats['total_trades']}")
    print(f"  Winrate: {stats['winrate']:.1f}%")
    print(f"  Avg profit: ${stats['avg_profit']:.2f}")
```

---

## 🔧 Расширенные настройки

### Cooldown алертов

Избегайте спама одинаковых алертов:

```python
alert_manager.alert_cooldown = timedelta(hours=2)  # 2 часа между алертами
```

### Множественные обработчики

```python
# Email для критических
def email_handler(alert):
    if alert.level == AlertLevel.CRITICAL:
        email.send_critical_alert(alert.type.value, alert.message)

# Telegram для всех WARNING+
def telegram_handler(alert):
    if alert.level.value in ["WARNING", "ERROR", "CRITICAL"]:
        telegram.send_alert(...)

alert_manager.add_handler(email_handler)
alert_manager.add_handler(telegram_handler)
```

### Автоматические дневные отчеты

```python
import schedule

def send_daily_report():
    stats = metrics.get_daily_stats()
    stats['balance'] = get_current_balance()
    
    if telegram:
        telegram.send_daily_report(stats)
    if email:
        email.send_daily_report(stats)
    
    # Завершение дня
    metrics.finalize_day(stats['balance'])

# Запланировать на 23:55
schedule.every().day.at("23:55").do(send_daily_report)
```

---

## 📝 Зависимости

Добавьте в `requirements.txt` или `pyproject.toml`:

```
requests>=2.31.0  # Для Telegram API
pyyaml>=6.0       # Для конфигурации
```

Email работает со стандартной библиотекой Python (smtplib).

---

## ⚠️ Безопасность

### Защита токенов

**НЕ коммитьте токены в Git!**

```bash
# Добавьте в .gitignore
config/monitoring.yaml
*.env
```

### Использование переменных окружения

```python
import os

telegram = TelegramNotifier(
    token=os.getenv('TELEGRAM_BOT_TOKEN'),
    chat_id=os.getenv('TELEGRAM_CHAT_ID')
)
```

### Gmail App Passwords

- Используйте **App Passwords**, не основной пароль
- Включите двухфакторную аутентификацию
- Отзывайте неиспользуемые пароли

---

## 🎯 Чеклист настройки

- [ ] Создан Telegram бот через @BotFather
- [ ] Получен Chat ID через @userinfobot
- [ ] Создан Gmail App Password (если используется email)
- [ ] Скопирован `monitoring.yaml.example` → `monitoring.yaml`
- [ ] Настроены токены и пароли
- [ ] Добавлен `monitoring.yaml` в `.gitignore`
- [ ] Протестированы уведомления
- [ ] Настроены пороги алертов
- [ ] Интегрировано в основной бот

---

## 🐛 Отладка

### Telegram не работает

```python
# Проверка токена
import requests
url = f"https://api.telegram.org/bot{TOKEN}/getMe"
print(requests.get(url).json())

# Проверка chat_id
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
print(requests.get(url).json())
```

### Email не отправляется

```python
# Gmail: убедитесь что используется App Password
# Проверьте порт: 587 для TLS, 465 для SSL
# Проверьте настройки безопасности аккаунта
```

---

## 📚 Дополнительно

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Gmail SMTP настройка](https://support.google.com/mail/answer/7126229)
- [Google App Passwords](https://support.google.com/accounts/answer/185833)

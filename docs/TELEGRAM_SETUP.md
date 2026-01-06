# Быстрая настройка Telegram уведомлений

## 1️⃣ Создать Telegram бота

1. Найдите **@BotFather** в Telegram
2. Отправьте `/newbot`
3. Введите имя бота (например: `BAZA Trading Bot`)
4. Введите username (например: `baza_trading_bot`)
5. Сохраните **Bot Token** (например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 2️⃣ Получить Chat ID

1. Найдите **@userinfobot** в Telegram
2. Отправьте `/start`
3. Бот покажет ваш **Chat ID** (например: `123456789`)

## 3️⃣ Настроить бота

Создайте файл `config/telegram.yaml`:

```yaml
telegram:
  enabled: true
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # Ваш токен
  chat_id: "123456789"  # Ваш chat ID
  
  notify:
    startup: true
    shutdown: true
    trade_opened: true
    trade_closed: true
    daily_report: true
    alerts: true
    
  alert_min_level: "WARNING"
```

## 4️⃣ Проверить работу

Запустите бота и проверьте, что пришло уведомление о запуске в Telegram!

## 📱 Что вы будете получать

- 🚀 **Запуск/остановка бота**
- 📈 **Открытие сделки** - инструмент, направление, объем, цены SL/TP
- ✅ **Закрытие сделки** - профит, пипсы, длительность
- ⚠️ **Алерты** - drawdown, убытки, проблемы с MT5
- 📊 **Дневной отчет** - баланс, сделки, winrate

## 🔐 Безопасность

**Не коммитьте `config/telegram.yaml` в Git!**

Добавьте в `.gitignore`:
```
config/telegram.yaml
```

## 🐛 Если не работает

1. Проверьте токен - попробуйте отправить тестовое сообщение:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   ```

2. Проверьте Chat ID - убедитесь что написали боту `/start`

3. Проверьте файл конфигурации:
   ```bash
   cat config/telegram.yaml
   ```

4. Посмотрите логи:
   ```bash
   tail -f logs/baza_*.log
   ```

## 💡 Советы

- Используйте отдельные боты для demo/live торговли
- Добавьте нескольких получателей через группу
- Отключайте ненужные уведомления через `notify` в конфиге
- Алерты можно фильтровать по уровню (`INFO`, `WARNING`, `ERROR`, `CRITICAL`)

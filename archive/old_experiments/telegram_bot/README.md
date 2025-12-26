# Telegram Bot Integration

## Setup

1. **Install dependencies:**
```bash
pip install python-telegram-bot
```

2. **Get your Chat ID:**
   - Open Telegram
   - Send message to `@userinfobot`
   - Bot will reply with your Chat ID

3. **Configure bot:**
   - Open `telegram/config.json`
   - Add your Chat ID
   - Set `enabled: true`

## Configuration

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "enabled": true,
  "notifications": {
    "trade_opened": true,
    "trade_closed": true,
    "system_status": true,
    "daily_report": true,
    "errors": true
  },
  "commands_enabled": true
}
```

## Available Commands

- `/start` - Start trading system
- `/stop` - Stop trading system  
- `/status` - Get current system status
- `/report` - Get trading performance report
- `/help` - Show help message

## Notifications

Bot automatically sends notifications for:

✅ Trade openings (entry, SL, TP)  
✅ Trade closings (exit, profit/loss)  
✅ System status changes (MT5 connection, errors)  
✅ Daily performance reports  
✅ Error alerts  

## Usage in Code

```python
from telegram import TelegramBotManager

# Initialize bot
bot = TelegramBotManager()

# Send trade notification
bot.notify_trade_opened(
    symbol="XAUUSD",
    direction="BUY",
    entry=2650.50,
    sl=2645.00,
    tp=2660.00,
    volume=0.01
)

# Send custom message
bot.send_notification("System started successfully")
```

## Security

- Bot only responds to your Chat ID
- Unauthorized access attempts are logged
- Token stored in config.json (add to .gitignore)

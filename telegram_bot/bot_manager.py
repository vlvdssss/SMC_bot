"""
Telegram Bot Manager

Handles all Telegram bot interactions:
- Send notifications (trade events, status updates, errors)
- Receive commands (start/stop trading, get status, reports)
- Authentication and security
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import logging
import threading

try:
    from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Create dummy classes to avoid NameError in type hints
    class Update:
        pass
    class ContextTypes:
        DEFAULT_TYPE = None
    class Bot:
        pass
    class Application:
        pass
    class InlineKeyboardButton:
        pass
    class InlineKeyboardMarkup:
        pass
    class CallbackQueryHandler:
        pass
    print("⚠️ python-telegram-bot not installed. Run: pip install python-telegram-bot")


class TelegramBotManager:
    """Manages Telegram bot for notifications and commands."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize Telegram bot manager.
        
        Args:
            config_path: Path to config file (default: telegram/config.json)
        """
        if not TELEGRAM_AVAILABLE:
            self.enabled = False
            return
        
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"
        else:
            config_path = Path(config_path)
        
        self.config_path = config_path
        self.config = self._load_config()
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.enabled = self.config.get('enabled', False) and self.config.get('chat_id') is not None
        self.polling_thread: Optional[threading.Thread] = None
        self.is_polling = False
        
        # Callbacks for commands
        self.on_start_command: Optional[Callable] = None
        self.on_stop_command: Optional[Callable] = None
        self.on_status_command: Optional[Callable] = None
        self.on_report_command: Optional[Callable] = None
        
        self.logger = logging.getLogger('TelegramBot')
        # Configure a file handler so bot logs are captured even when running as an EXE
        try:
            log_folder = Path(__file__).parent.parent / 'logs'
            log_folder.mkdir(parents=True, exist_ok=True)
            log_file = log_folder / 'telegram_bot.log'
            if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
                fh = logging.FileHandler(str(log_file), encoding='utf-8')
                fh.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] [TelegramBot] %(message)s')
                fh.setFormatter(formatter)
                self.logger.addHandler(fh)
            self.logger.setLevel(logging.DEBUG)
        except Exception:
            pass
        
        if self.enabled:
            self._initialize_bot()
            self.start_polling_async()  # Auto-start polling
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'bot_token': None,
                'chat_id': None,
                'enabled': False
            }
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
    
    def _initialize_bot(self):
        """Initialize bot and application."""
        try:
            token = self.config.get('bot_token')
            if not token:
                self.logger.error("Bot token not configured")
                self.enabled = False
                return
            
            self.bot = Bot(token=token)
            self.application = Application.builder().token(token).build()
            
            # Register command handlers
            if self.config.get('commands_enabled', True):
                self.application.add_handler(CommandHandler("start", self._handle_start))
                self.application.add_handler(CommandHandler("stop", self._handle_stop))
                self.application.add_handler(CommandHandler("status", self._handle_status))
                self.application.add_handler(CommandHandler("report", self._handle_report))
                self.application.add_handler(CommandHandler("help", self._handle_help))
                self.application.add_handler(CommandHandler("menu", self._handle_menu))
                
                # Register button callback handlers
                self.application.add_handler(CallbackQueryHandler(self._handle_button_callback))
            
            self.logger.info("✅ Telegram bot initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            self.enabled = False
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self._is_authorized(update):
            return
        
        if self.on_start_command:
            result = self.on_start_command()
            await update.message.reply_text(f"▶️ Trading started\n{result}")
        else:
            await update.message.reply_text("▶️ Start command received")
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        if not self._is_authorized(update):
            return
        
        if self.on_stop_command:
            result = self.on_stop_command()
            await update.message.reply_text(f"⏸️ Trading stopped\n{result}")
        else:
            await update.message.reply_text("⏸️ Stop command received")
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._is_authorized(update):
            return
        
        if self.on_status_command:
            status = self.on_status_command()
            await update.message.reply_text(f"📊 System Status:\n\n{status}")
        else:
            await update.message.reply_text("📊 Status: System running")
    
    async def _handle_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command."""
        if not self._is_authorized(update):
            return
        
        if self.on_report_command:
            report = self.on_report_command()
            await update.message.reply_text(f"📈 Trading Report:\n\n{report}")
        else:
            await update.message.reply_text("📈 Report generation not configured")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update):
            return
        
        help_text = """
🤖 SMC Trading Bot Commands:

/menu - Show control panel with buttons 🎛️
/start - Start trading system
/stop - Stop trading system
/status - Get current system status
/report - Get trading performance report
/help - Show this help message

📊 Notifications enabled for:
• Trade openings/closings
• System status changes
• Daily reports
• Error alerts
"""
        await update.message.reply_text(help_text)
    
    async def _handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - show button panel."""
        if not self._is_authorized(update):
            self.logger.warning("Unauthorized /menu command")
            return

        self.logger.debug("_handle_menu invoked")

        keyboard = self._create_main_menu_keyboard()
        msg = "🎛️ Control Panel\nChoose an action:"

        # Try sending via reply to the incoming message first (more reliable in some PTB versions)
        try:
            if hasattr(update, 'message') and update.message is not None:
                await update.message.reply_text(msg, reply_markup=keyboard)
                chat_id = update.effective_chat.id if update.effective_chat else None
                self.logger.info(f"/menu: replied with control panel to chat_id={chat_id} using update.message.reply_text")
                return
        except Exception as e:
            self.logger.debug(f"/menu: reply_text fallback failed: {e}")

        # Fallback: send via context.bot
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            try:
                await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=keyboard)
                self.logger.info(f"/menu: sent control panel with buttons to chat_id={chat_id} using context.bot.send_message")
                return
            except Exception as e:
                self.logger.error(f"/menu: failed to send control panel: {e}")

        self.logger.warning("/menu: no chat_id available in update, cannot send buttons")
    
    def _create_main_menu_keyboard(self):
        """Create main menu keyboard with buttons."""
        keyboard = [
            [
                InlineKeyboardButton("▶️ Start Trading", callback_data="cmd_start"),
                InlineKeyboardButton("⏸️ Stop Trading", callback_data="cmd_stop")
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="cmd_status"),
                InlineKeyboardButton("📈 Report", callback_data="cmd_report")
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="cmd_help"),
                InlineKeyboardButton("🔄 Refresh", callback_data="cmd_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button press callbacks."""
        query = update.callback_query
        if query is None:
            self.logger.warning("_handle_button_callback called without callback_query")
            return

        self.logger.debug(f"_handle_button_callback invoked, data={getattr(query, 'data', None)}")
        await query.answer()  # Acknowledge button press
        
        if not self._is_authorized_callback(query):
            return
        
        callback_data = query.data
        
        # Execute commands based on button pressed
        if callback_data == "cmd_start":
            if self.on_start_command:
                result = self.on_start_command()
                await query.edit_message_text(f"▶️ **Trading Started**\n\n{result}", parse_mode='Markdown')
            else:
                await query.edit_message_text("▶️ Trading started")
        
        elif callback_data == "cmd_stop":
            if self.on_stop_command:
                result = self.on_stop_command()
                await query.edit_message_text(f"⏸️ **Trading Stopped**\n\n{result}", parse_mode='Markdown')
            else:
                await query.edit_message_text("⏸️ Trading stopped")
        
        elif callback_data == "cmd_status":
            if self.on_status_command:
                status = self.on_status_command()
                keyboard = self._create_main_menu_keyboard()
                await query.edit_message_text(
                    f"📊 **System Status**\n\n{status}",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("📊 Status: System running")
        
        elif callback_data == "cmd_report":
            if self.on_report_command:
                report = self.on_report_command()
                keyboard = self._create_main_menu_keyboard()
                await query.edit_message_text(
                    f"📈 **Daily Report**\n\n{report}",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("📈 No report available")
        
        elif callback_data == "cmd_help":
            help_text = """
🤖 **SMC Trading Bot**

Use buttons to control the bot:
• **Start Trading** - Begin automated trading
• **Stop Trading** - Pause all trading activity
• **Status** - View current system status
• **Report** - Get daily performance report
• **Refresh** - Reload control panel

You will receive notifications for:
📊 Trade openings/closings
⚙️ System status changes
📈 Daily reports
⚠️ Error alerts
"""
            keyboard = self._create_main_menu_keyboard()
            await query.edit_message_text(help_text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif callback_data == "cmd_menu":
            keyboard = self._create_main_menu_keyboard()
            await query.edit_message_text(
                "🎛️ **Control Panel**\nChoose an action:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
    
    def _is_authorized_callback(self, query) -> bool:
        """Check if callback query is from authorized user."""
        chat_id = self.config.get('chat_id')
        if chat_id is None:
            return False
        
        user_chat_id = query.message.chat_id
        if str(user_chat_id) != str(chat_id):
            self.logger.warning(f"Unauthorized callback from chat_id: {user_chat_id}")
            return False
        
        return True
    
    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized."""
        chat_id = self.config.get('chat_id')
        if chat_id is None:
            return False
        
        user_chat_id = update.effective_chat.id
        if str(user_chat_id) != str(chat_id):
            self.logger.warning(f"Unauthorized access attempt from chat_id: {user_chat_id}")
            return False
        
        return True
    
    async def send_message(self, message: str, parse_mode: str = None) -> bool:
        """
        Send message to configured chat.
        
        Args:
            message: Message text
            parse_mode: 'Markdown' or 'HTML' (optional)
        
        Returns:
            True if sent successfully
        """
        if not self.enabled or not self.bot:
            return False
        
        try:
            chat_id = self.config.get('chat_id')
            if not chat_id:
                self.logger.error("Chat ID not configured")
                return False
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def send_notification(self, message: str, notification_type: str = None) -> bool:
        """
        Send notification (sync wrapper for async send_message).
        
        Args:
            message: Notification message
            notification_type: Type of notification (trade_opened, trade_closed, etc.)
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Check if this notification type is enabled
        if notification_type:
            notifications = self.config.get('notifications', {})
            if not notifications.get(notification_type, True):
                return False
        
        # Run async send in new event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_message(message))
    
    def notify_trade_opened(self, symbol: str, direction: str, entry: float, 
                           sl: float, tp: float, volume: float):
        """Send notification when trade is opened."""
        message = f"""
🔵 TRADE OPENED

Symbol: {symbol}
Direction: {direction}
Entry: {entry:.5f}
Stop Loss: {sl:.5f}
Take Profit: {tp:.5f}
Volume: {volume:.2f} lots

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_notification(message, 'trade_opened')
    
    def notify_trade_closed(self, symbol: str, direction: str, entry: float,
                           exit: float, profit: float, pips: float):
        """Send notification when trade is closed."""
        emoji = "🟢" if profit > 0 else "🔴"
        message = f"""
{emoji} TRADE CLOSED

Symbol: {symbol}
Direction: {direction}
Entry: {entry:.5f}
Exit: {exit:.5f}
Profit: ${profit:.2f} ({pips:+.1f} pips)

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_notification(message, 'trade_closed')
    
    def notify_system_status(self, status: str, details: str = ""):
        """Send system status notification."""
        message = f"""
⚙️ SYSTEM STATUS

Status: {status}
{details}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_notification(message, 'system_status')
    
    def notify_error(self, error_message: str):
        """Send error notification."""
        message = f"""
❌ ERROR

{error_message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_notification(message, 'errors')
    
    def notify_daily_report(self, total_trades: int, winning_trades: int,
                           total_profit: float, balance: float):
        """Send daily performance report."""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        message = f"""
📊 DAILY REPORT

Total Trades: {total_trades}
Winning Trades: {winning_trades} ({win_rate:.1f}%)
Total Profit: ${total_profit:+.2f}
Balance: ${balance:.2f}

Date: {datetime.now().strftime('%Y-%m-%d')}
"""
        self.send_notification(message, 'daily_report')
    
    def start_polling(self):
        """Start bot polling (for receiving commands)."""
        if not self.enabled or not self.application:
            return
        
        try:
            self.logger.info("🚀 Starting Telegram bot polling...")
            self.is_polling = True
            self.application.run_polling()
        except Exception as e:
            self.logger.error(f"Failed to start polling: {e}")
            self.is_polling = False
    
    def start_polling_async(self):
        """Start bot polling in background thread."""
        if not self.enabled or not self.application or self.is_polling:
            return
        
        self.polling_thread = threading.Thread(target=self.start_polling, daemon=True)
        self.polling_thread.start()
        self.logger.info("✅ Telegram bot polling started in background")
    
    def stop_polling(self):
        """Stop bot polling."""
        if self.application and self.is_polling:
            self.logger.info("⏸️ Stopping Telegram bot polling...")
            self.application.stop()
            self.is_polling = False
    
    def update_config(self, **kwargs):
        """Update configuration."""
        self.config.update(kwargs)
        self._save_config()
        
        # Reinitialize if enabled status changed
        if 'enabled' in kwargs or 'chat_id' in kwargs:
            self.enabled = self.config.get('enabled', False) and self.config.get('chat_id') is not None
            if self.enabled and not self.bot:
                self._initialize_bot()


# Example usage
if __name__ == "__main__":
    # Create bot manager
    bot = TelegramBotManager()
    
    if not bot.enabled:
        print("⚠️ Bot not enabled. Configure chat_id in config.json")
    else:
        # Send test notification
        bot.notify_system_status("System started", "All systems operational")
        
        # Start polling for commands
        bot.start_polling()

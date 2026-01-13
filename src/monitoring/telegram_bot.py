"""
Telegram Bot с интерактивными кнопками

Бот отвечает на запросы через кнопки вместо команд:
- 📊 Отчёт - показывает текущую статистику
- ✅ Статус работы - показывает работает ли бот
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.core.logger import logger


class TelegramBotWithButtons:
    """Telegram бот с кнопками для управления"""
    
    def __init__(self, token: str, bot_manager=None):
        """
        Args:
            token: Telegram Bot Token от @BotFather
            bot_manager: Ссылка на BotManager для получения статистики
        """
        self.token = token
        self.bot_manager = bot_manager
        self.application = None
        self.stats_file = Path("data/bot_stats.json")
        
        # Клавиатура с кнопками
        self.keyboard = [
            [KeyboardButton("📊 Отчёт"), KeyboardButton("✅ Статус работы")],
        ]
        self.reply_markup = ReplyKeyboardMarkup(
            self.keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        logger.info("Telegram бот инициализирован с кнопками")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        await update.message.reply_text(
            "🤖 <b>BAZA Trading Bot</b>\n\n"
            "Выберите действие из меню ниже:",
            parse_mode="HTML",
            reply_markup=self.reply_markup
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия кнопок"""
        text = update.message.text
        
        if text == "📊 Отчёт":
            await self.send_report(update)
        elif text == "✅ Статус работы":
            await self.send_status(update)
        else:
            # Отправляем клавиатуру с любым ответом
            await update.message.reply_text(
                "🤖 <b>BAZA Trading Bot</b>\n\n"
                "Используйте кнопки меню для взаимодействия с ботом:",
                parse_mode="HTML",
                reply_markup=self.reply_markup
            )
    
    async def send_report(self, update: Update):
        """Отправка отчёта по статистике"""
        try:
            # Читаем статистику из файла
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                stats = {}
            
            # Получаем данные
            balance = stats.get('balance', 0)
            total_profit = stats.get('total_profit', 0)
            today_profit = stats.get('today_profit', 0)
            total_trades = stats.get('total_trades', 0)
            today_trades = stats.get('today_trades', 0)
            winning_trades = stats.get('winning_trades', 0)
            losing_trades = stats.get('losing_trades', 0)
            winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Формируем отчёт
            report = f"""
📊 <b>Отчёт по торговле</b>
━━━━━━━━━━━━━━━━━━━━

💰 <b>Баланс:</b> ${balance:.2f}
📈 <b>Всего прибыль:</b> ${total_profit:.2f}
💵 <b>Сегодня прибыль:</b> ${today_profit:.2f}

📊 <b>Сделки всего:</b> {total_trades}
🔄 <b>Сегодня сделок:</b> {today_trades}

✅ <b>Прибыльных:</b> {winning_trades}
❌ <b>Убыточных:</b> {losing_trades}
🎯 <b>Winrate:</b> {winrate:.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await update.message.reply_text(
                report.strip(),
                parse_mode="HTML",
                reply_markup=self.reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки отчёта: {e}")
            await update.message.reply_text(
                "❌ Ошибка получения статистики",
                reply_markup=self.reply_markup
            )
    
    async def send_status(self, update: Update):
        """Отправка статуса работы бота"""
        try:
            # Проверяем работает ли бот
            is_running = False
            status_text = "🛑 Остановлен"
            
            if self.bot_manager:
                is_running = getattr(self.bot_manager, 'is_running', False)
                status_text = "✅ Работает" if is_running else "🛑 Остановлен"
            
            # Читаем статистику для дополнительной информации
            stats = {}
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            mode = stats.get('mode', 'Unknown')
            last_activity = stats.get('last_activity', 'Нет данных')
            
            status_report = f"""
✅ <b>Статус работы</b>
━━━━━━━━━━━━━━━━━━━━

🤖 <b>Бот:</b> {status_text}
🔄 <b>Режим:</b> {mode}

📊 <b>Открытых позиций:</b> {stats.get('open_positions', 0)}
🎯 <b>Сделок сегодня:</b> {stats.get('today_trades', 0)}

⏰ <b>Последняя активность:</b>
{last_activity}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await update.message.reply_text(
                status_report.strip(),
                parse_mode="HTML",
                reply_markup=self.reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки статуса: {e}")
            await update.message.reply_text(
                "❌ Ошибка получения статуса",
                reply_markup=self.reply_markup
            )
    
    # Метод run() больше не нужен, перенесён в start_polling()
    
    def start_polling(self):
        """Запуск бота в отдельном потоке"""
        # Создаём новый event loop для потока сразу
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Создаём приложение
            self.application = Application.builder().token(self.token).build()
            
            # Добавляем обработчики
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Запускаем polling
            logger.info("🤖 Telegram бот запущен с кнопками")
            loop.run_until_complete(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
            
        except Exception as e:
            logger.error(f"Ошибка polling Telegram бота: {e}")
        finally:
            loop.close()

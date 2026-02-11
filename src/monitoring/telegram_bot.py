"""
Telegram Bot с интерактивными кнопками

Бот отвечает на запросы через кнопки вместо команд:
- 📊 Отчёт - показывает текущую статистику
- ✅ Статус работы - показывает работает ли бот
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
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
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия inline кнопок (callback query)"""
        query = update.callback_query
        await query.answer()  # Подтверждаем получение callback
        
        # Обработка кнопки "Удалить сигнал"
        if query.data.startswith("delete_signal_"):
            signal_id = query.data.replace("delete_signal_", "")
            
            # Удаляем сигнал из SignalManager
            try:
                # Используем self.bot_manager вместо создания нового экземпляра
                if not self.bot_manager:
                    logger.error("[Telegram] BotManager not available")
                    await query.message.edit_text(
                        "❌ Bot manager not initialized",
                        parse_mode="HTML"
                    )
                    return
                
                # SignalManager находится в LiveTrader
                if not hasattr(self.bot_manager, 'live_trader') or not self.bot_manager.live_trader:
                    logger.error("[Telegram] LiveTrader not available")
                    await query.message.edit_text(
                        "❌ LiveTrader not initialized",
                        parse_mode="HTML"
                    )
                    return
                
                if not hasattr(self.bot_manager.live_trader, 'ai_signal_manager') or not self.bot_manager.live_trader.ai_signal_manager:
                    logger.error("[Telegram] AISignalManager not available")
                    await query.message.edit_text(
                        "❌ AI Signal manager not initialized",
                        parse_mode="HTML"
                    )
                    return
                
                if self.bot_manager.live_trader.ai_signal_manager.cancel_signal(signal_id):
                    logger.info(f"[Telegram] Signal {signal_id} cancelled from SignalManager")
                    
                    # Удаляем сообщение
                    await query.message.delete()
                    logger.info(f"[Telegram] Signal message deleted: {signal_id}")
                else:
                    logger.warning(f"[Telegram] Signal {signal_id} not found in SignalManager")
                    await query.message.edit_text(
                        "⚠️ Сигнал не найден или уже удалён",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"[Telegram] Failed to delete signal: {e}", exc_info=True)
                await query.message.edit_text(
                    f"❌ Ошибка при удалении сигнала: {str(e)}",
                    parse_mode="HTML"
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
            # Создаём приложение с увеличенным timeout
            request = HTTPXRequest(connection_pool_size=8, read_timeout=60, write_timeout=60, connect_timeout=60)
            self.application = Application.builder().token(self.token).request(request).build()
            
            # Добавляем обработчики
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))  # Обработчик inline кнопок
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Очищаем старые команды и устанавливаем новые (только /start)
            logger.info("🧹 Очистка старых команд Telegram бота...")
            loop.run_until_complete(self._setup_bot_commands())
            
            # Запускаем polling
            logger.info("🤖 Telegram бот запущен с кнопками")
            loop.run_until_complete(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
            
        except Exception as e:
            logger.error(f"Ошибка polling Telegram бота: {e}")
        finally:
            loop.close()
    
    async def _setup_bot_commands(self):
        """Настройка команд бота (удаление старых + установка новых) с retry"""
        from telegram import BotCommand
        retry_attempts = 3
        retry_delay = 2
        
        for attempt in range(1, retry_attempts + 1):
            try:
                # Удалить все старые команды
                await self.application.bot.delete_my_commands()
                logger.info("✅ Старые команды удалены")
                
                # Установить только /start (остальное через кнопки)
                commands = [
                    BotCommand("start", "🤖 Запустить бота и показать меню")
                ]
                await self.application.bot.set_my_commands(commands)
                logger.info(f"✅ Установлены новые команды: {[cmd.command for cmd in commands]}")
                return  # Успех - выходим
                
            except Exception as e:
                if attempt < retry_attempts:
                    logger.warning(f"⚠️ Попытка {attempt}/{retry_attempts} установки команд: {e}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Не удалось установить команды после {retry_attempts} попыток: {e}")
                    logger.info("ℹ️ Бот продолжит работу без команд (кнопки будут работать)")

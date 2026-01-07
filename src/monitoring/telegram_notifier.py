"""
Telegram бот для отправки уведомлений о торговле

VERSION 2.0: Разделение уведомлений по режимам торговли
- Strategy + AI: стандартные уведомления
- Pure AI: детальные объяснения от GPT
"""

import requests
from typing import Optional, Dict, Any
from datetime import datetime
from src.core.logger import logger


class TelegramNotifier:
    """Отправка уведомлений в Telegram v2.0"""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Args:
            token: Telegram Bot Token от @BotFather
            chat_id: ID чата для отправки сообщений
        """
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
        self.last_report_time = None  # Для отчетов каждые 3 часа
        
        if not self.enabled:
            logger.warning("Telegram уведомления отключены (нет токена или chat_id)")
        else:
            logger.info("Telegram уведомления активированы")
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Отправка текстового сообщения
        
        Args:
            text: Текст сообщения (поддерживает HTML разметку)
            parse_mode: Режим парсинга (HTML или Markdown)
            
        Returns:
            True если успешно отправлено
        """
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Telegram сообщение отправлено: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram: {e}")
            return False
    
    def send_trade_opened(self, symbol: str, direction: str, lot: float, 
                          entry: float, sl: float, tp: float, 
                          mode: str = "strategy", reasoning: str = None,
                          confidence: float = None) -> bool:
        """
        Уведомление об открытии сделки
        
        Args:
            mode: "strategy" или "pure_ai"
            reasoning: Объяснение от GPT (для pure_ai режима)
            confidence: Уверенность GPT в % (для pure_ai режима)
        """
        if mode == "pure_ai":
            # Pure AI режим - детальное сообщение с объяснением GPT
            text = f"""
🤖 <b>PURE AI: Открыта сделка</b>

📊 <b>{symbol}</b> | {direction.upper()}
💰 Объем: <b>{lot} лот</b>
🎯 Уверенность GPT: <b>{confidence:.0f}%</b>

💵 Вход: <code>{entry}</code>
🛑 Stop Loss: <code>{sl}</code> (риск: {abs(entry-sl):.2f})
🎯 Take Profit: <code>{tp}</code> (потенциал: {abs(tp-entry):.2f})
📊 R:R: <b>1:{abs(tp-entry)/abs(entry-sl):.2f}</b>

🧠 <b>Анализ GPT:</b>
<i>{reasoning or 'Нет объяснения'}</i>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Режим: <b>Pure AI Trading</b>
"""
        else:
            # Strategy + AI режим - стандартное сообщение
            text = f"""
🚀 <b>Открыта сделка</b>

📊 Инструмент: <b>{symbol}</b>
📈 Направление: <b>{direction}</b>
💰 Объем: <b>{lot} лот</b>

💵 Вход: <b>{entry}</b>
🛑 Stop Loss: <b>{sl}</b>
🎯 Take Profit: <b>{tp}</b>

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Режим: <b>Strategy + AI</b>
"""
        return self.send_message(text.strip())
    
    def send_trade_closed(self, symbol: str, direction: str, profit: float, 
                          pips: float, duration: str, mode: str = "strategy",
                          result_reason: str = None) -> bool:
        """
        Уведомление о закрытии сделки
        
        Args:
            mode: "strategy" или "pure_ai"
            result_reason: Причина закрытия (TP/SL/Manual)
        """
        emoji = "✅" if profit > 0 else "❌"
        profit_emoji = "💰" if profit > 0 else "💸"
        
        if mode == "pure_ai":
            # Pure AI режим - детальное сообщение
            text = f"""
{emoji} <b>PURE AI: Сделка закрыта</b>

📊 <b>{symbol}</b> | {direction.upper()}

{profit_emoji} Профит: <b>${profit:.2f}</b> {"🔥" if profit > 0 else ""}
📏 Пипсы: <b>{pips:.1f}</b>
⏱️ Длительность: <b>{duration}</b>
🎯 Результат: <b>{result_reason or 'Закрыто'}</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Режим: <b>Pure AI Trading</b>
"""
        else:
            # Strategy + AI режим - стандартное сообщение
            text = f"""
{emoji} <b>Сделка закрыта</b>

📊 Инструмент: <b>{symbol}</b>
📈 Направление: <b>{direction}</b>

💰 Профит: <b>${profit:.2f}</b>
📏 Пипсы: <b>{pips:.1f}</b>
⏱️ Длительность: <b>{duration}</b>

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Режим: <b>Strategy + AI</b>
"""
        return self.send_message(text.strip())
    
    def send_daily_report(self, mode: str = "strategy", stats: Dict[str, Any] = None) -> bool:
        """
        Ежедневный отчет
        
        Args:
            mode: "strategy" или "pure_ai"
            stats: Статистика работы
        """
        if mode == "pure_ai":
            text = f"""
📊 <b>Pure AI: Дневной отчет</b>

🤖 <b>Автономная торговля GPT-4</b>
━━━━━━━━━━━━━━━━━━━━

💰 Баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>

📊 Сделок: <b>{stats.get('total_trades', 0)}</b>
✅ Прибыльных: <b>{stats.get('winning_trades', 0)}</b>
❌ Убыточных: <b>{stats.get('losing_trades', 0)}</b>

🎯 Winrate: <b>{stats.get('winrate', 0):.1f}%</b>
📈 ROI: <b>{stats.get('roi', 0):.2f}%</b>

🔬 GPT анализов: <b>{stats.get('total_analyses', 0)}</b>
📡 Сигналов: <b>{stats.get('total_signals', 0)}</b>
💡 Средний конфиденс: <b>{stats.get('avg_confidence', 0):.1f}%</b>

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        else:
            text = f"""
📊 <b>Дневной отчет</b>

📈 <b>Strategy + AI</b>
━━━━━━━━━━━━━━━━━━━━

💰 Баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>

📊 Сделок: <b>{stats.get('total_trades', 0)}</b>
✅ Прибыльных: <b>{stats.get('winning_trades', 0)}</b>
❌ Убыточных: <b>{stats.get('losing_trades', 0)}</b>

🎯 Winrate: <b>{stats.get('winrate', 0):.1f}%</b>
📈 ROI: <b>{stats.get('roi', 0):.2f}%</b>

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        return self.send_message(text.strip())
    
    def send_alert(self, alert_type: str, message: str, level: str = "WARNING") -> bool:
        """
        Отправка алерта
        
        Args:
            alert_type: Тип алерта (RISK, ERROR, INFO)
            message: Текст сообщения
            level: Уровень критичности
        """
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "🚨",
            "CRITICAL": "🔥"
        }
        
        emoji = emoji_map.get(level, "⚠️")
        text = f"""
{emoji} <b>{alert_type}</b>

{message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())
    
    def send_startup(self, mode: str = "strategy", instruments: list = None, config: dict = None) -> bool:
        """
        Уведомление о запуске бота
        
        Args:
            mode: "strategy" или "pure_ai"
            instruments: Список инструментов
            config: Конфигурация режима
        """
        if mode == "pure_ai":
            text = f"""
🚀 <b>BAZA BOT: Pure AI Trading запущен</b>

🤖 <b>Режим:</b> Только GPT-4 анализ
⏰ <b>Интервал:</b> Каждые 2 часа
📊 <b>Таймфрейм:</b> 15 минут
💹 <b>Инструменты:</b> {', '.join(instruments or ['XAUUSD', 'EURUSD'])}

🎯 <b>Конфиденс:</b> {config.get('min_confidence', 70)}% минимум
📉 <b>Лимит сделок:</b> {config.get('max_trades_per_day', 5)}/день
🔒 <b>Кулдаун:</b> {config.get('symbol_cooldown_hours', 2)} часа

✅ Система готова к автономной торговле!
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""" if config else f"""
🚀 <b>BAZA BOT: Pure AI Trading запущен</b>

🤖 Режим автономной торговли активирован
📊 Анализ каждые 2 часа на 15M таймфрейме
💹 {', '.join(instruments or ['XAUUSD', 'EURUSD'])}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        else:
            text = f"""
🚀 <b>BAZA BOT запущен</b>

📈 <b>Режим:</b> Strategy + AI
🎯 <b>Стратегия:</b> {config.get('strategy', 'Multi-Strategy') if config else 'Multi-Strategy'} 
📊 <b>Инструменты:</b> {', '.join(instruments or ['Multiple'])}

✅ Система готова к торговле!
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())
    
    def send_shutdown(self, mode: str = "strategy", stats: Optional[Dict[str, Any]] = None) -> bool:
        """
        Уведомление об остановке бота
        
        Args:
            mode: "strategy" или "pure_ai"
            stats: Статистика работы
        """
        if mode == "pure_ai":
            text = "🛑 <b>BAZA BOT: Pure AI Trading остановлен</b>\n\n"
            
            if stats:
                text += f"""
🤖 <b>Итоговая статистика Pure AI:</b>
━━━━━━━━━━━━━━━━━━━━

💰 Финальный баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>
📊 Сделок: <b>{stats.get('total_trades', 0)}</b>
✅ Успешных: <b>{stats.get('winning_trades', 0)}</b>
❌ Убыточных: <b>{stats.get('losing_trades', 0)}</b>
🎯 Винрейт: <b>{stats.get('winrate', 0):.1f}%</b>

🔬 GPT анализов: <b>{stats.get('total_analyses', 0)}</b>
📡 Сигналов: <b>{stats.get('total_signals', 0)}</b>
"""
        else:
            text = "🛑 <b>BAZA BOT остановлен</b>\n\n"
            
            if stats:
                text += f"""
📊 <b>Итоговая статистика:</b>
━━━━━━━━━━━━━━━━━━━━

💰 Финальный баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>
📊 Сделок: <b>{stats.get('total_trades', 0)}</b>
✅ Успешных: <b>{stats.get('winning_trades', 0)}</b>
❌ Убыточных: <b>{stats.get('losing_trades', 0)}</b>
"""
        
        text += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(text.strip())
    
    def send_periodic_report(self, mode: str = "strategy", stats: Dict[str, Any] = None) -> bool:
        """
        Периодический отчет (каждые 3 часа)
        
        Args:
            mode: "strategy" или "pure_ai"
            stats: Текущая статистика
        """
        current_time = datetime.now()
        
        # Проверка на частоту отправки (не чаще раза в 3 часа)
        if self.last_report_time:
            time_diff = (current_time - self.last_report_time).total_seconds() / 3600
            if time_diff < 3:
                return False
        
        if mode == "pure_ai":
            text = f"""
⏰ <b>Pure AI: Периодический отчет</b>

🤖 <b>Статус системы</b>
━━━━━━━━━━━━━━━━━━━━

📊 <b>Сегодня:</b>
💰 Баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 P&L: <b>${stats.get('daily_profit', 0):.2f}</b>
📊 Сделок: <b>{stats.get('trades_today', 0)}/{stats.get('max_trades', 5)}</b>

🔬 <b>AI активность:</b>
📡 Анализов: <b>{stats.get('analyses_today', 0)}</b>
💡 Сигналов: <b>{stats.get('signals_today', 0)}</b>
⏱️ Следующий анализ: <b>{stats.get('next_analysis', 'Скоро')}</b>

🎯 Средний конфиденс: <b>{stats.get('avg_confidence', 0):.1f}%</b>

⏰ {current_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        else:
            text = f"""
⏰ <b>Периодический отчет</b>

📈 <b>Статус торговли</b>
━━━━━━━━━━━━━━━━━━━━

📊 <b>Сегодня:</b>
💰 Баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 P&L: <b>${stats.get('daily_profit', 0):.2f}</b>
📊 Сделок: <b>{stats.get('trades_today', 0)}</b>

✅ Открытых позиций: <b>{stats.get('open_positions', 0)}</b>
🎯 Winrate: <b>{stats.get('winrate', 0):.1f}%</b>

⏰ {current_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.last_report_time = current_time
        return self.send_message(text.strip())
    
    def send_ai_analysis_update(self, symbol: str, confidence: float, 
                                direction: str, reasoning: str, 
                                next_analysis_time: str = None) -> bool:
        """
        Обновление об анализе GPT (для Pure AI режима)
        
        Args:
            symbol: Инструмент
            confidence: Уверенность GPT
            direction: BUY/SELL/HOLD
            reasoning: Объяснение от GPT
            next_analysis_time: Время следующего анализа
        """
        emoji_map = {
            "BUY": "📈",
            "SELL": "📉",
            "HOLD": "⏸️",
            "NEUTRAL": "➖"
        }
        
        emoji = emoji_map.get(direction.upper(), "🔍")
        confidence_emoji = "🔥" if confidence >= 80 else "✅" if confidence >= 70 else "⚠️"
        
        text = f"""
🔬 <b>Pure AI: Анализ завершен</b>

📊 <b>{symbol}</b>
━━━━━━━━━━━━━━━━━━━━

{emoji} <b>Решение:</b> {direction.upper()}
{confidence_emoji} <b>Конфиденс:</b> {confidence:.1f}%

💭 <b>Объяснение GPT:</b>
{reasoning[:300]}{'...' if len(reasoning) > 300 else ''}

⏰ Время: {datetime.now().strftime('%H:%M:%S')}
"""
        
        if next_analysis_time:
            text += f"🔄 Следующий анализ: <b>{next_analysis_time}</b>\n"
        
        return self.send_message(text.strip())

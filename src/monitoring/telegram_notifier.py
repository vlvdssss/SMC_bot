"""
Telegram бот для отправки уведомлений о торговле
"""

import requests
from typing import Optional, Dict, Any
from datetime import datetime
from src.core.logger import logger


class TelegramNotifier:
    """Отправка уведомлений в Telegram"""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Args:
            token: Telegram Bot Token от @BotFather
            chat_id: ID чата для отправки сообщений
        """
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
        
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
                          entry: float, sl: float, tp: float) -> bool:
        """Уведомление об открытии сделки"""
        text = f"""
🚀 <b>Открыта сделка</b>

📊 Инструмент: <b>{symbol}</b>
📈 Направление: <b>{direction}</b>
💰 Объем: <b>{lot} лот</b>

💵 Вход: <b>{entry}</b>
🛑 Stop Loss: <b>{sl}</b>
🎯 Take Profit: <b>{tp}</b>

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())
    
    def send_trade_closed(self, symbol: str, direction: str, profit: float, 
                          pips: float, duration: str) -> bool:
        """Уведомление о закрытии сделки"""
        emoji = "✅" if profit > 0 else "❌"
        text = f"""
{emoji} <b>Сделка закрыта</b>

📊 Инструмент: <b>{symbol}</b>
📈 Направление: <b>{direction}</b>

💰 Профит: <b>${profit:.2f}</b>
📏 Пипсы: <b>{pips:.1f}</b>
⏱️ Длительность: <b>{duration}</b>

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())
    
    def send_daily_report(self, stats: Dict[str, Any]) -> bool:
        """Ежедневный отчет"""
        text = f"""
📊 <b>Дневной отчет</b>

💰 Баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>

📊 Сделки: <b>{stats.get('total_trades', 0)}</b>
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
    
    def send_startup(self, mode: str, instruments: list) -> bool:
        """Уведомление о запуске бота"""
        text = f"""
🤖 <b>BAZA Bot запущен</b>

🔧 Режим: <b>{mode}</b>
📊 Инструменты: <b>{', '.join(instruments)}</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())
    
    def send_shutdown(self, stats: Optional[Dict[str, Any]] = None) -> bool:
        """Уведомление об остановке бота"""
        text = "🛑 <b>BAZA Bot остановлен</b>\n\n"
        
        if stats:
            text += f"""
💰 Финальный баланс: <b>${stats.get('balance', 0):.2f}</b>
📈 Профит: <b>${stats.get('profit', 0):.2f}</b>
📊 Сделок: <b>{stats.get('total_trades', 0)}</b>
"""
        
        text += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(text.strip())

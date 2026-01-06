"""
Email уведомления для критических событий
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
from src.core.logger import logger


class EmailNotifier:
    """Отправка email уведомлений"""
    
    def __init__(self, smtp_server: Optional[str] = None, smtp_port: int = 587,
                 email_from: Optional[str] = None, email_password: Optional[str] = None,
                 email_to: Optional[List[str]] = None):
        """
        Args:
            smtp_server: SMTP сервер (например, smtp.gmail.com)
            smtp_port: Порт SMTP (обычно 587 для TLS)
            email_from: Email отправителя
            email_password: Пароль или App Password
            email_to: Список email получателей
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = email_to or []
        
        self.enabled = bool(smtp_server and email_from and email_password and email_to)
        
        if not self.enabled:
            logger.warning("Email уведомления отключены (нет конфигурации)")
        else:
            logger.info(f"Email уведомления активированы для {len(self.email_to)} получателей")
    
    def send_email(self, subject: str, body: str, html: bool = False) -> bool:
        """
        Отправка email
        
        Args:
            subject: Тема письма
            body: Текст письма
            html: True если body содержит HTML
            
        Returns:
            True если успешно отправлено
        """
        if not self.enabled:
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = ', '.join(self.email_to)
            
            # Добавление текста
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Отправка
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email отправлен: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False
    
    def send_critical_alert(self, alert_type: str, message: str) -> bool:
        """Отправка критического алерта"""
        subject = f"🚨 BAZA CRITICAL: {alert_type}"
        
        body = f"""
КРИТИЧЕСКИЙ АЛЕРТ ОТ BAZA TRADING BOT

Тип: {alert_type}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Сообщение:
{message}

---
Требуется немедленное внимание!
"""
        return self.send_email(subject, body)
    
    def send_daily_report(self, stats: dict) -> bool:
        """Отправка ежедневного отчета"""
        subject = f"📊 BAZA Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
ЕЖЕДНЕВНЫЙ ОТЧЕТ BAZA TRADING BOT
{datetime.now().strftime('%Y-%m-%d')}

БАЛАНС И ПРИБЫЛЬ
• Текущий баланс: ${stats.get('balance', 0):.2f}
• Прибыль за день: ${stats.get('profit', 0):.2f}
• ROI: {stats.get('roi', 0):.2f}%

СДЕЛКИ
• Всего сделок: {stats.get('total_trades', 0)}
• Прибыльных: {stats.get('winning_trades', 0)}
• Убыточных: {stats.get('losing_trades', 0)}
• Winrate: {stats.get('winrate', 0):.1f}%

РИСК-МЕНЕДЖМЕНТ
• Max Drawdown: {stats.get('max_drawdown', 0):.2f}%
• Текущая просадка: {stats.get('current_drawdown', 0):.2f}%

---
BAZA Trading Bot
"""
        return self.send_email(subject, body)
    
    def send_drawdown_alert(self, current_dd: float, max_dd: float) -> bool:
        """Алерт о превышении drawdown"""
        subject = f"⚠️ BAZA: High Drawdown Alert ({current_dd:.1f}%)"
        
        body = f"""
АЛЕРТ: ПРЕВЫШЕН МАКСИМАЛЬНЫЙ DRAWDOWN

Текущая просадка: {current_dd:.2f}%
Лимит: {max_dd:.2f}%

Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Рекомендуется проверить торговлю и рассмотреть остановку бота.

---
BAZA Trading Bot
"""
        return self.send_email(subject, body)
    
    def send_connection_error(self, error_message: str) -> bool:
        """Алерт о проблемах с подключением"""
        subject = "🔌 BAZA: Connection Error"
        
        body = f"""
ОШИБКА ПОДКЛЮЧЕНИЯ К MT5

Сообщение об ошибке:
{error_message}

Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Бот может не торговать до восстановления подключения.

---
BAZA Trading Bot
"""
        return self.send_email(subject, body)

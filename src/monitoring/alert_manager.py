"""
Система управления алертами
Отслеживает критические события и отправляет уведомления
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from src.core.logger import logger


class AlertLevel(Enum):
    """Уровни критичности алертов"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Типы алертов"""
    DRAWDOWN = "Превышен максимальный drawdown"
    DAILY_LOSS = "Превышен дневной лимит убытков"
    POSITION_SIZE = "Слишком большой размер позиции"
    CONNECTIVITY = "Проблемы с подключением к MT5"
    STRATEGY_ERROR = "Ошибка в стратегии"
    ML_ERROR = "Ошибка ML модели"
    NEWS_HIGH_IMPACT = "Важные новости - высокий риск"
    CONSECUTIVE_LOSSES = "Серия убыточных сделок"
    LOW_MARGIN = "Низкий уровень маржи"
    WINRATE_DROP = "Резкое падение винрейта"
    BALANCE_DROP = "Резкое падение баланса"
    STALE_DATA = "Устаревшие данные"
    SPREAD_SPIKE = "Аномальный спред"
    LICENSE_EXPIRING = "Истекает лицензия"
    OPEN_POSITIONS_LIMIT = "Превышен лимит открытых позиций"


@dataclass
class Alert:
    """Структура алерта"""
    type: AlertType
    level: AlertLevel
    message: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class AlertManager:
    """Менеджер алертов"""
    
    def __init__(self):
        self.alerts_history = []
        self.alert_handlers = []
        self.thresholds = {
            'max_drawdown_pct': 20.0,
            'daily_loss_pct': 5.0,
            'max_position_size': 10.0,
            'consecutive_losses': 5,
            'min_margin_level': 200.0,
            'min_winrate_pct': 40.0,
            'balance_drop_pct': 15.0,
            'data_age_minutes': 30,
            'max_spread_pips': 50,
            'max_open_positions': 5
        }
        
        # Частота отправки одинаковых алертов
        self.alert_cooldown = timedelta(hours=1)
        self.last_alert_times = {}
        
        logger.info("AlertManager инициализирован")
    
    def add_handler(self, handler: Callable):
        """
        Добавить обработчик алертов
        
        Args:
            handler: Функция вида handler(alert: Alert) -> None
        """
        self.alert_handlers.append(handler)
        logger.info(f"Добавлен обработчик алертов: {handler.__name__}")
    
    def set_threshold(self, key: str, value: float):
        """Установить порог срабатывания алерта"""
        self.thresholds[key] = value
        logger.info(f"Установлен порог {key} = {value}")
    
    def _should_send_alert(self, alert_type: AlertType) -> bool:
        """Проверка cooldown для избежания спама"""
        last_time = self.last_alert_times.get(alert_type)
        
        if last_time is None:
            return True
        
        if datetime.now() - last_time > self.alert_cooldown:
            return True
        
        return False
    
    def trigger_alert(self, alert_type: AlertType, level: AlertLevel, 
                     message: str, data: Optional[Dict[str, Any]] = None):
        """
        Вызвать алерт
        
        Args:
            alert_type: Тип алерта
            level: Уровень критичности
            message: Сообщение
            data: Дополнительные данные
        """
        # Проверка cooldown
        if not self._should_send_alert(alert_type):
            logger.debug(f"Алерт {alert_type.value} пропущен (cooldown)")
            return
        
        alert = Alert(
            type=alert_type,
            level=level,
            message=message,
            timestamp=datetime.now(),
            data=data
        )
        
        self.alerts_history.append(alert)
        self.last_alert_times[alert_type] = datetime.now()
        
        # Логирование
        log_message = f"ALERT [{level.value}] {alert_type.value}: {message}"
        if level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif level == AlertLevel.ERROR:
            logger.error(log_message)
        elif level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Вызов обработчиков
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Ошибка в обработчике алертов {handler.__name__}: {e}")
    
    def check_drawdown(self, current_equity: float, peak_equity: float):
        """Проверка drawdown"""
        if peak_equity <= 0:
            return
        
        dd_pct = ((peak_equity - current_equity) / peak_equity) * 100
        threshold = self.thresholds['max_drawdown_pct']
        
        if dd_pct >= threshold:
            self.trigger_alert(
                AlertType.DRAWDOWN,
                AlertLevel.CRITICAL,
                f"Drawdown {dd_pct:.2f}% превысил лимит {threshold}%",
                {'current_equity': current_equity, 'peak_equity': peak_equity, 'dd_pct': dd_pct}
            )
    
    def check_daily_loss(self, daily_pnl: float, starting_balance: float):
        """Проверка дневных убытков"""
        if starting_balance <= 0:
            return
        
        loss_pct = abs(daily_pnl / starting_balance) * 100
        threshold = self.thresholds['daily_loss_pct']
        
        if daily_pnl < 0 and loss_pct >= threshold:
            self.trigger_alert(
                AlertType.DAILY_LOSS,
                AlertLevel.ERROR,
                f"Дневной убыток {loss_pct:.2f}% превысил лимит {threshold}%",
                {'daily_pnl': daily_pnl, 'starting_balance': starting_balance, 'loss_pct': loss_pct}
            )
    
    def check_position_size(self, position_lots: float):
        """Проверка размера позиции"""
        threshold = self.thresholds['max_position_size']
        
        if position_lots > threshold:
            self.trigger_alert(
                AlertType.POSITION_SIZE,
                AlertLevel.WARNING,
                f"Размер позиции {position_lots} лотов превышает лимит {threshold}",
                {'position_lots': position_lots}
            )
    
    def check_consecutive_losses(self, loss_count: int):
        """Проверка серии убытков"""
        threshold = self.thresholds['consecutive_losses']
        
        if loss_count >= threshold:
            self.trigger_alert(
                AlertType.CONSECUTIVE_LOSSES,
                AlertLevel.WARNING,
                f"Серия из {loss_count} убыточных сделок подряд",
                {'loss_count': loss_count}
            )
    
    def check_margin_level(self, margin_level: float):
        """Проверка уровня маржи"""
        threshold = self.thresholds['min_margin_level']
        
        if margin_level < threshold:
            level = AlertLevel.CRITICAL if margin_level < 150 else AlertLevel.WARNING
            self.trigger_alert(
                AlertType.LOW_MARGIN,
                level,
                f"Низкий уровень маржи: {margin_level:.2f}% (минимум {threshold}%)",
                {'margin_level': margin_level}
            )
    
    def alert_connectivity_issue(self, error_message: str):
        """Алерт о проблемах с подключением"""
        self.trigger_alert(
            AlertType.CONNECTIVITY,
            AlertLevel.ERROR,
            f"Проблема с MT5: {error_message}",
            {'error': error_message}
        )
    
    def alert_strategy_error(self, strategy_name: str, error_message: str):
        """Алерт об ошибке в стратегии"""
        self.trigger_alert(
            AlertType.STRATEGY_ERROR,
            AlertLevel.ERROR,
            f"Ошибка в стратегии {strategy_name}: {error_message}",
            {'strategy': strategy_name, 'error': error_message}
        )
    
    def alert_high_impact_news(self, news_title: str, currency: str):
        """Алерт о важных новостях"""
        self.trigger_alert(
            AlertType.NEWS_HIGH_IMPACT,
            AlertLevel.WARNING,
            f"Важные новости: {news_title} ({currency})",
            {'news': news_title, 'currency': currency}
        )
    
    def alert_ml_error(self, error_message: str):
        """Алерт об ошибке ML модели"""
        self.trigger_alert(
            AlertType.ML_ERROR,
            AlertLevel.ERROR,
            f"Ошибка ML модели: {error_message}",
            {'error': error_message}
        )
    
    def check_winrate_drop(self, current_winrate: float, min_trades: int = 20):
        """Проверка падения винрейта"""
        threshold = self.thresholds['min_winrate_pct']
        
        if current_winrate < threshold:
            self.trigger_alert(
                AlertType.WINRATE_DROP,
                AlertLevel.WARNING,
                f"Винрейт упал до {current_winrate:.1f}% (минимум {threshold}%)",
                {'winrate': current_winrate, 'min_trades': min_trades}
            )
    
    def check_balance_drop(self, starting_balance: float, current_balance: float):
        """Проверка резкого падения баланса"""
        if starting_balance <= 0:
            return
        
        drop_pct = ((starting_balance - current_balance) / starting_balance) * 100
        threshold = self.thresholds['balance_drop_pct']
        
        if drop_pct >= threshold:
            self.trigger_alert(
                AlertType.BALANCE_DROP,
                AlertLevel.CRITICAL,
                f"Баланс упал на {drop_pct:.2f}% (лимит {threshold}%)",
                {'starting_balance': starting_balance, 'current_balance': current_balance, 'drop_pct': drop_pct}
            )
    
    def check_stale_data(self, last_update_time: datetime):
        """Проверка устаревших данных"""
        threshold_minutes = self.thresholds['data_age_minutes']
        age = datetime.now() - last_update_time
        age_minutes = age.total_seconds() / 60
        
        if age_minutes > threshold_minutes:
            self.trigger_alert(
                AlertType.STALE_DATA,
                AlertLevel.WARNING,
                f"Данные не обновлялись {age_minutes:.1f} минут (лимит {threshold_minutes})",
                {'last_update': last_update_time.isoformat(), 'age_minutes': age_minutes}
            )
    
    def check_spread_spike(self, symbol: str, current_spread: float):
        """Проверка аномального спреда"""
        threshold = self.thresholds['max_spread_pips']
        
        if current_spread > threshold:
            self.trigger_alert(
                AlertType.SPREAD_SPIKE,
                AlertLevel.WARNING,
                f"Аномальный спред для {symbol}: {current_spread:.1f} пипсов (лимит {threshold})",
                {'symbol': symbol, 'spread': current_spread}
            )
    
    def check_open_positions_limit(self, open_count: int):
        """Проверка лимита открытых позиций"""
        threshold = self.thresholds['max_open_positions']
        
        if open_count >= threshold:
            self.trigger_alert(
                AlertType.OPEN_POSITIONS_LIMIT,
                AlertLevel.WARNING,
                f"Открыто {open_count} позиций (лимит {threshold})",
                {'open_positions': open_count}
            )
    
    def alert_license_expiring(self, days_left: int, email: str):
        """Алерт об истечении лицензии"""
        level = AlertLevel.CRITICAL if days_left <= 3 else AlertLevel.WARNING
        self.trigger_alert(
            AlertType.LICENSE_EXPIRING,
            level,
            f"Лицензия для {email} истекает через {days_left} дней",
            {'email': email, 'days_left': days_left}
        )
    
    def get_recent_alerts(self, hours: int = 24) -> list:
        """Получить последние алерты за N часов"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alerts_history if a.timestamp > cutoff_time]
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика по алертам"""
        recent = self.get_recent_alerts(24)
        
        return {
            'total_alerts': len(self.alerts_history),
            'last_24h': len(recent),
            'by_level': {
                level.value: len([a for a in recent if a.level == level])
                for level in AlertLevel
            },
            'by_type': {
                alert_type.value: len([a for a in recent if a.type == alert_type])
                for alert_type in AlertType
            }
        }

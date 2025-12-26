"""Market Sessions Checker - проверка торговых сессий и выходных."""

from datetime import datetime, time
from typing import Tuple, Optional
import pytz


class MarketSessionChecker:
    """Проверка доступности торговых сессий и рыночного времени."""
    
    def __init__(self):
        """Инициализация чекера сессий."""
        self.server_tz = pytz.timezone('Europe/Kiev')  # MT5 обычно использует EET (Kiev)
        
        # Торговые сессии (по времени сервера)
        self.sessions = {
            'asian': {
                'start': time(1, 0),   # 01:00 (Tokyo open)
                'end': time(10, 0),    # 10:00 (Tokyo close)
                'name': 'Asian Session'
            },
            'london': {
                'start': time(9, 0),   # 09:00 (London open)
                'end': time(17, 30),   # 17:30 (London close)
                'name': 'London Session'
            },
            'ny': {
                'start': time(15, 30), # 15:30 (NY open)
                'end': time(22, 0),    # 22:00 (NY close)
                'name': 'New York Session'
            },
            'overlap': {
                'start': time(15, 30), # 15:30 (London-NY overlap)
                'end': time(17, 30),   # 17:30 (overlap end)
                'name': 'London-NY Overlap'
            }
        }
    
    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """
        Проверка выходного дня.
        
        Args:
            dt: Дата/время для проверки (по умолчанию - текущее время сервера)
            
        Returns:
            bool: True если выходной день
        """
        if dt is None:
            dt = datetime.now(self.server_tz)
        
        # Forex закрыт в субботу и воскресенье
        weekday = dt.weekday()  # 0=Monday, 6=Sunday
        
        # Суббота весь день
        if weekday == 5:
            return True
        
        # Воскресенье до 22:00 (открытие рынка)
        if weekday == 6 and dt.time() < time(22, 0):
            return True
        
        # Пятница после 22:00 (закрытие рынка)
        if weekday == 4 and dt.time() >= time(22, 0):
            return True
        
        return False
    
    def get_current_session(self, dt: Optional[datetime] = None) -> Tuple[bool, Optional[str], str]:
        """
        Определить текущую торговую сессию.
        
        Args:
            dt: Дата/время для проверки (по умолчанию - текущее время сервера)
            
        Returns:
            Tuple[bool, Optional[str], str]: (market_open, session_name, message)
        """
        if dt is None:
            dt = datetime.now(self.server_tz)
        
        current_time = dt.time()
        weekday = dt.weekday()
        
        # Проверка выходных
        if self.is_weekend(dt):
            if weekday == 5:  # Суббота
                return False, None, f"🔴 Рынок закрыт - Суббота (выходной). Открытие: воскресенье 22:00"
            elif weekday == 6:  # Воскресенье
                hours_until_open = 22 - dt.hour
                return False, None, f"🔴 Рынок закрыт - Воскресенье. Открытие через {hours_until_open}ч (в 22:00)"
            else:  # Пятница после 22:00
                return False, None, f"🔴 Рынок закрыт - Пятница (после 22:00). Открытие: воскресенье 22:00"
        
        # Проверка активных сессий
        active_sessions = []
        for session_id, session_info in self.sessions.items():
            if self._is_time_in_session(current_time, session_info['start'], session_info['end']):
                active_sessions.append(session_info['name'])
        
        if active_sessions:
            session_names = " + ".join(active_sessions)
            return True, session_names, f"🟢 Рынок открыт - {session_names}"
        else:
            # Рынок открыт, но нет активных основных сессий (тихое время)
            next_session = self._get_next_session(current_time)
            return True, "Pre-market", f"🟡 Рынок открыт - Тихое время. Следующая сессия: {next_session}"
    
    def _is_time_in_session(self, current: time, start: time, end: time) -> bool:
        """
        Проверить находится ли время в диапазоне сессии.
        
        Args:
            current: Текущее время
            start: Начало сессии
            end: Конец сессии
            
        Returns:
            bool: True если время в сессии
        """
        if start <= end:
            return start <= current <= end
        else:
            # Сессия переходит через полночь
            return current >= start or current <= end
    
    def _get_next_session(self, current: time) -> str:
        """
        Найти следующую торговую сессию.
        
        Args:
            current: Текущее время
            
        Returns:
            str: Название следующей сессии
        """
        # Упрощенная логика - проверяем основные сессии
        if current < time(1, 0):
            return "Asian (01:00)"
        elif current < time(9, 0):
            return "London (09:00)"
        elif current < time(15, 30):
            return "New York (15:30)"
        else:
            return "Asian (01:00 следующего дня)"
    
    def get_trading_status(self) -> dict:
        """
        Получить полную информацию о текущем статусе рынка.
        
        Returns:
            dict: Статус рынка с деталями
        """
        now = datetime.now(self.server_tz)
        market_open, session, message = self.get_current_session(now)
        is_weekend_now = self.is_weekend(now)
        
        return {
            'market_open': market_open,
            'is_weekend': is_weekend_now,
            'current_session': session,
            'message': message,
            'server_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'weekday': now.strftime('%A')
        }

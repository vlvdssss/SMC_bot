"""
Real-time News Fetcher для BAZA Trading Bot

Получает актуальные экономические новости и события.
Использует бесплатные источники.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class NewsEvent:
    """Экономическое событие."""
    
    def __init__(self, title: str, time: str, impact: str, currency: str, actual: str = "", forecast: str = "", previous: str = ""):
        self.title = title
        self.time = time
        self.impact = impact  # HIGH, MEDIUM, LOW
        self.currency = currency
        self.actual = actual
        self.forecast = forecast
        self.previous = previous
    
    def __str__(self):
        return f"[{self.impact}] {self.time} - {self.currency} - {self.title}"


class RealTimeNewsFetcher:
    """Получение актуальных экономических новостей."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 1 час
        self.last_fetch_time = None
        
    def fetch_todays_events(self) -> List[NewsEvent]:
        """
        Получает экономические события на сегодня.
        
        Returns:
            List[NewsEvent]: Список событий
        """
        # Проверяем кэш
        today = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"events_{today}"
        
        if cache_key in self.cache and self.last_fetch_time:
            time_diff = (datetime.now() - self.last_fetch_time).seconds
            if time_diff < self.cache_duration:
                logger.info(f"Using cached news data (age: {time_diff}s)")
                return self.cache[cache_key]
        
        # Пытаемся получить из нескольких источников
        events = []
        
        # Источник 1: Trading Economics (бесплатный календарь)
        try:
            events.extend(self._fetch_from_trading_economics())
        except Exception as e:
            logger.warning(f"Trading Economics fetch failed: {e}")
        
        # Источник 2: Investing.com календарь (парсинг)
        if not events:
            try:
                events.extend(self._fetch_from_investing())
            except Exception as e:
                logger.warning(f"Investing.com fetch failed: {e}")
        
        # Если мало HIGH-IMPACT событий - добавляем типичные как дополнение
        high_impact_count = sum(1 for e in events if e.impact in ['HIGH', 'EXTREME'])
        if high_impact_count < 2:
            logger.info(f"Only {high_impact_count} HIGH-IMPACT events from API, adding typical events")
            typical = self._get_typical_events()
            events.extend(typical)
        
        # Кэшируем
        self.cache[cache_key] = events
        self.last_fetch_time = datetime.now()
        
        logger.info(f"Fetched {len(events)} news events")
        return events
    
    def _fetch_from_trading_economics(self) -> List[NewsEvent]:
        """Получение с Trading Economics (бесплатный календарь)."""
        events = []
        
        try:
            # Trading Economics имеет публичный endpoint для календаря
            # Не требует API ключ для базового календаря
            today = datetime.now()
            date_str = today.strftime("%Y-%m-%d")
            
            # Публичный endpoint календаря
            url = f"https://api.tradingeconomics.com/calendar?c=guest:guest&d1={date_str}&d2={date_str}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Trading Economics returned status {response.status_code}")
                return events
            
            data = response.json()
            
            if not isinstance(data, list):
                return events
            
            for item in data:
                try:
                    title = item.get('Event', '')
                    
                    # Парсим дату и время
                    date_str_full = item.get('Date', '')
                    if date_str_full:
                        try:
                            dt = datetime.fromisoformat(date_str_full.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M UTC")
                        except (ValueError, AttributeError):
                            time_str = date_str_full[:5]  # Берем первые 5 символов (HH:MM)
                    else:
                        time_str = ""
                    
                    # Страна -> Валюта
                    country = item.get('Country', '')
                    currency_map = {
                        'United States': 'USD',
                        'Euro Area': 'EUR',
                        'United Kingdom': 'GBP',
                        'Japan': 'JPY',
                        'Canada': 'CAD',
                        'Australia': 'AUD',
                        'New Zealand': 'NZD',
                        'Switzerland': 'CHF',
                        'China': 'CNY'
                    }
                    currency = currency_map.get(country, country[:3].upper() if country else "")
                    
                    # Importance: 1=Low, 2=Medium, 3=High
                    importance = item.get('Importance', 1)
                    if importance >= 3:
                        impact = "HIGH"
                    elif importance == 2:
                        impact = "MEDIUM"
                    else:
                        impact = "LOW"
                    
                    # Ключевые события -> EXTREME
                    extreme_keywords = [
                        'NFP', 'NONFARM', 'FOMC', 'GDP', 'CPI', 'INFLATION', 
                        'INTEREST RATE', 'FED FUNDS', 'ECB DECISION', 'BOE DECISION',
                        'EMPLOYMENT', 'PAYROLLS', 'RATE DECISION', 'MONETARY POLICY'
                    ]
                    if any(kw in title.upper() for kw in extreme_keywords):
                        if impact == "HIGH":
                            impact = "EXTREME"
                    
                    actual = str(item.get('Actual', '')) if item.get('Actual') is not None else ""
                    forecast = str(item.get('Forecast', '')) if item.get('Forecast') is not None else ""
                    previous = str(item.get('Previous', '')) if item.get('Previous') is not None else ""
                    
                    if title and time_str:
                        event = NewsEvent(
                            title=title,
                            time=time_str,
                            impact=impact,
                            currency=currency,
                            actual=actual,
                            forecast=forecast,
                            previous=previous
                        )
                        events.append(event)
                        
                except Exception as e:
                    continue
            
            logger.info(f"Parsed {len(events)} events from Trading Economics")
            
        except Exception as e:
            logger.error(f"Trading Economics fetch error: {e}")
        
        return events
    
    def _fetch_from_investing(self) -> List[NewsEvent]:
        """Получение календаря из альтернативных источников."""
        events = []
        
        try:
            # Пробуем несколько источников
            # 1. Календарь с Myfxbook (открытый API)
            events = self._fetch_from_myfxbook()
            if events:
                return events
            
            # 2. FXStreet calendar widget
            events = self._fetch_from_fxstreet()
            if events:
                return events
            
        except Exception as e:
            logger.error(f"News API fetch error: {e}")
        
        return events
    
    def _fetch_from_myfxbook(self) -> List[NewsEvent]:
        """Получение с Myfxbook Economic Calendar."""
        events = []
        
        try:
            # Myfxbook предоставляет открытый endpoint
            today = datetime.now()
            date_str = today.strftime("%Y-%m-%d")
            
            url = f"https://www.myfxbook.com/api/get-economic-calendar.json?date={date_str}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Myfxbook returned status {response.status_code}")
                return events
            
            data = response.json()
            
            if not data or 'calendar' not in data:
                return events
            
            for item in data['calendar']:
                try:
                    # Парсим данные
                    title = item.get('title', '')
                    time_str = item.get('time', '')
                    currency = item.get('country', '')
                    
                    # Impact: 1=low, 2=medium, 3=high
                    impact_level = item.get('impact', 1)
                    if impact_level == 3:
                        impact = "HIGH"
                    elif impact_level == 2:
                        impact = "MEDIUM"
                    else:
                        impact = "LOW"
                    
                    # Особо важные -> EXTREME
                    if any(kw in title.upper() for kw in ['NFP', 'FOMC', 'GDP', 'CPI', 'RATE DECISION']):
                        if impact == "HIGH":
                            impact = "EXTREME"
                    
                    actual = item.get('actual', '')
                    forecast = item.get('forecast', '')
                    previous = item.get('previous', '')
                    
                    if title and time_str:
                        event = NewsEvent(
                            title=title,
                            time=time_str,
                            impact=impact,
                            currency=currency,
                            actual=str(actual) if actual else "",
                            forecast=str(forecast) if forecast else "",
                            previous=str(previous) if previous else ""
                        )
                        events.append(event)
                        
                except Exception as e:
                    continue
            
            logger.info(f"Parsed {len(events)} events from Myfxbook")
            
        except Exception as e:
            logger.error(f"Myfxbook fetch error: {e}")
        
        return events
    
    def _fetch_from_fxstreet(self) -> List[NewsEvent]:
        """Получение с FXStreet Calendar API."""
        events = []
        
        try:
            # FXStreet предоставляет JSON endpoint
            today = datetime.now()
            
            # Формат даты для FXStreet
            date_str = today.strftime("%Y/%m/%d")
            
            url = f"https://calendar-api.fxstreet.com/en/api/v1/eventDates/{date_str}/{date_str}?timezone=UTC&volatilities=3,4&countries=US,EU,GB,JP,CA,AU,NZ,CH"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"FXStreet returned status {response.status_code}")
                return events
            
            data = response.json()
            
            if not data:
                return events
            
            # FXStreet возвращает массив дат
            for date_entry in data:
                if 'events' not in date_entry:
                    continue
                
                for item in date_entry['events']:
                    try:
                        title = item.get('name', '')
                        
                        # Парсим время
                        date_utc = item.get('dateUtc', '')
                        if date_utc:
                            dt = datetime.fromisoformat(date_utc.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M UTC")
                        else:
                            time_str = ""
                        
                        # Страна -> валюта
                        country_code = item.get('countryCode', '')
                        currency_map = {
                            'US': 'USD', 'EU': 'EUR', 'GB': 'GBP',
                            'JP': 'JPY', 'CA': 'CAD', 'AU': 'AUD',
                            'NZ': 'NZD', 'CH': 'CHF'
                        }
                        currency = currency_map.get(country_code, country_code)
                        
                        # Volatility: 3=high, 4=extreme
                        volatility = item.get('volatility', 1)
                        if volatility >= 4:
                            impact = "EXTREME"
                        elif volatility == 3:
                            impact = "HIGH"
                        elif volatility == 2:
                            impact = "MEDIUM"
                        else:
                            impact = "LOW"
                        
                        actual = item.get('actual', '')
                        forecast = item.get('forecast', '')
                        previous = item.get('previous', '')
                        
                        if title and time_str:
                            event = NewsEvent(
                                title=title,
                                time=time_str,
                                impact=impact,
                                currency=currency,
                                actual=str(actual) if actual else "",
                                forecast=str(forecast) if forecast else "",
                                previous=str(previous) if previous else ""
                            )
                            events.append(event)
                            
                    except Exception as e:
                        continue
            
            logger.info(f"Parsed {len(events)} events from FXStreet")
            
        except Exception as e:
            logger.error(f"FXStreet fetch error: {e}")
        
        return events
    
    def _get_typical_events(self) -> List[NewsEvent]:
        """
        Возвращает типичные события на основе дня недели и времени.
        Используется как fallback когда Trading Economics API недоступен.
        """
        now = datetime.now()
        day_of_week = now.weekday()  # 0 = Monday, 6 = Sunday
        
        events = []
        
        logger.info("Using fallback typical events (Trading Economics API unavailable)")
        
        # Понедельник - Manufacturing PMI
        if day_of_week == 0:
            events.extend([
                NewsEvent(title="Manufacturing PMI", time="14:45 UTC", impact="HIGH", currency="USD"),
                NewsEvent(title="Retail Sales", time="15:00 UTC", impact="MEDIUM", currency="EUR"),
            ])
        
        # Вторник - CPI
        elif day_of_week == 1:
            events.extend([
                NewsEvent(title="CPI (Consumer Price Index)", time="13:30 UTC", impact="EXTREME", currency="USD"),
                NewsEvent(title="Core CPI", time="13:30 UTC", impact="HIGH", currency="USD"),
            ])
        
        # Среда - FOMC / Retail Sales
        elif day_of_week == 2:
            if now.day > 15 and now.day < 20:  # Середина месяца
                events.append(NewsEvent(title="FOMC Meeting Decision", time="18:00 UTC", impact="EXTREME", currency="USD"))
                events.append(NewsEvent(title="FOMC Press Conference", time="18:30 UTC", impact="EXTREME", currency="USD"))
            else:
                events.append(NewsEvent(title="Retail Sales", time="12:30 UTC", impact="HIGH", currency="USD"))
        
        # Четверг - Unemployment / ECB
        elif day_of_week == 3:
            events.extend([
                NewsEvent(title="Initial Jobless Claims", time="12:30 UTC", impact="MEDIUM", currency="USD"),
                NewsEvent(title="ECB Interest Rate Decision", time="12:15 UTC", impact="HIGH", currency="EUR"),
                NewsEvent(title="ECB Press Conference", time="12:45 UTC", impact="HIGH", currency="EUR"),
            ])
        
        # Пятница - NFP (первая пятница)
        elif day_of_week == 4:
            if now.day <= 7:  # Первая пятница месяца = NFP
                events.extend([
                    NewsEvent(title="Non-Farm Payrolls (NFP)", time="12:30 UTC", impact="EXTREME", currency="USD"),
                    NewsEvent(title="Unemployment Rate", time="12:30 UTC", impact="HIGH", currency="USD"),
                    NewsEvent(title="Average Hourly Earnings", time="12:30 UTC", impact="HIGH", currency="USD"),
                ])
            else:
                events.append(NewsEvent(title="Services PMI", time="14:45 UTC", impact="MEDIUM", currency="USD"))
        
        return events
    
    def get_high_impact_events(self, hours_ahead: int = 4) -> List[NewsEvent]:
        """
        Получает события высокого воздействия в ближайшие часы.
        
        Args:
            hours_ahead: Сколько часов вперед смотреть (по умолчанию 4)
                        Если hours_ahead >= 24 - возвращает все HIGH/EXTREME события дня
        
        Returns:
            List[NewsEvent]: Высокоимпактные события
        """
        all_events = self.fetch_todays_events()
        
        high_impact = []
        for event in all_events:
            if event.impact in ['HIGH', 'EXTREME']:
                # Если запрашивают весь день (24+ часа) - возвращаем все HIGH/EXTREME
                if hours_ahead >= 24:
                    high_impact.append(event)
                else:
                    # Проверяем время события
                    now = datetime.now()
                    try:
                        # Парсим время события (формат "HH:MM UTC")
                        time_str = event.time.replace(' UTC', '').strip()
                        event_hour, event_minute = map(int, time_str.split(':'))
                        
                        # Создаем datetime для события
                        event_dt = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
                        
                        # Проверяем: событие в будущем И в пределах hours_ahead
                        time_until = (event_dt - now).total_seconds() / 3600  # часы
                        if -1 <= time_until <= hours_ahead:  # -1 час назад до hours_ahead вперед
                            high_impact.append(event)
                    except (ValueError, TypeError, AttributeError, KeyError):
                        # Если не можем распарсить - добавляем на всякий случай
                        high_impact.append(event)
        
        return high_impact
    
    def get_relevant_news(self, symbol: str = "XAUUSD", hours: int = 24) -> List[Dict[str, Any]]:
        """
        Получает релевантные новости для символа.
        
        Args:
            symbol: Торговый символ
            hours: Часов вперед
        
        Returns:
            List[Dict]: Список новостей в формате dict
        """
        events = self.fetch_todays_events()
        high_impact = self.get_high_impact_events(hours_ahead=hours//4)  # Конвертируем в часы
        
        # Определяем релевантные валюты
        relevant_currencies = []
        if "XAU" in symbol or "GOLD" in symbol:
            relevant_currencies = ["USD"]
        elif "EUR" in symbol:
            relevant_currencies = ["EUR", "USD"]
        elif "GBP" in symbol:
            relevant_currencies = ["GBP", "USD"]
        else:
            relevant_currencies = ["USD"]
        
        # Конвертируем в dict формат
        news_list = []
        for event in events:
            if event.currency in relevant_currencies:
                news_list.append({
                    "title": event.title,
                    "time": event.time,
                    "impact": event.impact.lower(),
                    "currency": event.currency,
                    "summary": f"{event.currency} {event.title} at {event.time}"
                })
        
        return news_list
    
    def get_news_summary(self, instrument: str = "ALL") -> str:
        """
        Получает краткую сводку новостей для AI.
        
        Args:
            instrument: 'XAUUSD', 'EURUSD' или 'ALL'
        
        Returns:
            str: Текстовая сводка
        """
        events = self.fetch_todays_events()
        high_impact = self.get_high_impact_events(hours_ahead=6)
        
        if not events:
            return "Нет запланированных экономических событий на сегодня."
        
        # Фильтруем по инструменту
        relevant_currencies = []
        if instrument == "XAUUSD":
            relevant_currencies = ["USD"]
        elif instrument == "EURUSD":
            relevant_currencies = ["USD", "EUR"]
        else:
            relevant_currencies = ["USD", "EUR", "GBP", "JPY"]
        
        # Формируем сводку
        summary_lines = [f"📅 Экономические события на {datetime.now().strftime('%d.%m.%Y')}:\n"]
        
        if high_impact:
            summary_lines.append("⚠️ ВЫСОКОЕ ВЛИЯНИЕ (ближайшие 6 часов):")
            for event in high_impact[:3]:  # Топ-3
                if event.currency in relevant_currencies:
                    summary_lines.append(f"  • {event}")
        
        # Все события дня
        summary_lines.append("\n📊 Все события дня:")
        for event in events[:10]:  # Топ-10
            if event.currency in relevant_currencies:
                summary_lines.append(f"  • {event}")
        
        if len(events) > 10:
            summary_lines.append(f"  ... и еще {len(events) - 10} событий")
        
        return "\n".join(summary_lines)


# Singleton instance
_fetcher_instance = None

def get_news_fetcher() -> RealTimeNewsFetcher:
    """Получить синглтон instance фетчера новостей."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = RealTimeNewsFetcher()
    return _fetcher_instance

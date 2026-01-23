#!/usr/bin/env python3
"""
Gold News Filter v2.0 - Фильтрация HIGH IMPACT новостей ТОЛЬКО по XAU/USD/GOLD

ПРАВИЛА:
1. Учитываем ТОЛЬКО HIGH/EXTREME impact новости
2. Учитываем ТОЛЬКО новости, касающиеся:
   - USD (основная валюта золота)
   - GOLD/XAU (прямые новости по золоту)
   - Геополитика/ФРС (влияют на золото)
3. ИГНОРИРУЕМ:
   - EUR, GBP, JPY, AUD и другие валюты (если не влияют на USD)
   - MEDIUM/LOW impact новости
   - Технические новости (индексы, акции и т.п.)

ЛОГИКА БЛОКИРОВКИ:
- Если HIGH IMPACT новость по золоту в течение ±2 часов → БЛОКИРОВКА
- Иначе → Торговля разрешена
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.core.logger import logger


@dataclass
class GoldNewsEvent:
    """Событие, релевантное для золота."""
    title: str
    time: str  # "HH:MM UTC"
    impact: str  # "HIGH" or "EXTREME"
    currency: str  # "USD", "GOLD", etc.
    is_blocking: bool  # Блокирует ли торговлю
    minutes_until: int  # Сколько минут до события


class GoldNewsFilter:
    """
    Фильтр HIGH IMPACT новостей для золота (XAUUSD).
    """
    
    # Ключевые слова для определения релевантности новостей золоту
    GOLD_KEYWORDS = {
        'gold', 'xau', 'precious metals', 'bullion',
        'fed', 'fomc', 'federal reserve', 'jerome powell', 'janet yellen',
        'nfp', 'non-farm payrolls', 'employment', 'unemployment',
        'cpi', 'inflation', 'pce', 'consumer price',
        'gdp', 'interest rate', 'rate decision',
        'geopolitical', 'war', 'conflict', 'sanctions'
    }
    
    # Валюты, которые НЕ влияют на золото напрямую
    IRRELEVANT_CURRENCIES = {'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CAD', 'CHF'}
    
    def __init__(self, blocking_window_hours: int = 2):
        """
        Args:
            blocking_window_hours: За сколько часов до/после новости блокировать торговлю
        """
        self.blocking_window = blocking_window_hours
        logger.info(f"[Gold News Filter] Initialized | Blocking window: ±{blocking_window_hours}h")
    
    def is_relevant_to_gold(self, event_title: str, currency: str) -> bool:
        """
        Проверяет, релевантна ли новость для золота.
        
        Args:
            event_title: Заголовок новости
            currency: Валюта новости (USD, EUR, etc.)
        
        Returns:
            True если новость влияет на золото
        """
        title_lower = event_title.lower()
        
        # 1. Прямое упоминание золота
        if any(keyword in title_lower for keyword in ['gold', 'xau', 'bullion', 'precious']):
            return True
        
        # 2. Новости НЕ по USD → игнорируем (кроме глобальных событий)
        if currency in self.IRRELEVANT_CURRENCIES:
            # Исключение: геополитика влияет на золото независимо от валюты
            if any(kw in title_lower for kw in ['war', 'conflict', 'geopolitical', 'sanctions']):
                return True
            return False
        
        # 3. Ключевые USD/ФРС события, влияющие на золото
        if currency == 'USD':
            relevant_keywords = {
                'fed', 'fomc', 'powell', 'yellen',
                'nfp', 'payrolls', 'employment',
                'cpi', 'inflation', 'pce',
                'gdp', 'interest rate', 'rate decision'
            }
            if any(keyword in title_lower for keyword in relevant_keywords):
                return True
        
        # 4. По умолчанию - не релевантно
        return False
    
    def filter_gold_events(self, all_events: List[Dict]) -> List[GoldNewsEvent]:
        """
        Фильтрует события, оставляя только HIGH IMPACT новости по золоту.
        
        Args:
            all_events: Все новости из календаря (формат NewsEvent или dict)
        
        Returns:
            Список GoldNewsEvent - только релевантные для золота
        """
        gold_events = []
        now = datetime.now()
        
        for event in all_events:
            # Поддержка разных форматов входных данных
            if isinstance(event, dict):
                title = event.get('title', '')
                time_str = event.get('time', '')
                impact = event.get('impact', '')
                currency = event.get('currency', '')
            else:
                title = getattr(event, 'title', '')
                time_str = getattr(event, 'time', '')
                impact = getattr(event, 'impact', '')
                currency = getattr(event, 'currency', '')
            
            # Фильтр 1: Только HIGH/EXTREME impact
            if impact not in ['HIGH', 'EXTREME']:
                continue
            
            # Фильтр 2: Только релевантные для золота
            if not self.is_relevant_to_gold(title, currency):
                continue
            
            # Рассчитываем время до события
            try:
                time_clean = time_str.replace(' UTC', '').strip()
                event_hour, event_minute = map(int, time_clean.split(':'))
                event_dt = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
                
                # Если событие было раньше сегодня, пропускаем
                if event_dt < now - timedelta(hours=self.blocking_window):
                    continue
                
                minutes_until = int((event_dt - now).total_seconds() / 60)
                
                # Блокируется ли торговля
                is_blocking = abs(minutes_until) <= (self.blocking_window * 60)
                
            except Exception as e:
                logger.warning(f"[Gold News Filter] Failed to parse time '{time_str}': {e}")
                minutes_until = 0
                is_blocking = True  # На всякий случай блокируем
            
            gold_events.append(GoldNewsEvent(
                title=title,
                time=time_str,
                impact=impact,
                currency=currency,
                is_blocking=is_blocking,
                minutes_until=minutes_until
            ))
        
        return gold_events
    
    def should_block_trading(self, all_events: List[Dict]) -> Tuple[bool, Optional[GoldNewsEvent]]:
        """
        Проверяет, нужно ли блокировать торговлю из-за новостей.
        
        Args:
            all_events: Все новости из календаря
        
        Returns:
            (block: bool, blocking_event: GoldNewsEvent|None)
            - block=True если есть HIGH IMPACT новость в окне блокировки
            - blocking_event - событие, которое блокирует торговлю
        """
        gold_events = self.filter_gold_events(all_events)
        
        # Ищем ближайшее блокирующее событие
        for event in gold_events:
            if event.is_blocking:
                logger.warning(
                    f"[Gold News Filter] 🚫 TRADING BLOCKED | "
                    f"{event.impact} event in {event.minutes_until}min: {event.title} ({event.currency})"
                )
                return True, event
        
        # Нет блокирующих событий
        if gold_events:
            logger.info(
                f"[Gold News Filter] ✅ Trading allowed | "
                f"Found {len(gold_events)} gold events but outside blocking window"
            )
        else:
            logger.info("[Gold News Filter] ✅ No HIGH IMPACT gold events today")
        
        return False, None
    
    def get_upcoming_gold_events(self, all_events: List[Dict], hours_ahead: int = 24) -> List[GoldNewsEvent]:
        """
        Получает список предстоящих HIGH IMPACT событий по золоту.
        
        Args:
            all_events: Все новости
            hours_ahead: Сколько часов вперёд смотреть
        
        Returns:
            Список GoldNewsEvent в ближайшие hours_ahead часов
        """
        gold_events = self.filter_gold_events(all_events)
        
        # Фильтруем по времени
        upcoming = [
            event for event in gold_events
            if 0 <= event.minutes_until <= (hours_ahead * 60)
        ]
        
        # Сортируем по времени
        upcoming.sort(key=lambda e: e.minutes_until)
        
        return upcoming


# ============================================================
# ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМ NEWS FETCHER
# ============================================================

class GoldNewsFetcher:
    """
    Обёртка для интеграции GoldNewsFilter с существующим NewsFetcher.
    """
    
    def __init__(self, news_fetcher):
        """
        Args:
            news_fetcher: Экземпляр src.ai.news_fetcher.NewsFetcher
        """
        self.news_fetcher = news_fetcher
        self.gold_filter = GoldNewsFilter(blocking_window_hours=2)
        logger.info("[Gold News Fetcher] Initialized with existing NewsFetcher")
    
    def check_trading_safety_for_gold(self) -> Tuple[bool, str]:
        """
        Проверяет безопасность торговли золотом.
        
        Returns:
            (safe: bool, reason: str)
            - safe=True если можно торговать
            - reason - объяснение решения
        """
        try:
            # Получаем все события сегодня
            all_events = self.news_fetcher.fetch_todays_events()
            
            # Проверяем блокировку
            should_block, blocking_event = self.gold_filter.should_block_trading(all_events)
            
            if should_block:
                reason = (
                    f"HIGH IMPACT gold event in {blocking_event.minutes_until}min: "
                    f"{blocking_event.title} ({blocking_event.currency})"
                )
                return False, reason
            else:
                return True, "No HIGH IMPACT gold events in blocking window"
        
        except Exception as e:
            logger.error(f"[Gold News Fetcher] Error checking news: {e}")
            # Fail-safe: разрешаем торговлю при ошибке
            return True, f"News check failed: {e}"
    
    def get_todays_gold_events(self) -> List[GoldNewsEvent]:
        """Получает все HIGH IMPACT события по золоту сегодня."""
        try:
            all_events = self.news_fetcher.fetch_todays_events()
            return self.gold_filter.get_upcoming_gold_events(all_events, hours_ahead=24)
        except Exception as e:
            logger.error(f"[Gold News Fetcher] Error fetching events: {e}")
            return []


# ============================================================
# ТЕСТИРОВАНИЕ
# ============================================================

if __name__ == "__main__":
    # Тестовые данные
    test_events = [
        {'title': 'US Non-Farm Payrolls', 'time': '13:30 UTC', 'impact': 'HIGH', 'currency': 'USD'},
        {'title': 'FOMC Interest Rate Decision', 'time': '19:00 UTC', 'impact': 'EXTREME', 'currency': 'USD'},
        {'title': 'Eurozone CPI', 'time': '10:00 UTC', 'impact': 'HIGH', 'currency': 'EUR'},
        {'title': 'Gold Inventories Report', 'time': '15:00 UTC', 'impact': 'MEDIUM', 'currency': 'GOLD'},
        {'title': 'UK GDP', 'time': '09:00 UTC', 'impact': 'HIGH', 'currency': 'GBP'},
        {'title': 'US CPI Inflation', 'time': '13:30 UTC', 'impact': 'HIGH', 'currency': 'USD'},
    ]
    
    gold_filter = GoldNewsFilter(blocking_window_hours=2)
    
    print("\n=== GOLD NEWS FILTER TEST ===\n")
    
    # Фильтруем события
    gold_events = gold_filter.filter_gold_events(test_events)
    
    print(f"Total events: {len(test_events)}")
    print(f"Gold-relevant HIGH IMPACT events: {len(gold_events)}\n")
    
    for event in gold_events:
        block_status = "🚫 BLOCKS" if event.is_blocking else "✅ OK"
        print(f"{block_status} | {event.impact} | {event.currency} | {event.title} | {event.time}")
    
    # Проверяем блокировку
    should_block, blocking_event = gold_filter.should_block_trading(test_events)
    
    print(f"\n{'='*60}")
    if should_block:
        print(f"⛔ TRADING BLOCKED by: {blocking_event.title}")
    else:
        print("✅ TRADING ALLOWED - No blocking events")
    print(f"{'='*60}\n")

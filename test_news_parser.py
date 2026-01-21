"""
Тест парсера новостей Investing.com
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ai.news_fetcher import get_news_fetcher

def test_news_fetcher():
    print("\n" + "="*80)
    print("🔍 ТЕСТ ПАРСЕРА НОВОСТЕЙ INVESTING.COM")
    print("="*80 + "\n")
    
    fetcher = get_news_fetcher()
    
    print("📥 Fetching today's events...")
    events = fetcher.fetch_todays_events()
    
    print(f"\n✅ Получено событий: {len(events)}\n")
    
    if not events:
        print("⚠️  Нет событий (возможно проблема с парсингом или сайт недоступен)")
        print("   Fallback система будет использована автоматически\n")
        return
    
    # Показываем все события
    print("📅 ВСЕ СОБЫТИЯ СЕГОДНЯ:")
    print("-" * 80)
    for i, event in enumerate(events[:20], 1):  # Первые 20
        impact_emoji = {
            "EXTREME": "🔴",
            "HIGH": "🟠", 
            "MEDIUM": "🟡",
            "LOW": "⚪"
        }.get(event.impact, "⚪")
        
        print(f"{i:2}. {impact_emoji} {event.time:>8} | {event.currency:3} | {event.impact:7} | {event.title}")
        
        if event.forecast or event.previous:
            details = []
            if event.forecast:
                details.append(f"Forecast: {event.forecast}")
            if event.previous:
                details.append(f"Previous: {event.previous}")
            if event.actual:
                details.append(f"Actual: {event.actual}")
            if details:
                print(f"     └─ {' | '.join(details)}")
    
    if len(events) > 20:
        print(f"\n   ... и еще {len(events) - 20} событий")
    
    # Высокоимпактные события
    print("\n" + "="*80)
    print("⚠️  HIGH-IMPACT СОБЫТИЯ (для GUI):")
    print("="*80)
    
    high_impact = fetcher.get_high_impact_events(hours_ahead=24)
    
    if high_impact:
        for event in high_impact[:5]:  # Топ-5 для GUI
            impact_emoji = "🔴" if event.impact == "EXTREME" else "🟠"
            print(f"{impact_emoji} {event.time:>8} | {event.currency:3} | {event.impact:7} | {event.title}")
    else:
        print("   Нет высокоимпактных событий в ближайшие 24 часа")
    
    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_news_fetcher()

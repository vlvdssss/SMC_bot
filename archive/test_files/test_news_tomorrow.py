"""
Тест парсера новостей - завтрашние события
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from src.ai.news_fetcher import RealTimeNewsFetcher, NewsEvent
import requests

def test_tomorrow():
    print("\n" + "="*80)
    print("🔍 ТЕСТ: ЗАВТРАШНИЕ СОБЫТИЯ (Trading Economics)")
    print("="*80 + "\n")
    
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")
    
    url = f"https://api.tradingeconomics.com/calendar?c=guest:guest&d1={date_str}&d2={date_str}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json',
    }
    
    print(f"📅 Дата: {date_str}")
    print(f"🌐 URL: {url}\n")
    
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"📡 Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ События: {len(data)}\n")
        
        if data:
            print("📰 ТОП-20 СОБЫТИЙ НА ЗАВТРА:")
            print("-" * 80)
            
            for i, item in enumerate(data[:20], 1):
                title = item.get('Event', '')
                country = item.get('Country', '')
                importance = item.get('Importance', 1)
                
                # Currency mapping
                currency_map = {
                    'United States': 'USD',
                    'Euro Area': 'EUR',
                    'United Kingdom': 'GBP',
                    'Japan': 'JPY',
                    'Canada': 'CAD',
                }
                currency = currency_map.get(country, country[:3].upper() if country else "")
                
                # Impact
                if importance >= 3:
                    impact = "HIGH"
                    emoji = "🟠"
                elif importance == 2:
                    impact = "MEDIUM"
                    emoji = "🟡"
                else:
                    impact = "LOW"
                    emoji = "⚪"
                
                # Check for EXTREME events
                if any(kw in title.upper() for kw in ['NFP', 'NONFARM', 'FOMC', 'GDP', 'CPI', 'INFLATION', 'INTEREST RATE']):
                    if impact == "HIGH":
                        impact = "EXTREME"
                        emoji = "🔴"
                
                date_str_full = item.get('Date', '')
                if date_str_full:
                    try:
                        dt = datetime.fromisoformat(date_str_full.replace('Z', '+00:00'))
                        time_str = dt.strftime("%H:%M UTC")
                    except:
                        time_str = date_str_full[:5]
                else:
                    time_str = "N/A"
                
                print(f"{i:2}. {emoji} {time_str:>8} | {currency:3} | {impact:7} | {title}")
                
                actual = item.get('Actual')
                forecast = item.get('Forecast')
                previous = item.get('Previous')
                
                if actual or forecast or previous:
                    details = []
                    if forecast:
                        details.append(f"Forecast: {forecast}")
                    if previous:
                        details.append(f"Previous: {previous}")
                    if actual:
                        details.append(f"Actual: {actual}")
                    if details:
                        print(f"     └─ {' | '.join([str(d) for d in details])}")
        else:
            print("⚠️  Нет событий на завтра")
    else:
        print(f"❌ Error: {response.status_code}")
    
    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_tomorrow()

import requests
from datetime import datetime

# NFP день - первая пятница февраля 2026
date_str = "2026-02-06"

url = f"https://api.tradingeconomics.com/calendar?c=guest:guest&d1={date_str}&d2={date_str}"

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
}

response = requests.get(url, headers=headers, timeout=10)

print(f"Date: {date_str} (First Friday of February)")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Total Events: {len(data)}\n")
    
    # Filter HIGH-IMPACT
    high_impact = [i for i in data if i.get('Importance', 0) >= 2]
    print(f"HIGH-IMPACT Events: {len(high_impact)}\n")
    
    for item in high_impact[:15]:
        title = item.get('Event', '')
        country = item.get('Country', '')
        importance = item.get('Importance', 1)
        
        emoji = "HIGH" if importance >= 3 else "MED"
        nfp = " <-- NFP!" if 'NONFARM' in title.upper() else ""
        
        print(f"[{emoji}] {country:20} | {title}{nfp}")

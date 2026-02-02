#!/usr/bin/env python3
"""
Скрипт для проверки реального PnL сделки в MT5
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from pathlib import Path
import yaml

# Загружаем конфигурацию MT5
config_path = Path('config/mt5.yaml')
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        mt5_config = yaml.safe_load(f).get('mt5', {})
    
    # Подключаемся к MT5
    if not mt5.initialize():
        print(f"❌ Не удалось инициализировать MT5, error code = {mt5.last_error()}")
        quit()
    
    # Авторизуемся
    login = mt5_config.get('login')
    password = mt5_config.get('password')
    server = mt5_config.get('server')
    
    if mt5.login(login, password, server):
        print(f"✅ Подключено к MT5: {login}@{server}")
        
        # Ищем сделку #6631795594
        position_id = 6631795594
        
        # Ищем в истории сделок за последние 24 часа
        from_date = datetime.now() - timedelta(hours=24)
        to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals:
            print(f"\n📊 Найдено сделок за последние 24 часа: {len(deals)}")
            
            # Ищем сделки с position_id=6631795594
            target_deals = [d for d in deals if d.position_id == position_id]
            
            if target_deals:
                print(f"\n🎯 Сделки для позиции #{position_id}:")
                for deal in target_deals:
                    print(f"\n  Deal #{deal.ticket}:")
                    print(f"    Type: {'BUY' if deal.type == 0 else 'SELL'}")
                    print(f"    Entry: {'IN' if deal.entry == 0 else 'OUT'}")
                    print(f"    Price: {deal.price}")
                    print(f"    Volume: {deal.volume}")
                    print(f"    Profit: ${deal.profit:.2f}")
                    print(f"    Time: {datetime.fromtimestamp(deal.time)}")
                
                # Подсчитываем общий profit
                total_profit = sum(d.profit for d in target_deals)
                print(f"\n💰 Итоговый PnL для позиции #{position_id}: ${total_profit:.2f}")
            else:
                print(f"\n❌ Сделки для позиции #{position_id} не найдены")
                print("\nПроверим последние 10 сделок:")
                for deal in deals[-10:]:
                    print(f"  Deal #{deal.ticket}: Position #{deal.position_id}, Profit: ${deal.profit:.2f}")
        else:
            print("❌ История сделок пуста")
        
        mt5.shutdown()
    else:
        print(f"❌ Не удалось авторизоваться: {mt5.last_error()}")
        mt5.shutdown()
else:
    print("❌ Конфигурация MT5 не найдена")

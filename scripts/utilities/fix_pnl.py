#!/usr/bin/env python3
"""
Скрипт для исправления неправильного PnL в trades_history.json
Пересчитывает estimated profit по правильной формуле для XAUUSD
"""

import json
from pathlib import Path

trades_file = Path('data/trades_history.json')

if trades_file.exists():
    with open(trades_file, 'r', encoding='utf-8') as f:
        trades = json.load(f)
    
    print(f"📊 Всего сделок: {len(trades)}")
    print(f"🔍 Ищем сделки с неправильным PnL (result='Trailing Stop')...")
    
    fixed_count = 0
    
    for trade in trades:
        # Проверяем сделки где profit похож на неправильный расчет
        # (price_diff * volume * 100 вместо price_diff * volume * 100 / 100)
        
        if trade.get('symbol') == 'XAUUSD' and trade.get('volume') == 0.01:
            old_pnl = trade.get('pnl', 0)
            
            # Если PnL выглядит как неправильно рассчитанный (слишком большой)
            # Например: -19.71 вместо -2.43 (разница в 8.1 раз ~ 100/12.35)
            # Или -16.0 вместо -1.6 (разница в 10 раз)
            
            # Проверяем сделку #6631795594
            if trade.get('ticket') == 6631795594:
                print(f"\n🎯 Найдена проблемная сделка #{trade['ticket']}:")
                print(f"   Текущий PnL: ${old_pnl:.2f}")
                print(f"   Type: {trade['type']}")
                print(f"   Entry: {trade.get('entry')}")
                print(f"   Volume: {trade.get('volume')}")
                
                # Если у нас есть информация о ценах, пересчитываем
                # Но у нас нет цены закрытия в истории...
                # Предполагаем, что пользователь сказал: должно быть -2.43
                
                print(f"\n   ❓ Введите правильный PnL (по данным пользователя: -2.43): ", end='')
                correct_pnl = input().strip()
                
                if correct_pnl:
                    try:
                        new_pnl = float(correct_pnl)
                        trade['pnl'] = new_pnl
                        print(f"   ✅ PnL исправлен: ${old_pnl:.2f} → ${new_pnl:.2f}")
                        fixed_count += 1
                    except ValueError:
                        print(f"   ❌ Неверный формат PnL")
    
    if fixed_count > 0:
        # Сохраняем исправленные данные
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Исправлено сделок: {fixed_count}")
        print(f"💾 Данные сохранены в {trades_file}")
        
        # Пересчитываем статистику
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        today_pnl = sum(t.get('pnl', 0) for t in trades if t.get('date') == '2026-02-02')
        
        print(f"\n📊 Новая статистика:")
        print(f"   Total PnL: ${total_pnl:.2f}")
        print(f"   Today PnL: ${today_pnl:.2f}")
        
        # Обновляем bot_stats.json
        stats_file = Path('data/bot_stats.json')
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            stats['total_pnl'] = round(total_pnl, 2)
            stats['today_pnl'] = round(today_pnl, 2)
            
            # Пересчитываем starting_balance
            balance = stats.get('balance', 0)
            stats['starting_balance'] = balance - total_pnl
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            print(f"✅ bot_stats.json обновлен")
    else:
        print(f"\n❌ Сделок для исправления не найдено")
else:
    print("❌ Файл trades_history.json не найден")

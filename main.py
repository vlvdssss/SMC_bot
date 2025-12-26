#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    BAZA TRADING BOT v1.0                     ║
║                                                              ║
║  Автоматическая торговля на основе Smart Money Concepts      ║
║                                                              ║
║  Результаты бэктеста 2024:                                   ║
║  • XAUUSD: +45.86% ROI, 16% Max DD                          ║
║  • EURUSD: +340.75% ROI, 5.32% Max DD                       ║
║                                                              ║
║  Лицензия:                                                   ║
║  • Бэктестинг: БЕСПЛАТНО                                    ║
║  • Live торговля: ПЛАТНАЯ ЛИЦЕНЗИЯ                         ║
║                                                              ║
║  Запуск:                                                     ║
║    python main.py --mode demo                                ║
║    python main.py --mode live                                ║
║    python main.py --mode backtest --year 2024                ║
╚══════════════════════════════════════════════════════════════╝
"""

import argparse
import sys
import os
import time
import yaml
import base64
import json
import hashlib
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from strategies.xauusd_strategy import StrategyXAUUSD
from strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement
from mt5.connector import MT5Connector
from live.live_trader import LiveTrader
from backtest.portfolio_backtester import PortfolioBacktester
from backtest.backtester import RealisticBacktester
from core.broker_sim import BrokerSim
from core.data_loader import DataLoader


def _is_market_open(mt5_connector) -> bool:
    """Проверка, открыт ли рынок"""
    import MetaTrader5 as mt5
    
    if not mt5.terminal_info():
        return False
        
    # Проверяем сессии для основных пар
    symbols = ['EURUSD', 'XAUUSD']
    for symbol in symbols:
        if mt5.symbol_info(symbol) is None:
            continue
            
        # Получаем информацию о сессиях
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info and hasattr(symbol_info, 'session_deals'):
            # Если есть сделки в сессии, рынок открыт
            if symbol_info.session_deals > 0:
                return True
    
    # Простая проверка по времени
    now = datetime.now()
    if now.weekday() >= 5:  # суббота, воскресенье
        return False
        
    # Торговое время (00:00 - 23:59 UTC, но зависит от брокера)
    return True


def main():
    parser = argparse.ArgumentParser(
        description='BAZA Trading Bot - SMC автоматическая торговля',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--mode', type=str, required=True,
                        choices=['demo', 'live', 'backtest'],
                        help='Режим работы: demo, live, backtest')
    
    parser.add_argument('--year', type=int, default=2024,
                        help='Год для бэктеста (по умолчанию 2024)')
    
    parser.add_argument('--instrument', type=str, default='all',
                        choices=['all', 'xauusd', 'eurusd'],
                        help='Инструмент (по умолчанию all)')
    
    parser.add_argument('--portfolio', action='store_true',
                        help='Запустить портфельный бэктест')
    
    parser.add_argument('--interval', type=int, default=60,
                        help='Интервал проверки в секундах (по умолчанию 60)')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.mode == 'demo':
        run_demo(args)
    elif args.mode == 'live':
        run_live(args)
    elif args.mode == 'backtest':
        run_backtest(args)


def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    BAZA TRADING BOT v1.0                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def run_demo(args):
    """Запуск в демо режиме (мониторинг без торговли)"""
    print("[*] Режим: DEMO (мониторинг без торговли)")
    print(f"[*] Интервал проверки: {args.interval} сек")
    print("-" * 60)
    
    # Загрузка конфига MT5
    try:
        with open('config/mt5.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        mt5_config = config['mt5']
    except Exception as e:
        print(f"[!] Ошибка загрузки конфига MT5: {e}")
        return
    
    # Инициализация стратегий
    strategies = {
        'XAUUSD': StrategyXAUUSD(),
        'EURUSD': StrategyEURUSD_SMC_Retracement()
    }
    
    # Подключение к MT5
    mt5 = MT5Connector(mt5_config)
    if not mt5.connect():
        print("[!] Ошибка подключения к MT5")
        return
    
    print("[+] Подключено к MT5")
    
    try:
        while True:
            # Проверка времени рынка
            if not _is_market_open(mt5):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Рынок закрыт - ждём открытия...")
                time.sleep(300)  # Проверка каждые 5 минут
                continue
                
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Проверка сигналов...")
            
            for instrument, strategy in strategies.items():
                # Получение текущих данных
                data = mt5.get_latest_data(instrument, timeframe='H1', count=100)
                if data is None or data.empty:
                    print(f"[-] {instrument}: Нет данных")
                    continue
                
                current_bar = data.iloc[-1]
                
                # Генерация сигнала (упрощенная для demo)
                signal = None
                if len(data) > 10:
                    sma_short = data['close'].rolling(5).mean().iloc[-1]
                    sma_long = data['close'].rolling(20).mean().iloc[-1]
                    
                    if sma_short > sma_long:
                        signal = {'type': 'BUY'}
                    elif sma_short < sma_long:
                        signal = {'type': 'SELL'}
                
                if signal:
                    print(f"[!] {instrument}: СИГНАЛ {signal['type']} на цене {current_bar['close']:.5f}")
                else:
                    print(f"[+] {instrument}: Нет сигнала (цена: {current_bar['close']:.5f})")
            
            print(f"Следующая проверка через {args.interval} сек...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n[!] Остановлено пользователем")
    finally:
        mt5.disconnect()


def run_live(args):
    """Запуск реальной торговли"""
    print("[!] ВНИМАНИЕ: Режим LIVE торговли!")
    print("[!] Будут открываться реальные сделки!")
    print("[!] Требуется платная лицензия для live торговли!")
    
    confirm = input("\nВы уверены что хотите запустить LIVE торговлю? (Y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Отменено.")
        return
    
    # Проверка лицензии
    license_key = input("Введите лицензионный ключ (или 'TRIAL' для пробного периода 3 дня): ")
    if not validate_license(license_key):
        print("[!] НЕВАЛИДНЫЙ КЛЮЧ ЛИЦЕНЗИИ")
        print("[!] Свяжитесь для получения лицензии: kamsaaaimpa@gmail.com")
        return
    
    # Загрузка конфига MT5
    try:
        with open('config/mt5.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        mt5_config = config['mt5']
    except Exception as e:
        print(f"[!] Ошибка загрузки конфига MT5: {e}")
        return
    
    # Инициализация стратегий
    strategies = {
        'XAUUSD': StrategyXAUUSD(),
        'EURUSD': StrategyEURUSD_SMC_Retracement()
    }
    
    # Инициализация компонентов
    mt5_connector = MT5Connector(mt5_config)
    executor = BrokerSim()  # Пока используем симулятор, потом заменить на реальный
    
    # Запуск live трейдера
    trader = LiveTrader(strategies, executor, mt5_connector)
    trader.run()


def validate_license(key: str) -> bool:
    """Простая валидация лицензии с пробным периодом"""
    # Пробный период 3 дня
    if key == "TRIAL":
        return check_trial_period()
    
    # Проверка сгенерированных ключей
    try:
        if key.startswith("BAZA-"):
            # Декодирование
            encoded = key[5:]  # Убираем "BAZA-"
            json_str = base64.b64decode(encoded).decode()
            data = json.loads(json_str)
            
            # Проверка хэша
            data_copy = data.copy()
            hash_check = data_copy.pop("hash")
            data_str = json.dumps(data_copy, sort_keys=True)
            hash_obj = hashlib.sha256(data_str.encode())
            if hash_obj.hexdigest() != hash_check:
                return False
            
            # Проверка даты
            expiry = datetime.fromisoformat(data["expiry"])
            if datetime.now() > expiry:
                return False
            
            return True
    except:
        pass
    
    return False

def check_trial_period() -> bool:
    """Проверка пробного периода (3 дня от первого запуска)"""
    import os
    trial_file = "trial_start.txt"
    
    now = datetime.now()
    
    if os.path.exists(trial_file):
        # Читаем дату начала
        try:
            with open(trial_file, 'r') as f:
                start_str = f.read().strip()
                start_date = datetime.fromisoformat(start_str)
                days_used = (now - start_date).days
                if days_used <= 3:
                    return True
                else:
                    print(f"[!] Пробный период истёк ({days_used} дней из 3)")
                    return False
        except:
            pass
    
    # Первый запуск - начинаем trial
    with open(trial_file, 'w') as f:
        f.write(now.isoformat())
    
    print("[+] Активирован пробный период LIVE режима (3 дня)")
    return True


def run_backtest(args):
    """Запуск бэктеста"""
    print(f"[*] Режим: BACKTEST")
    print(f"[*] Год: {args.year}")
    print(f"[*] Инструмент: {args.instrument}")
    print(f"[*] Портфель: {args.portfolio}")
    print("-" * 60)
    
    if args.portfolio:
        # Portfolio backtest
        backtester = PortfolioBacktester()
        result = backtester.run_backtest(
            f"{args.year}-01-01",
            f"{args.year}-12-31"
        )
        print(f"\n[PORTFOLIO] ROI: {result['roi']}%, Trades: {result['trades']}, Max DD: {result['max_dd']}%, Win Rate: {result['win_rate']}%")
    else:
        # Single instrument backtests
        strategies = {
            'XAUUSD': StrategyXAUUSD(),
            'EURUSD': StrategyEURUSD_SMC_Retracement()
        }
        
        # Create broker and data loader
        broker = BrokerSim()
        data_loader = DataLoader()
        
        backtester = RealisticBacktester(strategies, broker, data_loader)
        
        if args.instrument in ['all', 'xauusd']:
            print("\n[XAUUSD]")
            result = backtester.run_backtest('XAUUSD', datetime(args.year, 1, 1), datetime(args.year, 12, 31))
            if 'error' in result:
                print(f"Ошибка: {result['error']}")
            else:
                print(f"ROI: {result['total_return']:.2f}%, Trades: {result['total_trades']}, Max DD: {result['max_drawdown']:.2f}%, Win Rate: {result['win_rate']:.1f}%")
        
        if args.instrument in ['all', 'eurusd']:
            print("\n[EURUSD]")
            result = backtester.run_backtest('EURUSD', datetime(args.year, 1, 1), datetime(args.year, 12, 31))
            if 'error' in result:
                print(f"Ошибка: {result['error']}")
            else:
                print(f"ROI: {result['total_return']:.2f}%, Trades: {result['total_trades']}, Max DD: {result['max_drawdown']:.2f}%, Win Rate: {result['win_rate']:.1f}%")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Остановлено пользователем (Ctrl+C)")
        sys.exit(0)

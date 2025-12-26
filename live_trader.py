"""
Live/Demo Trading Module

Реальная торговля с MT5 подключением и мониторингом сигналов.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yaml
import time
from datetime import datetime, timedelta
import pandas as pd

from mt5.connector import MT5Connector
from BAZA.strategies.xauusd_strategy import StrategyXAUUSD
from BAZA.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement


class LiveTrader:
    """
    Live/Demo трейдер для реальной торговли.
    
    Функции:
    - Подключение к MT5
    - Загрузка данных в реальном времени
    - Мониторинг сигналов стратегий
    - Выполнение сделок (опционально)
    """
    
    def __init__(self, config_dir='BAZA/config'):
        """Инициализация live трейдера."""
        self.config_dir = config_dir
        self.connector = None
        self.instruments = {}
        self.strategies = {}
        self.active_instruments = []
        self.enable_trading = False
        
        # Загрузка конфигов
        self.load_configs()
    
    def load_configs(self):
        """Загрузка конфигураций."""
        # MT5 config
        mt5_config_path = os.path.join(self.config_dir, 'mt5.yaml')
        with open(mt5_config_path, 'r', encoding='utf-8') as f:
            self.mt5_config = yaml.safe_load(f)
        
        # Instruments config
        instruments_config_path = os.path.join(self.config_dir, 'instruments.yaml')
        with open(instruments_config_path, 'r', encoding='utf-8') as f:
            self.instruments_config = yaml.safe_load(f)
        
        # Portfolio config
        portfolio_config_path = os.path.join(self.config_dir, 'portfolio.yaml')
        with open(portfolio_config_path, 'r', encoding='utf-8') as f:
            self.portfolio_config = yaml.safe_load(f)
        
        # Активные инструменты
        self.active_instruments = self.portfolio_config['portfolio']['instruments']
        
        print(f"[+] Configs loaded")
        print(f"    Active instruments: {', '.join(self.active_instruments)}")
    
    def connect_mt5(self):
        """Подключение к MT5."""
        print("\n[*] Connecting to MT5...")
        
        mt5_config_path = os.path.join(self.config_dir, 'mt5.yaml')
        self.connector = MT5Connector(config_path=mt5_config_path)
        
        if not self.connector.connect():
            print("[!] Failed to connect to MT5")
            return False
        
        # Проверяем режим торговли
        self.enable_trading = self.mt5_config['mt5']['settings']['enable_trade']
        
        if self.enable_trading:
            print("[!] WARNING: Trading is ENABLED. Real trades will be executed!")
        else:
            print("[+] Trading is DISABLED. Monitoring signals only (DEMO mode)")
        
        return True
    
    def initialize_strategies(self):
        """Инициализация стратегий для активных инструментов."""
        print("\n[*] Initializing strategies...")
        
        for instrument in self.active_instruments:
            config = self.instruments_config['instruments'][instrument]
            strategy_class_name = config['strategy_class']
            
            # Создаём стратегию
            if strategy_class_name == 'StrategyXAUUSD':
                strategy = StrategyXAUUSD()
            elif strategy_class_name in ['StrategyEURUSD', 'StrategyEURUSD_SMC_Retracement']:
                strategy = StrategyEURUSD_SMC_Retracement()
            else:
                print(f"[!] Unknown strategy class: {strategy_class_name}")
                continue
            
            self.strategies[instrument] = strategy
            
            strategy_name = getattr(strategy, 'name', strategy_class_name)
            strategy_version = getattr(strategy, 'version', 'unknown')
            
            print(f"    {instrument}: {strategy_name} v{strategy_version} - READY")
    
    def load_historical_data(self, instrument, bars_h1=500, bars_m15=2000):
        """
        Загрузка исторических данных из MT5.
        
        Args:
            instrument: Символ (XAUUSD, EURUSD)
            bars_h1: Количество H1 баров
            bars_m15: Количество M15 баров
            
        Returns:
            dict: {'h1': DataFrame, 'm15': DataFrame}
        """
        import MetaTrader5 as mt5
        from datetime import timezone
        
        # H1 data
        rates_h1 = mt5.copy_rates_from_pos(instrument, mt5.TIMEFRAME_H1, 0, bars_h1)
        if rates_h1 is None or len(rates_h1) == 0:
            print(f"[!] Failed to load H1 data for {instrument}")
            return None
        
        df_h1 = pd.DataFrame(rates_h1)
        df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
        
        # M15 data
        rates_m15 = mt5.copy_rates_from_pos(instrument, mt5.TIMEFRAME_M15, 0, bars_m15)
        if rates_m15 is None or len(rates_m15) == 0:
            print(f"[!] Failed to load M15 data for {instrument}")
            return None
        
        df_m15 = pd.DataFrame(rates_m15)
        df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
        
        return {'h1': df_h1, 'm15': df_m15}
    
    def check_signals(self):
        """Проверка сигналов для всех активных инструментов."""
        signals = {}
        
        for instrument in self.active_instruments:
            # Загружаем свежие данные
            data = self.load_historical_data(instrument, bars_h1=500, bars_m15=2000)
            if data is None:
                continue
            
            h1_data = data['h1']
            m15_data = data['m15']
            
            # Загружаем данные в стратегию
            strategy = self.strategies[instrument]
            strategy.load_data(h1_data, m15_data)
            
            # Строим контекст на последнем H1
            h1_idx = len(h1_data) - 1
            strategy.build_context(h1_idx)
            
            # Проверяем сигнал на последнем M15
            m15_idx = len(m15_data) - 1
            current_price = m15_data.iloc[m15_idx]['close']
            current_time = m15_data.iloc[m15_idx]['time']
            
            # generate_signal - LIVE версия: анализ на close, вход market
            if instrument == 'XAUUSD':
                # Для live: используем текущую цену как analysis_price и entry_price
                signal = strategy.generate_signal(m15_idx, current_price, current_price)
            else:
                signal = strategy.generate_signal(m15_idx, current_price, current_price, current_time)
            
            signals[instrument] = {
                'signal': signal,
                'price': current_price,
                'time': current_time,
                'h1_idx': h1_idx,
                'm15_idx': m15_idx
            }
        
        return signals
    
    def _prepare_mt5_request(self, instrument: str, trade_params: dict) -> dict:
        """
        Подготовка MT5 request из trade_params.
        
        Args:
            instrument: Символ (XAUUSD, EURUSD)
            trade_params: Параметры от execute_trade()
            
        Returns:
            dict: MT5 order request
        """
        import MetaTrader5 as mt5
        
        direction = trade_params['direction']
        # В live торговле используем текущую рыночную цену для входа
        # entry_price из сигнала используется только для расчета SL/TP
        sl = trade_params['sl']
        tp = trade_params['tp']
        lot_size = trade_params['lot_size']
        
        # Определяем тип ордера и текущую рыночную цену
        if direction == 'BUY':
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(instrument).ask
        elif direction == 'SELL':
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(instrument).bid
        else:
            return None
        
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": instrument,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,  # slippage
            "magic": 123456,  # magic number
            "comment": f"SMC {direction}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    
    def run_monitoring(self, log_interval=60):
        """
        Запуск мониторинга сигналов.
        
        Проверяет рынок ПОСТОЯННО (каждую секунду).
        Логи выводятся каждые log_interval секунд или при обнаружении сигнала.
        
        Args:
            log_interval: Интервал логирования в секундах (по умолчанию 60)
        """
        print("\n" + "=" * 80)
        print("LIVE MONITORING STARTED")
        print("=" * 80)
        print(f"Market Check: CONTINUOUS (every 1 second)")
        print(f"Log Interval: every {log_interval} seconds")
        print(f"Trading: {'ENABLED' if self.enable_trading else 'DISABLED (monitoring only)'}")
        print(f"Active Instruments: {', '.join(self.active_instruments)}")
        print("=" * 80)
        print("\nPress Ctrl+C to stop\n")
        
        iteration = 0
        last_log_time = time.time()
        last_prices = {inst: 0.0 for inst in self.active_instruments}
        
        try:
            while True:
                iteration += 1
                now = datetime.now()
                current_time = time.time()
                
                # Проверяем сигналы КАЖДУЮ СЕКУНДУ
                signals = self.check_signals()
                
                # Определяем нужно ли выводить лог
                should_log = (current_time - last_log_time) >= log_interval
                has_signal = any(data['signal']['valid'] for data in signals.values())
                
                # Проверяем изменение цены (больше 0.01% = интересно)
                price_changed = False
                for instrument, data in signals.items():
                    price = data['price']
                    if last_prices[instrument] > 0:
                        change_pct = abs((price - last_prices[instrument]) / last_prices[instrument]) * 100
                        if change_pct > 0.01:
                            price_changed = True
                    last_prices[instrument] = price
                
                # Логируем если: (1) время пришло, (2) есть сигнал, (3) цена изменилась
                if should_log or has_signal or (price_changed and iteration % 10 == 0):
                    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Check #{iteration}")
                    print("-" * 80)
                    
                    # Логируем открытые позиции
                    positions = self.connector.get_positions()
                    if positions:
                        print("Open Positions:")
                        for pos in positions:
                            print(f"  {pos['symbol']} {pos['type']} {pos['volume']} lots @ {pos['price_open']:.5f}, P/L: {pos['profit']:.2f}")
                    else:
                        print("No open positions")
                    print("-" * 40)
                    
                    # Выводим результаты
                    for instrument, data in signals.items():
                        signal = data['signal']
                        price = data['price']
                        time_str = data['time'].strftime('%Y-%m-%d %H:%M')
                        
                        if signal['valid']:
                            direction = signal['direction']
                            entry = signal['entry_price']
                            sl = signal['sl']
                            tp = signal['tp']
                            reason = signal.get('reason', 'N/A')
                            
                            print(f"\n🔔 [{instrument}] SIGNAL DETECTED!")
                            print(f"   Direction: {direction}")
                            print(f"   Entry: {entry:.5f}")
                            print(f"   SL: {sl:.5f}")
                            print(f"   TP: {tp:.5f}")
                            print(f"   Reason: {reason}")
                            print(f"   Current Price: {price:.5f}")
                            print(f"   Time: {time_str}")
                            
                            if self.enable_trading:
                                print(f"   [!] Executing trade...")
                                
                                # ========== GAP PROTECTION ==========
                                # Проверяем, не ушла ли цена слишком далеко от рассчитанного entry
                                gap_threshold = 0.001 if instrument == 'EURUSD' else 0.01  # 0.1% для EURUSD, 1% для XAUUSD
                                gap_pct = abs(price - entry) / entry * 100
                                
                                if gap_pct > gap_threshold:
                                    print(f"   [GAP-BLOCK] Price gap too large: {gap_pct:.2f}% (threshold: {gap_threshold:.2f}%)")
                                    print(f"   Signal entry: {entry:.5f}, Current price: {price:.5f}")
                                    continue
                                
                                print(f"   [✓] Gap check passed: {gap_pct:.2f}%")
                                
                                # Получаем текущий баланс
                                account_info = self.connector.get_account_info()
                                if account_info is None:
                                    print(f"   [EXEC-BLOCK] account_info is None")
                                    continue
                                
                                balance = account_info['balance']
                                
                                # Получаем risk_pct из config
                                risk_pct = self.portfolio_config['portfolio']['risk_per_trade']
                                
                                # Выполняем trade
                                strategy = self.strategies[instrument]
                                trade_params = strategy.execute_trade(signal, balance, risk_pct)
                                
                                if trade_params:
                                    # Преобразуем в MT5 request
                                    mt5_request = self._prepare_mt5_request(instrument, trade_params)
                                    
                                    if mt5_request:
                                        # Отправляем ордер
                                        order_result = self.connector.send_order(mt5_request)
                                        
                                        if order_result['retcode'] == 10009:  # TRADE_RETCODE_DONE
                                            print(f"   [✓] Trade executed successfully!")
                                        else:
                                            print(f"   [EXEC-BLOCK] order rejected: retcode={order_result['retcode']}, comment='{order_result['comment']}'")
                                    else:
                                        print(f"   [EXEC-BLOCK] invalid order request")
                                else:
                                    print(f"   [EXEC-BLOCK] trade_params is None")
                            else:
                                print(f"   [i] Trading disabled - signal logged only")
                        else:
                            print(f"[{instrument}] Watching... (Price: {price:.5f})")
                    
                    print("-" * 80)
                    if not has_signal:
                        print(f"Monitoring active. Next log in ~{log_interval}s (or on signal/price change)")
                    
                    last_log_time = current_time
                
                # Спим 1 секунду перед следующей проверкой
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n[!] Monitoring stopped by user")
        finally:
            self.disconnect()
    
    def disconnect(self):
        """Отключение от MT5."""
        if self.connector:
            self.connector.disconnect()
            print("[*] Disconnected from MT5")


def main():
    """Main entry point для demo торговли."""
    import argparse
    
    parser = argparse.ArgumentParser(description='BAZA Live/Demo Trader')
    parser.add_argument('--interval', type=int, default=60,
                       help='Check interval in seconds (default: 60)')
    parser.add_argument('--config-dir', type=str, default='BAZA/config',
                       help='Config directory (default: BAZA/config)')
    
    args = parser.parse_args()
    
    # Создаём трейдер
    trader = LiveTrader(config_dir=args.config_dir)
    
    # Подключаемся к MT5
    if not trader.connect_mt5():
        return
    
    # Инициализируем стратегии
    trader.initialize_strategies()
    
    # Запускаем мониторинг
    trader.run_monitoring(check_interval=args.interval)


if __name__ == "__main__":
    main()

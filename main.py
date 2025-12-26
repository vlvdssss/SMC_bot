"""
BAZA Trading Bot - Main Entry Point

Финальная версия после бэктестирования:
- XAUUSD: SMC Strategy (45.86% ROI 2024)
- EURUSD: SMC Retracement (340% ROI 2024)

Запуск:
    python main.py --mode demo      # Демо мониторинг
    python main.py --mode live      # Реальная торговля
    python main.py --mode backtest  # Бэктест
"""

import argparse
import sys
import time
import signal
import logging
from datetime import datetime, timedelta
import yaml
import os

# Импорты из проекта
from strategies.xauusd_strategy import XAUUSDStrategy
from strategies.eurusd_strategy import EURUSDStrategy
from core.data_loader import DataLoader
from core.executor import Executor
from core.broker_sim import BrokerSimulator
from mt5.connector import MT5Connector
from backtest.realistic_backtester import RealisticBacktester
from live.live_trader import LiveTrader

class BAZATradingBot:
    def __init__(self, mode='demo', start_date=None, end_date=None, instrument=None):
        self.mode = mode
        self.start_date = start_date
        self.end_date = end_date
        self.instrument = instrument
        self.running = True
        
        # Настройка логирования
        self.setup_logging()
        
        # Загрузка конфигураций
        self.load_configs()
        
        # Инициализация компонентов
        self.initialize_components()
        
        # Обработка сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Настройка логирования в файл и консоль"""
        log_filename = f"logs/baza_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('BAZA')
        self.logger.info("BAZA Trading Bot initialized")
    
    def load_configs(self):
        """Загрузка конфигурационных файлов"""
        try:
            with open('config/instruments.yaml', 'r') as f:
                self.instruments_config = yaml.safe_load(f)
            
            with open('config/portfolio.yaml', 'r') as f:
                self.portfolio_config = yaml.safe_load(f)
            
            if self.mode in ['live', 'demo']:
                with open('config/mt5.yaml', 'r') as f:
                    self.mt5_config = yaml.safe_load(f)
            
            self.logger.info("Configuration files loaded successfully")
        except FileNotFoundError as e:
            self.logger.error(f"Configuration file not found: {e}")
            sys.exit(1)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML: {e}")
            sys.exit(1)
    
    def initialize_components(self):
        """Инициализация стратегий и компонентов"""
        self.strategies = {}
        
        # Инициализация стратегий
        if self.instrument in [None, 'XAUUSD']:
            self.strategies['XAUUSD'] = XAUUSDStrategy(
                risk_percent=self.portfolio_config['instruments']['XAUUSD']['risk_percent'],
                config=self.instruments_config['XAUUSD']
            )
        
        if self.instrument in [None, 'EURUSD']:
            self.strategies['EURUSD'] = EURUSDStrategy(
                risk_percent=self.portfolio_config['instruments']['EURUSD']['risk_percent'],
                config=self.instruments_config['EURUSD']
            )
        
        # Инициализация компонентов в зависимости от режима
        if self.mode == 'backtest':
            self.data_loader = DataLoader()
            self.broker = BrokerSimulator(initial_balance=10000)
            self.backtester = RealisticBacktester(self.strategies, self.broker, self.data_loader)
        elif self.mode in ['live', 'demo']:
            self.mt5_connector = MT5Connector(self.mt5_config)
            self.executor = Executor(self.mt5_connector, self.mode == 'demo')
            self.live_trader = LiveTrader(self.strategies, self.executor, self.mt5_connector)
    
    def run_backtest(self):
        """Запуск бэктеста"""
        self.logger.info(f"Starting backtest from {self.start_date} to {self.end_date}")
        
        results = {}
        for instrument, strategy in self.strategies.items():
            self.logger.info(f"Backtesting {instrument} strategy")
            result = self.backtester.run_backtest(
                instrument=instrument,
                start_date=self.start_date,
                end_date=self.end_date
            )
            results[instrument] = result
        
        # Вывод результатов
        self.print_backtest_results(results)
    
    def run_live_demo(self):
        """Запуск live или demo режима"""
        self.logger.info(f"Starting {self.mode} trading mode")
        
        if not self.mt5_connector.connect():
            self.logger.error("Failed to connect to MT5")
            return
        
        self.live_trader.start()
        
        # Главный цикл мониторинга
        try:
            while self.running:
                time.sleep(30)  # Проверка каждые 30 секунд
                self.logger.info("Bot is running...")
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        finally:
            self.shutdown()
    
    def print_backtest_results(self, results):
        """Вывод результатов бэктеста"""
        print("\n" + "="*60)
        print("BAZA BACKTEST RESULTS")
        print("="*60)
        
        for instrument, result in results.items():
            print(f"\n{instrument} Strategy:")
            print(f"  Total Return: {result['total_return']:.2f}%")
            print(f"  Max Drawdown: {result['max_drawdown']:.2f}%")
            print(f"  Win Rate: {result['win_rate']:.1f}%")
            print(f"  Total Trades: {result['total_trades']}")
            print(f"  Profit Factor: {result['profit_factor']:.2f}")
        
        print("\n" + "="*60)
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down BAZA Trading Bot...")
        
        if hasattr(self, 'live_trader'):
            self.live_trader.stop()
        
        if hasattr(self, 'mt5_connector'):
            self.mt5_connector.disconnect()
        
        self.logger.info("Shutdown complete")
    
    def run(self):
        """Главная функция запуска"""
        if self.mode == 'backtest':
            self.run_backtest()
        elif self.mode in ['live', 'demo']:
            self.run_live_demo()
        else:
            self.logger.error(f"Unknown mode: {self.mode}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='BAZA Trading Bot')
    parser.add_argument('--mode', choices=['demo', 'live', 'backtest'], 
                       default='demo', help='Trading mode')
    parser.add_argument('--start', type=str, help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--instrument', choices=['EURUSD', 'XAUUSD'], 
                       help='Specific instrument to trade/backtest')
    
    args = parser.parse_args()
    
    # Валидация аргументов
    if args.mode == 'backtest':
        if not args.start or not args.end:
            print("Backtest mode requires --start and --end dates")
            sys.exit(1)
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    else:
        start_date = None
        end_date = None
    
    # Создание и запуск бота
    bot = BAZATradingBot(
        mode=args.mode,
        start_date=start_date,
        end_date=end_date,
        instrument=args.instrument
    )
    
    bot.run()

if __name__ == "__main__":
    main()
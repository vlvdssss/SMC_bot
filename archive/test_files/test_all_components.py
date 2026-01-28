"""
Комплексный тест всех компонентов BAZA Trading Bot
Проверяет: MT5, Settings, Bot Manager, Live Trader, GUI
"""
import sys
from pathlib import Path
import time

# Добавить корневую директорию
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import logger
from src.core.bot_manager import bot_manager
from src.core.mt5_manager import MT5Manager
from src.live.live_trader import LiveTrader
import yaml


class ComponentTester:
    """Тестер всех компонентов системы"""
    
    def __init__(self):
        self.results = {}
        
    def test_config_files(self):
        """Тест 1: Проверка конфигурационных файлов"""
        print("\n" + "="*60)
        print("TEST 1: Конфигурационные файлы")
        print("="*60)
        
        configs = {
            'MT5': 'config/mt5.yaml',
            'AI': 'config/ai.yaml',
            'Portfolio': 'config/portfolio.yaml',
            'Telegram': 'config/telegram.yaml',
            'Instruments': 'config/instruments.yaml'
        }
        
        for name, path in configs.items():
            try:
                config_path = Path(path)
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    print(f"✅ {name:12} - OK ({len(str(data))} bytes)")
                    self.results[f'config_{name}'] = True
                else:
                    print(f"❌ {name:12} - Файл не найден")
                    self.results[f'config_{name}'] = False
            except Exception as e:
                print(f"❌ {name:12} - Ошибка: {e}")
                self.results[f'config_{name}'] = False
    
    def test_mt5_manager(self):
        """Тест 2: MT5 Manager"""
        print("\n" + "="*60)
        print("TEST 2: MT5 Manager")
        print("="*60)
        
        try:
            mt5 = MT5Manager()
            print("✅ MT5Manager создан")
            
            # Проверка методов
            methods = [
                'initialize', 'connect', 'disconnect', 
                'is_connected', 'get_account_info', 
                'get_symbol_price', 'get_open_positions'
            ]
            
            for method in methods:
                if hasattr(mt5, method):
                    print(f"✅ Метод '{method}' существует")
                else:
                    print(f"❌ Метод '{method}' НЕ найден")
            
            # Проверка инициализации
            config_path = Path('config/mt5.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # Правильный путь в конфиге: mt5.connection.path
                connection = config.get('mt5', {}).get('connection', {})
                terminal_path = connection.get('path')
                
                if terminal_path and Path(terminal_path).exists():
                    if mt5.initialize(terminal_path):
                        print(f"✅ MT5 инициализирован: {terminal_path}")
                        
                        # Проверка подключения
                        login = connection.get('login')
                        password = connection.get('password')
                        server = connection.get('server')
                        
                        if login and password and server:
                            success, msg = mt5.connect(login, password, server)
                            if success:
                                print(f"✅ MT5 подключен: {msg}")
                                
                                # Тест получения цены
                                price = mt5.get_symbol_price('XAUUSD')
                                print(f"✅ Цена XAUUSD: {price}")
                                
                                # Тест информации о счете
                                account = mt5.get_account_info()
                                if account:
                                    print(f"✅ Баланс: ${account.get('balance', 0):.2f}")
                                    print(f"✅ Equity: ${account.get('equity', 0):.2f}")
                                
                                # Тест открытых позиций
                                positions = mt5.get_open_positions()
                                print(f"✅ Открытых позиций: {len(positions)}")
                                
                                self.results['mt5_manager'] = True
                            else:
                                print(f"⚠️ MT5 не подключен: {msg}")
                                self.results['mt5_manager'] = False
                        else:
                            print("⚠️ Credentials не найдены в конфиге")
                            self.results['mt5_manager'] = False
                    else:
                        print("❌ Не удалось инициализировать MT5")
                        self.results['mt5_manager'] = False
                else:
                    print(f"❌ MT5 terminal path не найден или не существует: {terminal_path}")
                    self.results['mt5_manager'] = False
            else:
                print("❌ mt5.yaml не найден")
                self.results['mt5_manager'] = False
                
        except Exception as e:
            print(f"❌ Ошибка MT5Manager: {e}")
            self.results['mt5_manager'] = False
    
    def test_bot_manager(self):
        """Тест 3: Bot Manager (Singleton)"""
        print("\n" + "="*60)
        print("TEST 3: Bot Manager")
        print("="*60)
        
        try:
            print(f"✅ BotManager: {bot_manager}")
            print(f"✅ Режим работы: {bot_manager.mode}")
            print(f"✅ Состояние: {'Running' if bot_manager.is_running else 'Stopped'}")
            
            # Проверка статистики
            stats = bot_manager.get_stats()
            print(f"✅ Всего сделок: {stats.get('total_trades', 0)}")
            print(f"✅ Прибыльных: {stats.get('winning_trades', 0)}")
            print(f"✅ Убыточных: {stats.get('losing_trades', 0)}")
            print(f"✅ Win rate: {stats.get('win_rate', 0):.1f}%")
            
            self.results['bot_manager'] = True
            
        except Exception as e:
            print(f"❌ Ошибка BotManager: {e}")
            self.results['bot_manager'] = False
    
    def test_live_trader(self):
        """Тест 4: Live Trader"""
        print("\n" + "="*60)
        print("TEST 4: Live Trader")
        print("="*60)
        
        try:
            # Создаём LiveTrader с правильными параметрами
            trader = LiveTrader(config_dir='config', enable_trading=False, enable_gpt=True)
            
            print(f"✅ LiveTrader создан")
            print(f"✅ Config dir: {trader.config_dir}")
            print(f"✅ Trading enabled: {trader.enable_trading}")
            print(f"✅ GPT enabled: {trader.enable_gpt}")
            
            # Проверка методов
            methods = ['check_signals', 'process_signal', 'close_position']
            for method in methods:
                if hasattr(trader, method):
                    print(f"✅ Метод '{method}' существует")
                else:
                    print(f"⚠️ Метод '{method}' не найден")
            
            # Проверка AI Signal Manager
            if hasattr(trader, 'ai_signal_manager') and trader.ai_signal_manager:
                print(f"✅ AI Signal Manager активен")
            else:
                print(f"⚠️ AI Signal Manager не активен")
            
            self.results['live_trader'] = True
            
        except Exception as e:
            print(f"❌ Ошибка LiveTrader: {e}")
            import traceback
            traceback.print_exc()
            self.results['live_trader'] = False
    
    def test_telegram(self):
        """Тест 5: Telegram уведомления"""
        print("\n" + "="*60)
        print("TEST 5: Telegram Bot")
        print("="*60)
        
        try:
            from src.monitoring.telegram_notifier import TelegramNotifier
            
            # Загружаем конфиг
            config_path = Path('config/telegram.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                telegram_config = config.get('telegram', {})
                
                # Создаём экземпляр
                notifier = TelegramNotifier(
                    token=telegram_config.get('bot_token'),
                    chat_id=telegram_config.get('chat_id')
                )
                
                if notifier.enabled:
                    print(f"✅ Telegram notifications: ENABLED")
                    print(f"✅ Bot token: {notifier.token[:20]}...")
                    print(f"✅ Chat ID: {notifier.chat_id}")
                    
                    # Проверка уведомлений
                    notify = telegram_config.get('notify', {})
                    print(f"✅ Startup: {notify.get('startup', False)}")
                    print(f"✅ Trade opened: {notify.get('trade_opened', False)}")
                    print(f"✅ Trade closed: {notify.get('trade_closed', False)}")
                    print(f"✅ Daily report: {notify.get('daily_report', False)}")
                    print(f"✅ Alerts: {notify.get('alerts', False)}")
                    
                    self.results['telegram'] = True
                else:
                    print("⚠️ Telegram notifications: DISABLED (нет токена/chat_id)")
                    self.results['telegram'] = False
            else:
                print("❌ telegram.yaml не найден")
                self.results['telegram'] = False
                
        except Exception as e:
            print(f"❌ Ошибка Telegram: {e}")
            import traceback
            traceback.print_exc()
            self.results['telegram'] = False
    
    def test_gui_components(self):
        """Тест 6: GUI компоненты"""
        print("\n" + "="*60)
        print("TEST 6: GUI Components")
        print("="*60)
        
        try:
            # Проверка основных файлов GUI
            gui_files = {
                'Main App': 'src/gui/app.py',
                'Settings Dialog': 'src/gui/settings_dialog.py',
                'MT5 Dialog': 'src/gui/mt5_dialog.py'
            }
            
            for name, path in gui_files.items():
                if Path(path).exists():
                    size = Path(path).stat().st_size
                    # Проверка классов внутри app.py
                    if name == 'Main App':
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            classes = ['HeaderPanel', 'ControlPanel', 'StatsPanel', 'AnalystPanel']
                            for cls in classes:
                                if f'class {cls}' in content:
                                    print(f"✅ {cls:18} - найден в app.py")
                    print(f"✅ {name:18} - {size} bytes")
                else:
                    print(f"❌ {name:18} - НЕ найден")
            
            self.results['gui_components'] = True
            
        except Exception as e:
            print(f"❌ Ошибка GUI: {e}")
            self.results['gui_components'] = False
    
    def test_ai_components(self):
        """Тест 7: AI компоненты"""
        print("\n" + "="*60)
        print("TEST 7: AI Components")
        print("="*60)
        
        try:
            # Проверка AI модулей
            ai_modules = {
                'Market Analyst': 'src/ai/market_analyst.py',
                'Screenshot Analyzer': 'src/ai/screenshot_analyzer.py',
                'Signal Manager': 'src/ai/ai_signal_manager.py',
                'GPT Client': 'src/ai/gpt_client.py'
            }
            
            for name, path in ai_modules.items():
                if Path(path).exists():
                    print(f"✅ {name:20} - OK")
                else:
                    print(f"❌ {name:20} - НЕ найден")
            
            # Проверка GPT API key
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                print(f"✅ OpenAI API Key: {api_key[:15]}...")
            else:
                print(f"⚠️ OpenAI API Key: НЕ установлен")
            
            # Проверка директорий с данными
            data_dirs = {
                'AI Analysis': 'data/ai_analysis',
                'AI Signals': 'data/ai_signals',
                'Screenshots': 'data/screenshots'
            }
            
            for name, path in data_dirs.items():
                dir_path = Path(path)
                if dir_path.exists():
                    files = list(dir_path.glob('*'))
                    print(f"✅ {name:15} - {len(files)} файлов")
                else:
                    print(f"❌ {name:15} - НЕ найдена")
            
            self.results['ai_components'] = True
            
        except Exception as e:
            print(f"❌ Ошибка AI: {e}")
            self.results['ai_components'] = False
    
    def print_summary(self):
        """Итоговая сводка"""
        print("\n" + "="*60)
        print("ИТОГОВАЯ СВОДКА")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        failed = total - passed
        
        print(f"\nВсего тестов: {total}")
        print(f"✅ Пройдено: {passed}")
        print(f"❌ Провалено: {failed}")
        print(f"Успешность: {(passed/total*100) if total > 0 else 0:.1f}%")
        
        print("\nДетальные результаты:")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {test_name}")


def main():
    """Главная функция тестирования"""
    print("\n" + "="*60)
    print("BAZA TRADING BOT - КОМПЛЕКСНЫЙ ТЕСТ СИСТЕМЫ")
    print("="*60)
    print(f"Время запуска: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = ComponentTester()
    
    # Запуск всех тестов
    tester.test_config_files()
    tester.test_mt5_manager()
    tester.test_bot_manager()
    tester.test_live_trader()
    tester.test_telegram()
    tester.test_gui_components()
    tester.test_ai_components()
    
    # Итоги
    tester.print_summary()
    
    print("\n" + "="*60)
    print("Тестирование завершено!")
    print("="*60)


if __name__ == "__main__":
    main()

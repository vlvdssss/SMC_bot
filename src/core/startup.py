"""
Startup - инициализация при запуске EXE
"""
import sys
from pathlib import Path
import yaml
import shutil


def init_exe_environment():
    """Инициализация окружения для EXE"""
    
    # Определить базовую директорию
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent.parent
    
    print(f"Base directory: {base_dir}")
    
    # Создать необходимые директории
    folders = [
        'config',
        'data',
        'logs',
        'models',
        'results',
        'data/ai_analysis',
        'data/ai_signals',
        'data/backtest',
        'data/screenshots'
    ]
    
    for folder in folders:
        folder_path = base_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {folder_path}")
    
    # Создать пустые конфиги если их нет
    config_dir = base_dir / 'config'
    
    # mt5.yaml
    mt5_config = config_dir / 'mt5.yaml'
    if not mt5_config.exists():
        default_mt5 = {
            'mt5': {
                'connection': {
                    'login': 0,
                    'password': '',
                    'server': 'MetaQuotes-Demo',
                    'path': 'C:/Program Files/MetaTrader 5/terminal64.exe',
                    'timeout': 10000
                },
                'settings': {
                    'enable_trade': True,
                    'max_retries': 3,
                    'retry_delay': 5,
                    'check_connection_interval': 60
                },
                'safety': {
                    'max_lot_size': 1.0,
                    'max_open_positions': 4,
                    'max_daily_trades': 10,
                    'max_daily_loss_percent': 5.0,
                    'max_total_risk_percent': 2.0
                },
                'symbols': {
                    'XAUUSD': {
                        'enabled': True,
                        'min_lot': 0.01,
                        'max_lot': 0.5,
                        'lot_step': 0.01
                    },
                    'EURUSD': {
                        'enabled': True,
                        'min_lot': 0.01,
                        'max_lot': 1.0,
                        'lot_step': 0.01
                    }
                },
                'mode': {
                    'current': 'demo',
                    'demo_account': 0,
                    'live_account': None
                }
            },
            'logging': {
                'level': 'INFO',
                'log_trades': True,
                'log_connections': True,
                'log_errors': True,
                'save_to_file': True,
                'log_file': 'logs/mt5_operations.log'
            }
        }
        
        with open(mt5_config, 'w', encoding='utf-8') as f:
            yaml.dump(default_mt5, f, default_flow_style=False, allow_unicode=True)
        print(f"Created: {mt5_config}")
    
    # telegram.yaml
    telegram_config = config_dir / 'telegram.yaml'
    if not telegram_config.exists():
        default_telegram = {
            'telegram': {
                'bot_token': '',
                'chat_id': '',
                'enabled': False,
                'enable_bot': False,
                'notify': {
                    'startup': True,
                    'trade_opened': True,
                    'trade_closed': True,
                    'daily_report': True,
                    'alerts': True
                },
                'alert_level': 'WARNING'
            }
        }
        
        with open(telegram_config, 'w', encoding='utf-8') as f:
            yaml.dump(default_telegram, f, default_flow_style=False, allow_unicode=True)
        print(f"Created: {telegram_config}")
    
    # ai.yaml
    ai_config = config_dir / 'ai.yaml'
    if not ai_config.exists():
        default_ai = {
            'openai': {
                'api_key': '',
                'model': 'gpt-4',
                'max_tokens': 2000,
                'temperature': 0.7
            },
            'market_analyst': {
                'enabled': True,
                'interval_minutes': 30,
                'schedule': {
                    'times': ['09:00', '12:00', '15:00', '18:00'],
                    'restrictions': {
                        'night_block': {
                            'enabled': True,
                            'start': '22:00',
                            'end': '02:00'
                        },
                        'weekend_block': {
                            'enabled': True
                        }
                    }
                }
            }
        }
        
        with open(ai_config, 'w', encoding='utf-8') as f:
            yaml.dump(default_ai, f, default_flow_style=False, allow_unicode=True)
        print(f"Created: {ai_config}")
    
    # portfolio.yaml
    portfolio_config = config_dir / 'portfolio.yaml'
    if not portfolio_config.exists():
        default_portfolio = {
            'portfolio': {
                'risk_model': {
                    'max_total_exposure': 1.25,
                    'single_position_risk': 0.02,
                    'max_daily_risk': 0.05
                }
            }
        }
        
        with open(portfolio_config, 'w', encoding='utf-8') as f:
            yaml.dump(default_portfolio, f, default_flow_style=False, allow_unicode=True)
        print(f"Created: {portfolio_config}")
    
    # instruments.yaml
    instruments_config = config_dir / 'instruments.yaml'
    if not instruments_config.exists():
        default_instruments = {
            'instruments': {
                'XAUUSD': {
                    'enabled': True,
                    'type': 'metals'
                },
                'EURUSD': {
                    'enabled': True,
                    'type': 'forex'
                }
            }
        }
        
        with open(instruments_config, 'w', encoding='utf-8') as f:
            yaml.dump(default_instruments, f, default_flow_style=False, allow_unicode=True)
        print(f"Created: {instruments_config}")
    
    # Создать .env если нет
    env_file = base_dir / '.env'
    if not env_file.exists():
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('# OpenAI API Key\n')
            f.write('OPENAI_API_KEY=\n')
        print(f"Created: {env_file}")
    
    print("✓ Initialization complete!")
    return base_dir

#!/usr/bin/env python3
"""
Credentials Loader - загружает чувствительные данные из config/ai.yaml или .env

Приоритет загрузки:
1. config/ai.yaml (gpt.api_key)
2. .env файл в корне проекта
3. Переменные окружения (OPENAI_API_KEY)
4. (опционально) C:\\Users\\kamsa\\Desktop\\baza_credentials.txt
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional
from src.core.logger import logger


class CredentialsLoader:
    """Загрузчик credentials из config файлов."""
    
    # Опциональный внешний файл (для обратной совместимости)
    CREDENTIALS_PATH = Path(r"C:\Users\kamsa\Desktop\baza_credentials.txt")
    
    # Путь к config/ai.yaml
    AI_CONFIG_PATH = Path("config/ai.yaml")
    
    # Путь к .env файлу
    ENV_PATH = Path(".env")
    
    @classmethod
    def load(cls) -> Dict[str, str]:
        """
        Загрузить credentials из config/ai.yaml, .env или переменных окружения.
        
        Приоритет:
        1. config/ai.yaml (поле gpt.api_key)
        2. .env файл
        3. Переменные окружения
        4. (опционально) baza_credentials.txt
        
        Returns:
            Dict с ключами: OPENAI_API_KEY, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, 
            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        """
        credentials = {}
        sources_used = []
        
        # 1. Проверяем config/ai.yaml (ПРИОРИТЕТ)
        if cls.AI_CONFIG_PATH.exists():
            try:
                with open(cls.AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    ai_config = yaml.safe_load(f)
                
                # Проверяем gpt.api_key
                api_key = ai_config.get('market_analyst', {}).get('gpt', {}).get('api_key')
                if api_key and api_key != 'YOUR_OPENAI_API_KEY_HERE':
                    credentials['OPENAI_API_KEY'] = api_key
                    sources_used.append('ai.yaml')
                    
            except Exception as e:
                logger.debug(f"[Credentials] Could not load from ai.yaml: {e}")
        
        # 2. Проверяем .env файл
        if cls.ENV_PATH.exists():
            try:
                with open(cls.ENV_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            # Убираем кавычки, пробелы и escape-последовательности (\n, \r, \t)
                            value = value.strip().strip('"').strip("'")
                            value = value.replace('\\n', '').replace('\\r', '').replace('\\t', '').strip()
                            
                            # Добавляем только если еще не загружено и значение не пустое
                            if value and value != 'YOUR_WORKING_API_KEY_HERE' and key not in credentials:
                                credentials[key] = value
                                if '.env' not in sources_used:
                                    sources_used.append('.env')
            except Exception as e:
                logger.debug(f"[Credentials] Could not load from .env: {e}")
        
        # 3. Проверяем переменные окружения
        env_keys = ['OPENAI_API_KEY', 'MT5_LOGIN', 'MT5_PASSWORD', 'MT5_SERVER',
                   'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        
        for key in env_keys:
            if key not in credentials:
                env_value = os.getenv(key)
                if env_value:
                    credentials[key] = env_value
                    if 'env_vars' not in sources_used:
                        sources_used.append('env_vars')
        
        # 4. (опционально) Проверяем внешний credentials файл
        if cls.CREDENTIALS_PATH.exists():
            try:
                with open(cls.CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Добавляем только если еще не загружено
                            if value and key not in credentials:
                                credentials[key] = value
                                if 'credentials.txt' not in sources_used:
                                    sources_used.append('credentials.txt')
            except Exception as e:
                logger.debug(f"[Credentials] Could not load from credentials.txt: {e}")
        
        # Логируем результаты
        if credentials:
            logger.info(f"[Credentials] ✅ Loaded from: {', '.join(sources_used)}")
            loaded_keys = [k for k in credentials.keys()]
            logger.info(f"[Credentials] Keys: {', '.join(loaded_keys)}")
        else:
            logger.warning("[Credentials] ⚠️ No credentials loaded from any source")
        
        return credentials
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Получить конкретный credential.
        
        Args:
            key: Имя ключа (OPENAI_API_KEY, MT5_LOGIN, и т.д.)
            default: Значение по умолчанию если ключ не найден
            
        Returns:
            Значение credential или default
        """
        credentials = cls.load()
        return credentials.get(key, default)


# Глобальная функция для удобства
def get_credential(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Получить credential из внешнего файла.
    
    Args:
        key: OPENAI_API_KEY, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, 
             TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        default: Значение по умолчанию
        
    Returns:
        Значение credential
    """
    return CredentialsLoader.get(key, default)

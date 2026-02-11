#!/usr/bin/env python3
"""
Credentials Loader - загружает чувствительные данные из файла на рабочем столе.

Файл credentials находится по пути: C:\\Users\\kamsa\\Desktop\\baza_credentials.txt
"""

import os
from pathlib import Path
from typing import Dict, Optional
from src.core.logger import logger


class CredentialsLoader:
    """Загрузчик credentials из внешнего файла."""
    
    CREDENTIALS_PATH = Path(r"C:\Users\kamsa\Desktop\baza_credentials.txt")
    
    @classmethod
    def load(cls) -> Dict[str, str]:
        """
        Загрузить credentials из файла.
        
        Returns:
            Dict с ключами: OPENAI_API_KEY, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, 
            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        """
        credentials = {}
        
        if not cls.CREDENTIALS_PATH.exists():
            logger.warning(
                f"[Credentials] File not found: {cls.CREDENTIALS_PATH}\n"
                f"Please create this file with your credentials!"
            )
            return credentials
        
        try:
            with open(cls.CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Пропускаем комментарии и пустые строки
                    if not line or line.startswith('#'):
                        continue
                    
                    # Парсим KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if value and value != 'YOUR_OPENAI_API_KEY_HERE':
                            credentials[key] = value
            
            logger.info(
                f"[Credentials] ✅ Loaded {len(credentials)} credentials from external file"
            )
            
            # Показываем какие ключи загружены (но не сами значения!)
            loaded_keys = list(credentials.keys())
            logger.info(f"[Credentials] Keys: {', '.join(loaded_keys)}")
            
        except Exception as e:
            logger.error(f"[Credentials] Failed to load: {e}")
        
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

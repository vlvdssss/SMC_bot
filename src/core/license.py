"""
Система лицензирования BAZA Trading Bot.

Простая проверка ключа активации.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
import os


class LicenseManager:
    """Менеджер лицензий."""
    
    LICENSE_FILE = 'data/license.json'
    
    # Захардкоженные ключи (можешь добавить свои)
    VALID_KEYS = {
        'BAZA-FREE-2025': {'type': 'free', 'days': 30},
        'BAZA-PRO-OWNER': {'type': 'pro', 'days': 36500},  # 100 лет = навсегда
        'BAZA-DEMO-TEST': {'type': 'demo', 'days': 7},
    }
    
    def __init__(self):
        self.license_data = None
        self.load_license()
    
    def load_license(self):
        """Загрузка лицензии из файла."""
        license_path = Path(self.LICENSE_FILE)
        
        if license_path.exists():
            try:
                with open(license_path, 'r') as f:
                    self.license_data = json.load(f)
            except:
                self.license_data = None
    
    def save_license(self, key: str, license_type: str, expires: str):
        """Сохранение лицензии."""
        license_path = Path(self.LICENSE_FILE)
        license_path.parent.mkdir(exist_ok=True)
        
        self.license_data = {
            'key': key,
            'type': license_type,
            'activated': datetime.now().isoformat(),
            'expires': expires
        }
        
        with open(license_path, 'w') as f:
            json.dump(self.license_data, f, indent=2)
    
    def activate(self, key: str) -> tuple[bool, str]:
        """
        Активация ключа.
        
        Returns:
            (success: bool, message: str)
        """
        key = key.strip().upper()
        
        # Проверяем ключ
        if key not in self.VALID_KEYS:
            return (False, "❌ Неверный ключ активации")
        
        key_info = self.VALID_KEYS[key]
        expires = datetime.now() + timedelta(days=key_info['days'])
        
        self.save_license(key, key_info['type'], expires.isoformat())
        
        return (True, f"✅ Активировано! Тип: {key_info['type'].upper()}, до {expires.strftime('%d.%m.%Y')}")
    
    def is_valid(self) -> tuple[bool, str]:
        """
        Проверка валидности лицензии.
        
        Returns:
            (valid: bool, message: str)
        """
        if not self.license_data:
            return (False, "Требуется активация")
        
        try:
            expires = datetime.fromisoformat(self.license_data['expires'])
            
            if datetime.now() > expires:
                return (False, "Лицензия истекла")
            
            days_left = (expires - datetime.now()).days
            license_type = self.license_data.get('type', 'unknown')
            
            return (True, f"{license_type.upper()} | Осталось {days_left} дней")
            
        except Exception as e:
            return (False, f"Ошибка лицензии: {e}")
    
    def get_license_info(self) -> dict:
        """Информация о лицензии."""
        if not self.license_data:
            return {'valid': False, 'type': None, 'expires': None}
        
        try:
            expires = datetime.fromisoformat(self.license_data['expires'])
            return {
                'valid': datetime.now() < expires,
                'type': self.license_data.get('type'),
                'expires': expires.strftime('%d.%m.%Y'),
                'days_left': (expires - datetime.now()).days
            }
        except:
            return {'valid': False, 'type': None, 'expires': None}


# Глобальный инстанс
license_manager = LicenseManager()
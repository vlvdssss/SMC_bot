"""
Update Checker - проверка версий и доступных обновлений
"""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from packaging import version
import logging

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Проверка обновлений с GitHub"""
    
    def __init__(self, current_version: str, version_url: str):
        """
        Args:
            current_version: Текущая версия приложения (например, "1.0.0")
            version_url: URL к version.json на GitHub
        """
        self.current_version = current_version
        self.version_url = version_url
        
    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Проверить наличие обновлений
        
        Returns:
            Dict с информацией об обновлении или None, если обновлений нет
            {
                'latest_version': '1.1.0',
                'download_url': 'https://...',
                'size_mb': 38,
                'changelog': ['...', '...']
            }
        """
        try:
            # Скачиваем version.json с GitHub
            logger.info(f"Checking for updates from: {self.version_url}")
            
            with urllib.request.urlopen(self.version_url, timeout=10) as response:
                data = response.read()
                version_info = json.loads(data.decode('utf-8'))
            
            latest_version = version_info.get('latest_version')
            
            if not latest_version:
                logger.error("latest_version not found in version.json")
                return None
            
            # Сравниваем версии
            if self._is_newer_version(latest_version):
                logger.info(f"New version available: {latest_version} (current: {self.current_version})")
                return version_info
            else:
                logger.info(f"Already on latest version: {self.current_version}")
                return None
                
        except urllib.error.URLError as e:
            logger.error(f"Failed to check for updates (network error): {e}")
            raise ConnectionError(f"Не удалось подключиться к серверу обновлений: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse version.json: {e}")
            raise ValueError(f"Неверный формат файла обновлений: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while checking updates: {e}")
            raise RuntimeError(f"Ошибка при проверке обновлений: {e}")
    
    def _is_newer_version(self, latest_version: str) -> bool:
        """
        Проверить, является ли latest_version новее текущей
        
        Args:
            latest_version: Версия для сравнения
            
        Returns:
            True, если latest_version новее
        """
        try:
            current = version.parse(self.current_version)
            latest = version.parse(latest_version)
            return latest > current
        except Exception as e:
            logger.warning(f"Failed to parse versions, falling back to string comparison: {e}")
            # Fallback на строковое сравнение
            return latest_version != self.current_version

"""
Update Downloader - загрузка обновлений с прогресс-баром
"""

import os
import urllib.request
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class UpdateDownloader:
    """Загрузчик обновлений"""
    
    def __init__(self, download_url: str, destination_path: str):
        """
        Args:
            download_url: URL файла обновления
            destination_path: Путь для сохранения (например, 'app_update.exe')
        """
        self.download_url = download_url
        self.destination_path = destination_path
        self._cancel_flag = False
        
    def download(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Скачать файл обновления
        
        Args:
            progress_callback: Функция для отображения прогресса (downloaded_bytes, total_bytes)
            
        Returns:
            True, если загрузка успешна
        """
        try:
            logger.info(f"Starting download from: {self.download_url}")
            logger.info(f"Destination: {self.destination_path}")
            
            # Создаем директорию, если не существует
            os.makedirs(os.path.dirname(self.destination_path) or '.', exist_ok=True)
            
            # Открываем соединение
            with urllib.request.urlopen(self.download_url, timeout=30) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                logger.info(f"File size: {total_size / (1024*1024):.2f} MB")
                
                downloaded = 0
                chunk_size = 8192  # 8 KB chunks
                
                # Скачиваем файл по частям
                with open(self.destination_path, 'wb') as f:
                    while not self._cancel_flag:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Вызываем callback для обновления прогресса
                        if progress_callback:
                            progress_callback(downloaded, total_size)
                
                # Проверяем, была ли отменена загрузка
                if self._cancel_flag:
                    logger.warning("Download cancelled by user")
                    # Удаляем частично загруженный файл
                    if os.path.exists(self.destination_path):
                        os.remove(self.destination_path)
                    return False
                
                logger.info(f"Download completed: {downloaded / (1024*1024):.2f} MB")
                return True
                
        except urllib.error.URLError as e:
            logger.error(f"Download failed (network error): {e}")
            # Удаляем частично загруженный файл
            if os.path.exists(self.destination_path):
                os.remove(self.destination_path)
            raise ConnectionError(f"Ошибка загрузки: {e}")
        except Exception as e:
            logger.error(f"Download failed (unexpected error): {e}")
            # Удаляем частично загруженный файл
            if os.path.exists(self.destination_path):
                os.remove(self.destination_path)
            raise RuntimeError(f"Непредвиденная ошибка при загрузке: {e}")
    
    def cancel(self):
        """Отменить загрузку"""
        logger.info("Cancelling download...")
        self._cancel_flag = True

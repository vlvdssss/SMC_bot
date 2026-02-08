"""
Cleanup Service - Автоматическая очистка старых данных
Очищает:
- AI сигналы старше 36 часов (в 22:00 каждый день)
- Скриншоты старше 3 дней (в 22:00 каждый день)
- Логи старше 7 дней 20 часов (в 22:00 раз в неделю)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import threading
import time
import yaml


class CleanupService:
    """Сервис автоматической очистки старых данных"""
    
    def __init__(self, config: Dict = None):
        """
        Args:
            config: Конфигурация очистки (если None - загружается из config/cleanup.yaml)
        """
        self.logger = logging.getLogger(__name__)
        
        # Загружаем конфигурацию
        if config is None:
            config = self._load_config()
        
        # Конфигурация по умолчанию
        self.config = config or {
            'signals': {
                'max_age_hours': 36,  # Сигналы старше 36 часов удаляются
                'cleanup_time': '22:00'  # Время очистки каждый день
            },
            'logs': {
                'max_age_days': 7,  # 7 дней
                'max_age_hours': 20,  # + 20 часов = 7 дней 20 часов
                'cleanup_time': '22:00',  # Время очистки
                'cleanup_day': 0  # 0=Monday, день недели для очистки
            },
            'screenshots': {
                'max_age_days': 3,  # Скриншоты старше 3 дней удаляются
                'cleanup_time': '22:00'  # Время очистки каждый день
            }
        }
        
        # Пути к данным
        self.signals_dir = Path('data/ai_signals')
        self.logs_dir = Path('logs')
        self.screenshots_dir = Path('data/screenshots')
        
        # Фоновый поток
        self._cleanup_thread = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Время последней очистки
        self._last_signals_cleanup = None
        self._last_screenshots_cleanup = None
        self._last_logs_cleanup = None
        
        self.logger.info("🧹 Cleanup Service initialized")
        self.logger.info(f"   Signals: delete after {self.config['signals']['max_age_hours']}h")
        self.logger.info(f"   Screenshots: delete after {self.config['screenshots']['max_age_days']}d")
        self.logger.info(f"   Logs: delete after {self.config['logs']['max_age_days']}d {self.config['logs']['max_age_hours']}h")
    
    def _load_config(self) -> Dict:
        """Загрузка конфигурации из config/cleanup.yaml"""
        try:
            config_path = Path('config/cleanup.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"✅ Loaded cleanup config from {config_path}")
                return config
            else:
                self.logger.warning(f"⚠️ Config not found: {config_path}, using defaults")
                return None
        except Exception as e:
            self.logger.error(f"❌ Failed to load config: {e}")
            return None
    
    def start(self):
        """Запустить фоновый процесс очистки"""
        if self._running:
            self.logger.warning("Cleanup service already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True, name="CleanupService")
        self._cleanup_thread.start()
        self.logger.info("✅ Cleanup service started")
    
    def stop(self):
        """Остановить фоновый процесс"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        self.logger.info("🛑 Cleanup service stopped")
    
    def _cleanup_loop(self):
        """Основной цикл проверки времени очистки"""
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                
                # Проверяем время для очистки сигналов (каждый день в 22:00)
                if current_time == self.config['signals']['cleanup_time']:
                    if not self._last_signals_cleanup or \
                       (now - self._last_signals_cleanup).total_seconds() > 3600:  # Не чаще раза в час
                        self.logger.info("🕐 Time for signals cleanup: 22:00")
                        self.cleanup_old_signals()
                        self._last_signals_cleanup = now
                
                # Проверяем время для очистки скриншотов (каждый день в 22:00)
                if current_time == self.config['screenshots']['cleanup_time']:
                    if not self._last_screenshots_cleanup or \
                       (now - self._last_screenshots_cleanup).total_seconds() > 3600:  # Не чаще раза в час
                        self.logger.info("🕐 Time for screenshots cleanup: 22:00")
                        self.cleanup_old_screenshots()
                        self._last_screenshots_cleanup = now
                
                # Проверяем время для очистки логов (раз в неделю в понедельник в 22:00)
                if now.weekday() == self.config['logs']['cleanup_day'] and \
                   current_time == self.config['logs']['cleanup_time']:
                    if not self._last_logs_cleanup or \
                       (now - self._last_logs_cleanup).total_seconds() > 86400:  # Не чаще раза в сутки
                        self.logger.info("🕐 Time for logs cleanup: Monday 22:00")
                        self.cleanup_old_logs()
                        self._last_logs_cleanup = now
                
                # Спим 60 секунд
                self._stop_event.wait(60)
                
            except Exception as e:
                self.logger.error(f"❌ Error in cleanup loop: {e}", exc_info=True)
                self._stop_event.wait(60)
    
    def cleanup_old_signals(self) -> Dict:
        """
        Очистка старых AI сигналов (старше 36 часов)
        
        Returns:
            Статистика очистки
        """
        stats = {
            'deleted_active': 0,
            'deleted_history': 0,
            'total_deleted': 0,
            'errors': []
        }
        
        try:
            max_age = timedelta(hours=self.config['signals']['max_age_hours'])
            cutoff_time = datetime.now() - max_age
            
            self.logger.info(f"🧹 Starting signals cleanup (older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 1. Очистка active_signals.json
            active_file = self.signals_dir / 'active_signals.json'
            if active_file.exists():
                try:
                    with open(active_file, 'r', encoding='utf-8') as f:
                        active_signals = json.load(f)
                    
                    # Фильтруем старые сигналы
                    original_count = len(active_signals)
                    filtered_signals = []
                    
                    for signal in active_signals:
                        created_at_str = signal.get('created_at', '')
                        try:
                            created_at = datetime.fromisoformat(created_at_str)
                            if created_at >= cutoff_time:
                                filtered_signals.append(signal)
                            else:
                                stats['deleted_active'] += 1
                                self.logger.debug(f"   Deleted active signal: {signal.get('id', 'N/A')} (age: {datetime.now() - created_at})")
                        except (ValueError, TypeError, KeyError) as e:
                            # Если не можем распарсить дату - удаляем на всякий случай
                            self.logger.debug(f"   Could not parse signal date: {e}")
                            stats['deleted_active'] += 1
                    
                    # Сохраняем обратно
                    if stats['deleted_active'] > 0:
                        with open(active_file, 'w', encoding='utf-8') as f:
                            json.dump(filtered_signals, f, indent=2, ensure_ascii=False)
                        self.logger.info(f"   ✅ Deleted {stats['deleted_active']} active signals ({original_count} → {len(filtered_signals)})")
                    
                except Exception as e:
                    error_msg = f"Error cleaning active_signals.json: {e}"
                    self.logger.error(f"   ❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            # 2. Очистка signal_history (все JSON файлы)
            history_dir = self.signals_dir
            if history_dir.exists():
                for json_file in history_dir.glob('*.json'):
                    if json_file.name == 'active_signals.json':
                        continue  # Уже обработали
                    
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            history = json.load(f)
                        
                        if isinstance(history, list):
                            original_count = len(history)
                            filtered_history = []
                            
                            for entry in history:
                                timestamp_str = entry.get('timestamp', '')
                                try:
                                    timestamp = datetime.fromisoformat(timestamp_str)
                                    if timestamp >= cutoff_time:
                                        filtered_history.append(entry)
                                    else:
                                        stats['deleted_history'] += 1
                                except (ValueError, TypeError, KeyError) as e:
                                    # Если не можем распарсить - удаляем
                                    self.logger.debug(f"   Could not parse history timestamp: {e}")
                                    stats['deleted_history'] += 1
                            
                            # Если удалили что-то - перезаписываем файл
                            if len(filtered_history) < original_count:
                                with open(json_file, 'w', encoding='utf-8') as f:
                                    json.dump(filtered_history, f, indent=2, ensure_ascii=False)
                                deleted = original_count - len(filtered_history)
                                self.logger.info(f"   ✅ Deleted {deleted} entries from {json_file.name}")
                            
                            # Если файл пустой - удаляем его
                            if len(filtered_history) == 0:
                                json_file.unlink()
                                self.logger.info(f"   🗑️ Deleted empty file: {json_file.name}")
                    
                    except Exception as e:
                        error_msg = f"Error cleaning {json_file.name}: {e}"
                        self.logger.error(f"   ❌ {error_msg}")
                        stats['errors'].append(error_msg)
            
            stats['total_deleted'] = stats['deleted_active'] + stats['deleted_history']
            
            if stats['total_deleted'] > 0:
                self.logger.info(f"✅ Signals cleanup complete: {stats['total_deleted']} signals deleted")
            else:
                self.logger.info("✅ Signals cleanup complete: no old signals found")
            
        except Exception as e:
            error_msg = f"Critical error in cleanup_old_signals: {e}"
            self.logger.error(f"❌ {error_msg}", exc_info=True)
            stats['errors'].append(error_msg)
        
        return stats
    
    def cleanup_old_logs(self) -> Dict:
        """
        Очистка старых логов (старше 7 дней 20 часов)
        
        Returns:
            Статистика очистки
        """
        stats = {
            'deleted_files': 0,
            'deleted_size_mb': 0.0,
            'errors': []
        }
        
        try:
            # 7 дней 20 часов = 7*24 + 20 = 188 часов
            max_age_hours = self.config['logs']['max_age_days'] * 24 + self.config['logs']['max_age_hours']
            max_age = timedelta(hours=max_age_hours)
            cutoff_time = datetime.now() - max_age
            
            self.logger.info(f"🧹 Starting logs cleanup (older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
            self.logger.info(f"   Max age: {self.config['logs']['max_age_days']}d {self.config['logs']['max_age_hours']}h")
            
            if not self.logs_dir.exists():
                self.logger.warning(f"   Logs directory not found: {self.logs_dir}")
                return stats
            
            # Проходим по всем лог-файлам
            for log_file in self.logs_dir.glob('*.log'):
                try:
                    # Проверяем время модификации файла
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        # Файл старый - удаляем
                        file_size_mb = log_file.stat().st_size / (1024 * 1024)
                        log_file.unlink()
                        
                        stats['deleted_files'] += 1
                        stats['deleted_size_mb'] += file_size_mb
                        
                        self.logger.info(f"   🗑️ Deleted: {log_file.name} ({file_size_mb:.2f} MB, age: {datetime.now() - file_mtime})")
                
                except Exception as e:
                    error_msg = f"Error deleting {log_file.name}: {e}"
                    self.logger.error(f"   ❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            # Также удаляем старые .txt файлы в logs/
            for txt_file in self.logs_dir.glob('*.txt'):
                try:
                    file_mtime = datetime.fromtimestamp(txt_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_size_mb = txt_file.stat().st_size / (1024 * 1024)
                        txt_file.unlink()
                        
                        stats['deleted_files'] += 1
                        stats['deleted_size_mb'] += file_size_mb
                        
                        self.logger.info(f"   🗑️ Deleted: {txt_file.name} ({file_size_mb:.2f} MB)")
                
                except Exception as e:
                    error_msg = f"Error deleting {txt_file.name}: {e}"
                    self.logger.error(f"   ❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            if stats['deleted_files'] > 0:
                self.logger.info(f"✅ Logs cleanup complete: {stats['deleted_files']} files deleted ({stats['deleted_size_mb']:.2f} MB freed)")
            else:
                self.logger.info("✅ Logs cleanup complete: no old logs found")
        
        except Exception as e:
            error_msg = f"Critical error in cleanup_old_logs: {e}"
            self.logger.error(f"❌ {error_msg}", exc_info=True)
            stats['errors'].append(error_msg)
        
        return stats
    
    def cleanup_old_screenshots(self) -> Dict:
        """
        Очистка старых скриншотов (старше 3 дней)
        
        Returns:
            Статистика очистки
        """
        stats = {
            'deleted_files': 0,
            'deleted_size_mb': 0.0,
            'errors': []
        }
        
        try:
            max_age = timedelta(days=self.config['screenshots']['max_age_days'])
            cutoff_time = datetime.now() - max_age
            
            self.logger.info(f"🧹 Starting screenshots cleanup (older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
            self.logger.info(f"   Max age: {self.config['screenshots']['max_age_days']} days")
            
            if not self.screenshots_dir.exists():
                self.logger.warning(f"   Screenshots directory not found: {self.screenshots_dir}")
                return stats
            
            # Проходим по всем PNG файлам
            for screenshot_file in self.screenshots_dir.glob('*.png'):
                try:
                    # Проверяем время модификации файла
                    file_mtime = datetime.fromtimestamp(screenshot_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        # Файл старый - удаляем
                        file_size_mb = screenshot_file.stat().st_size / (1024 * 1024)
                        screenshot_file.unlink()
                        
                        stats['deleted_files'] += 1
                        stats['deleted_size_mb'] += file_size_mb
                        
                        age = datetime.now() - file_mtime
                        self.logger.debug(f"   🗑️ Deleted: {screenshot_file.name} ({file_size_mb:.2f} MB, age: {age.days}d {age.seconds//3600}h)")
                
                except Exception as e:
                    error_msg = f"Error deleting {screenshot_file.name}: {e}"
                    self.logger.error(f"   ❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            if stats['deleted_files'] > 0:
                self.logger.info(f"✅ Screenshots cleanup complete: {stats['deleted_files']} files deleted ({stats['deleted_size_mb']:.2f} MB freed)")
            else:
                self.logger.info("✅ Screenshots cleanup complete: no old screenshots found")
        
        except Exception as e:
            error_msg = f"Critical error in cleanup_old_screenshots: {e}"
            self.logger.error(f"❌ {error_msg}", exc_info=True)
            stats['errors'].append(error_msg)
        
        return stats
    
    def force_cleanup_now(self, cleanup_type: str = 'all') -> Dict:
        """
        Принудительная очистка (не дожидаясь расписания)
        
        Args:
            cleanup_type: 'signals', 'screenshots', 'logs' или 'all'
        
        Returns:
            Статистика очистки
        """
        results = {}
        
        if cleanup_type in ['signals', 'all']:
            self.logger.info("🔧 Force cleanup: signals")
            results['signals'] = self.cleanup_old_signals()
        
        if cleanup_type in ['screenshots', 'all']:
            self.logger.info("🔧 Force cleanup: screenshots")
            results['screenshots'] = self.cleanup_old_screenshots()
        
        if cleanup_type in ['logs', 'all']:
            self.logger.info("🔧 Force cleanup: logs")
            results['logs'] = self.cleanup_old_logs()
        
        return results
    
    def get_stats(self) -> Dict:
        """Получить статистику сервиса"""
        return {
            'running': self._running,
            'last_signals_cleanup': self._last_signals_cleanup.isoformat() if self._last_signals_cleanup else None,
            'last_screenshots_cleanup': self._last_screenshots_cleanup.isoformat() if self._last_screenshots_cleanup else None,
            'last_logs_cleanup': self._last_logs_cleanup.isoformat() if self._last_logs_cleanup else None,
            'config': self.config
        }


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаём сервис
    cleanup = CleanupService()
    
    # Тестовая принудительная очистка
    print("\n=== Test Cleanup ===")
    results = cleanup.force_cleanup_now('all')
    print(f"\nResults: {results}")
    
    # Запуск в фоне (для продакшена)
    # cleanup.start()
    # time.sleep(3600)  # Работает час
    # cleanup.stop()

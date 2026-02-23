"""
Config Manager - централизованное управление конфигурацией

Singleton для чтения и горячей перезагрузки конфигов.
Все модули должны читать конфиг через этот менеджер.
"""

import threading
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from src.core.logger import logger


class ConfigManager:
    """
    Централизованный менеджер конфигурации.
    
    Features:
    - Singleton pattern
    - Thread-safe
    - Hot reload support
    - Change tracking (old→new logging)
    - Dynamic config reading (no caching)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config_lock = threading.Lock()
            self.config_dir = Path('config')
            
            # Cached configs (для быстрого доступа)
            self._cache: Dict[str, Dict] = {}
            self._last_modified: Dict[str, float] = {}
            
            # Reload callbacks
            self._reload_callbacks = []
            
            logger.info("[ConfigManager] Initialized")
    
    def get(self, config_name: str, section: Optional[str] = None, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Получить значение из конфига.
        
        Args:
            config_name: Имя файла (trading.yaml, ai.yaml и т.д.)
            section: Секция в конфиге (опционально)
            key: Ключ в секции (опционально)
            default: Значение по умолчанию
        
        Returns:
            Значение из конфига или default
        
        Examples:
            >>> cfg = get_config_manager()
            >>> cfg.get('trading.yaml', 'trading', 'enabled', True)
            >>> cfg.get('ai.yaml', 'market_analyst', 'gpt', {})
        """
        config = self.load_config(config_name)
        
        if section is None:
            return config
        
        value = config.get(section, {})
        
        if key is None:
            return value if value else default
        
        return value.get(key, default)
    
    def load_config(self, config_name: str, force_reload: bool = False) -> Dict:
        """
        Загрузить конфиг файл с кешированием.
        
        Args:
            config_name: Имя файла (trading.yaml, ai.yaml и т.д.)
            force_reload: Принудительная перезагрузка (игнорировать кеш)
        
        Returns:
            Dictionary с конфигом или {}
        """
        with self.config_lock:
            filepath = self.config_dir / config_name
            
            if not filepath.exists():
                logger.warning(f"[ConfigManager] Config not found: {config_name}")
                return {}
            
            # Проверка изменений файла
            mtime = filepath.stat().st_mtime
            cached_mtime = self._last_modified.get(config_name, 0)
            
            if not force_reload and config_name in self._cache and mtime == cached_mtime:
                # Кеш актуален
                return self._cache[config_name]
            
            # Загрузка из файла
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                # Обновление кеша
                self._cache[config_name] = config
                self._last_modified[config_name] = mtime
                
                logger.debug(f"[ConfigManager] Loaded config: {config_name}")
                return config
            
            except Exception as e:
                logger.error(f"[ConfigManager] Failed to load {config_name}: {e}")
                return {}
    
    def reload_all(self) -> Dict[str, bool]:
        """
        Перезагрузить все конфиги.
        
        Returns:
            Dict с результатами: {config_name: success}
        """
        logger.info("="*80)
        logger.info("[ConfigManager] 🔄 Reloading all configurations...")
        
        results = {}
        config_files = ['trading.yaml', 'ai.yaml', 'portfolio.yaml', 'mt5.yaml', 'telegram.yaml']
        
        for config_name in config_files:
            try:
                old_config = self._cache.get(config_name, {})
                new_config = self.load_config(config_name, force_reload=True)
                
                # Логирование изменений
                self._log_config_changes(config_name, old_config, new_config)
                
                results[config_name] = True
            except Exception as e:
                logger.error(f"[ConfigManager] Failed to reload {config_name}: {e}")
                results[config_name] = False
        
        # Вызов callbacks
        self._notify_reload_callbacks()
        
        logger.info("[ConfigManager] ✅ Reload complete")
        logger.info("="*80)
        return results
    
    def _log_config_changes(self, config_name: str, old_config: Dict, new_config: Dict):
        """
        Логирование изменений конфига (old→new).
        
        Args:
            config_name: Имя файла
            old_config: Старая конфигурация
            new_config: Новая конфигурация
        """
        if not old_config:
            logger.info(f"[ConfigManager] ✅ {config_name} loaded (first time)")
            return
        
        changes = self._find_changes(old_config, new_config)
        
        if not changes:
            logger.info(f"[ConfigManager] ✅ {config_name} - no changes")
            return
        
        logger.info(f"[ConfigManager] 🔄 {config_name} - changes detected:")
        for path, (old_val, new_val) in changes.items():
            logger.info(f"  ↳ {path}: {old_val} → {new_val}")
    
    def _find_changes(self, old: Any, new: Any, path: str = "") -> Dict[str, tuple]:
        """
        Рекурсивный поиск изменений в конфигах.
        
        Returns:
            Dict {path: (old_value, new_value)}
        """
        changes = {}
        
        if type(old) != type(new):
            changes[path or 'root'] = (old, new)
            return changes
        
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            
            for key in all_keys:
                current_path = f"{path}.{key}" if path else key
                
                if key not in old:
                    changes[current_path] = (None, new[key])
                elif key not in new:
                    changes[current_path] = (old[key], None)
                elif old[key] != new[key]:
                    # Рекурсивный поиск в nested dict
                    if isinstance(old[key], dict) and isinstance(new[key], dict):
                        nested_changes = self._find_changes(old[key], new[key], current_path)
                        changes.update(nested_changes)
                    else:
                        changes[current_path] = (old[key], new[key])
        
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                changes[path or 'root'] = (old, new)
        
        elif old != new:
            changes[path or 'root'] = (old, new)
        
        return changes
    
    def register_reload_callback(self, callback):
        """
        Регистрация callback для уведомления о перезагрузке.
        
        Args:
            callback: Функция без аргументов
        """
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)
            logger.debug(f"[ConfigManager] Registered reload callback: {callback.__name__}")
    
    def _notify_reload_callbacks(self):
        """Вызвать все зарегистрированные callbacks."""
        for callback in self._reload_callbacks:
            try:
                callback()
                logger.debug(f"[ConfigManager] Callback executed: {callback.__name__}")
            except Exception as e:
                logger.error(f"[ConfigManager] Callback failed: {callback.__name__}: {e}")
    
    def get_effective_config(self) -> Dict[str, Any]:
        """
        Получить актуальные эффективные значения всех конфигов.
        
        Returns:
            Dict со всеми текущими настройками
        """
        effective = {
            'timestamp': datetime.now().isoformat(),
            'configs': {}
        }
        
        config_files = ['trading.yaml', 'ai.yaml', 'portfolio.yaml', 'mt5.yaml', 'telegram.yaml']
        
        for config_name in config_files:
            config = self.load_config(config_name)
            effective['configs'][config_name] = config
        
        return effective
    
    def save_config(self, config_name: str, config: Dict) -> bool:
        """
        Сохранить конфиг в файл.
        
        Args:
            config_name: Имя файла
            config: Dictionary для сохранения
        
        Returns:
            True если успешно
        """
        with self.config_lock:
            filepath = self.config_dir / config_name
            
            try:
                # Логирование изменений
                old_config = self._cache.get(config_name, {})
                self._log_config_changes(config_name, old_config, config)
                
                # Сохранение в файл
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                # Обновление кеша
                self._cache[config_name] = config
                self._last_modified[config_name] = filepath.stat().st_mtime
                
                logger.info(f"[ConfigManager] ✅ Saved config: {config_name}")
                return True
            
            except Exception as e:
                logger.error(f"[ConfigManager] Failed to save {config_name}: {e}")
                return False


# ==================== GLOBAL INSTANCE ====================

_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get singleton instance of ConfigManager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

"""
Logging Configuration

Настройка системы логирования для SMC-framework.

ТЕКУЩИЙ СТАТУС: Шаблон без реализации
"""

import logging


def setup_logger(name, level=logging.INFO):
    """
    Настройка логгера.
    
    Args:
        name: Имя логгера (обычно имя модуля или стратегии)
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Logger: Настроенный логгер
        
    TODO:
    - Реализовать настройку форматирования
    - Добавить вывод в файл
    - Добавить ротацию логов
    - Добавить цветной вывод в консоль
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # TODO: Настроить форматирование
    # TODO: Добавить handlers (console, file)
    # TODO: Настроить ротацию
    
    return logger


def get_logger(name):
    """
    Получение существующего логгера.
    
    Args:
        name: Имя логгера
        
    Returns:
        Logger: Логгер
    """
    return logging.getLogger(name)

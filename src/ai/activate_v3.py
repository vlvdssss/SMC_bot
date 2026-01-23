#!/usr/bin/env python3
"""
АКТИВАТОР SIGNAL QUALITY V3.0

Простой скрипт для включения новой архитектуры Accuracy/Quality в боте.

ИСПОЛЬЗОВАНИЕ:
1. Импортировать этот модуль в live_trader.py или app.py
2. Вызвать activate_v3() после создания signal_manager

ПРИМЕР:
    from src.ai.activate_v3 import activate_v3
    
    signal_manager = AISignalManager()
    signal_manager = activate_v3(signal_manager, news_fetcher, enable=True)
"""

from src.core.logger import logger


def activate_v3(signal_manager, news_fetcher, enable: bool = True):
    """
    Активирует Signal Quality System V3.0.
    
    Args:
        signal_manager: Экземпляр AISignalManager
        news_fetcher: Экземпляр NewsFetcher
        enable: True - использовать V3, False - оставить V2
    
    Returns:
        signal_manager с активированной V3 логикой
    """
    if not enable:
        logger.info("[V3 Activator] V3 disabled - using V2 logic")
        return signal_manager
    
    try:
        from src.ai.signal_manager_v3 import migrate_to_v3
        
        # Мигрируем на V3
        signal_manager = migrate_to_v3(
            signal_manager=signal_manager,
            news_fetcher=news_fetcher,
            enable_v3=True
        )
        
        logger.info(
            "[V3 Activator] ✅ Signal Quality V3.0 ACTIVATED\n"
            "  - Accuracy/Quality separation enabled\n"
            "  - Gold news filter active (HIGH IMPACT only)\n"
            "  - Risk mode: BALANCED (configurable)"
        )
        
        return signal_manager
        
    except Exception as e:
        logger.error(f"[V3 Activator] ❌ Failed to activate V3: {e}")
        logger.warning("[V3 Activator] Falling back to V2 logic")
        return signal_manager


def get_v3_status(signal_manager) -> bool:
    """
    Проверяет, активна ли V3 логика.
    
    Returns:
        True если V3 активна, False если V2
    """
    return hasattr(signal_manager, '_v3_processor')


def switch_to_v2(signal_manager):
    """
    Переключает обратно на V2 логику (для тестирования/сравнения).
    """
    if hasattr(signal_manager, '_process_analysis_v2'):
        signal_manager.process_analysis = signal_manager._process_analysis_v2
        logger.info("[V3 Activator] Switched back to V2 logic")
    else:
        logger.warning("[V3 Activator] V2 fallback not available")


def switch_to_v3(signal_manager):
    """
    Переключает обратно на V3 логику.
    """
    if hasattr(signal_manager, 'process_analysis_v3'):
        signal_manager.process_analysis = signal_manager.process_analysis_v3
        logger.info("[V3 Activator] Switched to V3 logic")
    else:
        logger.warning("[V3 Activator] V3 not available - activate first")


# =================================================================
# ФЛАГ ДЛЯ БЫСТРОГО ВКЛЮЧЕНИЯ/ВЫКЛЮЧЕНИЯ V3 В ПРОЕКТЕ
# =================================================================

# ⚙️ ИЗМЕНИТЬ ЗДЕСЬ ДЛЯ ВКЛЮЧЕНИЯ/ВЫКЛЮЧЕНИЯ V3
ENABLE_SIGNAL_QUALITY_V3 = True  # True = V3, False = V2

logger.info(f"[V3 Config] Signal Quality V3.0 is {'ENABLED' if ENABLE_SIGNAL_QUALITY_V3 else 'DISABLED'}")

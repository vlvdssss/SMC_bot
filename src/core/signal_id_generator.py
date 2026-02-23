"""
Signal ID Generator - Генерация уникальных ID для дедупликации сигналов
"""

import hashlib
from datetime import datetime
from typing import Dict, Any


def generate_signal_id(
    symbol: str,
    timeframe: str,
    action: str,
    entry: float,
    sl: float,
    tp: float,
    timestamp: datetime = None
) -> str:
    """
    Генерирует уникальный signal_id.
    
    Формат: {symbol}_{tf}_{timestamp}_{hash}
    Пример: XAUUSD_M5_20260221_142530_a3f9b2
    
    Args:
        symbol: Торговый символ (XAUUSD)
        timeframe: Таймфрейм (M5, M15, H1)
        action: Направление (BUY/SELL)
        entry: Цена входа
        sl: Stop loss
        tp: Take profit
        timestamp: Дата/время (default: сейчас)
    
    Returns:
        Уникальный signal_id
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Timestamp в формате YYYYMMDD_HHMMSS
    ts_str = timestamp.strftime('%Y%m%d_%H%M%S')
    
    # Хеш от ключевых параметров (защита от дублей в одну секунду)
    hash_input = f"{symbol}_{action}_{entry:.5f}_{sl:.5f}_{tp:.5f}_{ts_str}"
    hash_digest = hashlib.md5(hash_input.encode()).hexdigest()[:6]
    
    # Финальный ID
    signal_id = f"{symbol}_{timeframe}_{ts_str}_{hash_digest}"
    
    return signal_id


def generate_signal_id_from_dict(data: Dict[str, Any]) -> str:
    """
    Генерирует signal_id из словаря с данными сигнала.
    
    Args:
        data: Словарь с ключами:
            - symbol: str
            - timeframe: str (optional, default: "M5")
            - type/action: str (BUY/SELL)
            - entry_price/entry: float
            - stop_loss/sl: float
            - take_profit/tp: float
    
    Returns:
        signal_id
    """
    symbol = data.get('symbol', 'UNKNOWN')
    timeframe = data.get('timeframe', data.get('tf', 'M5'))
    action = data.get('type', data.get('action', 'UNKNOWN'))
    
    # Flexible key names
    entry = data.get('entry_price', data.get('entry', 0))
    sl = data.get('stop_loss', data.get('sl', 0))
    tp = data.get('take_profit', data.get('tp', 0))
    
    return generate_signal_id(
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        entry=entry,
        sl=sl,
        tp=tp
    )


def parse_signal_id(signal_id: str) -> Dict[str, str]:
    """
    Парсит signal_id обратно в компоненты.
    
    Args:
        signal_id: "XAUUSD_M5_20260221_142530_a3f9b2"
    
    Returns:
        Dict с ключами: symbol, timeframe, date, time, hash
        Или None если формат неверный
    """
    try:
        parts = signal_id.split('_')
        
        if len(parts) < 5:
            return None
        
        return {
            'symbol': parts[0],
            'timeframe': parts[1],
            'date': parts[2],
            'time': parts[3],
            'hash': parts[4]
        }
    except Exception:
        return None


def is_valid_signal_id(signal_id: str) -> bool:
    """Проверка валидности signal_id."""
    parsed = parse_signal_id(signal_id)
    return parsed is not None

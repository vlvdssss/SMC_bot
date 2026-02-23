#!/usr/bin/env python3
"""
Rejected Signals Logger v1.0

Логирует все отклоненные сигналы для последующего анализа.
Помогает понять:
- Почему сигналы отклоняются
- Какие фильтры слишком строгие
- Упущенные возможности

ФОРМАТ ЛОГА:
- Timestamp
- Symbol, Direction, Confidence
- Причина отклонения
- Технические данные на момент отклонения
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from src.core.logger import logger


class RejectedSignalsLogger:
    """
    Логирует отклоненные сигналы для анализа.
    
    Используется для:
    1. Анализа эффективности фильтров
    2. Поиска упущенных возможностей  
    3. Оптимизации параметров входа
    """
    
    def __init__(self, log_dir: str = "data/rejected_signals"):
        """
        Initialize rejected signals logger.
        
        Args:
            log_dir: Директория для логов
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV лог для быстрого анализа
        self.csv_file = self.log_dir / f"rejected_{datetime.now().strftime('%Y%m')}.csv"
        
        # JSON лог для детального анализа
        self.json_file = self.log_dir / f"rejected_{datetime.now().strftime('%Y%m')}.json"
        
        # Инициализируем CSV если не существует
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'direction', 'confidence',
                    'entry', 'sl', 'tp', 'reason', 'filter_type',
                    'session', 'spread_pips', 'ema_trend', 'rsi'
                ])
        
        logger.info(f"[RejectedLogger] Initialized - logging to {self.log_dir}")
    
    def _sanitize_for_json(self, data: Dict) -> Dict:
        """
        Конвертирует все значения в JSON-serializable типы.
        
        Args:
            data: Словарь с данными
        
        Returns:
            Словарь с JSON-safe данными
        """
        import numpy as np
        
        sanitized = {}
        for key, value in data.items():
            try:
                # Convert numpy types to Python types
                if isinstance(value, (np.integer, np.int64, np.int32)):
                    sanitized[key] = int(value)
                elif isinstance(value, (np.floating, np.float64, np.float32)):
                    sanitized[key] = float(value)
                elif isinstance(value, (np.bool_, bool)):
                    sanitized[key] = bool(value)
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_for_json(value)
                elif isinstance(value, (list, tuple)):
                    sanitized[key] = [self._sanitize_for_json({'v': v})['v'] if isinstance(v, dict) else v for v in value]
                else:
                    sanitized[key] = value
            except Exception as e:
                # If conversion fails, convert to string
                sanitized[key] = str(value)
        
        return sanitized
    
    def log_rejection(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        entry: float,
        sl: float,
        tp: float,
        reason: str,
        filter_type: str,
        tech_data: Dict = None,
        session_info: Dict = None
    ) -> None:
        """
        Логирует отклоненный сигнал.
        
        Args:
            symbol: Торговый инструмент
            direction: BUY или SELL
            confidence: Уверенность GPT
            entry: Цена входа
            sl: Stop Loss
            tp: Take Profit
            reason: Причина отклонения
            filter_type: Тип фильтра ('spread', 'technical', 'session', 'risk', etc.)
            tech_data: Технические данные (опционально)
            session_info: Информация о сессии (опционально)
        """
        try:
            timestamp = datetime.now()
            
            # Извлекаем ключевые данные
            spread_pips = 0.0
            ema_trend = 'unknown'
            rsi = 0.0
            session_name = 'unknown'
            
            if tech_data:
                spread_pips = tech_data.get('spread_pips', 0.0)
                if tech_data.get('ema_bullish'):
                    ema_trend = 'bullish'
                elif tech_data.get('ema_bearish'):
                    ema_trend = 'bearish'
                else:
                    ema_trend = 'sideways'
                rsi = tech_data.get('rsi', 0.0)
            
            if session_info:
                session_name = session_info.get('session_name', 'unknown')
            
            # CSV запись (быстрый анализ)
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp.isoformat(),
                    symbol,
                    direction,
                    confidence,
                    entry,
                    sl,
                    tp,
                    reason,
                    filter_type,
                    session_name,
                    spread_pips,
                    ema_trend,
                    rsi
                ])
            
            # JSON запись (детальный анализ)
            rejection_data = {
                'timestamp': timestamp.isoformat(),
                'symbol': symbol,
                'direction': direction,
                'confidence': float(confidence),
                'entry': float(entry),
                'sl': float(sl),
                'tp': float(tp),
                'reason': str(reason),
                'filter_type': str(filter_type),
                'technical_data': self._sanitize_for_json(tech_data or {}),
                'session_info': self._sanitize_for_json(session_info or {})
            }
            
            # Добавляем в JSON файл
            if self.json_file.exists():
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    try:
                        all_rejections = json.load(f)
                    except:
                        all_rejections = []
            else:
                all_rejections = []
            
            all_rejections.append(rejection_data)
            
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(all_rejections, f, indent=2)
            
            logger.debug(f"[RejectedLogger] Logged rejection: {symbol} {direction} - {reason}")
            
        except Exception as e:
            logger.error(f"[RejectedLogger] Failed to log rejection: {e}")
    
    def get_rejection_stats(self, days: int = 7) -> Dict:
        """
        Возвращает статистику отклонений за N дней.
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Dict со статистикой
        """
        try:
            if not self.csv_file.exists():
                return {}
            
            # Читаем CSV
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rejections = list(reader)
            
            # Фильтруем по дате
            cutoff_date = datetime.now().timestamp() - (days * 86400)
            recent_rejections = [
                r for r in rejections
                if datetime.fromisoformat(r['timestamp']).timestamp() > cutoff_date
            ]
            
            if not recent_rejections:
                return {'total': 0}
            
            # Статистика по причинам
            reasons = {}
            filter_types = {}
            symbols = {}
            
            for r in recent_rejections:
                reason = r['reason']
                filter_type = r['filter_type']
                symbol = r['symbol']
                
                reasons[reason] = reasons.get(reason, 0) + 1
                filter_types[filter_type] = filter_types.get(filter_type, 0) + 1
                symbols[symbol] = symbols.get(symbol, 0) + 1
            
            stats = {
                'total': len(recent_rejections),
                'days': days,
                'top_reasons': sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5],
                'by_filter_type': filter_types,
                'by_symbol': symbols,
                'avg_confidence': sum(float(r['confidence']) for r in recent_rejections) / len(recent_rejections)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"[RejectedLogger] Failed to get stats: {e}")
            return {}
    
    def print_rejection_report(self, days: int = 7) -> None:
        """Выводит отчет по отклонениям."""
        stats = self.get_rejection_stats(days)
        
        if not stats or stats.get('total', 0) == 0:
            logger.info(f"[RejectedLogger] No rejections in last {days} days")
            return
        
        logger.info("=" * 60)
        logger.info(f"[RejectedLogger] REJECTION REPORT (last {days} days)")
        logger.info("=" * 60)
        logger.info(f"Total Rejections: {stats['total']}")
        logger.info(f"Average Confidence: {stats['avg_confidence']:.1f}%")
        logger.info("")
        
        logger.info("Top 5 Rejection Reasons:")
        for reason, count in stats['top_reasons']:
            percent = (count / stats['total']) * 100
            logger.info(f"  - {reason}: {count} ({percent:.1f}%)")
        
        logger.info("")
        logger.info("By Filter Type:")
        for filter_type, count in stats['by_filter_type'].items():
            percent = (count / stats['total']) * 100
            logger.info(f"  - {filter_type}: {count} ({percent:.1f}%)")
        
        logger.info("")
        logger.info("By Symbol:")
        for symbol, count in stats['by_symbol'].items():
            percent = (count / stats['total']) * 100
            logger.info(f"  - {symbol}: {count} ({percent:.1f}%)")
        
        logger.info("=" * 60)

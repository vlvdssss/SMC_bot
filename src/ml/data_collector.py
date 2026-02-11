"""
ML Data Collector - Сбор всех данных для машинного обучения
Записывает каждую проверку сигнала с полным контекстом рынка
"""

import csv
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Any, Optional
import pandas as pd

# Helper для работы с путями
def get_data_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    return base_path / 'data' / filename

class MLDataCollector:
    """Собирает данные рынка для ML обучения"""
    
    def __init__(self):
        self.ml_folder = get_data_path('ml_training')
        self.ml_folder.mkdir(exist_ok=True)
        
        # Файлы для записи
        self.market_snapshots_file = self.ml_folder / 'market_snapshots.csv'
        self.ai_decisions_file = self.ml_folder / 'ai_decisions.csv'
        self.trade_outcomes_file = self.ml_folder / 'trade_outcomes.csv'
        
        # Инициализация CSV файлов с заголовками
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Создаём CSV файлы с заголовками если их нет"""
        
        # Market Snapshots - каждая проверка сигнала
        if not self.market_snapshots_file.exists():
            with open(self.market_snapshots_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'date', 'time', 'hour', 'minute', 'day_of_week',
                    'symbol', 'price', 'bid', 'ask', 'spread',
                    'atr_14', 'atr_normalized',
                    'ema_20', 'ema_50', 'ema_200',
                    'rsi_14', 'macd', 'macd_signal', 'macd_hist',
                    'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                    'volume', 'volume_sma_20',
                    'distance_to_ema20', 'distance_to_ema50', 'distance_to_ema200',
                    'trend_slope_20', 'trend_slope_50',
                    'candle_1_open', 'candle_1_high', 'candle_1_low', 'candle_1_close', 'candle_1_body',
                    'candle_2_open', 'candle_2_high', 'candle_2_low', 'candle_2_close', 'candle_2_body',
                    'candle_3_open', 'candle_3_high', 'candle_3_low', 'candle_3_close', 'candle_3_body',
                    'session', 'volatility_state', 'trend_state'
                ])
        
        # AI Decisions - когда AI дал сигнал
        if not self.ai_decisions_file.exists():
            with open(self.ai_decisions_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'date', 'time', 'hour',
                    'symbol', 'action', 'confidence', 'trend',
                    'entry_price', 'sl_price', 'tp_price', 'risk_reward',
                    'reasoning', 'entry_quality',
                    'market_price', 'atr_14', 'rsi_14', 'ema_trend',
                    'triggered', 'executed', 'skip_reason'
                ])
        
        # Trade Outcomes - результаты сделок для обучения
        if not self.trade_outcomes_file.exists():
            with open(self.trade_outcomes_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'trade_id', 'open_time', 'close_time', 'duration_minutes',
                    'symbol', 'direction', 'volume',
                    'entry_price', 'exit_price', 'sl', 'tp',
                    'pnl', 'pnl_pips', 'win',
                    'open_hour', 'open_day_of_week', 'session',
                    'open_atr', 'open_rsi', 'open_ema_trend',
                    'ai_confidence', 'ai_reasoning',
                    'close_reason'
                ])
    
    def log_market_snapshot(self, market_data: Dict[str, Any]):
        """Записывает snapshot состояния рынка"""
        try:
            now = datetime.now()
            
            # Проверка что есть хоть какие-то данные
            if not market_data or not market_data.get('price'):
                return  # Пропускаем если нет данных
            
            # Определяем сессию
            hour = now.hour
            if 2 <= hour < 10:
                session = 'ASIA'
            elif 10 <= hour < 16:
                session = 'EUROPE'
            elif 16 <= hour < 22:
                session = 'US'
            else:
                session = 'OFF_HOURS'
            
            # Определяем volatility state
            atr = market_data.get('atr_14', 0)
            if atr < 5:
                volatility = 'LOW'
            elif atr < 15:
                volatility = 'NORMAL'
            elif atr < 25:
                volatility = 'HIGH'
            else:
                volatility = 'EXTREME'
            
            # Определяем trend state
            price = market_data.get('price', 0)
            ema20 = market_data.get('ema_20', 0)
            ema50 = market_data.get('ema_50', 0)
            ema200 = market_data.get('ema_200', 0)
            
            if ema20 > ema50 > ema200:
                trend = 'STRONG_UPTREND'
            elif ema20 > ema50:
                trend = 'UPTREND'
            elif ema20 < ema50 < ema200:
                trend = 'STRONG_DOWNTREND'
            elif ema20 < ema50:
                trend = 'DOWNTREND'
            else:
                trend = 'SIDEWAYS'
            
            row = [
                now.isoformat(),
                now.strftime('%Y-%m-%d'),
                now.strftime('%H:%M:%S'),
                now.hour,
                now.minute,
                now.strftime('%A'),
                market_data.get('symbol', 'XAUUSD'),
                market_data.get('price', 0),
                market_data.get('bid', 0),
                market_data.get('ask', 0),
                market_data.get('spread', 0),
                market_data.get('atr_14', 0),
                market_data.get('atr_normalized', 0),
                market_data.get('ema_20', 0),
                market_data.get('ema_50', 0),
                market_data.get('ema_200', 0),
                market_data.get('rsi_14', 0),
                market_data.get('macd', 0),
                market_data.get('macd_signal', 0),
                market_data.get('macd_hist', 0),
                market_data.get('bb_upper', 0),
                market_data.get('bb_middle', 0),
                market_data.get('bb_lower', 0),
                market_data.get('bb_width', 0),
                market_data.get('volume', 0),
                market_data.get('volume_sma_20', 0),
                market_data.get('distance_to_ema20', 0),
                market_data.get('distance_to_ema50', 0),
                market_data.get('distance_to_ema200', 0),
                market_data.get('trend_slope_20', 0),
                market_data.get('trend_slope_50', 0),
                # Последние 3 свечи
                market_data.get('candle_1_open', 0),
                market_data.get('candle_1_high', 0),
                market_data.get('candle_1_low', 0),
                market_data.get('candle_1_close', 0),
                market_data.get('candle_1_body', 0),
                market_data.get('candle_2_open', 0),
                market_data.get('candle_2_high', 0),
                market_data.get('candle_2_low', 0),
                market_data.get('candle_2_close', 0),
                market_data.get('candle_2_body', 0),
                market_data.get('candle_3_open', 0),
                market_data.get('candle_3_high', 0),
                market_data.get('candle_3_low', 0),
                market_data.get('candle_3_close', 0),
                market_data.get('candle_3_body', 0),
                session,
                volatility,
                trend
            ]
            
            with open(self.market_snapshots_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
        except Exception as e:
            print(f"[ML Collector] Error logging market snapshot: {e}")
    
    def log_ai_decision(self, ai_data: Dict[str, Any], market_data: Dict[str, Any], 
                       triggered: bool = False, executed: bool = False, skip_reason: str = ''):
        """Записывает решение AI"""
        try:
            # Защита от пустых данных
            if not ai_data:
                return
            
            # Пропускаем NONE actions (ошибки валидации)
            action = ai_data.get('action', 'NONE')
            if action == 'NONE':
                return
            
            now = datetime.now()
            
            # Поддержка плоского формата (как в live_trader)
            action = ai_data.get('action', 'NONE')
            confidence = ai_data.get('confidence', 100)
            reasoning = ai_data.get('reasoning', '')
            entry = ai_data.get('entry_price', 0)
            sl = ai_data.get('sl_price', 0)
            tp = ai_data.get('tp_price', 0)
            
            row = [
                now.isoformat(),
                now.strftime('%Y-%m-%d'),
                now.strftime('%H:%M:%S'),
                now.hour,
                market_data.get('symbol', 'XAUUSD'),
                action,
                confidence,
                'unknown',  # trend
                entry,
                sl,
                tp,
                0,  # risk_reward
                reasoning[:100] if reasoning else '',
                'unknown',  # entry_quality
                market_data.get('price', 0),
                market_data.get('atr_14', 0),
                market_data.get('rsi_14', 0),
                market_data.get('ema_trend', 'unknown'),
                triggered,
                executed,
                skip_reason
            ]
            
            with open(self.ai_decisions_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
        except Exception as e:
            print(f"[ML Collector] Error logging AI decision: {e}")
    
    def log_trade_outcome(self, trade: Dict[str, Any], ai_data: Optional[Dict] = None):
        """Записывает результат сделки для обучения"""
        try:
            # Защита от пустых данных
            if not trade or not trade.get('id'):
                logger.debug("[ML Collector] Skipping - no trade id")
                return
            
            win = trade.get('pnl', 0) > 0
            
            # Вычисляем pips
            entry = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            pnl_pips = abs(exit_price - entry) * 10 if entry and exit_price else 0  # Для золота
            
            # Безопасный парсинг дат
            open_time_str = trade.get('open_time', '')
            close_time_str = trade.get('close_time', '')
            
            try:
                # Пытаемся распарсить даты
                if isinstance(open_time_str, str) and open_time_str:
                    open_time = datetime.fromisoformat(open_time_str)
                else:
                    open_time = datetime.now()
                    
                if isinstance(close_time_str, str) and close_time_str:
                    close_time = datetime.fromisoformat(close_time_str)
                else:
                    close_time = datetime.now()
                    
                duration = (close_time - open_time).total_seconds() / 60
            except Exception as e:
                logger.warning(f"[ML Collector] Date parsing error: {e}, using 0 duration")
                open_time = datetime.now()
                close_time = datetime.now()
                duration = 0
            
            row = [
                trade.get('id', 0),
                trade.get('open_time', ''),
                trade.get('close_time', ''),
                duration,
                trade.get('instrument', 'XAUUSD'),
                trade.get('direction', ''),
                trade.get('volume', 0),
                trade.get('entry_price', 0),
                trade.get('exit_price', 0),
                trade.get('sl', 0),
                trade.get('tp', 0),
                trade.get('pnl', 0),
                pnl_pips,
                1 if win else 0,
                open_time.hour,
                open_time.strftime('%A'),
                trade.get('session', ''),
                trade.get('open_atr', 0),
                trade.get('open_rsi', 0),
                trade.get('open_ema_trend', ''),
                ai_data.get('confidence', 0) if ai_data else 0,
                ai_data.get('reasoning', '')[:100] if ai_data else '',
                trade.get('close_reason', 'unknown')
            ]
            
            with open(self.trade_outcomes_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            logger.info(f"[ML Collector] ✅ Logged trade: #{trade.get('id')} {trade.get('direction')} ${trade.get('pnl', 0):.2f} ({duration:.0f}min)")
                
        except Exception as e:
            logger.error(f"[ML Collector] ❌ Error logging trade outcome: {e}")
            import traceback
            logger.error(f"[ML Collector] Traceback: {traceback.format_exc()}")
    
    def get_stats(self) -> Dict[str, int]:
        """Получить статистику собранных данных"""
        try:
            snapshots = sum(1 for _ in open(self.market_snapshots_file)) - 1
            decisions = sum(1 for _ in open(self.ai_decisions_file)) - 1
            trades = sum(1 for _ in open(self.trade_outcomes_file)) - 1
            
            return {
                'market_snapshots': max(0, snapshots),
                'ai_decisions': max(0, decisions),
                'trade_outcomes': max(0, trades)
            }
        except:
            return {'market_snapshots': 0, 'ai_decisions': 0, 'trade_outcomes': 0}

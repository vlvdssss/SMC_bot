"""
Сборщик метрик торговли
Собирает и агрегирует статистику для анализа
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from src.core.logger import logger


@dataclass
class TradeMetrics:
    """Метрики одной сделки"""
    timestamp: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    exit_price: float
    profit: float
    pips: float
    duration_minutes: int
    strategy: str
    ml_confidence: float = 0.0
    gpt_filtered: bool = False


@dataclass
class DailyMetrics:
    """Дневные метрики"""
    date: str
    starting_balance: float
    ending_balance: float
    profit: float
    roi_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    winrate_pct: float
    total_pips: float
    max_drawdown_pct: float
    sharpe_ratio: float = 0.0


class MetricsCollector:
    """Сборщик метрик"""
    
    def __init__(self, data_dir: str = "data/metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.trade_metrics = []
        self.daily_metrics = []
        
        # Кеш для быстрого доступа
        self.current_day_trades = []
        self.starting_balance = 10000.0
        self.peak_equity = 10000.0
        
        self._load_metrics()
        logger.info("MetricsCollector инициализирован")
    
    def _load_metrics(self):
        """Загрузка метрик из файлов"""
        try:
            trades_file = self.data_dir / "trades_metrics.json"
            if trades_file.exists():
                with open(trades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trade_metrics = [TradeMetrics(**t) for t in data]
                logger.info(f"Загружено {len(self.trade_metrics)} метрик сделок")
            
            daily_file = self.data_dir / "daily_metrics.json"
            if daily_file.exists():
                with open(daily_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.daily_metrics = [DailyMetrics(**d) for d in data]
                logger.info(f"Загружено {len(self.daily_metrics)} дневных метрик")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки метрик: {e}")
    
    def _save_metrics(self):
        """Сохранение метрик в файлы с атомарной записью"""
        try:
            # Сохранение trades_metrics
            trades_file = self.data_dir / "trades_metrics.json"
            temp_file = trades_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(t) for t in self.trade_metrics], f, indent=2, ensure_ascii=False)
                temp_file.replace(trades_file)
            except Exception as e:
                logger.error(f"Ошибка сохранения trades_metrics: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise
            
            # Сохранение daily_metrics
            daily_file = self.data_dir / "daily_metrics.json"
            temp_file = daily_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(d) for d in self.daily_metrics], f, indent=2, ensure_ascii=False)
                temp_file.replace(daily_file)
            except Exception as e:
                logger.error(f"Ошибка сохранения daily_metrics: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise
            
            logger.debug("Метрики сохранены")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения метрик: {e}")
    
    def add_trade_metrics(self, metrics: TradeMetrics):
        """Добавить метрики сделки"""
        self.trade_metrics.append(metrics)
        self.current_day_trades.append(metrics)
        self._save_metrics()
        
        logger.info(f"Добавлены метрики сделки: {metrics.symbol} {metrics.direction} "
                   f"Profit=${metrics.profit:.2f}")
    
    def finalize_day(self, ending_balance: float) -> DailyMetrics:
        """
        Завершить день и создать дневные метрики
        
        Args:
            ending_balance: Конечный баланс дня
            
        Returns:
            Объект DailyMetrics
        """
        if not self.current_day_trades:
            logger.warning("Нет сделок за день для метрик")
            return None
        
        profit = ending_balance - self.starting_balance
        roi_pct = (profit / self.starting_balance) * 100
        
        winning = [t for t in self.current_day_trades if t.profit > 0]
        losing = [t for t in self.current_day_trades if t.profit <= 0]
        
        winrate = (len(winning) / len(self.current_day_trades)) * 100
        total_pips = sum(t.pips for t in self.current_day_trades)
        
        # Расчет максимального drawdown
        equity_curve = [self.starting_balance]
        for trade in self.current_day_trades:
            equity_curve.append(equity_curve[-1] + trade.profit)
        
        peak = max(equity_curve)
        max_dd = 0
        for equity in equity_curve:
            dd = ((peak - equity) / peak) * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        daily = DailyMetrics(
            date=datetime.now().strftime('%Y-%m-%d'),
            starting_balance=self.starting_balance,
            ending_balance=ending_balance,
            profit=profit,
            roi_pct=roi_pct,
            total_trades=len(self.current_day_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            winrate_pct=winrate,
            total_pips=total_pips,
            max_drawdown_pct=max_dd
        )
        
        self.daily_metrics.append(daily)
        self._save_metrics()
        
        # Обновление для следующего дня
        self.current_day_trades = []
        self.starting_balance = ending_balance
        
        logger.info(f"Дневные метрики: Profit=${profit:.2f} ROI={roi_pct:.2f}% "
                   f"Trades={len(self.current_day_trades)} Winrate={winrate:.1f}%")
        
        return daily
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Получить статистику текущего дня"""
        if not self.current_day_trades:
            return {
                'trades': 0,
                'profit': 0.0,
                'winning': 0,
                'losing': 0,
                'winrate': 0.0
            }
        
        winning = [t for t in self.current_day_trades if t.profit > 0]
        losing = [t for t in self.current_day_trades if t.profit <= 0]
        profit = sum(t.profit for t in self.current_day_trades)
        
        return {
            'trades': len(self.current_day_trades),
            'profit': profit,
            'winning': len(winning),
            'losing': len(losing),
            'winrate': (len(winning) / len(self.current_day_trades)) * 100,
            'total_pips': sum(t.pips for t in self.current_day_trades)
        }
    
    def get_period_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получить статистику за период"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        period_daily = [d for d in self.daily_metrics if d.date >= cutoff_date]
        
        if not period_daily:
            return {'error': 'Нет данных за период'}
        
        total_profit = sum(d.profit for d in period_daily)
        avg_roi = sum(d.roi_pct for d in period_daily) / len(period_daily)
        total_trades = sum(d.total_trades for d in period_daily)
        winning_days = len([d for d in period_daily if d.profit > 0])
        
        return {
            'days': len(period_daily),
            'total_profit': total_profit,
            'avg_daily_roi': avg_roi,
            'total_trades': total_trades,
            'winning_days': winning_days,
            'day_winrate': (winning_days / len(period_daily)) * 100,
            'avg_trades_per_day': total_trades / len(period_daily)
        }
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Анализ производительности по стратегиям"""
        strategies = {}
        
        for trade in self.trade_metrics:
            if trade.strategy not in strategies:
                strategies[trade.strategy] = {
                    'trades': [],
                    'total_profit': 0.0,
                    'winning': 0,
                    'losing': 0
                }
            
            strategies[trade.strategy]['trades'].append(trade)
            strategies[trade.strategy]['total_profit'] += trade.profit
            
            if trade.profit > 0:
                strategies[trade.strategy]['winning'] += 1
            else:
                strategies[trade.strategy]['losing'] += 1
        
        # Расчет статистики
        result = {}
        for name, data in strategies.items():
            total = len(data['trades'])
            result[name] = {
                'total_trades': total,
                'total_profit': data['total_profit'],
                'avg_profit': data['total_profit'] / total,
                'winning_trades': data['winning'],
                'losing_trades': data['losing'],
                'winrate': (data['winning'] / total) * 100 if total > 0 else 0
            }
        
        return result
    
    def export_to_csv(self, filepath: str):
        """Экспорт метрик в CSV"""
        try:
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if not self.trade_metrics:
                    logger.warning("Нет метрик для экспорта")
                    return
                
                writer = csv.DictWriter(f, fieldnames=asdict(self.trade_metrics[0]).keys())
                writer.writeheader()
                
                for trade in self.trade_metrics:
                    writer.writerow(asdict(trade))
            
            logger.info(f"Метрики экспортированы в {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка экспорта метрик: {e}")

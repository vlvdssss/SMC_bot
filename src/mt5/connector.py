"""
MT5 Connector - MetaTrader 5 Integration
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any

class MT5Connector:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('MT5Connector')
        self.connected = False
    
    def connect(self) -> bool:
        """Подключение к MT5"""
        try:
            if not mt5.initialize(
                path=self.config['connection']['path'],
                login=self.config['connection']['login'],
                password=self.config['connection']['password'],
                server=self.config['connection']['server'],
                timeout=self.config['connection']['timeout']
            ):
                self.logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            self.connected = True
            self.logger.info("Successfully connected to MT5")
            return True
        
        except Exception as e:
            self.logger.error(f"Error connecting to MT5: {e}")
            return False
    
    def disconnect(self):
        """Отключение от MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Disconnected from MT5")
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Получение текущей цены"""
        if not self.connected:
            return None
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.logger.error(f"Failed to get tick for {symbol}")
            return None
        
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'spread': tick.ask - tick.bid
        }
    
    def get_latest_data(self, symbol: str, timeframe: str = 'H1', count: int = 100) -> pd.DataFrame:
        """Получение последних данных"""
        if not self.connected:
            return pd.DataFrame()
        
        # Преобразование timeframe
        tf_map = {
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'D1': mt5.TIMEFRAME_D1
        }
        
        tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            self.logger.error(f"Failed to get rates for {symbol}")
            return pd.DataFrame()
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о счете"""
        if not self.connected:
            return None
        
        account = mt5.account_info()
        if account is None:
            self.logger.error("Failed to get account info")
            return None
        
        return {
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'leverage': account.leverage
        }
    
    def get_trade_history(self, days: int = 30) -> list:
        """Получение истории сделок за последние дни"""
        if not self.connected:
            return []
        
        try:
            # Получаем историю сделок
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            
            trades = []
            for deal in deals:
                if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    # Рассчитываем P&L для закрытых позиций
                    pnl = 0
                    if deal.profit is not None:
                        pnl = deal.profit
                    
                    trades.append({
                        'id': deal.ticket,
                        'date': deal.time.strftime('%Y-%m-%d'),
                        'time': deal.time.strftime('%H:%M'),
                        'instrument': deal.symbol,
                        'direction': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                        'pnl': round(pnl, 2),
                        'volume': deal.volume,
                        'price': deal.price
                    })
            
            return trades
        
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []
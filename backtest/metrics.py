"""
Metrics calculation for backtesting results
"""

import pandas as pd
import numpy as np
from typing import Dict, List

class MetricsCalculator:
    @staticmethod
    def calculate_portfolio_metrics(trades_df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        """Расчет метрик портфеля"""
        
        if trades_df.empty:
            return {
                'total_return': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'total_trades': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'avg_trade': 0
            }
        
        # Расчет кумулятивной прибыли
        trades_df = trades_df.sort_values('exit_time')
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        trades_df['balance'] = initial_balance + trades_df['cumulative_pnl']
        
        # Total Return
        total_return = (trades_df['balance'].iloc[-1] - initial_balance) / initial_balance * 100
        
        # Max Drawdown
        peak = trades_df['balance'].cummax()
        drawdown = (trades_df['balance'] - peak) / peak
        max_drawdown = abs(drawdown.min()) * 100
        
        # Win Rate
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        
        # Profit Factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe Ratio (упрощено, без risk-free rate)
        returns = trades_df['pnl'] / initial_balance
        if returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Average Trade
        avg_trade = trades_df['pnl'].mean()
        
        return {
            'total_return': round(total_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 1),
            'total_trades': len(trades_df),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'avg_trade': round(avg_trade, 2)
        }
    
    @staticmethod
    def calculate_monthly_returns(trades_df: pd.DataFrame) -> pd.DataFrame:
        """Расчет месячных доходностей"""
        if trades_df.empty:
            return pd.DataFrame()
        
        trades_df['month'] = trades_df['exit_time'].dt.to_period('M')
        monthly = trades_df.groupby('month')['pnl'].sum()
        monthly_returns = monthly / 10000 * 100  # Процент от начального баланса
        
        return monthly_returns.reset_index()
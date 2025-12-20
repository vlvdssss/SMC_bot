"""
BAZA - Production Trading Bot

Modular multi-instrument portfolio trading system.

Components:
- bot.py: Main entry point
- portfolio_manager.py: Multi-instrument portfolio execution
- core/: Core modules (broker, executor, data_loader)
- strategies/: FROZEN baseline strategies
- config/: Instrument and portfolio configurations

Usage:
    from BAZA.portfolio_manager import PortfolioManager
    
    portfolio = PortfolioManager(initial_balance=100.0)
    results = portfolio.run_backtest('2024-01-01', '2024-12-31')
"""

__version__ = '1.0.0'
__status__ = 'PRODUCTION_READY'

from .portfolio_manager import PortfolioManager

__all__ = ['PortfolioManager']

"""
AI Module for BAZA Trading Bot

Contains AI-powered tools for trading analysis and risk management.
"""

from .news_filter import GPTNewsFilter

# Optional imports - don't break if unavailable
try:
    from .news_fetcher import RealTimeNewsFetcher, get_news_fetcher
    __all__ = ['GPTNewsFilter', 'RealTimeNewsFetcher', 'get_news_fetcher']
except ImportError as e:
    # NewsFetcher requires bs4 - graceful degradation
    __all__ = ['GPTNewsFilter']
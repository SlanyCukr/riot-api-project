"""
Detection factor analyzers.

This package contains individual analyzer modules for different
player detection factors to improve maintainability and separation of concerns.
"""

from .win_rate_analyzer import WinRateFactorAnalyzer
from .account_level_analyzer import AccountLevelFactorAnalyzer

__all__ = [
    "WinRateFactorAnalyzer",
    "AccountLevelFactorAnalyzer",
]

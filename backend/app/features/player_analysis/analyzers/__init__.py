"""
Detection factor analyzers.

This package contains individual analyzer modules for different
player detection factors to improve maintainability and separation of concerns.
"""

from .win_rate_analyzer import WinRateFactorAnalyzer
from .win_rate_trend_analyzer import WinRateTrendFactorAnalyzer
from .account_level_analyzer import AccountLevelFactorAnalyzer
from .performance_analyzer import PerformanceFactorAnalyzer
from .rank_progression_analyzer import RankProgressionFactorAnalyzer
from .rank_discrepancy_analyzer import RankDiscrepancyFactorAnalyzer
from .performance_trends_analyzer import PerformanceTrendsFactorAnalyzer
from .role_performance_analyzer import RolePerformanceFactorAnalyzer
from .kda_analyzer import KDAFactorAnalyzer

__all__ = [
    "WinRateFactorAnalyzer",
    "WinRateTrendFactorAnalyzer",
    "AccountLevelFactorAnalyzer",
    "PerformanceFactorAnalyzer",
    "RankProgressionFactorAnalyzer",
    "RankDiscrepancyFactorAnalyzer",
    "PerformanceTrendsFactorAnalyzer",
    "RolePerformanceFactorAnalyzer",
    "KDAFactorAnalyzer",
]

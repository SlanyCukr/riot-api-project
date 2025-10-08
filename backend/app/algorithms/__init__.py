"""
Detection algorithms package for smurf detection analysis.

This package contains various algorithms for analyzing player behavior
to detect potential smurf accounts.
"""

from .win_rate import WinRateAnalyzer
from .rank_progression import RankProgressionAnalyzer
from .performance import PerformanceAnalyzer

__all__ = ["WinRateAnalyzer", "RankProgressionAnalyzer", "PerformanceAnalyzer"]

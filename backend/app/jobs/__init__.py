"""Job system package for automated data fetching and analysis."""

from .scheduler import get_scheduler, start_scheduler, shutdown_scheduler
from .tracked_player_updater import TrackedPlayerUpdaterJob
from .match_fetcher import MatchFetcherJob
from .smurf_analyzer import SmurfAnalyzerJob
from .ban_checker import BanCheckerJob

__all__ = [
    "get_scheduler",
    "start_scheduler",
    "shutdown_scheduler",
    "TrackedPlayerUpdaterJob",
    "MatchFetcherJob",
    "SmurfAnalyzerJob",
    "BanCheckerJob",
]

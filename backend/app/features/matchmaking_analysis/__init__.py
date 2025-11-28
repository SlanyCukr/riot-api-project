"""Matchmaking Analysis feature module."""

# NOTE: Imports are intentionally minimal to avoid circular dependencies.
# Import directly from submodules when needed (e.g., from .router import router)

from .models import (
    MatchmakingAnalysis,
    MatchmakingMetrics,
    MatchDataPoint,
)

__all__ = [
    "MatchmakingAnalysis",
    "MatchmakingMetrics",
    "MatchDataPoint",
]

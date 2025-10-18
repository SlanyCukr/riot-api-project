"""
Win rate trend factor analyzer for smurf detection.

This module analyzes win rate trends over time to detect sudden improvements
that may indicate smurfing behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ...schemas.detection import DetectionFactor

if TYPE_CHECKING:
    from ..models.players import Player

logger = structlog.get_logger(__name__)


class WinRateTrendFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for win rate trend detection factor.

    Analyzes win rate changes over time to identify patterns that may
    indicate smurfing, such as sudden performance improvements.
    """

    def __init__(self):
        super().__init__("win_rate_trend")

    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze win rate trend for smurf detection.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data in chronological order
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session
        :type db: Any
        :returns: DetectionFactor with win rate trend analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(recent_matches)})

        try:
            if len(recent_matches) < 10:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="Win rate trend: insufficient data (need 10+ matches)",
                    score=0.0,
                )

            # Split matches into recent and older halves
            mid_point = len(recent_matches) // 2
            older_matches = recent_matches[mid_point:]
            recent_half = recent_matches[:mid_point]

            older_wins = sum(1 for m in older_matches if m.get("win", False))
            recent_wins = sum(1 for m in recent_half if m.get("win", False))

            older_rate = older_wins / len(older_matches) if older_matches else 0.0
            recent_rate = recent_wins / len(recent_half) if recent_half else 0.0

            trend_improvement = recent_rate - older_rate

            # Calculate trend score and type
            if trend_improvement > 0.1:  # 10% improvement
                trend_score = min(1.0, trend_improvement * 3)
                trend_type = "improving"
                meets_threshold = trend_score > 0.5
            elif trend_improvement < -0.1:
                trend_score = min(1.0, abs(trend_improvement) * 2)
                trend_type = "declining"
                meets_threshold = False
            else:
                trend_score = 0.0
                trend_type = "stable"
                meets_threshold = False

            description = (
                f"Win rate trend: {trend_type} ({trend_improvement:+.1%} change)"
            )

            factor = self._create_factor(
                value=trend_improvement,
                meets_threshold=meets_threshold,
                description=description,
                score=trend_score,
                context={
                    "trend_type": trend_type,
                    "older_win_rate": older_rate,
                    "recent_win_rate": recent_rate,
                    "improvement": trend_improvement,
                },
            )

            self._log_analysis_result(
                puuid,
                trend_improvement,
                meets_threshold,
                trend_score,
                context={"trend_type": trend_type},
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

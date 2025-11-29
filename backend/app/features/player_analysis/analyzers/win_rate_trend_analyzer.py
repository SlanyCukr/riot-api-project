"""
Win rate trend factor analyzer for player analysis.

This module analyzes win rate trends over time to detect sudden improvements
that may indicate smurfing behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.ranks import PlayerRank
    from app.features.players.orm_models import PlayerORM

logger = structlog.get_logger(__name__)


class WinRateTrendFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for win rate trend detection factor.

    Analyzes win rate changes over time to identify patterns that may
    indicate smurfing, such as sudden performance improvements.
    """

    def __init__(self):
        """Initialize the win rate trend analyzer."""
        super().__init__("win_rate_trend")

    def _calculate_trend_metrics(self, improvement: float) -> tuple[float, str, bool]:
        """
        Calculate trend score, type, and threshold status from improvement value.

        Args:
            improvement: Win rate change (recent - older)

        Returns:
            Tuple of (trend_score, trend_type, meets_threshold)
        """
        if improvement > 0.1:  # 10% improvement
            return min(1.0, improvement * 3), "improving", True
        elif improvement < -0.1:
            return min(1.0, abs(improvement) * 2), "declining", False
        else:
            return 0.0, "stable", False

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze win rate trend for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data in chronological order
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with win rate trend analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            if len(matches_data) < 10:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="Win rate trend: insufficient data (need 10+ matches)",
                    score=0.0,
                )

            # Split matches into recent and older halves
            mid_point = len(matches_data) // 2
            older_matches = matches_data[mid_point:]
            recent_half = matches_data[:mid_point]

            older_wins = sum(1 for m in older_matches if m.get("win", False))
            recent_wins = sum(1 for m in recent_half if m.get("win", False))

            # Both halves guaranteed non-empty (validated min 10 matches above)
            older_rate = older_wins / len(older_matches)
            recent_rate = recent_wins / len(recent_half)

            trend_improvement = recent_rate - older_rate

            # Calculate trend score and type
            trend_score, trend_type, meets_threshold = self._calculate_trend_metrics(
                trend_improvement
            )

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

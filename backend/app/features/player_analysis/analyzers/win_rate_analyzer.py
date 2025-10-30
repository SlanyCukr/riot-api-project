"""
Win rate factor analyzer for player analysis.

This module analyzes player win rates as part of the player analysis
algorithm, looking for unusually high win rates that may indicate smurfing.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.ranks import PlayerRank
    from app.features.players.orm_models import PlayerORM

logger = structlog.get_logger(__name__)


class WinRateFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for player win rate detection factor.

    Analyzes win rates across recent matches to identify patterns
    that may indicate smurfing behavior.
    """

    def __init__(self):
        """Initialize the win rate analyzer."""
        super().__init__("win_rate")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze win rate for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with win rate analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            if not matches_data:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No matches available for win rate analysis",
                    score=0.0,
                )

            # Calculate win rate
            wins = sum(1 for match in matches_data if match.get("win", False))
            total_games = len(matches_data)
            win_rate = wins / total_games

            # Check against threshold
            high_win_rate_threshold = self._get_threshold("high_win_rate")
            min_games_threshold = self._get_threshold("min_games")

            meets_threshold = (
                win_rate >= high_win_rate_threshold
                and total_games >= min_games_threshold
            )

            # Calculate score (normalized to 0-1 range)
            # Scores above 65% get progressively higher scores
            if win_rate < high_win_rate_threshold:
                score = 0.0
            else:
                # Score increases from 0.1 to 1.0 as win rate goes from 65% to 80%
                score = min(
                    1.0, (win_rate - high_win_rate_threshold) / 0.15 * 0.9 + 0.1
                )

            description = (
                f"Win rate: {win_rate:.1%} ({wins}/{total_games} games). "
                f"Threshold: {high_win_rate_threshold:.1%}, "
                f"Min games: {min_games_threshold}"
            )

            factor = self._create_factor(
                value=win_rate,
                meets_threshold=meets_threshold,
                description=description,
                score=score,
                context={
                    "wins": wins,
                    "total_games": total_games,
                    "threshold": high_win_rate_threshold,
                    "min_games": min_games_threshold,
                },
            )

            self._log_analysis_result(
                puuid,
                win_rate,
                meets_threshold,
                score,
                context={"wins": wins, "total_games": total_games},
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

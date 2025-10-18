"""
Win rate factor analyzer for smurf detection.

This module analyzes player win rates as part of the smurf detection
algorithm, looking for unusually high win rates that may indicate smurfing.
"""

from typing import TYPE_CHECKING, Dict, Any, List
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ...schemas.detection import DetectionFactor

if TYPE_CHECKING:
    from ..models.players import Player

logger = structlog.get_logger(__name__)


class WinRateFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for player win rate detection factor.

    Analyzes win rates across recent matches to identify patterns
    that may indicate smurfing behavior.
    """

    def __init__(self):
        super().__init__("win_rate")

    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze win rate for smurf detection.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session
        :type db: Any
        :returns: DetectionFactor with win rate analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(recent_matches)})

        try:
            if not recent_matches:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No matches available for win rate analysis",
                    score=0.0,
                )

            # Calculate win rate
            wins = sum(1 for match in recent_matches if match.get("win", False))
            total_games = len(recent_matches)
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

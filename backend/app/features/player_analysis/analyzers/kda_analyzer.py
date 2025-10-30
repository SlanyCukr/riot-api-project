"""
KDA (Kill/Death/Assist) factor analyzer.

This module analyzes a player's KDA ratio to detect smurf behavior patterns.
"""

from typing import List, Dict, Any, TYPE_CHECKING, Optional
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM
    from app.features.players.ranks import PlayerRank

logger = structlog.get_logger(__name__)


class KDAFactorAnalyzer(BaseFactorAnalyzer):
    """Analyzes KDA (Kills/Deaths/Assists) patterns for smurf detection.

    High KDA ratios can indicate a skilled player on a new account.
    """

    def __init__(self):
        """Initialize the KDA analyzer."""
        super().__init__("kda")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze KDA patterns to detect smurf behavior.

        :param puuid: Player PUUID
        :param matches_data: Pre-fetched match data
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with KDA analysis results
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            # Handle empty match data
            if not matches_data:
                return self._create_error_factor(
                    ValueError("No match data available"), puuid
                )

            # Extract KDA statistics from matches
            total_kills = sum(m.get("kills", 0) for m in matches_data)
            total_deaths = sum(m.get("deaths", 0) for m in matches_data)
            total_assists = sum(m.get("assists", 0) for m in matches_data)

            # Calculate average KDA
            match_count = len(matches_data)
            if match_count > 0:
                avg_kda = self._calculate_kda_ratio(
                    total_kills, total_deaths, total_assists
                )
            else:
                avg_kda = 0.0

            # Get threshold and evaluate
            threshold = self._get_threshold("high_kda")
            meets_threshold = avg_kda >= threshold

            # Calculate normalized score
            if meets_threshold:
                # Score scales from 0.0 to 1.0 based on how much above threshold
                score = min(1.0, avg_kda / threshold)
            else:
                score = 0.0

            # Create result
            factor = self._create_factor(
                value=avg_kda,
                meets_threshold=meets_threshold,
                description=f"Average KDA: {avg_kda:.2f} (threshold: {threshold:.2f})",
                score=score,
                context={
                    "total_kills": total_kills,
                    "total_deaths": total_deaths,
                    "total_assists": total_assists,
                    "match_count": match_count,
                    "threshold": threshold,
                },
            )

            self._log_analysis_result(
                puuid=puuid,
                value=avg_kda,
                meets_threshold=meets_threshold,
                score=score,
                context={
                    "avg_kda": avg_kda,
                    "threshold": threshold,
                    "meets_threshold": meets_threshold,
                },
            )

            return factor

        except Exception as e:
            logger.error(
                "KDA analysis failed",
                puuid=puuid,
                error=str(e),
                exc_info=True,
            )
            return self._create_error_factor(e, puuid)

    @staticmethod
    def _calculate_kda_ratio(kills: int, deaths: int, assists: int) -> float:
        """
        Calculate KDA (Kill/Death/Assist) ratio.

        KDA = (Kills + Assists) / Deaths
        If deaths is 0, KDA = Kills + Assists (perfect performance)

        :param kills: Total kills
        :param deaths: Total deaths
        :param assists: Total assists
        :returns: KDA ratio as float
        """
        if deaths == 0:
            # Perfect games (no deaths) - return total kills + assists
            return float(kills + assists)
        return float(kills + assists) / deaths

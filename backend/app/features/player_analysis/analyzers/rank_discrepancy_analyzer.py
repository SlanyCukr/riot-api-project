"""
Rank discrepancy factor analyzer for player analysis.

This module analyzes the discrepancy between a player's current rank and
their actual performance to identify smurfs who play significantly above
their rank.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from dataclasses import dataclass
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor
from app.features.players.ranks import PlayerRank
from app.core.enums import Tier

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM

logger = structlog.get_logger(__name__)


@dataclass
class TierPerformanceBaseline:
    """Baseline expected performance metrics for each tier."""

    min_kda: float
    min_win_rate: float
    min_cs_per_min: float


class RankDiscrepancyFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for rank discrepancy detection factor.

    Compares actual player performance to expected performance for their
    current rank to identify smurfs who play significantly above their rank.
    """

    # Expected performance baselines for each tier
    TIER_BASELINES = {
        Tier.IRON: TierPerformanceBaseline(
            min_kda=1.0, min_win_rate=0.45, min_cs_per_min=4.0
        ),
        Tier.BRONZE: TierPerformanceBaseline(
            min_kda=1.5, min_win_rate=0.48, min_cs_per_min=4.5
        ),
        Tier.SILVER: TierPerformanceBaseline(
            min_kda=2.0, min_win_rate=0.50, min_cs_per_min=5.0
        ),
        Tier.GOLD: TierPerformanceBaseline(
            min_kda=2.5, min_win_rate=0.52, min_cs_per_min=5.5
        ),
        Tier.PLATINUM: TierPerformanceBaseline(
            min_kda=3.0, min_win_rate=0.55, min_cs_per_min=6.0
        ),
        Tier.EMERALD: TierPerformanceBaseline(
            min_kda=3.5, min_win_rate=0.57, min_cs_per_min=6.5
        ),
        Tier.DIAMOND: TierPerformanceBaseline(
            min_kda=4.0, min_win_rate=0.60, min_cs_per_min=7.0
        ),
        Tier.MASTER: TierPerformanceBaseline(
            min_kda=5.0, min_win_rate=0.62, min_cs_per_min=7.5
        ),
        Tier.GRANDMASTER: TierPerformanceBaseline(
            min_kda=6.0, min_win_rate=0.65, min_cs_per_min=8.0
        ),
        Tier.CHALLENGER: TierPerformanceBaseline(
            min_kda=7.0, min_win_rate=0.68, min_cs_per_min=8.5
        ),
    }

    def __init__(self):
        """Initialize the rank discrepancy analyzer."""
        super().__init__("rank_discrepancy")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze rank discrepancy for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with rank discrepancy analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            # Use pre-fetched rank history
            if not rank_history:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No rank data available",
                    score=0.0,
                )

            current_rank = rank_history[0]

            # Calculate actual performance metrics
            performance_metrics = self._calculate_actual_performance(matches_data)

            if not performance_metrics["has_valid_data"]:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="Insufficient match data for analysis",
                    score=0.0,
                )

            # Get expected performance for current tier
            expected_metrics = self._get_expected_performance(current_rank)

            # Calculate discrepancy
            discrepancy_score = self._calculate_discrepancy(
                performance_metrics, expected_metrics
            )

            # Determine if threshold is met
            meets_threshold = discrepancy_score >= 0.5  # 50% above expected

            # Calculate normalized score
            score = min(1.0, discrepancy_score)

            # Build description
            description = self._build_description(
                current_rank,
                performance_metrics,
                expected_metrics,
                discrepancy_score,
                meets_threshold,
            )

            context = {
                "current_tier": current_rank.tier,
                "current_rank": current_rank.rank,
                "actual_kda": performance_metrics["avg_kda"],
                "expected_kda": expected_metrics["min_kda"],
                "actual_win_rate": performance_metrics["win_rate"],
                "expected_win_rate": expected_metrics["min_win_rate"],
                "discrepancy_score": discrepancy_score,
            }

            factor = self._create_factor(
                value=discrepancy_score,
                meets_threshold=meets_threshold,
                description=description,
                score=score,
                context=context,
            )

            self._log_analysis_result(
                puuid, discrepancy_score, meets_threshold, score, context
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

    def _calculate_actual_performance(
        self, matches_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate actual performance metrics from match data."""
        if not matches_data:
            return {"has_valid_data": False}

        # Calculate win rate
        wins = sum(1 for match in matches_data if match.get("win", False))
        win_rate = wins / len(matches_data)

        # Calculate average KDA
        kda_values = []
        cs_values = []

        for match in matches_data:
            kills = match.get("kills", 0)
            deaths = match.get("deaths", 0)
            assists = match.get("assists", 0)

            if deaths == 0:
                kda = float(kills + assists)
            else:
                kda = (kills + assists) / deaths

            kda_values.append(kda)

            cs = match.get("cs", 0)
            if cs > 0:
                cs_values.append(cs)

        avg_kda = sum(kda_values) / len(kda_values) if kda_values else 0.0
        avg_cs = sum(cs_values) / len(cs_values) if cs_values else 0.0

        return {
            "has_valid_data": True,
            "win_rate": win_rate,
            "avg_kda": avg_kda,
            "avg_cs_per_min": avg_cs,
            "games_analyzed": len(matches_data),
        }

    def _get_expected_performance(self, rank: PlayerRank) -> TierPerformanceBaseline:
        """Get expected performance baseline for a rank's tier."""
        try:
            tier_enum = Tier(rank.tier)
            return self.TIER_BASELINES.get(
                tier_enum,
                self.TIER_BASELINES[Tier.IRON],  # Default to Iron baseline
            )
        except (ValueError, KeyError):
            logger.warning("Invalid tier value encountered", tier=rank.tier)
            return self.TIER_BASELINES[Tier.IRON]

    def _calculate_discrepancy(
        self,
        actual: Dict[str, Any],
        expected: TierPerformanceBaseline,
    ) -> float:
        """Calculate discrepancy score between actual and expected performance."""
        # Calculate how far above expected each metric is
        kda_ratio = expected.min_kda / actual["avg_kda"] if actual["avg_kda"] > 0 else 0
        win_rate_ratio = (
            actual["win_rate"] / expected.min_win_rate
            if expected.min_win_rate > 0
            else 0
        )
        cs_ratio = (
            actual["avg_cs_per_min"] / expected.min_cs_per_min
            if expected.min_cs_per_min > 0
            else 0
        )

        # If all metrics are below expected, no discrepancy
        if kda_ratio > 1.0 or win_rate_ratio > 1.0 or cs_ratio > 1.0:
            # Player is performing below expectations for their rank
            return 0.0

        # Calculate average performance ratio (higher = more above expected)
        # Values > 1.0 mean player is performing better than expected
        performance_ratios = []
        if kda_ratio < 1.0:
            performance_ratios.append(1.0 / kda_ratio)
        if win_rate_ratio < 1.0:
            performance_ratios.append(1.0 / win_rate_ratio)
        if cs_ratio < 1.0:
            performance_ratios.append(1.0 / cs_ratio)

        if not performance_ratios:
            return 0.0

        # Average performance improvement ratio
        avg_improvement = sum(performance_ratios) / len(performance_ratios)

        # Discrepancy score: how much above expected (0.0 to 3.0+)
        discrepancy = avg_improvement - 1.0

        # Normalize to 0.0-1.0 scale where 1.0 = 100% above expected
        # and cap at 1.0
        return min(1.0, discrepancy)

    def _build_description(
        self,
        rank: PlayerRank,
        actual: Dict[str, Any],
        expected: TierPerformanceBaseline,
        discrepancy: float,
        meets_threshold: bool,
    ) -> str:
        """Generate human-readable description."""
        current_display = (
            rank.display_rank
            if hasattr(rank, "display_rank")
            else f"{rank.tier} {rank.rank}"
        )

        if meets_threshold:
            return (
                f"Performance exceeds rank: {actual['avg_kda']:.1f} KDA vs {expected.min_kda:.1f} expected "
                f"for {current_display}, {actual['win_rate']:.1%} win rate vs {expected.min_win_rate:.1%} expected"
            )
        else:
            return (
                f"Performance matches rank: {actual['avg_kda']:.1f} KDA for {current_display} "
                f"(expected {expected.min_kda:.1f}), {actual['win_rate']:.1%} win rate"
            )

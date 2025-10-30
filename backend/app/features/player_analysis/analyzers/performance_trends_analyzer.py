"""
Performance trends factor analyzer for player analysis.

This module analyzes how player performance metrics change over time to
detect sudden improvements that may indicate smurfing behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import statistics
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM
    from app.features.players.ranks import PlayerRank

logger = structlog.get_logger(__name__)


class PerformanceTrendsFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for performance trends detection factor.

    Analyzes changes in player performance over time to identify sudden
    improvements that may indicate smurfing behavior.
    """

    def __init__(self):
        """Initialize the performance trends analyzer."""
        super().__init__("performance_trends")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze performance trends for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data in chronological order
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with performance trends analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            # Need sufficient data for trend analysis
            if len(matches_data) < 20:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="Insufficient data: need 20+ matches for trend analysis",
                    score=0.0,
                )

            # Extract performance metrics for all matches
            performance_data = self._extract_all_performance_metrics(matches_data)

            if not performance_data["valid_matches"]:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No valid performance data available",
                    score=0.0,
                )

            # Split into recent and older halves
            recent_metrics, older_metrics = self._split_performance_periods(
                matches_data, performance_data
            )

            # Calculate improvements
            improvements = self._calculate_improvements(recent_metrics, older_metrics)

            # Analyze trend
            trend_score, trend_type, meets_threshold = self._analyze_trend(
                improvements, recent_metrics, older_metrics
            )

            # Build description
            description = self._build_description(
                improvements, trend_type, meets_threshold
            )

            context = {
                "trend_type": trend_type,
                "kda_improvement": improvements["kda"],
                "cs_improvement": improvements["cs"],
                "vision_improvement": improvements["vision"],
                "recent_kda": recent_metrics["avg_kda"],
                "older_kda": older_metrics["avg_kda"],
                "recent_games": recent_metrics["game_count"],
                "older_games": older_metrics["game_count"],
            }

            factor = self._create_factor(
                value=trend_score,
                meets_threshold=meets_threshold,
                description=description,
                score=trend_score,
                context=context,
            )

            self._log_analysis_result(
                puuid, trend_score, meets_threshold, trend_score, context
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

    def _extract_all_performance_metrics(
        self, matches_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract performance metrics for all matches."""
        kda_values = []
        cs_values = []
        vision_values = []
        valid_matches = 0

        for match in matches_data:
            kills = match.get("kills", 0)
            deaths = match.get("deaths", 0)
            assists = match.get("assists", 0)
            cs = match.get("cs", 0)
            vision = match.get("vision_score", 0)

            # Calculate KDA
            if deaths == 0:
                kda = float(kills + assists)
            else:
                kda = (kills + assists) / deaths

            kda_values.append(kda)
            if cs > 0:
                cs_values.append(cs)
            if vision > 0:
                vision_values.append(vision)

            valid_matches += 1

        return {
            "kda_values": kda_values,
            "cs_values": cs_values,
            "vision_values": vision_values,
            "valid_matches": valid_matches,
        }

    def _split_performance_periods(
        self,
        matches_data: List[Dict[str, Any]],
        performance_data: Dict[str, Any],
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """Split performance data into recent and older periods."""
        mid_point = len(matches_data) // 2

        # Recent half (first half of matches)
        recent_kda = performance_data["kda_values"][:mid_point]
        recent_cs = performance_data["cs_values"][:mid_point]
        recent_vision = performance_data["vision_values"][:mid_point]

        # Older half (second half of matches)
        older_kda = performance_data["kda_values"][mid_point:]
        older_cs = performance_data["cs_values"][mid_point:]
        older_vision = performance_data["vision_values"][mid_point:]

        # Calculate averages
        recent_metrics = {
            "avg_kda": statistics.mean(recent_kda) if recent_kda else 0.0,
            "avg_cs": statistics.mean(recent_cs) if recent_cs else 0.0,
            "avg_vision": statistics.mean(recent_vision) if recent_vision else 0.0,
            "game_count": len(recent_kda),
        }

        older_metrics = {
            "avg_kda": statistics.mean(older_kda) if older_kda else 0.0,
            "avg_cs": statistics.mean(older_cs) if older_cs else 0.0,
            "avg_vision": statistics.mean(older_vision) if older_vision else 0.0,
            "game_count": len(older_kda),
        }

        return recent_metrics, older_metrics

    def _calculate_improvements(
        self,
        recent_metrics: Dict[str, float],
        older_metrics: Dict[str, float],
    ) -> Dict[str, float]:
        """Calculate improvement percentages for each metric."""
        improvements = {}

        # Calculate KDA improvement
        if older_metrics["avg_kda"] > 0:
            improvements["kda"] = (
                recent_metrics["avg_kda"] - older_metrics["avg_kda"]
            ) / older_metrics["avg_kda"]
        else:
            improvements["kda"] = 0.0

        # Calculate CS improvement
        if older_metrics["avg_cs"] > 0:
            improvements["cs"] = (
                recent_metrics["avg_cs"] - older_metrics["avg_cs"]
            ) / older_metrics["avg_cs"]
        else:
            improvements["cs"] = 0.0

        # Calculate vision improvement
        if older_metrics["avg_vision"] > 0:
            improvements["vision"] = (
                recent_metrics["avg_vision"] - older_metrics["avg_vision"]
            ) / older_metrics["avg_vision"]
        else:
            improvements["vision"] = 0.0

        return improvements

    def _analyze_trend(
        self,
        improvements: Dict[str, float],
        recent_metrics: Dict[str, float],
        older_metrics: Dict[str, float],
    ) -> tuple[float, str, bool]:
        """Analyze performance trend and determine if it indicates smurfing."""
        # Determine overall improvement
        avg_improvement = statistics.mean(
            [
                improvements["kda"],
                improvements["cs"],
                improvements["vision"],
            ]
        )

        # Classification thresholds
        significant_improvement_threshold = 0.50  # 50% improvement
        moderate_improvement_threshold = 0.25  # 25% improvement

        # Calculate trend score
        if avg_improvement >= significant_improvement_threshold:
            # Sudden major improvement - strong smurf indicator
            trend_score = min(1.0, avg_improvement / 1.0)  # Normalize to 0-1
            trend_type = "sudden_improvement"
            meets_threshold = True
        elif avg_improvement >= moderate_improvement_threshold:
            # Moderate improvement
            trend_score = avg_improvement / 2.0  # Scale down
            trend_type = "moderate_improvement"
            meets_threshold = False
        elif avg_improvement < 0:
            # Declining performance
            trend_score = 0.0
            trend_type = "declining"
            meets_threshold = False
        else:
            # Stable or minimal improvement
            trend_score = 0.0
            trend_type = "stable"
            meets_threshold = False

        # Additional check: if KDA improved significantly (>50%), increase suspicion
        if improvements["kda"] > 0.5:
            trend_score = min(1.0, trend_score + 0.3)
            if not meets_threshold:
                meets_threshold = True

        return trend_score, trend_type, meets_threshold

    def _build_description(
        self,
        improvements: Dict[str, float],
        trend_type: str,
        meets_threshold: bool,
    ) -> str:
        """Generate human-readable description."""
        kda_change = improvements["kda"] * 100
        cs_change = improvements["cs"] * 100
        vision_change = improvements["vision"] * 100

        if meets_threshold:
            return (
                f"Sudden performance improvement: KDA +{kda_change:.0f}%, "
                f"CS +{cs_change:.0f}%, Vision +{vision_change:.0f}%"
            )
        elif trend_type == "moderate_improvement":
            return (
                f"Moderate performance improvement: KDA +{kda_change:.0f}%, "
                f"CS +{cs_change:.0f}%, Vision +{vision_change:.0f}%"
            )
        elif trend_type == "declining":
            return (
                f"Performance declining: KDA {kda_change:+.0f}%, "
                f"CS {cs_change:+.0f}%, Vision {vision_change:+.0f}%"
            )
        else:
            return (
                f"Stable performance: KDA {kda_change:+.0f}%, "
                f"CS {cs_change:+.0f}%, Vision {vision_change:+.0f}%"
            )

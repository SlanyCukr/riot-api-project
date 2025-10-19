"""
Performance consistency factor analyzer for smurf detection.

This module analyzes player performance metrics (KDA, CS, vision) to identify
unusually consistent high performance that may indicate smurfing behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ...schemas.detection import DetectionFactor
from ...utils.statistics import safe_mean, safe_stdev, safe_divide

if TYPE_CHECKING:
    from ...models.players import Player

logger = structlog.get_logger(__name__)


class PerformanceFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for player performance consistency detection factor.

    Analyzes performance metrics across recent matches to identify patterns
    of consistently high performance that may indicate smurfing.
    """

    def __init__(self):
        """Initialize the performance analyzer."""
        super().__init__("performance_consistency")

    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze performance consistency for smurf detection.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session
        :type db: Any
        :returns: DetectionFactor with performance analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(recent_matches)})

        try:
            # Get thresholds
            min_games = self._get_threshold("min_games")
            high_kda = self._get_threshold("high_kda")
            consistency_threshold = self._get_threshold("performance_variance")

            # Check minimum games
            if len(recent_matches) < min_games:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description=f"Insufficient data: {len(recent_matches)}/{min_games} matches",
                    score=0.0,
                )

            # Extract performance metrics
            metrics = self._extract_performance_metrics(recent_matches)

            if not metrics["kda_values"]:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No valid performance data available",
                    score=0.0,
                )

            # Calculate statistics
            avg_kda = safe_mean(metrics["kda_values"])
            kda_std_dev = safe_stdev(metrics["kda_values"])
            avg_cs = safe_mean(metrics["cs_values"])
            avg_vision = safe_mean(metrics["vision_values"])

            # Calculate consistency score
            consistency_score = self._calculate_consistency(avg_kda, kda_std_dev)

            # Check threshold
            meets_threshold = self._check_threshold(
                avg_kda, consistency_score, high_kda, consistency_threshold, min_games
            )

            # Calculate normalized score (0-1)
            score = self._calculate_score(avg_kda, consistency_score, high_kda)

            description = self._build_description(
                avg_kda, consistency_score, meets_threshold
            )

            context = {
                "avg_kda": avg_kda,
                "kda_std_dev": kda_std_dev,
                "avg_cs": avg_cs,
                "avg_vision_score": avg_vision,
                "consistency_score": consistency_score,
                "matches_analyzed": len(recent_matches),
            }

            factor = self._create_factor(
                value=consistency_score,
                meets_threshold=meets_threshold,
                description=description,
                score=score,
                context=context,
            )

            self._log_analysis_result(
                puuid, consistency_score, meets_threshold, score, context
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

    def _extract_performance_metrics(
        self, recent_matches: List[Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """Extract KDA, CS, and vision scores from matches."""
        kda_values: List[float] = []
        cs_values: List[float] = []
        vision_values: List[float] = []

        for match in recent_matches:
            kda = self._calculate_match_kda(match)
            cs = match.get("cs", 0)
            vision = match.get("vision_score", 0)

            if kda > 0:
                kda_values.append(kda)
            if cs > 0:
                cs_values.append(cs)
            if vision > 0:
                vision_values.append(vision)

        return {
            "kda_values": kda_values,
            "cs_values": cs_values,
            "vision_values": vision_values,
        }

    def _calculate_match_kda(self, match: Dict[str, Any]) -> float:
        """Calculate KDA for a single match."""
        kills = match.get("kills", 0)
        deaths = match.get("deaths", 0)
        assists = match.get("assists", 0)

        # If no deaths, return perfect KDA (kills + assists)
        return safe_divide(kills + assists, deaths, default=kills + assists)

    def _calculate_consistency(self, mean: float, std_dev: float) -> float:
        """Calculate consistency score (0.0-1.0, where 1.0 is most consistent)."""
        # Coefficient of variation (lower = more consistent)
        cv = safe_divide(std_dev, mean, default=0.0)

        # Convert to consistency score (inverse of CV, capped at 1.0)
        consistency = max(0.0, 1.0 - cv)
        return consistency

    def _check_threshold(
        self,
        avg_kda: float,
        consistency_score: float,
        high_kda: float,
        consistency_threshold: float,
        min_games: int,
    ) -> bool:
        """Determine if performance meets smurf threshold."""
        # High KDA requirement
        if avg_kda < high_kda:
            return False

        # Consistency requirement (high consistency = low variance)
        if consistency_score < (1.0 - consistency_threshold):
            return False

        return True

    def _calculate_score(
        self, avg_kda: float, consistency_score: float, high_kda: float
    ) -> float:
        """Calculate normalized score (0.0-1.0) for detection factor."""
        if avg_kda < high_kda:
            return 0.0

        # Score based on how much KDA exceeds threshold + consistency
        kda_excess = (avg_kda - high_kda) / high_kda
        kda_score = min(1.0, kda_excess)

        # Weight: 60% KDA performance, 40% consistency
        return kda_score * 0.6 + consistency_score * 0.4

    def _build_description(
        self, avg_kda: float, consistency_score: float, meets_threshold: bool
    ) -> str:
        """Generate human-readable description."""
        consistency_pct = consistency_score * 100

        if meets_threshold:
            return f"Consistently high performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency"
        else:
            return f"Normal performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency"

"""
Performance consistency analysis algorithm for player analysis.

This algorithm analyzes player performance metrics to identify
unusually consistent high performance that may indicate smurf behavior.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import structlog

from ..utils.statistics import safe_mean, safe_stdev, safe_divide

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceResult:
    """Result of performance consistency analysis."""

    avg_kda: float
    kda_std_dev: float
    avg_cs: float
    cs_std_dev: float
    avg_vision_score: float
    consistency_score: float
    meets_threshold: bool
    confidence: float
    description: str


class PerformanceAnalyzer:
    """Analyzes performance consistency for player analysis."""

    def __init__(
        self,
        high_kda_threshold: float = 3.5,
        consistency_threshold: float = 0.3,
        min_games_for_analysis: int = 10,
    ):
        """
        Initialize the performance analyzer.

        Args:
            high_kda_threshold: KDA threshold for high performance
            consistency_threshold: Maximum variance for consistency
            min_games_for_analysis: Minimum games for meaningful analysis
        """
        self.high_kda_threshold = high_kda_threshold
        self.consistency_threshold = consistency_threshold
        self.min_games_for_analysis = min_games_for_analysis

    async def analyze(self, recent_matches: List[Dict[str, Any]]) -> PerformanceResult:
        """
        Analyze performance consistency from recent matches.

        Args:
            recent_matches: List of match data dictionaries

        Returns:
            PerformanceResult with analysis details
        """
        if not recent_matches:
            return self._create_empty_result("No match data available")

        if len(recent_matches) < self.min_games_for_analysis:
            return self._create_empty_result(
                f"Insufficient data: only {len(recent_matches)} matches (needs {self.min_games_for_analysis})"
            )

        # Extract performance metrics
        kda_values: List[float] = []
        cs_values: List[float] = []
        vision_scores: List[float] = []

        for match in recent_matches:
            kda = self._calculate_match_kda(match)
            cs = match.get("cs", 0)
            vision = match.get("vision_score", 0)

            if kda > 0:  # Only include valid KDA values
                kda_values.append(kda)
            if cs > 0:
                cs_values.append(cs)
            if vision > 0:
                vision_scores.append(vision)

        if not kda_values:
            return self._create_empty_result("No valid performance data available")

        # Calculate statistics
        avg_kda: float = safe_mean(kda_values)
        kda_std_dev: float = safe_stdev(kda_values)

        avg_cs: float = safe_mean(cs_values)
        cs_std_dev: float = safe_stdev(cs_values)

        avg_vision_score: float = safe_mean(vision_scores)

        # Calculate consistency metrics
        kda_consistency: float = self._calculate_consistency(avg_kda, kda_std_dev)
        cs_consistency: float = (
            self._calculate_consistency(avg_cs, cs_std_dev) if cs_values else 0.0
        )

        # Overall consistency score (weighted average)
        consistency_score: float = kda_consistency * 0.7 + cs_consistency * 0.3

        # Determine if threshold is met
        meets_threshold: bool = self._meets_smurf_threshold(
            avg_kda, consistency_score, len(recent_matches)
        )

        confidence: float = self._calculate_confidence(len(recent_matches))
        description: str = self._generate_description(
            avg_kda, consistency_score, meets_threshold, len(recent_matches)
        )

        logger.info(
            "Performance analysis completed",
            avg_kda=avg_kda,
            kda_std_dev=kda_std_dev,
            consistency_score=consistency_score,
            meets_threshold=meets_threshold,
        )

        return PerformanceResult(
            avg_kda=avg_kda,
            kda_std_dev=kda_std_dev,
            avg_cs=avg_cs,
            cs_std_dev=cs_std_dev,
            avg_vision_score=avg_vision_score,
            consistency_score=consistency_score,
            meets_threshold=meets_threshold,
            confidence=confidence,
            description=description,
        )

    def _calculate_match_kda(self, match: Dict[str, Any]) -> float:
        """Calculate KDA for a single match."""
        kills = match.get("kills", 0)
        deaths = match.get("deaths", 0)
        assists = match.get("assists", 0)

        # If no deaths, return perfect KDA (kills + assists)
        return safe_divide(kills + assists, deaths, default=kills + assists)

    def _create_empty_result(self, description: str) -> PerformanceResult:
        """
        Create an empty PerformanceResult with all metrics set to zero.

        Args:
            description: Explanation for why result is empty

        Returns:
            PerformanceResult with zero values
        """
        return PerformanceResult(
            avg_kda=0.0,
            kda_std_dev=0.0,
            avg_cs=0.0,
            cs_std_dev=0.0,
            avg_vision_score=0.0,
            consistency_score=0.0,
            meets_threshold=False,
            confidence=0.0,
            description=description,
        )

    def _calculate_consistency(self, mean: float, std_dev: float) -> float:
        """Calculate consistency score (0.0-1.0, where 1.0 is most consistent)."""
        # Coefficient of variation (lower = more consistent)
        cv = safe_divide(std_dev, mean, default=0.0)

        # Convert to consistency score (inverse of CV, capped at 1.0)
        consistency = max(0.0, 1.0 - cv)
        return consistency

    def _meets_smurf_threshold(
        self, avg_kda: float, consistency_score: float, num_games: int
    ) -> bool:
        """Determine if performance meets smurf threshold."""
        # High KDA requirement
        if avg_kda < self.high_kda_threshold:
            return False

        # Consistency requirement (low variance = high consistency)
        if consistency_score < (1.0 - self.consistency_threshold):
            return False

        # Sufficient sample size
        if num_games < self.min_games_for_analysis:
            return False

        return True

    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate confidence in the performance analysis."""
        return min(1.0, sample_size / self.min_games_for_analysis)

    def _generate_description(
        self,
        avg_kda: float,
        consistency_score: float,
        meets_threshold: bool,
        num_games: int,
    ) -> str:
        """Generate human-readable description of performance analysis."""
        consistency_pct: float = consistency_score * 100

        if meets_threshold:
            return f"Consistently high performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency ({num_games} games)"
        else:
            if avg_kda < self.high_kda_threshold:
                return (
                    f"Normal KDA: {avg_kda:.1f} (threshold: {self.high_kda_threshold})"
                )
            else:
                return f"Inconsistent performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency"

    # TODO: Integrate into detection service for enhanced player analysis
    #       Tracks: Temporal performance patterns (improvement/decline over time)
    #       Use case: Detect suddenly improving accounts (bought/boosted)
    #       Integration point: services/detection.py - add to factor scoring
    def analyze_performance_trends(
        self, recent_matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze performance trends over time for additional smurf signals.

        Args:
            recent_matches: List of match data in chronological order

        Returns:
            Dictionary with trend analysis
        """
        if len(recent_matches) < 10:
            return {"trend": "insufficient_data", "score": 0.0}

        # Calculate performance for each match
        match_performances: List[float] = []
        for match in recent_matches:
            kda = self._calculate_match_kda(match)
            cs = match.get("cs", 0)
            vision = match.get("vision_score", 0)

            # Simple performance score (can be enhanced)
            performance_score: float = (
                kda * 0.6 + min(cs / 200, 1.0) * 0.3 + min(vision / 50, 1.0) * 0.1
            )
            match_performances.append(performance_score)

        # Analyze trend
        early_performance: List[float] = match_performances[
            -5:
        ]  # Last 5 matches (oldest)
        recent_performance: List[float] = match_performances[
            :5
        ]  # First 5 matches (newest)

        early_avg: float = safe_mean(early_performance)
        recent_avg: float = safe_mean(recent_performance)

        performance_change: float = recent_avg - early_avg

        # Calculate trend score
        if performance_change > 0.2:  # 20% improvement
            trend_score: float = min(1.0, performance_change * 2)
            trend_type: str = "improving"
        elif performance_change < -0.2:
            trend_score: float = min(1.0, abs(performance_change) * 1.5)
            trend_type: str = "declining"
        else:
            trend_score: float = 0.0
            trend_type: str = "stable"

        # Check for unusually stable high performance (smurf indicator)
        all_avg: float = safe_mean(match_performances)
        all_std: float = safe_stdev(match_performances)
        stability_score: float = self._calculate_consistency(all_avg, all_std)

        is_suspiciously_stable: bool = (
            all_avg > 0.7  # High average performance
            and stability_score > 0.8  # Very consistent
        )

        return {
            "trend": trend_type,
            "trend_score": trend_score,
            "early_performance": early_avg,
            "recent_performance": recent_avg,
            "performance_change": performance_change,
            "overall_performance": all_avg,
            "stability_score": stability_score,
            "is_suspiciously_stable": is_suspiciously_stable,
        }

    def _build_role_performances(
        self, recent_matches: List[Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """Build dictionary mapping roles to KDA performances."""
        role_performances: Dict[str, List[float]] = {}

        for match in recent_matches:
            role = match.get("role", "UNKNOWN")
            kda = self._calculate_match_kda(match)

            if role not in role_performances:
                role_performances[role] = []
            role_performances[role].append(kda)

        return role_performances

    def _calculate_role_statistics(
        self, role_performances: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics for each role with sufficient data."""
        role_stats: Dict[str, Dict[str, Any]] = {}

        for role, kdas in role_performances.items():
            if len(kdas) < 3:  # Skip roles without sufficient data
                continue

            avg_kda = safe_mean(kdas)
            std_dev = safe_stdev(kdas)
            role_stats[role] = {
                "avg_kda": avg_kda,
                "std_dev": std_dev,
                "games_played": len(kdas),
                "consistency": self._calculate_consistency(avg_kda, std_dev),
            }

        return role_stats

    def _detect_suspicious_role_patterns(
        self, role_stats: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Detect suspicious multi-role high performance patterns."""
        if len(role_stats) < 3:
            return []

        high_performance_roles = [
            role
            for role, stats in role_stats.items()
            if stats["avg_kda"] > self.high_kda_threshold
        ]

        if len(high_performance_roles) >= 2:
            return [f"High performance across {len(high_performance_roles)} roles"]

        return []

    def _count_high_performance_roles(
        self, role_stats: Dict[str, Dict[str, Any]]
    ) -> int:
        """Count roles where player exceeds high performance threshold."""
        return sum(
            1
            for stats in role_stats.values()
            if stats["avg_kda"] > self.high_kda_threshold
        )

    # TODO: Integrate into detection service for role-specific smurf patterns
    #       Tracks: Performance consistency across different roles
    #       Use case: Smurfs often excel at one role, boosters at multiple
    #       Integration point: services/detection.py - add role-based scoring
    def analyze_role_performance(
        self, recent_matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze performance across different roles/positions.

        Args:
            recent_matches: List of match data dictionaries

        Returns:
            Dictionary with role-based performance analysis
        """
        role_performances = self._build_role_performances(recent_matches)
        role_stats = self._calculate_role_statistics(role_performances)
        suspicious_patterns = self._detect_suspicious_role_patterns(role_stats)

        return {
            "role_stats": role_stats,
            "suspicious_patterns": suspicious_patterns,
            "role_versatility_score": len(role_stats),
            "consistent_high_performance": self._count_high_performance_roles(
                role_stats
            ),
        }

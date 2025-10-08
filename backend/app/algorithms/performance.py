"""
Performance consistency analysis algorithm for smurf detection.

This algorithm analyzes player performance metrics to identify
unusually consistent high performance that may indicate smurf behavior.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import statistics
import structlog

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
    """Analyzes performance consistency for smurf detection."""

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
            return PerformanceResult(
                avg_kda=0.0,
                kda_std_dev=0.0,
                avg_cs=0.0,
                cs_std_dev=0.0,
                avg_vision_score=0.0,
                consistency_score=0.0,
                meets_threshold=False,
                confidence=0.0,
                description="No match data available",
            )

        if len(recent_matches) < self.min_games_for_analysis:
            return PerformanceResult(
                avg_kda=0.0,
                kda_std_dev=0.0,
                avg_cs=0.0,
                cs_std_dev=0.0,
                avg_vision_score=0.0,
                consistency_score=0.0,
                meets_threshold=False,
                confidence=0.0,
                description=f"Insufficient data: only {len(recent_matches)} matches (needs {self.min_games_for_analysis})",
            )

        # Extract performance metrics
        kda_values = []
        cs_values = []
        vision_scores = []

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
            return PerformanceResult(
                avg_kda=0.0,
                kda_std_dev=0.0,
                avg_cs=0.0,
                cs_std_dev=0.0,
                avg_vision_score=0.0,
                consistency_score=0.0,
                meets_threshold=False,
                confidence=0.0,
                description="No valid performance data available",
            )

        # Calculate statistics
        avg_kda = statistics.mean(kda_values)
        kda_std_dev = statistics.stdev(kda_values) if len(kda_values) > 1 else 0.0

        avg_cs = statistics.mean(cs_values) if cs_values else 0.0
        cs_std_dev = statistics.stdev(cs_values) if len(cs_values) > 1 else 0.0

        avg_vision_score = statistics.mean(vision_scores) if vision_scores else 0.0

        # Calculate consistency metrics
        kda_consistency = self._calculate_consistency(avg_kda, kda_std_dev)
        cs_consistency = (
            self._calculate_consistency(avg_cs, cs_std_dev) if cs_values else 0.0
        )

        # Overall consistency score (weighted average)
        consistency_score = kda_consistency * 0.7 + cs_consistency * 0.3

        # Determine if threshold is met
        meets_threshold = self._meets_smurf_threshold(
            avg_kda, consistency_score, len(recent_matches)
        )

        confidence = self._calculate_confidence(len(recent_matches))
        description = self._generate_description(
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

        if deaths == 0:
            return kills + assists
        return (kills + assists) / deaths

    def _calculate_consistency(self, mean: float, std_dev: float) -> float:
        """Calculate consistency score (0.0-1.0, where 1.0 is most consistent)."""
        if mean == 0:
            return 0.0

        # Coefficient of variation (lower = more consistent)
        cv = std_dev / mean

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
        consistency_pct = consistency_score * 100

        if meets_threshold:
            return f"Consistently high performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency ({num_games} games)"
        else:
            if avg_kda < self.high_kda_threshold:
                return (
                    f"Normal KDA: {avg_kda:.1f} (threshold: {self.high_kda_threshold})"
                )
            else:
                return f"Inconsistent performance: {avg_kda:.1f} KDA, {consistency_pct:.0f}% consistency"

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
        match_performances = []
        for match in recent_matches:
            kda = self._calculate_match_kda(match)
            cs = match.get("cs", 0)
            vision = match.get("vision_score", 0)

            # Simple performance score (can be enhanced)
            performance_score = (
                kda * 0.6 + min(cs / 200, 1.0) * 0.3 + min(vision / 50, 1.0) * 0.1
            )
            match_performances.append(performance_score)

        # Analyze trend
        early_performance = match_performances[-5:]  # Last 5 matches (oldest)
        recent_performance = match_performances[:5]  # First 5 matches (newest)

        early_avg = statistics.mean(early_performance)
        recent_avg = statistics.mean(recent_performance)

        performance_change = recent_avg - early_avg

        # Calculate trend score
        if performance_change > 0.2:  # 20% improvement
            trend_score = min(1.0, performance_change * 2)
            trend_type = "improving"
        elif performance_change < -0.2:
            trend_score = min(1.0, abs(performance_change) * 1.5)
            trend_type = "declining"
        else:
            trend_score = 0.0
            trend_type = "stable"

        # Check for unusually stable high performance (smurf indicator)
        all_avg = statistics.mean(match_performances)
        all_std = statistics.stdev(match_performances)
        stability_score = self._calculate_consistency(all_avg, all_std)

        is_suspiciously_stable = (
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
        role_performances = {}

        for match in recent_matches:
            role = match.get("role", "UNKNOWN")
            kda = self._calculate_match_kda(match)

            if role not in role_performances:
                role_performances[role] = []
            role_performances[role].append(kda)

        # Calculate statistics for each role
        role_stats = {}
        for role, kdas in role_performances.items():
            if len(kdas) >= 3:  # Only analyze roles with sufficient data
                role_stats[role] = {
                    "avg_kda": statistics.mean(kdas),
                    "std_dev": statistics.stdev(kdas) if len(kdas) > 1 else 0.0,
                    "games_played": len(kdas),
                    "consistency": self._calculate_consistency(
                        statistics.mean(kdas),
                        statistics.stdev(kdas) if len(kdas) > 1 else 0.0,
                    ),
                }

        # Check for suspicious patterns
        suspicious_patterns = []
        if len(role_stats) >= 3:
            # Check if player performs exceptionally well across multiple roles
            high_performance_roles = [
                role
                for role, stats in role_stats.items()
                if stats["avg_kda"] > self.high_kda_threshold
            ]

            if len(high_performance_roles) >= 2:
                suspicious_patterns.append(
                    f"High performance across {len(high_performance_roles)} roles"
                )

        return {
            "role_stats": role_stats,
            "suspicious_patterns": suspicious_patterns,
            "role_versatility_score": len(role_stats),
            "consistent_high_performance": len(
                [
                    r
                    for r, s in role_stats.items()
                    if s["avg_kda"] > self.high_kda_threshold
                ]
            ),
        }

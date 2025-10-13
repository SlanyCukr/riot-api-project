"""
Win rate analysis algorithm for smurf detection.

This algorithm analyzes player win rates over recent matches to identify
suspiciously high win rates that may indicate smurf behavior.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WinRateResult:
    """Result of win rate analysis."""

    win_rate: float
    wins: int
    total_games: int
    meets_threshold: bool
    confidence: float
    description: str


class WinRateAnalyzer:
    """Analyzes win rate patterns for smurf detection."""

    def __init__(self, threshold: float = 0.65, min_games: int = 30):
        """
        Initialize the win rate analyzer.

        Args:
            threshold: Win rate threshold (0.0-1.0) to flag as suspicious
            min_games: Minimum number of games required for analysis
        """
        self.threshold = threshold
        self.min_games = min_games

    async def analyze(self, recent_matches: List[Dict[str, Any]]) -> WinRateResult:
        """
        Analyze win rate factor from recent matches.

        Args:
            recent_matches: List of match data dictionaries

        Returns:
            WinRateResult with analysis details
        """
        if not recent_matches:
            return WinRateResult(
                win_rate=0.0,
                wins=0,
                total_games=0,
                meets_threshold=False,
                confidence=0.0,
                description="No match data available",
            )

        wins = sum(1 for match in recent_matches if match.get("win", False))
        total_games = len(recent_matches)
        win_rate = wins / total_games if total_games > 0 else 0.0

        # Calculate confidence based on sample size
        confidence = self._calculate_confidence(total_games)

        # Determine if threshold is met (only with sufficient games)
        meets_threshold = win_rate >= self.threshold and total_games >= self.min_games

        description = self._generate_description(
            win_rate, wins, total_games, meets_threshold
        )

        logger.info(
            "Win rate analysis completed",
            win_rate=win_rate,
            wins=wins,
            total_games=total_games,
            meets_threshold=meets_threshold,
            confidence=confidence,
        )

        return WinRateResult(
            win_rate=win_rate,
            wins=wins,
            total_games=total_games,
            meets_threshold=meets_threshold,
            confidence=confidence,
            description=description,
        )

    def _calculate_confidence(self, sample_size: int) -> float:
        """
        Calculate confidence in the win rate based on sample size.

        Args:
            sample_size: Number of games analyzed

        Returns:
            Confidence score (0.0-1.0)
        """
        if sample_size < self.min_games:
            return sample_size / self.min_games
        return 1.0

    def _generate_description(
        self, win_rate: float, wins: int, total_games: int, meets_threshold: bool
    ) -> str:
        """
        Generate human-readable description of win rate analysis.

        Args:
            win_rate: Calculated win rate
            wins: Number of wins
            total_games: Total games
            meets_threshold: Whether threshold is met

        Returns:
            Description string
        """
        if total_games < self.min_games:
            return f"Insufficient data: {win_rate:.1%} win rate ({wins}/{total_games} games, needs {self.min_games})"

        if meets_threshold:
            return f"High win rate: {win_rate:.1%} ({wins}/{total_games} games)"
        else:
            return f"Normal win rate: {win_rate:.1%} ({wins}/{total_games} games)"

    def calculate_win_rate_score(self, win_rate: float, total_games: int) -> float:
        """
        Calculate a normalized score for win rate factor.

        Args:
            win_rate: Player's win rate
            total_games: Number of games analyzed

        Returns:
            Normalized score (0.0-1.0)
        """
        if total_games < self.min_games:
            return 0.0

        # Score increases exponentially above threshold
        if win_rate >= self.threshold:
            excess = win_rate - self.threshold
            return min(1.0, 0.5 + (excess * 5))  # Scale excess win rate
        else:
            return 0.0

    # TODO: Integrate into detection service for win rate evolution tracking
    #       Tracks: Changes in win rate over time (improving vs declining)
    #       Use case: Sudden win rate spike = smurf/booster, gradual improvement = legitimate improvement
    #       Integration point: services/detection.py - add temporal win rate factor
    def analyze_win_rate_trend(
        self, recent_matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze win rate trend over time for additional smurf signals.

        Args:
            recent_matches: List of match data in chronological order

        Returns:
            Dictionary with trend analysis
        """
        if len(recent_matches) < 10:
            return {"trend": "insufficient_data", "score": 0.0}

        # Split matches into recent and older halves
        mid_point = len(recent_matches) // 2
        older_matches = recent_matches[mid_point:]
        recent_half = recent_matches[:mid_point]

        older_wins = sum(1 for m in older_matches if m.get("win", False))
        recent_wins = sum(1 for m in recent_half if m.get("win", False))

        older_rate = older_wins / len(older_matches) if older_matches else 0.0
        recent_rate = recent_wins / len(recent_half) if recent_half else 0.0

        trend_improvement = recent_rate - older_rate

        # Calculate trend score
        if trend_improvement > 0.1:  # 10% improvement
            trend_score = min(1.0, trend_improvement * 3)
            trend_type = "improving"
        elif trend_improvement < -0.1:
            trend_score = min(1.0, abs(trend_improvement) * 2)
            trend_type = "declining"
        else:
            trend_score = 0.0
            trend_type = "stable"

        return {
            "trend": trend_type,
            "score": trend_score,
            "older_win_rate": older_rate,
            "recent_win_rate": recent_rate,
            "improvement": trend_improvement,
        }

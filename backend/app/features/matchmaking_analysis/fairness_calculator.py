"""Fairness calculator for matchmaking analysis metrics."""

from typing import List
import statistics
import structlog

logger = structlog.get_logger(__name__)


class FairnessCalculator:
    """Calculates various fairness metrics for matchmaking analysis.

    Supports configurable weights and improved normalization for fairness scoring.
    """

    def __init__(
        self,
        winrate_weight: float = 0.6,
        rank_weight: float = 0.4,
        max_rank_difference: float = 800.0,
    ):
        """Initialize fairness calculator with configurable weights.

        Args:
            winrate_weight: Weight for winrate fairness (0.0-1.0)
            rank_weight: Weight for rank fairness (0.0-1.0)
            max_rank_difference: Maximum expected rank difference for normalization
        """
        # Validate and normalize weights
        total_weight = winrate_weight + rank_weight
        if total_weight == 0:
            raise ValueError("Sum of weights cannot be zero")

        self.winrate_weight = winrate_weight / total_weight
        self.rank_weight = rank_weight / total_weight
        self.max_rank_difference = max_rank_difference

        logger.debug(
            "fairness_calculator_initialized",
            winrate_weight=self.winrate_weight,
            rank_weight=self.rank_weight,
            max_rank_diff=self.max_rank_difference,
        )

    def calculate_player_winrate(self, wins: List[bool]) -> float:
        """Calculate player's winrate from match results.

        Args:
            wins: List of win/loss results (True for win, False for loss)

        Returns:
            Winrate as float between 0.0-1.0
        """
        if not wins:
            return 0.0

        win_count = sum(1 for win in wins if win)
        return win_count / len(wins)

    def calculate_average_winrate(self, winrates: List[float]) -> float:
        """Calculate average winrate from a list of winrates.

        Args:
            winrates: List of winrate values

        Returns:
            Average winrate as float between 0.0-1.0
        """
        if not winrates:
            return 0.0

        return statistics.mean(winrates)

    def calculate_average_rank_difference(self, rank_differences: List[float]) -> float:
        """Calculate average rank difference between teams.

        Args:
            rank_differences: List of rank difference values

        Returns:
            Average rank difference
        """
        if not rank_differences:
            return 0.0

        return statistics.mean(rank_differences)

    def calculate_fairness_score(
        self, team_avg_winrate: float, enemy_avg_winrate: float, avg_rank_difference: float
    ) -> float:
        """Calculate matchmaking fairness score based on multiple factors.

        Uses configurable weights and improved normalization for better accuracy.

        Args:
            team_avg_winrate: Average winrate of player's teammates
            enemy_avg_winrate: Average winrate of enemy team
            avg_rank_difference: Average rank difference between teams

        Returns:
            Fairness score between 0.0 (unfair) and 1.0 (perfectly fair)
        """
        # Winrate fairness: closer team and enemy winrates are better
        # Maximum winrate difference is 1.0 (100%), normalize to 0-1
        winrate_difference = abs(team_avg_winrate - enemy_avg_winrate)
        winrate_fairness = max(0.0, 1.0 - winrate_difference)

        # Rank fairness: smaller rank differences are better
        # Normalize using configured max_rank_difference
        # If rank_diff >= max, fairness = 0; if rank_diff = 0, fairness = 1
        rank_fairness = max(0.0, 1.0 - (avg_rank_difference / self.max_rank_difference))

        # Combine factors with configured weights
        fairness_score = (winrate_fairness * self.winrate_weight) + (
            rank_fairness * self.rank_weight
        )

        # Ensure score is between 0.0 and 1.0 (should already be, but safeguard)
        final_score = max(0.0, min(1.0, fairness_score))

        logger.debug(
            "fairness_calculated",
            team_winrate=team_avg_winrate,
            enemy_winrate=enemy_avg_winrate,
            rank_diff=avg_rank_difference,
            winrate_fairness=winrate_fairness,
            rank_fairness=rank_fairness,
            winrate_weight=self.winrate_weight,
            rank_weight=self.rank_weight,
            final_score=final_score,
        )

        return final_score
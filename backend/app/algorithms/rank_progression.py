"""
Rank progression analysis algorithm for player analysis.

This algorithm analyzes player rank progression to identify unusually
rapid climbing that may indicate smurf behavior.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from ..models.ranks import PlayerRank, Tier

logger = structlog.get_logger(__name__)


@dataclass
class RankProgressionResult:
    """Result of rank progression analysis."""

    current_tier: str
    current_rank: Optional[str]
    peak_tier: str
    peak_rank: Optional[str]
    progression_speed: float
    tier_jumps: int
    time_to_current: Optional[int]
    meets_threshold: bool
    confidence: float
    description: str


class RankProgressionAnalyzer:
    """Analyzes rank progression patterns for player analysis."""

    def __init__(
        self,
        tier_jump_threshold: int = 2,
        rapid_progression_days: int = 30,
        min_games_for_analysis: int = 20,
    ):
        """
        Initialize the rank progression analyzer.

        Args:
            tier_jump_threshold: Number of tier jumps to flag as suspicious
            rapid_progression_days: Days to consider for rapid progression
            min_games_for_analysis: Minimum games for meaningful analysis
        """
        self.tier_jump_threshold = tier_jump_threshold
        self.rapid_progression_days = rapid_progression_days
        self.min_games_for_analysis = min_games_for_analysis

        # Tier hierarchy for progression calculation
        self.tier_hierarchy = {
            Tier.IRON: 0,
            Tier.BRONZE: 1,
            Tier.SILVER: 2,
            Tier.GOLD: 3,
            Tier.PLATINUM: 4,
            Tier.EMERALD: 5,
            Tier.DIAMOND: 6,
            Tier.MASTER: 7,
            Tier.GRANDMASTER: 8,
            Tier.CHALLENGER: 9,
        }

    async def analyze(self, puuid: str, db: AsyncSession) -> RankProgressionResult:
        """
        Analyze rank progression factor for a player.

        Args:
            puuid: Player PUUID
            db: Database session

        Returns:
            RankProgressionResult with analysis details
        """
        # Get player's rank history
        rank_history = await self._get_rank_history(puuid, db)

        if not rank_history:
            return RankProgressionResult(
                current_tier="UNRANKED",
                current_rank=None,
                peak_tier="UNRANKED",
                peak_rank=None,
                progression_speed=0.0,
                tier_jumps=0,
                time_to_current=None,
                meets_threshold=False,
                confidence=0.0,
                description="No rank data available",
            )

        current_rank = rank_history[0]  # Most recent rank
        peak_rank = self._find_peak_rank(rank_history)

        # Calculate progression metrics
        progression_speed = self._calculate_progression_speed(rank_history)
        tier_jumps = self._count_tier_jumps(rank_history)
        time_to_current = self._calculate_time_to_current(rank_history)

        # Determine if threshold is met
        meets_threshold = self._meets_smurf_threshold(
            progression_speed, tier_jumps, rank_history
        )

        confidence = self._calculate_confidence(rank_history, meets_threshold)
        description = self._generate_description(
            current_rank, peak_rank, progression_speed, tier_jumps, meets_threshold
        )

        logger.info(
            "Rank progression analysis completed",
            puuid=puuid,
            current_tier=current_rank.tier,
            peak_tier=peak_rank.tier,
            progression_speed=progression_speed,
            tier_jumps=tier_jumps,
            meets_threshold=meets_threshold,
        )

        return RankProgressionResult(
            current_tier=current_rank.tier,
            current_rank=current_rank.rank,
            peak_tier=peak_rank.tier,
            peak_rank=peak_rank.rank,
            progression_speed=progression_speed,
            tier_jumps=tier_jumps,
            time_to_current=time_to_current,
            meets_threshold=meets_threshold,
            confidence=confidence,
            description=description,
        )

    async def _get_rank_history(self, puuid: str, db: AsyncSession) -> List[PlayerRank]:
        """Get player's rank history ordered by date."""
        query = (
            select(PlayerRank)
            .where(PlayerRank.puuid == puuid)
            .order_by(desc(PlayerRank.created_at))
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    def _find_peak_rank(self, rank_history: List[PlayerRank]) -> PlayerRank:
        """Find the highest rank achieved by the player."""
        peak_rank = rank_history[0]
        peak_score = self._calculate_rank_score(peak_rank)

        for rank in rank_history[1:]:
            current_score = self._calculate_rank_score(rank)
            if current_score > peak_score:
                peak_rank = rank
                peak_score = current_score

        return peak_rank

    def _calculate_rank_score(self, rank: PlayerRank) -> int:
        """Calculate numeric score for a rank."""
        tier_score = self.tier_hierarchy.get(Tier(rank.tier), 0)
        rank_score = 4 - (ord(rank.rank) - ord("I")) if rank.rank else 0
        return tier_score * 100 + rank_score * 25 + rank.league_points

    def _calculate_progression_speed(self, rank_history: List[PlayerRank]) -> float:
        """Calculate how quickly the player is climbing."""
        if len(rank_history) < 2:
            return 0.0

        # Calculate progression over the most recent period
        recent_ranks = rank_history[: min(5, len(rank_history))]

        if len(recent_ranks) < 2:
            return 0.0

        current_score = self._calculate_rank_score(recent_ranks[0])
        oldest_score = self._calculate_rank_score(recent_ranks[-1])

        time_diff = (recent_ranks[0].created_at - recent_ranks[-1].created_at).days

        if time_diff == 0:
            return 0.0

        score_diff = current_score - oldest_score
        return score_diff / time_diff  # Score per day

    def _count_tier_jumps(self, rank_history: List[PlayerRank]) -> int:
        """Count significant tier jumps in rank history."""
        if len(rank_history) < 2:
            return 0

        tier_jumps = 0
        current_tier_level: int = self.tier_hierarchy.get(Tier(rank_history[0].tier), 0)

        for rank in rank_history[1:]:
            tier_level: int = self.tier_hierarchy.get(Tier(rank.tier), 0)
            if tier_level > current_tier_level:
                tier_jumps += tier_level - current_tier_level
            current_tier_level = tier_level

        return tier_jumps

    def _calculate_time_to_current(
        self, rank_history: List[PlayerRank]
    ) -> Optional[int]:
        """Calculate days taken to reach current rank from lowest."""
        if len(rank_history) < 2:
            return None

        # Find the lowest rank in history
        lowest_rank = min(rank_history, key=lambda r: self._calculate_rank_score(r))

        time_diff = (rank_history[0].created_at - lowest_rank.created_at).days
        return max(0, time_diff)

    def _meets_smurf_threshold(
        self, progression_speed: float, tier_jumps: int, rank_history: List[PlayerRank]
    ) -> bool:
        """Determine if rank progression meets smurf threshold."""
        # Check for rapid tier jumps
        if tier_jumps >= self.tier_jump_threshold:
            return True

        # Check for rapid progression speed
        if progression_speed > 50:  # 50+ LP per day
            return True

        # Check for suspiciously fast climb to high ranks
        if len(rank_history) >= 2:
            current_rank = rank_history[0]
            time_to_current = self._calculate_time_to_current(rank_history)

            if (
                time_to_current
                and time_to_current < self.rapid_progression_days
                and self.tier_hierarchy.get(Tier(current_rank.tier), 0)
                >= self.tier_hierarchy[Tier.GOLD]
            ):
                return True

        return False

    def _calculate_confidence(
        self, rank_history: List[PlayerRank], meets_threshold: bool
    ) -> float:
        """Calculate confidence in the rank progression analysis."""
        if not rank_history:
            return 0.0

        base_confidence = min(
            1.0, len(rank_history) / 10
        )  # More history = more confidence

        if meets_threshold:
            return min(1.0, base_confidence * 1.2)  # Boost confidence if threshold met

        return base_confidence

    def _generate_description(
        self,
        current_rank: PlayerRank,
        peak_rank: PlayerRank,
        progression_speed: float,
        tier_jumps: int,
        meets_threshold: bool,
    ) -> str:
        """Generate human-readable description of rank progression."""
        current_display = current_rank.display_rank
        peak_display = peak_rank.display_rank

        if meets_threshold:
            if tier_jumps >= self.tier_jump_threshold:
                return f"Rapid tier climbing: {tier_jumps} tier jumps, currently {current_display}"
            elif progression_speed > 50:
                return f"Fast progression: {progression_speed:.1f} LP/day, currently {current_display}"
            else:
                return f"Suspicious rank progression: {current_display} (peak: {peak_display})"
        else:
            return f"Normal rank progression: {current_display} (peak: {peak_display})"

    # TODO: Integrate into detection service for rank vs performance analysis
    #       Tracks: Players performing significantly above/below their rank
    #       Use case: High KDA in low rank = smurf signal, low KDA in high rank = boosted signal
    #       Integration point: services/detection.py - add discrepancy factor to scoring
    def analyze_rank_discrepancy(
        self, current_rank: PlayerRank, performance_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze discrepancy between current rank and performance metrics.

        Args:
            current_rank: Player's current rank
            performance_metrics: Dictionary with performance stats

        Returns:
            Dictionary with discrepancy analysis
        """
        # Handle UNRANKED tier (not in Tier enum)
        if current_rank.tier == "UNRANKED":
            return {
                "discrepancy_score": 0.0,
                "is_suspicious": False,
                "expected_kda": 1.0,
                "actual_kda": performance_metrics.get("kda", 0.0),
                "expected_win_rate": 0.50,
                "actual_win_rate": performance_metrics.get("win_rate", 0.0),
                "tier_mismatch": False,
                "note": "Player is unranked - no tier comparison available",
            }

        tier_level: int = self.tier_hierarchy.get(Tier(current_rank.tier), 0)

        # Expected performance metrics for this tier
        expected_kda = {
            0: 1.0,  # Iron
            1: 1.2,  # Bronze
            2: 1.5,  # Silver
            3: 2.0,  # Gold
            4: 2.5,  # Platinum
            5: 3.0,  # Emerald
            6: 3.5,  # Diamond
            7: 4.0,  # Master+
        }

        expected_win_rate = {
            0: 0.45,  # Iron
            1: 0.48,  # Bronze
            2: 0.50,  # Silver
            3: 0.52,  # Gold
            4: 0.54,  # Platinum
            5: 0.56,  # Emerald
            6: 0.58,  # Diamond
            7: 0.60,  # Master+
        }

        actual_kda = performance_metrics.get("kda", 0.0)
        actual_win_rate = performance_metrics.get("win_rate", 0.0)

        expected_kda_value = expected_kda.get(tier_level, 2.0)
        expected_win_rate_value = expected_win_rate.get(tier_level, 0.50)

        kda_discrepancy = max(0, actual_kda - expected_kda_value)
        win_rate_discrepancy = max(0, actual_win_rate - expected_win_rate_value)

        # Calculate overall discrepancy score
        discrepancy_score = kda_discrepancy * 0.6 + win_rate_discrepancy * 0.4
        is_suspicious = discrepancy_score > 0.15  # 15% or more above expected

        return {
            "discrepancy_score": discrepancy_score,
            "is_suspicious": is_suspicious,
            "expected_kda": expected_kda_value,
            "actual_kda": actual_kda,
            "expected_win_rate": expected_win_rate_value,
            "actual_win_rate": actual_win_rate,
            "tier_mismatch": is_suspicious,
        }

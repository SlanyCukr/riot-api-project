"""
Rank progression factor analyzer for smurf detection.

This module analyzes player rank progression to identify unusually
rapid climbing that may indicate smurf behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from sqlalchemy import select, desc
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor
from app.features.players.ranks import PlayerRank
from app.core.enums import Tier

if TYPE_CHECKING:
    from app.features.players.models import Player

logger = structlog.get_logger(__name__)


class RankProgressionFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for rank progression detection factor.

    Analyzes rank history to identify rapid climbing patterns
    that may indicate smurfing behavior.
    """

    # Tier hierarchy for progression calculation
    TIER_HIERARCHY = {
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

    def __init__(self):
        """Initialize the rank progression analyzer."""
        super().__init__("rank_progression")

    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze rank progression for smurf detection.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session
        :type db: Any
        :returns: DetectionFactor with rank progression analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid)

        try:
            # Get rank history from database
            rank_history = await self._get_rank_history(puuid, db)

            if not rank_history:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No rank data available",
                    score=0.0,
                )

            # Calculate progression metrics
            current_rank = rank_history[0]
            progression_speed = self._calculate_progression_speed(rank_history)
            tier_jumps = self._count_tier_jumps(rank_history)

            # Get thresholds
            tier_jump_threshold = self._get_threshold("rank_tier_jump")
            rapid_progression_days = 30  # Configuration constant

            # Determine if threshold is met
            meets_threshold = self._check_threshold(
                progression_speed,
                tier_jumps,
                tier_jump_threshold,
                rank_history,
                rapid_progression_days,
            )

            # Calculate score
            score = self._calculate_score(progression_speed, tier_jumps)

            # Build description
            description = self._build_description(
                current_rank, progression_speed, tier_jumps, meets_threshold
            )

            context = {
                "current_tier": current_rank.tier,
                "current_rank": current_rank.rank,
                "progression_speed": progression_speed,
                "tier_jumps": tier_jumps,
                "rank_history_count": len(rank_history),
            }

            factor = self._create_factor(
                value=progression_speed,
                meets_threshold=meets_threshold,
                description=description,
                score=score,
                context=context,
            )

            self._log_analysis_result(
                puuid, progression_speed, meets_threshold, score, context
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

    async def _get_rank_history(self, puuid: str, db: Any) -> List[PlayerRank]:
        """Get player's rank history ordered by date (newest first)."""
        query = (
            select(PlayerRank)
            .where(PlayerRank.puuid == puuid)
            .order_by(desc(PlayerRank.created_at))
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    def _get_tier_level(self, tier_string: str) -> int:
        """Convert tier string to numeric level."""
        try:
            tier_enum = Tier(tier_string)
            tier_level = self.TIER_HIERARCHY.get(tier_enum, 0)
            # Normalize Master+ (7-9) to level 7 for consistency
            return min(tier_level, 7)
        except (ValueError, KeyError):
            logger.warning("Invalid tier value encountered", tier=tier_string)
            return 0

    def _calculate_rank_score(self, rank: PlayerRank) -> int:
        """Calculate numeric score for a rank."""
        # Map Roman numerals to division scores (IV=1, III=2, II=3, I=4)
        division_scores = {"IV": 1, "III": 2, "II": 3, "I": 4}

        tier_score = self._get_tier_level(rank.tier)
        rank_score = division_scores.get(rank.rank, 0) if rank.rank else 0
        return tier_score * 100 + rank_score * 25 + rank.league_points

    def _calculate_progression_speed(self, rank_history: List[PlayerRank]) -> float:
        """Calculate progression speed (score per day)."""
        if len(rank_history) < 2:
            return 0.0

        # Use most recent 5 ranks for speed calculation
        recent_ranks = rank_history[: min(5, len(rank_history))]

        if len(recent_ranks) < 2:
            return 0.0

        current_score = self._calculate_rank_score(recent_ranks[0])
        oldest_score = self._calculate_rank_score(recent_ranks[-1])

        time_diff = (recent_ranks[0].created_at - recent_ranks[-1].created_at).days

        if time_diff == 0:
            return 0.0

        score_diff = current_score - oldest_score
        return score_diff / time_diff

    def _count_tier_jumps(self, rank_history: List[PlayerRank]) -> int:
        """Count significant tier jumps in rank history."""
        if len(rank_history) < 2:
            return 0

        tier_jumps = 0
        current_tier_level = self._get_tier_level(rank_history[0].tier)

        for rank in rank_history[1:]:
            tier_level = self._get_tier_level(rank.tier)
            if tier_level > current_tier_level:
                tier_jumps += tier_level - current_tier_level
            current_tier_level = tier_level

        return tier_jumps

    def _check_threshold(
        self,
        progression_speed: float,
        tier_jumps: int,
        tier_jump_threshold: int,
        rank_history: List[PlayerRank],
        rapid_progression_days: int,
    ) -> bool:
        """Determine if rank progression meets smurf threshold."""
        # Check for rapid tier jumps
        if tier_jumps >= tier_jump_threshold:
            return True

        # Check for rapid progression speed (50+ LP per day)
        if progression_speed > 50:
            return True

        # Check for suspiciously fast climb to high ranks
        if len(rank_history) >= 2:
            current_rank = rank_history[0]
            time_to_current = self._calculate_time_to_current(rank_history)

            if (
                time_to_current
                and time_to_current < rapid_progression_days
                and self._get_tier_level(current_rank.tier)
                >= self.TIER_HIERARCHY[Tier.GOLD]
            ):
                return True

        return False

    def _calculate_time_to_current(
        self, rank_history: List[PlayerRank]
    ) -> Optional[int]:
        """Calculate days taken to reach current rank from lowest."""
        if len(rank_history) < 2:
            return None

        lowest_rank = min(rank_history, key=lambda r: self._calculate_rank_score(r))
        time_diff = (rank_history[0].created_at - lowest_rank.created_at).days
        return max(0, time_diff)

    def _calculate_score(self, progression_speed: float, tier_jumps: int) -> float:
        """Calculate normalized score (0.0-1.0) for detection factor."""
        # Score based on progression speed and tier jumps
        speed_score = min(1.0, progression_speed / 100)  # 100+ LP/day = max score
        jump_score = min(1.0, tier_jumps / 3)  # 3+ tier jumps = max score

        # Weight: 60% speed, 40% jumps
        return speed_score * 0.6 + jump_score * 0.4

    def _build_description(
        self,
        current_rank: PlayerRank,
        progression_speed: float,
        tier_jumps: int,
        meets_threshold: bool,
    ) -> str:
        """Generate human-readable description."""
        current_display = current_rank.display_rank

        if meets_threshold:
            if tier_jumps >= 2:
                return f"Rapid tier climbing: {tier_jumps} tier jumps, currently {current_display}"
            else:
                return f"Fast progression: {progression_speed:.1f} LP/day, currently {current_display}"
        else:
            return f"Normal rank progression: {current_display}"

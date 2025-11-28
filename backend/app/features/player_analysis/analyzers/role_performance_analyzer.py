"""
Role performance factor analyzer for player analysis.

This module analyzes player performance across different roles to identify
versatility that may indicate smurfing behavior.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from dataclasses import dataclass
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM
    from app.features.players.ranks import PlayerRank

logger = structlog.get_logger(__name__)


@dataclass
class RoleStats:
    """Statistics for a single role."""

    role: str
    games_played: int
    win_rate: float
    avg_kda: float
    avg_cs: float
    avg_vision: float


class RolePerformanceFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for role performance detection factor.

    Analyzes player performance across different roles to identify high
    performance in multiple roles that may indicate smurfing behavior.
    """

    # Role mapping from lane to standard role names
    ROLE_MAPPING = {
        "TOP": "TOP",
        "JUNGLE": "JUNGLE",
        "MIDDLE": "MID",
        "MID": "MID",
        "BOTTOM": "ADC",
        "DUO_CARRY": "ADC",
        "SUPPORT": "SUPPORT",
        "DUO_SUPPORT": "SUPPORT",
    }

    def __init__(self):
        """Initialize the role performance analyzer."""
        super().__init__("role_performance")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze role performance for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with role performance analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid, {"match_count": len(matches_data)})

        try:
            if not matches_data:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="No match data available for role analysis",
                    score=0.0,
                )

            # Collect role statistics
            role_stats = self._collect_role_statistics(matches_data)

            if len(role_stats) < 2:
                return self._create_factor(
                    value=0.0,
                    meets_threshold=False,
                    description="Insufficient role diversity: need 2+ roles played",
                    score=0.0,
                )

            # Analyze performance across roles
            analysis = self._analyze_role_performance(role_stats)

            # Build description
            description = self._build_description(role_stats, analysis)

            context = {
                "roles_played": len(role_stats),
                "roles_with_good_performance": analysis["roles_above_threshold"],
                "top_roles": analysis["top_roles"],
                "total_diversity_score": analysis["diversity_score"],
                "role_stats": {
                    role: {
                        "games": stats.games_played,
                        "win_rate": stats.win_rate,
                        "kda": stats.avg_kda,
                    }
                    for role, stats in role_stats.items()
                },
            }

            factor = self._create_factor(
                value=analysis["diversity_score"],
                meets_threshold=analysis["meets_threshold"],
                description=description,
                score=analysis["score"],
                context=context,
            )

            self._log_analysis_result(
                puuid,
                analysis["diversity_score"],
                analysis["meets_threshold"],
                analysis["score"],
                context,
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

    def _collect_role_statistics(
        self, matches_data: List[Dict[str, Any]]
    ) -> Dict[str, RoleStats]:
        """Collect performance statistics for each role."""
        role_data: Dict[str, List[Dict[str, Any]]] = {}

        # Group matches by role
        for match in matches_data:
            # Get role from match data
            role = self._extract_role(match)

            if not role:
                continue

            if role not in role_data:
                role_data[role] = []

            role_data[role].append(match)

        # Calculate statistics for each role
        role_stats = {}
        min_games_per_role = 3  # Minimum games to consider a role

        for role, matches in role_data.items():
            if len(matches) < min_games_per_role:
                # Skip roles with too few games
                continue

            stats = self._calculate_role_stats(role, matches)
            role_stats[role] = stats

        return role_stats

    def _extract_role(self, match: Dict[str, Any]) -> str | None:
        """Extract role from match data."""
        # Try different possible field names
        role = match.get("role") or match.get("lane") or match.get("team_position")

        if role:
            # Map to standard role name
            return self.ROLE_MAPPING.get(role, role)

        # Infer from champion if role not available
        # (This is a fallback and may not be accurate)
        champion = match.get("champion_name", "").lower()
        if champion in ["thresh", "blitzcrank", "leona", "braum"]:
            return "SUPPORT"
        elif champion in ["vayne", "jinx", "caitlyn", "jhin"]:
            return "ADC"
        elif champion in ["lee sin", "khazix", "graves"]:
            return "JUNGLE"
        elif champion in ["yasuo", "zed", "katarina"]:
            return "MID"

        return None

    def _calculate_role_stats(
        self, role: str, matches: List[Dict[str, Any]]
    ) -> RoleStats:
        """Calculate statistics for a specific role."""
        if not matches:
            return RoleStats(
                role=role,
                games_played=0,
                win_rate=0.0,
                avg_kda=0.0,
                avg_cs=0.0,
                avg_vision=0.0,
            )

        games = len(matches)

        # Calculate win rate
        wins = sum(1 for match in matches if match.get("win", False))
        win_rate = wins / games if games > 0 else 0.0

        # Calculate average metrics
        kda_sum = 0.0
        cs_sum = 0.0
        vision_sum = 0.0
        valid_matches = 0

        for match in matches:
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

            kda_sum += kda
            if cs > 0:
                cs_sum += cs
            if vision > 0:
                vision_sum += vision

            valid_matches += 1

        avg_kda = kda_sum / valid_matches if valid_matches > 0 else 0.0
        avg_cs = cs_sum / valid_matches if valid_matches > 0 else 0.0
        avg_vision = vision_sum / valid_matches if valid_matches > 0 else 0.0

        return RoleStats(
            role=role,
            games_played=games,
            win_rate=win_rate,
            avg_kda=avg_kda,
            avg_cs=avg_cs,
            avg_vision=avg_vision,
        )

    def _analyze_role_performance(
        self, role_stats: Dict[str, RoleStats]
    ) -> Dict[str, Any]:
        """Analyze performance across roles."""
        # Define thresholds for "good" performance
        good_win_rate_threshold = 0.55  # 55% win rate
        good_kda_threshold = 3.0  # 3.0 KDA

        # Count roles with good performance
        roles_above_threshold = 0
        top_roles = []

        for role, stats in role_stats.items():
            is_good = (
                stats.win_rate >= good_win_rate_threshold
                and stats.avg_kda >= good_kda_threshold
            )
            if is_good:
                roles_above_threshold += 1
                top_roles.append(
                    {
                        "role": role,
                        "win_rate": stats.win_rate,
                        "kda": stats.avg_kda,
                    }
                )

        # Sort top roles by win rate
        top_roles.sort(key=lambda r: r["win_rate"], reverse=True)

        # Calculate diversity score
        diversity_score = self._calculate_diversity_score(role_stats)

        # Determine if threshold is met
        # Smurf indicator: good performance in 2+ roles
        meets_threshold = roles_above_threshold >= 2

        # Calculate final score
        score = self._calculate_score(roles_above_threshold, diversity_score)

        return {
            "roles_above_threshold": roles_above_threshold,
            "top_roles": top_roles,
            "diversity_score": diversity_score,
            "meets_threshold": meets_threshold,
            "score": score,
        }

    def _calculate_diversity_score(self, role_stats: Dict[str, RoleStats]) -> float:
        """Calculate how diverse the player's role usage is."""
        if not role_stats:
            return 0.0

        # Count total games
        total_games = sum(stats.games_played for stats in role_stats.values())

        # Calculate distribution entropy
        import math

        entropy = 0.0
        for stats in role_stats.values():
            proportion = stats.games_played / total_games
            if proportion > 0:
                entropy -= proportion * math.log(proportion, 2)

        # Normalize entropy (max for 5 roles is log2(5) ≈ 2.32)
        max_entropy = math.log(len(role_stats), 2)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        return normalized_entropy

    def _calculate_score(
        self, roles_above_threshold: int, diversity_score: float
    ) -> float:
        """Calculate normalized score based on role performance."""
        # Score based on number of roles with good performance
        if roles_above_threshold >= 3:
            base_score = 1.0
        elif roles_above_threshold == 2:
            base_score = 0.6
        elif roles_above_threshold == 1:
            base_score = 0.3
        else:
            base_score = 0.0

        # Boost score based on diversity
        score = base_score + (diversity_score * 0.2)

        # Cap at 1.0
        return min(1.0, score)

    def _build_description(
        self, role_stats: Dict[str, RoleStats], analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable description."""
        roles_above = analysis["roles_above_threshold"]

        if roles_above == 0:
            role_list = ", ".join(sorted(role_stats.keys()))
            return f"Specialized player: primarily plays {role_list} with average performance"
        elif roles_above == 1:
            top_role = analysis["top_roles"][0]["role"]
            return f"Single-role specialist: good performance in {top_role}"
        elif roles_above >= 2:
            role_list = ", ".join([r["role"] for r in analysis["top_roles"][:3]])
            return f"Multi-role excellence: good performance in {len(analysis['top_roles'])} roles ({role_list})"
        else:
            return f"Role versatility: plays {len(role_stats)} roles"

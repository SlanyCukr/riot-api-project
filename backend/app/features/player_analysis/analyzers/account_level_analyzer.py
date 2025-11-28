"""
Account level factor analyzer for player analysis.

This module analyzes player account levels as part of the player analysis
algorithm, looking for low account levels that may indicate new accounts.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ..schemas import DetectionFactor

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM
    from app.features.players.ranks import PlayerRank

logger = structlog.get_logger(__name__)


class AccountLevelFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for player account level detection factor.

    Analyzes account levels to identify very new accounts
    that may be more likely to be smurfs.
    """

    def __init__(self):
        """Initialize the account level analyzer."""
        super().__init__("account_level")

    async def analyze(
        self,
        puuid: str,
        matches_data: List[Dict[str, Any]],
        player_data: "PlayerORM",
        rank_history: Optional[List["PlayerRank"]],
    ) -> DetectionFactor:
        """
        Analyze account level for player analysis.

        :param puuid: Player PUUID
        :type puuid: str
        :param matches_data: Pre-fetched match data (not used for this analyzer)
        :type matches_data: List[Dict[str, Any]]
        :param player_data: Pre-fetched player ORM instance
        :type player_data: PlayerORM
        :param rank_history: Pre-fetched rank history (not used by this analyzer)
        :type rank_history: Optional[List[PlayerRank]]
        :returns: DetectionFactor with account level analysis results
        :rtype: DetectionFactor
        """
        self._log_analysis_start(puuid)

        try:
            account_level = player_data.account_level or 0
            low_account_level_threshold = self._get_threshold("low_account_level")

            # Check if account level is suspiciously low
            meets_threshold = account_level <= low_account_level_threshold

            # Calculate score based on how low the account level is
            # Very low levels get higher scores
            if account_level <= 10:
                score = 0.8
            elif account_level <= 25:
                score = 0.5
            elif account_level <= low_account_level_threshold:
                score = 0.3
            else:
                score = 0.0

            description = (
                f"Account level: {account_level}. "
                f"Low level threshold: {low_account_level_threshold}"
            )

            factor = self._create_factor(
                value=float(account_level),
                meets_threshold=meets_threshold,
                description=description,
                score=score,
                context={
                    "account_level": account_level,
                    "threshold": low_account_level_threshold,
                },
            )

            self._log_analysis_result(
                puuid,
                float(account_level),
                meets_threshold,
                score,
                {"account_level": account_level},
            )

            return factor

        except Exception as e:
            return self._create_error_factor(e, puuid)

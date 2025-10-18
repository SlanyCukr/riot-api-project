"""
Account level factor analyzer for smurf detection.

This module analyzes player account levels as part of the smurf detection
algorithm, looking for low account levels that may indicate new accounts.
"""

from typing import TYPE_CHECKING, Dict, Any, List
import structlog

from .base_analyzer import BaseFactorAnalyzer
from ...schemas.detection import DetectionFactor

if TYPE_CHECKING:
    from ..models.players import Player

logger = structlog.get_logger(__name__)


class AccountLevelFactorAnalyzer(BaseFactorAnalyzer):
    """
    Analyzer for player account level detection factor.

    Analyzes account levels to identify very new accounts
    that may be more likely to be smurfs.
    """

    def __init__(self):
        super().__init__("account_level")

    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze account level for smurf detection.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data (not used for this analyzer)
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session (not used for this analyzer)
        :type db: Any
        :returns: DetectionFactor with account level analysis results
        :rtype: DetectionFactor
        """

        self._log_analysis_start(puuid)

        try:
            account_level = player.account_level or 0
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

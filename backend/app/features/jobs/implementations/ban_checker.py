"""Ban Checker Job - Checks ban status for flagged players.

This job checks if players flagged as smurfs have been banned. It's designed
to run infrequently (daily) as ban checks are not time-sensitive.
"""

from contextlib import asynccontextmanager
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseJob
from ..error_handling import handle_riot_api_errors
from app.core.riot_api.client import RiotAPIClient
from app.features.players.service import PlayerService
from app.core import get_global_settings, get_riot_api_key

logger = structlog.get_logger(__name__)


class BanCheckerJob(BaseJob):
    """Job that checks ban status for flagged players."""

    def __init__(self, job_config_id: int):
        """Initialize the ban checker job."""
        super().__init__(job_config_id)
        self.settings = get_global_settings()

        self.api_client: Optional[RiotAPIClient] = None
        self.player_service: Optional[PlayerService] = None

    def _load_configuration(self) -> None:
        """Load job configuration from database.

        :raises ValueError: If required configuration is missing.
        """
        if not self.job_config:
            raise ValueError("Job configuration not loaded")

        config = self.job_config.config_json or {}

        # Required configuration - fail hard if missing
        self.ban_check_days = config.get("ban_check_days")
        self.max_checks_per_run = config.get("max_checks_per_run")

        # Validate all required fields exist
        required_fields = {
            "ban_check_days": self.ban_check_days,
            "max_checks_per_run": self.max_checks_per_run,
        }

        missing = [k for k, v in required_fields.items() if v is None]
        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")

    def _record_api_request(self, metric: str, count: int) -> None:
        """Track API request counts for job metrics.

        :param metric: Name of the metric being recorded.
        :param count: Number of requests made.
        """
        if metric == "requests_made":
            self.increment_metric("api_requests_made", count)

    @asynccontextmanager
    async def _service_resources(self, db: AsyncSession):
        """Initialize services and API client."""
        try:
            # Get API key from database first, fallback to environment
            api_key = await get_riot_api_key(db)

            self.api_client = RiotAPIClient(
                api_key=api_key,
                region=self.settings.riot_region,
                platform=self.settings.riot_platform,
                request_callback=self._record_api_request,
            )
            self.player_service = PlayerService(db)

            yield

        finally:
            # Clean up resources
            if self.api_client:
                await self.api_client.close()
            self.api_client = None
            self.player_service = None

    async def execute(self, db: AsyncSession) -> None:
        """Execute the ban checker job.

        :param db: Database session for job execution.
        """
        # Load configuration from database
        self._load_configuration()

        logger.info("Starting ban checker job", job_id=self.job_config.id)

        execution_summary = {
            "ban_checks": 0,
            "bans_found": 0,
        }

        async with self._service_resources(db):
            await self._ban_check_phase(execution_summary)

        self._log_execution_summary(execution_summary)
        logger.info("Ban checker completed", **execution_summary)

    @handle_riot_api_errors(
        operation="ban check",
        critical=False,
        log_context=lambda self, execution_summary: {},
    )
    async def _ban_check_phase(self, execution_summary: dict) -> None:
        """Check ban status for flagged players."""
        # Exit early if service not initialized
        if not self.player_service:
            return

        players = await self.player_service.get_players_for_ban_check(
            days=self.ban_check_days,
            limit=self.max_checks_per_run,
        )

        # Exit early if no players need checking
        if not players:
            logger.info("No players need ban check")
            return

        logger.info("Checking ban status", count=len(players))

        for player in players:
            is_banned = await self._check_player_ban(player, execution_summary)
            # Error decorator handles failures, so we get None on error
            if is_banned is not None:
                execution_summary["ban_checks"] += 1
                self.increment_metric("records_updated")
                if is_banned:
                    execution_summary["bans_found"] += 1
                    logger.info("Player possibly banned", puuid=player.puuid)

    @handle_riot_api_errors(
        operation="check player ban status",
        critical=False,
        log_context=lambda self, player, execution_summary: {"puuid": player.puuid},
    )
    async def _check_player_ban(
        self, player, execution_summary: dict
    ) -> Optional[bool]:
        """Check if a player is banned.

        :param player: Player to check ban status for.
        :param execution_summary: Execution summary dict for tracking metrics.
        :returns: True if banned, False if not banned, None if error occurred.
        """
        return await self.player_service.check_ban_status(player, self.api_client)

    def _log_execution_summary(self, execution_summary: dict) -> None:
        """Log execution summary to job execution log."""
        for key, value in execution_summary.items():
            self.add_log_entry(key, value)

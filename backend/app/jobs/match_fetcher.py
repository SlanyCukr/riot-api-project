"""Match Fetcher Job - Fetches new matches for discovered players.

This job fetches match history from Riot API for discovered players who need
more matches for analysis. It's designed to be API-rate-limit friendly.
"""

from contextlib import asynccontextmanager
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from .error_handling import handle_riot_api_errors
from app.core.riot_api.client import RiotAPIClient
from ..services.players import PlayerService
from ..services.matches import MatchService
from app.core import get_global_settings, get_riot_api_key

logger = structlog.get_logger(__name__)


class MatchFetcherJob(BaseJob):
    """Job that fetches new matches for discovered players."""

    def __init__(self, job_config_id: int):
        """Initialize the match fetcher job."""
        super().__init__(job_config_id)
        self.settings = get_global_settings()

        self.api_client: Optional[RiotAPIClient] = None
        self.player_service: Optional[PlayerService] = None
        self.match_service: Optional[MatchService] = None
        self.db: Optional[AsyncSession] = None

    def _load_configuration(self) -> None:
        """Load job configuration from database.

        :raises ValueError: If required configuration is missing.
        """
        if not self.job_config:
            raise ValueError("Job configuration not loaded")

        config = self.job_config.config_json or {}

        # Required configuration - fail hard if missing
        self.discovered_players_per_run = config.get("discovered_players_per_run")
        self.matches_per_player_per_run = config.get("matches_per_player_per_run")
        self.target_matches_per_player = config.get("target_matches_per_player")

        # Validate all required fields exist
        required_fields = {
            "discovered_players_per_run": self.discovered_players_per_run,
            "matches_per_player_per_run": self.matches_per_player_per_run,
            "target_matches_per_player": self.target_matches_per_player,
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
        self.db = db

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
            self.match_service = MatchService(db)

            yield

        finally:
            # Clean up resources
            if self.api_client:
                await self.api_client.close()
            self.api_client = None
            self.player_service = None
            self.match_service = None
            self.db = None

    async def execute(self, db: AsyncSession) -> None:
        """Execute the match fetcher job.

        :param db: Database session for job execution.
        """
        # Load configuration from database
        self._load_configuration()

        logger.info("Starting match fetcher job", job_id=self.job_config.id)

        execution_summary = {
            "players_processed": 0,
            "matches_fetched": 0,
        }

        async with self._service_resources(db):
            await self._fetch_phase(execution_summary)

        self._log_execution_summary(execution_summary)
        logger.info("Match fetcher completed", **execution_summary)

    @handle_riot_api_errors(
        operation="fetch player matches",
        critical=False,
        log_context=lambda self, execution_summary: {},
    )
    async def _fetch_phase(self, execution_summary: dict) -> None:
        """Fetch match history for players needing more matches."""
        # Exit early if services not initialized
        if not self.player_service or not self.match_service:
            return

        players = await self.player_service.get_players_needing_matches(
            limit=self.discovered_players_per_run,
            target_matches=self.target_matches_per_player,
        )

        # Exit early if no players need matches
        if not players:
            logger.info("No players need match history")
            return

        logger.info("Fetching matches for players", count=len(players))

        for player in players:
            logger.debug(
                "Starting match fetch for player",
                puuid=player.puuid,
                platform=player.platform,
            )

            matches_fetched = await self._fetch_player_matches(
                player, execution_summary
            )
            # Error decorator handles failures, so we get None on error
            if matches_fetched is not None:
                execution_summary["players_processed"] += 1
                execution_summary["matches_fetched"] += matches_fetched
                self.increment_metric("records_created", matches_fetched)

                logger.debug(
                    "Completed match fetch for player",
                    puuid=player.puuid,
                    matches_fetched=matches_fetched,
                )
            else:
                logger.debug(
                    "No new matches fetched for player",
                    puuid=player.puuid,
                )

    @handle_riot_api_errors(
        operation="fetch matches for player",
        critical=False,
        log_context=lambda self, player, execution_summary: {"puuid": player.puuid},
    )
    async def _fetch_player_matches(
        self, player, execution_summary: dict
    ) -> Optional[int]:
        """Fetch matches for a single player.

        :param player: Player to fetch matches for.
        :param execution_summary: Execution summary dict for tracking metrics.
        :returns: Number of matches fetched, or None if error occurred.
        """
        matches_fetched = await self.match_service.fetch_and_store_matches_for_player(
            riot_api_client=self.api_client,
            puuid=player.puuid,
            count=self.matches_per_player_per_run,
            queue=420,
            platform=player.platform,
        )

        # Mark player as exhausted if no new matches were fetched
        if matches_fetched == 0:
            player.matches_exhausted = True
            await self.safe_commit(
                self.db,
                "mark player matches exhausted",
                on_success=lambda: self.increment_metric("records_updated"),
            )
            logger.info("Player marked as matches exhausted", puuid=player.puuid)
            return None

        return matches_fetched

    def _log_execution_summary(self, execution_summary: dict) -> None:
        """Log execution summary to job execution log."""
        for key, value in execution_summary.items():
            self.add_log_entry(key, value)

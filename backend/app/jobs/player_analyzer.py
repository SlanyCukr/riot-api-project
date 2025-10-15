"""Player Analyzer Job - Analyzes discovered players for smurf/boosted status.

This job:
1. Fetches match history for discovered players
2. Analyzes players with sufficient match data
3. Checks ban status for players flagged as smurfs
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from .error_handling import handle_riot_api_errors
from ..models.job_tracking import JobConfiguration
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..services.detection import SmurfDetectionService
from ..services.players import PlayerService
from ..services.matches import MatchService
from ..config import get_global_settings, get_riot_api_key

logger = structlog.get_logger(__name__)


class PlayerAnalyzerJob(BaseJob):
    """Job that analyzes discovered players for smurf/boosted status."""

    def __init__(self, job_config: JobConfiguration):
        super().__init__(job_config)
        self.settings = get_global_settings()

        config = job_config.config_json or {}
        self.discovered_players_per_run = config.get("discovered_players_per_run", 8)
        self.matches_per_player_per_run = config.get("matches_per_player_per_run", 10)
        self.target_matches_per_player = config.get("target_matches_per_player", 50)
        self.unanalyzed_players_per_run = config.get("unanalyzed_players_per_run", 20)
        self.ban_check_days = config.get("ban_check_days", 7)

        self.api_client: Optional[RiotAPIClient] = None
        self.data_manager: Optional[RiotDataManager] = None
        self.player_service: Optional[PlayerService] = None
        self.match_service: Optional[MatchService] = None
        self.detection_service: Optional[SmurfDetectionService] = None
        self.db: Optional[AsyncSession] = None

    @asynccontextmanager
    async def _service_resources(self, db: AsyncSession):
        self.db = db

        # Get API key from database first, fallback to environment
        # Pass the db session so it can query settings without creating a new engine
        api_key = await get_riot_api_key(db)

        self.api_client = RiotAPIClient(
            api_key=api_key,
            region=self.settings.riot_region,
            platform=self.settings.riot_platform,
            request_callback=self._record_api_request,
        )
        self.data_manager = RiotDataManager(db, self.api_client)
        self.player_service = PlayerService(db, self.data_manager)
        self.match_service = MatchService(db, self.data_manager)
        self.detection_service = SmurfDetectionService(db, self.data_manager)

        try:
            yield
        finally:
            if self.api_client:
                await self.api_client.close()
            self.api_client = None
            self.data_manager = None
            self.player_service = None
            self.match_service = None
            self.detection_service = None
            self.db = None

    def _record_api_request(self, metric: str, count: int) -> None:
        """Track API request counts for job metrics.

        :param metric: Name of the metric being recorded.
        :param count: Number of requests made.
        """
        if metric == "requests_made":
            self.increment_metric("api_requests_made", count)

    async def execute(self, db: AsyncSession) -> None:
        """Execute the player analyzer job.

        :param db: Database session for job execution.
        """
        logger.info("Starting player analyzer job", job_id=self.job_config.id)

        execution_summary = {
            "players_processed": 0,
            "matches_fetched": 0,
            "players_analyzed": 0,
            "smurfs_detected": 0,
            "ban_checks": 0,
            "bans_found": 0,
        }

        async with self._service_resources(db):
            await self._fetch_phase(execution_summary)
            await self._analyze_phase(execution_summary)
            await self._ban_check_phase(execution_summary)

        self._log_execution_summary(execution_summary)
        logger.info("Player analyzer completed", **execution_summary)

    # ============================================
    # Phase 1: Fetch Matches
    # ============================================

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
            matches_fetched = await self._fetch_player_matches(
                player, execution_summary
            )
            # Error decorator handles failures, so we get None on error
            if matches_fetched is not None:
                execution_summary["players_processed"] += 1
                execution_summary["matches_fetched"] += matches_fetched
                self.increment_metric("records_created", matches_fetched)

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
            puuid=player.puuid,
            count=self.matches_per_player_per_run,
            queue=420,
            platform=player.platform,
        )

        # Return None if no matches were fetched (signals skip to caller)
        if matches_fetched == 0:
            return None

        return matches_fetched

    @handle_riot_api_errors(
        operation="analyze players",
        critical=False,
        log_context=lambda self, execution_summary: {},
    )
    async def _analyze_phase(self, execution_summary: dict) -> None:
        """Analyze players with sufficient match history."""
        # Exit early if services not initialized
        if not self.player_service or not self.detection_service or not self.db:
            return

        players = await self.player_service.get_players_ready_for_analysis(
            limit=self.unanalyzed_players_per_run,
            min_matches=20,
        )

        # Exit early if no players ready
        if not players:
            logger.info("No players ready for analysis")
            return

        logger.info("Analyzing players", count=len(players))

        for player in players:
            result = await self._analyze_single_player(player, execution_summary)
            # Error decorator handles failures, so we get None on error
            if result is not None:
                execution_summary["players_analyzed"] += 1
                if result.is_smurf:
                    execution_summary["smurfs_detected"] += 1

    @handle_riot_api_errors(
        operation="analyze player",
        critical=False,
        log_context=lambda self, player, execution_summary: {"puuid": player.puuid},
    )
    async def _analyze_single_player(self, player, execution_summary: dict):
        """Analyze a single player for smurf detection.

        :param player: Player to analyze.
        :param execution_summary: Execution summary dict for tracking metrics.
        :returns: Detection result, or None if error occurred.
        """
        result = await self.detection_service.analyze_player(
            puuid=player.puuid,
            min_games=20,
            queue_filter=420,
            force_reanalyze=True,
        )

        player.is_analyzed = True
        player.updated_at = datetime.now()
        await self.db.commit()
        self.increment_metric("records_updated")

        logger.info(
            "Player analyzed",
            puuid=player.puuid,
            is_smurf=result.is_smurf,
            score=result.detection_score,
        )

        return result

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
            limit=10,
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
        return await self.player_service.check_ban_status(player)

    # Private helper methods

    def _log_execution_summary(self, execution_summary: dict) -> None:
        """Log execution summary to job execution log."""
        for key, value in execution_summary.items():
            self.add_log_entry(key, value)

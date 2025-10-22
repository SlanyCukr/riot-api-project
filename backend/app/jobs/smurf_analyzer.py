"""Smurf Analyzer Job - Analyzes players for smurf/boosted behavior.

This job analyzes players using existing database data. It makes NO Riot API calls,
so it can run frequently without rate limit concerns.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from .error_handling import handle_riot_api_errors
from app.core.riot_api.data_manager import RiotDataManager
from ..services.detection import SmurfDetectionService
from ..services.players import PlayerService
from app.core import get_global_settings

logger = structlog.get_logger(__name__)


class SmurfAnalyzerJob(BaseJob):
    """Job that analyzes players for smurf/boosted behavior (NO API CALLS)."""

    def __init__(self, job_config_id: int):
        """Initialize the smurf analyzer job."""
        super().__init__(job_config_id)
        self.settings = get_global_settings()

        self.data_manager: Optional[RiotDataManager] = None
        self.player_service: Optional[PlayerService] = None
        self.detection_service: Optional[SmurfDetectionService] = None
        self.db: Optional[AsyncSession] = None

    def _load_configuration(self) -> None:
        """Load job configuration from database.

        :raises ValueError: If required configuration is missing.
        """
        if not self.job_config:
            raise ValueError("Job configuration not loaded")

        config = self.job_config.config_json or {}

        # Required configuration - fail hard if missing
        self.unanalyzed_players_per_run = config.get("unanalyzed_players_per_run")
        self.min_matches_required = config.get("min_matches_required")

        # Validate all required fields exist
        required_fields = {
            "unanalyzed_players_per_run": self.unanalyzed_players_per_run,
            "min_matches_required": self.min_matches_required,
        }

        missing = [k for k, v in required_fields.items() if v is None]
        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")

    @asynccontextmanager
    async def _service_resources(self, db: AsyncSession):
        """Initialize services (NO API CLIENT - pure database work)."""
        self.db = db

        try:
            # Note: No RiotAPIClient needed - pure database analysis!
            # We pass None for api_client in RiotDataManager (it won't make API calls)
            self.data_manager = RiotDataManager(db, None)
            self.player_service = PlayerService(db)
            self.detection_service = SmurfDetectionService(db, self.data_manager)

            yield

        finally:
            # Clean up resources
            self.data_manager = None
            self.player_service = None
            self.detection_service = None
            self.db = None

    async def execute(self, db: AsyncSession) -> None:
        """Execute the smurf analyzer job.

        :param db: Database session for job execution.
        """
        # Load configuration from database
        self._load_configuration()

        logger.info("Starting smurf analyzer job", job_id=self.job_config.id)

        execution_summary = {
            "players_analyzed": 0,
            "smurfs_detected": 0,
        }

        async with self._service_resources(db):
            await self._analyze_phase(execution_summary)

        self._log_execution_summary(execution_summary)
        logger.info("Smurf analyzer completed", **execution_summary)

    def _update_analysis_summary(self, execution_summary: dict, result) -> None:
        """Update execution summary with analysis result."""
        if result is not None:
            execution_summary["players_analyzed"] += 1
            if result.is_smurf:
                execution_summary["smurfs_detected"] += 1

    async def _analyze_phase(self, execution_summary: dict) -> None:
        """Analyze players with sufficient match history."""
        # Exit early if services not initialized
        if not self.player_service or not self.detection_service or not self.db:
            return

        players = await self.player_service.get_players_ready_for_analysis(
            limit=self.unanalyzed_players_per_run,
            min_matches=self.min_matches_required,
        )

        # Exit early if no players ready
        if not players:
            logger.info("No players ready for analysis")
            return

        logger.info("Analyzing players", count=len(players))

        for player in players:
            result = await self._analyze_single_player(player, execution_summary)
            # Error decorator handles failures, so we get None on error
            self._update_analysis_summary(execution_summary, result)

    @handle_riot_api_errors(
        operation="analyze player",
        critical=False,
        log_context=lambda self, player, execution_summary: {"puuid": player.puuid},
    )
    async def _analyze_single_player(self, player, execution_summary: dict):
        """Analyze a single player for smurf behavior.

        :param player: Player to analyze.
        :param execution_summary: Execution summary dict for tracking metrics.
        :returns: Detection result, or None if error occurred.
        """
        result = await self.detection_service.analyze_player(
            puuid=player.puuid,
            min_games=self.min_matches_required,
            queue_filter=420,
            force_reanalyze=True,
        )

        player.is_analyzed = True
        player.updated_at = datetime.now()
        await self.safe_commit(
            self.db,
            "player analysis",
            on_success=lambda: self.increment_metric("records_updated"),
        )

        logger.info(
            "Player analyzed",
            puuid=player.puuid,
            is_smurf=result.is_smurf,
            score=result.detection_score,
        )

        return result

    def _log_execution_summary(self, execution_summary: dict) -> None:
        """Log execution summary to job execution log."""
        for key, value in execution_summary.items():
            self.add_log_entry(key, value)

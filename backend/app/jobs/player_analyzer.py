"""Player Analyzer Job - Simplified version for analyzing discovered players."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from ..models.players import Player
from ..models.job_tracking import JobConfiguration
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError
from ..services.detection import SmurfDetectionService
from ..services.players import PlayerService
from ..services.matches import MatchService
from ..config import get_global_settings

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
        self.api_client = RiotAPIClient(
            api_key=self.settings.riot_api_key,
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
        """Track API request counts for job metrics."""
        if metric == "requests_made":
            self.increment_metric("api_requests_made", count)

    async def execute(self, db: AsyncSession) -> None:
        logger.info("Starting player analyzer job", job_id=self.job_config.id)

        summary = {
            "players_processed": 0,
            "matches_fetched": 0,
            "players_analyzed": 0,
            "smurfs_detected": 0,
            "ban_checks": 0,
            "bans_found": 0,
        }

        async with self._service_resources(db):
            await self._fetch_phase(summary)
            await self._analyze_phase(summary)
            await self._ban_check_phase(summary)

        for key, value in summary.items():
            self.add_log_entry(key, value)

        logger.info(
            "Player analyzer completed",
            **summary,
        )

    # ============================================
    # Phase 1: Fetch Matches
    # ============================================

    async def _fetch_phase(self, summary: dict) -> None:
        if not self.player_service or not self.match_service:
            return

        players = await self.player_service.get_players_needing_matches(
            limit=self.discovered_players_per_run,
            target_matches=self.target_matches_per_player,
        )

        if not players:
            logger.info("No players need match history")
            return

        logger.info("Fetching matches for players", count=len(players))

        for player in players:
            try:
                matches_fetched = (
                    await self.match_service.fetch_and_store_matches_for_player(
                        puuid=player.puuid,
                        count=self.matches_per_player_per_run,
                        queue=420,
                        platform=player.platform,
                    )
                )

                if matches_fetched > 0:
                    summary["players_processed"] += 1
                    summary["matches_fetched"] += matches_fetched
                    self.increment_metric("records_created", matches_fetched)

            except RateLimitError:
                logger.warning("Rate limit hit, stopping match fetch")
                break
            except Exception as error:
                logger.warning(
                    "Failed to fetch matches",
                    puuid=player.puuid,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                continue

    async def _analyze_phase(self, summary: dict) -> None:
        if not self.player_service or not self.detection_service or not self.db:
            return

        players = await self.player_service.get_players_ready_for_analysis(
            limit=self.unanalyzed_players_per_run,
            min_matches=20,
        )

        if not players:
            logger.info("No players ready for analysis")
            return

        logger.info("Analyzing players", count=len(players))

        for player in players:
            try:
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

                summary["players_analyzed"] += 1
                if result.is_smurf:
                    summary["smurfs_detected"] += 1

                logger.info(
                    "Player analyzed",
                    puuid=player.puuid,
                    is_smurf=result.is_smurf,
                    score=result.detection_score,
                )

            except RateLimitError:
                logger.warning("Rate limit hit during analysis")
                break
            except Exception as error:
                logger.warning(
                    "Failed to analyze player",
                    puuid=player.puuid,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                await self.db.rollback()
                continue

    async def _ban_check_phase(self, summary: dict) -> None:
        if not self.player_service:
            return

        players = await self.player_service.get_players_for_ban_check(
            days=self.ban_check_days,
            limit=10,
        )

        if not players:
            logger.info("No players need ban check")
            return

        logger.info("Checking ban status", count=len(players))

        for player in players:
            try:
                is_banned = await self.player_service.check_ban_status(player)

                summary["ban_checks"] += 1
                self.increment_metric("records_updated")
                if is_banned:
                    summary["bans_found"] += 1
                    logger.info("Player possibly banned", puuid=player.puuid)

            except RateLimitError:
                logger.warning("Rate limit hit during ban check")
                break
            except Exception as error:
                logger.warning(
                    "Ban check failed",
                    puuid=player.puuid,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                continue

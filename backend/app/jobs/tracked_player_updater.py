"""Tracked Player Updater Job - Updates match history and rank for tracked players."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from .error_handling import handle_riot_api_errors
from ..models.players import Player
from ..models.job_tracking import JobConfiguration
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import NotFoundError
from ..config import get_global_settings, get_riot_api_key

logger = structlog.get_logger(__name__)


class TrackedPlayerUpdaterJob(BaseJob):
    """Job that updates match history and rank for tracked players.

    This job:
    1. Fetches all players marked as tracked (is_tracked=True)
    2. For each tracked player:
       - Fetches new matches since last check
       - Stores match details and participants
       - Marks new discovered players (is_tracked=False, is_analyzed=False)
       - Updates player rank
    3. Respects API rate limits with backoff
    4. Logs progress and metrics
    """

    def __init__(self, job_config: JobConfiguration):
        """Initialize tracked player updater job.

        :param job_config: Job configuration from database.
        :type job_config: JobConfiguration
        """
        super().__init__(job_config)
        self.settings = get_global_settings()

        # Extract configuration (use settings defaults for consistency across environments)
        config = job_config.config_json or {}
        self.max_new_matches_per_player = config.get(
            "max_new_matches_per_player", self.settings.max_new_matches_per_player
        )
        self.max_tracked_players = config.get(
            "max_tracked_players", self.settings.max_tracked_players
        )

        # Initialize Riot API client (will be created in execute)
        self.api_client: Optional[RiotAPIClient] = None
        self.data_manager: Optional[RiotDataManager] = None

    @asynccontextmanager
    async def _riot_resources(self, db: AsyncSession):
        """Async context manager for Riot API resources.

        :param db: Database session.
        :type db: AsyncSession
        :yields: None - sets up API client and data manager
        """
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
        try:
            yield
        finally:
            if self.api_client:
                await self.api_client.close()
            self.api_client = None
            self.data_manager = None

    def _record_api_request(self, metric: str, count: int) -> None:
        """Record API request metrics from Riot API client callbacks.

        :param metric: Name of the metric being recorded.
        :type metric: str
        :param count: Number of requests made.
        :type count: int
        """
        if metric == "requests_made":
            self.increment_metric("api_requests_made", count)

    async def execute(self, db: AsyncSession) -> None:
        """Execute the tracked player updater job.

        :param db: Database session for job execution.
        :type db: AsyncSession
        """
        logger.info(
            "Starting tracked player updater job",
            job_id=self.job_config.id,
            max_new_matches=self.max_new_matches_per_player,
        )

        summary = {
            "total": 0,
            "processed": 0,
            "matches": 0,
            "discovered": 0,
            "skipped": [],
            "tracked_ids": [],
        }

        async with self._riot_resources(db):
            tracked_players = await self._get_tracked_players(db)
            summary["total"] = len(tracked_players)
            summary["tracked_ids"] = [p.puuid for p in tracked_players]

            # Exit early if no tracked players
            if not tracked_players:
                logger.info("No tracked players found, job complete")
                self._log_summary_to_execution_log(summary)
                return

            logger.debug(
                "Found tracked players to update",
                count=len(tracked_players),
                player_ids=summary["tracked_ids"],
            )

            for player in tracked_players:
                player_result = await self._sync_tracked_player(db, player)
                # None if non-critical error occurred
                if player_result is not None:
                    summary["processed"] += 1
                    summary["matches"] += player_result["matches"]
                    summary["discovered"] += player_result["discovered"]

        self._log_summary_to_execution_log(summary)

        logger.debug(
            "Tracked player updater job completed successfully",
            api_requests=self.metrics["api_requests_made"],
            records_created=self.metrics["records_created"],
            records_updated=self.metrics["records_updated"],
            players_processed=summary["processed"],
            matches_ingested=summary["matches"],
            players_discovered=summary["discovered"],
        )

    async def _get_tracked_players(self, db: AsyncSession) -> List[Player]:
        """Get all players marked as tracked.

        :param db: Database session.
        :type db: AsyncSession
        :returns: List of tracked players.
        :rtype: List[Player]
        """
        stmt = (
            select(Player)
            .where(Player.is_tracked)
            .where(Player.is_active)
            .limit(self.max_tracked_players)
        )
        result = await db.execute(stmt)
        players = result.scalars().all()
        return list(players)

    @handle_riot_api_errors(
        operation="update tracked player",
        critical=False,
        log_context=lambda self, db, player: {"puuid": player.puuid},
    )
    async def _sync_tracked_player(
        self, db: AsyncSession, player: Player
    ) -> Dict[str, int]:
        """Synchronize tracked player's matches and rank.

        :param db: Database session.
        :type db: AsyncSession
        :param player: Player to synchronize.
        :type player: Player
        :returns: Summary statistics.
        :rtype: Dict[str, int]
        """
        logger.info(
            "Updating tracked player",
            puuid=player.puuid,
            riot_id=f"{player.riot_id}#{player.tag_line}",
        )

        new_matches = await self._fetch_new_matches(db, player)

        if not new_matches:
            logger.info("No new matches found for player", puuid=player.puuid)
        else:
            logger.info(
                "Found new matches for player",
                puuid=player.puuid,
                match_count=len(new_matches),
            )

        matches_processed = 0
        players_discovered = 0

        for match_id in new_matches:
            discovered = await self._process_match(db, match_id, player)
            if discovered is not None:  # None if non-critical error occurred
                players_discovered += discovered
                matches_processed += 1

        await self._update_player_rank(db, player)

        player.updated_at = datetime.now()
        await self.safe_commit(
            db,
            "tracked player update",
            on_success=lambda: self.increment_metric("records_updated"),
        )

        logger.info(
            "Successfully updated tracked player",
            puuid=player.puuid,
            new_matches=matches_processed,
            new_players=players_discovered,
        )

        return {"matches": matches_processed, "discovered": players_discovered}

    async def _fetch_new_matches(self, db: AsyncSession, player: Player) -> List[str]:
        """Fetch new match IDs for a player since last check.

        :param db: Database session.
        :type db: AsyncSession
        :param player: Player to fetch matches for.
        :type player: Player
        :returns: List of new match IDs.
        :rtype: List[str]
        """
        try:
            existing_match_count = await self._get_existing_match_count(db, player)
            last_match_time = await self._get_last_match_time(db, player)

            start_time = self._calculate_fetch_start_time(
                last_match_time, existing_match_count, player.puuid
            )

            match_ids = await self._fetch_match_ids_in_batches(player, start_time)
            new_match_ids = await self._filter_new_matches(db, match_ids)

            logger.info(
                "Filtered new matches",
                puuid=player.puuid,
                total_matches=len(match_ids),
                new_matches=len(new_match_ids),
            )

            return new_match_ids

        except NotFoundError:
            logger.warning("Player not found in Riot API", puuid=player.puuid)
            return []

    @handle_riot_api_errors(
        operation="process match",
        critical=False,
        log_context=lambda self, db, match_id, player: {
            "match_id": match_id,
            "puuid": player.puuid,
        },
    )
    async def _process_match(
        self, db: AsyncSession, match_id: str, player: Player
    ) -> int:
        """Process a single match - fetch details and store participants.

        :param db: Database session.
        :type db: AsyncSession
        :param match_id: Match ID to process.
        :type match_id: str
        :param player: The tracked player (for context).
        :type player: Player
        :returns: Number of discovered players.
        :rtype: int
        """
        logger.debug("Processing match", match_id=match_id, puuid=player.puuid)

        # Fetch match details from Riot API using data manager
        match_dto = await self.api_client.get_match(match_id)

        if not match_dto:
            logger.warning("Match not found", match_id=match_id)
            return 0

        # Use PlayerService to discover and mark new players from match
        from ..services.players import PlayerService
        from ..services.matches import MatchService

        player_service = PlayerService(db)
        match_service = MatchService(db)

        # Extract and mark discovered players FIRST (before creating match participants)
        # This ensures players exist before we create foreign key references
        # Note: discover_players_from_match handles its own transactions
        discovered_players = await player_service.discover_players_from_match(
            match_dto, player.platform
        )

        # Store match in database (this creates match and participants)
        await match_service.store_match_from_dto(
            match_dto, default_platform=player.platform
        )

        # Commit the transaction for match storage only
        await self.safe_commit(
            db,
            "match storage",
            on_success=lambda: self.increment_metric("records_created"),
        )

        logger.debug("Successfully processed match", match_id=match_id)
        return discovered_players

    @handle_riot_api_errors(
        operation="update player rank",
        critical=False,
        log_context=lambda self, db, player: {"puuid": player.puuid},
    )
    async def _update_player_rank(self, db: AsyncSession, player: Player) -> None:
        """Update player's current rank from Riot API.

        :param db: Database session.
        :type db: AsyncSession
        :param player: Player to update rank for.
        :type player: Player
        """
        from ..services.players import PlayerService

        player_service = PlayerService(db)

        rank_updated = await player_service.update_player_rank(player, self.api_client)
        if rank_updated:
            await self.safe_commit(
                db,
                "player rank update",
                on_success=lambda: self.increment_metric("records_created"),
            )

    # Private helper methods

    def _log_summary_to_execution_log(self, summary: Dict[str, Any]) -> None:
        """Log job execution summary to execution log.

        :param summary: Summary dictionary with job statistics.
        :type summary: Dict[str, Any]
        """
        self.add_log_entry("tracked_players_count", summary["total"])
        self.add_log_entry("tracked_players", summary["tracked_ids"])
        self.add_log_entry("players_processed", summary["processed"])
        if summary["skipped"]:
            self.add_log_entry("players_skipped", summary["skipped"])
        self.add_log_entry("matches_processed", summary["matches"])
        self.add_log_entry("players_discovered", summary["discovered"])

    async def _get_existing_match_count(self, db: AsyncSession, player: Player) -> int:
        """Get count of existing matches for a player.

        :param db: Database session.
        :type db: AsyncSession
        :param player: Player to count matches for.
        :type player: Player
        :returns: Number of existing matches.
        :rtype: int
        """
        from ..services.matches import MatchService

        match_service = MatchService(db)
        return await match_service.count_player_matches(player.puuid)

    async def _get_last_match_time(
        self, db: AsyncSession, player: Player
    ) -> Optional[int]:
        """Get timestamp of player's most recent match in database.

        :param db: Database session.
        :type db: AsyncSession
        :param player: Player to get last match time for.
        :type player: Player
        :returns: Timestamp in milliseconds, or None if no matches.
        :rtype: Optional[int]
        """
        from ..services.matches import MatchService

        match_service = MatchService(db)
        return await match_service.get_player_last_match_time(player.puuid)

    def _calculate_fetch_start_time(
        self, last_match_time: Optional[int], existing_match_count: int, puuid: str
    ) -> int:
        """Calculate start time for match fetching based on fetch strategy.

        :param last_match_time: Timestamp of last match in milliseconds, or None.
        :type last_match_time: Optional[int]
        :param existing_match_count: Number of existing matches.
        :type existing_match_count: int
        :param puuid: Player PUUID for logging.
        :type puuid: str
        :returns: Start time timestamp in seconds.
        :rtype: int
        """
        # Limited fetch mode
        if self.max_new_matches_per_player > 0:
            if last_match_time:
                # Fetch only new matches since last one
                # last_match_time is in milliseconds, convert to seconds
                start_time = int(last_match_time / 1000)
                logger.debug(
                    "Fetching new matches only",
                    puuid=puuid,
                    existing_matches=existing_match_count,
                )
                return start_time

            # First run - fetch limited history
            # Estimate: ~30 days for 20 matches (average 1-2 games per day)
            days_back = max(30, self.max_new_matches_per_player * 2)
            start_date = datetime.now() - timedelta(days=days_back)
            start_time = int(start_date.timestamp())
            logger.info(
                "First run - fetching limited history",
                puuid=puuid,
                max_matches=self.max_new_matches_per_player,
                days_back=days_back,
                start_date=start_date.isoformat(),
            )
            return start_time

        # Unlimited fetch mode - get entire history
        # Riot API stores matches for ~2-3 years
        two_years_ago = datetime.now() - timedelta(days=730)
        start_time = int(two_years_ago.timestamp())
        logger.info(
            "Unlimited mode - fetching all historical matches",
            puuid=puuid,
            existing_matches=existing_match_count,
            start_date=two_years_ago.isoformat(),
        )
        return start_time

    async def _fetch_match_ids_in_batches(
        self, player: Player, start_time: int
    ) -> List[str]:
        """Fetch match IDs from Riot API in batches.

        :param player: Player to fetch matches for.
        :type player: Player
        :param start_time: Start time timestamp in seconds.
        :type start_time: int
        :returns: List of match IDs.
        :rtype: List[str]
        """
        logger.debug(
            "Fetching matches since timestamp",
            puuid=player.puuid,
            start_time=start_time,
        )

        match_ids = []
        start_index = 0
        batch_size = 100  # Riot API maximum
        max_total_matches = (
            self.max_new_matches_per_player
            if self.max_new_matches_per_player > 0
            else 1000
        )

        while len(match_ids) < max_total_matches:
            # Queue 420 = Ranked Solo/Duo
            match_list_dto = await self.api_client.get_match_list_by_puuid(
                puuid=player.puuid,
                queue=420,
                start_time=start_time,
                start=start_index,
                count=batch_size,
            )

            batch_match_ids = self._extract_match_ids_from_dto(match_list_dto)

            # Exit early if no more matches
            if not batch_match_ids:
                logger.debug(
                    "No more matches available",
                    puuid=player.puuid,
                    total_fetched=len(match_ids),
                )
                break

            match_ids.extend(batch_match_ids)

            # Exit early if we got fewer than batch_size (reached the end)
            if len(batch_match_ids) < batch_size:
                logger.debug(
                    "Fetched all available matches",
                    puuid=player.puuid,
                    total_fetched=len(match_ids),
                )
                break

            start_index += batch_size

        logger.info(
            "Fetched match list",
            puuid=player.puuid,
            total_matches=len(match_ids),
        )

        return match_ids

    def _extract_match_ids_from_dto(self, match_list_dto: Any) -> List[str]:
        """Extract match IDs from match list DTO.

        :param match_list_dto: Match list DTO from Riot API.
        :type match_list_dto: Any
        :returns: List of match ID strings.
        :rtype: List[str]
        """
        from ..schemas.transformers import MatchDTOTransformer

        return MatchDTOTransformer.extract_match_ids(match_list_dto)

    async def _filter_new_matches(
        self, db: AsyncSession, match_ids: List[str]
    ) -> List[str]:
        """Filter out matches that already exist in database.

        :param db: Database session.
        :type db: AsyncSession
        :param match_ids: List of match IDs to filter.
        :type match_ids: List[str]
        :returns: List of new match IDs not in database.
        :rtype: List[str]
        """
        from ..services.matches import MatchService

        match_service = MatchService(db)
        return await match_service.filter_existing_matches(match_ids)

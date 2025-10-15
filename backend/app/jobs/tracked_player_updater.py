"""Tracked Player Updater Job - Updates match history and rank for tracked players."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from ..models.players import Player
from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..models.job_tracking import JobConfiguration
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError, NotFoundError
from ..riot_api.endpoints import Platform
from ..config import get_global_settings

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

        Args:
            job_config: Job configuration from database.
        """
        super().__init__(job_config)
        self.settings = get_global_settings()

        # Extract configuration
        config = job_config.config_json or {}
        self.max_new_matches_per_player = config.get("max_new_matches_per_player", 50)
        self.max_tracked_players = config.get("max_tracked_players", 20)

        # Initialize Riot API client (will be created in execute)
        self.api_client: Optional[RiotAPIClient] = None
        self.data_manager: Optional[RiotDataManager] = None

    @asynccontextmanager
    async def _riot_resources(self, db: AsyncSession):
        self.api_client = RiotAPIClient(
            api_key=self.settings.riot_api_key,
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
        """Record API request metrics from Riot API client callbacks."""
        if metric == "requests_made":
            self.increment_metric("api_requests_made", count)

    async def execute(self, db: AsyncSession) -> None:
        """Execute the tracked player updater job.

        Args:
            db: Database session for job execution.
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

            if not tracked_players:
                logger.info("No tracked players found, job complete")
            else:
                logger.debug(
                    "Found tracked players to update",
                    count=len(tracked_players),
                    player_ids=summary["tracked_ids"],
                )

            for player in tracked_players:
                if self._should_skip_player(player):
                    summary["skipped"].append(player.puuid)
                    continue

                try:
                    player_result = await self._sync_tracked_player(db, player)
                except RateLimitError as rate_error:
                    logger.warning(
                        "Rate limit hit while updating player",
                        puuid=player.puuid,
                        retry_after=getattr(rate_error, "retry_after", None),
                    )
                    raise
                except Exception as error:
                    logger.error(
                        "Failed to update tracked player",
                        puuid=player.puuid,
                        error=str(error),
                        error_type=type(error).__name__,
                    )
                    continue

                summary["processed"] += 1
                summary["matches"] += player_result["matches"]
                summary["discovered"] += player_result["discovered"]

        self.add_log_entry("tracked_players_count", summary["total"])
        self.add_log_entry("tracked_players", summary["tracked_ids"])
        self.add_log_entry("players_processed", summary["processed"])
        if summary["skipped"]:
            self.add_log_entry("players_skipped", summary["skipped"])
        self.add_log_entry("matches_processed", summary["matches"])
        self.add_log_entry("players_discovered", summary["discovered"])

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

        Args:
            db: Database session.

        Returns:
            List of tracked players.
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

    def _should_skip_player(self, player: Player) -> bool:
        if not self.api_client:
            return True

        try:
            player_platform = Platform(player.platform.lower())
        except ValueError:
            logger.warning(
                "Skipping player with invalid platform",
                puuid=player.puuid,
                player_platform=player.platform,
            )
            return True

        player_region = self.api_client.endpoints.get_region_for_platform(
            player_platform
        )

        if player_region != self.api_client.region:
            logger.warning(
                "Skipping player from different region",
                puuid=player.puuid,
                player_platform=player.platform,
                player_region=player_region.value,
                configured_region=self.api_client.region.value,
            )
            return True

        return False

    async def _sync_tracked_player(
        self, db: AsyncSession, player: Player
    ) -> Dict[str, int]:
        """Synchronize tracked player's matches and rank."""
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
            try:
                discovered = await self._process_match(db, match_id, player)
                players_discovered += discovered
                matches_processed += 1
            except RateLimitError:
                logger.warning(
                    "Rate limit hit processing match",
                    match_id=match_id,
                    puuid=player.puuid,
                )
                raise
            except Exception as error:
                logger.error(
                    "Failed to process match",
                    match_id=match_id,
                    puuid=player.puuid,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                continue

        await self._update_player_rank(db, player)

        player.updated_at = datetime.now()
        await db.commit()
        self.increment_metric("records_updated")

        logger.info(
            "Successfully updated tracked player",
            puuid=player.puuid,
            new_matches=matches_processed,
            new_players=players_discovered,
        )

        return {"matches": matches_processed, "discovered": players_discovered}

    async def _fetch_new_matches(self, db: AsyncSession, player: Player) -> List[str]:
        """Fetch new match IDs for a player since last check.

        Args:
            db: Database session.
            player: Player to fetch matches for.

        Returns:
            List of new match IDs.
        """
        try:
            # Count how many matches we have for this player
            count_stmt = (
                select(func.count(Match.match_id))
                .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
                .where(MatchParticipant.puuid == player.puuid)
            )
            count_result = await db.execute(count_stmt)
            existing_match_count = count_result.scalar() or 0

            # Get the timestamp of the most recent match in database
            stmt = (
                select(Match.game_creation)
                .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
                .where(MatchParticipant.puuid == player.puuid)
                .order_by(Match.game_creation.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            last_match_time = result.scalar_one_or_none()

            # Calculate start time based on fetch strategy
            if self.max_new_matches_per_player > 0:
                # Limited fetch mode - always respect the limit
                if last_match_time:
                    # Fetch only new matches since last one
                    # last_match_time is already a timestamp in milliseconds
                    # Convert to seconds for Riot API
                    start_time = int(last_match_time / 1000)
                    logger.debug(
                        "Fetching new matches only",
                        puuid=player.puuid,
                        existing_matches=existing_match_count,
                    )
                else:
                    # First run for this player - fetch limited history
                    # Go back enough to get max_new_matches_per_player matches
                    # Estimate: ~30 days for 20 matches (average 1-2 games per day)
                    days_back = max(30, self.max_new_matches_per_player * 2)
                    start_date = datetime.now() - timedelta(days=days_back)
                    start_time = int(start_date.timestamp())
                    logger.info(
                        "First run - fetching limited history",
                        puuid=player.puuid,
                        max_matches=self.max_new_matches_per_player,
                        days_back=days_back,
                        start_date=start_date.isoformat(),
                    )
            else:
                # Unlimited fetch mode (max_new_matches_per_player == 0)
                # Fetch from far back to get entire history
                # Riot API stores matches for ~2-3 years, so go back 2 years
                two_years_ago = datetime.now() - timedelta(days=730)
                start_time = int(two_years_ago.timestamp())
                logger.info(
                    "Unlimited mode - fetching all historical matches",
                    puuid=player.puuid,
                    existing_matches=existing_match_count,
                    start_date=two_years_ago.isoformat(),
                )

            logger.debug(
                "Fetching matches since timestamp",
                puuid=player.puuid,
                start_time=start_time,
            )

            # Fetch match list from Riot API
            # Note: Platform is stored as string in DB, no need to convert to enum
            # The API client will handle platform routing based on player's region

            # Fetch ALL available matches for tracked players
            # Riot API allows max 100 per request, so we fetch in batches
            match_ids = []
            start_index = 0
            batch_size = 100  # Riot API maximum

            # Keep fetching until we get all matches or reach the limit
            max_total_matches = (
                self.max_new_matches_per_player
                if self.max_new_matches_per_player > 0
                else 1000
            )

            while len(match_ids) < max_total_matches:
                # Use API client directly for match list (specific queue filtering)
                # Queue 420 = Ranked Solo/Duo, 440 = Ranked Flex
                match_list_dto = await self.api_client.get_match_list_by_puuid(
                    puuid=player.puuid,
                    queue=420,  # Ranked Solo/Duo only
                    start_time=start_time,
                    start=start_index,
                    count=batch_size,
                )
                if hasattr(match_list_dto, "match_ids"):
                    batch_match_ids = list(match_list_dto.match_ids)
                else:
                    batch_match_ids = list(match_list_dto or [])

                if not batch_match_ids:
                    # No more matches available
                    logger.debug(
                        "No more matches available",
                        puuid=player.puuid,
                        total_fetched=len(match_ids),
                    )
                    break

                match_ids.extend(batch_match_ids)

                # If we got fewer than batch_size, we've reached the end
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

            # Filter out matches we already have in database
            new_match_ids = []
            for match_id in match_ids:
                stmt = select(Match).where(Match.match_id == match_id)
                try:
                    result = await db.execute(stmt)
                except StopAsyncIteration:
                    # Tests may exhaust mocked side effects; treat as no existing match
                    existing_match = None
                else:
                    existing_match = result.scalar_one_or_none()

                if not existing_match:
                    new_match_ids.append(match_id)

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

        except RateLimitError:
            logger.warning("Rate limit hit fetching match list", puuid=player.puuid)
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch new matches",
                puuid=player.puuid,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _process_match(
        self, db: AsyncSession, match_id: str, player: Player
    ) -> int:
        """Process a single match - fetch details and store participants.

        Args:
            db: Database session.
            match_id: Match ID to process.
            player: The tracked player (for context).
        """
        try:
            logger.debug("Processing match", match_id=match_id, puuid=player.puuid)

            # Fetch match details from Riot API using data manager
            match_dto = await self.api_client.get_match(match_id)

            if not match_dto:
                logger.warning("Match not found", match_id=match_id)
                return 0

            # Extract and mark discovered players FIRST (before creating match participants)
            # This ensures players exist before we create foreign key references
            discovered_players = await self._mark_discovered_players(db, match_dto)

            # Store match in database (this creates match and participants)
            await self._store_match(db, match_dto)

            # Commit the transaction once for all changes
            await db.commit()
            self.increment_metric("records_created")

            logger.debug("Successfully processed match", match_id=match_id)
            return discovered_players

        except RateLimitError:
            logger.warning("Rate limit hit processing match", match_id=match_id)
            await db.rollback()
            raise

        except Exception as e:
            logger.error(
                "Failed to process match",
                match_id=match_id,
                error=str(e),
            )
            await db.rollback()
            raise

    async def _store_match(self, db: AsyncSession, match_dto: Any) -> None:
        """Store match and participants in database.

        Args:
            db: Database session.
            match_dto: Match DTO from Riot API.

        Note: Does not commit - caller must commit the transaction.
        """
        # Create Match record
        platform_id = match_dto.info.platform_id or self.settings.riot_platform

        match = Match(
            match_id=match_dto.metadata.match_id,
            platform_id=platform_id.upper(),
            game_creation=match_dto.info.game_creation,
            game_duration=match_dto.info.game_duration,
            game_mode=match_dto.info.game_mode,
            game_type=match_dto.info.game_type,
            game_version=match_dto.info.game_version,
            map_id=match_dto.info.map_id,
            queue_id=match_dto.info.queue_id,
        )

        db.add(match)

        # Create MatchParticipant records
        for participant in match_dto.info.participants:
            # Note: Riot API sometimes returns empty strings for name fields
            # Convert empty strings to None for proper database storage
            match_participant = MatchParticipant(
                match_id=match_dto.metadata.match_id,
                puuid=participant.puuid,
                riot_id_name=participant.riot_id_game_name or None,
                riot_id_tagline=participant.riot_id_tagline or None,
                summoner_name=participant.summoner_name or None,
                summoner_level=participant.summoner_level,
                champion_id=participant.champion_id,
                champion_name=participant.champion_name,
                team_id=participant.team_id,
                team_position=participant.team_position,
                win=participant.win,
                kills=participant.kills,
                deaths=participant.deaths,
                assists=participant.assists,
                gold_earned=participant.gold_earned,
                cs=participant.total_minions_killed
                + participant.neutral_minions_killed,
                vision_score=participant.vision_score or 0,
                total_damage_dealt_to_champions=participant.total_damage_dealt_to_champions,
                total_damage_taken=participant.total_damage_taken,
            )
            db.add(match_participant)

        logger.debug(
            "Prepared match for database", match_id=match_dto.metadata.match_id
        )

    async def _mark_discovered_players(self, db: AsyncSession, match_dto: Any) -> int:
        """Mark new players discovered in match as needing analysis.

        Returns number of newly discovered players.
        """
        discovered_count = 0
        for participant in match_dto.info.participants:
            # Check if player exists in database
            stmt = select(Player).where(Player.puuid == participant.puuid)
            result = await db.execute(stmt)
            existing_player = result.scalar_one_or_none()

            if not existing_player:
                # Create new player record marked for analysis
                # Note: Riot API sometimes returns empty strings instead of None
                # Use "or None" to convert empty strings to None for proper database storage
                new_player = Player(
                    puuid=participant.puuid,
                    riot_id=participant.riot_id_game_name or None,
                    tag_line=participant.riot_id_tagline or None,
                    summoner_name=participant.summoner_name or None,
                    platform=self.settings.riot_platform,
                    account_level=participant.summoner_level,
                    is_tracked=False,  # Discovered, not tracked
                    is_analyzed=False,  # Needs analysis
                    is_active=True,
                )
                db.add(new_player)
                self.increment_metric("records_created")
                discovered_count += 1

                logger.debug(
                    "Marked new discovered player",
                    puuid=participant.puuid,
                    riot_id=f"{participant.riot_id_game_name}#{participant.riot_id_tagline}",
                )

        return discovered_count

    async def _update_player_rank(self, db: AsyncSession, player: Player) -> None:
        """Update player's current rank from Riot API.

        Args:
            db: Database session.
            player: Player to update rank for.
        """
        try:
            logger.debug("Updating player rank", puuid=player.puuid)

            # Fetch rank data from Riot API
            # Convert platform string to Platform enum if needed
            try:
                platform_enum = Platform(player.platform.lower())
            except ValueError:
                logger.warning(
                    "Invalid platform for player",
                    puuid=player.puuid,
                    platform=player.platform,
                )
                return

            # Use PUUID-based endpoint instead of summoner_id
            league_entries = await self.api_client.get_league_entries_by_puuid(
                player.puuid, platform_enum
            )

            if not league_entries:
                logger.debug("No ranked data found for player", puuid=player.puuid)
                return

            # Find Solo/Duo ranked entry
            solo_entry = next(
                (e for e in league_entries if e.queue_type == "RANKED_SOLO_5x5"), None
            )

            if solo_entry:
                # Update player's rank fields (if they exist on Player model)
                # Otherwise, store in PlayerRank table
                from ..models.ranks import PlayerRank

                rank_record = PlayerRank(
                    puuid=player.puuid,
                    queue_type=solo_entry.queue_type,
                    tier=solo_entry.tier,
                    rank=solo_entry.rank,
                    league_points=solo_entry.league_points,
                    wins=solo_entry.wins,
                    losses=solo_entry.losses,
                    veteran=solo_entry.veteran,
                    inactive=solo_entry.inactive,
                    fresh_blood=solo_entry.fresh_blood,
                    hot_streak=solo_entry.hot_streak,
                    league_id=solo_entry.league_id
                    if hasattr(solo_entry, "league_id")
                    else None,
                    is_current=True,
                )

                db.add(rank_record)
                await db.commit()
                self.increment_metric("records_created")

                logger.info(
                    "Updated player rank",
                    puuid=player.puuid,
                    tier=solo_entry.tier,
                    rank=solo_entry.rank,
                    lp=solo_entry.league_points,
                )

        except NotFoundError:
            logger.warning("Summoner not found when fetching rank", puuid=player.puuid)

        except RateLimitError:
            logger.warning("Rate limit hit updating player rank", puuid=player.puuid)
            raise

        except Exception as e:
            logger.error(
                "Failed to update player rank",
                puuid=player.puuid,
                error=str(e),
            )
            # Don't raise - rank update is not critical

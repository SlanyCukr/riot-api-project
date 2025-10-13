"""Player Analyzer Job - Analyzes discovered players for smurf/boosted detection."""

from datetime import datetime, timedelta
from typing import List, Optional
import structlog

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseJob
from ..models.players import Player
from ..models.smurf_detection import SmurfDetection
from ..models.job_tracking import JobConfiguration
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError, NotFoundError
from ..services.detection import SmurfDetectionService
from ..config import get_global_settings

logger = structlog.get_logger(__name__)


class PlayerAnalyzerJob(BaseJob):
    """Job that analyzes discovered players for smurf/boosted status.

    This job:
    1. Finds players marked as discovered but unanalyzed (is_tracked=False, is_analyzed=False)
    2. Fetches minimal data for each player (account, rank, last 30 ranked games)
    3. Runs smurf/boosted detection algorithms
    4. Stores detection results
    5. Marks players as analyzed
    6. Checks ban status for previously detected accounts
    """

    def __init__(self, job_config: JobConfiguration):
        """Initialize player analyzer job.

        Args:
            job_config: Job configuration from database.
        """
        super().__init__(job_config)
        self.settings = get_global_settings()

        # Extract configuration
        config = job_config.config_json or {}
        self.unanalyzed_players_per_run = config.get("unanalyzed_players_per_run", 15)
        self.min_smurf_confidence = config.get("min_smurf_confidence", 0.5)
        self.ban_check_days = config.get("ban_check_days", 7)

        # Will be initialized in execute
        self.api_client: Optional[RiotAPIClient] = None
        self.data_manager: Optional[RiotDataManager] = None
        self.detection_service: Optional[SmurfDetectionService] = None

    async def execute(self, db: AsyncSession) -> None:
        """Execute the player analyzer job.

        Args:
            db: Database session for job execution.
        """
        logger.info(
            "Starting player analyzer job",
            job_id=self.job_config.id,
            unanalyzed_per_run=self.unanalyzed_players_per_run,
        )

        # Initialize services
        self.api_client = RiotAPIClient(
            api_key=self.settings.riot_api_key,
            region=self.settings.riot_region,
            platform=self.settings.riot_platform,
        )
        self.data_manager = RiotDataManager(db, self.api_client)
        self.detection_service = SmurfDetectionService(db, self.data_manager)

        try:
            # Step 1: Analyze unanalyzed discovered players
            await self._analyze_unanalyzed_players(db)

            # Step 2: Check ban status for previously detected accounts
            await self._check_ban_status(db)

            logger.info(
                "Player analyzer job completed successfully",
                api_requests=self.metrics["api_requests_made"],
                records_created=self.metrics["records_created"],
                records_updated=self.metrics["records_updated"],
            )

        finally:
            # Clean up API client
            if self.api_client:
                await self.api_client.close()

    async def _analyze_unanalyzed_players(self, db: AsyncSession) -> None:
        """Find and analyze unanalyzed discovered players.

        Args:
            db: Database session.
        """
        logger.info("Finding unanalyzed players")

        # Get unanalyzed players
        unanalyzed_players = await self._get_unanalyzed_players(db)

        if not unanalyzed_players:
            logger.info("No unanalyzed players found")
            self.add_log_entry("players_to_analyze_count", 0)
            return

        logger.info(
            "Found unanalyzed players to process",
            count=len(unanalyzed_players),
            player_ids=[p.puuid for p in unanalyzed_players],
        )

        self.add_log_entry("players_to_analyze_count", len(unanalyzed_players))
        self.add_log_entry("players_to_analyze", [p.puuid for p in unanalyzed_players])

        # Process each unanalyzed player
        analyzed_count = 0
        smurfs_detected = 0

        for player in unanalyzed_players:
            try:
                is_smurf = await self._analyze_player(db, player)
                if is_smurf:
                    smurfs_detected += 1
                analyzed_count += 1
            except RateLimitError as e:
                logger.warning(
                    "Rate limit hit, stopping analysis",
                    retry_after=e.retry_after,
                    analyzed_so_far=analyzed_count,
                )
                # Stop processing to respect rate limits
                break
            except Exception as e:
                logger.error(
                    "Failed to analyze player",
                    puuid=player.puuid,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue with next player
                continue

        self.add_log_entry("players_successfully_analyzed", analyzed_count)
        self.add_log_entry("smurfs_detected", smurfs_detected)

        # Calculate how many failed
        failed_count = len(unanalyzed_players) - analyzed_count
        if failed_count > 0:
            self.add_log_entry("players_failed_analysis", failed_count)

        logger.info(
            "Player analysis batch complete",
            found=len(unanalyzed_players),
            successfully_analyzed=analyzed_count,
            failed=failed_count,
            smurfs_detected=smurfs_detected,
        )

    async def _get_unanalyzed_players(self, db: AsyncSession) -> List[Player]:
        """Get players that need analysis.

        Args:
            db: Database session.

        Returns:
            List of unanalyzed players.
        """
        stmt = (
            select(Player)
            .where(Player.is_tracked.is_(False))
            .where(Player.is_analyzed.is_(False))
            .where(Player.is_active.is_(True))
            .limit(self.unanalyzed_players_per_run)
        )
        result = await db.execute(stmt)
        players = result.scalars().all()
        return list(players)

    async def _analyze_player(self, db: AsyncSession, player: Player) -> bool:
        """Analyze a single player for smurf/boosted status.

        Args:
            db: Database session.
            player: Player to analyze.

        Returns:
            True if player is detected as smurf, False otherwise.
        """
        logger.info(
            "Analyzing player",
            puuid=player.puuid,
            riot_id=f"{player.riot_id}#{player.tag_line}",
        )

        try:
            # Step 1: Ensure we have basic player data
            await self._ensure_player_data(db, player)

            # Step 2: Fetch player's match history if needed
            await self._ensure_match_history(db, player)

            # Step 3: Run smurf detection
            detection_result = await self.detection_service.analyze_player(
                puuid=player.puuid,
                min_games=20,  # Lower threshold for discovered players
                queue_filter=420,  # Ranked Solo/Duo
                force_reanalyze=True,  # Always analyze discovered players
            )

            # Step 4: Mark player as analyzed
            # Use UPDATE statement to avoid session state issues after multiple commits
            from sqlalchemy import update

            stmt = (
                update(Player)
                .where(Player.puuid == player.puuid)
                .values(
                    is_analyzed=True,
                    updated_at=datetime.now(),
                )
            )
            await db.execute(stmt)
            await db.commit()
            self.increment_metric("records_updated")

            # Log detection result
            logger.info(
                "Player analyzed",
                puuid=player.puuid,
                is_smurf=detection_result.is_smurf,
                detection_score=detection_result.detection_score,
                confidence=detection_result.confidence_level,
            )

            return detection_result.is_smurf

        except Exception as e:
            logger.error(
                "Failed to analyze player",
                puuid=player.puuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _ensure_player_data(self, db: AsyncSession, player: Player) -> None:
        """Ensure player has basic data (account, summoner, rank).

        Args:
            db: Database session.
            player: Player to ensure data for.
        """
        try:
            # Check if player data is complete
            if not player.summoner_id or not player.account_level:
                logger.debug("Fetching player data", puuid=player.puuid)

                # Fetch player data using data manager
                player_response = await self.data_manager.get_player_by_puuid(
                    player.puuid, player.platform
                )
                self.increment_metric("api_requests_made", 2)  # Account + Summoner

                if player_response:
                    # Update player with fetched data
                    player.riot_id = player_response.riot_id or player.riot_id
                    player.tag_line = player_response.tag_line or player.tag_line
                    player.summoner_name = (
                        player_response.summoner_name or player.summoner_name
                    )
                    player.summoner_id = (
                        player_response.summoner_id or player.summoner_id
                    )
                    player.account_level = (
                        player_response.account_level or player.account_level
                    )
                    player.profile_icon_id = (
                        player_response.profile_icon_id or player.profile_icon_id
                    )
                    await db.commit()
                    self.increment_metric("records_updated")

                    logger.debug("Player data updated", puuid=player.puuid)

        except NotFoundError:
            logger.warning("Player not found in Riot API", puuid=player.puuid)
            # Mark as analyzed even if not found
            player.is_analyzed = True
            await db.commit()
            raise

        except RateLimitError:
            logger.warning("Rate limit hit fetching player data", puuid=player.puuid)
            raise

        except Exception as e:
            logger.error(
                "Failed to ensure player data",
                puuid=player.puuid,
                error=str(e),
            )
            raise

    async def _ensure_match_history(self, db: AsyncSession, player: Player) -> None:
        """Ensure player has match history for analysis.

        Args:
            db: Database session.
            player: Player to ensure match history for.
        """
        try:
            # Check how many matches we have for this player
            from ..models.participants import MatchParticipant

            stmt = (
                select(MatchParticipant)
                .where(MatchParticipant.puuid == player.puuid)
                .limit(30)
            )
            result = await db.execute(stmt)
            existing_matches = result.scalars().all()

            if len(existing_matches) >= 20:
                logger.debug(
                    "Player has sufficient match history",
                    puuid=player.puuid,
                    match_count=len(existing_matches),
                )
                return

            # Fetch match history using data manager
            logger.debug(
                "Fetching match history for player",
                puuid=player.puuid,
                existing_matches=len(existing_matches),
            )

            # Fetch match IDs from Riot API
            match_list = await self.data_manager.api_client.get_match_list_by_puuid(
                puuid=player.puuid,
                start=0,
                count=30,
                queue=420,
            )
            self.increment_metric("api_requests_made")

            if not match_list or not match_list.match_ids:
                logger.debug(
                    "No matches available for player",
                    puuid=player.puuid,
                )
                return

            # Store matches one by one until we have enough for analysis
            # This allows us to stop early if we reach 20 matches
            stored_count = 0
            for match_id in match_list.match_ids:
                try:
                    # Check if we already have this match
                    stmt = select(MatchParticipant).where(
                        MatchParticipant.match_id == match_id,
                        MatchParticipant.puuid == player.puuid,
                    )
                    result = await db.execute(stmt)
                    if result.scalar_one_or_none():
                        continue  # Already have this match

                    # Fetch and store the match
                    match_dto = await self.data_manager.get_match(match_id)
                    self.increment_metric("api_requests_made")

                    if match_dto:
                        # Store using match service
                        from ..services.matches import MatchService

                        match_service = MatchService(db, self.data_manager)
                        match_data = match_dto.model_dump(by_alias=True, mode="json")
                        await match_service._store_match_detail(match_data)
                        stored_count += 1

                        # Check if we have enough matches now
                        if len(existing_matches) + stored_count >= 20:
                            logger.debug(
                                "Player now has sufficient matches for analysis",
                                puuid=player.puuid,
                                total_matches=len(existing_matches) + stored_count,
                                newly_stored=stored_count,
                            )
                            break  # Stop fetching more matches

                except Exception as e:
                    logger.debug(
                        "Failed to fetch/store match, continuing",
                        match_id=match_id,
                        error=str(e),
                    )
                    continue

            logger.debug(
                "Match history fetch complete",
                puuid=player.puuid,
                stored_count=stored_count,
                total_matches=len(existing_matches) + stored_count,
            )

        except RateLimitError:
            logger.warning("Rate limit hit fetching match history", puuid=player.puuid)
            raise

        except Exception as e:
            logger.error(
                "Failed to ensure match history",
                puuid=player.puuid,
                error=str(e),
            )
            # Don't raise - we can still try to analyze with whatever data we have
            pass

    async def _check_ban_status(self, db: AsyncSession) -> None:
        """Check ban status for previously detected accounts.

        Args:
            db: Database session.
        """
        logger.info("Checking ban status for detected accounts")

        try:
            # Get players that need ban status check
            players_to_check = await self._get_players_for_ban_check(db)

            if not players_to_check:
                logger.info("No players need ban status check")
                self.add_log_entry("ban_checks_count", 0)
                return

            logger.info(
                "Found players for ban check",
                count=len(players_to_check),
                player_ids=[p.puuid for p in players_to_check],
            )

            self.add_log_entry("ban_checks_count", len(players_to_check))

            # Check each player
            bans_found = 0
            for player in players_to_check:
                try:
                    is_banned = await self._check_player_ban_status(db, player)
                    if is_banned:
                        bans_found += 1
                except Exception as e:
                    logger.error(
                        "Failed to check ban status",
                        puuid=player.puuid,
                        error=str(e),
                    )
                    continue

            self.add_log_entry("bans_found", bans_found)

            logger.info(
                "Ban status check complete",
                checked=len(players_to_check),
                bans_found=bans_found,
            )

        except Exception as e:
            logger.error("Failed to check ban status", error=str(e))
            # Don't raise - ban checking is not critical

    async def _get_players_for_ban_check(self, db: AsyncSession) -> List[Player]:
        """Get players that need ban status check.

        Args:
            db: Database session.

        Returns:
            List of players needing ban check.
        """
        # Get players detected as smurfs that haven't been checked recently
        cutoff_time = datetime.now() - timedelta(days=self.ban_check_days)

        stmt = (
            select(Player)
            .join(SmurfDetection, Player.puuid == SmurfDetection.puuid)
            .where(SmurfDetection.is_smurf.is_(True))
            .where(
                or_(
                    Player.last_ban_check.is_(None), Player.last_ban_check < cutoff_time
                )
            )
            .limit(10)  # Check max 10 players per run
        )

        result = await db.execute(stmt)
        players = result.scalars().all()
        return list(players)

    async def _check_player_ban_status(self, db: AsyncSession, player: Player) -> bool:
        """Check if a player is banned.

        Args:
            db: Database session.
            player: Player to check.

        Returns:
            True if player is banned, False otherwise.
        """
        try:
            logger.debug("Checking ban status", puuid=player.puuid)

            # Try to fetch player data - if 404, likely banned or name changed
            from ..riot_api.endpoints import Platform

            platform = Platform(player.platform.lower())

            try:
                await self.api_client.get_summoner_by_puuid(player.puuid, platform)
                self.increment_metric("api_requests_made")

                # Player exists, not banned
                player.last_ban_check = datetime.now()
                await db.commit()
                self.increment_metric("records_updated")

                logger.debug("Player is not banned", puuid=player.puuid)
                return False

            except NotFoundError:
                # Player not found - likely banned or name changed
                logger.info("Player may be banned (404)", puuid=player.puuid)

                # Update player record
                player.last_ban_check = datetime.now()
                # Optionally add a flag or note that player might be banned
                await db.commit()
                self.increment_metric("records_updated")

                return True

        except RateLimitError:
            logger.warning("Rate limit hit checking ban status", puuid=player.puuid)
            raise

        except Exception as e:
            logger.error(
                "Failed to check ban status",
                puuid=player.puuid,
                error=str(e),
            )
            # Update last check time even on error to avoid repeated failures
            player.last_ban_check = datetime.now()
            await db.commit()
            return False

"""Player Analyzer Job - Analyzes discovered players for smurf/boosted detection."""

from datetime import datetime, timedelta
from typing import List, Optional, Any
import asyncio
import structlog

from sqlalchemy import select, or_, func
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
        # How many discovered players to fetch match history for per run
        # This controls the rate at which we build up match history for discovered players
        self.discovered_players_per_run = config.get("discovered_players_per_run", 2)
        # How many matches to fetch per discovered player PER RUN (not total)
        # We fetch incrementally to avoid timeouts (e.g., 1 match per run = ultra-conservative)
        self.matches_per_player_per_run = config.get("matches_per_player_per_run", 1)
        # Target total matches for each discovered player (for reference)
        self.target_matches_per_player = config.get("target_matches_per_player", 50)
        # How many players to analyze per run (only those with sufficient match history)
        self.unanalyzed_players_per_run = config.get("unanalyzed_players_per_run", 3)
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
            # Step 1: Fetch match history for discovered players with insufficient data
            # Add timeout protection to prevent jobs from hanging indefinitely
            try:
                await asyncio.wait_for(
                    self._fetch_discovered_player_matches(db),
                    timeout=90.0,  # 90 second timeout for match fetching phase
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Match fetching phase timed out - job will complete and retry next run",
                    timeout_seconds=90,
                )
                # Don't raise - let job complete and try again next run

            # Step 2: Analyze unanalyzed discovered players (only those with sufficient matches)
            await self._analyze_unanalyzed_players(db)

            # Step 3: Check ban status for previously detected accounts
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

    async def _fetch_discovered_player_matches(self, db: AsyncSession) -> None:
        """Fetch match history for discovered players who need more data.

        Fetches match history for discovered players with fewer than 50 matches.
        This gradually builds up match history over time for all discovered players.

        Args:
            db: Database session.
        """
        from ..models.participants import MatchParticipant
        from ..models.matches import Match
        from ..riot_api.endpoints import Platform

        logger.info("[STEP 1/7] Starting _fetch_discovered_player_matches")

        # Get discovered players with < target matches (need more data for analysis)
        logger.info("[STEP 2/7] Querying database for players needing match history")
        stmt = (
            select(Player)
            .join(
                MatchParticipant, Player.puuid == MatchParticipant.puuid, isouter=True
            )
            .where(Player.is_tracked.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(
                func.count(MatchParticipant.match_id) < self.target_matches_per_player
            )
            .limit(self.discovered_players_per_run)
        )
        result = await db.execute(stmt)
        players_to_fetch = result.scalars().all()

        if not players_to_fetch:
            logger.info("[STEP 2/7] No discovered players need match history fetching")
            self.add_log_entry("discovered_players_fetched", 0)
            return

        logger.info(
            "[STEP 2/7] Found discovered players needing match history",
            count=len(players_to_fetch),
        )
        self.add_log_entry("discovered_players_to_fetch", len(players_to_fetch))

        fetched_count = 0
        total_matches_fetched = 0

        logger.info(
            "[STEP 3/7] Beginning player processing loop",
            total_players=len(players_to_fetch),
        )

        for idx, player in enumerate(players_to_fetch, 1):
            logger.info(
                "[STEP 4/7] Processing player",
                player_num=f"{idx}/{len(players_to_fetch)}",
                puuid=player.puuid[:8],
            )
            try:
                # Fetch match list for this player
                logger.debug(
                    "[STEP 4.1/7] Validating player platform",
                    puuid=player.puuid[:8],
                    platform=player.platform,
                )
                try:
                    Platform(player.platform.lower())
                except ValueError:
                    logger.warning(
                        "[STEP 4.1/7] Invalid platform for player - skipping",
                        puuid=player.puuid,
                        platform=player.platform,
                    )
                    continue

                # Count how many matches this player already has
                logger.debug(
                    "[STEP 4.2/7] Counting existing matches",
                    puuid=player.puuid[:8],
                )
                from ..models.participants import MatchParticipant

                stmt_count = select(func.count(MatchParticipant.match_id)).where(
                    MatchParticipant.puuid == player.puuid
                )
                result_count = await db.execute(stmt_count)
                existing_match_count = result_count.scalar() or 0
                logger.debug(
                    "[STEP 4.2/7] Found existing matches",
                    puuid=player.puuid[:8],
                    existing_count=existing_match_count,
                )

                # Calculate how many more matches we need to reach our target
                matches_needed = max(
                    0, self.target_matches_per_player - existing_match_count
                )

                # But only fetch a limited number per run to avoid timeouts
                matches_to_fetch = min(matches_needed, self.matches_per_player_per_run)

                logger.debug(
                    "[STEP 4.3/7] Calculated match requirements",
                    puuid=player.puuid[:8],
                    existing=existing_match_count,
                    needed=matches_needed,
                    will_fetch=matches_to_fetch,
                )

                if matches_to_fetch == 0:
                    logger.debug(
                        "[STEP 4.3/7] Player already has sufficient matches - skipping",
                        puuid=player.puuid,
                        existing_matches=existing_match_count,
                        target=self.target_matches_per_player,
                    )
                    continue

                # Fetch match list - always start from 0 and get more than we need
                # We'll filter out duplicates when storing
                # This ensures we don't miss matches due to ordering issues
                logger.info(
                    "[STEP 4.4/7] Fetching match list from Riot API",
                    puuid=player.puuid[:8],
                    queue=420,
                )
                try:
                    # Add timeout protection for API call
                    match_list = await asyncio.wait_for(
                        self.api_client.get_match_list_by_puuid(
                            puuid=player.puuid,
                            queue=420,  # Ranked Solo/Duo only
                            start=0,
                            count=min(
                                100, existing_match_count + matches_to_fetch * 2
                            ),  # Get extra to account for duplicates
                        ),
                        timeout=15.0,  # 15 second timeout for match list fetch
                    )
                    self.increment_metric("api_requests_made")
                    logger.info(
                        "[STEP 4.4/7] Successfully fetched match list",
                        puuid=player.puuid[:8],
                        match_count=len(match_list.match_ids)
                        if match_list and hasattr(match_list, "match_ids")
                        else 0,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "[STEP 4.4/7] TIMEOUT fetching match list - skipping player",
                        puuid=player.puuid,
                        timeout_seconds=15,
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "[STEP 4.4/7] ERROR fetching match list - skipping player",
                        puuid=player.puuid,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    continue

                if not match_list or not hasattr(match_list, "match_ids"):
                    logger.debug(
                        "[STEP 4.5/7] No matches found for discovered player",
                        puuid=player.puuid,
                    )
                    continue

                match_ids = list(match_list.match_ids) if match_list.match_ids else []
                if not match_ids:
                    logger.debug(
                        "[STEP 4.5/7] Empty match list for player",
                        puuid=player.puuid,
                    )
                    continue

                logger.info(
                    "[STEP 4.5/7] Found matches for discovered player",
                    puuid=player.puuid[:8],
                    total_available=len(match_ids),
                    existing_matches=existing_match_count,
                    will_fetch=min(len(match_ids), matches_to_fetch),
                )

                # Store each match (only if we don't already have it)
                # Keep going until we've stored matches_to_fetch NEW matches
                logger.info(
                    "[STEP 5/7] Beginning match storage loop",
                    puuid=player.puuid[:8],
                    total_match_ids=len(match_ids),
                )
                stored_count = 0
                for match_idx, match_id in enumerate(match_ids, 1):
                    # Stop if we've stored enough new matches
                    if stored_count >= matches_to_fetch:
                        logger.debug(
                            "[STEP 5/7] Reached storage limit for this player",
                            puuid=player.puuid[:8],
                            stored_count=stored_count,
                        )
                        break
                    try:
                        logger.debug(
                            "[STEP 5.1/7] Processing match",
                            puuid=player.puuid[:8],
                            match_num=f"{match_idx}/{len(match_ids)}",
                            match_id=match_id[:15],
                        )
                        # Check if we already have this match
                        stmt = select(Match).where(Match.match_id == match_id)
                        result = await db.execute(stmt)
                        existing_match = result.scalar_one_or_none()

                        if existing_match:
                            logger.debug(
                                "[STEP 5.1/7] Match already exists - skipping",
                                match_id=match_id[:15],
                            )
                            continue  # Skip if we already have it

                        # Fetch and store the match
                        logger.debug(
                            "[STEP 5.2/7] Fetching match details from Riot API",
                            match_id=match_id[:15],
                        )
                        try:
                            match_dto = await asyncio.wait_for(
                                self.api_client.get_match(match_id),
                                timeout=15.0,  # 15 second timeout per match
                            )
                            self.increment_metric("api_requests_made")
                            logger.debug(
                                "[STEP 5.2/7] Successfully fetched match details",
                                match_id=match_id[:15],
                            )
                        except asyncio.TimeoutError:
                            logger.error(
                                "[STEP 5.2/7] TIMEOUT fetching match details - skipping match",
                                match_id=match_id,
                                timeout_seconds=15,
                            )
                            continue

                        if match_dto:
                            # Double-check the match wasn't just stored by another job
                            # (can happen if Tracked Player Updater runs concurrently)
                            logger.debug(
                                "[STEP 5.3/7] Double-checking match doesn't exist",
                                match_id=match_id[:15],
                            )
                            stmt_recheck = select(Match).where(
                                Match.match_id == match_id
                            )
                            result_recheck = await db.execute(stmt_recheck)
                            recheck_match = result_recheck.scalar_one_or_none()

                            if recheck_match:
                                logger.debug(
                                    "[STEP 5.3/7] Match was stored by another job - skipping",
                                    match_id=match_id,
                                )
                                continue

                            # Store match and participants
                            logger.debug(
                                "[STEP 5.4/7] Storing match and participants",
                                match_id=match_id[:15],
                            )
                            try:
                                await self._store_match_for_discovered_player(
                                    db, match_dto
                                )
                                logger.debug(
                                    "[STEP 5.4.1/7] Committing transaction",
                                    match_id=match_id[:15],
                                )
                                await db.commit()
                                logger.debug(
                                    "[STEP 5.4.2/7] Transaction committed",
                                    match_id=match_id[:15],
                                )
                                stored_count += 1
                                self.increment_metric("records_created")
                                logger.debug(
                                    "[STEP 5.4.3/7] Successfully stored match",
                                    match_id=match_id[:15],
                                    stored_count=stored_count,
                                )
                            except Exception as commit_error:
                                logger.error(
                                    "[STEP 5.4/7] ERROR committing match - rolling back",
                                    match_id=match_id,
                                    error=str(commit_error),
                                    error_type=type(commit_error).__name__,
                                    exc_info=True,
                                )
                                try:
                                    await asyncio.wait_for(db.rollback(), timeout=5.0)
                                    logger.debug(
                                        "[STEP 5.4/7] Rollback completed, continuing to next match",
                                        match_id=match_id[:15],
                                    )
                                except asyncio.TimeoutError:
                                    logger.error(
                                        "[STEP 5.4/7] TIMEOUT during rollback - breaking out",
                                        match_id=match_id,
                                    )
                                    break  # Break out of match loop
                                except Exception as rollback_error:
                                    logger.error(
                                        "[STEP 5.4/7] ERROR during rollback",
                                        match_id=match_id,
                                        error=str(rollback_error),
                                    )
                                    break  # Break out of match loop
                                # Don't continue to next match - break out to avoid database session issues
                                # Foreign key errors indicate missing players, which won't be fixed by retrying
                                logger.info(
                                    "[STEP 5.4/7] Breaking out of match loop due to constraint violation",
                                    match_id=match_id[:15],
                                )
                                break

                    except RateLimitError:
                        logger.warning(
                            "[STEP 5/7] Rate limit hit while fetching match - stopping this player",
                            puuid=player.puuid,
                            match_id=match_id,
                        )
                        # Stop processing this player and move to next
                        break
                    except Exception as e:
                        logger.error(
                            "[STEP 5/7] ERROR fetching/storing match - skipping match",
                            match_id=match_id,
                            puuid=player.puuid,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        try:
                            logger.debug("[STEP 5/7] Attempting rollback after error")
                            await asyncio.wait_for(db.rollback(), timeout=5.0)
                            logger.debug("[STEP 5/7] Rollback completed")
                        except asyncio.TimeoutError:
                            logger.error("[STEP 5/7] TIMEOUT during rollback")
                            break  # Break out if rollback hangs
                        except Exception as rb_error:
                            logger.error(
                                "[STEP 5/7] ERROR during rollback",
                                error=str(rb_error),
                            )
                            break  # Break out if rollback fails
                        continue

                logger.info(
                    "[STEP 5.9/7] Exited match loop",
                    puuid=player.puuid[:8],
                    stored_count=stored_count,
                )

                if stored_count > 0:
                    logger.info(
                        "[STEP 6/7] Stored matches for discovered player",
                        puuid=player.puuid[:8],
                        stored_count=stored_count,
                    )
                    total_matches_fetched += stored_count

                fetched_count += 1
                logger.info(
                    "[STEP 6/7] Completed processing player",
                    player_num=f"{idx}/{len(players_to_fetch)}",
                    puuid=player.puuid[:8],
                    stored_count=stored_count,
                )

            except RateLimitError:
                logger.warning(
                    "[STEP 4/7] Rate limit hit - stopping all player processing",
                    players_completed=fetched_count,
                    players_total=len(players_to_fetch),
                )
                # Stop processing remaining players
                break
            except NotFoundError:
                logger.debug(
                    "[STEP 4/7] Discovered player not found in Riot API - skipping",
                    puuid=player.puuid,
                )
                continue
            except asyncio.TimeoutError:
                logger.error(
                    "[STEP 4/7] TIMEOUT processing player - skipping",
                    puuid=player.puuid,
                )
                continue
            except Exception as e:
                logger.error(
                    "[STEP 4/7] ERROR processing player - skipping",
                    puuid=player.puuid,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                continue

        self.add_log_entry("discovered_players_fetched", fetched_count)
        self.add_log_entry("total_matches_fetched", total_matches_fetched)

        logger.info(
            "[STEP 7/7] Discovered player match fetching complete",
            players_processed=fetched_count,
            total_players=len(players_to_fetch),
            total_matches=total_matches_fetched,
        )

    async def _store_match_for_discovered_player(
        self, db: AsyncSession, match_dto: Any
    ) -> None:
        """Store match and participants in database for a discovered player.

        Args:
            db: Database session.
            match_dto: Match DTO from Riot API.

        Note: Does not commit - caller must commit the transaction.
        """
        from ..models.matches import Match
        from ..models.participants import MatchParticipant

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
        ensured_players: set[str] = set()
        for participant in match_dto.info.participants:
            participant_puuid = participant.puuid

            if participant_puuid not in ensured_players:
                result_player = await db.execute(
                    select(Player.puuid).where(Player.puuid == participant_puuid)
                )
                if result_player.scalar_one_or_none() is None:
                    placeholder_player = Player(
                        puuid=participant_puuid,
                        platform=platform_id.upper(),
                        riot_id=participant.riot_id_game_name or None,
                        tag_line=participant.riot_id_tagline or None,
                        summoner_name=participant.summoner_name or None,
                        account_level=participant.summoner_level,
                        is_active=True,
                        is_tracked=False,
                        is_analyzed=False,
                    )
                    db.add(placeholder_player)
                    logger.debug(
                        "Created placeholder player for participant",
                        puuid=participant_puuid[:8],
                        match_id=match_dto.metadata.match_id,
                    )
                ensured_players.add(participant_puuid)

            # Note: Riot API sometimes returns empty strings for name fields
            # Convert empty strings to None for proper database storage
            match_participant = MatchParticipant(
                match_id=match_dto.metadata.match_id,
                puuid=participant_puuid,
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

        Only selects players who have sufficient match history (>= 20 matches).
        This avoids wasting API calls on players with insufficient data.

        Args:
            db: Database session.

        Returns:
            List of unanalyzed players with sufficient match history.
        """
        from ..models.participants import MatchParticipant

        # Get players with at least 20 matches for meaningful analysis
        # This subquery counts matches per player
        stmt = (
            select(Player)
            .join(MatchParticipant, Player.puuid == MatchParticipant.puuid)
            .where(Player.is_tracked.is_(False))
            .where(Player.is_analyzed.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(func.count(MatchParticipant.match_id) >= 20)
            .limit(self.unanalyzed_players_per_run)
        )
        result = await db.execute(stmt)
        players = result.scalars().all()

        logger.info(
            "Found unanalyzed players with sufficient match history",
            count=len(players),
            required_matches=20,
        )

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
        """Check if player has sufficient match history for analysis.

        This method no longer fetches matches - that's done by _fetch_discovered_player_matches.
        It just validates the player has enough data.

        Args:
            db: Database session.
            player: Player to check match history for.
        """
        try:
            # Check how many matches we have for this player
            from ..models.participants import MatchParticipant

            stmt = select(func.count(MatchParticipant.match_id)).where(
                MatchParticipant.puuid == player.puuid
            )
            result = await db.execute(stmt)
            existing_match_count = result.scalar() or 0

            logger.debug(
                "Player match history check",
                puuid=player.puuid,
                match_count=existing_match_count,
            )

        except Exception as e:
            logger.error(
                "Failed to check match history",
                puuid=player.puuid,
                error=str(e),
            )
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

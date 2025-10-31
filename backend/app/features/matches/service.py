"""Match service for handling match data operations.

REFACTORED: Enterprise Architecture with Repository Pattern
- Service layer is now thin (orchestration only)
- All database queries delegated to MatchRepository
- Business logic lives in domain models (MatchORM)
- Gateway handles Riot API integration
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.players.orm_models import PlayerORM
from app.core.riot_api.errors import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    RiotAPIError,
)
from app.core.riot_api.transformers import MatchTransformer as CoreMatchTransformer

from .gateway import RiotMatchGateway
from .orm_models import MatchORM
from .participants_orm import MatchParticipantORM
from .repository import (
    MatchParticipantRepositoryInterface,
    MatchRepositoryInterface,
    SQLAlchemyMatchParticipantRepository,
    SQLAlchemyMatchRepository,
)
from .schemas import (
    MatchListResponse,
    MatchStatsResponse,
)
from .transformers import (
    MatchTransformer as MatchDataMapper,
)

if TYPE_CHECKING:
    from app.core.riot_api.client import RiotAPIClient

logger = structlog.get_logger(__name__)


class MatchService:
    """Service for handling match data operations (Thin Orchestration Layer).

    Responsibilities:
    - Orchestrate operations across repository and external services
    - Validate inputs and handle errors
    - Transform between domain models and API schemas
    - Coordinate business workflows

    Does NOT:
    - Execute SQL queries directly (delegated to repository)
    - Contain business logic (lives in domain models)
    - Know about database implementation details
    - Make direct API calls (use RiotMatchGateway instead)
    """

    # Type annotations for all instance attributes
    repository: MatchRepositoryInterface
    participant_repository: MatchParticipantRepositoryInterface
    riot_gateway: RiotMatchGateway | None
    transformer: CoreMatchTransformer
    db: AsyncSession | None  # Only available in legacy mode

    def __init__(
        self,
        repository_or_db: MatchRepositoryInterface | AsyncSession,
        participant_repository: Optional[MatchParticipantRepositoryInterface] = None,
        riot_gateway: Optional[RiotMatchGateway] = None,
    ):
        """Initialize match service with repository and gateway.

        Supports two initialization modes:
        1. New (recommended): Pass MatchRepositoryInterface + RiotMatchGateway
        2. Legacy (for jobs): Pass AsyncSession only (creates defaults)

        :param repository_or_db: Repository instance or AsyncSession for legacy mode
        :param participant_repository: Match participant repository (new mode only)
        :param riot_gateway: Anti-Corruption Layer for Riot API (new mode only)
        """
        # Handle both new and legacy initialization
        if isinstance(repository_or_db, AsyncSession):
            # Legacy mode: create defaults (for backward compatibility with jobs)
            self.db = repository_or_db  # Store database session for legacy mode
            self.repository = SQLAlchemyMatchRepository(repository_or_db)
            self.participant_repository = SQLAlchemyMatchParticipantRepository(
                repository_or_db
            )
            self.riot_gateway = None  # Will be created lazily if needed
        else:
            # New mode: use provided dependencies
            self.db = None  # No direct database access in enterprise mode
            self.repository = repository_or_db
            if participant_repository is None:
                raise ValueError(
                    "participant_repository is required when using new initialization mode. "
                    "Use dependencies.get_match_service() for proper DI."
                )
            self.participant_repository = participant_repository
            if riot_gateway is None:
                raise ValueError(
                    "riot_gateway is required when using new initialization mode. "
                    "Use dependencies.get_match_service() for proper DI."
                )
            self.riot_gateway = riot_gateway

        # Keep transformer for legacy compatibility
        self.transformer = CoreMatchTransformer()

    async def get_player_matches(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> MatchListResponse:
        """
        Get match history for a player from database only (REFACTORED).

        Never calls Riot API - returns whatever matches are available in database.
        Supports pagination for infinite scroll.

        Args:
            puuid: PlayerORM PUUID
            start: Start index for pagination
            count: Number of matches to return
            queue: Filter by queue ID
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            MatchListResponse with matches from database
        """
        try:
            # Get matches from database using repository
            match_orms = await self.repository.find_by_player(
                puuid=puuid,
                limit=count,
                offset=start,
                queue_id=queue,
                start_time=start_time,
                end_time=end_time,
            )

            # Get total count of matches for pagination using repository
            total_count = await self.repository.count_player_matches(
                puuid=puuid,
                queue_id=queue,
                start_time=start_time,
                end_time=end_time,
            )

            # Transform ORM models to response schemas using MatchDataMapper
            match_responses = [
                MatchDataMapper.match_orm_to_response(match_orm)
                for match_orm in match_orms
            ]

            # Calculate page-based pagination from start/count
            page = (start // count) if count > 0 else 0
            size = count
            pages = ((total_count + count - 1) // count) if count > 0 else 0

            logger.debug(
                "Retrieved matches from database",
                puuid=puuid,
                matches_count=len(match_responses),
                total_count=total_count,
                page=page,
                size=size,
            )

            return MatchListResponse(
                matches=match_responses,
                total=total_count,
                page=page,
                size=size,
                pages=pages,
            )
        except Exception as e:
            logger.error(
                "Failed to get player matches from database", puuid=puuid, error=str(e)
            )
            raise

    @staticmethod
    def _create_empty_stats_response(puuid: str) -> MatchStatsResponse:
        """Create stats response for players with no matches."""
        return MatchStatsResponse(
            puuid=puuid,
            total_matches=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            avg_kills=0.0,
            avg_deaths=0.0,
            avg_assists=0.0,
            avg_kda=0.0,
            avg_cs=0.0,
            avg_vision_score=0.0,
        )

    async def get_player_stats(
        self, puuid: str, queue: Optional[int] = None, limit: int = 50
    ) -> MatchStatsResponse:
        """
        Calculate player statistics from recent matches (REFACTORED).

        Args:
            puuid: PlayerORM PUUID
            queue: Filter by queue ID
            limit: Number of matches to analyze

        Returns:
            MatchStatsResponse with player statistics
        """
        try:
            # Get recent matches for the player using repository
            match_orms = await self.repository.find_by_player(
                puuid=puuid,
                limit=limit,
                offset=0,
                queue_id=queue,
                start_time=None,
                end_time=None,
            )

            if not match_orms:
                return self._create_empty_stats_response(puuid)

            # Get participants for these matches using participant repository
            match_ids = [m.match_id for m in match_orms]
            participants: list[MatchParticipantORM] = []
            for match_id in match_ids:
                participant = await self.participant_repository.get_by_match_and_player(
                    match_id, puuid
                )
                if participant:
                    participants.append(participant)

            participants_by_match = {p.match_id: p for p in participants}

            # Aggregate statistics using the domain model method
            total_kills, total_deaths, total_assists, total_cs, total_vision, wins = (
                MatchParticipantORM.aggregate_participant_stats(
                    match_orms, participants_by_match
                )
            )

            total_matches = len(match_orms)
            avg_kda = MatchParticipantORM.calculate_kda_from_values(
                total_kills, total_deaths, total_assists
            )

            # total_matches is guaranteed > 0 (checked for empty matches above)
            return MatchStatsResponse(
                puuid=puuid,
                total_matches=total_matches,
                wins=wins,
                losses=total_matches - wins,
                win_rate=wins / total_matches,
                avg_kills=total_kills / total_matches,
                avg_deaths=total_deaths / total_matches,
                avg_assists=total_assists / total_matches,
                avg_kda=avg_kda,
                avg_cs=total_cs / total_matches,
                avg_vision_score=total_vision / total_matches,
            )
        except Exception as e:
            logger.error("Failed to get player stats", puuid=puuid, error=str(e))
            raise

    async def _fetch_match_ids_from_api(self, puuid: str, queue: int) -> list[str]:
        """
        Fetch match IDs from Riot API using gateway.

        Raises:
            RiotAPIError: API errors that should propagate
        """
        if not self.riot_gateway:
            raise RuntimeError("RiotMatchGateway is required for API operations")

        try:
            match_ids = await self.riot_gateway.fetch_player_match_history(
                puuid=puuid,
                count=100,
                queue=queue,
            )

            logger.debug(
                "Fetched match IDs from Riot API via gateway",
                puuid=puuid,
                queue=queue,
                api_returned_count=len(match_ids),
                requested_count=100,
            )

            return match_ids
        except NotFoundError as e:
            logger.warning(
                "Player not found in Riot API",
                puuid=puuid,
                error=str(e),
            )
            return []  # Return empty list for not found players
        except RateLimitError as e:
            logger.warning(
                "Rate limit hit while fetching match list",
                puuid=puuid,
                retry_after=getattr(e, "retry_after", None),
            )
            raise  # Let job handler convert to RateLimitSignal
        except (AuthenticationError, ForbiddenError) as e:
            logger.error(
                "Authentication error fetching match list - cannot continue",
                puuid=puuid,
                error=str(e),
                status_code=e.status_code,
            )
            raise  # Always fail immediately on auth errors

    async def _get_new_match_ids(self, all_match_ids: list[str]) -> list[str]:
        """Filter match IDs to only those not in database (REFACTORED)."""
        if not all_match_ids:
            return []

        # Use repository to filter existing matches
        return await self.repository.filter_existing_matches(all_match_ids)

    async def _fetch_and_store_single_match(self, match_id: str) -> bool:
        """
        Fetch and store a single match using gateway.

        Returns:
            True if successfully stored, False otherwise

        Raises:
            RateLimitError: If rate limit is hit (should stop processing)
        """
        if not self.riot_gateway:
            raise RuntimeError("RiotMatchGateway is required for API operations")

        try:
            # Use gateway to fetch match details (Anti-Corruption Layer)
            match_orm = await self.riot_gateway.fetch_match_details(match_id)

            # Store the match using repository
            await self.repository.create(match_orm)

            # Store participants using participant repository
            if match_orm.participants:
                await self.participant_repository.create_bulk(match_orm.participants)

            logger.debug(
                "Successfully fetched and stored match via gateway",
                match_id=match_id,
                participants=len(match_orm.participants)
                if match_orm.participants
                else 0,
            )
            return True

        except RateLimitError:
            logger.warning("Rate limit hit fetching match", match_id=match_id)
            raise
        except Exception as e:
            logger.warning("Failed to fetch match", match_id=match_id, error=str(e))
            return False

    def _validate_platform_code(self, platform: str, puuid: str) -> bool:
        """Validate platform code. Returns True if valid, False if invalid."""
        from app.core.riot_api.constants import Platform

        try:
            Platform(platform.lower())
            return True
        except ValueError:
            logger.warning("Invalid platform", puuid=puuid, platform=platform)
            return False

    async def _fetch_new_match_ids_for_player(
        self, puuid: str, queue: int
    ) -> list[str]:
        """Fetch and filter to only new match IDs using gateway."""
        all_match_ids = await self._fetch_match_ids_from_api(puuid, queue)
        if not all_match_ids:
            logger.debug("No matches found for player", puuid=puuid)
            return []

        new_match_ids = await self._get_new_match_ids(all_match_ids)
        already_in_db = len(all_match_ids) - len(new_match_ids)

        logger.debug(
            "Match ID filtering results",
            puuid=puuid,
            total_from_api=len(all_match_ids),
            already_in_database=already_in_db,
            new_matches=len(new_match_ids),
        )

        if not new_match_ids:
            logger.debug("All matches already in database", puuid=puuid)
            return []

        return new_match_ids

    async def fetch_and_store_matches_for_player(
        self,
        puuid_or_client: "str | RiotAPIClient",  # Legacy: RiotAPIClient, New: PUUID
        puuid: str | None = None,  # Legacy: PUUID, New: None
        count: int = 1,
        queue: int = 420,
        platform: str = "EUN1",
    ) -> int:
        """
        Fetch match history from Riot API and store new matches for a player.

        Supports both legacy mode (for jobs) and new enterprise mode.
        This method checks the database before fetching to avoid duplicate API calls.

        Args:
            puuid_or_client: Legacy - RiotAPIClient instance, New - Player PUUID
            puuid: Legacy - Player PUUID, New - None
            count: Maximum number of NEW matches to fetch (not total matches)
            queue: Queue ID filter (default: 420 = Ranked Solo/Duo)
            platform: Platform ID for the player

        Returns:
            Number of new matches fetched and stored

        Raises:
            RateLimitError: If Riot API rate limit is hit
            AuthenticationError: If API key is invalid
            ForbiddenError: If API key is expired
            ValueError: If invalid platform provided
        """
        actual_puuid = ""  # Initialize to prevent unbound variable error
        try:
            # Handle both legacy and new parameter patterns
            if isinstance(puuid_or_client, str):
                # New mode: puuid_or_client is PUUID, puuid is None
                actual_puuid = puuid_or_client
                if not self.riot_gateway:
                    raise RuntimeError(
                        "RiotMatchGateway is required in enterprise mode"
                    )
            else:
                # Legacy mode: puuid_or_client is RiotAPIClient, puuid is PUUID
                if puuid is None:
                    raise ValueError("puuid is required in legacy mode")
                actual_puuid = puuid
                logger.warning(
                    "Using legacy mode with direct Riot API client - should migrate to gateway pattern"
                )

            # Validate platform
            if not self._validate_platform_code(platform, actual_puuid):
                return 0

            # Fetch new match IDs
            new_match_ids = await self._fetch_new_match_ids_for_player(
                actual_puuid, queue
            )
            if not new_match_ids:
                return 0

            # Fetch requested count of new matches
            fetched_count = 0
            for match_id in new_match_ids[:count]:
                if await self._fetch_and_store_single_match(match_id):
                    fetched_count += 1

            logger.info(
                "Fetched matches for player",
                puuid=actual_puuid,
                count=fetched_count,
                new_matches=len(new_match_ids),
                mode="gateway" if self.riot_gateway else "legacy",
            )
            return fetched_count

        except RiotAPIError:
            # Re-raise RiotAPI errors (rate limits, auth errors, etc.) to caller
            raise
        except Exception as e:
            logger.error(
                "Failed to fetch and store matches", puuid=actual_puuid, error=str(e)
            )
            return 0

    def _get_summoner_name_for_puuid(
        self, puuid: str, participants: List[Dict[str, Any]]
    ) -> str:
        """Extract summoner name for a PUUID from participant data."""
        summoner_name = next(
            (p["summoner_name"] for p in participants if p["puuid"] == puuid),
            None,
        )
        # Ensure summoner_name is never null or empty
        if not summoner_name or summoner_name.strip() == "":
            return "Unknown PlayerORM"
        return summoner_name

    async def _ensure_players_exist(
        self,
        participants: List[Dict[str, Any]],
        platform_id: str,
    ) -> None:
        """Ensure all participant players exist in database, creating if needed (REFACTORED)."""
        # Import players repository for this operation
        from app.features.players.repository import SQLAlchemyPlayerRepository

        # Create players repository if in legacy mode
        if self.db is not None:
            players_repo = SQLAlchemyPlayerRepository(self.db)
        else:
            # In new mode, we don't have direct db access, so skip this operation
            # This method should be handled at a higher level in the new architecture
            logger.debug("Skipping player creation in new enterprise mode")
            return

        # Bulk check for existing players
        participant_puuids = {p["puuid"] for p in participants}

        # Check existing players one by one (repository pattern)
        existing_puuids: set[str] = set()
        for puuid in participant_puuids:
            player = await players_repo.get_by_puuid(puuid)
            if player:
                existing_puuids.add(puuid)

        # Bulk create missing players
        missing_puuids = participant_puuids - existing_puuids
        if not missing_puuids:
            return

        # For now, create using direct database access for legacy compatibility
        # In full enterprise mode, this should be handled by PlayerService

        new_players = [
            PlayerORM(
                puuid=puuid,
                summoner_name=self._get_summoner_name_for_puuid(puuid, participants),
                platform=platform_id.lower(),
                is_active=False,
            )
            for puuid in missing_puuids
        ]

        self.db.add_all(new_players)  # type: ignore
        logger.debug("Created minimal player records", count=len(new_players))

    async def _store_match_detail(self, match_data: Dict[str, Any]) -> MatchORM:
        """Store match detail in database (REFACTORED)."""
        try:
            # Validate match data
            if not self.transformer.validate_match_data(match_data):
                raise ValueError("Invalid match data")

            transformed = self.transformer.transform_match_data(match_data)
            platform_id = transformed["match"].get("platform_id", "EUN1")

            # Ensure all participant players exist (legacy mode only)
            if self.db is not None:
                await self._ensure_players_exist(
                    transformed["participants"], platform_id
                )

            # For legacy mode, use direct database access
            if self.db is not None:
                # Store match and participants using ORM models
                match = MatchORM(**transformed["match"])
                self.db.add(match)  # type: ignore

                participants = [
                    MatchParticipantORM(**p_data)
                    for p_data in transformed["participants"]
                ]
                self.db.add_all(participants)  # type: ignore

                await self.db.commit()  # type: ignore
                await self.db.refresh(match)  # type: ignore

                logger.info(
                    "Stored match detail (legacy mode)", match_id=match.match_id
                )
                return match
            else:
                # In new enterprise mode, this should be handled differently
                # For now, raise an error to indicate this needs to be refactored
                raise NotImplementedError(
                    "_store_match_detail needs to be refactored for enterprise mode. "
                    "Use gateway pattern instead."
                )
        except Exception as e:
            if self.db is not None:
                await self.db.rollback()  # type: ignore
            logger.error("Failed to store match detail", error=str(e))
            raise

    # ============================================
    # Helper Methods for Jobs
    # ============================================

    async def store_match_from_dto(
        self, match_dto: Any, default_platform: str = "EUN1"
    ) -> MatchORM:
        """Store match and participants from Riot API DTO using gateway pattern.

        This method handles:
        - Creating Match record using repository pattern
        - Creating MatchParticipantORM records using participant repository
        - Using Anti-Corruption Layer (gateway) for transformations

        Args:
            match_dto: Match DTO from Riot API
            default_platform: Default platform if not in DTO

        Returns:
            Stored Match object

        Raises:
            Exception: If storage fails

        Note:
            Caller must commit the transaction (legacy mode only).
            In enterprise mode, repositories handle transactions.
        """
        try:
            # Use Anti-Corruption Layer (gateway) for transformations
            if self.riot_gateway:
                # Enterprise mode: Use gateway for transformation
                match_orm = self.riot_gateway._transform_match_dto(match_dto)

                # Store match using repository
                created_match = await self.repository.create(match_orm)

                # Store participants using participant repository
                if match_orm.participants:
                    await self.participant_repository.create_bulk(
                        match_orm.participants
                    )

                logger.debug(
                    "Stored match from DTO (enterprise mode via gateway)",
                    match_id=match_dto.metadata.match_id,
                    participant_count=len(match_dto.info.participants),
                )

                return created_match
            else:
                # Legacy mode: Direct transformation and database access
                logger.warning(
                    "Using legacy mode for store_match_from_dto - should migrate to gateway pattern"
                )

                from .transformers import MatchDTOTransformer

                # Extract platform
                platform_id = match_dto.info.platform_id or default_platform

                # For legacy mode, use direct database access
                if hasattr(self, "db"):
                    # Create MatchORM record
                    match = MatchORM(
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

                    self.db.add(match)  # type: ignore

                    # Create MatchParticipantORM records
                    for participant in match_dto.info.participants:
                        participant_data = MatchDTOTransformer.extract_participant_data(
                            participant
                        )
                        match_participant = MatchParticipantORM(
                            match_id=match_dto.metadata.match_id,
                            **participant_data,
                        )
                        self.db.add(match_participant)  # type: ignore

                    logger.debug(
                        "Stored match from DTO (legacy mode)",
                        match_id=match_dto.metadata.match_id,
                        participant_count=len(match_dto.info.participants),
                    )

                    return match
                else:
                    raise NotImplementedError(
                        "Legacy mode requires direct database access - missing 'db' attribute"
                    )

        except Exception as e:
            logger.error(
                "Failed to store match from DTO",
                match_id=(
                    match_dto.metadata.match_id
                    if hasattr(match_dto, "metadata")
                    else "unknown"
                ),
                error=str(e),
                mode="gateway" if self.riot_gateway else "legacy",
            )
            raise

    async def count_player_matches(self, puuid: str) -> int:
        """Get count of matches for a player in database (REFACTORED).

        Args:
            puuid: PlayerORM PUUID

        Returns:
            Number of matches in database
        """
        return await self.repository.count_player_matches(puuid)

    async def get_player_last_match_time(self, puuid: str) -> Optional[int]:
        """Get timestamp of player's most recent match in database (REFACTORED).

        Args:
            puuid: PlayerORM PUUID

        Returns:
            Timestamp in milliseconds, or None if no matches
        """
        return await self.repository.get_player_last_match_time(puuid)

    async def filter_existing_matches(self, match_ids: List[str]) -> List[str]:
        """Filter out matches that already exist in database (REFACTORED).

        Args:
            match_ids: List of match IDs to check

        Returns:
            List of match IDs not in database
        """
        return await self.repository.filter_existing_matches(match_ids)

    # ============================================
    # Gateway-Based Methods for Enterprise Mode
    # ============================================

    async def fetch_and_store_match(self, match_id: str) -> MatchORM:
        """Fetch a single match from Riot API and store it using gateway pattern.

        This is the recommended method for fetching matches in enterprise mode.
        Uses the Anti-Corruption Layer to transform Riot API data to domain models.

        Args:
            match_id: Riot match identifier

        Returns:
            Stored MatchORM with participants

        Raises:
            RuntimeError: If gateway is not available
            RiotAPIError: If API call fails
        """
        if not self.riot_gateway:
            raise RuntimeError("RiotMatchGateway is required for this operation")

        try:
            # Use Anti-Corruption Layer to fetch and transform
            match_orm = await self.riot_gateway.fetch_match_details(match_id)

            # Store using repository pattern
            created_match = await self.repository.create(match_orm)

            # Store participants using participant repository
            if match_orm.participants:
                await self.participant_repository.create_bulk(match_orm.participants)

            logger.info(
                "Successfully fetched and stored match via gateway",
                match_id=match_id,
                participants=len(match_orm.participants)
                if match_orm.participants
                else 0,
            )

            return created_match

        except Exception as e:
            logger.error(
                "Failed to fetch and store match via gateway",
                match_id=match_id,
                error=str(e),
            )
            raise

    async def fetch_player_match_ids_via_gateway(
        self,
        puuid: str,
        count: int = 20,
        queue: int = 420,
    ) -> List[str]:
        """Fetch player match history using gateway pattern.

        Args:
            puuid: Player PUUID
            count: Number of matches to fetch
            queue: Queue ID filter

        Returns:
            List of match IDs

        Raises:
            RuntimeError: If gateway is not available
            RiotAPIError: If API call fails
        """
        if not self.riot_gateway:
            raise RuntimeError("RiotMatchGateway is required for this operation")

        try:
            match_ids = await self.riot_gateway.fetch_player_match_history(
                puuid=puuid,
                count=count,
                queue=queue,
            )

            logger.debug(
                "Fetched player match history via gateway",
                puuid=puuid,
                count=len(match_ids),
                queue=queue,
            )

            return match_ids

        except Exception as e:
            logger.error(
                "Failed to fetch player match history via gateway",
                puuid=puuid,
                error=str(e),
            )
            raise

    async def fetch_new_matches_for_player(
        self,
        puuid: str,
        count: int = 1,
        queue: int = 420,
        platform: str = "EUN1",
    ) -> List[MatchORM]:
        """Fetch and store new matches for a player using gateway pattern.

        This is the enterprise mode equivalent of fetch_and_store_matches_for_player
        but uses the gateway pattern and returns the actual matches.

        Args:
            puuid: Player PUUID
            count: Maximum number of NEW matches to fetch
            queue: Queue ID filter (default: 420 = Ranked Solo/Duo)
            platform: Platform ID for the player

        Returns:
            List of newly fetched and stored MatchORM objects

        Raises:
            RuntimeError: If gateway is not available
            ValueError: If invalid platform provided
            RiotAPIError: If API call fails
        """
        if not self.riot_gateway:
            raise RuntimeError("RiotMatchGateway is required for enterprise mode")

        try:
            # Validate platform
            if not self._validate_platform_code(platform, puuid):
                raise ValueError(f"Invalid platform code: {platform}")

            # Fetch new match IDs using gateway
            all_match_ids = await self.fetch_player_match_ids_via_gateway(
                puuid, 100, queue
            )
            if not all_match_ids:
                logger.debug("No matches found for player", puuid=puuid)
                return []

            # Filter to only new matches
            new_match_ids = await self._get_new_match_ids(all_match_ids)
            if not new_match_ids:
                logger.debug("All matches already in database", puuid=puuid)
                return []

            # Fetch and store requested count of new matches
            fetched_matches: list[MatchORM] = []
            for match_id in new_match_ids[:count]:
                match_orm = await self.fetch_and_store_match(match_id)
                fetched_matches.append(match_orm)

            logger.info(
                "Fetched new matches for player via gateway",
                puuid=puuid,
                count=len(fetched_matches),
                new_matches_available=len(new_match_ids),
            )

            return fetched_matches

        except Exception as e:
            logger.error(
                "Failed to fetch new matches for player via gateway",
                puuid=puuid,
                error=str(e),
            )
            raise

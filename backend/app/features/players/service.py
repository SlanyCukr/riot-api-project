"""Player service for handling player data operations.

REFACTORED: Enterprise Architecture with Repository Pattern
- Service layer is now thin (orchestration only)
- All database queries delegated to PlayerRepository
- Business logic lives in domain models (PlayerORM)
- Transformers handle ORM ↔ Pydantic conversions
- Anti-Corruption Layer via RiotAPIGateway isolates external API usage
"""

from typing import List, Any, TYPE_CHECKING
from datetime import datetime
from Levenshtein import distance as levenshtein_distance
import structlog

from .orm_models import PlayerORM, PlayerRankORM
from .schemas import PlayerResponse
from .repository import PlayerRepositoryInterface
from .transformers import player_orm_to_response
from .gateway import RiotAPIGateway
from app.core.exceptions import (
    PlayerServiceError,
)
from app.core.decorators import service_error_handler, input_validation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class PlayerService:
    """Service for handling player data operations (Thin Orchestration Layer).

    Responsibilities:
    - Orchestrate operations across repository and external services
    - Validate inputs and handle errors
    - Transform between domain models and API schemas
    - Coordinate business workflows

    Does NOT:
    - Execute SQL queries directly (delegated to repository)
    - Contain business logic (lives in domain models)
    - Know about database implementation details
    - Make direct API calls (use RiotAPIGateway instead)
    """

    def __init__(
        self,
        repository_or_db: PlayerRepositoryInterface | AsyncSession,
        riot_gateway: RiotAPIGateway | None = None,
    ):
        """Initialize player service with repository and gateway.

        Supports two initialization modes:
        1. New (recommended): Pass PlayerRepositoryInterface + RiotAPIGateway
        2. Legacy (for jobs): Pass AsyncSession only (creates defaults)

        :param repository_or_db: Repository instance or AsyncSession for legacy mode
        :param riot_gateway: Anti-Corruption Layer for Riot API (new mode only)
        """
        # Handle both new and legacy initialization
        if isinstance(repository_or_db, AsyncSession):
            # Legacy mode: create defaults (for backward compatibility with jobs)
            from .repository import SQLAlchemyPlayerRepository
            from app.core.riot_api.client import RiotAPIClient

            # Create default repository and gateway for jobs
            self.repository = SQLAlchemyPlayerRepository(repository_or_db)
            self.riot_gateway = RiotAPIGateway(RiotAPIClient())
        else:
            # New mode: use provided dependencies
            self.repository = repository_or_db
            if riot_gateway is None:
                raise ValueError(
                    "riot_gateway is required when using new initialization mode. "
                    "Use dependencies.get_player_service() for proper DI."
                )
            self.riot_gateway = riot_gateway

    @service_error_handler("PlayerService")
    @input_validation(
        validate_non_empty=["game_name", "platform"],
    )
    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """Get player by Riot ID from database (REFACTORED).

        Thin orchestration layer:
        1. Normalize inputs
        2. Delegate query to repository
        3. Transform ORM → Pydantic via transformer

        :param game_name: Riot ID game name
        :param tag_line: Riot ID tag line
        :param platform: Platform code (e.g., "NA1", "EUW1")
        :returns: Player response schema
        :raises PlayerServiceError: If player not found
        """
        # Step 1: Normalize inputs
        safe_game_name = game_name.strip()
        safe_tag_line = tag_line.strip() if tag_line else None
        normalized_platform = platform.strip().upper()

        # Step 2: Delegate query to repository
        player_orm = await self.repository.find_by_riot_id(
            safe_game_name, safe_tag_line, normalized_platform
        )

        if not player_orm:
            raise PlayerServiceError(
                message=f"Player not found in database: {safe_game_name}#{safe_tag_line} on {normalized_platform}. "
                f"Please track this player first.",
                operation="get_player_by_riot_id",
                context={
                    "game_name": safe_game_name,
                    "tag_line": safe_tag_line,
                    "platform": normalized_platform,
                },
            )

        logger.info(
            "Player data retrieved from database",
            game_name=safe_game_name,
            tag_line=safe_tag_line,
            platform=normalized_platform,
            puuid=player_orm.puuid,
        )

        # Step 3: Transform ORM → Pydantic
        return player_orm_to_response(player_orm)

    def _find_exact_summoner_match(self, players: list, safe_summoner_name: str):
        """Find exact summoner name match from list of players.

        Works with both Player and PlayerORM models.

        :param players: List of player models
        :param safe_summoner_name: Normalized summoner name to match
        :returns: Matching player or None
        """
        for player in players:
            if (
                player.summoner_name
                and player.summoner_name.lower() == safe_summoner_name.lower()
            ):
                return player
        return None

    def _handle_no_summoner_matches(
        self, safe_summoner_name: str, normalized_platform: str
    ) -> None:
        """Raise error when no summoner name matches found."""
        logger.info(
            "No player found in database for summoner name",
            summoner_name=safe_summoner_name,
            platform=normalized_platform,
        )
        raise PlayerServiceError(
            message=f"No players found matching '{safe_summoner_name}' on {normalized_platform}. "
            f"Please check the summoner name and platform, or track this player first.",
            operation="get_player_by_summoner_name",
            context={
                "summoner_name": safe_summoner_name,
                "platform": normalized_platform,
            },
        )

    async def get_player_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> PlayerResponse:
        """Get player by summoner name from database (REFACTORED).

        Thin orchestration with fuzzy search logic.

        :param summoner_name: Summoner name to search
        :param platform: Platform code
        :returns: Player response
        :raises PlayerServiceError: If player not found or multiple matches
        """
        # Normalize inputs
        safe_summoner_name = summoner_name.strip()
        normalized_platform = platform.strip().upper()

        # Delegate fuzzy search to repository
        players = await self.repository.find_by_summoner_name(
            safe_summoner_name, normalized_platform
        )

        # Try to find exact match first
        exact_match = self._find_exact_summoner_match(players, safe_summoner_name)
        if exact_match:
            logger.info(
                "Found exact match for summoner name",
                summoner_name=safe_summoner_name,
                platform=normalized_platform,
                puuid=exact_match.puuid,
            )
            return player_orm_to_response(exact_match)

        # If only one partial match, return it
        if len(players) == 1:
            logger.info(
                "Found single partial match for summoner name",
                summoner_name=safe_summoner_name,
                platform=normalized_platform,
                matched_name=players[0].summoner_name,
            )
            return player_orm_to_response(players[0])

        # If multiple partial matches, return error with suggestions
        if len(players) > 1:
            matched_names = [p.summoner_name for p in players if p.summoner_name]
            logger.info(
                "Found multiple matches for summoner name",
                summoner_name=safe_summoner_name,
                platform=normalized_platform,
                matches=matched_names,
            )
            raise PlayerServiceError(
                message=f"Multiple players found matching '{safe_summoner_name}': {', '.join(matched_names)}. "
                f"Please be more specific.",
                operation="get_player_by_summoner_name",
                context={
                    "summoner_name": safe_summoner_name,
                    "platform": normalized_platform,
                    "matches": matched_names,
                },
            )

        # No matches found
        self._handle_no_summoner_matches(safe_summoner_name, normalized_platform)

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Get player by PUUID from database (REFACTORED).

        Thin orchestration: delegate to repository, transform response.

        :param puuid: Player's unique identifier
        :param platform: Platform code (unused, kept for compatibility)
        :returns: Player response schema
        :raises PlayerServiceError: If player not found
        """
        # Delegate query to repository
        player_orm = await self.repository.get_by_puuid(puuid)

        if not player_orm:
            raise PlayerServiceError(
                message=f"Player not found in database: {puuid}. "
                f"Please track this player first.",
                operation="get_player_by_puuid",
                context={"puuid": puuid, "platform": platform},
            )

        logger.info(
            "Player data retrieved by PUUID from database",
            puuid=puuid,
            platform=platform,
        )

        # Transform ORM → Pydantic
        return player_orm_to_response(player_orm)

    @staticmethod
    def _parse_search_query(query: str) -> tuple[str, str | None, str | None]:
        """
        Parse search query to detect search type and extract components.

        Returns:
            Tuple of (search_type, game_name, tag_line)
            search_type: "riot_id", "tag", "name", or "all"
        """
        if query.startswith("#"):
            # Tag-only search: "#EUW"
            return "tag", None, query[1:].strip()

        if "#" in query:
            # Riot ID search: "DangerousDan#EUW"
            if query.count("#") == 1:
                game_name, tag_line = query.split("#", 1)
                return "riot_id", game_name.strip(), tag_line.strip()
            # Multiple # - treat as invalid, search everything
            return "all", None, None

        # Name search: "DangerousDan"
        return "name", query.strip(), None

    @staticmethod
    def _check_exact_riot_id_match(
        player: PlayerORM, game_name: str, tag_line: str
    ) -> bool:
        """Check if player is an exact Riot ID match."""
        return (
            player.riot_id
            and player.riot_id.lower() == game_name.lower()
            and player.tag_line
            and player.tag_line.lower() == tag_line.lower()
        )

    @staticmethod
    def _score_summoner_name(
        player: PlayerORM, search_type: str, query_lower: str
    ) -> int | None:
        """Calculate distance for summoner name if applicable."""
        if player.summoner_name and (search_type in ["name", "all"]):
            return levenshtein_distance(query_lower, player.summoner_name.lower())
        return None

    @staticmethod
    def _score_riot_id(
        player: PlayerORM, search_type: str, query_lower: str
    ) -> int | None:
        """Calculate distance for riot_id if applicable."""
        if player.riot_id and (search_type in ["name", "riot_id", "all"]):
            target = (
                (f"{player.riot_id}#{player.tag_line}").lower()
                if player.tag_line
                else player.riot_id.lower()
            )
            return levenshtein_distance(query_lower, target)
        return None

    @staticmethod
    def _score_tag_line(
        player: PlayerORM, search_type: str, query_lower: str, tag_line: str | None
    ) -> int | None:
        """Calculate distance for tag_line if applicable."""
        if player.tag_line and (search_type in ["tag", "riot_id"]):
            tag_query = tag_line.lower() if tag_line else query_lower
            return levenshtein_distance(tag_query, player.tag_line.lower())
        return None

    @staticmethod
    def _calculate_levenshtein_distances(
        player: PlayerORM,
        search_type: str,
        query_lower: str,
        tag_line: str | None,
    ) -> list[int]:
        """Calculate Levenshtein distances for all relevant fields."""
        distances = []

        # Score summoner name
        summoner_dist = PlayerService._score_summoner_name(
            player, search_type, query_lower
        )
        if summoner_dist is not None:
            distances.append(summoner_dist)

        # Score riot_id
        riot_id_dist = PlayerService._score_riot_id(player, search_type, query_lower)
        if riot_id_dist is not None:
            distances.append(riot_id_dist)

        # Score tag_line
        tag_dist = PlayerService._score_tag_line(
            player, search_type, query_lower, tag_line
        )
        if tag_dist is not None:
            distances.append(tag_dist)

        return distances

    @staticmethod
    def _score_player_match(
        player: PlayerORM,
        search_type: str,
        query_lower: str,
        game_name: str | None,
        tag_line: str | None,
    ) -> float:
        """Calculate relevance score for a player match.

        :param player: Player domain model to score
        :param search_type: Type of search being performed
        :param query_lower: Lowercased search query
        :param game_name: Parsed game name
        :param tag_line: Parsed tag line
        :returns: Score where 1000.0 = exact match, 0.0-1.0 = fuzzy match quality
        """
        # Exact Riot ID match = highest priority
        if (
            search_type == "riot_id"
            and game_name
            and tag_line
            and PlayerService._check_exact_riot_id_match(player, game_name, tag_line)
        ):
            return 1000.0

        # Levenshtein scoring for fuzzy matches
        distances = PlayerService._calculate_levenshtein_distances(
            player, search_type, query_lower, tag_line
        )

        if distances:
            min_dist = min(distances)
            # Convert to score: 1 / (1 + distance)
            return 1.0 / (1.0 + min_dist)

        return 0.0

    def _validate_search_query(
        self, query: str, search_type: str, game_name: str | None, tag_line: str | None
    ) -> bool:
        """Validate search query and return False if invalid."""
        if len(query.strip()) < 1:
            logger.warning("Query too short", query=query)
            return False

        if search_type == "riot_id" and (not game_name or not tag_line):
            logger.warning(
                "Invalid Riot ID search: empty game_name or tag_line",
                query=query,
                search_type=search_type,
            )
            return False

        return True

    def _score_and_sort_players(
        self,
        players: list[PlayerORM],
        search_type: str,
        query_lower: str,
        game_name: str | None,
        tag_line: str | None,
        limit: int,
    ) -> list[dict]:
        """Score players by relevance and return top matches.

        :param players: List of player domain models to score
        :param search_type: Type of search being performed
        :param query_lower: Lowercased search query
        :param game_name: Parsed game name
        :param tag_line: Parsed tag line
        :param limit: Maximum results to return
        :returns: List of dicts with player, score, and name keys
        """
        scored_players = [
            {
                "player": player,
                "score": self._score_player_match(
                    player, search_type, query_lower, game_name, tag_line
                ),
                "name": player.summoner_name or player.riot_id or "",
            }
            for player in players
        ]

        scored_players.sort(key=lambda x: (-x["score"], x["name"].lower()))
        return scored_players[:limit]

    async def fuzzy_search_players(
        self, query: str, platform: str, limit: int = 10
    ) -> List[PlayerResponse]:
        """Search for players using fuzzy matching with Levenshtein distance (REFACTORED).

        Auto-detects search type:
        - Contains '#' → Search Riot ID (game_name#tag_line)
        - Starts with '#' → Search tags only
        - Otherwise → Search both summoner_name and riot_id

        Returns up to `limit` results sorted by relevance:
        1. Exact Riot ID match (highest priority)
        2. Best summoner name matches (by Levenshtein distance)
        3. Best tag matches (by Levenshtein distance)
        4. Alphabetical as tiebreaker

        :param query: Search query string
        :param platform: Platform region
        :param limit: Maximum results to return
        :returns: List of PlayerResponse sorted by relevance
        """
        # Parse search query (business logic)
        search_type, game_name, tag_line = self._parse_search_query(query)

        # Validate search query (business logic)
        if not self._validate_search_query(query, search_type, game_name, tag_line):
            return []

        # Delegate search to repository
        query_lower = query.lower().strip()
        players = await self.repository.fuzzy_search_by_type(
            platform, search_type, query_lower, game_name, tag_line, 100
        )

        # Score and sort results (business logic)
        top_players = self._score_and_sort_players(
            players, search_type, query_lower, game_name, tag_line, limit
        )

        logger.info(
            "Fuzzy search completed",
            query=query,
            platform=platform,
            search_type=search_type,
            total_candidates=len(players),
            results_returned=len(top_players),
        )

        # Transform to responses
        return [player_orm_to_response(p["player"]) for p in top_players]

    @service_error_handler("PlayerService")
    @input_validation(validate_non_empty=["puuid"], validate_positive=["limit"])
    async def get_recent_opponents_with_details(
        self, puuid: str, limit: int
    ) -> List[PlayerResponse]:
        """Get recent opponents for a player (REFACTORED).

        Delegates complex join query to repository.

        :param puuid: Player PUUID
        :param limit: Maximum opponents to return
        :returns: List of opponent player responses
        """
        # Delegate complex join query to repository
        opponents = await self.repository.get_recent_opponents(puuid, limit)

        logger.debug(
            "Found recent opponents with details",
            puuid=puuid,
            opponent_count=len(opponents),
            limit=limit,
        )

        # Transform list to responses
        return [player_orm_to_response(player) for player in opponents]

    # === Player Tracking Methods for Automated Jobs ===

    async def add_and_track_player(
        self,
        game_name: str | None = None,
        tag_line: str | None = None,
        summoner_name: str | None = None,
        platform: str = "eun1",
    ) -> PlayerResponse:
        """
        Fetch player from Riot API and immediately track them.

        Combines fetch_player + track_player in one transaction.

        Args:
            game_name: Riot game name (for Riot ID search)
            tag_line: Riot tag line (for Riot ID search)
            summoner_name: Summoner name (legacy, database-only search)
            platform: Platform region (default: eun1)

        Returns:
            PlayerResponse with is_tracked=True

        Raises:
            ValueError: If player not found
        """
        # Step 1: Fetch player data from Riot API using gateway
        if game_name and tag_line:
            # Use RiotAPIGateway to fetch from API and get domain model
            player_orm = await self.riot_gateway.fetch_player_profile(
                game_name, tag_line, platform
            )

            # Step 2: Save to database (or update existing)
            existing_player = await self.repository.get_by_puuid(player_orm.puuid)
            if existing_player:
                # Update existing player
                updated_player = await self.repository.save(player_orm)
                player_response = player_orm_to_response(updated_player)
            else:
                # Create new player
                created_player = await self.repository.create(player_orm)
                player_response = player_orm_to_response(created_player)

        elif summoner_name:
            # For summoner name, try database first
            player_response = await self.get_player_by_summoner_name(
                summoner_name, platform
            )
        else:
            raise ValueError("Either game_name+tag_line or summoner_name required")

        # Step 3: Check if already tracked
        if player_response.is_tracked:
            logger.info(
                "Player is already tracked",
                puuid=player_response.puuid,
                summoner_name=player_response.summoner_name,
            )
            return player_response

        # Step 4: Track the player
        tracked_player = await self.track_player(player_response.puuid)

        logger.info(
            "Player added and tracked successfully",
            puuid=tracked_player.puuid,
            summoner_name=tracked_player.summoner_name,
            platform=platform,
        )

        return tracked_player

    async def track_player(self, puuid: str) -> PlayerResponse:
        """Mark a player as tracked for automated monitoring (REFACTORED).

        Demonstrates domain model usage:
        1. Get player from repository
        2. Use domain model method to mark as tracked
        3. Save via repository
        4. Transform to response

        :param puuid: Player's PUUID to track
        :returns: Updated player data
        :raises ValueError: If player not found
        """
        # Step 1: Get player domain model
        player_orm = await self.repository.get_by_puuid(puuid)

        if not player_orm:
            raise ValueError(f"Player not found: {puuid}")

        # Step 2: Use domain model method (business logic in model)
        player_orm.mark_as_tracked()

        # Step 3: Save via repository
        updated_player = await self.repository.save(player_orm)

        logger.info(
            "Player marked as tracked",
            puuid=puuid,
            summoner_name=updated_player.summoner_name,
        )

        # Step 4: Transform to response
        return player_orm_to_response(updated_player)

    async def untrack_player(self, puuid: str) -> PlayerResponse:
        """Remove a player from tracked status (REFACTORED).

        Same pattern as track_player but uses domain model's unmark method.

        :param puuid: Player's PUUID to untrack
        :returns: Updated player data
        :raises ValueError: If player not found
        """
        # Get player domain model
        player_orm = await self.repository.get_by_puuid(puuid)

        if not player_orm:
            raise ValueError(f"Player not found: {puuid}")

        # Use domain model method
        player_orm.unmark_as_tracked()

        # Save via repository
        updated_player = await self.repository.save(player_orm)

        logger.info(
            "Player unmarked as tracked",
            puuid=puuid,
            summoner_name=updated_player.summoner_name,
        )

        # Transform to response
        return player_orm_to_response(updated_player)

    async def get_tracked_players(self) -> List[PlayerResponse]:
        """Get all players currently marked for tracking (REFACTORED).

        Thin orchestration: delegate to repository, transform list.

        :returns: List of tracked players
        """
        # Delegate to repository
        players_orm = await self.repository.get_tracked_players()

        # Transform list using transformer
        return [player_orm_to_response(p) for p in players_orm]

    async def count_tracked_players(self) -> int:
        """Get count of currently tracked players (REFACTORED).

        Simple orchestration using repository.

        :returns: Number of tracked players
        """
        # Delegate to repository and count results
        players = await self.repository.get_tracked_players()
        return len(players)

    # === Methods for Player Analyzer Job ===

    async def get_players_needing_matches(
        self, limit: int, target_matches: int
    ) -> List[PlayerORM]:
        """Get discovered players with insufficient match history (REFACTORED).

        Used by player analyzer job to find players needing more matches.

        :param limit: Maximum number of players to return
        :param target_matches: Target number of matches per player
        :returns: List of player domain models needing match data
        """
        # Delegate complex join query to repository
        players = await self.repository.get_players_needing_matches(
            target_matches, limit
        )

        logger.debug(
            "Found players needing matches",
            count=len(players),
            target_matches=target_matches,
        )

        # Log detailed info for debugging
        for player in players:
            logger.debug(
                "Player needing matches details",
                puuid=player.puuid,
                target_matches=target_matches,
                is_analyzed=player.is_analyzed,
                is_tracked=player.is_tracked,
            )

        return players

    async def get_players_ready_for_analysis(
        self, limit: int, min_matches: int = 20
    ) -> List[PlayerORM]:
        """Get unanalyzed players with sufficient match history (REFACTORED).

        Used by player analyzer job to find players ready for analysis.

        Note: Checks player_analysis table directly instead of is_analyzed flag,
        as the flag can be unreliable (set even when analysis fails).

        :param limit: Maximum number of players to return
        :param min_matches: Minimum number of matches required for analysis
        :returns: List of player domain models ready for analysis
        """
        # Delegate complex join query to repository
        players = await self.repository.get_players_ready_for_analysis(
            min_matches, limit
        )

        logger.debug(
            "Found players ready for analysis",
            count=len(players),
            min_matches=min_matches,
        )

        # Log detailed info for debugging
        for player in players:
            logger.debug(
                "Player ready for analysis details",
                puuid=player.puuid,
                min_matches=min_matches,
                is_analyzed=player.is_analyzed,
                is_tracked=player.is_tracked,
            )

        return players

    async def get_players_for_ban_check(
        self, days: int, limit: int = 10
    ) -> List[PlayerORM]:
        """Get detected smurfs that need ban status checking (REFACTORED).

        Used by player analyzer job to find previously detected smurfs
        that haven't had their ban status checked recently.

        :param days: Number of days since last ban check
        :param limit: Maximum number of players to return
        :returns: List of player domain models needing ban check
        """
        from datetime import timedelta

        # Calculate cutoff date (business logic)
        cutoff = datetime.now() - timedelta(days=days)

        # Delegate join query to repository
        players = await self.repository.get_players_for_ban_check(cutoff, limit)

        logger.debug(
            "Found players needing ban check",
            count=len(players),
            days_since_last_check=days,
        )

        return players

    async def check_ban_status(
        self,
        player: PlayerORM,
    ) -> bool:
        """Check if a player is banned by fetching summoner data (REFACTORED).

        A 404 response from the Riot API typically indicates the player is banned
        or has changed their name.

        :param player: Player domain model to check
        :returns: True if player is likely banned, False if player is active
        """
        # Use gateway to check ban status (handles 404 = banned logic)
        is_banned = await self.riot_gateway.check_ban_status(player)

        # Update timestamp if player is active (not banned)
        if not is_banned:
            player.last_ban_check = datetime.now()
            await self.repository.save(player)

        logger.debug(
            "Player ban status checked", puuid=player.puuid, is_banned=is_banned
        )
        return is_banned

    # ============================================
    # Helper Methods for Jobs
    # ============================================

    @service_error_handler("PlayerService")
    @input_validation(
        validate_non_empty=["platform"],
    )
    async def discover_players_from_match(self, match_dto: Any, platform: str) -> int:
        """Discover and create player records from match participants (REFACTORED).

        Checks if players exist in the database and creates minimal player records
        for any new players discovered in a match. These discovered players are
        marked as not tracked and not analyzed.

        :param match_dto: Match DTO from Riot API
        :param platform: Platform for the players
        :returns: Number of newly discovered players
        :raises PlayerServiceError: If match processing fails
        :raises ValidationError: If input parameters are invalid
        :raises DatabaseError: If database operations fail
        """
        from app.features.matches.transformers import PlayerDataSanitizer

        normalized_platform = platform.strip().upper()
        discovered_count = 0

        for participant in match_dto.info.participants:
            # Check if player exists in database (delegate to repository)
            existing_player = await self.repository.get_by_puuid(participant.puuid)

            if not existing_player:
                # Sanitize player data (business logic)
                player_data = {
                    "riot_id": participant.riot_id_game_name,
                    "tag_line": participant.riot_id_tagline,
                    "summoner_name": participant.summoner_name,
                }
                player_data = PlayerDataSanitizer.sanitize_player_fields(player_data)

                # Create new player record marked for analysis
                new_player = PlayerORM(
                    puuid=participant.puuid,
                    riot_id=player_data["riot_id"],
                    tag_line=player_data["tag_line"],
                    summoner_name=player_data["summoner_name"],
                    platform=normalized_platform,
                    account_level=participant.summoner_level,
                    is_tracked=False,  # Discovered, not tracked
                    is_analyzed=False,  # Needs analysis
                    is_active=True,
                )

                # Delegate creation to repository
                await self.repository.create(new_player)
                discovered_count += 1

                logger.debug(
                    "Marked new discovered player",
                    puuid=participant.puuid,
                    riot_id=(
                        f"{player_data['riot_id']}#{player_data['tag_line']}"
                        if player_data.get("riot_id") and player_data.get("tag_line")
                        else player_data.get("riot_id")
                    ),
                )

        # Log results
        if discovered_count > 0:
            logger.info(
                "Discovered players from match",
                match_id=match_dto.metadata.match_id,
                discovered_count=discovered_count,
                platform=normalized_platform,
            )
        else:
            logger.debug(
                "No new players discovered in match",
                match_id=match_dto.metadata.match_id,
                platform=normalized_platform,
            )

        return discovered_count

    @service_error_handler("PlayerService")
    async def update_player_rank(
        self,
        player: PlayerORM,
    ) -> bool:
        """Update player's current rank from Riot API (REFACTORED).

        Fetches the player's ranked league entries and stores their
        Solo/Duo rank in the PlayerRank table.

        :param player: Player domain model to update rank for
        :returns: True if rank was updated, False if no rank data found
        :raises ValueError: If player has invalid platform
        """

        logger.debug("Updating player rank", puuid=player.puuid)

        # Use gateway to fetch and transform rank data
        rank_orms = await self.riot_gateway.fetch_player_ranks(
            player.puuid, player.platform
        )

        if not rank_orms:
            logger.debug("No ranked data found for player", puuid=player.puuid)
            return False

        # Find Solo/Duo ranked entry (business logic)
        solo_rank = next(
            (r for r in rank_orms if r.queue_type == "RANKED_SOLO_5x5"), None
        )

        if not solo_rank:
            logger.debug("No Solo/Duo rank found for player", puuid=player.puuid)
            return False

        # Delegate creation to repository
        await self.repository.create_rank(solo_rank)

        logger.info(
            "Updated player rank",
            puuid=player.puuid,
            tier=solo_rank.tier,
            rank=solo_rank.rank,
            lp=solo_rank.league_points,
        )

        return True

    async def get_player_rank(
        self, puuid: str, queue_type: str = "RANKED_SOLO_5x5"
    ) -> "PlayerRankORM | None":
        """Get the most recent rank for a player (REFACTORED).

        :param puuid: Player's PUUID
        :param queue_type: Queue type (default: RANKED_SOLO_5x5)
        :returns: Most recent PlayerRankORM or None if no rank data exists
        """
        # Delegate query to repository
        return await self.repository.get_rank_by_puuid(puuid, queue_type)

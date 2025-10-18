"""Player service for handling player data operations."""

from typing import List, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from Levenshtein import distance as levenshtein_distance
import structlog

from ..models.players import Player
from ..schemas.players import PlayerResponse
from ..config import get_global_settings
from .exceptions import (
    PlayerServiceError,
)
from .decorators import service_error_handler, input_validation
from .utils import (
    validate_platform,
    validate_summoner_name,
    create_safe_riot_id,
    sanitize_string_field,
)

if TYPE_CHECKING:
    from ..riot_api.client import RiotAPIClient

logger = structlog.get_logger(__name__)


class PlayerService:
    """Service for handling player data operations."""

    def __init__(self, db: AsyncSession):
        """Initialize player service with database session only."""
        self.db = db

    @service_error_handler("PlayerService")
    @input_validation(
        validate_non_empty=["game_name", "platform"],
        custom_validators={"platform": validate_platform},
    )
    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """
        Get player by Riot ID from database only.

        This method searches only the local database for players already being tracked.
        To add new players from Riot API, use a separate add/import feature.

        Args:
            game_name: Riot ID game name of the player
            tag_line: Riot ID tag line of the player
            platform: Riot API platform code (e.g., "NA1", "EUW1")

        Returns:
            Player response object with player data

        Raises:
            PlayerServiceError: If player is not found or database error occurs
            ValidationError: If input parameters are invalid
        """
        # Sanitize inputs
        safe_game_name = sanitize_string_field(game_name)
        safe_tag_line = sanitize_string_field(tag_line)
        normalized_platform = validate_platform(platform)

        # Query database only
        result = await self.db.execute(
            select(Player).where(
                Player.riot_id == safe_game_name,
                Player.tag_line == safe_tag_line,
                Player.platform == normalized_platform,
                Player.is_active,
            )
        )
        player = result.scalar_one_or_none()

        if not player:
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
            puuid=player.puuid,
        )

        return PlayerResponse.model_validate(player)

    @service_error_handler("PlayerService")
    @input_validation(
        validate_non_empty=["summoner_name", "platform"],
        custom_validators={
            "platform": validate_platform,
            "summoner_name": validate_summoner_name,
        },
    )
    async def get_player_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> PlayerResponse:
        """
        Get player by summoner name from database only.

        This searches only the local database for players already being tracked.
        To add new players from Riot API, use a separate add/import feature.

        Args:
            summoner_name: Summoner name to search for
            platform: Riot API platform code

        Returns:
            Player response object with player data

        Raises:
            PlayerServiceError: If player is not found
            ValidationError: If input parameters are invalid
        """
        # Sanitize inputs
        safe_summoner_name = validate_summoner_name(summoner_name)
        normalized_platform = validate_platform(platform)

        # Search database for exact match or partial match
        result = await self.db.execute(
            select(Player).where(
                Player.summoner_name.ilike(f"%{safe_summoner_name}%"),
                Player.platform == normalized_platform,
                Player.is_active,
            )
        )
        players = result.scalars().all()

        # If exact match found, return it
        for player in players:
            if (
                player.summoner_name
                and player.summoner_name.lower() == safe_summoner_name.lower()
            ):
                logger.info(
                    "Found exact match for summoner name",
                    summoner_name=safe_summoner_name,
                    platform=normalized_platform,
                    puuid=player.puuid,
                )
                return PlayerResponse.model_validate(player)

        # If only one partial match, return it
        if len(players) == 1:
            logger.info(
                "Found single partial match for summoner name",
                summoner_name=safe_summoner_name,
                platform=normalized_platform,
                matched_name=players[0].summoner_name,
            )
            return PlayerResponse.model_validate(players[0])

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

        # No matches found in database
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

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Get player by PUUID from database only. Never calls Riot API."""
        # Query database only
        result = await self.db.execute(
            select(Player).where(Player.puuid == puuid, Player.is_active)
        )
        player = result.scalar_one_or_none()

        if not player:
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

        return PlayerResponse.model_validate(player)

    async def fuzzy_search_players(
        self, query: str, platform: str, limit: int = 10
    ) -> List[PlayerResponse]:
        """
        Search for players using fuzzy matching with Levenshtein distance.

        Auto-detects search type:
        - Contains '#' → Search Riot ID (game_name#tag_line)
        - Starts with '#' → Search tags only
        - Otherwise → Search both summoner_name and riot_id

        Returns up to `limit` results sorted by relevance:
        1. Exact Riot ID match (highest priority)
        2. Best summoner name matches (by Levenshtein distance)
        3. Best tag matches (by Levenshtein distance)
        4. Alphabetical as tiebreaker

        Args:
            query: Search query string
            platform: Platform region
            limit: Maximum results to return (default: 10)

        Returns:
            List of PlayerResponse sorted by relevance
        """

        # Fix #3: Add Input Validation (Major)
        # Validate and normalize input
        query = query.strip()
        if len(query) < 2:
            logger.warning("Query too short", query=query)
            return []

        valid_platforms = [
            "eun1",
            "euw1",
            "na1",
            "kr",
            "br1",
            "la1",
            "la2",
            "oc1",
            "ru",
            "tr1",
            "jp1",
            "ph2",
            "sg2",
            "th2",
            "tw2",
            "vn2",
        ]
        if platform not in valid_platforms:
            logger.error("Invalid platform", platform=platform)
            raise ValueError(f"Invalid platform: {platform}")

        # Step 1: Detect search type
        search_type = "name"
        game_name = None
        tag_line = None

        # Fix #1: Reorder Conditional Logic (Critical)
        # Check startswith("#") BEFORE "#" in query to fix tag-only search bug
        if query.startswith("#"):
            # Tag-only search: "#EUW"
            search_type = "tag"
            tag_line = query[1:].strip()
        elif "#" in query:
            # Riot ID search: "DangerousDan#EUW"
            if query.count("#") == 1:
                search_type = "riot_id"
                game_name, tag_line = query.split("#", 1)
                game_name = game_name.strip()
                tag_line = tag_line.strip()
            else:
                # Multiple # - treat as invalid, search everything
                search_type = "all"
        else:
            # Name search: "DangerousDan"
            search_type = "name"
            game_name = query.strip()

        # Fix #2: Add Validation After Conditional (Critical)
        # Validate that Riot ID search has both game_name and tag_line
        if search_type == "riot_id" and (not game_name or not tag_line):
            logger.warning(
                "Invalid Riot ID search: empty game_name or tag_line",
                query=query,
                search_type=search_type,
            )
            return []

        # Step 2: Build database query (broad match with ILIKE)
        query_lower = query.lower().strip()

        if search_type == "riot_id" and game_name and tag_line:
            # Search for exact or partial Riot ID
            stmt = select(Player).where(
                and_(
                    Player.platform == platform,
                    Player.is_active,
                    or_(
                        # Exact match
                        and_(
                            Player.riot_id.ilike(game_name),
                            Player.tag_line.ilike(tag_line),
                        ),
                        # Partial matches
                        Player.riot_id.ilike(f"%{game_name}%"),
                        Player.tag_line.ilike(f"%{tag_line}%"),
                    ),
                )
            )
        elif search_type == "tag" and tag_line:
            # Search tags only
            stmt = select(Player).where(
                and_(
                    Player.platform == platform,
                    Player.is_active,
                    Player.tag_line.ilike(f"%{tag_line}%"),
                )
            )
        else:  # name or all
            # Search summoner names and riot_id
            search_term = game_name if game_name else query_lower
            stmt = select(Player).where(
                and_(
                    Player.platform == platform,
                    Player.is_active,
                    or_(
                        Player.summoner_name.ilike(f"%{search_term}%"),
                        Player.riot_id.ilike(f"%{search_term}%"),
                    ),
                )
            )

        # Fix #4: Add Performance Limit (Major)
        # Limit candidates to prevent excessive result sets
        stmt = stmt.limit(100)

        result = await self.db.execute(stmt)
        players = result.scalars().all()

        # Step 3: Score and sort results
        scored_players = []

        for player in players:
            score = 0.0

            # Exact Riot ID match = highest priority (score: 1000)
            if search_type == "riot_id" and game_name and tag_line:
                if (
                    player.riot_id
                    and player.riot_id.lower() == game_name.lower()
                    and player.tag_line
                    and player.tag_line.lower() == tag_line.lower()
                ):
                    score = 1000.0

            # Levenshtein scoring for fuzzy matches
            if score < 1000:
                distances = []

                # Score summoner name
                if player.summoner_name and (search_type in ["name", "all"]):
                    dist = levenshtein_distance(
                        query_lower, player.summoner_name.lower()
                    )
                    distances.append(dist)

                # Score riot_id
                if player.riot_id and (search_type in ["name", "riot_id", "all"]):
                    target = (
                        (f"{player.riot_id}#{player.tag_line}").lower()
                        if player.tag_line
                        else player.riot_id.lower()
                    )
                    dist = levenshtein_distance(query_lower, target)
                    distances.append(dist)

                # Score tag_line
                if player.tag_line and (search_type in ["tag", "riot_id"]):
                    dist = levenshtein_distance(
                        tag_line.lower() if tag_line else query_lower,
                        player.tag_line.lower(),
                    )
                    distances.append(dist)

                # Best (minimum) distance
                if distances:
                    min_dist = min(distances)
                    # Convert to score: 1 / (1 + distance)
                    # Distance 0 = score 1.0, distance 10 = score 0.09
                    score = 1.0 / (1.0 + min_dist)

            # Add to scored list
            scored_players.append(
                {
                    "player": player,
                    "score": score,
                    "name": player.summoner_name or player.riot_id or "",
                }
            )

        # Step 4: Sort by score (desc), then alphabetically
        scored_players.sort(key=lambda x: (-x["score"], x["name"].lower()))

        # Step 5: Return top results
        top_players = scored_players[:limit]

        logger.info(
            "Fuzzy search completed",
            query=query,
            platform=platform,
            search_type=search_type,
            total_candidates=len(players),
            results_returned=len(top_players),
        )

        return [PlayerResponse.model_validate(p["player"]) for p in top_players]

    @service_error_handler("PlayerService")
    @input_validation(validate_non_empty=["puuid"], validate_positive=["limit"])
    async def get_recent_opponents_with_details(
        self, puuid: str, limit: int
    ) -> List[PlayerResponse]:
        """
        Get recent opponents for a player with their details from database only.
        Only returns players that exist in our database with summoner_name populated.
        Does NOT make any Riot API calls.

        Args:
            puuid: Player PUUID
            limit: Maximum number of unique opponents to return

        Returns:
            List of PlayerResponse objects for opponents found in database
        """
        from ..models.participants import MatchParticipant

        # Use a single JOIN query to get opponent player data efficiently (fixes N+1 query problem)
        # This joins MatchParticipant twice: once to find recent matches, once to find opponents
        recent_matches_subq = (
            select(MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
            .order_by(MatchParticipant.id.desc())
            .limit(limit * 5)  # Get more matches to find enough opponents
            .subquery()
        )

        players_stmt = (
            select(Player)
            .join(MatchParticipant, Player.puuid == MatchParticipant.puuid)
            .where(
                and_(
                    MatchParticipant.match_id.in_(recent_matches_subq),
                    MatchParticipant.puuid != puuid,
                    Player.is_active,
                    Player.summoner_name.isnot(None),
                    Player.summoner_name != "",
                )
            )
            .distinct()
            .limit(limit)
        )

        result = await self.db.execute(players_stmt)
        players = result.scalars().all()

        logger.debug(
            "Found recent opponents with details",
            puuid=puuid,
            opponent_count=len(players),
            limit=limit,
        )

        return [PlayerResponse.model_validate(player) for player in players]

    # === Player Tracking Methods for Automated Jobs ===

    async def add_and_track_player(
        self,
        riot_data_manager,
        game_name: str | None = None,
        tag_line: str | None = None,
        summoner_name: str | None = None,
        platform: str = "eun1",
    ) -> PlayerResponse:
        """
        Fetch player from Riot API and immediately track them.
        Combines get_player + track_player in one transaction.

        Args:
            riot_data_manager: RiotDataManager instance for Riot API calls
            game_name: Riot game name (for Riot ID search)
            tag_line: Riot tag line (for Riot ID search)
            summoner_name: Summoner name (legacy, database-only search)
            platform: Platform region (default: eun1)

        Returns:
            PlayerResponse with is_tracked=True

        Raises:
            ValueError: If player not found or tracking limit reached
        """
        settings = get_global_settings()

        # Check current tracked player count before fetching
        tracked_count = await self.count_tracked_players()
        if tracked_count >= settings.max_tracked_players:
            raise ValueError(
                f"Maximum tracked players limit reached ({settings.max_tracked_players}). "
                f"Please untrack a player before adding a new one."
            )

        # Fetch player data from Riot API (this will add to DB if not exists)
        if game_name and tag_line:
            # Use RiotDataManager to fetch from API
            player_response = await riot_data_manager.get_player_by_riot_id(
                game_name, tag_line, platform
            )

            if not player_response:
                raise ValueError(f"Player not found: {game_name}#{tag_line}")

        elif summoner_name:
            # For summoner name, try database first
            player_response = await self.get_player_by_summoner_name(
                summoner_name, platform
            )
        else:
            raise ValueError("Either game_name+tag_line or summoner_name required")

        # Check if already tracked
        if player_response.is_tracked:
            logger.info(
                "Player is already tracked",
                puuid=player_response.puuid,
                summoner_name=player_response.summoner_name,
            )
            return player_response

        # Track the player
        tracked_player = await self.track_player(player_response.puuid)

        logger.info(
            "Player added and tracked successfully",
            puuid=tracked_player.puuid,
            summoner_name=tracked_player.summoner_name,
            platform=platform,
        )

        return tracked_player

    async def track_player(self, puuid: str) -> PlayerResponse:
        """Mark a player as tracked for automated monitoring.

        Args:
            puuid: Player's PUUID to track.

        Returns:
            Updated player data.

        Raises:
            ValueError: If player not found or tracking limit reached.
        """
        settings = get_global_settings()

        # Check current tracked player count
        tracked_count = await self.count_tracked_players()
        if tracked_count >= settings.max_tracked_players:
            raise ValueError(
                f"Maximum tracked players limit reached ({settings.max_tracked_players}). "
                f"Please untrack a player before adding a new one."
            )

        # Update player to tracked status
        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .where(Player.is_active)
            .values(is_tracked=True, updated_at=datetime.now(timezone.utc))
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise ValueError(f"Player not found: {puuid}")

        await self.db.commit()

        logger.info(
            "Player marked as tracked",
            puuid=puuid,
            summoner_name=player.summoner_name,
            tracked_count=tracked_count + 1,
        )

        return PlayerResponse.model_validate(player)

    async def untrack_player(self, puuid: str) -> PlayerResponse:
        """Remove a player from tracked status.

        Args:
            puuid: Player's PUUID to untrack.

        Returns:
            Updated player data.

        Raises:
            ValueError: If player not found.
        """
        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .where(Player.is_active)
            .values(is_tracked=False, updated_at=datetime.now(timezone.utc))
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise ValueError(f"Player not found: {puuid}")

        await self.db.commit()

        logger.info(
            "Player unmarked as tracked",
            puuid=puuid,
            summoner_name=player.summoner_name,
        )

        return PlayerResponse.model_validate(player)

    async def get_tracked_players(self) -> List[PlayerResponse]:
        """Get all players currently marked for tracking.

        Returns:
            List of tracked players.
        """
        query = (
            select(Player)
            .where(Player.is_tracked)
            .where(Player.is_active)
            .order_by(Player.summoner_name)
        )

        result = await self.db.execute(query)
        players = result.scalars().all()

        return [PlayerResponse.model_validate(player) for player in players]

    async def count_tracked_players(self) -> int:
        """Get count of currently tracked players.

        Returns:
            Number of tracked players.
        """
        query = (
            select(func.count())
            .select_from(Player)
            .where(Player.is_tracked, Player.is_active)
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    # === Methods for Player Analyzer Job ===

    async def get_players_needing_matches(
        self, limit: int, target_matches: int
    ) -> List[Player]:
        """
        Get discovered players with insufficient match history.

        This is used by the player analyzer job to find players that need
        more matches fetched before they can be analyzed.

        Args:
            limit: Maximum number of players to return
            target_matches: Target number of matches per player

        Returns:
            List of Player objects needing match data
        """
        from ..models.participants import MatchParticipant

        stmt = (
            select(Player)
            .join(
                MatchParticipant, Player.puuid == MatchParticipant.puuid, isouter=True
            )
            .where(Player.is_tracked.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(func.count(MatchParticipant.match_id) < target_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players needing matches",
            count=len(players),
            target_matches=target_matches,
        )

        return players

    async def get_players_ready_for_analysis(
        self, limit: int, min_matches: int = 20
    ) -> List[Player]:
        """
        Get unanalyzed players with sufficient match history for player analysis.

        This is used by the player analyzer job to find players ready for
        player analysis.

        Args:
            limit: Maximum number of players to return
            min_matches: Minimum number of matches required for analysis

        Returns:
            List of Player objects ready for analysis
        """
        from ..models.participants import MatchParticipant

        stmt = (
            select(Player)
            .join(MatchParticipant, Player.puuid == MatchParticipant.puuid)
            .where(Player.is_tracked.is_(False))
            .where(Player.is_analyzed.is_(False))
            .where(Player.is_active.is_(True))
            .group_by(Player.puuid)
            .having(func.count(MatchParticipant.match_id) >= min_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players ready for analysis",
            count=len(players),
            min_matches=min_matches,
        )

        return players

    async def get_players_for_ban_check(
        self, days: int, limit: int = 10
    ) -> List[Player]:
        """
        Get detected smurfs that need ban status checking.

        This is used by the player analyzer job to find players that were
        previously detected as smurfs and haven't had their ban status checked
        recently.

        Args:
            days: Number of days since last ban check
            limit: Maximum number of players to return

        Returns:
            List of Player objects needing ban check
        """
        from ..models.smurf_detection import SmurfDetection
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)

        stmt = (
            select(Player)
            .join(SmurfDetection, Player.puuid == SmurfDetection.puuid)
            .where(SmurfDetection.is_smurf.is_(True))
            .where(or_(Player.last_ban_check.is_(None), Player.last_ban_check < cutoff))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "Found players needing ban check",
            count=len(players),
            days_since_last_check=days,
        )

        return players

    async def check_ban_status(
        self, player: Player, riot_api_client: "RiotAPIClient"
    ) -> bool:
        """
        Check if a player is banned by attempting to fetch their summoner data.

        A 404 response from the Riot API typically indicates the player is banned
        or has changed their name.

        Args:
            player: Player object to check
            riot_api_client: RiotAPIClient instance (from jobs)

        Returns:
            True if player is likely banned, False if player is active
        """
        from ..riot_api.constants import Platform
        from datetime import datetime

        platform = Platform(player.platform.lower())

        # Attempt to fetch summoner data
        await riot_api_client.get_summoner_by_puuid(player.puuid, platform)

        # Player found = not banned
        player.last_ban_check = datetime.now()
        await self.db.commit()

        logger.debug("Player is active (not banned)", puuid=player.puuid)
        return False

    # ============================================
    # Helper Methods for Jobs
    # ============================================

    @service_error_handler("PlayerService")
    @input_validation(
        validate_non_empty=["platform"],
        custom_validators={"platform": validate_platform},
    )
    async def discover_players_from_match(self, match_dto: Any, platform: str) -> int:
        """
        Discover and create player records from match participants.

        This method checks if players exist in the database and creates
        minimal player records for any new players discovered in a match.
        These discovered players are marked as not tracked and not analyzed.

        The method handles its own transaction boundaries to ensure
        data consistency without requiring external transaction management.

        Args:
            match_dto: Match DTO from Riot API
            platform: Platform for the players

        Returns:
            Number of newly discovered players

        Raises:
            PlayerServiceError: If match processing fails
            ValidationError: If input parameters are invalid
            DatabaseError: If database operations fail
        """
        from ..schemas.transformers import PlayerDataSanitizer

        normalized_platform = validate_platform(platform)
        discovered_count = 0

        for participant in match_dto.info.participants:
            # Check if player exists in database
            result = await self.db.execute(
                select(Player).where(Player.puuid == participant.puuid)
            )
            existing_player = result.scalar_one_or_none()

            if not existing_player:
                # Sanitize player data
                player_data = {
                    "riot_id": participant.riot_id_game_name,
                    "tag_line": participant.riot_id_tagline,
                    "summoner_name": participant.summoner_name,
                }
                player_data = PlayerDataSanitizer.sanitize_player_fields(player_data)

                # Create new player record marked for analysis
                new_player = Player(
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
                self.db.add(new_player)
                discovered_count += 1

                logger.debug(
                    "Marked new discovered player",
                    puuid=participant.puuid,
                    riot_id=create_safe_riot_id(
                        player_data["riot_id"], player_data["tag_line"]
                    ),
                )

        # Commit transaction for all discovered players
        if discovered_count > 0:
            await self.db.commit()
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
        self, player: Player, riot_api_client: "RiotAPIClient"
    ) -> bool:
        """Update player's current rank from Riot API.

        Fetches the player's ranked league entries and stores their
        Solo/Duo rank in the PlayerRank table.

        Args:
            player: Player to update rank for
            riot_api_client: RiotAPIClient instance (from jobs)

        Returns:
            True if rank was updated, False if no rank data found or error occurred

        Raises:
            ValueError: If player has invalid platform
        """
        from ..riot_api.constants import Platform
        from ..models.ranks import PlayerRank

        logger.debug("Updating player rank", puuid=player.puuid)

        # Convert platform string to Platform enum
        platform_enum = Platform(player.platform.lower())

        # Fetch rank data from Riot API using PUUID-based endpoint
        league_entries = await riot_api_client.get_league_entries_by_puuid(
            player.puuid, platform_enum
        )

        if not league_entries:
            logger.debug("No ranked data found for player", puuid=player.puuid)
            return False

        # Find Solo/Duo ranked entry
        solo_entry = next(
            (e for e in league_entries if e.queue_type == "RANKED_SOLO_5x5"), None
        )

        if not solo_entry:
            logger.debug("No Solo/Duo rank found for player", puuid=player.puuid)
            return False

        # Create rank record
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

        self.db.add(rank_record)

        logger.info(
            "Updated player rank",
            puuid=player.puuid,
            tier=solo_entry.tier,
            rank=solo_entry.rank,
            lp=solo_entry.league_points,
        )

        return True

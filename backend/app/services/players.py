"""Player service for handling player data operations."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError, NotFoundError
from ..models.players import Player
from ..schemas.players import PlayerResponse, PlayerUpdate
from ..config import get_global_settings
import structlog

logger = structlog.get_logger(__name__)


class PlayerService:
    """Service for handling player data operations."""

    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        """Initialize player service with database and data manager."""
        self.db = db
        self.data_manager = riot_data_manager

    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """Get player by Riot ID (name#tag) using intelligent data management."""
        try:
            # Validate platform
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
                raise ValueError(
                    f"Invalid platform: {platform}. Must be one of: {', '.join(valid_platforms)}"
                )

            # Use RiotDataManager for intelligent data fetching
            player_response = await self.data_manager.get_player_by_riot_id(
                game_name, tag_line, platform
            )

            if not player_response:
                raise ValueError(f"Player not found: {game_name}#{tag_line}")

            logger.info(
                "Player data retrieved successfully",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": platform,
                },
            )

            return player_response

        except RateLimitError as e:
            logger.warning(
                "Rate limit hit while fetching player",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "retry_after": e.retry_after,
                },
            )
            raise

        except NotFoundError:
            # Player not found in Riot API - convert to ValueError for API layer
            raise ValueError(f"Player not found: {game_name}#{tag_line}")

        except ValueError:
            # Re-raise validation errors
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch player data",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": platform,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise Exception(f"Failed to fetch player data: {str(e)}")

    async def get_player_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> PlayerResponse:
        """
        Get player by summoner name from database only.

        This searches only the local database for players already being tracked.
        To add new players from Riot API, use a separate add/import feature.
        """
        # Search database for exact match or partial match
        result = await self.db.execute(
            select(Player).where(
                Player.summoner_name.ilike(f"%{summoner_name}%"),
                Player.platform == platform,
                Player.is_active,
            )
        )
        players = result.scalars().all()

        # If exact match found, return it
        for player in players:
            if (
                player.summoner_name
                and player.summoner_name.lower() == summoner_name.lower()
            ):
                logger.info(
                    "Found exact match for summoner name",
                    summoner_name=summoner_name,
                    platform=platform,
                )
                return PlayerResponse.model_validate(player)

        # If only one partial match, return it
        if len(players) == 1:
            logger.info(
                "Found single partial match for summoner name",
                summoner_name=summoner_name,
                platform=platform,
                matched_name=players[0].summoner_name,
            )
            return PlayerResponse.model_validate(players[0])

        # If multiple partial matches, return error with suggestions
        if len(players) > 1:
            matched_names = [p.summoner_name for p in players if p.summoner_name]
            logger.info(
                "Found multiple matches for summoner name",
                summoner_name=summoner_name,
                platform=platform,
                matches=matched_names,
            )
            raise ValueError(
                f"Multiple players found matching '{summoner_name}': {', '.join(matched_names)}. "
                "Please be more specific."
            )

        # No matches found in database
        logger.info(
            "No player found in database for summoner name",
            summoner_name=summoner_name,
            platform=platform,
        )
        raise ValueError(f"Player not found: {summoner_name}")

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Get player by PUUID using intelligent data management."""
        try:
            player_response = await self.data_manager.get_player_by_puuid(
                puuid, platform
            )

            if not player_response:
                raise ValueError(f"Player not found: {puuid}")

            logger.info(
                "Player data retrieved by PUUID successfully",
                puuid=puuid,
                platform=platform,
            )

            return player_response

        except RateLimitError as e:
            logger.warning(
                "Rate limit hit while fetching player by PUUID",
                puuid=puuid,
                retry_after=e.retry_after,
            )
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch player data by PUUID",
                puuid=puuid,
                platform=platform,
                error=str(e),
            )
            raise Exception(f"Failed to fetch player data: {str(e)}")

    async def get_recent_opponents(self, puuid: str, limit: int) -> List[str]:
        """
        Get recent opponents for a player by querying match participants.

        Args:
            puuid: Player PUUID
            limit: Maximum number of unique opponents to return

        Returns:
            List of opponent PUUIDs
        """
        try:
            # Query for recent matches where this player participated
            from ..models.participants import MatchParticipant

            # Subquery to get recent match IDs for this player
            player_matches_stmt = (
                select(MatchParticipant.match_id)
                .where(MatchParticipant.puuid == puuid)
                .order_by(MatchParticipant.id.desc())
                .limit(
                    limit * 5
                )  # Get more matches to ensure we find enough unique opponents
            )
            player_match_ids = (
                (await self.db.execute(player_matches_stmt)).scalars().all()
            )

            if not player_match_ids:
                logger.debug("No matches found for player", puuid=puuid)
                return []

            # Query for all participants in those matches, excluding the player themselves
            opponents_stmt = (
                select(MatchParticipant.puuid)
                .where(
                    and_(
                        MatchParticipant.match_id.in_(player_match_ids),
                        MatchParticipant.puuid != puuid,
                    )
                )
                .distinct()
                .limit(limit)
            )

            result = await self.db.execute(opponents_stmt)
            opponent_puuids = result.scalars().all()

            logger.debug(
                "Found recent opponents",
                puuid=puuid,
                opponent_count=len(opponent_puuids),
                limit=limit,
            )

            return list(opponent_puuids)

        except Exception as e:
            logger.error("Failed to get recent opponents", puuid=puuid, error=str(e))
            # Return empty list instead of raising to not break the UI
            return []

    async def _update_player(
        self, puuid: UUID, update_data: PlayerUpdate
    ) -> Optional[Player]:
        """Update existing player record."""
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return None

        update_dict["updated_at"] = datetime.now(timezone.utc)
        if "last_seen" not in update_dict:
            update_dict["last_seen"] = datetime.now(timezone.utc)

        stmt = (
            update(Player)
            .where(Player.puuid == puuid)
            .values(**update_dict)
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def bulk_get_players(self, puuids: List[str]) -> List[PlayerResponse]:
        """Get multiple players by PUUIDs."""
        if not puuids:
            return []

        result = await self.db.execute(
            select(Player).where(Player.puuid.in_(puuids), Player.is_active)
        )
        players = result.scalars().all()
        return [PlayerResponse.model_validate(player) for player in players]

    async def search_players(
        self,
        summoner_name: Optional[str] = None,
        riot_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlayerResponse]:
        """Search players by various criteria."""
        query = select(Player).where(Player.is_active)

        if summoner_name:
            query = query.where(Player.summoner_name.ilike(f"%{summoner_name}%"))

        if riot_id:
            if "#" in riot_id:
                game_name, tag_line = riot_id.split("#", 1)
                query = query.where(
                    Player.riot_id.ilike(f"%{game_name}%"),
                    Player.tag_line.ilike(f"%{tag_line}%"),
                )
            else:
                query = query.where(Player.riot_id.ilike(f"%{riot_id}%"))

        if platform:
            query = query.where(Player.platform == platform)

        query = query.limit(limit)

        result = await self.db.execute(query)
        players = result.scalars().all()
        return [PlayerResponse.model_validate(player) for player in players]

    # === Player Tracking Methods for Automated Jobs ===

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

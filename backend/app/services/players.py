"""Player service for handling player data operations."""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..riot_api.data_manager import RiotDataManager
from ..riot_api.errors import RateLimitError
from ..models.players import Player
from ..schemas.players import PlayerResponse, PlayerCreate, PlayerUpdate
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
            if player.summoner_name.lower() == summoner_name.lower():
                logger.info(
                    "Found exact match for summoner name",
                    summoner_name=summoner_name,
                    platform=platform,
                )
                return PlayerResponse.from_orm(player)

        # If only one partial match, return it
        if len(players) == 1:
            logger.info(
                "Found single partial match for summoner name",
                summoner_name=summoner_name,
                platform=platform,
                matched_name=players[0].summoner_name,
            )
            return PlayerResponse.from_orm(players[0])

        # If multiple partial matches, return error with suggestions
        if len(players) > 1:
            matched_names = [p.summoner_name for p in players]
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
        """Get recent opponents for a player."""
        # This would query match_participants table
        # For now, return empty list - will be implemented in Task 8
        return []

    async def _get_player_from_db(
        self, riot_id: str = None, puuid: str = None
    ) -> Optional[Player]:
        """Get player from database by Riot ID or PUUID."""
        query = select(Player).where(Player.is_active)

        if riot_id:
            query = query.where(Player.riot_id == riot_id)
        elif puuid:
            query = query.where(Player.puuid == puuid)
        else:
            return None

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _create_or_update_player(self, player_data: PlayerCreate) -> Player:
        """Create new player record or update existing one."""
        # Use PostgreSQL UPSERT functionality
        stmt = (
            insert(Player)
            .values(
                puuid=player_data.puuid,
                riot_id=player_data.riot_id,
                tag_line=player_data.tag_line,
                summoner_name=player_data.summoner_name,
                platform=player_data.platform,
                account_level=player_data.account_level,
                profile_icon_id=player_data.profile_icon_id,
                summoner_id=player_data.summoner_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["puuid"],
                set_=dict(
                    riot_id=player_data.riot_id,
                    tag_line=player_data.tag_line,
                    summoner_name=player_data.summoner_name,
                    platform=player_data.platform,
                    account_level=player_data.account_level,
                    profile_icon_id=player_data.profile_icon_id,
                    summoner_id=player_data.summoner_id,
                    updated_at=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                ),
            )
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    async def _update_player(
        self, puuid: UUID, update_data: PlayerUpdate
    ) -> Optional[Player]:
        """Update existing player record."""
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            return None

        update_dict["updated_at"] = datetime.utcnow()
        if "last_seen" not in update_dict:
            update_dict["last_seen"] = datetime.utcnow()

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
        return [PlayerResponse.from_orm(player) for player in players]

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
        return [PlayerResponse.from_orm(player) for player in players]

"""
Player service for handling player data operations.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..riot_api.client import RiotAPIClient
from ..models.players import Player
from ..schemas.players import PlayerResponse, PlayerCreate, PlayerUpdate
import structlog

logger = structlog.get_logger(__name__)


class PlayerService:
    """Service for handling player data operations."""

    def __init__(self, db: AsyncSession, riot_client: RiotAPIClient):
        self.db = db
        self.riot_client = riot_client

    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """Get player by Riot ID (name#tag)."""
        # First try to get from database
        riot_id = f"{game_name}#{tag_line}"
        player = await self._get_player_from_db(riot_id=riot_id)

        if not player:
            # Fetch from Riot API
            try:
                account = await self.riot_client.get_account_by_riot_id(game_name, tag_line)
                summoner = await self.riot_client.get_summoner_by_puuid(account.puuid)

                # Create player record
                player_data = PlayerCreate(
                    puuid=account.puuid,
                    riot_id=game_name,
                    tag_line=tag_line,
                    summoner_name=summoner.name,
                    platform=platform,
                    account_level=summoner.summoner_level,
                    profile_icon_id=summoner.profile_icon_id,
                    summoner_id=summoner.id
                )

                player = await self._create_or_update_player(player_data)

            except Exception as e:
                logger.error("Failed to fetch player data from Riot API",
                           game_name=game_name, tag_line=tag_line, error=str(e))
                raise Exception(f"Failed to fetch player data: {str(e)}")

        return PlayerResponse.from_orm(player)

    async def get_player_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> PlayerResponse:
        """Get player by summoner name."""
        # Try database first - look for exact match or partial match
        result = await self.db.execute(
            select(Player).where(
                Player.summoner_name.ilike(f"%{summoner_name}%"),
                Player.platform == platform,
                Player.is_active == True
            )
        )
        players = result.scalars().all()

        # If exact match found, return it
        for player in players:
            if player.summoner_name.lower() == summoner_name.lower():
                return PlayerResponse.from_orm(player)

        # If only one partial match, return it
        if len(players) == 1:
            return PlayerResponse.from_orm(players[0])

        # If multiple matches or no matches, fetch from Riot API
        try:
            summoner = await self.riot_client.get_summoner_by_name(summoner_name, platform)

            # Check if we already have this player by PUUID
            existing_player = await self._get_player_from_db(puuid=summoner.puuid)
            if existing_player:
                # Update the summoner name if it changed
                if existing_player.summoner_name != summoner.name:
                    await self._update_player(existing_player.puuid, PlayerUpdate(
                        summoner_name=summoner.name,
                        account_level=summoner.summoner_level,
                        profile_icon_id=summoner.profile_icon_id,
                        summoner_id=summoner.id
                    ))
                    existing_player.summoner_name = summoner.name
                    existing_player.account_level = summoner.summoner_level
                    existing_player.profile_icon_id = summoner.profile_icon_id
                    existing_player.summoner_id = summoner.id

                return PlayerResponse.from_orm(existing_player)

            # Create new player record
            player_data = PlayerCreate(
                puuid=summoner.puuid,
                summoner_name=summoner.name,
                platform=platform,
                account_level=summoner.summoner_level,
                profile_icon_id=summoner.profile_icon_id,
                summoner_id=summoner.id
            )

            player = await self._create_or_update_player(player_data)
            return PlayerResponse.from_orm(player)

        except Exception as e:
            logger.error("Failed to fetch player by summoner name",
                       summoner_name=summoner_name, platform=platform, error=str(e))
            if players:
                # Return the first partial match if API call fails
                return PlayerResponse.from_orm(players[0])
            raise Exception(f"Player not found: {str(e)}")

    async def get_player_by_puuid(self, puuid: str) -> Optional[PlayerResponse]:
        """Get player by PUUID."""
        result = await self.db.execute(
            select(Player).where(
                Player.puuid == puuid,
                Player.is_active == True
            )
        )
        player = result.scalar_one_or_none()

        if player:
            return PlayerResponse.from_orm(player)
        return None

    async def get_recent_opponents(self, puuid: str, limit: int) -> List[str]:
        """Get recent opponents for a player."""
        # This would query match_participants table
        # For now, return empty list - will be implemented in Task 8
        return []

    async def _get_player_from_db(self, riot_id: str = None, puuid: str = None) -> Optional[Player]:
        """Get player from database by Riot ID or PUUID."""
        query = select(Player).where(Player.is_active == True)

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
        stmt = insert(Player).values(
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
            last_seen=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['puuid'],
            set_=dict(
                riot_id=player_data.riot_id,
                tag_line=player_data.tag_line,
                summoner_name=player_data.summoner_name,
                platform=player_data.platform,
                account_level=player_data.account_level,
                profile_icon_id=player_data.profile_icon_id,
                summoner_id=player_data.summoner_id,
                updated_at=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
        ).returning(Player)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    async def _update_player(self, puuid: UUID, update_data: PlayerUpdate) -> Optional[Player]:
        """Update existing player record."""
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            return None

        update_dict['updated_at'] = datetime.utcnow()
        if 'last_seen' not in update_dict:
            update_dict['last_seen'] = datetime.utcnow()

        stmt = update(Player).where(
            Player.puuid == puuid
        ).values(**update_dict).returning(Player)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def bulk_get_players(self, puuids: List[str]) -> List[PlayerResponse]:
        """Get multiple players by PUUIDs."""
        if not puuids:
            return []

        result = await self.db.execute(
            select(Player).where(
                Player.puuid.in_(puuids),
                Player.is_active == True
            )
        )
        players = result.scalars().all()
        return [PlayerResponse.from_orm(player) for player in players]

    async def search_players(
        self,
        summoner_name: Optional[str] = None,
        riot_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 20
    ) -> List[PlayerResponse]:
        """Search players by various criteria."""
        query = select(Player).where(Player.is_active == True)

        if summoner_name:
            query = query.where(Player.summoner_name.ilike(f"%{summoner_name}%"))

        if riot_id:
            if "#" in riot_id:
                game_name, tag_line = riot_id.split("#", 1)
                query = query.where(
                    Player.riot_id.ilike(f"%{game_name}%"),
                    Player.tag_line.ilike(f"%{tag_line}%")
                )
            else:
                query = query.where(Player.riot_id.ilike(f"%{riot_id}%"))

        if platform:
            query = query.where(Player.platform == platform)

        query = query.limit(limit)

        result = await self.db.execute(query)
        players = result.scalars().all()
        return [PlayerResponse.from_orm(player) for player in players]
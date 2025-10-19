"""
RiotDataManager: Simplified database-first data management.

Simple flow:
1. Check PostgreSQL database
2. If found, return from database
3. If not found, fetch from Riot API (rate-limited)
4. Store in database
5. Return data

No TTL caching, no freshness tracking, no queue management.
"""

import structlog
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .client import RiotAPIClient
from .errors import RateLimitError, RiotAPIError
from .models import MatchDTO
from .constants import Platform, Region
from ..models.players import Player
from ..models.matches import Match
from ..schemas.players import PlayerResponse, PlayerCreate

logger = structlog.get_logger(__name__)


class RiotDataManager:
    """
    Simplified Riot API data manager with database-first approach.

    Flow: Database → Riot API (if miss) → Store in DB → Return
    """

    def __init__(self, db: AsyncSession, api_client: RiotAPIClient):
        """Initialize data manager with database session and API client."""
        self.db = db
        self.api_client = api_client

    # ===================
    # Player Data Methods
    # ===================

    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> Optional[PlayerResponse]:
        """
        Get player data by Riot ID (database-first).

        Args:
            game_name: Riot game name
            tag_line: Riot tag line
            platform: Platform region (e.g., "eun1")

        Returns:
            PlayerResponse if found/fetched, None if rate limited
        """
        riot_id = f"{game_name}#{tag_line}"

        try:
            # 1. Check database first
            result = await self.db.execute(
                select(Player).where(
                    Player.riot_id == game_name,
                    Player.tag_line == tag_line,
                    Player.platform == platform,
                    Player.is_active,
                )
            )
            player = result.scalar_one_or_none()

            if player:
                logger.debug(
                    "Player found in database",
                    riot_id=riot_id,
                    platform=platform,
                    puuid=player.puuid,
                )
                return PlayerResponse.model_validate(player)

            # 2. Not in database, fetch from Riot API
            logger.info(
                "Player not in database, fetching from Riot API",
                riot_id=riot_id,
                platform=platform,
            )

            # Convert platform string to enum
            platform_enum = Platform(platform.lower())

            # Fetch account (Riot ID → PUUID)
            account = await self.api_client.get_account_by_riot_id(game_name, tag_line)

            # Fetch summoner data (PUUID → summoner details)
            summoner = await self.api_client.get_summoner_by_puuid(
                account.puuid, platform_enum
            )

            # 3. Store in database
            player_data = PlayerCreate(
                puuid=account.puuid,
                riot_id=game_name,
                tag_line=tag_line,
                summoner_name=game_name,  # Use game_name as fallback
                platform=platform,
                account_level=summoner.summoner_level,
                profile_icon_id=summoner.profile_icon_id,
                summoner_id=summoner.id,
            )

            player = await self._upsert_player(player_data)

            logger.info(
                "Player fetched and stored",
                riot_id=riot_id,
                platform=platform,
                puuid=player.puuid,
            )

            return PlayerResponse.model_validate(player)

        except RateLimitError as e:
            logger.warning(
                "Rate limited when fetching player",
                riot_id=riot_id,
                platform=platform,
                retry_after=e.retry_after,
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get player by Riot ID",
                riot_id=riot_id,
                platform=platform,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> Optional[PlayerResponse]:
        """
        Get player data by PUUID (database-first).

        Args:
            puuid: Player PUUID
            platform: Platform region

        Returns:
            PlayerResponse if found/fetched, None if rate limited
        """
        try:
            # 1. Check database first
            result = await self.db.execute(
                select(Player).where(Player.puuid == puuid, Player.is_active)
            )
            player = result.scalar_one_or_none()

            if player:
                logger.debug("Player found in database", puuid=puuid)
                return PlayerResponse.model_validate(player)

            # 2. Not in database, fetch from Riot API
            logger.info("Player not in database, fetching from Riot API", puuid=puuid)

            platform_enum = Platform(platform.lower())

            # Fetch summoner data
            summoner = await self.api_client.get_summoner_by_puuid(puuid, platform_enum)

            # 3. Store in database
            # Ensure summoner_name is never null or empty
            summoner_name = summoner.name
            if not summoner_name or summoner_name.strip() == "":
                summoner_name = "Unknown Player"  # Fallback for missing summoner name

            player_data = PlayerCreate(
                puuid=puuid,
                riot_id=None,  # Not available when fetching by PUUID
                tag_line=None,  # Not available when fetching by PUUID
                summoner_name=summoner_name,
                platform=platform,
                account_level=summoner.summoner_level,
                profile_icon_id=summoner.profile_icon_id,
                summoner_id=summoner.id,
            )

            player = await self._upsert_player(player_data)

            logger.info("Player fetched and stored", puuid=puuid)

            return PlayerResponse.model_validate(player)

        except RateLimitError as e:
            logger.warning(
                "Rate limited when fetching player",
                puuid=puuid,
                retry_after=e.retry_after,
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get player by PUUID",
                puuid=puuid,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _upsert_player(self, player_data: PlayerCreate) -> Player:
        """
        Create or update player in database.

        Uses PostgreSQL UPSERT to handle duplicates.
        """
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
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                is_active=True,
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
                    updated_at=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                ),
            )
            .returning(Player)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    # ==================
    # Match Data Methods
    # ==================

    async def get_match(
        self, match_id: str, region: str = "europe"
    ) -> Optional[MatchDTO]:
        """
        Get match data (database-first).

        Note: Match data is immutable once the game ends.

        Args:
            match_id: Match ID (e.g., "EUN1_3087654321")
            region: Regional endpoint

        Returns:
            MatchDTO if found/fetched, None if rate limited
        """
        try:
            # 1. Check database first
            result = await self.db.execute(
                select(Match).where(Match.match_id == match_id)
            )
            match = result.scalar_one_or_none()

            if match:
                logger.debug("Match found in database", match_id=match_id)
                # Would need to convert Match model to MatchDTO
                # For now, fetch from API to get complete data
                pass

            # 2. Fetch from Riot API
            logger.info("Fetching match from Riot API", match_id=match_id)

            region_enum = Region(region.lower())
            match_dto = await self.api_client.get_match(match_id, region_enum)

            # 3. Store in database (implementation would store match details)
            # This would require proper match storage logic
            logger.info("Match fetched", match_id=match_id)

            return match_dto

        except RiotAPIError as e:
            # Handle rate limits (429) and not found (404) differently
            if e.status_code == 429:
                logger.warning(
                    "Rate limited when fetching match",
                    match_id=match_id,
                    retry_after=e.retry_after,
                )
                return None
            elif e.status_code == 404:
                logger.info("Match not found", match_id=match_id)
                return None
            else:
                # Re-raise other errors
                raise

        except Exception as e:
            logger.error(
                "Failed to get match", match_id=match_id, error=str(e), exc_info=True
            )
            raise

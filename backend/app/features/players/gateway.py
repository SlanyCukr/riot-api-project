"""
Riot API Gateway - Anti-Corruption Layer for Players Feature.

This gateway translates Riot API semantics and data structures to our domain language,
isolating the players feature from external API details following the Anti-Corruption
Layer pattern from the enterprise patterns guide.

Transforms:
- Riot API DTOs (camelCase, Riot-specific naming) → PlayerORM (snake_case, our naming)
- Multiple API calls → Single domain operation
- Error-prone manual transforms → Centralized, tested transformation

See docs/plans/enterprise-patterns-guide.md for pattern details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import structlog

from .orm_models import PlayerORM, PlayerRankORM

if TYPE_CHECKING:
    from app.core.riot_api.client import RiotAPIClient

logger = structlog.get_logger(__name__)


class RiotAPIGateway:
    """
    Anti-Corruption Layer for Riot API integration.

    Hides external API structure and transforms data to our domain model.
    This prevents Riot API semantics from leaking into our domain layer.
    """

    def __init__(self, riot_api_client: "RiotAPIClient"):
        """
        Initialize gateway with Riot API client.

        :param riot_api_client: Low-level Riot API client
        """
        self._client = riot_api_client

    async def fetch_player_profile(
        self,
        game_name: str,
        tag_line: str,
        platform: str,
    ) -> PlayerORM:
        """
        Fetch player profile from Riot API and transform to our domain model.

        This method:
        1. Makes multiple Riot API calls (account, summoner)
        2. Transforms Riot's camelCase → our snake_case
        3. Returns a PlayerORM domain model
        4. Handles all Riot-specific naming and structure

        Args:
            game_name: Player's game name (Riot ID part 1)
            tag_line: Player's tag line (Riot ID part 2)
            platform: Platform code (e.g., "eun1")

        Returns:
            PlayerORM domain model with all fetched data

        Raises:
            PlayerNotFoundError: If player doesn't exist
            RiotAPIError: If API call fails (except rate limit)
        """
        from app.core.enums import Platform
        from app.core.riot_api.errors import RateLimitError
        from app.core.exceptions import PlayerServiceError

        # Step 1: Fetch account from Riot API (handles rate limiting internally)
        logger.debug(
            "Fetching player from Riot API",
            game_name=game_name,
            tag_line=tag_line,
            platform=platform,
        )

        try:
            # Get account info (gameName, tagLine in camelCase from Riot)
            account_dto = await self._client.get_account(game_name, tag_line)
        except RateLimitError:
            logger.warning(
                "Rate limited while fetching account",
                game_name=game_name,
                tag_line=tag_line,
                platform=platform,
            )
            raise PlayerServiceError(
                message="Riot API rate limit exceeded. Please try again later.",
                operation="fetch_player_profile",
                context={"game_name": game_name, "tag_line": tag_line},
            )

        # Step 2: Fetch summoner data (summonerLevel, name in camelCase from Riot)
        platform_enum = Platform(platform.lower())
        summoner_dto = await self._client.get_summoner_by_puuid(
            account_dto.puuid, platform_enum
        )

        # Step 3: Transform to OUR domain model (snake_case, our naming)
        # This is where we translate:
        # - gameName (Riot) → riot_id (our domain)
        # - tagLine (Riot) → tag_line (our domain)
        # - summonerLevel (Riot) → account_level (our domain)
        # - name (Riot) → summoner_name (our domain)
        player_orm = PlayerORM(
            puuid=account_dto.puuid,  # Same in both (UUID format)
            riot_id=game_name,  # OUR naming (not gameName)
            tag_line=tag_line,  # OUR naming (not tagLine)
            platform=platform,  # OUR concept (Riot doesn't have this concept)
            summoner_name=summoner_dto.name,  # Translated from camelCase
            account_level=summoner_dto.summonerLevel,  # Translated from camelCase
            # Default values for new players
            is_tracked=False,
            is_analyzed=False,
            is_active=True,
        )

        logger.info(
            "Player profile fetched and transformed",
            puuid=player_orm.puuid,
            riot_id=player_orm.riot_id,
            tag_line=player_orm.tag_line,
            summoner_name=player_orm.summoner_name,
            platform=platform,
        )

        return player_orm

    async def fetch_player_ranks(
        self,
        puuid: str,
        platform: str,
    ) -> list[PlayerRankORM]:
        """
        Fetch player ranked data from Riot API and transform to our domain model.

        Args:
            puuid: Player's unique identifier
            platform: Platform code (e.g., "eun1")

        Returns:
            List of PlayerRankORM domain models

        Raises:
            RiotAPIError: If API call fails
        """
        from app.core.enums import Platform

        logger.debug(
            "Fetching player ranks from Riot API", puuid=puuid, platform=platform
        )

        platform_enum = Platform(platform.lower())

        # Fetch ranked entries from Riot API
        league_entries = await self._client.get_league_entries_by_puuid(
            puuid, platform_enum
        )

        if not league_entries:
            logger.debug("No ranked data found for player", puuid=puuid)
            return []

        # Transform to our domain models
        rank_orms = []
        for entry in league_entries:
            # Translate Riot DTO to our domain model
            rank_orm = PlayerRankORM(
                puuid=puuid,
                queue_type=entry.queue_type,  # Same format
                tier=entry.tier,  # Same format
                rank=entry.rank,  # Same format
                league_points=entry.league_points,  # Same
                wins=entry.wins,  # Same
                losses=entry.losses,  # Same
                veteran=entry.veteran,  # Same
                inactive=entry.inactive,  # Same
                fresh_blood=entry.fresh_blood,  # Same
                hot_streak=entry.hot_streak,  # Same
                league_id=getattr(entry, "league_id", None),  # Handle optional field
                is_current=True,
            )
            rank_orms.append(rank_orm)

        logger.debug(
            "Player ranks fetched and transformed",
            puuid=puuid,
            rank_count=len(rank_orms),
        )

        return rank_orms

    async def check_ban_status(
        self,
        player: PlayerORM,
    ) -> bool:
        """
        Check if a player is banned by attempting to fetch their data.

        Args:
            player: PlayerORM domain model to check

        Returns:
            True if player is likely banned, False if player is active

        Raises:
            RiotAPIError: If API call fails (banned players return 404)
        """
        from app.core.enums import Platform
        from app.core.riot_api.errors import RiotAPIError

        platform_enum = Platform(player.platform.lower())

        try:
            # Attempt to fetch summoner data
            await self._client.get_summoner_by_puuid(player.puuid, platform_enum)
            # Player found = not banned
            logger.debug("Player is active (not banned)", puuid=player.puuid)
            return False
        except RiotAPIError as e:
            if e.status_code == 404:
                # 404 typically means banned or name changed
                logger.info("Player is likely banned", puuid=player.puuid)
                return True
            # Other errors - re-raise
            raise

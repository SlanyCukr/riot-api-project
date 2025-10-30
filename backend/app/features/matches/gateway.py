"""Anti-Corruption Layer (Gateway) for Riot Match API.

This module provides isolation between Riot API and our domain model,
following Martin Fowler's Anti-Corruption Layer pattern to protect
our domain from external system semantics.
"""

from typing import TYPE_CHECKING

import structlog

from .orm_models import MatchORM
from .participants_orm import MatchParticipantORM

if TYPE_CHECKING:
    from app.core.riot_api.client import RiotAPIClient
    from app.core.riot_api.schemas import MatchDTO

logger = structlog.get_logger(__name__)


class RiotMatchGateway:
    """Gateway to Riot Match API - Anti-Corruption Layer.

    Translates Riot API semantics (camelCase, Riot-specific structures)
    to our domain language (snake_case, domain models).

    Responsibilities:
    - Hide Riot API complexity from domain
    - Transform Riot DTOs to domain models
    - Coordinate multiple Riot API calls if needed
    - Handle Riot-specific error cases
    """

    def __init__(self, riot_client: "RiotAPIClient"):
        """Initialize gateway with Riot API client.

        Args:
            riot_client: Riot API client instance
        """
        self.riot_client = riot_client

    async def fetch_match_details(self, match_id: str) -> MatchORM:
        """Fetch match details from Riot API and convert to domain model.

        This method hides Riot API complexity:
        - Calls Riot API
        - Transforms camelCase to snake_case
        - Creates domain objects (MatchORM, MatchParticipantORM)

        Args:
            match_id: Riot match identifier

        Returns:
            MatchORM domain object with participants

        Raises:
            RiotAPIError: If API call fails
        """
        # Call Riot API (external system)
        match_dto = await self.riot_client.get_match(match_id)

        if not match_dto:
            logger.warning("match_not_found_in_riot_api", match_id=match_id)
            raise ValueError(f"Match not found: {match_id}")

        # Transform to domain model
        match_orm = self._transform_match_dto(match_dto)

        logger.debug(
            "match_fetched_from_riot_api",
            match_id=match_id,
            participants=len(match_orm.participants),
        )

        return match_orm

    async def fetch_player_match_history(
        self,
        puuid: str,
        count: int = 20,
        queue: int = 420,
    ) -> list[str]:
        """Fetch player's match history from Riot API.

        Args:
            puuid: Player PUUID
            count: Number of matches to fetch
            queue: Queue ID filter

        Returns:
            List of match IDs

        Raises:
            RiotAPIError: If API call fails
        """
        match_list = await self.riot_client.get_match_list_by_puuid(
            puuid=puuid,
            start=0,
            count=count,
            queue=queue,
        )

        match_ids = (
            list(match_list.match_ids) if match_list and match_list.match_ids else []
        )

        logger.debug(
            "match_history_fetched",
            puuid=puuid,
            count=len(match_ids),
            queue=queue,
        )

        return match_ids

    def _transform_match_dto(self, match_dto: "MatchDTO") -> MatchORM:
        """Transform Riot MatchDTO to domain MatchORM.

        Internal method that converts from Riot API semantics
        to our domain language.

        Args:
            match_dto: Riot API match data

        Returns:
            MatchORM domain object with participants
        """
        # Extract match-level data (translate Riot semantics to domain)
        match_orm = MatchORM(
            match_id=match_dto.metadata.match_id,
            platform_id=match_dto.info.platform_id or "EUN1",
            game_creation=match_dto.info.game_creation,
            game_duration=match_dto.info.game_duration,
            queue_id=match_dto.info.queue_id,
            game_version=match_dto.info.game_version,
            map_id=match_dto.info.map_id,
            game_mode=match_dto.info.game_mode,
            game_type=match_dto.info.game_type,
            game_end_timestamp=match_dto.info.game_end_timestamp,
            tournament_id=getattr(match_dto.info, "tournament_code", None),
            is_processed=False,
        )

        # Transform participants
        participants = []
        for participant_dto in match_dto.info.participants:
            participant_orm = self._transform_participant_dto(
                participant_dto, match_dto.metadata.match_id
            )
            participants.append(participant_orm)

        # Attach participants to match
        match_orm.participants = participants

        return match_orm

    def _transform_participant_dto(
        self, participant_dto, match_id: str
    ) -> MatchParticipantORM:
        """Transform Riot ParticipantDTO to domain MatchParticipantORM.

        Args:
            participant_dto: Riot API participant data
            match_id: Match identifier

        Returns:
            MatchParticipantORM domain object
        """
        # Calculate CS from Riot fields
        cs = getattr(participant_dto, "total_minions_killed", 0) + getattr(
            participant_dto, "neutral_minions_killed", 0
        )

        return MatchParticipantORM(
            match_id=match_id,
            puuid=participant_dto.puuid,
            summoner_name=participant_dto.summoner_name or None,
            summoner_level=getattr(participant_dto, "summoner_level", 1),
            team_id=participant_dto.team_id,
            champion_id=participant_dto.champion_id,
            champion_name=participant_dto.champion_name,
            kills=participant_dto.kills,
            deaths=participant_dto.deaths,
            assists=participant_dto.assists,
            win=participant_dto.win,
            gold_earned=participant_dto.gold_earned,
            vision_score=participant_dto.vision_score,
            cs=cs,
            champ_level=participant_dto.champ_level,
            total_damage_dealt=participant_dto.total_damage_dealt,
            total_damage_dealt_to_champions=participant_dto.total_damage_dealt_to_champions,
            total_damage_taken=participant_dto.total_damage_taken,
            total_heal=participant_dto.total_heal,
            individual_position=participant_dto.individual_position,
            team_position=participant_dto.team_position,
            role=participant_dto.role,
            riot_id_name=getattr(participant_dto, "riot_id_name", None),
            riot_id_tagline=getattr(participant_dto, "riot_id_tagline", None),
        )

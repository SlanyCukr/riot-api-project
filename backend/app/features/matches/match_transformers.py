"""Transformers for converting between ORM and Pydantic models (Data Mapper pattern).

This module provides transformation logic to convert between:
- ORM models (database/persistence layer)
- Pydantic models (API/presentation layer)

Following Martin Fowler's Data Mapper pattern to keep layers independent.
"""

from .orm_models import MatchORM
from .participants_orm import MatchParticipantORM
from .schemas import MatchResponse
from .participants_schemas import MatchParticipantResponse


class MatchTransformer:
    """Transforms between Match ORM and Pydantic schemas."""

    @staticmethod
    def to_response_schema(match_orm: MatchORM) -> MatchResponse:
        """Transform Match ORM to API response schema.

        Args:
            match_orm: Domain model from database

        Returns:
            Pydantic schema for API response
        """
        return MatchResponse(
            match_id=match_orm.match_id,
            platform_id=match_orm.platform_id,
            game_creation=match_orm.game_creation,
            game_duration=match_orm.game_duration,
            queue_id=match_orm.queue_id,
            game_version=match_orm.game_version,
            map_id=match_orm.map_id,
            game_mode=match_orm.game_mode,
            game_type=match_orm.game_type,
            game_end_timestamp=match_orm.game_end_timestamp,
            tournament_id=match_orm.tournament_id,
            is_processed=match_orm.is_processed,
            created_at=match_orm.created_at,
            updated_at=match_orm.updated_at,
        )


class MatchParticipantTransformer:
    """Transforms between MatchParticipant ORM and Pydantic schemas."""

    @staticmethod
    def to_response_schema(
        participant_orm: MatchParticipantORM,
    ) -> MatchParticipantResponse:
        """Transform MatchParticipant ORM to API response schema.

        Args:
            participant_orm: Domain model from database

        Returns:
            Pydantic schema for API response with computed fields
        """
        return MatchParticipantResponse(
            id=participant_orm.id,
            match_id=participant_orm.match_id,
            puuid=participant_orm.puuid,
            summoner_name=participant_orm.summoner_name,
            summoner_level=participant_orm.summoner_level,
            team_id=participant_orm.team_id,
            champion_id=participant_orm.champion_id,
            champion_name=participant_orm.champion_name,
            kills=participant_orm.kills,
            deaths=participant_orm.deaths,
            assists=participant_orm.assists,
            win=participant_orm.win,
            gold_earned=participant_orm.gold_earned,
            vision_score=participant_orm.vision_score,
            cs=participant_orm.cs,
            kda=float(participant_orm.calculate_kda()),  # Computed from domain logic
            champ_level=participant_orm.champ_level,
            total_damage_dealt=participant_orm.total_damage_dealt,
            total_damage_dealt_to_champions=participant_orm.total_damage_dealt_to_champions,
            total_damage_taken=participant_orm.total_damage_taken,
            total_heal=participant_orm.total_heal,
            individual_position=participant_orm.individual_position,
            team_position=participant_orm.team_position,
            role=participant_orm.role,
            riot_id_name=participant_orm.riot_id_name,
            riot_id_tagline=participant_orm.riot_id_tagline,
            created_at=participant_orm.created_at,
            updated_at=participant_orm.updated_at,
        )

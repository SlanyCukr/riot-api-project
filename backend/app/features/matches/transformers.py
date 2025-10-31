"""Data transformation utilities for converting between DTOs and database models.

This module provides utility classes for transforming data from Riot API DTOs
to formats suitable for database storage, validation, and processing.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import structlog

if TYPE_CHECKING:
    from .orm_models import MatchORM, MatchParticipantORM


logger = structlog.get_logger(__name__)


class MatchDTOTransformer:
    """Utility for transforming match DTOs from Riot API."""

    @staticmethod
    def extract_match_ids(match_list_dto: Any) -> List[str]:
        """Extract match IDs from match list DTO.

        Handles different DTO formats from Riot API.

        Args:
            match_list_dto: Match list DTO from Riot API

        Returns:
            List of match ID strings

        Example:
            >>> dto = MatchListDTO(match_ids=['EUN1_123', 'EUN1_456'])
            >>> MatchDTOTransformer.extract_match_ids(dto)
            ['EUN1_123', 'EUN1_456']
        """
        if match_list_dto is None:
            return []

        # Handle DTO with match_ids attribute
        if hasattr(match_list_dto, "match_ids"):
            return list(match_list_dto.match_ids)

        # Handle direct list
        if isinstance(match_list_dto, list):
            # Cast to list of strings since we expect match IDs
            return [str(item) for item in match_list_dto]  # type: ignore[arg-type]

        # Fallback to empty list
        logger.warning(
            "Unexpected match list DTO format",
            dto_type=type(match_list_dto).__name__,
        )
        return []

    @staticmethod
    def sanitize_participant_names(participant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize player name fields by converting empty strings to None.

        The Riot API sometimes returns empty strings for name fields instead of null.
        This normalizes the data for proper database storage.

        Args:
            participant_data: Participant data dictionary

        Returns:
            Sanitized participant data with None instead of empty strings

        Example:
            >>> data = {'summoner_name': '', 'riot_id_name': 'Player'}
            >>> MatchDTOTransformer.sanitize_participant_names(data)
            {'summoner_name': None, 'riot_id_name': 'Player'}
        """
        name_fields = ["riot_id_name", "riot_id_tagline", "summoner_name"]

        for field in name_fields:
            if field in participant_data:
                if participant_data[field] == "" or participant_data[field] is None:
                    participant_data[field] = None

        return participant_data

    @staticmethod
    def extract_participant_data(participant_dto: Any) -> Dict[str, Any]:
        """Extract participant data from DTO for database storage.

        Args:
            participant_dto: Participant DTO from match data

        Returns:
            Dictionary with participant data ready for database storage
        """
        data: Dict[str, Any] = {
            "puuid": participant_dto.puuid,
            "riot_id_name": participant_dto.riot_id_game_name or None,
            "riot_id_tagline": participant_dto.riot_id_tagline or None,
            "summoner_name": participant_dto.summoner_name or None,
            "summoner_level": participant_dto.summoner_level,
            "champion_id": participant_dto.champion_id,
            "champion_name": participant_dto.champion_name,
            "team_id": participant_dto.team_id,
            "team_position": participant_dto.team_position,
            "win": participant_dto.win,
            "kills": participant_dto.kills,
            "deaths": participant_dto.deaths,
            "assists": participant_dto.assists,
            "gold_earned": participant_dto.gold_earned,
            "cs": participant_dto.total_minions_killed
            + participant_dto.neutral_minions_killed,
            "vision_score": participant_dto.vision_score or 0,
            "total_damage_dealt_to_champions": participant_dto.total_damage_dealt_to_champions,
            "total_damage_taken": participant_dto.total_damage_taken,
        }

        return MatchDTOTransformer.sanitize_participant_names(data)


class PlayerDataSanitizer:
    """Utility for sanitizing player data."""

    @staticmethod
    def ensure_summoner_name(summoner_name: Optional[str]) -> str:
        """Ensure summoner name is never null or empty string.

        Args:
            summoner_name: Summoner name from API (may be None or empty)

        Returns:
            Valid summoner name or fallback value

        Example:
            >>> PlayerDataSanitizer.ensure_summoner_name(None)
            'Unknown Player'
            >>> PlayerDataSanitizer.ensure_summoner_name('')
            'Unknown Player'
            >>> PlayerDataSanitizer.ensure_summoner_name('Player1')
            'Player1'
        """
        if not summoner_name or summoner_name.strip() == "":
            return "Unknown Player"
        return summoner_name

    @staticmethod
    def sanitize_player_fields(player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all player data fields.

        Ensures:
        - Empty strings converted to None
        - Summoner name has fallback value
        - Platform is lowercase

        Args:
            player_data: Player data dictionary

        Returns:
            Sanitized player data
        """
        # Convert empty strings to None
        name_fields = ["riot_id", "tag_line", "summoner_name"]
        for field in name_fields:
            if field in player_data:
                if player_data[field] == "":
                    player_data[field] = None

        # Ensure summoner name has a value
        if "summoner_name" in player_data:
            player_data["summoner_name"] = PlayerDataSanitizer.ensure_summoner_name(
                player_data.get("summoner_name")
            )

        # Normalize platform to lowercase
        if "platform" in player_data and player_data["platform"]:
            player_data["platform"] = player_data["platform"].upper()

        return player_data


class MatchTransformer:
    """Data mapper for converting between ORM models and API response schemas.

    Following the Data Mapper pattern to keep layers decoupled.
    Transforms rich domain models with business logic into API response schemas.
    """

    @staticmethod
    def match_orm_to_response(match_orm: "MatchORM"):
        """Transform MatchORM domain model to MatchResponse API schema.

        Applies business logic from domain model (e.g., game type detection,
        duration calculations, patch version extraction) and converts to API response format.

        This demonstrates the Data Mapper pattern where transformers bridge
        the domain layer (with business logic) and the API layer (with DTOs).

        :param match_orm: Match domain model from database
        :returns: Match response schema for API
        """
        from .schemas import MatchResponse

        # Use Pydantic's from_attributes to map most fields automatically
        response = MatchResponse.model_validate(match_orm)

        # Add computed fields from domain logic
        # These values are calculated using the domain model's business methods
        response.is_ranked = match_orm.is_ranked_game()
        response.duration_minutes = match_orm.get_duration_minutes()
        response.is_recent = match_orm.is_recent()
        response.is_valid_game = match_orm.is_valid_game()
        response.is_summoners_rift = match_orm.is_summoners_rift()
        response.game_creation_datetime = match_orm.get_game_creation_datetime()
        response.patch_version = match_orm.get_patch_version()
        response.winning_team_id = match_orm.get_winning_team_id()

        return response

    @staticmethod
    def match_participant_orm_to_response(participant_orm: "MatchParticipantORM"):
        """Transform MatchParticipantORM to response schema.

        Adds computed fields from domain logic (e.g., KDA calculation, performance metrics).

        :param participant_orm: Match participant domain model from database
        :returns: Match participant response schema for API
        """
        from .schemas import MatchParticipantResponse

        # Use Pydantic's from_attributes to map most fields automatically
        response = MatchParticipantResponse.model_validate(participant_orm)

        # Add computed fields from domain logic
        # These values are calculated using the domain model's business methods
        response.calculated_kda = participant_orm.calculate_kda()
        response.is_carry_performance = participant_orm.is_carry_performance()
        response.cs_per_minute = participant_orm.get_cs_per_minute()
        response.is_support_role = participant_orm.is_support_role()
        response.is_high_vision = participant_orm.is_high_vision()
        response.is_perfect_kda = participant_orm.is_perfect_kda()
        response.is_good_cs = participant_orm.is_good_cs()
        response.performance_grade = participant_orm.get_performance_grade()

        return response

    @staticmethod
    def match_with_participants_to_response(
        match_orm: "MatchORM", include_participants: bool = True
    ):
        """Transform MatchORM with participants to comprehensive response.

        Includes match data and optionally participant data with all computed fields.

        :param match_orm: Match domain model from database
        :param include_participants: Whether to include participant data
        :returns: Comprehensive match response with participants
        """
        from .schemas import MatchWithParticipantsResponse

        # Transform match data
        match_response = MatchTransformer.match_orm_to_response(match_orm)

        if include_participants and match_orm.participants:
            # Transform all participants
            participants_response = [
                MatchTransformer.match_participant_orm_to_response(participant)
                for participant in match_orm.participants
            ]

            # Create comprehensive response
            return MatchWithParticipantsResponse(
                **match_response.model_dump(),
                participants=participants_response,
                participant_count=len(participants_response),
            )

        # Return basic match response if no participants
        return match_response


# Legacy transformation functions for backward compatibility
def match_orm_to_response(match_orm: "MatchORM"):
    """Transform MatchORM to MatchResponse schema.

    :param match_orm: Match domain model
    :returns: Match response schema
    """
    return MatchTransformer.match_orm_to_response(match_orm)


def match_participant_orm_to_response(participant_orm: "MatchParticipantORM"):
    """Transform MatchParticipantORM to response schema.

    :param participant_orm: Match participant domain model
    :returns: Match participant response schema
    """
    return MatchTransformer.match_participant_orm_to_response(participant_orm)

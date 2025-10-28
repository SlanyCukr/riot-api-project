"""Transformers for converting between layers in players feature.

This module provides transformation functions for:
- ORM models → Pydantic schemas (API responses)
- Riot API DTOs → ORM models (Anti-Corruption Layer)

Following the Data Mapper pattern to keep layers decoupled.
"""

from .orm_models import PlayerORM, PlayerRankORM
from .schemas import PlayerResponse
from .ranks_schemas import PlayerRankResponse


def player_orm_to_response(player: PlayerORM) -> PlayerResponse:
    """Transform PlayerORM domain model to PlayerResponse API schema.

    Applies business logic from domain model (e.g., smurf likelihood calculation)
    and converts to API response format.

    :param player: Player domain model from database
    :returns: Player response schema for API
    """
    # Use Pydantic's from_attributes to map most fields automatically
    response = PlayerResponse.model_validate(player)

    # Add computed fields from domain logic
    # Note: smurf_likelihood is calculated using domain model's business logic
    # This demonstrates how transformers bridge domain logic and API layer

    return response


def player_rank_orm_to_response(rank: PlayerRankORM) -> PlayerRankResponse:
    """Transform PlayerRankORM to PlayerRankResponse API schema.

    :param rank: Rank domain model from database
    :returns: Rank response schema for API
    """
    return PlayerRankResponse.model_validate(rank)

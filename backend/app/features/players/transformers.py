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

    Applies business logic from domain model (e.g., win rate, smurf likelihood)
    and converts to API response format.

    This demonstrates the Data Mapper pattern where transformers bridge
    the domain layer (with business logic) and the API layer (with DTOs).

    :param player: Player domain model from database
    :returns: Player response schema for API
    """
    # Use Pydantic's from_attributes to map most fields automatically
    response = PlayerResponse.model_validate(player)

    # Add computed fields from domain logic
    # These values are calculated using the domain model's business methods
    response.win_rate = player.win_rate
    response.total_games = player.total_games
    response.display_rank = player.display_rank
    response.is_new_account = player.is_new_account()
    response.is_veteran = player.is_veteran()
    response.is_high_elo = player.is_high_elo()
    response.needs_data_refresh = player.needs_data_refresh()

    # Calculate and add smurf likelihood (complex multi-factor calculation)
    response.smurf_likelihood = player.calculate_smurf_likelihood()

    return response


def player_rank_orm_to_response(rank: PlayerRankORM) -> PlayerRankResponse:
    """Transform PlayerRankORM to PlayerRankResponse API schema.

    Adds computed fields from domain logic (e.g., mmr_estimate, is_fresh).

    :param rank: Rank domain model from database
    :returns: Rank response schema for API
    """
    response = PlayerRankResponse.model_validate(rank)

    # Add computed fields from domain logic
    response.is_provisional = rank.is_provisional()
    response.is_fresh = rank.is_fresh()
    response.mmr_estimate = rank.calculate_mmr_estimate()

    return response

"""Player API endpoints for the Riot API application."""

import logging
import re
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.players import (
    PlayerResponse,
)
from ..schemas.ranks import PlayerRankResponse
from ..models.ranks import PlayerRank
from ..api.dependencies import (
    PlayerServiceDep,
    RiotDataManagerDep,
    get_player_service,
    get_db,
)
from ..riot_api.constants import Platform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players", tags=["players"])
router.get_player_service = get_player_service  # type: ignore[attr-defined]


def validate_riot_id(riot_id: str) -> tuple[str, str]:
    """Validate Riot ID format and return game_name and tag_line."""
    if "#" not in riot_id:
        raise HTTPException(status_code=400, detail="Invalid Riot ID format")

    game_name, tag_line = riot_id.split("#", 1)
    game_name, tag_line = game_name.strip(), tag_line.strip()

    if not game_name or not tag_line:
        raise HTTPException(status_code=400, detail="Invalid Riot ID format")

    if len(game_name) > 16 or len(tag_line) > 8:
        raise HTTPException(status_code=400, detail="Riot ID too long")

    # Basic character validation
    if not re.match(r"^[a-zA-Z0-9\s\.\-_]+$", game_name):
        raise HTTPException(status_code=400, detail="Invalid characters in name")

    if not re.match(r"^[a-zA-Z0-9]+$", tag_line):
        raise HTTPException(status_code=400, detail="Invalid characters in tag")

    return game_name, tag_line


@router.get("/search", response_model=list[PlayerResponse])
async def search_player(
    request: Request,
    player_service: PlayerServiceDep,
    query: str = Query(
        ...,
        min_length=3,
        max_length=30,
        description="Search query (name, tag, or riot_id)",
    ),
    platform: Platform = Query(Platform.EUN1, description="Platform region"),
):
    """
    Fuzzy search for players by name, tag, or Riot ID.

    **BREAKING CHANGE (Phase 2)**: This endpoint now returns an array
    of results instead of a single player object. Returns empty array []
    if no matches found (no longer returns 404).

    Search patterns:
    - "Name#TAG" → Search for Riot ID (exact match gets highest priority)
    - "#TAG" → Search for tag only
    - "Name" → Search for summoner name

    Args:
        query: Search string (3-100 characters)
        platform: Platform region (e.g., "eun1", "euw1", "na1")

    Returns:
        list[PlayerResponse]: Array of up to 10 matching players,
                              sorted by relevance (empty array if none found)

    Examples:
        GET /players/search?query=Dangerous&platform=eun1
        GET /players/search?query=DangerousDan#EUW&platform=eun1
        GET /players/search?query=#EUW&platform=eun1
    """
    try:
        results = await player_service.fuzzy_search_players(
            query=query,
            platform=platform.value,
            limit=10,
        )
        if not results:
            logger.debug(
                f"No results found for query: {query}, platform: {platform.value}"
            )
        return results

    except Exception as e:
        # Unexpected error - log and return 500
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/suggestions", response_model=list[PlayerResponse])
async def get_player_suggestions(
    request: Request,
    player_service: PlayerServiceDep,
    q: str = Query(
        ...,
        min_length=3,
        max_length=30,
        description="Search query (name, tag, or riot_id)",
    ),
    platform: Platform = Query(..., description="Platform region (required)"),
    limit: int = Query(
        5,
        ge=1,
        le=10,
        description="Number of suggestions to return (default: 5, max: 10)",
    ),
):
    """
    Get autocomplete suggestions for player search.

    This endpoint is optimized for autocomplete/typeahead functionality
    and returns a smaller set of top matches (default: 5) for quick response.

    Search patterns:
    - "Name#TAG" → Search for Riot ID (exact match gets highest priority)
    - "#TAG" → Search for tag only
    - "Name" → Search for summoner name

    Args:
        q: Search string (3-100 characters)
        platform: Platform region (e.g., "eun1", "euw1", "na1") - required
        limit: Maximum number of suggestions to return (default: 5, max: 10)

    Returns:
        list[PlayerResponse]: Array of up to `limit` matching players,
                              sorted by relevance (empty array if none found)

    Examples:
        GET /players/suggestions?q=Danger&platform=eun1
        GET /players/suggestions?q=DangerousDan#EUW&platform=eun1&limit=3
        GET /players/suggestions?q=#EUW&platform=eun1&limit=10
    """
    try:
        results = await player_service.fuzzy_search_players(
            query=q,
            platform=platform.value,
            limit=limit,
        )
        if not results:
            logger.debug(
                f"No suggestions found for query: {q}, platform: {platform.value}"
            )
        return results

    except Exception as e:
        # Unexpected error - log and return 500
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions failed: {str(e)}",
        )


@router.get("/{puuid}", response_model=PlayerResponse)
async def get_player_by_puuid(puuid: str, player_service: PlayerServiceDep):
    """Get player information by PUUID."""
    player = await player_service.get_player_by_puuid(puuid)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{puuid}/recent-opponents", response_model=list[PlayerResponse])
async def get_player_recent_opponents(
    puuid: str,
    player_service: PlayerServiceDep,
    limit: int = Query(10, ge=1, le=50, description="Number of recent opponents"),
):
    """Get recent opponents for a player with their details (database only, no Riot API calls)."""
    opponents = await player_service.get_recent_opponents_with_details(puuid, limit)
    return opponents


# === Player Tracking Endpoints ===


@router.post("/{puuid}/track", response_model=PlayerResponse)
async def track_player(puuid: str, player_service: PlayerServiceDep):
    """
    Mark a player for automated tracking and monitoring.

    Tracked players will have their match history and rank automatically
    updated every 2 minutes by the background job scheduler.

    Returns:
        Updated player data with is_tracked=True

    Raises:
        404: Player not found
        400: Maximum tracked players limit reached
    """
    try:
        player = await player_service.track_player(puuid)
        return player
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            # Tracking limit reached or other validation error
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track player: {str(e)}",
        )


@router.delete("/{puuid}/track", response_model=PlayerResponse)
async def untrack_player(puuid: str, player_service: PlayerServiceDep):
    """
    Remove a player from automated tracking.

    The player's data will remain in the database but will no longer
    receive automatic updates.

    Returns:
        Updated player data with is_tracked=False

    Raises:
        404: Player not found
    """
    try:
        player = await player_service.untrack_player(puuid)
        return player
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to untrack player: {str(e)}",
        )


@router.get("/{puuid}/tracking-status")
async def get_tracking_status(puuid: str, player_service: PlayerServiceDep):
    """
    Get the tracking status for a player.

    Returns:
        dict: {'is_tracked': bool}

    Raises:
        404: Player not found
    """
    try:
        player = await player_service.get_player_by_puuid(puuid)
        return {"is_tracked": player.is_tracked}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tracking status: {str(e)}",
        )


@router.get("/tracked/list", response_model=list[PlayerResponse])
async def get_tracked_players(player_service: PlayerServiceDep):
    """
    Get all players currently marked for tracking.

    Returns:
        List of tracked players with their current data
    """
    try:
        players = await player_service.get_tracked_players()
        return players
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tracked players: {str(e)}",
        )


@router.post("/add-tracked", response_model=PlayerResponse)
async def add_tracked_player(
    player_service: PlayerServiceDep,
    riot_data_manager: RiotDataManagerDep,
    riot_id: str | None = Query(None, description="Riot ID in format name#tag"),
    summoner_name: str | None = Query(None, description="Summoner name"),
    platform: str = Query("eun1", description="Platform region"),
):
    """
    Search for a player in Riot API and add them with is_tracked=true.

    Accepts either riot_id (name#tag) or summoner_name.
    If the player is already in the database, marks them as tracked.
    If not found in database, fetches from Riot API and tracks them.

    Args:
        riot_id: Riot ID in format name#tag
        summoner_name: Summoner name (legacy search)
        platform: Platform region (default: eun1)

    Returns:
        Player data with is_tracked=True

    Raises:
        400: Invalid input or tracking limit reached
        404: Player not found in Riot API
        500: Unexpected error
    """
    if not riot_id and not summoner_name:
        raise HTTPException(
            status_code=400, detail="Either riot_id or summoner_name must be provided"
        )

    try:
        if riot_id:
            # Parse and validate Riot ID (name#tag)
            game_name, tag_line = validate_riot_id(riot_id)

            # Fetch and track player (this calls Riot API once)
            player = await player_service.add_and_track_player(
                riot_data_manager=riot_data_manager,
                game_name=game_name,
                tag_line=tag_line,
                platform=platform,
            )
        else:
            if summoner_name is None:
                raise HTTPException(status_code=400, detail="summoner_name is required")

            # For summoner name, we need to fetch from Riot API
            # Since summoner name alone doesn't work with Riot API v5,
            # we'll try to find in database first, then error if not found
            try:
                player_response = await player_service.get_player_by_summoner_name(
                    summoner_name, platform
                )
                # Track the found player
                player = await player_service.track_player(player_response.puuid)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Player '{summoner_name}' not found in database. Please use Riot ID (name#tag) format to add new players.",
                )

        return player

    except ValueError as e:
        # Player not found or validation error
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            # Tracking limit or other validation error
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while adding tracked player: {str(e)}",
        )


# === Player Rank Endpoints ===


@router.get("/{puuid}/rank", response_model=PlayerRankResponse | None)
async def get_player_current_rank(
    puuid: str,
    queue_type: str = Query(
        "RANKED_SOLO_5x5", description="Queue type to fetch rank for"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current rank for a player.

    Args:
        puuid: Player's PUUID
        queue_type: Queue type (default: RANKED_SOLO_5x5)

    Returns:
        Current rank data or None if no rank data exists

    Raises:
        500: Database error
    """
    try:
        stmt = (
            select(PlayerRank)
            .where(PlayerRank.puuid == puuid)
            .where(PlayerRank.queue_type == queue_type)
            .order_by(PlayerRank.updated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        rank = result.scalar_one_or_none()

        if rank:
            return PlayerRankResponse.model_validate(rank)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch player rank: {str(e)}",
        )

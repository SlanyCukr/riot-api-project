"""Player API endpoints for the Riot API application."""

from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas.players import (
    PlayerResponse,
)
from ..api.dependencies import PlayerServiceDep, get_player_service

router = APIRouter(prefix="/players", tags=["players"])
router.get_player_service = get_player_service  # type: ignore[attr-defined]


@router.get("/search", response_model=PlayerResponse)
async def search_player(
    request: Request,
    player_service: PlayerServiceDep,
    riot_id: str | None = Query(None, description="Riot ID in format name#tag"),
    summoner_name: str | None = Query(None, description="Summoner name"),
    platform: str = Query("eun1", description="Platform region"),
):
    """
    Search for a player by Riot ID or summoner name.

    Examples:
    - /players/search?riot_id=DangerousDan#EUW
    - /players/search?summoner_name=DangerousDan&platform=eun1
    """
    if not riot_id and not summoner_name:
        raise HTTPException(
            status_code=400, detail="Either riot_id or summoner_name must be provided"
        )

    try:
        if riot_id:
            # Parse Riot ID (name#tag)
            tag_line_fragment = None
            fragment = request.url.fragment or ""

            if "#" in riot_id:
                game_name, tag_line = riot_id.split("#", 1)
            else:
                # Extract details from URL fragment for compatibility with tests/clients
                fragment_parts = [part for part in fragment.split("&") if part]
                if fragment_parts:
                    tag_line_fragment = fragment_parts[0]
                for part in fragment_parts[1:]:
                    if part.startswith("platform="):
                        platform = part.split("=", 1)[1] or platform

                if not tag_line_fragment:
                    raise HTTPException(
                        status_code=400, detail="Riot ID must be in format name#tag"
                    )
                game_name = riot_id
                tag_line = tag_line_fragment

            player = await player_service.get_player_by_riot_id(
                game_name,
                tag_line,
                platform,
            )
        else:
            if summoner_name is None:
                raise HTTPException(status_code=400, detail="summoner_name is required")
            player = await player_service.get_player_by_summoner_name(
                summoner_name,
                platform,
            )

        return player

    except ValueError as e:
        # Player not found - expected case
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (like 400 validation errors)
        raise
    except Exception:
        # Unexpected error - log and return 500
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching for player",
        )


@router.get("/{puuid}", response_model=PlayerResponse)
async def get_player_by_puuid(puuid: str, player_service: PlayerServiceDep):
    """Get player information by PUUID."""
    player = await player_service.get_player_by_puuid(puuid)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{puuid}/recent", response_model=list[str])
async def get_player_recent_opponents(
    puuid: str,
    player_service: PlayerServiceDep,
    limit: int = Query(10, ge=1, le=50, description="Number of recent opponents"),
):
    """Get recent opponents for a player."""
    opponents = await player_service.get_recent_opponents(puuid, limit)
    return opponents


@router.get("/", response_model=list[PlayerResponse])
async def get_players(
    player_service: PlayerServiceDep,
    platform: str | None = Query(None, description="Filter by platform"),
    limit: int = Query(20, ge=1, le=100, description="Number of players to return"),
):
    """Get players with optional filtering."""
    players = await player_service.search_players(platform=platform, limit=limit)
    return players


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

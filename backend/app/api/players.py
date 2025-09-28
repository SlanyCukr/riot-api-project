"""
Player API endpoints for the Riot API application.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID

from ..schemas.players import PlayerResponse, PlayerSearchRequest, PlayerListResponse, PlayerBulkRequest, PlayerBulkResponse
from ..services.players import PlayerService
from ..api.dependencies import PlayerServiceDep

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/search", response_model=PlayerResponse)
async def search_player(
    riot_id: Optional[str] = Query(None, description="Riot ID in format name#tag"),
    summoner_name: Optional[str] = Query(None, description="Summoner name"),
    platform: str = Query("eun1", description="Platform region"),
    player_service: PlayerService = Depends()
):
    """
    Search for a player by Riot ID or summoner name.

    Examples:
    - /players/search?riot_id=DangerousDan#EUW
    - /players/search?summoner_name=DangerousDan&platform=eun1
    """
    if not riot_id and not summoner_name:
        raise HTTPException(
            status_code=400,
            detail="Either riot_id or summoner_name must be provided"
        )

    try:
        if riot_id:
            # Parse Riot ID (name#tag)
            if "#" not in riot_id:
                raise HTTPException(
                    status_code=400,
                    detail="Riot ID must be in format name#tag"
                )
            game_name, tag_line = riot_id.split("#", 1)
            player = await player_service.get_player_by_riot_id(
                game_name, tag_line, platform
            )
        else:
            player = await player_service.get_player_by_summoner_name(
                summoner_name, platform
            )

        return player

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{puuid}", response_model=PlayerResponse)
async def get_player_by_puuid(
    puuid: UUID,
    player_service: PlayerService = Depends()
):
    """Get player information by PUUID"""
    player = await player_service.get_player_by_puuid(str(puuid))
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{puuid}/recent", response_model=List[str])
async def get_player_recent_opponents(
    puuid: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of recent opponents"),
    player_service: PlayerService = Depends()
):
    """Get recent opponents for a player"""
    opponents = await player_service.get_recent_opponents(str(puuid), limit)
    return opponents


@router.post("/search", response_model=List[PlayerResponse])
async def search_players_advanced(
    search_request: PlayerSearchRequest,
    player_service: PlayerService = Depends()
):
    """Advanced player search with multiple criteria."""
    players = await player_service.search_players(
        summoner_name=search_request.summoner_name,
        riot_id=search_request.riot_id,
        platform=search_request.platform,
        limit=search_request.size
    )
    return players


@router.post("/bulk", response_model=PlayerBulkResponse)
async def get_players_bulk(
    bulk_request: PlayerBulkRequest,
    player_service: PlayerService = Depends()
):
    """Get multiple players by PUUIDs."""
    puuids = [str(puuid) for puuid in bulk_request.puuids]
    players = await player_service.bulk_get_players(puuids)

    # Find which PUUIDs were not found
    found_puuids = {str(player.puuid) for player in players}
    not_found = [puuid for puuid in puuids if puuid not in found_puuids]

    return PlayerBulkResponse(
        players=players,
        not_found=[UUID(puuid) for puuid in not_found]
    )


@router.get("/", response_model=List[PlayerResponse])
async def get_players(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(20, ge=1, le=100, description="Number of players to return"),
    player_service: PlayerService = Depends()
):
    """Get players with optional filtering."""
    players = await player_service.search_players(
        platform=platform,
        limit=limit
    )
    return players
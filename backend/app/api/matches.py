"""Match API endpoints for the Riot API application."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..schemas.matches import (
    MatchListResponse,
    MatchStatsResponse,
)
from ..api.dependencies import (
    MatchServiceDep,
    get_match_service,
)

router = APIRouter(prefix="/matches", tags=["matches"])
router.get_match_service = get_match_service  # type: ignore[attr-defined]


@router.get("/player/{puuid}", response_model=MatchListResponse)
async def get_player_matches(
    puuid: str,
    match_service: MatchServiceDep,
    start: int = Query(0, ge=0, description="Start index for pagination"),
    count: int = Query(20, ge=1, le=500, description="Number of matches to return"),
    queue: Optional[int] = Query(
        None, description="Filter by queue ID (420=ranked solo)"
    ),
    start_time: Optional[int] = Query(None, description="Start timestamp"),
    end_time: Optional[int] = Query(None, description="End timestamp"),
):
    """
    Get match history for a player.

    Queue IDs:
    - 420: Ranked Solo/Duo
    - 440: Ranked Flex
    - 450: ARAM
    - 400: Normal Draft
    """
    try:
        matches = await match_service.get_player_matches(
            puuid=puuid,
            start=start,
            count=count,
            queue=queue,
            start_time=start_time,
            end_time=end_time,
        )
        return matches
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{puuid}/stats", response_model=MatchStatsResponse)
async def get_player_match_stats(
    puuid: str,
    match_service: MatchServiceDep,
    queue: Optional[int] = Query(None, description="Filter by queue ID"),
    limit: int = Query(50, ge=1, le=200, description="Number of matches to analyze"),
):
    """Get player statistics from recent matches."""
    try:
        stats = await match_service.get_player_stats(
            puuid=puuid, queue=queue, limit=limit
        )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""Match API endpoints for the Riot API application."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from ..schemas.matches import (
    MatchResponse,
    MatchListResponse,
    MatchStatsResponse,
    MatchSearchRequest,
)
from ..api.dependencies import MatchServiceDep, StatsServiceDep

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/player/{puuid}", response_model=MatchListResponse)
async def get_player_matches(
    puuid: str,
    match_service: MatchServiceDep,
    start: int = Query(0, ge=0, description="Start index for pagination"),
    count: int = Query(20, ge=1, le=100, description="Number of matches to return"),
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match_details(match_id: str, match_service: MatchServiceDep):
    """Get detailed match information."""
    try:
        match = await match_service.get_match_details(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return match
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
        stats = await match_service.get_player_stats(puuid, queue=queue, limit=limit)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{puuid}/encounters", response_model=List[str])
async def get_player_encounters(
    puuid: str,
    match_service: MatchServiceDep,
    limit: int = Query(20, ge=1, le=100, description="Number of matches to check"),
):
    """Get players encountered with/against in recent matches."""
    try:
        encounters = await match_service.get_player_encounters(puuid, limit=limit)
        return encounters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{puuid}/detailed-stats")
async def get_player_detailed_stats(
    puuid: str,
    stats_service: StatsServiceDep,
    queue: Optional[int] = Query(None, description="Filter by queue ID"),
    start_time: Optional[int] = Query(None, description="Start timestamp"),
    end_time: Optional[int] = Query(None, description="End timestamp"),
    limit: int = Query(100, ge=1, le=200, description="Number of matches to analyze"),
):
    """Get comprehensive player statistics including champion and position stats."""
    try:
        stats = await stats_service.calculate_player_statistics(
            puuid=puuid,
            queue_id=queue,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{puuid}/encounter-stats")
async def get_player_encounter_stats(
    puuid: str,
    stats_service: StatsServiceDep,
    limit: int = Query(50, ge=1, le=100, description="Number of matches to analyze"),
    min_encounters: int = Query(
        3, ge=1, le=10, description="Minimum encounters to include"
    ),
):
    """Get detailed encounter statistics with win rates and performance metrics."""
    try:
        encounter_stats = await stats_service.calculate_encounter_statistics(
            puuid=puuid, limit=limit, min_encounters=min_encounters
        )
        return encounter_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{match_id}/stats")
async def get_match_stats(match_id: str, stats_service: StatsServiceDep):
    """Get detailed statistics for a specific match."""
    try:
        stats = await stats_service.calculate_match_statistics(match_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Match not found")
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_matches(
    search_request: MatchSearchRequest, match_service: MatchServiceDep
):
    """Search matches with various filters."""
    try:
        results = await match_service.search_matches(
            puuid=search_request.puuid,
            queue_id=search_request.queue_id,
            game_mode=search_request.game_mode,
            start_time=search_request.start_time,
            end_time=search_request.end_time,
            champion_id=search_request.champion_id,
            is_processed=search_request.is_processed,
            page=search_request.page,
            size=search_request.size,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{match_id}/participants")
async def get_match_participants(match_id: str, match_service: MatchServiceDep):
    """Get all participants in a match with their details."""
    try:
        match_data = await match_service.get_match_by_id_with_participants(match_id)
        if not match_data:
            raise HTTPException(status_code=404, detail="Match not found")
        return match_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{puuid}/recent-form")
async def get_player_recent_form(
    puuid: str,
    stats_service: StatsServiceDep,
    queue: Optional[int] = Query(None, description="Filter by queue ID"),
    matches: int = Query(
        10, ge=5, le=20, description="Number of recent matches to analyze"
    ),
) -> Dict[str, Any]:
    """Get player's recent form and performance trends."""
    try:
        # Get player statistics to include performance trends
        stats = await stats_service.calculate_player_statistics(
            puuid=puuid, queue_id=queue, limit=matches
        )

        # Return only the relevant performance trend information
        return {
            "puuid": puuid,
            "recent_form": stats["performance_trends"],
            "matches_analyzed": stats["time_period"]["matches_analyzed"],
            "queue_filter": queue,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

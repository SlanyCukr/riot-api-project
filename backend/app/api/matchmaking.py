"""Matchmaking analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.matchmaking import (
    MatchmakingAnalysisRequest,
    MatchmakingAnalysisResponse,
    MatchmakingAnalysisStatusResponse,
)
from ..services.matchmaking_analysis import MatchmakingAnalysisService
from ..riot_api.client import RiotAPIClient
from .dependencies import get_riot_client

router = APIRouter(prefix="/matchmaking-analysis", tags=["matchmaking-analysis"])


async def get_matchmaking_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    riot_client: Annotated[RiotAPIClient, Depends(get_riot_client)],
) -> MatchmakingAnalysisService:
    """Get matchmaking analysis service instance."""
    return MatchmakingAnalysisService(db, riot_client)


MatchmakingServiceDep = Annotated[
    MatchmakingAnalysisService, Depends(get_matchmaking_service)
]


@router.post("/start", response_model=MatchmakingAnalysisResponse)
async def start_analysis(
    request: MatchmakingAnalysisRequest,
    service: MatchmakingServiceDep,
):
    """
    Start a new matchmaking analysis for a player.

    This will analyze the player's last 10 ranked matches and calculate
    average winrates for teammates vs enemies.
    """
    try:
        return await service.start_analysis(request.puuid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}", response_model=MatchmakingAnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: int,
    service: MatchmakingServiceDep,
):
    """Get the current status of a matchmaking analysis."""
    result = await service.get_analysis_status(analysis_id)

    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return result


@router.get("/player/{puuid}", response_model=MatchmakingAnalysisResponse)
async def get_latest_analysis(
    puuid: str,
    service: MatchmakingServiceDep,
):
    """Get the latest analysis for a player."""
    result = await service.get_latest_analysis(puuid)

    if not result:
        raise HTTPException(status_code=404, detail="No analysis found for this player")

    return result


@router.post("/{analysis_id}/cancel")
async def cancel_analysis(
    analysis_id: int,
    service: MatchmakingServiceDep,
):
    """Cancel an ongoing matchmaking analysis."""
    success = await service.cancel_analysis(analysis_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found or already completed/cancelled",
        )

    return {"message": "Analysis cancelled successfully"}

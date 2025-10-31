from fastapi import APIRouter, HTTPException, status

from app.features.matchmaking_analysis.dependencies import MatchmakingAnalysisServiceDep
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
    MatchmakingAnalysisListResponse,
)

router = APIRouter(prefix="/matchmaking-analysis", tags=["matchmaking-analysis"])


@router.post("/start", response_model=MatchmakingAnalysisResponse)
async def start_analysis(
    request: MatchmakingAnalysisCreate, service: MatchmakingAnalysisServiceDep
) -> MatchmakingAnalysisResponse:
    """Start a new matchmaking analysis"""
    try:
        return await service.start_analysis(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}",
        )


@router.get("/job/{job_id}/status", response_model=MatchmakingAnalysisResponse)
async def get_analysis_status(
    job_id: str, service: MatchmakingAnalysisServiceDep
) -> MatchmakingAnalysisResponse:
    """Get analysis job status"""
    result = await service.get_analysis_status(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found"
        )
    return result


@router.get("/user/{user_id}/analyses", response_model=MatchmakingAnalysisListResponse)
async def get_user_analyses(
    user_id: str, service: MatchmakingAnalysisServiceDep, limit: int = 50
) -> MatchmakingAnalysisListResponse:
    """Get user's analysis history"""
    analyses = await service.get_user_analyses(user_id, limit)
    return MatchmakingAnalysisListResponse(analyses=analyses)


@router.post("/job/{job_id}/execute", response_model=dict)
async def execute_analysis(job_id: str, service: MatchmakingAnalysisServiceDep) -> dict:
    """Execute analysis job (for background task execution)"""
    try:
        await service.execute_background_analysis(job_id)
        return {"message": "Analysis execution started", "job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute analysis: {str(e)}",
        )

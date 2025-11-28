from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query, status

from app.features.matchmaking_analysis.dependencies import MatchmakingAnalysisServiceDep
from app.features.matchmaking_analysis.schemas import (
    MatchmakingAnalysisCreate,
    MatchmakingAnalysisResponse,
    MatchmakingAnalysisListResponse,
)
from app.features.jobs.implementations.matchmaking_analysis_job import MatchmakingAnalysisJob

router = APIRouter(prefix="/matchmaking-analysis", tags=["matchmaking-analysis"])


@router.post(
    "/start",
    response_model=MatchmakingAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Matchmaking Analysis",
    description="""
    Start a new matchmaking fairness analysis for a player.

    This endpoint creates an analysis job and queues it for background execution.
    The analysis will:
    - Fetch the player's recent ranked matches
    - Calculate teammate and enemy winrates from cached player data
    - Analyze rank differences between teams
    - Compute an overall fairness score

    **Returns immediately with job ID**. Use GET /job/{job_id}/status to check progress.

    **Parameters**:
    - `user_id`: User identifier (from authenticated session)
    - `puuid`: Player's Riot PUUID to analyze
    - `region`: Riot region (e.g., 'na1', 'euw1')
    - `match_count`: Number of recent matches to analyze (1-100)

    **Fairness Score**: Value from 0.0 (very unfair) to 1.0 (perfectly fair)
    - Considers winrate disparity between teams
    - Considers rank differences between players
    - Weighted average of multiple fairness metrics
    """,
    responses={
        201: {
            "description": "Analysis job created and queued for background execution",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "user123",
                        "status": "pending",
                        "progress": 0.0,
                        "created_at": "2025-11-03T10:00:00Z",
                        "parameters": {
                            "puuid": "abc123...",
                            "region": "na1",
                            "match_count": 20,
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid request parameters (bad PUUID, region, or match count)"},
        429: {"description": "Rate limit exceeded - too many analysis requests"},
        500: {"description": "Internal server error during job creation"},
    },
)
async def start_analysis(
    request: MatchmakingAnalysisCreate,
    service: MatchmakingAnalysisServiceDep,
    background_tasks: BackgroundTasks,
) -> MatchmakingAnalysisResponse:
    """Start a new matchmaking analysis job.

    :param request: Analysis creation request with parameters
    :param service: Matchmaking analysis service (injected)
    :param background_tasks: FastAPI background tasks for scheduling execution
    :returns: Created analysis job with ID and initial status
    :raises HTTPException: 500 if job creation fails
    """
    try:
        # Create the job record
        response = await service.start_analysis(request)

        # Schedule background execution using the job system
        # This creates its own database session, avoiding the closed session issue
        job = MatchmakingAnalysisJob(job_config_id=0, analysis_id=response.id)
        background_tasks.add_task(job.run)

        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}",
        )


@router.get(
    "/job/{job_id}/status",
    response_model=MatchmakingAnalysisResponse,
    summary="Get Analysis Status",
    description="""
    Retrieve the current status and results of a matchmaking analysis.

    **Status Values**:
    - `pending`: Job queued, not yet started
    - `running`: Analysis in progress (check `progress` field for percentage)
    - `success`: Analysis completed successfully (see `result` field)
    - `failed`: Analysis failed (see `error_message` field)

    **Progress**: Percentage from 0.0 to 100.0 indicating completion

    **Results** (when status=success):
    - `matches_analyzed`: Number of matches processed
    - `winrate`: Player's overall winrate in analyzed matches
    - `avg_rank_difference`: Average rank gap between teams
    - `fairness_score`: Overall fairness metric (0.0-1.0)
    """,
    responses={
        200: {
            "description": "Analysis job found and returned",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "success",
                        "progress": 100.0,
                        "matches_analyzed": 20,
                        "winrate": 0.55,
                        "avg_rank_difference": 2.3,
                        "fairness_score": 0.82,
                        "completed_at": "2025-11-03T10:05:00Z",
                    }
                }
            },
        },
        404: {"description": "Analysis job not found"},
    },
)
async def get_analysis_status(
    service: MatchmakingAnalysisServiceDep,
    job_id: str = Path(..., description="Analysis job ID (UUID)"),
) -> MatchmakingAnalysisResponse:
    """Get analysis status and results by job ID.

    :param job_id: Analysis job UUID
    :param service: Matchmaking analysis service (injected)
    :returns: Analysis job with current status and results
    :raises HTTPException: 404 if job not found
    """
    result = await service.get_analysis_status(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found"
        )
    return result


@router.get(
    "/user/{user_id}/analyses",
    response_model=MatchmakingAnalysisListResponse,
    summary="List User Analyses",
    description="""
    Retrieve all matchmaking analyses for a specific user.

    Results are ordered by creation date (most recent first) and limited
    to the most recent analyses.

    **Use Cases**:
    - Display user's analysis history
    - Check if user has existing analyses
    - Track analysis patterns over time

    **Pagination**: Use `limit` parameter to control result count (max 100)
    """,
    responses={
        200: {
            "description": "List of user's analyses",
            "content": {
                "application/json": {
                    "example": {
                        "analyses": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "success",
                                "created_at": "2025-11-03T10:00:00Z",
                                "fairness_score": 0.82,
                            },
                            {
                                "id": "660e8400-e29b-41d4-a716-446655440111",
                                "status": "running",
                                "created_at": "2025-11-03T09:00:00Z",
                                "progress": 45.0,
                            },
                        ]
                    }
                }
            },
        },
    },
)
async def get_user_analyses(
    service: MatchmakingAnalysisServiceDep,
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of analyses to return"
    ),
) -> MatchmakingAnalysisListResponse:
    """List all analyses for a user.

    :param user_id: User identifier
    :param limit: Maximum results (1-100, default 50)
    :param service: Matchmaking analysis service (injected)
    :returns: List of user's analyses
    """
    analyses = await service.get_user_analyses(user_id, limit)
    return MatchmakingAnalysisListResponse(analyses=analyses)


@router.post(
    "/job/{job_id}/execute",
    response_model=dict,
    summary="Execute Analysis (Manual Trigger)",
    description="""
    Manually trigger execution of an existing analysis job.

    **Note**: This endpoint is primarily for manual/admin triggers.
    Normal flow uses automatic background execution after job creation.

    **Use Cases**:
    - Retry failed analyses
    - Admin/debug manual execution
    - Testing and development

    **Warning**: Executing an already-running job may cause conflicts.
    """,
    responses={
        200: {"description": "Analysis execution started"},
        404: {"description": "Analysis job not found"},
        500: {"description": "Execution failed"},
    },
)
async def execute_analysis(
    service: MatchmakingAnalysisServiceDep,
    job_id: str = Path(..., description="Analysis job ID to execute"),
) -> dict:
    """Execute analysis job manually (for admin/debug use).

    :param job_id: Analysis job UUID
    :param service: Matchmaking analysis service (injected)
    :returns: Confirmation message with job ID
    :raises HTTPException: 500 if execution fails
    """
    try:
        await service.execute_background_analysis(job_id)
        return {"message": "Analysis execution started", "job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute analysis: {str(e)}",
        )

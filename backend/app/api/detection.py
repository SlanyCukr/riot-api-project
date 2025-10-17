"""
Player analysis API endpoints.

This module provides REST API endpoints for player analysis,
including player analysis, detection history, statistics, and configuration.
"""

from fastapi import APIRouter, HTTPException, Query
import structlog

from ..schemas.detection import (
    DetectionResponse,
    DetectionRequest,
    DetectionExistsResponse,
)
from ..api.dependencies import DetectionServiceDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/player-analysis", tags=["player-analysis"])


@router.post("/analyze", response_model=DetectionResponse)
async def analyze_player(
    request: DetectionRequest, detection_service: DetectionServiceDep
):
    """
    Analyze a player using the player analysis algorithm.

    This endpoint performs comprehensive player analysis using multiple factors:
    - Win rate over recent matches
    - Account level analysis
    - Rank progression speed
    - Performance consistency metrics
    - KDA analysis

    The analysis returns a detection score, confidence level, and detailed factor breakdown.

    Args:
        request: Detection request with player PUUID and analysis parameters

    Returns:
        DetectionResponse with analysis results

    Raises:
        HTTPException: If player not found or analysis fails
    """
    try:
        logger.info(
            "Starting player analysis",
            puuid=request.puuid,
            min_games=request.min_games,
            queue_filter=request.queue_filter,
        )

        result = await detection_service.analyze_player(
            puuid=request.puuid,
            min_games=request.min_games,
            queue_filter=request.queue_filter,
            time_period_days=request.time_period_days,
            force_reanalyze=request.force_reanalyze,
        )

        logger.info(
            "Player analysis completed",
            puuid=request.puuid,
            is_smurf=result.is_smurf,
            detection_score=result.detection_score,
            confidence_level=result.confidence_level,
        )

        return result

    except ValueError as e:
        logger.error("Player not found", puuid=request.puuid, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Detection analysis failed", puuid=request.puuid, error=str(e))
        raise HTTPException(status_code=500, detail="Detection analysis failed")


@router.get("/player/{puuid}/exists", response_model=DetectionExistsResponse)
async def check_detection_exists(
    puuid: str,
    detection_service: DetectionServiceDep,
):
    """
    Check if player analysis exists for a player.

    This endpoint checks if a player analysis exists for a player
    and returns basic information about the most recent analysis.

    Args:
        puuid: Player PUUID

    Returns:
        DetectionExistsResponse with existence status and basic info

    Raises:
        HTTPException: If query fails
    """
    try:
        # Get most recent detection (within last 30 days)
        recent_result = await detection_service._get_recent_detection(
            puuid, hours=24 * 30
        )

        if recent_result:
            return DetectionExistsResponse(
                exists=True,
                last_analysis=recent_result.last_analysis,
                is_smurf=recent_result.is_smurf,
                detection_score=float(recent_result.smurf_score),
                confidence_level=recent_result.confidence or "none",
            )
        else:
            return DetectionExistsResponse(
                exists=False,
                last_analysis=None,
                is_smurf=None,
                detection_score=None,
                confidence_level=None,
            )

    except Exception as e:
        logger.error("Failed to check detection exists", puuid=puuid, error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to check detection existence"
        )


@router.get("/player/{puuid}/latest", response_model=DetectionResponse)
async def get_latest_detection(
    puuid: str,
    detection_service: DetectionServiceDep,
    force_refresh: bool = Query(False, description="Force new analysis"),
):
    """
    Get the latest player analysis result for a player.

    This endpoint returns the most recent player analysis for a player.
    If no recent analysis exists, it will perform a new analysis.

    Args:
        puuid: Player PUUID
        force_refresh: Force new analysis even if recent exists

    Returns:
        DetectionResponse with the latest analysis results

    Raises:
        HTTPException: If player not found or analysis fails
    """
    try:
        if force_refresh:
            result = await detection_service.analyze_player(puuid=puuid)
        else:
            # Try to get recent analysis first
            recent_result = await detection_service._get_recent_detection(
                puuid, hours=24
            )
            if recent_result:
                result = detection_service._convert_to_response(recent_result)
                logger.info("Returning cached detection result", puuid=puuid)
            else:
                result = await detection_service.analyze_player(puuid=puuid)
                logger.info("Performed new detection analysis", puuid=puuid)

        return result

    except ValueError as e:
        logger.error("Player not found", puuid=puuid, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to get latest detection", puuid=puuid, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get detection result: {str(e)}"
        )

"""
Smurf detection API endpoints.

This module provides REST API endpoints for smurf detection analysis,
including player analysis, detection history, statistics, and configuration.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import structlog

from ..schemas.detection import (
    DetectionResponse,
    DetectionRequest,
    DetectionStatsResponse,
)
from ..api.dependencies import DetectionServiceDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/detection", tags=["smurf-detection"])


@router.post("/analyze", response_model=DetectionResponse)
async def analyze_player(
    request: DetectionRequest, detection_service: DetectionServiceDep
):
    """
    Analyze a player for smurf behavior.

    This endpoint performs comprehensive smurf detection analysis using multiple factors:
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
            "Starting smurf detection analysis",
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
            "Smurf detection analysis completed",
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


@router.get("/player/{puuid}/latest", response_model=DetectionResponse)
async def get_latest_detection(
    puuid: str,
    detection_service: DetectionServiceDep,
    force_refresh: bool = Query(False, description="Force new analysis"),
):
    """
    Get the latest smurf detection result for a player.

    This endpoint returns the most recent smurf detection analysis for a player.
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
        logger.error("Failed to get latest detection", puuid=puuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get detection result")


@router.get("/player/{puuid}/history", response_model=List[DetectionResponse])
async def get_detection_history(
    puuid: str,
    detection_service: DetectionServiceDep,
    limit: int = Query(
        default=10, ge=1, le=50, description="Number of historical results"
    ),
    include_factors: bool = Query(
        default=True, description="Include detailed factor analysis"
    ),
):
    """
    Get historical smurf detection results for a player.

    This endpoint returns a history of smurf detection analyses for a player,
    allowing tracking of detection scores and confidence levels over time.

    Args:
        puuid: Player PUUID
        limit: Maximum number of historical results to return
        include_factors: Whether to include detailed factor analysis

    Returns:
        list of DetectionResponse objects with historical analysis results

    Raises:
        HTTPException: If history retrieval fails
    """
    try:
        logger.info("Retrieving detection history", puuid=puuid, limit=limit)

        history = await detection_service.get_detection_history(
            puuid=puuid, limit=limit, include_factors=include_factors
        )

        logger.info(
            "Detection history retrieved", puuid=puuid, results_count=len(history)
        )

        return history

    except Exception as e:
        logger.error("Failed to get detection history", puuid=puuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get detection history")


@router.get("/stats", response_model=DetectionStatsResponse)
async def get_detection_stats(detection_service: DetectionServiceDep):
    """
    Get overall smurf detection statistics.

    This endpoint provides statistics about the smurf detection system,
    including total analyses, detection rates, and confidence distributions.

    Returns:
        DetectionStatsResponse with system-wide statistics

    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        logger.info("Retrieving detection statistics")

        stats = await detection_service.get_detection_stats()

        logger.info(
            "Detection statistics retrieved",
            total_analyses=stats.total_analyses,
            smurf_count=stats.smurf_count,
            detection_rate=stats.smurf_detection_rate,
        )

        return stats

    except Exception as e:
        logger.error("Failed to get detection stats", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get detection statistics"
        )

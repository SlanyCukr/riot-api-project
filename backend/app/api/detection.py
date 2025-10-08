"""
Smurf detection API endpoints.

This module provides REST API endpoints for smurf detection analysis,
including player analysis, detection history, statistics, and configuration.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List
import structlog

from ..schemas.detection import (
    DetectionResponse,
    DetectionRequest,
    DetectionStatsResponse,
    DetectionConfigResponse,
    BulkDetectionRequest,
    BulkDetectionResponse,
    DetailedDetectionResponse,
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
    limit: int = Query(10, ge=1, le=50, description="Number of historical results"),
    include_factors: bool = Query(True, description="Include detailed factor analysis"),
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
        List of DetectionResponse objects with historical analysis results

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


@router.get("/config", response_model=DetectionConfigResponse)
async def get_detection_config(detection_service: DetectionServiceDep):
    """
    Get current detection configuration.

    This endpoint returns the current configuration for the smurf detection
    system, including thresholds, weights, and algorithm version.

    Returns:
        DetectionConfigResponse with current configuration

    Raises:
        HTTPException: If configuration retrieval fails
    """
    try:
        logger.info("Retrieving detection configuration")

        config = await detection_service.get_config()

        logger.info(
            "Detection configuration retrieved",
            version=config.analysis_version,
            thresholds_count=len(config.thresholds),
            weights_count=len(config.weights),
        )

        return config

    except Exception as e:
        logger.error("Failed to get detection config", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get detection configuration"
        )


@router.post("/bulk-analyze", response_model=BulkDetectionResponse)
async def bulk_analyze_players(
    request: BulkDetectionRequest,
    background_tasks: BackgroundTasks,
    detection_service: DetectionServiceDep,
):
    """
    Perform bulk smurf detection analysis on multiple players.

    This endpoint allows analyzing multiple players simultaneously,
    which is useful for batch processing and system-wide analysis.

    Args:
        request: Bulk detection request with player list and configuration
        background_tasks: FastAPI background tasks for long-running operations

    Returns:
        BulkDetectionResponse with analysis results and summary

    Raises:
        HTTPException: If bulk analysis fails
    """
    try:
        logger.info(
            "Starting bulk smurf detection analysis",
            players_count=len(request.puuids),
            max_concurrent=request.max_concurrent,
        )

        # Validate player count
        if len(request.puuids) > 50:
            raise HTTPException(
                status_code=400, detail="Maximum 50 players allowed per bulk request"
            )

        result = await detection_service.analyze_bulk_players(
            puuids=request.puuids, analysis_config=request.analysis_config
        )

        logger.info(
            "Bulk detection analysis completed",
            total_players=len(request.puuids),
            successful=result.successful_analyses,
            failed=result.failed_analyses,
            processing_time=result.processing_time_seconds,
        )

        return result

    except ValueError as e:
        logger.error("Bulk analysis validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Bulk analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Bulk analysis failed")


@router.get("/player/{puuid}/detailed", response_model=DetailedDetectionResponse)
async def get_detailed_detection(
    puuid: str,
    detection_service: DetectionServiceDep,
    include_trends: bool = Query(True, description="Include trend analysis"),
    include_recommendations: bool = Query(True, description="Include recommendations"),
):
    """
    Get detailed smurf detection analysis with additional insights.

    This endpoint provides comprehensive analysis including trend analysis,
    recommendations, and detailed signal breakdowns.

    Args:
        puuid: Player PUUID
        include_trends: Whether to include trend analysis
        include_recommendations: Whether to include recommendations

    Returns:
        DetailedDetectionResponse with comprehensive analysis

    Raises:
        HTTPException: If detailed analysis fails
    """
    try:
        logger.info("Retrieving detailed detection analysis", puuid=puuid)

        # Get basic detection result
        basic_result = await detection_service.analyze_player(puuid=puuid)

        # For now, return enhanced version of basic result
        # Additional features like trends and recommendations would be implemented here
        detailed_result = DetailedDetectionResponse(
            **basic_result.dict(),
            signals=[],  # Would be populated with detailed signal analysis
            recommendations=[],  # Would be populated with AI recommendations
            trend_analysis=None,  # Would be populated with trend analysis
            player_context={},  # Would be populated with additional context
        )

        logger.info(
            "Detailed detection analysis completed",
            puuid=puuid,
            is_smurf=detailed_result.is_smurf,
            detection_score=detailed_result.detection_score,
        )

        return detailed_result

    except ValueError as e:
        logger.error(
            "Player not found for detailed analysis", puuid=puuid, error=str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Detailed analysis failed", puuid=puuid, error=str(e))
        raise HTTPException(status_code=500, detail="Detailed analysis failed")


@router.get("/health")
async def detection_health_check():
    """
    Health check endpoint for the smurf detection service.

    Returns:
        Health status of the detection service
    """
    return {
        "status": "healthy",
        "service": "smurf-detection",
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",
    }


@router.get("/player/{puuid}/exists")
async def check_player_analysis_exists(
    puuid: str, detection_service: DetectionServiceDep
):
    """
    Check if a player has existing smurf detection analysis.

    Args:
        puuid: Player PUUID

    Returns:
        Dictionary with existence check result and recent analysis info
    """
    try:
        recent_analysis = await detection_service._get_recent_detection(puuid, hours=24)

        if recent_analysis:
            return {
                "exists": True,
                "last_analysis": recent_analysis.last_analysis.isoformat(),
                "is_smurf": recent_analysis.is_smurf,
                "detection_score": float(recent_analysis.smurf_score),
                "confidence_level": recent_analysis.confidence,
            }
        else:
            return {
                "exists": False,
                "last_analysis": None,
                "message": "No recent analysis found for player",
            }

    except Exception as e:
        logger.error(
            "Failed to check player analysis existence", puuid=puuid, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail="Failed to check analysis existence"
        )

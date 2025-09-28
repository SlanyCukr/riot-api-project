"""
Pydantic schemas for smurf detection API.

This module contains the request/response schemas for the smurf detection
API endpoints, including detection requests, responses, and statistics.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class DetectionFactor(BaseModel):
    """Individual detection factor with its analysis."""
    name: str = Field(..., description="Factor name (e.g., 'win_rate', 'kda')")
    value: float = Field(..., description="Factor value")
    meets_threshold: bool = Field(..., description="Whether factor meets smurf threshold")
    weight: float = Field(..., description="Factor weight in overall scoring")
    description: str = Field(..., description="Human-readable description")
    score: float = Field(..., description="Normalized score (0.0-1.0)")


class DetectionRequest(BaseModel):
    """Request for smurf detection analysis."""
    puuid: str = Field(..., description="Player PUUID to analyze")
    min_games: int = Field(30, ge=10, le=100, description="Minimum games for analysis")
    queue_filter: Optional[int] = Field(None, description="Filter by queue ID")
    time_period_days: Optional[int] = Field(None, ge=1, le=365, description="Time period in days")
    force_reanalyze: bool = Field(False, description="Force re-analysis even if recent analysis exists")


class DetectionResponse(BaseModel):
    """Response from smurf detection analysis."""
    puuid: str = Field(..., description="Player PUUID")
    is_smurf: bool = Field(..., description="Whether player is detected as smurf")
    detection_score: float = Field(..., description="Overall detection score (0.0-1.0)")
    confidence_level: str = Field(..., description="Confidence level (none/low/medium/high)")
    factors: List[DetectionFactor] = Field(..., description="Individual factor analysis")
    reason: str = Field(..., description="Human-readable explanation")
    sample_size: int = Field(..., description="Number of matches analyzed")
    analysis_time_seconds: Optional[float] = Field(None, description="Analysis time in seconds")
    created_at: Optional[datetime] = Field(None, description="Analysis timestamp")

    class Config:
        from_attributes = True


class DetectionStatsResponse(BaseModel):
    """Overall smurf detection statistics."""
    total_analyses: int = Field(..., description="Total number of analyses performed")
    smurf_count: int = Field(..., description="Number of smurfs detected")
    smurf_detection_rate: float = Field(..., description="Percentage of analyses that detected smurfs")
    average_score: float = Field(..., description="Average detection score")
    confidence_distribution: Dict[str, int] = Field(..., description="Distribution of confidence levels")
    factor_trigger_rates: Dict[str, float] = Field(..., description="Rate at which each factor triggers detection")
    queue_type_distribution: Dict[str, int] = Field(..., description="Distribution by queue type")
    last_analysis: Optional[datetime] = Field(None, description="Last analysis timestamp")


class DetectionConfigResponse(BaseModel):
    """Current detection configuration."""
    thresholds: Dict[str, float] = Field(..., description="Current detection thresholds")
    weights: Dict[str, float] = Field(..., description="Factor weights")
    min_games_required: int = Field(..., description="Minimum games required")
    analysis_version: str = Field(..., description="Algorithm version")
    last_updated: datetime = Field(..., description="When config was last updated")


class DetectionHistoryRequest(BaseModel):
    """Request for detection history."""
    puuid: str = Field(..., description="Player PUUID")
    limit: int = Field(10, ge=1, le=50, description="Number of historical results")
    include_factors: bool = Field(True, description="Include detailed factor analysis")


class BulkDetectionRequest(BaseModel):
    """Request for bulk smurf detection analysis."""
    puuids: List[str] = Field(..., description="List of player PUUIDs to analyze")
    analysis_config: DetectionRequest = Field(..., description="Analysis configuration")
    max_concurrent: int = Field(5, ge=1, le=10, description="Maximum concurrent analyses")


class BulkDetectionResponse(BaseModel):
    """Response from bulk smurf detection analysis."""
    results: List[DetectionResponse] = Field(..., description="Individual analysis results")
    summary: Dict[str, Any] = Field(..., description="Bulk analysis summary")
    processing_time_seconds: float = Field(..., description="Total processing time")
    successful_analyses: int = Field(..., description="Number of successful analyses")
    failed_analyses: int = Field(..., description="Number of failed analyses")


class DetectionSignalAnalysis(BaseModel):
    """Detailed analysis of individual detection signals."""
    signal_name: str = Field(..., description="Name of the detection signal")
    signal_value: float = Field(..., description="Calculated signal value")
    threshold: float = Field(..., description="Threshold used for this signal")
    triggered: bool = Field(..., description="Whether signal was triggered")
    contribution: float = Field(..., description="Contribution to overall score")
    metadata: Dict[str, Any] = Field(..., description="Additional signal metadata")


class DetectionTrendAnalysis(BaseModel):
    """Analysis of detection trends over time."""
    puuid: str = Field(..., description="Player PUUID")
    trend_direction: str = Field(..., description="Trend direction (improving/stable/declining)")
    score_change: float = Field(..., description="Change in detection score")
    factor_changes: Dict[str, float] = Field(..., description="Changes in individual factors")
    time_period_days: int = Field(..., description="Time period analyzed")
    analyses_compared: int = Field(..., description="Number of analyses compared")


class DetectionRecommendation(BaseModel):
    """Recommendation based on detection analysis."""
    type: str = Field(..., description="Recommendation type")
    priority: str = Field(..., description="Priority level")
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed description")
    action_items: List[str] = Field(..., description="Suggested actions")


class DetailedDetectionResponse(DetectionResponse):
    """Extended detection response with additional details."""
    signals: List[DetectionSignalAnalysis] = Field(..., description="Detailed signal analysis")
    recommendations: List[DetectionRecommendation] = Field(..., description="Detection recommendations")
    trend_analysis: Optional[DetectionTrendAnalysis] = Field(None, description="Trend analysis")
    player_context: Dict[str, Any] = Field(..., description="Additional player context")


class DetectionCalibrationRequest(BaseModel):
    """Request for detection algorithm calibration."""
    known_smurfs: List[str] = Field(..., description="List of known smurf PUUIDs")
    known_legitimate: List[str] = Field(..., description="List of known legitimate players")
    optimization_target: str = Field(..., description="Target metric to optimize")
    validation_split: float = Field(0.2, ge=0.1, le=0.5, description="Validation split ratio")


class DetectionCalibrationResponse(BaseModel):
    """Response from detection algorithm calibration."""
    optimized_thresholds: Dict[str, float] = Field(..., description="Optimized thresholds")
    optimized_weights: Dict[str, float] = Field(..., description="Optimized weights")
    performance_metrics: Dict[str, float] = Field(..., description="Calibration performance metrics")
    validation_results: Dict[str, Any] = Field(..., description="Validation results")
    calibration_timestamp: datetime = Field(..., description="When calibration was performed")


class DetectionExportRequest(BaseModel):
    """Request for detection data export."""
    format: str = Field(..., description="Export format (json/csv)")
    filters: Dict[str, Any] = Field(..., description="Export filters")
    include_signals: bool = Field(True, description="Include detailed signals")
    include_recommendations: bool = Field(True, description="Include recommendations")


class DetectionExportResponse(BaseModel):
    """Response from detection data export."""
    export_id: str = Field(..., description="Unique export identifier")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    status: str = Field(..., description="Export status")
    total_records: int = Field(..., description="Total records exported")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class DetectionAlertRequest(BaseModel):
    """Request for setting up detection alerts."""
    puuid: str = Field(..., description="Player PUUID to monitor")
    alert_threshold: float = Field(..., description="Score threshold for alerts")
    notification_channels: List[str] = Field(..., description="Notification channels")
    alert_frequency: str = Field(..., description="Alert frequency")


class DetectionAlertResponse(BaseModel):
    """Response from setting up detection alerts."""
    alert_id: str = Field(..., description="Unique alert identifier")
    puuid: str = Field(..., description="Monitored player PUUID")
    threshold: float = Field(..., description="Alert threshold")
    status: str = Field(..., description="Alert status")
    created_at: datetime = Field(..., description="When alert was created")
    last_triggered: Optional[datetime] = Field(None, description="When alert was last triggered")
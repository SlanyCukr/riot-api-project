"""
Pydantic schemas for player analysis API.

This module contains the request/response schemas for the player analysis
API endpoints, including detection requests, responses, and statistics.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DetectionFactor(BaseModel):
    """Individual detection factor with its analysis."""

    name: str = Field(..., description="Factor name (e.g., 'win_rate', 'kda')")
    value: float = Field(..., description="Factor value")
    meets_threshold: bool = Field(
        ..., description="Whether factor meets smurf threshold"
    )
    weight: float = Field(..., description="Factor weight in overall scoring")
    description: str = Field(..., description="Human-readable description")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score (0.0-1.0)")


class DetectionRequest(BaseModel):
    """Request for player analysis."""

    puuid: str = Field(..., description="Player PUUID to analyze")
    min_games: int = Field(30, ge=10, le=100, description="Minimum games for analysis")
    queue_filter: Optional[int] = Field(None, description="Filter by queue ID")
    time_period_days: Optional[int] = Field(
        None, ge=1, le=365, description="Time period in days"
    )
    force_reanalyze: bool = Field(
        False, description="Force re-analysis even if recent analysis exists"
    )


class DetectionResponse(BaseModel):
    """Response from player analysis."""

    puuid: str = Field(..., description="Player PUUID")
    is_smurf: bool = Field(..., description="Whether player is detected as smurf")
    detection_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall detection score (0.0-1.0)"
    )
    confidence_level: str = Field(
        ..., description="Confidence level (none/low/medium/high)"
    )
    factors: List[DetectionFactor] = Field(
        ..., description="Individual factor analysis"
    )
    sample_size: int = Field(..., description="Number of matches analyzed")
    created_at: Optional[datetime] = Field(None, description="Analysis timestamp")
    reason: Optional[str] = Field(
        None, description="Human-readable reason for detection"
    )
    analysis_time_seconds: Optional[float] = Field(
        None, description="Time taken for analysis"
    )

    model_config = ConfigDict(from_attributes=True)


class DetectionExistsResponse(BaseModel):
    """Response indicating whether detection analysis exists for a player."""

    exists: bool = Field(..., description="Whether detection analysis exists")
    last_analysis: Optional[datetime] = Field(
        None, description="Timestamp of last analysis"
    )
    is_smurf: Optional[bool] = Field(
        None, description="Whether player is detected as smurf"
    )
    detection_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall detection score (0.0-1.0)"
    )
    confidence_level: Optional[str] = Field(
        None, description="Confidence level (none/low/medium/high)"
    )

    model_config = ConfigDict(from_attributes=True)

"""Schemas for matchmaking analysis requests and responses."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MatchmakingAnalysisRequest(BaseModel):
    """Request to start a matchmaking analysis."""

    puuid: str = Field(..., description="Player PUUID to analyze")


class MatchmakingAnalysisResults(BaseModel):
    """Results of matchmaking analysis."""

    team_avg_winrate: float = Field(
        ...,
        description="Average winrate of teammates",
        ge=0.0,
        le=1.0,
    )
    enemy_avg_winrate: float = Field(
        ...,
        description="Average winrate of enemies",
        ge=0.0,
        le=1.0,
    )
    matches_analyzed: int = Field(
        ...,
        description="Number of matches analyzed",
        ge=0,
    )


class MatchmakingAnalysisResponse(BaseModel):
    """Response containing matchmaking analysis data."""

    id: int
    puuid: str
    status: str
    progress: int
    total_requests: int
    estimated_minutes_remaining: int
    results: Optional[MatchmakingAnalysisResults] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class MatchmakingAnalysisStatusResponse(BaseModel):
    """Quick status check response."""

    id: int
    status: str
    progress: int
    total_requests: int
    estimated_minutes_remaining: int
    results: Optional[MatchmakingAnalysisResults] = None
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True

"""Schemas for matchmaking analysis requests and responses."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.enums import JobStatus


class MatchmakingAnalysisCreate(BaseModel):
    """Schema for creating a new matchmaking analysis."""

    user_id: str = Field(..., description="User ID requesting the analysis")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis parameters"
    )


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

    id: str
    user_id: str
    job_type: str
    status: str
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    matches_analyzed: int = 0
    winrate: Optional[float] = None
    avg_rank_difference: Optional[float] = None
    fairness_score: Optional[float] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class MatchmakingAnalysisStatus(BaseModel):
    """Enumeration for analysis status."""

    # Map to JobStatus enum values
    @classmethod
    def from_job_status(cls, job_status: JobStatus) -> str:
        """Convert JobStatus to string representation."""
        return job_status.value


class MatchmakingAnalysisStatusResponse(BaseModel):
    """Quick status check response."""

    id: str
    user_id: str
    job_type: str
    status: str
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    matches_analyzed: int = 0
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class MatchmakingAnalysisListResponse(BaseModel):
    """Response containing a list of matchmaking analyses."""

    analyses: list[MatchmakingAnalysisResponse] = Field(
        default_factory=list, description="List of analyses"
    )

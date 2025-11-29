"""Schemas for matchmaking analysis requests and responses."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.enums import JobStatus


class MatchmakingAnalysisCreate(BaseModel):
    """Schema for creating a new matchmaking analysis."""

    user_id: str = Field(..., description="User ID requesting the analysis")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis parameters"
    )


class MatchmakingAnalysisRequest(BaseModel):
    """Request to start a matchmaking analysis."""

    puuid: str = Field(..., description="Player PUUID to analyze", min_length=1, max_length=100)
    region: str = Field(default="na", description="Region for analysis", min_length=2, max_length=10)
    match_count: int = Field(default=50, description="Number of matches to analyze", ge=1, le=100)

    @field_validator('puuid')
    @classmethod
    def validate_puuid(cls, v: str) -> str:
        """Validate PUUID format.

        PUUIDs are alphanumeric strings with dashes and underscores.
        """
        v = v.strip()
        if not v:
            raise ValueError("PUUID cannot be empty")

        # PUUID should be alphanumeric with dashes and underscores
        if not all(c.isalnum() or c in ('-', '_') for c in v):
            raise ValueError(
                "PUUID must contain only alphanumeric characters, dashes, and underscores"
            )

        # Typical PUUID length is around 78 characters
        if len(v) < 10 or len(v) > 100:
            raise ValueError("PUUID length must be between 10 and 100 characters")

        return v

    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate and normalize region format.

        Supported regions: na, euw, eune, kr, br, jp, las, lan, oce, tr, ru
        """
        v = v.strip().lower()
        if not v:
            raise ValueError("Region cannot be empty")

        # Valid Riot API regions
        valid_regions = {
            "na", "na1",
            "euw", "euw1",
            "eune", "eun1",
            "kr",
            "br", "br1",
            "jp", "jp1",
            "las", "la1",
            "lan", "la2",
            "oce", "oc1",
            "tr", "tr1",
            "ru",
        }

        if v not in valid_regions:
            raise ValueError(
                f"Invalid region '{v}'. Must be one of: {', '.join(sorted(valid_regions))}"
            )

        return v


class AnalysisParameters(BaseModel):
    """Validated parameters for matchmaking analysis (for internal use)."""

    region: str = Field(default="na", description="Region for analysis", min_length=2, max_length=10)
    puuid: str = Field(..., description="Player PUUID to analyze", min_length=10, max_length=100)
    match_count: int = Field(default=50, description="Number of matches to analyze", ge=1, le=100)

    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate and normalize region format."""
        v = v.strip().lower()
        if not v:
            raise ValueError("Region cannot be empty")

        # Valid Riot API regions
        valid_regions = {
            "na", "na1",
            "euw", "euw1",
            "eune", "eun1",
            "kr",
            "br", "br1",
            "jp", "jp1",
            "las", "la1",
            "lan", "la2",
            "oce", "oc1",
            "tr", "tr1",
            "ru",
        }

        if v not in valid_regions:
            raise ValueError(
                f"Invalid region '{v}'. Must be one of: {', '.join(sorted(valid_regions))}"
            )

        return v

    @field_validator('puuid')
    @classmethod
    def validate_puuid(cls, v: str) -> str:
        """Validate PUUID format."""
        v = v.strip()
        if not v:
            raise ValueError("PUUID cannot be empty")

        # PUUID should be alphanumeric with dashes and underscores
        if not all(c.isalnum() or c in ('-', '_') for c in v):
            raise ValueError(
                "PUUID must contain only alphanumeric characters, dashes, and underscores"
            )

        if len(v) < 10 or len(v) > 100:
            raise ValueError("PUUID length must be between 10 and 100 characters")

        return v


class MatchDataValidation(BaseModel):
    """Schema for match data validation utilities."""

    @classmethod
    def validate_match_structure(cls, match_data: dict) -> bool:
        """Validate match data structure."""
        if not isinstance(match_data, dict):
            return False

        info = match_data.get("info")
        if not isinstance(info, dict):
            return False

        participants = info.get("participants")
        if not isinstance(participants, list) or len(participants) == 0:
            return False

        return True

    @classmethod
    def filter_valid_matches(cls, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and return only valid matches."""
        valid_matches = []
        for match in matches:
            if isinstance(match, dict) and match.get("matchId"):
                valid_matches.append(match)
        return valid_matches


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

    model_config = ConfigDict(from_attributes=True)

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


class MatchmakingAnalysisStatus(BaseModel):
    """Enumeration for analysis status."""

    # Map to JobStatus enum values
    @classmethod
    def from_job_status(cls, job_status: JobStatus) -> str:
        """Convert JobStatus to string representation."""
        return job_status.value


class MatchmakingAnalysisStatusResponse(BaseModel):
    """Quick status check response."""

    model_config = ConfigDict(from_attributes=True)

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


class MatchmakingAnalysisListResponse(BaseModel):
    """Response containing a list of matchmaking analyses."""

    analyses: list[MatchmakingAnalysisResponse] = Field(
        default_factory=list, description="List of analyses"
    )

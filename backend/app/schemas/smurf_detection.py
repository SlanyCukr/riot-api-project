"""
Pydantic schemas for SmurfDetection model.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class SmurfSignalType(str, Enum):
    """Types of smurf detection signals."""
    HIGH_WIN_RATE = "high_win_rate"
    HIGH_KDA = "high_kda"
    LOW_ACCOUNT_LEVEL = "low_account_level"
    RANK_DISCREPANCY = "rank_discrepancy"
    RAPID_RANK_PROGRESSION = "rapid_rank_progression"
    CONSISTENT_HIGH_PERFORMANCE = "consistent_high_performance"
    CHAMPION_POOL_BREADTH = "champion_pool_breadth"
    ROLE_VERSATILITY = "role_versatility"
    UNUSUAL_TIMING_PATTERNS = "unusual_timing_patterns"
    LOW_NORMAL_GAMES = "low_normal_games"


class SmurfConfidence(str, Enum):
    """Confidence levels for smurf detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SmurfDetectionBase(BaseModel):
    """Base SmurfDetection schema with common attributes."""
    puuid: uuid.UUID = Field(..., description="Reference to the player being analyzed")
    is_smurf: bool = Field(False, description="Whether the player is detected as a smurf")
    confidence: Optional[SmurfConfidence] = Field(None, description="Confidence level in the smurf detection")
    smurf_score: Decimal = Field(0.0, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Overall smurf score")
    win_rate_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Win rate based smurf score component")
    kda_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="KDA based smurf score component")
    account_level_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Account level based smurf score component")
    rank_discrepancy_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Rank discrepancy based smurf score component")
    games_analyzed: int = Field(0, ge=0, description="Number of games analyzed for this detection")
    queue_type: Optional[str] = Field(None, max_length=32, description="Queue type analyzed")
    time_period_days: Optional[int] = Field(None, ge=1, description="Time period in days analyzed")
    win_rate_threshold: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Win rate threshold used for detection")
    kda_threshold: Optional[Decimal] = Field(None, ge=0.0, max_digits=5, decimal_places=3, description="KDA threshold used for detection")
    account_level: Optional[int] = Field(None, ge=1, description="Account level at time of analysis")
    current_tier: Optional[str] = Field(None, max_length=16, description="Current tier at time of analysis")
    current_rank: Optional[str] = Field(None, max_length=4, description="Current rank at time of analysis")
    peak_tier: Optional[str] = Field(None, max_length=16, description="Peak tier observed")
    peak_rank: Optional[str] = Field(None, max_length=4, description="Peak rank observed")
    analysis_version: Optional[str] = Field(None, max_length=16, description="Version of the smurf detection algorithm")
    false_positive_reported: bool = Field(False, description="Whether this detection was reported as false positive")
    manually_verified: bool = Field(False, description="Whether this detection was manually verified")
    notes: Optional[str] = Field(None, description="Additional notes about this detection")


class SmurfDetectionCreate(SmurfDetectionBase):
    """Schema for creating a new SmurfDetection."""
    pass


class SmurfDetectionUpdate(BaseModel):
    """Schema for updating a SmurfDetection."""
    is_smurf: Optional[bool] = Field(None, description="Whether the player is detected as a smurf")
    confidence: Optional[SmurfConfidence] = Field(None, description="Confidence level in the smurf detection")
    smurf_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Overall smurf score")
    win_rate_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Win rate based smurf score component")
    kda_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="KDA based smurf score component")
    account_level_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Account level based smurf score component")
    rank_discrepancy_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Rank discrepancy based smurf score component")
    games_analyzed: Optional[int] = Field(None, ge=0, description="Number of games analyzed for this detection")
    queue_type: Optional[str] = Field(None, max_length=32, description="Queue type analyzed")
    time_period_days: Optional[int] = Field(None, ge=1, description="Time period in days analyzed")
    win_rate_threshold: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Win rate threshold used for detection")
    kda_threshold: Optional[Decimal] = Field(None, ge=0.0, max_digits=5, decimal_places=3, description="KDA threshold used for detection")
    account_level: Optional[int] = Field(None, ge=1, description="Account level at time of analysis")
    current_tier: Optional[str] = Field(None, max_length=16, description="Current tier at time of analysis")
    current_rank: Optional[str] = Field(None, max_length=4, description="Current rank at time of analysis")
    peak_tier: Optional[str] = Field(None, max_length=16, description="Peak tier observed")
    peak_rank: Optional[str] = Field(None, max_length=4, description="Peak rank observed")
    analysis_version: Optional[str] = Field(None, max_length=16, description="Version of the smurf detection algorithm")
    false_positive_reported: Optional[bool] = Field(None, description="Whether this detection was reported as false positive")
    manually_verified: Optional[bool] = Field(None, description="Whether this detection was manually verified")
    notes: Optional[str] = Field(None, description="Additional notes about this detection")


class SmurfDetectionResponse(SmurfDetectionBase):
    """Schema for SmurfDetection response."""
    id: int = Field(..., description="Auto-incrementing primary key")
    created_at: datetime = Field(..., description="When this smurf detection was created")
    updated_at: datetime = Field(..., description="When this smurf detection was last updated")
    last_analysis: datetime = Field(..., description="When the last analysis was performed")
    display_confidence: str = Field(..., description="Display-friendly confidence level")
    risk_level: str = Field(..., description="Risk level based on smurf score")
    top_signals: List[str] = Field(..., description="Top contributing signals")

    model_config = ConfigDict(from_attributes=True)


class SmurfDetectionListResponse(BaseModel):
    """Schema for paginated SmurfDetection list response."""
    detections: list[SmurfDetectionResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class SmurfDetectionSearchRequest(BaseModel):
    """Schema for smurf detection search requests."""
    puuid: Optional[uuid.UUID] = Field(None, description="Filter by player PUUID")
    is_smurf: Optional[bool] = Field(None, description="Filter by smurf detection status")
    confidence: Optional[SmurfConfidence] = Field(None, description="Filter by confidence level")
    queue_type: Optional[str] = Field(None, max_length=32, description="Filter by queue type")
    min_smurf_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Minimum smurf score")
    max_smurf_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, max_digits=5, decimal_places=3, description="Maximum smurf score")
    false_positive_reported: Optional[bool] = Field(None, description="Filter by false positive reports")
    manually_verified: Optional[bool] = Field(None, description="Filter by manual verification status")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")


class SmurfDetectionAnalysis(BaseModel):
    """Schema for smurf detection analysis request."""
    puuid: uuid.UUID = Field(..., description="Player to analyze")
    queue_type: str = Field(..., max_length=32, description="Queue type to analyze")
    games_to_analyze: int = Field(30, ge=10, le=100, description="Number of games to analyze")
    time_period_days: Optional[int] = Field(None, ge=1, description="Time period in days to analyze")
    win_rate_threshold: Decimal = Field(0.65, ge=0.5, le=1.0, max_digits=5, decimal_places=3, description="Win rate threshold")
    kda_threshold: Decimal = Field(3.0, ge=1.0, max_digits=5, decimal_places=2, description="KDA threshold")
    force_reanalyze: bool = Field(False, description="Whether to force reanalysis")


class SmurfDetectionAnalysisResponse(BaseModel):
    """Schema for smurf detection analysis response."""
    puuid: uuid.UUID
    analysis_completed: bool
    detection_result: Optional[SmurfDetectionResponse] = None
    analysis_time_seconds: Optional[float] = None
    games_analyzed: int
    signals_found: List[str]
    recommendations: List[str]

    model_config = ConfigDict(from_attributes=True)


class SmurfDetectionStatsResponse(BaseModel):
    """Schema for smurf detection statistics response."""
    total_players_analyzed: int
    total_smurfs_detected: int
    smurf_detection_rate: float
    average_smurf_score: float
    confidence_distribution: dict
    signal_frequency: dict
    queue_type_distribution: dict

    model_config = ConfigDict(from_attributes=True)


class SmurfDetectionBulkRequest(BaseModel):
    """Schema for bulk smurf detection analysis."""
    puuids: List[uuid.UUID] = Field(..., min_length=1, max_length=50, description="List of player PUUIDs to analyze")
    analysis_config: SmurfDetectionAnalysis


class SmurfDetectionBulkResponse(BaseModel):
    """Schema for bulk smurf detection response."""
    results: List[SmurfDetectionAnalysisResponse]
    summary: dict
    processing_time_seconds: float

    model_config = ConfigDict(from_attributes=True)
"""
Pydantic schemas for Match model.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, computed_field


class MatchBase(BaseModel):
    """Base Match schema with common attributes."""
    platform_id: str = Field(..., max_length=8, description="Platform where the match was played")
    game_creation: int = Field(..., description="Game creation timestamp in milliseconds since epoch")
    game_duration: int = Field(..., ge=0, description="Game duration in seconds")
    queue_id: int = Field(..., description="Queue type ID")
    game_version: str = Field(..., max_length=32, description="Game version")
    map_id: int = Field(..., description="Map ID")
    game_mode: Optional[str] = Field(None, max_length=32, description="Game mode")
    game_type: Optional[str] = Field(None, max_length=32, description="Game type")
    game_end_timestamp: Optional[int] = Field(None, description="Game end timestamp in milliseconds since epoch")
    tournament_id: Optional[str] = Field(None, max_length=64, description="Tournament ID")
    is_processed: bool = Field(False, description="Whether this match has been processed for smurf detection")
    processing_error: Optional[str] = Field(None, max_length=256, description="Error message if match processing failed")


class MatchCreate(MatchBase):
    """Schema for creating a new Match."""
    match_id: str = Field(..., max_length=64, description="Unique match identifier from Riot API")


class MatchUpdate(BaseModel):
    """Schema for updating a Match."""
    game_duration: Optional[int] = Field(None, ge=0, description="Game duration in seconds")
    game_end_timestamp: Optional[int] = Field(None, description="Game end timestamp in milliseconds since epoch")
    game_mode: Optional[str] = Field(None, max_length=32, description="Game mode")
    game_type: Optional[str] = Field(None, max_length=32, description="Game type")
    tournament_id: Optional[str] = Field(None, max_length=64, description="Tournament ID")
    is_processed: Optional[bool] = Field(None, description="Whether this match has been processed for smurf detection")
    processing_error: Optional[str] = Field(None, max_length=256, description="Error message if match processing failed")


class MatchResponse(MatchBase):
    """Schema for Match response."""
    match_id: str = Field(..., max_length=64, description="Unique match identifier from Riot API")
    created_at: datetime = Field(..., description="When this match record was created in our database")
    updated_at: datetime = Field(..., description="When this match record was last updated")
    game_start_datetime: Optional[datetime] = Field(None, description="Game creation as a datetime object")
    game_end_datetime: Optional[datetime] = Field(None, description="Game end as a datetime object")
    patch_version: Optional[str] = Field(None, description="Extracted patch version from game version")

    @computed_field
    @property
    def is_ranked_match(self) -> bool:
        """Whether this is a ranked match."""
        return self.queue_id in [420, 440]  # Ranked Solo/Duo and Ranked Flex

    @computed_field
    @property
    def is_normal_match(self) -> bool:
        """Whether this is a normal match."""
        return self.queue_id in [400, 430]  # Normal Draft and Blind Pick

    model_config = ConfigDict(from_attributes=True)


class MatchListResponse(BaseModel):
    """Schema for paginated Match list response."""
    matches: List[MatchResponse]
    total: int = Field(..., description="Total matches available")
    start: int = Field(..., description="Start index")
    count: int = Field(..., description="Number of matches returned")

    model_config = ConfigDict(from_attributes=True)


class MatchStatsResponse(BaseModel):
    """Schema for player match statistics response."""
    puuid: str = Field(..., description="Player PUUID")
    total_matches: int = Field(..., ge=0, description="Total matches analyzed")
    wins: int = Field(..., ge=0, description="Number of wins")
    losses: int = Field(..., ge=0, description="Number of losses")
    win_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate (0.0 to 1.0)")
    avg_kills: float = Field(..., ge=0.0, description="Average kills per match")
    avg_deaths: float = Field(..., ge=0.0, description="Average deaths per match")
    avg_assists: float = Field(..., ge=0.0, description="Average assists per match")
    avg_kda: float = Field(..., ge=0.0, description="Average KDA ratio")
    avg_cs: float = Field(..., ge=0.0, description="Average CS per match")
    avg_vision_score: float = Field(..., ge=0.0, description="Average vision score")

    model_config = ConfigDict(from_attributes=True)


class MatchSearchRequest(BaseModel):
    """Schema for match search requests."""
    queue_id: Optional[int] = Field(None, description="Queue type ID to filter by")
    platform_id: Optional[str] = Field(None, max_length=8, description="Platform to filter by")
    game_version: Optional[str] = Field(None, max_length=32, description="Game version to filter by")
    start_time: Optional[int] = Field(None, description="Start time in milliseconds since epoch")
    end_time: Optional[int] = Field(None, description="End time in milliseconds since epoch")
    is_processed: Optional[bool] = Field(None, description="Filter by processing status")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")


class MatchBulkRequest(BaseModel):
    """Schema for bulk match operations."""
    match_ids: list[str] = Field(..., min_length=1, max_length=100, description="List of match IDs")


class MatchBulkResponse(BaseModel):
    """Schema for bulk match operations response."""
    matches: list[MatchResponse]
    not_found: list[str]

    model_config = ConfigDict(from_attributes=True)


class MatchProcessingRequest(BaseModel):
    """Schema for match processing requests."""
    match_ids: list[str] = Field(..., min_length=1, max_length=50, description="List of match IDs to process")
    force_reprocess: bool = Field(False, description="Whether to reprocess already processed matches")


class MatchProcessingResponse(BaseModel):
    """Schema for match processing response."""
    processed_count: int
    failed_count: int
    errors: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
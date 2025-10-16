"""Pydantic response schemas for Match model."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class MatchResponse(BaseModel):
    """Schema for Match response."""

    match_id: str = Field(
        ..., max_length=64, description="Unique match identifier from Riot API"
    )
    platform_id: str = Field(
        ..., max_length=8, description="Platform where the match was played"
    )
    game_creation: int = Field(
        ..., description="Game creation timestamp in milliseconds since epoch"
    )
    game_duration: int = Field(..., ge=0, description="Game duration in seconds")
    queue_id: int = Field(..., description="Queue type ID")
    game_version: str = Field(..., max_length=32, description="Game version")
    map_id: int = Field(..., description="Map ID")
    game_mode: Optional[str] = Field(None, max_length=32, description="Game mode")
    game_type: Optional[str] = Field(None, max_length=32, description="Game type")
    game_end_timestamp: Optional[int] = Field(
        None, description="Game end timestamp in milliseconds since epoch"
    )
    tournament_id: Optional[str] = Field(
        None, max_length=64, description="Tournament ID"
    )
    is_processed: bool = Field(
        False, description="Whether this match has been processed for smurf detection"
    )
    processing_error: Optional[str] = Field(
        None, max_length=256, description="Error message if match processing failed"
    )
    created_at: datetime = Field(
        ..., description="When this match record was created in our database"
    )
    updated_at: datetime = Field(
        ..., description="When this match record was last updated"
    )

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

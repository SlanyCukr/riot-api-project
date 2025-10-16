"""Pydantic schemas for Match model."""

from typing import Optional

from pydantic import BaseModel, Field


class MatchBase(BaseModel):
    """Base Match schema with common attributes."""

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


class MatchCreate(MatchBase):
    """Schema for creating a new Match."""

    match_id: str = Field(
        ..., max_length=64, description="Unique match identifier from Riot API"
    )


class MatchUpdate(BaseModel):
    """Schema for updating a Match."""

    game_duration: Optional[int] = Field(
        None, ge=0, description="Game duration in seconds"
    )
    game_end_timestamp: Optional[int] = Field(
        None, description="Game end timestamp in milliseconds since epoch"
    )
    game_mode: Optional[str] = Field(None, max_length=32, description="Game mode")
    game_type: Optional[str] = Field(None, max_length=32, description="Game type")
    tournament_id: Optional[str] = Field(
        None, max_length=64, description="Tournament ID"
    )
    is_processed: Optional[bool] = Field(
        None, description="Whether this match has been processed for smurf detection"
    )
    processing_error: Optional[str] = Field(
        None, max_length=256, description="Error message if match processing failed"
    )

"""Pydantic schemas for PlayerRank model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.core.enums import Tier


class PlayerRankBase(BaseModel):
    """Base PlayerRank schema with common attributes."""

    puuid: str = Field(
        ..., max_length=78, description="Reference to the player (Riot PUUID)"
    )
    queue_type: str = Field(..., max_length=32, description="Queue type")
    tier: Tier = Field(..., description="Rank tier")
    rank: Optional[str] = Field(None, max_length=4, description="Rank division")
    league_points: int = Field(0, ge=0, le=100, description="League points")
    wins: int = Field(0, ge=0, description="Number of wins")
    losses: int = Field(0, ge=0, description="Number of losses")
    veteran: bool = Field(False, description="Whether the player is a veteran")
    inactive: bool = Field(False, description="Whether the player is inactive")
    fresh_blood: bool = Field(False, description="Whether the player is fresh blood")
    hot_streak: bool = Field(False, description="Whether the player is on a hot streak")
    league_id: Optional[str] = Field(None, max_length=64, description="League ID")
    league_name: Optional[str] = Field(None, max_length=64, description="League name")
    season_id: Optional[str] = Field(
        None, max_length=16, description="Season identifier"
    )
    is_current: bool = Field(True, description="Whether this is the current rank")


class PlayerRankCreate(PlayerRankBase):
    """Schema for creating a new PlayerRank."""

    pass


class PlayerRankUpdate(BaseModel):
    """Schema for updating a PlayerRank - minimal fields for rank progression."""

    tier: Optional[Tier] = Field(None, description="Rank tier")
    rank: Optional[str] = Field(None, max_length=4, description="Rank division")
    league_points: Optional[int] = Field(
        None, ge=0, le=100, description="League points"
    )
    wins: Optional[int] = Field(None, ge=0, description="Number of wins")
    losses: Optional[int] = Field(None, ge=0, description="Number of losses")
    is_current: Optional[bool] = Field(
        None, description="Whether this is the current rank"
    )


class PlayerRankResponse(PlayerRankBase):
    """Schema for PlayerRank response."""

    id: int = Field(..., description="Auto-incrementing primary key")
    created_at: datetime = Field(..., description="When this rank record was created")
    updated_at: datetime = Field(
        ..., description="When this rank record was last updated"
    )
    win_rate: float = Field(..., description="Win rate as a percentage")
    total_games: int = Field(..., description="Total number of games played")
    display_rank: str = Field(..., description="Display rank (e.g., 'Gold II')")

    # Additional computed fields from domain logic
    is_provisional: Optional[bool] = Field(
        None, description="Whether this rank is provisional (new account)"
    )
    is_fresh: Optional[bool] = Field(
        None, description="Whether this rank record is recent"
    )
    mmr_estimate: Optional[float] = Field(
        None, description="Estimated MMR (Matchmaking Rating)"
    )

    model_config = ConfigDict(from_attributes=True)

"""Pydantic schemas for PlayerRank model."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class Tier(str, Enum):
    """League of Legends rank tiers."""

    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class Division(str, Enum):
    """League of Legends rank divisions."""

    I = "I"  # noqa: E741
    II = "II"
    III = "III"
    IV = "IV"


class QueueType(str, Enum):
    """League of Legends queue types."""

    RANKED_SOLO_5x5 = "RANKED_SOLO_5x5"
    RANKED_FLEX_5x5 = "RANKED_FLEX_SR"
    RANKED_FLEX_3x3 = "RANKED_FLEX_TT"


class PlayerRankBase(BaseModel):
    """Base PlayerRank schema with common attributes."""

    puuid: str = Field(
        ..., max_length=78, description="Reference to the player (Riot PUUID)"
    )
    queue_type: str = Field(..., max_length=32, description="Queue type")
    tier: str = Field(..., max_length=16, description="Rank tier")
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
    """Schema for updating a PlayerRank."""

    tier: Optional[str] = Field(None, max_length=16, description="Rank tier")
    rank: Optional[str] = Field(None, max_length=4, description="Rank division")
    league_points: Optional[int] = Field(
        None, ge=0, le=100, description="League points"
    )
    wins: Optional[int] = Field(None, ge=0, description="Number of wins")
    losses: Optional[int] = Field(None, ge=0, description="Number of losses")
    veteran: Optional[bool] = Field(None, description="Whether the player is a veteran")
    inactive: Optional[bool] = Field(None, description="Whether the player is inactive")
    fresh_blood: Optional[bool] = Field(
        None, description="Whether the player is fresh blood"
    )
    hot_streak: Optional[bool] = Field(
        None, description="Whether the player is on a hot streak"
    )
    league_id: Optional[str] = Field(None, max_length=64, description="League ID")
    league_name: Optional[str] = Field(None, max_length=64, description="League name")
    season_id: Optional[str] = Field(
        None, max_length=16, description="Season identifier"
    )
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
    display_lp: str = Field(..., description="Display LP (e.g., '75 LP')")
    is_high_tier: bool = Field(..., description="Whether this is a high tier rank")
    is_diamond_plus: bool = Field(..., description="Whether this is diamond or above")
    is_platinum_plus: bool = Field(..., description="Whether this is platinum or above")

    model_config = ConfigDict(from_attributes=True)


class PlayerRankListResponse(BaseModel):
    """Schema for paginated PlayerRank list response."""

    ranks: list[PlayerRankResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class PlayerRankSearchRequest(BaseModel):
    """Schema for player rank search requests."""

    puuid: Optional[uuid.UUID] = Field(None, description="Filter by player PUUID")
    queue_type: Optional[str] = Field(
        None, max_length=32, description="Filter by queue type"
    )
    tier: Optional[str] = Field(None, max_length=16, description="Filter by tier")
    rank: Optional[str] = Field(None, max_length=4, description="Filter by rank")
    is_current: Optional[bool] = Field(None, description="Filter by current ranks")
    min_league_points: Optional[int] = Field(
        None, ge=0, le=100, description="Minimum league points"
    )
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")


class RankDistributionResponse(BaseModel):
    """Schema for rank distribution response."""

    tier: str
    rank: Optional[str]
    count: int
    percentage: float
    average_league_points: float

    model_config = ConfigDict(from_attributes=True)


class PlayerRankHistoryResponse(BaseModel):
    """Schema for player rank history response."""

    puuid: uuid.UUID
    queue_type: str
    history: list[PlayerRankResponse]
    current_rank: Optional[PlayerRankResponse]
    peak_rank: Optional[PlayerRankResponse]

    model_config = ConfigDict(from_attributes=True)

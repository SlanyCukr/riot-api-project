"""Pydantic schemas for Player model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PlayerBase(BaseModel):
    """Base player schema with common fields."""

    puuid: str = Field(..., min_length=78, max_length=78, description="Player's PUUID")
    riot_id: Optional[str] = Field(None, description="Riot ID in format name#tag")
    tag_line: Optional[str] = Field(None, description="Riot tag line")
    summoner_name: str = Field(..., description="Current summoner name")
    platform: str = Field(..., description="Platform region")
    account_level: Optional[int] = Field(None, description="Account level")
    profile_icon_id: Optional[int] = Field(None, description="Profile icon ID")
    summoner_id: Optional[str] = Field(None, description="Encrypted summoner ID")


class PlayerCreate(PlayerBase):
    """Schema for creating a new player."""

    pass


class PlayerUpdate(BaseModel):
    """Schema for updating an existing player."""

    summoner_name: Optional[str] = None
    account_level: Optional[int] = None
    last_seen: Optional[datetime] = None


class PlayerResponse(PlayerBase):
    """Schema for player response data."""

    id: Optional[int] = Field(None, description="Database ID")
    created_at: datetime
    updated_at: datetime
    last_seen: datetime
    is_tracked: bool = Field(
        default=False,
        description="Whether this player is being tracked for automated updates",
    )
    is_analyzed: bool = Field(
        default=False,
        description="Whether this player has been analyzed for smurf/boosted detection",
    )
    last_ban_check: Optional[datetime] = Field(
        None, description="When this player was last checked for ban status"
    )

    # Computed fields from domain logic
    win_rate: Optional[float] = Field(
        None, description="Win rate as percentage (calculated from wins/losses)"
    )
    total_games: Optional[int] = Field(
        None, description="Total number of games (wins + losses)"
    )
    display_rank: Optional[str] = Field(
        None, description="Human-readable rank display (e.g., 'Gold II')"
    )
    is_new_account: Optional[bool] = Field(
        None, description="Whether this is considered a new account (< level 30)"
    )
    is_veteran: Optional[bool] = Field(
        None, description="Whether this is a veteran player (level 100+, 500+ games)"
    )
    is_high_elo: Optional[bool] = Field(
        None, description="Whether this player is in high ELO (Diamond+)"
    )
    needs_data_refresh: Optional[bool] = Field(
        None, description="Whether player data needs to be refreshed from Riot API"
    )
    smurf_likelihood: Optional[float] = Field(
        None, description="Probability score (0.0-1.0) that this is a smurf account"
    )

    model_config = ConfigDict(from_attributes=True)


class PlayerListResponse(BaseModel):
    """Schema for paginated Player list response."""

    players: list[PlayerResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

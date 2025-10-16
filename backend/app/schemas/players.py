"""Pydantic schemas for Player model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PlayerBase(BaseModel):
    """Base player schema with common fields."""

    puuid: str = Field(..., description="Player's PUUID")
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

    model_config = ConfigDict(from_attributes=True)


class PlayerListResponse(BaseModel):
    """Schema for paginated Player list response."""

    players: list[PlayerResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

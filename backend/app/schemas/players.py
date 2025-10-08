"""
Pydantic schemas for Player model.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PlayerBase(BaseModel):
    puuid: str = Field(..., description="Player's PUUID")
    riot_id: Optional[str] = Field(None, description="Riot ID in format name#tag")
    tag_line: Optional[str] = Field(None, description="Riot tag line")
    summoner_name: str = Field(..., description="Current summoner name")
    platform: str = Field(..., description="Platform region")
    account_level: int = Field(..., description="Account level")
    profile_icon_id: Optional[int] = Field(None, description="Profile icon ID")
    summoner_id: Optional[str] = Field(None, description="Encrypted summoner ID")


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    summoner_name: Optional[str] = None
    account_level: Optional[int] = None
    last_seen: Optional[datetime] = None


class PlayerResponse(PlayerBase):
    id: Optional[int] = Field(None, description="Database ID")
    created_at: datetime
    updated_at: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class PlayerSearchRequest(BaseModel):
    riot_id: Optional[str] = Field(None, description="Riot ID in format name#tag")
    summoner_name: Optional[str] = Field(None, description="Summoner name")
    platform: str = Field("eun1", description="Platform region")
    size: int = Field(
        10, ge=1, le=100, description="Maximum number of results to return"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"riot_id": "DangerousDan#EUW", "platform": "eun1", "size": 10}
        }
    )


class PlayerListResponse(BaseModel):
    """Schema for paginated Player list response."""

    players: list[PlayerResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class PlayerBulkRequest(BaseModel):
    """Schema for bulk player operations."""

    puuids: list[uuid.UUID] = Field(
        ..., min_length=1, max_length=100, description="List of player PUUIDs"
    )


class PlayerBulkResponse(BaseModel):
    """Schema for bulk player operations response."""

    players: list[PlayerResponse]
    not_found: list[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)

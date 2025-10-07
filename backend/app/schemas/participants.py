"""
Pydantic schemas for MatchParticipant model.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class MatchParticipantBase(BaseModel):
    """Base MatchParticipant schema with common attributes."""
    match_id: str = Field(..., max_length=64, description="Reference to the match this participant belongs to")
    puuid: uuid.UUID = Field(..., description="Reference to the player")
    summoner_name: str = Field(..., max_length=32, description="Summoner name at the time of the match")
    team_id: int = Field(..., description="Team ID (100 for blue side, 200 for red side)")
    champion_id: int = Field(..., description="Champion ID played by the participant")
    champion_name: str = Field(..., max_length=32, description="Champion name played by the participant")
    kills: int = Field(0, ge=0, description="Number of kills")
    deaths: int = Field(0, ge=0, description="Number of deaths")
    assists: int = Field(0, ge=0, description="Number of assists")
    win: bool = Field(..., description="Whether the participant won the match")
    gold_earned: int = Field(0, ge=0, description="Total gold earned")
    vision_score: int = Field(0, ge=0, description="Vision score")
    cs: int = Field(0, ge=0, description="Total creep score")
    kda: Optional[Decimal] = Field(None, ge=0, max_digits=5, decimal_places=2, description="Kill-death-assist ratio")
    champ_level: int = Field(1, ge=1, description="Champion level achieved")
    total_damage_dealt: int = Field(0, ge=0, description="Total damage dealt")
    total_damage_dealt_to_champions: int = Field(0, ge=0, description="Total damage dealt to champions")
    total_damage_taken: int = Field(0, ge=0, description="Total damage taken")
    total_heal: int = Field(0, ge=0, description="Total healing done")
    individual_position: Optional[str] = Field(None, max_length=16, description="Individual position")
    team_position: Optional[str] = Field(None, max_length=16, description="Team position")
    role: Optional[str] = Field(None, max_length=16, description="Role")


class MatchParticipantCreate(MatchParticipantBase):
    """Schema for creating a new MatchParticipant."""
    pass


class MatchParticipantUpdate(BaseModel):
    """Schema for updating a MatchParticipant."""
    summoner_name: Optional[str] = Field(None, max_length=32, description="Summoner name at the time of the match")
    team_id: Optional[int] = Field(None, description="Team ID")
    champion_id: Optional[int] = Field(None, description="Champion ID played by the participant")
    champion_name: Optional[str] = Field(None, max_length=32, description="Champion name played by the participant")
    kills: Optional[int] = Field(None, ge=0, description="Number of kills")
    deaths: Optional[int] = Field(None, ge=0, description="Number of deaths")
    assists: Optional[int] = Field(None, ge=0, description="Number of assists")
    win: Optional[bool] = Field(None, description="Whether the participant won the match")
    gold_earned: Optional[int] = Field(None, ge=0, description="Total gold earned")
    vision_score: Optional[int] = Field(None, ge=0, description="Vision score")
    cs: Optional[int] = Field(None, ge=0, description="Total creep score")
    kda: Optional[Decimal] = Field(None, ge=0, max_digits=5, decimal_places=2, description="Kill-death-assist ratio")
    champ_level: Optional[int] = Field(None, ge=1, description="Champion level achieved")
    total_damage_dealt: Optional[int] = Field(None, ge=0, description="Total damage dealt")
    total_damage_dealt_to_champions: Optional[int] = Field(None, ge=0, description="Total damage dealt to champions")
    total_damage_taken: Optional[int] = Field(None, ge=0, description="Total damage taken")
    total_heal: Optional[int] = Field(None, ge=0, description="Total healing done")
    individual_position: Optional[str] = Field(None, max_length=16, description="Individual position")
    team_position: Optional[str] = Field(None, max_length=16, description="Team position")
    role: Optional[str] = Field(None, max_length=16, description="Role")


class MatchParticipantResponse(MatchParticipantBase):
    """Schema for MatchParticipant response."""
    id: int = Field(..., description="Auto-incrementing primary key")
    created_at: datetime = Field(..., description="When this participant record was created")
    updated_at: datetime = Field(..., description="When this participant record was last updated")
    kdr: Optional[float] = Field(None, description="Kill-death ratio")
    total_kills_participation: int = Field(..., description="Total kills participated in")

    model_config = ConfigDict(from_attributes=True)


class MatchParticipantListResponse(BaseModel):
    """Schema for paginated MatchParticipant list response."""
    participants: list[MatchParticipantResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class ParticipantSearchRequest(BaseModel):
    """Schema for participant search requests."""
    puuid: Optional[uuid.UUID] = Field(None, description="Filter by player PUUID")
    match_id: Optional[str] = Field(None, max_length=64, description="Filter by match ID")
    champion_id: Optional[int] = Field(None, description="Filter by champion ID")
    team_id: Optional[int] = Field(None, description="Filter by team ID")
    individual_position: Optional[str] = Field(None, max_length=16, description="Filter by position")
    role: Optional[str] = Field(None, max_length=16, description="Filter by role")
    win: Optional[bool] = Field(None, description="Filter by win/loss")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")


class MatchParticipantsBulkCreate(BaseModel):
    """Schema for bulk creating match participants."""
    match_id: str = Field(..., max_length=64, description="Match ID")
    participants: list[MatchParticipantCreate] = Field(..., min_length=1, max_length=10, description="List of participants")


class ParticipantStatsResponse(BaseModel):
    """Schema for participant statistics response."""
    puuid: uuid.UUID
    total_matches: int
    wins: int
    losses: int
    win_rate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_kda: float
    avg_cs: float
    avg_gold_earned: float
    avg_vision_score: float
    most_played_champions: list[dict]
    performance_by_position: dict

    model_config = ConfigDict(from_attributes=True)
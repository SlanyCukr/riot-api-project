"""Pydantic schemas for Match model."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


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
        False, description="Whether this match has been processed for player analysis"
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
        None, description="Whether this match has been processed for player analysis"
    )
    processing_error: Optional[str] = Field(
        None, max_length=256, description="Error message if match processing failed"
    )


class MatchResponse(MatchBase):
    """Schema for Match response."""

    match_id: str = Field(
        ..., max_length=64, description="Unique match identifier from Riot API"
    )
    created_at: datetime = Field(
        ..., description="When this match record was created in our database"
    )
    updated_at: datetime = Field(
        ..., description="When this match record was last updated"
    )

    # Computed fields from domain model business logic
    is_ranked: bool = Field(default=False, description="Whether this is a ranked game")
    duration_minutes: float = Field(
        default=0.0, description="Game duration in minutes with decimal precision"
    )
    is_recent: bool = Field(
        default=False, description="Whether this match is recent (within 7 days)"
    )
    is_valid_game: bool = Field(
        default=False,
        description="Whether this is a valid complete game (>= 5 minutes)",
    )
    is_summoners_rift: bool = Field(
        default=False, description="Whether this match was played on Summoner's Rift"
    )
    game_creation_datetime: datetime = Field(
        ..., description="Game creation time as datetime object"
    )
    patch_version: str = Field(
        default="", description="Extracted patch version (e.g., '14.20')"
    )
    winning_team_id: Optional[int] = Field(
        default=None, description="Team ID that won the match (100 or 200)"
    )

    model_config = ConfigDict(from_attributes=True)


class MatchParticipantResponse(BaseModel):
    """Schema for Match Participant response with computed fields."""

    # Basic participant fields
    id: int = Field(..., description="Participant record ID")
    match_id: str = Field(..., description="Match ID")
    puuid: str = Field(..., description="Player PUUID")
    summoner_name: Optional[str] = Field(
        None, description="Summoner name at time of match"
    )
    summoner_level: int = Field(..., description="Summoner level at time of match")
    team_id: int = Field(..., description="Team ID (100 or 200)")
    champion_id: int = Field(..., description="Champion ID played")
    champion_name: str = Field(..., description="Champion name played")
    kills: int = Field(..., description="Number of kills")
    deaths: int = Field(..., description="Number of deaths")
    assists: int = Field(..., description="Number of assists")
    win: bool = Field(..., description="Whether the participant won")
    gold_earned: int = Field(..., description="Total gold earned")
    vision_score: int = Field(..., description="Vision score")
    cs: int = Field(..., description="Total creep score")
    kda: Optional[float] = Field(None, description="KDA ratio from database")
    champ_level: int = Field(..., description="Champion level achieved")
    total_damage_dealt: int = Field(..., description="Total damage dealt")
    total_damage_dealt_to_champions: int = Field(
        ..., description="Total damage dealt to champions"
    )
    total_damage_taken: int = Field(..., description="Total damage taken")
    total_heal: int = Field(..., description="Total healing done")
    individual_position: Optional[str] = Field(None, description="Individual position")
    team_position: Optional[str] = Field(None, description="Team position")
    role: Optional[str] = Field(None, description="Role")
    riot_id_name: Optional[str] = Field(None, description="Riot ID game name")
    riot_id_tagline: Optional[str] = Field(None, description="Riot ID tagline")
    created_at: datetime = Field(
        ..., description="When this participant record was created"
    )
    updated_at: datetime = Field(
        ..., description="When this participant record was last updated"
    )

    # Computed fields from domain model business logic
    calculated_kda: float = Field(..., description="Calculated KDA ratio")
    is_carry_performance: bool = Field(
        ..., description="Whether this was a carry performance"
    )
    cs_per_minute: float = Field(..., description="CS per minute")
    is_support_role: bool = Field(
        ..., description="Whether playing support/utility role"
    )
    is_high_vision: bool = Field(
        ..., description="Whether player has high vision score"
    )
    is_perfect_kda: bool = Field(..., description="Whether player achieved perfect KDA")
    is_good_cs: bool = Field(..., description="Whether CS per minute is good")
    performance_grade: str = Field(
        ..., description="Overall performance grade (S, A, B, C, D)"
    )

    model_config = ConfigDict(from_attributes=True)


class MatchWithParticipantsResponse(MatchResponse):
    """Schema for Match response with participants included."""

    participants: List[MatchParticipantResponse] = Field(
        default=[], description="List of match participants with computed fields"
    )
    participant_count: int = Field(
        default=0, description="Number of participants in the match"
    )


class MatchListResponse(BaseModel):
    """Schema for paginated Match list response."""

    matches: List[MatchResponse]
    total: int = Field(..., description="Total matches available")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of matches per page")
    pages: int = Field(..., description="Total number of pages")

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

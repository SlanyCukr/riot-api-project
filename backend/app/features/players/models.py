"""
SQLModel models for players feature.

This file replaces:
- models.py (SQLAlchemy ORM)
- schemas.py (Pydantic schemas)
- ranks.py (PlayerRank SQLAlchemy model)
- ranks_schemas.py (PlayerRank Pydantic schemas)

Pattern: Base → Table → API schemas
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index, Column, DateTime
from pydantic import ConfigDict
import structlog

from app.core.enums import Tier

logger = structlog.get_logger()

# ============================================================================
# BASE MODELS - Shared fields between table and API
# ============================================================================


class PlayerBase(SQLModel):
    """
    Shared player fields between table and API.

    Include only fields that appear in BOTH:
    - Database table
    - API requests/responses
    """

    # Riot ID
    riot_id: Optional[str] = Field(
        default=None,
        max_length=128,
        index=True,
        description="Player's Riot ID (game name)",
    )
    tag_line: Optional[str] = Field(
        default=None, max_length=32, description="Player's tag line (region identifier)"
    )

    # Platform
    platform: str = Field(
        max_length=8,
        index=True,
        description="Platform where the player was last seen (e.g., EUW1, EUN1)",
    )

    # Summoner info
    summoner_name: Optional[str] = Field(
        default=None,
        max_length=32,
        index=True,
        description="Current summoner name (can change)",
    )
    summoner_id: Optional[str] = Field(
        default=None,
        max_length=64,
        index=True,
        description="Encrypted summoner ID (used for some Riot API endpoints)",
    )
    account_level: Optional[int] = Field(
        default=None, ge=1, le=1000, description="Player's account level"
    )
    profile_icon_id: Optional[int] = Field(default=None, description="Profile icon ID")


class PlayerRankBase(SQLModel):
    """Base PlayerRank schema with common attributes."""

    # Rank data
    queue_type: str = Field(
        max_length=32, description="Queue type (e.g., RANKED_SOLO_5x5, RANKED_FLEX_SR)"
    )
    tier: Tier = Field(description="Rank tier (e.g., GOLD, PLATINUM, DIAMOND)")
    rank: Optional[str] = Field(
        default=None, max_length=4, description="Rank division (I, II, III, IV)"
    )
    league_points: int = Field(
        default=0, ge=0, le=100, description="League points (0-100)"
    )
    wins: int = Field(default=0, ge=0, description="Number of wins in this queue")
    losses: int = Field(default=0, ge=0, description="Number of losses in this queue")

    # League status flags
    veteran: bool = Field(default=False, description="Whether the player is a veteran")
    inactive: bool = Field(default=False, description="Whether the player is inactive")
    fresh_blood: bool = Field(
        default=False, description="Whether the player is fresh blood"
    )
    hot_streak: bool = Field(
        default=False, description="Whether the player is on a hot streak"
    )

    # League information
    league_id: Optional[str] = Field(
        default=None, max_length=64, description="League ID"
    )
    league_name: Optional[str] = Field(
        default=None, max_length=64, description="League name"
    )

    # Season information
    season_id: Optional[str] = Field(
        default=None, max_length=16, index=True, description="Season identifier"
    )

    # Is current rank flag
    is_current: bool = Field(
        default=True,
        index=True,
        description="Whether this is the current rank for the player",
    )


# ============================================================================
# TABLE MODELS - Database tables
# ============================================================================


class Player(PlayerBase, table=True):
    """
    Player database table.

    Combines:
    - Shared fields from PlayerBase
    - Database-only fields (timestamps, flags)
    - Relationships to other tables
    """

    __tablename__ = "players"

    # Primary key - PUUID is the unique identifier from Riot API
    # Note: Riot PUUID is a base64-encoded string, not a standard UUID
    puuid: str = Field(
        primary_key=True,
        max_length=78,  # Riot PUUIDs are 78 characters
        index=True,
        description="Player's universally unique identifier from Riot API",
    )

    # Timestamps - Database generated defaults
    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default="NOW()"
        ),
        description="When this player record was first created",
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default="NOW()"
        ),
        description="When this player record was last updated",
    )
    last_seen: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default="NOW()", index=True
        ),
        description="When this player was last seen in a match",
    )

    # Soft deletion flag
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": "true"},
        index=True,
        description="Whether this player record is active (not deleted)",
    )

    # Tracking flags for automated jobs
    is_tracked: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        index=True,
        description="Whether this player is being actively tracked for continuous updates",
    )
    is_analyzed: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        index=True,
        description="Whether this player has been analyzed for smurf/boosted detection",
    )
    matches_exhausted: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        index=True,
        description="True when all available matches have been fetched from Riot API",
    )
    last_ban_check: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
        description="When this player was last checked for ban status",
    )

    # Relationships
    ranks: list["PlayerRank"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # Match participations - now enabled after SQLModel migration
    match_participations: list["MatchParticipant"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # Player analyses - now enabled after SQLModel migration
    player_analyses: list["PlayerAnalysis"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    # ========================================================================
    # COMPOSITE INDEXES - Performance optimization for common queries
    # ========================================================================

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index("idx_players_summoner_platform", "summoner_name", "platform"),
        Index("idx_players_riot_tag", "riot_id", "tag_line"),
        Index("idx_players_last_seen_active", "last_seen", "is_active"),
        {"schema": "core"},
    )

    # ========================================================================
    # CLASS METHODS - Constructors from different sources
    # ========================================================================

    @classmethod
    def from_riot_api(
        cls,
        puuid: str,
        platform: str,
        account_data: dict,
        summoner_data: Optional[dict] = None,
    ) -> "Player":
        """
        Create Player from Riot API responses.

        Handles:
        - camelCase → snake_case conversion
        - Field name mapping
        - Missing data (summoner_data optional)

        Args:
            puuid: Player's PUUID
            platform: Platform region
            account_data: Riot Account API response (has gameName, tagLine)
            summoner_data: Riot Summoner API response (has summonerLevel, etc.)

        Returns:
            Player instance ready to be added to database

        Example:
            account_dto = await riot_api.get_account_by_riot_id(...)
            summoner_dto = await riot_api.get_summoner_by_puuid(...)

            player = Player.from_riot_api(
                puuid=account_dto.puuid,
                platform="EUW1",
                account_data=account_dto.model_dump(by_alias=True),
                summoner_data=summoner_dto.model_dump(by_alias=True)
            )
        """
        player_dict = {
            "puuid": puuid,
            "platform": platform,
            "riot_id": account_data.get("gameName"),
            "tag_line": account_data.get("tagLine"),
        }

        if summoner_data:
            player_dict.update(
                {
                    "summoner_name": summoner_data.get("name"),
                    "summoner_id": summoner_data.get("id"),
                    "account_level": summoner_data.get("summonerLevel"),
                    "profile_icon_id": summoner_data.get("profileIconId"),
                }
            )

        return cls(**player_dict)

    # ========================================================================
    # INSTANCE METHODS - Operations on existing players
    # ========================================================================

    def update_from_riot(self, summoner_data: dict) -> None:
        """
        Update existing player with fresh Riot API data.

        Only updates Riot-sourced fields, preserves our internal flags.

        Args:
            summoner_data: Fresh data from Riot Summoner API

        Example:
            player = await get_player(puuid)
            summoner_dto = await riot_api.get_summoner_by_puuid(puuid)
            player.update_from_riot(summoner_dto.model_dump(by_alias=True))
            await db.commit()
        """
        # Update only Riot fields
        self.summoner_name = summoner_data.get("name", self.summoner_name)
        self.summoner_id = summoner_data.get("id", self.summoner_id)
        self.account_level = summoner_data.get("summonerLevel", self.account_level)
        self.profile_icon_id = summoner_data.get("profileIconId", self.profile_icon_id)

        # Note: last_seen, updated_at timestamps will be updated by database triggers

        logger.info(
            "player_updated_from_riot",
            puuid=self.puuid,
            account_level=self.account_level,
        )


class PlayerRank(PlayerRankBase, table=True):
    """
    Player rank information for a specific queue.

    One player can have multiple ranks (Solo/Duo, Flex, etc.).
    """

    __tablename__ = "player_ranks"
    __table_args__ = {"schema": "core"}

    # Primary key
    id: Optional[int] = Field(
        default=None, primary_key=True, description="Auto-incrementing primary key"
    )

    # Foreign key
    puuid: str = Field(
        foreign_key="core.players.puuid",
        max_length=78,
        index=True,
        description="Reference to the player (Riot PUUID)",
    )

    # Timestamps - Database generated defaults
    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default="NOW()"
        ),
        description="When this rank record was created",
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default="NOW()"
        ),
        description="When this rank record was last updated",
    )

    # Relationship
    player: Player = Relationship(back_populates="ranks")

    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100

    @property
    def total_games(self) -> int:
        """Get total number of games played."""
        return self.wins + self.losses

    @property
    def display_rank(self) -> str:
        """Get the display rank (e.g., 'Gold II')."""
        if self.rank:
            return f"{self.tier.title()} {self.rank}"
        return self.tier.title()


# ============================================================================
# API MODELS - Request schemas
# ============================================================================


class PlayerSearchRequest(SQLModel):
    """
    Request to search for a player by Riot ID.

    Used in POST /players/search endpoint.
    """

    riot_id: str = Field(min_length=1, max_length=16, description="Game name")
    tag_line: str = Field(min_length=1, max_length=5, description="Tag line")
    platform: str = Field(min_length=2, max_length=8, description="Platform")


class PlayerCreate(PlayerBase):
    """
    Request to create a player manually.

    Requires PUUID (from prior Riot API lookup).
    """

    puuid: str = Field(min_length=78, max_length=78, description="Player's PUUID")


class PlayerUpdate(SQLModel):
    """
    Request to update player settings.

    All fields optional for PATCH semantics.
    Only includes user-modifiable fields.
    """

    summoner_name: Optional[str] = Field(
        None, max_length=32, description="Current summoner name (can change)"
    )
    account_level: Optional[int] = Field(
        None, ge=1, le=1000, description="Player's account level"
    )
    profile_icon_id: Optional[int] = Field(None, description="Profile icon ID")
    last_seen: Optional[datetime] = Field(
        None, description="When this player was last seen in a match"
    )
    is_tracked: Optional[bool] = Field(None, description="Enable/disable auto-updates")
    is_analyzed: Optional[bool] = Field(None, description="Mark as analyzed")
    matches_exhausted: Optional[bool] = Field(
        None, description="Mark matches as exhausted"
    )


class PlayerRankUpdate(SQLModel):
    """Schema for updating a PlayerRank - minimal fields for rank progression."""

    tier: Optional[Tier] = Field(None, description="Rank tier")
    rank: Optional[str] = Field(None, max_length=4, description="Rank division")
    league_points: Optional[int] = Field(
        None, ge=0, le=100, description="League points"
    )
    wins: Optional[int] = Field(None, ge=0, description="Number of wins")
    losses: Optional[int] = Field(None, ge=0, description="Number of losses")
    veteran: Optional[bool] = Field(None, description="Whether player is a veteran")
    inactive: Optional[bool] = Field(None, description="Whether player is inactive")
    fresh_blood: Optional[bool] = Field(
        None, description="Whether player is fresh blood"
    )
    hot_streak: Optional[bool] = Field(
        None, description="Whether player is on hot streak"
    )
    league_id: Optional[str] = Field(None, max_length=64, description="League ID")
    league_name: Optional[str] = Field(None, max_length=64, description="League name")
    season_id: Optional[str] = Field(
        None, max_length=16, description="Season identifier"
    )
    is_current: Optional[bool] = Field(None, description="Whether this is current rank")


# ============================================================================
# API MODELS - Response schemas
# ============================================================================


class PlayerPublic(PlayerBase):
    """
    Basic player response.

    Includes all public fields, excludes sensitive data.
    """

    puuid: str
    created_at: datetime
    updated_at: datetime
    last_seen: datetime
    is_active: bool
    is_tracked: bool
    is_analyzed: bool
    matches_exhausted: bool
    last_ban_check: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PlayerRankPublic(PlayerRankBase):
    """Rank information for API responses."""

    id: int
    puuid: str
    created_at: datetime
    updated_at: datetime

    # Computed properties
    win_rate: float
    total_games: int
    display_rank: str

    model_config = ConfigDict(from_attributes=True)


class PlayerPublicWithRanks(PlayerPublic):
    """
    Player response with nested rank information.

    Used when client needs full player profile.
    """

    ranks: list[PlayerRankPublic] = []


class PlayerListResponse(SQLModel):
    """Paginated list of players."""

    players: list[PlayerPublic]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# COMPOSITE INDEXES
# ============================================================================

# These indexes are created at the database level via Alembic migration
# but documented here for reference

# Common query patterns:
# 1. Search by Riot ID + tag line (account lookup)
# 2. Search by summoner name + platform (common lookup)
# 3. Filter by last_seen + is_active (cleanup queries)

# Note: Individual field indexes are defined in Field() definitions above
# Composite indexes need to be added via Alembic migration for performance

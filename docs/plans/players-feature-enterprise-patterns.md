# Players Feature: Enterprise Architecture Implementation Guide

**Date**: 2025-10-28
**Status**: Planning
**Effort Estimate**: 12-16 hours
**Approach**: SQLAlchemy 2.0 + Pydantic v2 with Enterprise Patterns

---

## Table of Contents

1. [Overview](#overview)
2. [Current State](#current-state)
3. [Target Architecture](#target-architecture)
4. [Enterprise Patterns Applied](#enterprise-patterns-applied)
5. [Implementation Guide](#implementation-guide)
6. [Code Examples](#code-examples)
7. [Data Flow](#data-flow)
8. [Effort Breakdown](#effort-breakdown)
9. [Success Criteria](#success-criteria)

---

## Overview

### Goals

Transform the players feature from a functional implementation into an **enterprise-grade architecture** with:

- ✅ **Clear separation of concerns** - ORM models, repositories, services, API schemas
- ✅ **Rich domain models** - Business logic lives with the data
- ✅ **Repository pattern** - Isolate data access from business logic
- ✅ **Anti-Corruption Layer** - Protect domain from external API (Riot API) semantics
- ✅ **Type safety** - Full mypy/pyright validation across all layers
- ✅ **Testability** - Each layer independently testable with clear interfaces

### Why Enterprise Patterns?

**Current pain points:**
- Service layer contains both business logic AND database queries (mixed responsibilities)
- No clear abstraction for data access (tight coupling to SQLAlchemy)
- Riot API semantics leak into domain layer (camelCase, Riot-specific terminology)
- Difficult to test business logic in isolation
- Unclear where to add new business rules

**Benefits of refactoring:**
- Clear responsibilities: Repository = data access, Service = orchestration, Model = domain logic
- Easy testing: Mock repositories instead of database
- Maintainable: New developers understand the 3-layer architecture immediately
- Flexible: Can swap data sources without changing business logic
- Type-safe: Strong typing across all layers catches errors at compile time

---

## Current State

### Existing File Structure (Pre-SQLModel)

```
features/players/
├── __init__.py           # Exports for other modules
├── models.py             # SQLAlchemy ORM models
├── schemas.py            # Pydantic request/response schemas
├── service.py            # Business logic + database queries mixed
├── router.py             # FastAPI endpoints
├── dependencies.py       # Dependency injection
└── README.md             # Feature documentation
```

### Current Architecture

**Layers (not clearly separated):**

```
┌─────────────────────────────────────────┐
│ Router (FastAPI endpoints)              │
│ - Thin controllers                      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Service Layer                           │
│ - Business logic                        │
│ - Database queries (MIXED!)             │
│ - Riot API calls                        │
│ - Transformations                       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Database (PostgreSQL)                   │
└─────────────────────────────────────────┘
```

**Problems with current architecture:**

1. **Service does too much**: Contains queries, business logic, API calls, transformations
2. **No abstraction for data access**: Service directly uses `db.execute(select(...))`
3. **Hard to test**: Cannot mock data access without mocking entire database
4. **Riot API leakage**: External API semantics visible in service layer
5. **Type safety gaps**: Transformations between layers not explicitly typed

---

## Target Architecture

### Enhanced File Structure

```
features/players/
├── __init__.py                 # Public API exports
├── orm_models.py               # NEW: SQLAlchemy ORM models (database)
├── schemas.py                  # Pydantic request/response schemas (API)
├── repository.py               # NEW: Data access abstraction
├── service.py                  # REFACTORED: Thin orchestration layer
├── transformers.py             # NEW: Explicit transformations
├── router.py                   # FastAPI endpoints (minimal changes)
├── dependencies.py             # Updated DI for repository
└── README.md                   # Updated documentation
```

### Three-Layer Separation

```
┌──────────────────────────────────────────────────────────────┐
│ External Layer: Riot API                                     │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ RiotAPIClient (connection object)                        │ │
│ │ RiotAPIGateway (Anti-Corruption Layer)                   │ │
│ │ RiotDTO schemas (external contracts)                     │ │
│ └──────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │ Transform DTOs → Domain
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Domain Layer: Your Business Logic                            │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ PlayerORM (Rich Domain Model with business logic)        │ │
│ │ PlayerRankORM (Domain models)                            │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ PlayerRepository (Data access interface)                 │ │
│ │ - get_by_puuid(), find_by_riot_id()                      │ │
│ │ - get_tracked_players(), save(), create()                │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ PlayerService (Orchestration + coordination)             │ │
│ │ - Delegates to repository for data access                │ │
│ │ - Delegates to models for business logic                 │ │
│ │ - Coordinates across multiple repositories               │ │
│ └──────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │ Data Mapper (SQLAlchemy)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Persistence Layer: PostgreSQL                                │
└───────────────────────────┬──────────────────────────────────┘
                            │ Load domain models
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ API Layer: Your REST API                                     │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ FastAPI Routes (thin controllers)                        │ │
│ │ Pydantic Schemas (PlayerPublic, PlayerCreate, etc.)      │ │
│ │ Transformers (ORM → Pydantic)                            │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Dependency Direction**: API → Service → Repository → Database (never reverse)
2. **One Responsibility**: Each layer has ONE clear purpose
3. **Interface-Based**: Repository implements interface for testability
4. **Explicit Transformations**: Clear conversion points between layers
5. **Rich Domain Models**: Business logic lives in ORM models

---

## Enterprise Patterns Applied

### 1. Repository Pattern (Martin Fowler)

**Definition**: "Mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects."

**Purpose**:
- Encapsulate data access logic
- Provide collection-like interface (`get`, `find`, `add`, `remove`)
- Enable easy mocking for tests
- Isolate business logic from SQL

**Application in Players Feature**:
```python
class PlayerRepository:
    """Acts as in-memory collection of Player objects."""

    async def get_by_puuid(self, puuid: str) -> PlayerORM | None:
        """Get player by ID - collection semantics."""

    async def find_by_riot_id(self, game_name: str, tag: str, platform: str) -> PlayerORM | None:
        """Find player by Riot ID - query semantics."""

    async def add(self, player: PlayerORM) -> PlayerORM:
        """Add player to collection."""

    async def get_tracked_players(self) -> list[PlayerORM]:
        """Get all tracked players - collection filtering."""
```

### 2. Rich Domain Model Pattern (Martin Fowler)

**Definition**: "An object model of the domain that incorporates both behavior and data."

**Purpose**:
- Combine data and behavior in domain objects
- Encapsulate business rules close to data
- Avoid anemic domain models (just getters/setters)

**Application in Players Feature**:
```python
class PlayerORM(Base):
    """Rich domain model with business logic."""

    # Data fields
    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    account_level: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    # Business behavior
    def is_new_account(self) -> bool:
        """Domain logic: what makes a new account?"""
        return self.account_level is not None and self.account_level < 30

    def calculate_win_rate(self) -> float:
        """Domain calculation."""
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    def calculate_smurf_likelihood(self) -> float:
        """Complex business logic on domain data."""
        score = 0.0
        if self.is_new_account():
            score += 0.3
        if self.calculate_win_rate() > 65:
            score += 0.4
        return min(score, 1.0)

    def validate_for_tracking(self) -> list[str]:
        """Domain validation rules."""
        errors = []
        if not self.riot_id or not self.tag_line:
            errors.append("Missing Riot ID - cannot track player")
        if not self.platform:
            errors.append("Missing platform - cannot track player")
        return errors
```

**Key Principle**: "Service layer is thin - all key logic lies in the domain layer."

### 3. Data Mapper Pattern (SQLAlchemy 2.0)

**Definition**: "A layer of mappers that moves data between objects and a database while keeping them independent of each other."

**Purpose**:
- Keep domain objects unaware of database
- Bidirectional independence
- Separate mapping layer handles persistence

**Application**: SQLAlchemy 2.0 follows Data Mapper pattern
- ORM models don't have `.save()` or `.delete()` methods (not Active Record)
- Session object handles persistence
- Domain models can exist without database knowledge

### 4. Anti-Corruption Layer (Martin Fowler)

**Definition**: "Creates isolation between subsystems that don't share the same semantics."

**Purpose**:
- Protect domain from external system semantics
- Translate external concepts to domain language
- Isolate changes in external system

**Application in Players Feature**:
```python
# External Riot API returns DTOs with Riot semantics
class RiotAccountDTO(BaseModel):
    puuid: str
    gameName: str        # camelCase
    tagLine: str         # Riot-specific

# Anti-Corruption Layer transforms to domain
class RiotAPIGateway:
    async def fetch_player_profile(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerORM:
        """Gateway translates Riot DTOs to domain ORM."""
        # Fetch from Riot API
        account_dto = await self.client.get_account(game_name, tag_line)
        summoner_dto = await self.client.get_summoner(account_dto.puuid, platform)

        # Transform to domain model (hide Riot semantics)
        return PlayerORM(
            puuid=account_dto.puuid,
            riot_id=account_dto.gameName,  # Translate naming
            tag_line=account_dto.tagLine,
            platform=platform,
            summoner_name=summoner_dto.name,
            account_level=summoner_dto.summonerLevel,
        )
```

### 5. DTO Pattern (Data Transfer Objects)

**Definition**: "An object that carries data between processes to reduce the number of method calls."

**Purpose**:
- Cross process boundaries (HTTP requests/responses)
- Different shapes for different operations
- Isolate API contracts from domain models

**Application in Players Feature**:
```python
# API Request DTO
class PlayerCreate(BaseModel):
    """DTO for creating player - API input."""
    puuid: str = Field(min_length=78, max_length=78)
    riot_id: str
    tag_line: str
    platform: str

# API Response DTO
class PlayerPublic(BaseModel):
    """DTO for player API response - API output."""
    puuid: str
    riot_id: str | None
    summoner_name: str | None
    is_tracked: bool
    created_at: datetime

    # Computed field not in database
    smurf_likelihood: float | None = None

    model_config = ConfigDict(from_attributes=True)

# Domain Model (separate from DTOs)
class PlayerORM(Base):
    """Domain model - database representation."""
    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    riot_id: Mapped[str | None] = mapped_column(String(128))
    # ... domain fields ...
```

---

## Implementation Guide

### Phase 1: Setup and Preparation (1 hour)

**1.1 Create directory structure**
```bash
cd backend/app/features/players/
touch orm_models.py repository.py transformers.py
```

**1.2 Update dependencies**
Ensure SQLAlchemy 2.0 and Pydantic v2:
```toml
# pyproject.toml
[project.dependencies]
sqlalchemy = "^2.0.0"
pydantic = "^2.0.0"
```

**1.3 Configure type checking**
```toml
# pyproject.toml
[tool.mypy]
plugins = ["sqlalchemy.ext.mypy.plugin", "pydantic.mypy"]
strict = true

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
```

### Phase 2: Create ORM Models (2-3 hours)

**2.1 Define Base class**
```python
# app/core/database.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
```

**2.2 Create Player ORM model**

See [Code Examples](#code-examples) section for complete `PlayerORM` implementation.

**Key points**:
- Use `Mapped` type annotations for all fields
- Use `mapped_column` for explicit configuration
- Add business logic methods directly to model
- Define relationships with type hints

**2.3 Create PlayerRank ORM model**

See [Code Examples](#code-examples) section for complete `PlayerRankORM` implementation.

### Phase 3: Create Repository Layer (3-4 hours)

**3.1 Define Repository Interface**

```python
# features/players/repository.py
from abc import ABC, abstractmethod

class PlayerRepositoryInterface(ABC):
    """Interface for testability and flexibility."""

    @abstractmethod
    async def get_by_puuid(self, puuid: str) -> PlayerORM | None:
        """Get player by PUUID."""
        pass

    @abstractmethod
    async def find_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerORM | None:
        """Find player by Riot ID."""
        pass

    @abstractmethod
    async def get_tracked_players(self) -> list[PlayerORM]:
        """Get all tracked players."""
        pass

    @abstractmethod
    async def create(self, player: PlayerORM) -> PlayerORM:
        """Add new player."""
        pass

    @abstractmethod
    async def save(self, player: PlayerORM) -> PlayerORM:
        """Save existing player."""
        pass
```

**3.2 Implement SQLAlchemy Repository**

See [Code Examples](#code-examples) section for complete `SQLAlchemyPlayerRepository` implementation.

**Key points**:
- All SQL queries isolated in repository
- Use `selectinload` for eager loading relationships
- Return domain models (ORM objects)
- No business logic - pure data access

### Phase 4: Refactor Service Layer (4-5 hours)

**4.1 Create Transformer for Riot API**

```python
# features/players/transformers.py
class PlayerTransformer:
    """Transforms between different representations."""

    @staticmethod
    def from_riot_dto(
        account_dto: RiotAccountDTO,
        summoner_dto: RiotSummonerDTO,
        platform: str
    ) -> PlayerORM:
        """Transform Riot API DTO to domain ORM."""
        return PlayerORM(
            puuid=account_dto.puuid,
            riot_id=account_dto.gameName,
            tag_line=account_dto.tagLine,
            platform=platform,
            summoner_name=summoner_dto.name,
            account_level=summoner_dto.summonerLevel,
            profile_icon_id=summoner_dto.profileIconId,
        )

    @staticmethod
    def to_public_schema(player: PlayerORM) -> PlayerPublic:
        """Transform domain ORM to API response DTO."""
        return PlayerPublic(
            puuid=player.puuid,
            riot_id=player.riot_id,
            summoner_name=player.summoner_name,
            account_level=player.account_level,
            is_tracked=player.is_tracked,
            created_at=player.created_at,
            updated_at=player.updated_at,
            # Computed fields using domain logic
            smurf_likelihood=player.calculate_smurf_likelihood(),
        )
```

**4.2 Refactor Service to Thin Orchestration**

See [Code Examples](#code-examples) section for complete `PlayerService` implementation.

**Key changes from current service**:
- **Remove**: All `db.execute(select(...))` calls → move to repository
- **Remove**: Domain calculations → move to ORM models
- **Keep**: Orchestration logic (call repository, call Riot API, coordinate)
- **Add**: Explicit transformations using transformer

### Phase 5: Update Router and Dependencies (1-2 hours)

**5.1 Update dependency injection**

```python
# features/players/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.riot_api import get_riot_api_gateway
from .repository import PlayerRepositoryInterface, SQLAlchemyPlayerRepository
from .service import PlayerService

def get_player_repository(
    db: AsyncSession = Depends(get_db)
) -> PlayerRepositoryInterface:
    """Provide player repository."""
    return SQLAlchemyPlayerRepository(db)

def get_player_service(
    repository: PlayerRepositoryInterface = Depends(get_player_repository),
    riot_gateway: RiotAPIGateway = Depends(get_riot_api_gateway),
) -> PlayerService:
    """Provide player service."""
    return PlayerService(repository, riot_gateway)
```

**5.2 Update router endpoints**

```python
# features/players/router.py
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import get_player_service
from .service import PlayerService
from .schemas import PlayerPublic, PlayerCreate

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/{puuid}", response_model=PlayerPublic)
async def get_player(
    puuid: str,
    service: PlayerService = Depends(get_player_service),
):
    """Get player by PUUID."""
    try:
        return await service.get_player(puuid)
    except PlayerNotFoundError:
        raise HTTPException(status_code=404, detail="Player not found")

@router.post("", response_model=PlayerPublic, status_code=201)
async def create_player(
    player_data: PlayerCreate,
    service: PlayerService = Depends(get_player_service),
):
    """Create new player."""
    return await service.create_player(player_data)
```

### Phase 6: Update Documentation (1 hour)

**6.1 Update `__init__.py` exports**

```python
# features/players/__init__.py
"""Players feature - Enterprise architecture.

Public API exports following repository pattern and domain-driven design.
"""

from .orm_models import PlayerORM, PlayerRankORM
from .schemas import PlayerCreate, PlayerUpdate, PlayerPublic, PlayerRankPublic
from .repository import PlayerRepositoryInterface, SQLAlchemyPlayerRepository
from .service import PlayerService
from .router import router as players_router

__all__ = [
    # Domain models
    "PlayerORM",
    "PlayerRankORM",
    # API schemas
    "PlayerCreate",
    "PlayerUpdate",
    "PlayerPublic",
    "PlayerRankPublic",
    # Repository
    "PlayerRepositoryInterface",
    "SQLAlchemyPlayerRepository",
    # Service
    "PlayerService",
    # Router
    "players_router",
]
```

**6.2 Update README.md**

Document new architecture, patterns applied, and how to extend.

---

## Code Examples

### Complete ORM Models

```python
# features/players/orm_models.py
"""SQLAlchemy 2.0 ORM models for players feature.

Follows Data Mapper pattern with Rich Domain Model behavior.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

class PlayerORM(Base):
    """
    Player domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety
    - Business logic methods
    - Domain validation rules
    """

    __tablename__ = "players"
    __table_args__ = (
        Index("idx_players_riot_id_platform", "riot_id", "platform"),
        Index("idx_players_summoner_name_platform", "summoner_name", "platform"),
        Index("idx_players_is_tracked", "is_tracked"),
        Index("idx_players_last_seen", "last_seen"),
        {"schema": "core"},
    )

    # Primary key
    puuid: Mapped[str] = mapped_column(
        String(78),
        primary_key=True,
        comment="Player's universally unique identifier from Riot API"
    )

    # Riot ID
    riot_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        index=True,
        comment="Player's Riot ID (game name)"
    )
    tag_line: Mapped[Optional[str]] = mapped_column(
        String(32),
        comment="Player's tag line (region identifier)"
    )

    # Platform
    platform: Mapped[str] = mapped_column(
        String(8),
        index=True,
        comment="Platform where player was last seen (e.g., EUW1, NA1)"
    )

    # Summoner info
    summoner_name: Mapped[Optional[str]] = mapped_column(
        String(32),
        index=True,
        comment="Current summoner name (can change)"
    )
    summoner_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="Encrypted summoner ID (for Riot API endpoints)"
    )
    account_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Player's account level"
    )
    profile_icon_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Profile icon ID"
    )

    # Tracking flags
    is_tracked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        index=True,
        comment="Whether player is being actively tracked for updates"
    )
    is_analyzed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        index=True,
        comment="Whether player has been analyzed for smurf detection"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        comment="Whether player record is active (not soft-deleted)"
    )
    matches_exhausted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="True when all available matches fetched from Riot API"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this player record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this player record was last updated"
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When player was last seen in a match"
    )
    last_ban_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When player was last checked for ban status"
    )

    # Relationships (type-safe with Mapped)
    ranks: Mapped[list["PlayerRankORM"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    match_participations: Mapped[list["MatchParticipantORM"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    player_analyses: Mapped[list["PlayerAnalysisORM"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def is_new_account(self) -> bool:
        """
        Determine if player has a new account.

        Business rule: Accounts below level 30 are considered new.
        Used for smurf detection algorithms.
        """
        return self.account_level is not None and self.account_level < 30

    def is_veteran(self) -> bool:
        """
        Determine if player is a veteran.

        Business rule: Level 100+ with 500+ total games.
        """
        if not self.account_level or self.account_level < 100:
            return False

        # Check if they have rank data with sufficient games
        if self.ranks:
            total_games = sum(r.wins + r.losses for r in self.ranks if r.is_current)
            return total_games >= 500

        return False

    def calculate_smurf_likelihood(self) -> float:
        """
        Calculate likelihood that this player is a smurf account.

        Business logic combining multiple factors:
        - New account (low level)
        - High win rate
        - High rank for account level

        Returns:
            Score between 0.0 and 1.0 (0 = unlikely, 1 = very likely)
        """
        score = 0.0

        # Factor 1: New account (30% weight)
        if self.is_new_account():
            score += 0.3

        # Factor 2: High win rate on new account (40% weight)
        if self.ranks:
            current_rank = next((r for r in self.ranks if r.is_current), None)
            if current_rank:
                win_rate = current_rank.calculate_win_rate()
                if self.is_new_account() and win_rate > 65:
                    score += 0.4
                elif win_rate > 70:
                    score += 0.2

        # Factor 3: High rank for low level (30% weight)
        if self.is_new_account() and self.ranks:
            current_rank = next((r for r in self.ranks if r.is_current), None)
            if current_rank and current_rank.tier in ("DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"):
                score += 0.3

        return min(score, 1.0)

    def needs_data_refresh(self, refresh_interval_days: int = 1) -> bool:
        """
        Determine if player data should be refreshed from Riot API.

        Business rule: Data is stale after refresh_interval_days.
        """
        if not self.updated_at:
            return True

        from datetime import timezone
        age = datetime.now(timezone.utc) - self.updated_at
        return age.days >= refresh_interval_days

    def validate_for_tracking(self) -> list[str]:
        """
        Validate that player can be tracked.

        Domain validation rules for business invariants.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.riot_id or not self.tag_line:
            errors.append("Missing Riot ID - cannot track player without full Riot ID")

        if not self.platform:
            errors.append("Missing platform - cannot track player without platform")

        if not self.summoner_name and not self.summoner_id:
            errors.append("Missing summoner data - fetch from Riot API first")

        return errors

    def mark_as_tracked(self) -> None:
        """Mark player as tracked (business operation)."""
        self.is_tracked = True

    def unmark_as_tracked(self) -> None:
        """Remove player from tracking (business operation)."""
        self.is_tracked = False

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PlayerORM(puuid='{self.puuid}', "
            f"riot_id='{self.riot_id}#{self.tag_line}', "
            f"platform='{self.platform}', "
            f"is_tracked={self.is_tracked})>"
        )


class PlayerRankORM(Base):
    """
    Player rank information for a specific queue (Rich Domain Model).

    One player can have multiple ranks (Solo/Duo, Flex, etc.).
    """

    __tablename__ = "player_ranks"
    __table_args__ = (
        Index("idx_player_ranks_puuid_queue", "puuid", "queue_type"),
        Index("idx_player_ranks_is_current", "is_current"),
        {"schema": "core"},
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing primary key"
    )

    # Foreign key
    puuid: Mapped[str] = mapped_column(
        String(78),
        # ForeignKey will be added in Alembic migration
        index=True,
        comment="Reference to player (Riot PUUID)"
    )

    # Rank data
    queue_type: Mapped[str] = mapped_column(
        String(32),
        comment="Queue type (e.g., RANKED_SOLO_5x5, RANKED_FLEX_SR)"
    )
    tier: Mapped[str] = mapped_column(
        String(16),
        comment="Rank tier (e.g., GOLD, PLATINUM, DIAMOND)"
    )
    rank: Mapped[Optional[str]] = mapped_column(
        String(4),
        comment="Rank division (I, II, III, IV)"
    )
    league_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="League points (0-100)"
    )
    wins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of wins in this queue"
    )
    losses: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of losses in this queue"
    )

    # League status flags
    veteran: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether player is a veteran"
    )
    inactive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether player is inactive"
    )
    fresh_blood: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether player is fresh blood"
    )
    hot_streak: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether player is on a hot streak"
    )

    # League information
    league_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="League ID"
    )
    league_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="League name"
    )

    # Season information
    season_id: Mapped[Optional[str]] = mapped_column(
        String(16),
        comment="Season identifier"
    )

    # Current rank flag
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        comment="Whether this is the current rank for the player"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this rank record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this rank record was last updated"
    )

    # Relationships
    player: Mapped["PlayerORM"] = relationship(back_populates="ranks")

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def calculate_win_rate(self) -> float:
        """
        Calculate win rate as a percentage.

        Business calculation on domain data.
        """
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100

    def total_games(self) -> int:
        """Get total number of games played."""
        return self.wins + self.losses

    def display_rank(self) -> str:
        """
        Get human-readable rank (e.g., 'Gold II').

        Business formatting rule.
        """
        if self.rank:
            return f"{self.tier.title()} {self.rank}"
        return self.tier.title()

    def is_high_elo(self) -> bool:
        """
        Determine if rank is high elo.

        Business rule: Diamond+ is considered high elo.
        """
        return self.tier.upper() in ("DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PlayerRankORM(id={self.id}, "
            f"puuid='{self.puuid}', "
            f"rank='{self.display_rank()}', "
            f"lp={self.league_points}, "
            f"wr={self.calculate_win_rate():.1f}%)>"
        )
```

### Complete Repository Implementation

```python
# features/players/repository.py
"""Repository pattern implementation for players feature.

Provides collection-like interface for accessing player domain objects.
Isolates data access logic from business logic.
"""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import structlog

from .orm_models import PlayerORM, PlayerRankORM

logger = structlog.get_logger(__name__)


class PlayerRepositoryInterface(ABC):
    """
    Interface for player repository.

    Defines contract for data access operations.
    Enables mocking in tests and potential swap of implementations.
    """

    @abstractmethod
    async def get_by_puuid(self, puuid: str) -> Optional[PlayerORM]:
        """
        Get player by PUUID.

        Args:
            puuid: Player's unique identifier

        Returns:
            PlayerORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        platform: str
    ) -> Optional[PlayerORM]:
        """
        Find player by Riot ID.

        Args:
            game_name: Riot ID game name
            tag_line: Riot ID tag line
            platform: Platform region

        Returns:
            PlayerORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_summoner_name(
        self,
        summoner_name: str,
        platform: str
    ) -> list[PlayerORM]:
        """
        Find players by summoner name (fuzzy match).

        Args:
            summoner_name: Summoner name to search
            platform: Platform region

        Returns:
            List of matching players
        """
        pass

    @abstractmethod
    async def get_tracked_players(self) -> list[PlayerORM]:
        """
        Get all tracked players.

        Returns:
            List of tracked players
        """
        pass

    @abstractmethod
    async def get_players_needing_refresh(
        self,
        days_since_update: int,
        limit: int
    ) -> list[PlayerORM]:
        """
        Get players needing data refresh.

        Args:
            days_since_update: Age threshold in days
            limit: Maximum number of players

        Returns:
            List of players with stale data
        """
        pass

    @abstractmethod
    async def create(self, player: PlayerORM) -> PlayerORM]:
        """
        Add new player to repository.

        Args:
            player: Player domain object to add

        Returns:
            Created player with generated fields populated
        """
        pass

    @abstractmethod
    async def save(self, player: PlayerORM) -> PlayerORM:
        """
        Save existing player changes.

        Args:
            player: Player domain object with changes

        Returns:
            Updated player with refreshed state
        """
        pass

    @abstractmethod
    async def delete(self, player: PlayerORM) -> None:
        """
        Remove player from repository (soft delete).

        Args:
            player: Player to delete
        """
        pass


class SQLAlchemyPlayerRepository(PlayerRepositoryInterface):
    """
    SQLAlchemy implementation of player repository.

    Handles all database operations for players.
    Translates repository interface to SQLAlchemy operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_by_puuid(self, puuid: str) -> Optional[PlayerORM]:
        """Get player by PUUID with eager-loaded relationships."""
        stmt = (
            select(PlayerORM)
            .options(
                selectinload(PlayerORM.ranks),
                # Add other relationships as needed
            )
            .where(
                PlayerORM.puuid == puuid,
                PlayerORM.is_active == True
            )
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if player:
            logger.debug(
                "player_retrieved",
                puuid=puuid,
                riot_id=player.riot_id,
            )

        return player

    async def find_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        platform: str
    ) -> Optional[PlayerORM]:
        """Find player by Riot ID (exact match)."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.riot_id == game_name,
                PlayerORM.tag_line == tag_line,
                PlayerORM.platform == platform.upper(),
                PlayerORM.is_active == True
            )
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        logger.debug(
            "player_search_by_riot_id",
            game_name=game_name,
            tag_line=tag_line,
            platform=platform,
            found=player is not None,
        )

        return player

    async def find_by_summoner_name(
        self,
        summoner_name: str,
        platform: str
    ) -> list[PlayerORM]:
        """Find players by summoner name (fuzzy match with ILIKE)."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.summoner_name.ilike(f"%{summoner_name}%"),
                PlayerORM.platform == platform.upper(),
                PlayerORM.is_active == True
            )
            .limit(10)  # Prevent excessive results
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "player_search_by_summoner_name",
            summoner_name=summoner_name,
            platform=platform,
            results_count=len(players),
        )

        return players

    async def get_tracked_players(self) -> list[PlayerORM]:
        """Get all tracked players."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.is_tracked == True,
                PlayerORM.is_active == True
            )
            .order_by(PlayerORM.summoner_name)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.info(
            "tracked_players_retrieved",
            count=len(players),
        )

        return players

    async def get_players_needing_refresh(
        self,
        days_since_update: int,
        limit: int
    ) -> list[PlayerORM]:
        """Get players with stale data."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_update)

        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.is_tracked == True,
                PlayerORM.is_active == True,
                PlayerORM.updated_at < cutoff
            )
            .order_by(PlayerORM.updated_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "players_needing_refresh",
            days_threshold=days_since_update,
            count=len(players),
        )

        return players

    async def create(self, player: PlayerORM) -> PlayerORM:
        """Create new player record."""
        self.db.add(player)
        await self.db.commit()
        await self.db.refresh(player)

        logger.info(
            "player_created",
            puuid=player.puuid,
            riot_id=player.riot_id,
            platform=player.platform,
        )

        return player

    async def save(self, player: PlayerORM) -> PlayerORM:
        """Save existing player changes."""
        await self.db.commit()
        await self.db.refresh(player)

        logger.debug(
            "player_saved",
            puuid=player.puuid,
        )

        return player

    async def delete(self, player: PlayerORM) -> None:
        """Soft delete player."""
        player.is_active = False
        await self.db.commit()

        logger.info(
            "player_deleted",
            puuid=player.puuid,
        )
```

### Complete Service Layer

```python
# features/players/service.py
"""Player service layer - thin orchestration only.

Business logic delegated to domain models.
Data access delegated to repository.
External API calls delegated to Anti-Corruption Layer (RiotAPIGateway).
"""

from typing import Optional
import structlog

from .repository import PlayerRepositoryInterface
from .orm_models import PlayerORM
from .schemas import PlayerPublic, PlayerCreate
from .transformers import PlayerTransformer
from .exceptions import PlayerNotFoundError, ValidationError
from app.core.riot_api import RiotAPIGateway

logger = structlog.get_logger(__name__)


class PlayerService:
    """
    Player service - orchestrates operations across layers.

    Responsibilities:
    - Coordinate repository and domain models
    - Handle transactions
    - Transform between layers
    - Delegate logic to appropriate layer

    Does NOT contain:
    - Database queries (in repository)
    - Business logic (in domain models)
    - Riot API calls (in gateway/ACL)
    """

    def __init__(
        self,
        repository: PlayerRepositoryInterface,
        riot_gateway: RiotAPIGateway,
    ):
        """
        Initialize service with dependencies.

        Args:
            repository: Player repository for data access
            riot_gateway: Riot API gateway (Anti-Corruption Layer)
        """
        self.repo = repository
        self.riot = riot_gateway

    async def get_player(self, puuid: str) -> PlayerPublic:
        """
        Get player by PUUID.

        Args:
            puuid: Player's unique identifier

        Returns:
            Player API response

        Raises:
            PlayerNotFoundError: If player doesn't exist
        """
        # Delegate data access to repository
        player_orm = await self.repo.get_by_puuid(puuid)

        if not player_orm:
            raise PlayerNotFoundError(f"Player not found: {puuid}")

        # Transform ORM → API response (includes computed fields)
        return PlayerTransformer.to_public_schema(player_orm)

    async def get_player_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        platform: str
    ) -> PlayerPublic:
        """
        Get player by Riot ID.

        Args:
            game_name: Riot ID game name
            tag_line: Riot ID tag line
            platform: Platform region

        Returns:
            Player API response

        Raises:
            PlayerNotFoundError: If player doesn't exist
        """
        # Delegate data access to repository
        player_orm = await self.repo.find_by_riot_id(game_name, tag_line, platform)

        if not player_orm:
            raise PlayerNotFoundError(
                f"Player not found: {game_name}#{tag_line} on {platform}"
            )

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(player_orm)

    async def create_player(self, player_data: PlayerCreate) -> PlayerPublic:
        """
        Create new player.

        Args:
            player_data: Player creation data

        Returns:
            Created player API response
        """
        # Check if player already exists
        existing = await self.repo.get_by_puuid(player_data.puuid)
        if existing:
            logger.warning(
                "player_already_exists",
                puuid=player_data.puuid,
            )
            return PlayerTransformer.to_public_schema(existing)

        # Create domain model from API request
        player_orm = PlayerORM(
            puuid=player_data.puuid,
            riot_id=player_data.riot_id,
            tag_line=player_data.tag_line,
            platform=player_data.platform,
            summoner_name=player_data.summoner_name,
            account_level=player_data.account_level,
        )

        # Delegate persistence to repository
        created_player = await self.repo.create(player_orm)

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(created_player)

    async def fetch_and_store_player(
        self,
        game_name: str,
        tag_line: str,
        platform: str
    ) -> PlayerPublic:
        """
        Fetch player from Riot API and store in database.

        This is where Anti-Corruption Layer shines:
        - Riot API has its own semantics (camelCase, Riot-specific IDs)
        - Gateway translates to our domain model
        - Service just orchestrates

        Args:
            game_name: Riot ID game name
            tag_line: Riot ID tag line
            platform: Platform region

        Returns:
            Created player API response
        """
        # Check if already exists in database
        existing = await self.repo.find_by_riot_id(game_name, tag_line, platform)
        if existing:
            logger.info(
                "player_already_in_database",
                puuid=existing.puuid,
            )
            return PlayerTransformer.to_public_schema(existing)

        # Delegate Riot API interaction to gateway (Anti-Corruption Layer)
        # Gateway returns domain model (ORM), hiding Riot API details
        player_orm = await self.riot.fetch_player_profile(game_name, tag_line, platform)

        # Delegate persistence to repository
        created_player = await self.repo.create(player_orm)

        logger.info(
            "player_fetched_and_stored",
            puuid=created_player.puuid,
            riot_id=f"{game_name}#{tag_line}",
        )

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(created_player)

    async def track_player(self, puuid: str) -> PlayerPublic:
        """
        Mark player as tracked for automated monitoring.

        Args:
            puuid: Player's unique identifier

        Returns:
            Updated player API response

        Raises:
            PlayerNotFoundError: If player doesn't exist
            ValidationError: If player cannot be tracked
        """
        # Delegate data access to repository
        player_orm = await self.repo.get_by_puuid(puuid)

        if not player_orm:
            raise PlayerNotFoundError(f"Player not found: {puuid}")

        # Delegate validation to domain model
        validation_errors = player_orm.validate_for_tracking()
        if validation_errors:
            raise ValidationError(validation_errors)

        # Delegate business operation to domain model
        player_orm.mark_as_tracked()

        # Delegate persistence to repository
        updated_player = await self.repo.save(player_orm)

        logger.info(
            "player_tracked",
            puuid=puuid,
            riot_id=player_orm.riot_id,
        )

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(updated_player)

    async def untrack_player(self, puuid: str) -> PlayerPublic:
        """
        Remove player from tracked status.

        Args:
            puuid: Player's unique identifier

        Returns:
            Updated player API response

        Raises:
            PlayerNotFoundError: If player doesn't exist
        """
        # Delegate data access to repository
        player_orm = await self.repo.get_by_puuid(puuid)

        if not player_orm:
            raise PlayerNotFoundError(f"Player not found: {puuid}")

        # Delegate business operation to domain model
        player_orm.unmark_as_tracked()

        # Delegate persistence to repository
        updated_player = await self.repo.save(player_orm)

        logger.info(
            "player_untracked",
            puuid=puuid,
        )

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(updated_player)

    async def get_tracked_players(self) -> list[PlayerPublic]:
        """
        Get all tracked players.

        Returns:
            List of tracked players
        """
        # Delegate data access to repository
        players_orm = await self.repo.get_tracked_players()

        # Transform list of ORM → list of API responses
        return [
            PlayerTransformer.to_public_schema(player)
            for player in players_orm
        ]

    async def refresh_player_data(self, puuid: str) -> PlayerPublic:
        """
        Refresh player data from Riot API.

        Orchestrates:
        1. Get player from database
        2. Check if needs refresh (domain logic)
        3. Fetch fresh data from Riot API (ACL)
        4. Update database (repository)

        Args:
            puuid: Player's unique identifier

        Returns:
            Updated player API response

        Raises:
            PlayerNotFoundError: If player doesn't exist
        """
        # Delegate data access to repository
        player_orm = await self.repo.get_by_puuid(puuid)

        if not player_orm:
            raise PlayerNotFoundError(f"Player not found: {puuid}")

        # Delegate business logic to domain model
        if not player_orm.needs_data_refresh():
            logger.debug(
                "player_data_fresh",
                puuid=puuid,
            )
            return PlayerTransformer.to_public_schema(player_orm)

        # Delegate Riot API interaction to gateway (ACL)
        fresh_player_orm = await self.riot.fetch_player_profile(
            player_orm.riot_id,
            player_orm.tag_line,
            player_orm.platform
        )

        # Update existing player with fresh data
        player_orm.summoner_name = fresh_player_orm.summoner_name
        player_orm.account_level = fresh_player_orm.account_level
        player_orm.profile_icon_id = fresh_player_orm.profile_icon_id

        # Delegate persistence to repository
        updated_player = await self.repo.save(player_orm)

        logger.info(
            "player_data_refreshed",
            puuid=puuid,
        )

        # Transform ORM → API response
        return PlayerTransformer.to_public_schema(updated_player)
```

---

## Data Flow

### Complete Request Flow Example

**User Request**: `GET /api/v1/players/{puuid}`

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. API Layer (Router)                                            │
│    - FastAPI receives request                                    │
│    - Validates path parameter (puuid: str)                       │
│    - Injects PlayerService dependency                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Service Layer (PlayerService)                                 │
│    - service.get_player(puuid)                                   │
│    - Delegates data access to repository                         │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. Repository Layer (SQLAlchemyPlayerRepository)                 │
│    - repository.get_by_puuid(puuid)                              │
│    - Executes: select(PlayerORM).where(puuid==...)               │
│    - Returns: PlayerORM (domain model)                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. Database (PostgreSQL)                                         │
│    - Queries core.players table                                  │
│    - Returns row data                                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. Domain Model (PlayerORM)                                      │
│    - SQLAlchemy materializes PlayerORM instance                  │
│    - Includes business logic methods                             │
│    - Domain calculations: player_orm.calculate_smurf_likelihood()│
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. Transformer (PlayerTransformer)                               │
│    - PlayerTransformer.to_public_schema(player_orm)              │
│    - Transforms ORM → Pydantic DTO                               │
│    - Adds computed fields using domain logic                     │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. API Response (PlayerPublic Pydantic Schema)                   │
│    - FastAPI validates response_model                            │
│    - Serializes to JSON                                          │
│    - Returns HTTP 200 with player data                           │
└──────────────────────────────────────────────────────────────────┘
```

### Riot API Integration Flow

**User Request**: `POST /api/v1/players/fetch` (fetch from Riot API)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. API Layer                                                     │
│    Request body: {game_name, tag_line, platform}                │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Service Layer                                                 │
│    service.fetch_and_store_player(game_name, tag_line, platform)│
│    - Check if exists in database (repository)                   │
│    - If not, delegate to Riot API Gateway                       │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. Anti-Corruption Layer (RiotAPIGateway)                        │
│    gateway.fetch_player_profile(game_name, tag_line, platform)  │
│    - Calls Riot Account API (get account by Riot ID)            │
│    - Calls Riot Summoner API (get summoner by PUUID)            │
│    - Transforms Riot DTOs → PlayerORM (domain model)            │
│    - Hides Riot semantics (camelCase, Riot IDs, etc.)           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. Domain Model (PlayerORM)                                      │
│    - Created by gateway transformation                           │
│    - Contains player data in OUR domain language                 │
│    - Ready for persistence                                       │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. Repository Layer                                              │
│    repository.create(player_orm)                                 │
│    - Persists player to database                                 │
│    - Returns created player with generated fields                │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. Transformer → API Response                                    │
│    - Transform ORM → PlayerPublic                                │
│    - Return to client                                            │
└──────────────────────────────────────────────────────────────────┘
```

**Key Observation**: External API (Riot) semantics NEVER leak into service or repository layers. Gateway (ACL) acts as barrier.

---

## Effort Breakdown

### Phase-by-Phase Estimates

| Phase | Tasks | Hours | Complexity |
|-------|-------|-------|------------|
| **Phase 1: Setup** | Directory structure, dependencies, type config | 1 | Low |
| **Phase 2: ORM Models** | Create PlayerORM, PlayerRankORM with rich domain logic | 2-3 | Medium |
| **Phase 3: Repository** | Interface + implementation, all queries | 3-4 | Medium |
| **Phase 4: Service** | Refactor to thin orchestration, add transformers | 4-5 | High |
| **Phase 5: Router/DI** | Update dependencies, minimal router changes | 1-2 | Low |
| **Phase 6: Documentation** | Update exports, README, code comments | 1 | Low |
| **TOTAL** | | **12-16 hours** | |

### Complexity Factors

**Low Complexity (easier than expected)**:
- Router changes minimal (already using dependency injection)
- ORM models straightforward (just add type hints + methods)
- Clear layer separation simplifies implementation

**High Complexity (takes longer)**:
- Refactoring service layer (current service does everything)
- Ensuring all queries moved to repository
- Handling edge cases in transformations

### Risk Buffer

Add **20% buffer** for unexpected issues:
- **Estimated**: 12-16 hours
- **With buffer**: 14-19 hours
- **Realistic range**: **14-19 hours** for players feature

---

## Success Criteria

### Technical Checklist

- [ ] **ORM Models Created**
  - [ ] PlayerORM with all fields using `Mapped` types
  - [ ] PlayerRankORM with relationships
  - [ ] Business logic methods in models
  - [ ] Domain validation methods

- [ ] **Repository Layer Implemented**
  - [ ] PlayerRepositoryInterface defined
  - [ ] SQLAlchemyPlayerRepository implements all methods
  - [ ] All SQL queries moved from service to repository
  - [ ] Eager loading configured for relationships

- [ ] **Service Layer Refactored**
  - [ ] All database queries removed (delegated to repository)
  - [ ] All business logic removed (delegated to models)
  - [ ] Service contains only orchestration
  - [ ] Explicit transformations using transformer

- [ ] **Anti-Corruption Layer Verified**
  - [ ] Riot API semantics hidden from service/repository
  - [ ] RiotAPIGateway returns domain models (ORM)
  - [ ] No Riot DTOs visible outside gateway

- [ ] **Type Safety Validated**
  - [ ] mypy passes with strict mode
  - [ ] pyright passes with strict mode
  - [ ] No `type: ignore` comments added

- [ ] **Documentation Updated**
  - [ ] `__init__.py` exports correct
  - [ ] README.md documents new architecture
  - [ ] Code comments explain patterns

### Functional Checklist

- [ ] **All existing endpoints work**
  - [ ] GET /players/{puuid}
  - [ ] GET /players?riot_id=...
  - [ ] POST /players (create)
  - [ ] PATCH /players/{puuid} (update)
  - [ ] POST /players/{puuid}/track
  - [ ] DELETE /players/{puuid}/track

- [ ] **No regressions**
  - [ ] No performance degradation
  - [ ] Same API contracts maintained

- [ ] **New capabilities enabled**
  - [ ] Clear layer boundaries obvious to new developers
  - [ ] Easy to understand where to add new features
  - [ ] Business logic centralized in domain models

### Quality Gates

- [ ] **Code Review Passed**
  - [ ] Patterns applied correctly
  - [ ] No anti-patterns introduced
  - [ ] SOLID principles followed

- [ ] **Performance Acceptable**
  - [ ] Query performance same or better
  - [ ] No N+1 query issues
  - [ ] Eager loading configured properly

- [ ] **Maintainability Improved**
  - [ ] Clear where to add new features
  - [ ] Easy to understand for new developers
  - [ ] Each layer has single responsibility

---

## Next Steps

After completing players feature:

1. **Validate approach** - Ensure patterns work well before scaling
2. **Document learnings** - Update enterprise patterns guide with lessons
3. **Apply to next feature** - Use template for matches, jobs, etc.
4. **Iterate and improve** - Refine patterns based on experience

---

## References

**Research Sources**:
- Martin Fowler: *Patterns of Enterprise Application Architecture*
  - Repository Pattern
  - Rich Domain Model Pattern
  - Data Mapper Pattern
  - Anti-Corruption Layer Pattern
- FastAPI Official Documentation
- SQLAlchemy 2.0 Documentation (Mapped types)
- Pydantic v2 Documentation
- Real-world FastAPI projects (Netflix Dispatch, RealWorld)

**Related Documentation**:
- `docs/plans/enterprise-patterns-guide.md` - Reusable pattern templates
- `backend/app/features/CLAUDE.md` - Feature development guide
- `backend/CLAUDE.md` - Backend architecture overview

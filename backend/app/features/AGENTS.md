# Feature Development Guide

## Overview

The `backend/app/features/` directory contains domain-specific business logic organized by feature. Each feature is self-contained with all related code: API routes, business logic, database models, request/response schemas, and dependency injection.

## Feature-Based Architecture

### Principles

1. **Feature Cohesion**: All code related to a domain feature lives together
2. **Clear Boundaries**: Features have well-defined public APIs exposed via `__init__.py`
3. **Dependency Flow**: Features depend on `core/`, optionally on other features, but `core/` never depends on features
4. **Minimal Cross-Feature Dependencies**: Features should be as independent as possible

### Existing Features

- **`players/`** - Player management (search, tracking, rank info)
- **`matches/`** - Match data and statistics
- **`smurf_detection/`** - Smurf analysis algorithms (see feature-specific AGENTS.md)
- **`matchmaking_analysis/`** - Matchmaking fairness evaluation
- **`jobs/`** - Background job scheduling and execution (see feature-specific AGENTS.md)
- **`settings/`** - System configuration management

## Standard Feature Structure

Every feature follows this structure:

```
features/<feature_name>/
├── __init__.py          # Public API exports
├── router.py            # FastAPI routes
├── service.py           # Business logic
├── models.py            # Database models (optional)
├── schemas.py           # Pydantic request/response schemas
├── dependencies.py      # Dependency injection helpers
├── tests/               # Feature-specific tests
└── README.md            # Feature documentation (optional)
```

### File Responsibilities

#### `__init__.py` - Public API

Export the feature's public interface for use by other features and `main.py`:

```python
"""Player management feature."""

from .router import router as players_router
from .service import PlayerService
from .models import Player, Rank
from .schemas import PlayerResponse, PlayerCreate, PlayerUpdate

__all__ = [
    "players_router",
    "PlayerService",
    "Player",
    "Rank",
    "PlayerResponse",
    "PlayerCreate",
    "PlayerUpdate",
]
```

#### `router.py` - API Endpoints

Define FastAPI routes with thin controllers that delegate to services:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .dependencies import get_player_service
from .service import PlayerService
from .schemas import PlayerResponse

router = APIRouter()

@router.get("/players/{puuid}", response_model=PlayerResponse)
async def get_player(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service),
    db: AsyncSession = Depends(get_db)
):
    """Get player by PUUID.

    :param puuid: Player's unique identifier
    :param player_service: Player service instance
    :param db: Database session
    :returns: Player data
    :raises HTTPException: If player not found
    """
    player = await player_service.get_player(puuid, db)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player
```

**Keep routes thin** - no business logic in route handlers.

#### `service.py` - Business Logic

Implement business logic with async methods:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.riot_api import RiotDataManager
from app.core.enums import Platform
from .models import Player
from .schemas import PlayerCreate

logger = structlog.get_logger()

class PlayerService:
    """Service for player management operations."""

    def __init__(self, riot_data_manager: RiotDataManager):
        self.riot_data_manager = riot_data_manager

    async def get_player(self, puuid: str, db: AsyncSession) -> Player | None:
        """Get player by PUUID.

        :param puuid: Player's unique identifier
        :param db: Database session
        :returns: Player if found, None otherwise
        """
        result = await db.execute(
            select(Player).where(Player.puuid == puuid)
        )
        return result.scalar_one_or_none()

    async def create_player(
        self,
        player_data: PlayerCreate,
        platform: Platform,
        db: AsyncSession
    ) -> Player:
        """Create new player.

        :param player_data: Player creation data
        :param platform: Riot platform
        :param db: Database session
        :returns: Created player
        """
        # Fetch from Riot API
        riot_player = await self.riot_data_manager.get_account_by_riot_id(
            player_data.game_name,
            player_data.tag_line,
            platform,
            db
        )

        # Create database record
        player = Player(
            puuid=riot_player.puuid,
            game_name=riot_player.game_name,
            tag_line=riot_player.tag_line,
        )
        db.add(player)
        await db.commit()
        await db.refresh(player)

        logger.info("player_created", puuid=player.puuid)
        return player
```

**Service Guidelines:**
- Async methods only (no blocking I/O)
- Use RiotDataManager for Riot API calls
- Log operations with structlog context keys
- Handle errors gracefully
- Return early to reduce complexity

#### `models.py` - Database Models

Define SQLAlchemy models with proper relationships:

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.models import BaseModel

class Player(BaseModel):
    """Player database model."""

    __tablename__ = "players"

    puuid = Column(String, unique=True, nullable=False, index=True)
    game_name = Column(String, nullable=False)
    tag_line = Column(String, nullable=False)
    summoner_level = Column(Integer)
    is_tracked = Column(Boolean, default=False, nullable=False)

    # Relationships
    ranks = relationship("Rank", back_populates="player", cascade="all, delete-orphan")
    matches = relationship("PlayerMatch", back_populates="player")

class Rank(BaseModel):
    """Rank information for a player."""

    __tablename__ = "ranks"

    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    tier = Column(String, nullable=False)
    rank = Column(String, nullable=False)
    league_points = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)

    # Relationships
    player = relationship("Player", back_populates="ranks")
```

**Model Guidelines:**
- Inherit from `BaseModel` (provides `id`, `created_at`, `updated_at`)
- Use proper indexes on frequently queried columns
- Define relationships with `back_populates`
- Use cascades appropriately
- Add docstrings to all models

#### `schemas.py` - Pydantic Schemas

Define request/response schemas with validation:

```python
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class PlayerBase(BaseModel):
    """Base player schema."""

    game_name: str = Field(..., min_length=1, max_length=16)
    tag_line: str = Field(..., min_length=1, max_length=5)

class PlayerCreate(PlayerBase):
    """Schema for creating a player."""
    pass

class PlayerUpdate(BaseModel):
    """Schema for updating a player."""

    is_tracked: bool | None = None
    summoner_level: int | None = Field(None, ge=1, le=500)

class PlayerResponse(PlayerBase):
    """Schema for player API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    puuid: str
    summoner_level: int | None
    is_tracked: bool
    created_at: datetime
    updated_at: datetime
```

**Schema Guidelines:**
- Use Pydantic v2 patterns (`ConfigDict`, field validators)
- Separate schemas for create, update, and response
- Use `Field()` for validation constraints
- Enable `from_attributes=True` for ORM models
- Add descriptions for API documentation

#### `dependencies.py` - Dependency Injection

Provide factory functions for FastAPI dependency injection:

```python
from fastapi import Depends

from app.core.dependencies import get_riot_data_manager
from app.core.riot_api import RiotDataManager
from .service import PlayerService

def get_player_service(
    riot_data_manager: RiotDataManager = Depends(get_riot_data_manager)
) -> PlayerService:
    """Provide PlayerService instance.

    :param riot_data_manager: Riot data manager dependency
    :returns: PlayerService instance
    """
    return PlayerService(riot_data_manager)
```

## Creating a New Feature

### Step-by-Step Guide

1. **Create feature directory**:
   ```bash
   mkdir -p backend/app/features/my_feature
   cd backend/app/features/my_feature
   ```

2. **Create `__init__.py`** with public exports
3. **Create `models.py`** (if feature needs database tables)
4. **Create database migration**:
   ```bash
   ./scripts/alembic.sh revision --autogenerate -m "Add my_feature tables"
   ./scripts/alembic.sh upgrade head
   ```

5. **Create `schemas.py`** with Pydantic schemas
6. **Create `service.py`** with business logic
7. **Create `dependencies.py`** with DI factories
8. **Create `router.py`** with API endpoints
9. **Register router** in `backend/app/main.py`:
   ```python
   from app.features.my_feature import my_feature_router
   app.include_router(my_feature_router, prefix="/api/v1", tags=["my_feature"])
   ```

10. **Write tests** in `tests/features/my_feature/`
11. **Document feature** (optional README.md or AGENTS.md if complex)

## Import Patterns

### Within Feature (Internal)
```python
# Import sibling modules directly
from .models import Player, Rank
from .schemas import PlayerResponse
from .service import PlayerService
```

### From Core
```python
from app.core.database import get_db
from app.core.riot_api import RiotDataManager
from app.core.enums import Platform, Tier
from app.core.exceptions import RiotAPIError
```

### From Other Features (Use Public API)
```python
# ✅ Correct: Import from public API
from app.features.players import PlayerService, Player

# ❌ Wrong: Import internal modules
from app.features.players.service import PlayerService
```

### In main.py (Router Registration)
```python
from app.features.players import players_router
from app.features.matches import matches_router
from app.features.smurf_detection import smurf_detection_router
```

## Testing Features

Feature tests should cover service logic and API endpoints:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.players.service import PlayerService
from app.features.players.models import Player

@pytest.mark.asyncio
async def test_get_player(db: AsyncSession, test_client: AsyncClient):
    """Test getting player by PUUID."""
    # Setup
    player = Player(puuid="test-puuid", game_name="TestPlayer", tag_line="NA1")
    db.add(player)
    await db.commit()

    # Execute
    response = await test_client.get(f"/api/v1/players/{player.puuid}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["puuid"] == player.puuid
    assert data["game_name"] == "TestPlayer"
```

## Common Patterns

### Pagination
```python
@router.get("/players", response_model=list[PlayerResponse])
async def list_players(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """List players with pagination."""
    result = await db.execute(
        select(Player).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### Error Handling
```python
from app.core.exceptions import RiotAPIError, PlayerNotFoundError

try:
    player = await riot_data_manager.get_account_by_riot_id(name, tag, platform, db)
except PlayerNotFoundError:
    raise HTTPException(status_code=404, detail="Player not found")
except RiotAPIError as e:
    logger.error("riot_api_error", error=str(e))
    raise HTTPException(status_code=503, detail="Riot API unavailable")
```

### Background Tasks
```python
from fastapi import BackgroundTasks

@router.post("/players/{puuid}/refresh")
async def refresh_player(
    puuid: str,
    background_tasks: BackgroundTasks,
    player_service: PlayerService = Depends(get_player_service)
):
    """Refresh player data in background."""
    background_tasks.add_task(player_service.refresh_player_data, puuid)
    return {"status": "refresh queued"}
```

## See Also

- `backend/app/AGENTS.md` - FastAPI application structure
- `backend/app/core/AGENTS.md` - Core infrastructure details
- `backend/AGENTS.md` - Overall backend architecture
- `backend/app/features/smurf_detection/AGENTS.md` - Smurf detection feature details
- `backend/app/features/jobs/AGENTS.md` - Background jobs feature details

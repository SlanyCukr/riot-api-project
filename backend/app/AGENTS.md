# FastAPI Application Structure

## Overview

The `backend/app/` directory contains the FastAPI application with a feature-based architecture separating core infrastructure from domain features.

## Directory Structure

```
app/
├── main.py              # FastAPI app initialization, router registration
├── core/                # Infrastructure (database, config, Riot API, etc.)
│   ├── database.py
│   ├── config.py
│   ├── riot_api/
│   └── ...
└── features/            # Domain features (players, matches, smurf_detection, etc.)
    ├── players/
    ├── matches/
    ├── smurf_detection/
    ├── matchmaking_analysis/
    ├── jobs/
    └── settings/
```

## Application Initialization

**`main.py`** handles:

- FastAPI app creation with CORS, middleware
- Router registration from features
- Startup/shutdown lifecycle (database, scheduler)
- Health check endpoint

### Router Registration Pattern

```python
from app.features.players import players_router
from app.features.matches import matches_router

app.include_router(players_router, prefix="/api/v1", tags=["players"])
app.include_router(matches_router, prefix="/api/v1", tags=["matches"])
```

## Startup/Shutdown Lifecycle

```python
@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup."""
    # Database connection pool created automatically
    # Background job scheduler starts
    logger.info("application_started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    # Scheduler stops gracefully
    # Database connections close
    logger.info("application_shutdown")
```

## Core vs Features

### Core (`app/core/`)

**Infrastructure that all features depend on:**

- Database session management
- Configuration and settings
- Riot API client and rate limiting
- Shared enums and exceptions
- Base models and validation
- Structured logging setup

**Rule:** Features depend on core, never the reverse.

### Features (`app/features/`)

**Domain-specific business logic:**

- Each feature is self-contained
- Standard structure: `router.py`, `service.py`, `models.py`, `schemas.py`, `dependencies.py`
- Features expose public APIs via `__init__.py`
- Features can depend on core and other features (but minimize cross-feature dependencies)

## Import Patterns

### From Core

```python
from app.core.database import get_db
from app.core.config import get_settings
from app.core.riot_api import RiotAPIClient, RiotDataManager
from app.core.enums import Tier, Platform
from app.core.exceptions import RiotAPIError
```

### From Features (Public API)

```python
from app.features.players import PlayerService, Player, PlayerResponse
from app.features.matches import MatchService, Match
from app.features.smurf_detection import SmurfDetectionService
```

### From Features (Direct)

```python
# Internal feature use
from app.features.players.service import PlayerService
from app.features.players.models import Player, Rank
```

## Dependency Injection

FastAPI's DI system provides services and database sessions to route handlers:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.players.dependencies import get_player_service
from app.features.players.service import PlayerService

router = APIRouter()

@router.get("/players/{puuid}")
async def get_player(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service),
    db: AsyncSession = Depends(get_db)
):
    """Get player by PUUID."""
    return await player_service.get_player(puuid, db)
```

## Middleware and CORS

```python
# CORS configured for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Adding New Features

1. **Create feature directory**: `app/features/my_feature/`
2. **Create standard files**:
   - `__init__.py` - Public API exports
   - `router.py` - FastAPI routes
   - `service.py` - Business logic
   - `models.py` - Database models (if needed)
   - `schemas.py` - Pydantic request/response schemas
   - `dependencies.py` - Dependency injection helpers
3. **Register router** in `main.py`:
   ```python
   from app.features.my_feature import my_feature_router
   app.include_router(my_feature_router, prefix="/api/v1", tags=["my_feature"])
   ```
4. **Create tests** in `tests/features/my_feature/`

## Commands

```bash
# Run application locally (development)
docker compose exec backend uv run uvicorn app.main:app --reload

# Run tests
docker compose exec backend uv run pytest

# Run tests with coverage
docker compose exec backend uv run pytest --cov=app

# Type checking
docker compose exec backend uv run pyright

# Linting
docker compose exec backend uv run ruff check app/
```

## See Also

- `backend/AGENTS.md` - Overall backend architecture and patterns
- `backend/app/core/AGENTS.md` - Core infrastructure details
- `backend/app/features/AGENTS.md` - Feature development guide
- `openspec/AGENTS.md` - OpenSpec workflow for architectural changes

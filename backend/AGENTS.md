# Tech Stack

- Python 3.13 + FastAPI + SQLAlchemy 2.0+
- Pydantic v2 for validation
- structlog for structured logging
- APScheduler for background jobs
- httpx for async HTTP requests
- pytest for testing

# Project Structure

## Feature-Based Architecture

The backend uses **feature-based organization** where related code is grouped by domain:

### Core Infrastructure (`app/core/`)

- `database.py` - Database session management
- `config.py` - Application settings and configuration
- `exceptions.py` - Base exception classes
- `dependencies.py` - Core dependency injection
- `enums.py` - Shared enums (Tier, Platform, etc.)
- `models.py` - Base SQLAlchemy model class
- `decorators.py` - Utility decorators (retry, circuit breaker, etc.)
- `validation.py` - Shared validation utilities
- `riot_api/` - Riot API client infrastructure
  - `client.py` - RiotAPIClient with rate limiting
  - `data_manager.py` - RiotDataManager for data enrichment
  - `rate_limiter.py` - Rate limit handling
  - `transformers.py` - API DTO transformations

### Domain Features (`app/features/`)

Each feature is self-contained with all related code:

**`features/auth/`** - User authentication and authorization

- JWT-based authentication system
- User registration, login, and token management
- Password hashing and validation
- Rate limiting for auth endpoints

**`features/players/`** - Player management (Enterprise Architecture)

- `router.py` - Player API endpoints
- `service.py` - PlayerService (orchestration layer)
- `repository.py` - Repository pattern implementation with interface
- `orm_models.py` - Rich domain models with business logic
- `models.py` - Pydantic domain models (separate from ORM)
- `schemas.py` - Pydantic request/response schemas
- `transformers.py` - Data mapper between ORM and domain models
- `dependencies.py` - Feature-specific dependency injection
- `README.md` - Comprehensive enterprise architecture documentation

**`features/matches/`** - Match data and statistics

- Match history retrieval and storage
- Match participant tracking
- Statistics aggregation
- MatchDTOTransformer for API data

**`features/player_analysis/`** - Player analysis

- PlayerAnalysisService with multi-factor analysis
- `analyzers/` - Factor analyzers (win rate, account level, performance, etc.)
- `config.py` - Detection thresholds and weights

**`features/matchmaking_analysis/`** - Matchmaking fairness

- Team composition analysis
- Rank distribution evaluation
- Fairness score calculation

**`features/jobs/`** - Background job scheduling

- `scheduler.py` - APScheduler setup
- `base.py` - BaseJob abstract class
- `error_handling.py` - Riot API error decorator
- `implementations/` - Job implementations
  - `tracked_player_updater.py` - Updates tracked player data (every 15 min)
  - `match_fetcher.py` - Fetches new matches (every 30 min)
  - `player_analyzer.py` - Runs player analysis (daily)
  - `ban_checker.py` - Checks for banned accounts (daily)

**`features/settings/`** - System configuration

- Runtime settings management
- Riot API key validation
- Sensitive value masking

## Architectural Principles

### 1. Core vs. Features Separation

- **Core**: Infrastructure that all features depend on
- **Features**: Domain-specific business logic
- **Rule**: Features depend on core, never the reverse

### 2. Dependency Flow

```
features/players/ ──┐
features/matches/ ──┼─→ core/ ──→ External Libraries
features/jobs/ ─────┘
```

### 3. Feature Structure

Every feature follows the same pattern:

**Standard Feature Structure:**

```
features/<feature_name>/
├── __init__.py          # Public API exports
├── router.py            # FastAPI routes
├── service.py           # Business logic
├── models.py            # Database models
├── schemas.py           # Pydantic schemas
├── dependencies.py      # Dependency injection
├── tests/               # Feature tests
└── README.md            # Feature documentation
```

**Enterprise Feature Structure (players):**

```
features/players/
├── __init__.py          # Public API exports
├── router.py            # FastAPI routes
├── service.py           # Business orchestration
├── repository.py        # Repository pattern interface + implementation
├── orm_models.py        # Rich domain models (SQLAlchemy)
├── models.py            # Pydantic domain models
├── schemas.py           # API request/response schemas
├── transformers.py      # Data mapper between ORM and domain
├── dependencies.py      # Dependency injection
├── ranks.py             # Rank-related domain models
├── ranks_schemas.py     # Rank API schemas
├── tests/               # Feature tests
└── README.md            # Enterprise architecture documentation
```

### 4. Public API Exports

Features expose clean public APIs:

```python
# features/players/__init__.py
from .router import router as players_router
from .service import PlayerService
from .models import Player, Rank
from .schemas import PlayerResponse, PlayerCreate

__all__ = ["players_router", "PlayerService", "Player", "Rank", ...]
```

## Import Patterns

### Importing from Core

```python
from app.core.database import get_db
from app.core.config import get_settings
from app.core.riot_api import RiotAPIClient, RiotDataManager
from app.core.enums import Tier, Platform
```

### Importing from Features

```python
# Direct module imports (preferred to avoid circular dependencies)
from app.features.players.service import PlayerService
from app.features.players.models import Player
from app.features.players.schemas import PlayerResponse

# For enterprise features (players), you may also import:
from app.features.players.repository import PlayerRepositoryInterface
from app.features.players.orm_models import PlayerORM
from app.features.players.transformers import PlayerTransformer

# Some features have public API exports (jobs, settings, auth)
from app.features.jobs import jobs_router, start_scheduler
from app.features.settings import settings_router
from app.features.auth import auth_router
```

### Dependency Injection

```python
from fastapi import APIRouter, Depends
from app.features.players.dependencies import get_player_service
from app.features.players.service import PlayerService

router = APIRouter()

@router.get("/players/{puuid}")
async def get_player(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service)
):
    return await player_service.get_player(puuid)
```

# Commands

- `docker compose exec backend uv run pytest` - Run tests
- `docker compose exec backend uv run pytest --cov=app` - Run with coverage
- `docker compose build backend` - Rebuild if dependencies change
- `docker compose exec backend uv run alembic upgrade head` - Apply DB migrations
- `docker compose exec backend uv run alembic revision --autogenerate -m "msg"` - Create migration

# Code Style

- Use type hints everywhere (pyright enforced)
- Use async/await for all I/O operations
- Use structlog with context keys: `logger.info("action", puuid=puuid)`
- Keep API endpoints thin, business logic in services

## Adding New Features

When creating a new feature, follow this structure:

1. **Create feature directory**: `app/features/my_feature/`
2. **Create standard files**:
   - `__init__.py` - Public API exports
   - `router.py` - FastAPI endpoints
   - `service.py` - Business logic
   - `models.py` - Database models (if needed)
   - `schemas.py` - Pydantic schemas
   - `dependencies.py` - Dependency injection
   - `README.md` - Feature documentation
3. **Register router** in `main.py`:
   ```python
   from app.features.my_feature import my_feature_router
   app.include_router(my_feature_router, prefix="/api/v1", tags=["my_feature"])
   ```

**Note**: The current `main.py` uses `@app.on_event("startup")` and `@app.on_event("shutdown")` lifecycle handlers instead of the newer `lifespan` context manager pattern. 4. **Create tests** in `features/my_feature/tests/`

## Adding Endpoints to Existing Features

1. Add route to feature's `router.py`
2. Add business logic to feature's `service.py`
3. Add schemas to feature's `schemas.py` (if needed)
4. Update feature's `__init__.py` exports (if exposing new classes)
5. Document in feature's `README.md`

# Documentation

- Use ReST docstrings (`:param name:`, `:returns:`, `:raises:`)
- Don't include `:type:` or `:rtype:` (redundant with type hints)
- Add module docstrings to all files
- Example: `"""Get player by Riot ID.\n\n:param game_name: Player's game name\n:returns: Player response\n"""`

# Do

- Use return-early strategy to reduce cognitive complexity whenever possible

# Do Not

- Don't call RiotAPIClient directly (use RiotDataManager)
- Don't block event loop (no time.sleep(), use asyncio.sleep())
- Don't catch generic Exception (catch specific exceptions)
- Don't hardcode configuration (use app/config.py)
- Don't use `create_all()` or manual SQL (use Alembic - see `backend/alembic/AGENTS.md`)
- Don't write complex functions (keep cyclomatic complexity <20, aim for <10)
- Don't use f-strings in log messages (use context: `logger.info("msg", key=value)`)
- Don't skip pre-commit checks (`git commit --no-verify` is forbidden)
- Don't ignore pydocstyle warnings (all public functions need docstrings)
- Don't ignore pyright type errors (fix them incrementally - see plan above)

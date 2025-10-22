# Core Infrastructure

## Overview

The `backend/app/core/` directory contains shared infrastructure code that all features depend on. This includes database management, configuration, Riot API integration, shared enums, exceptions, and utilities.

## Core Modules

### `database.py` - Database Session Management
- **`AsyncSessionLocal`**: SQLAlchemy async session factory
- **`get_db()`**: Async generator dependency for FastAPI routes
- **`async_engine`**: Database engine with connection pooling

```python
from app.core.database import get_db

@router.get("/example")
async def example(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player))
    return result.scalars().all()
```

### `config.py` - Application Configuration
- **`Settings`**: Pydantic settings model with environment variables
- **`get_settings()`**: Cached settings dependency
- **Configuration sources**: `.env` file, environment variables

```python
from app.core.config import get_settings

settings = get_settings()
print(settings.DATABASE_URL)
print(settings.RIOT_API_KEY)
```

**Key settings:**
- `DATABASE_URL` - PostgreSQL connection string
- `RIOT_API_KEY` - Riot API authentication key
- `CORS_ORIGINS` - Allowed CORS origins for frontend
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### `logging.py` - Structured Logging
- **`structlog`** configuration with JSON output
- **Context keys** for trace ability
- **Request ID tracking** for request correlation

```python
import structlog

logger = structlog.get_logger()
logger.info("player_searched", puuid=puuid, platform=platform)
logger.error("api_error", error=str(e), endpoint="/summoner/v4")
```

**Never use f-strings in log messages** - use context keys instead.

### `exceptions.py` - Custom Exceptions
Base exception classes for application errors:

- **`RiotAPIError`**: Riot API request failures
- **`RateLimitError`**: Rate limit exceeded (429 response)
- **`PlayerNotFoundError`**: Player lookup failures (404 response)
- **`DatabaseError`**: Database operation failures

```python
from app.core.exceptions import RiotAPIError, PlayerNotFoundError

if response.status_code == 404:
    raise PlayerNotFoundError(f"Player {puuid} not found")
```

### `dependencies.py` - Core Dependency Injection
- **`get_db()`**: Database session (imported from database.py)
- **`get_settings()`**: Application settings (imported from config.py)
- **`get_riot_api_client()`**: Riot API client instance
- **`get_riot_data_manager()`**: Riot data manager (preferred over direct client)

```python
from app.core.dependencies import get_riot_data_manager

@router.get("/player/{puuid}")
async def get_player(
    puuid: str,
    data_manager: RiotDataManager = Depends(get_riot_data_manager)
):
    return await data_manager.get_summoner_by_puuid(puuid, platform)
```

### `enums.py` - Shared Enumerations
- **`Tier`**: Rank tiers (IRON, BRONZE, SILVER, GOLD, PLATINUM, EMERALD, DIAMOND, MASTER, GRANDMASTER, CHALLENGER)
- **`Platform`**: Riot API platforms (NA1, EUW1, EUN1, KR, etc.)
- **`QueueType`**: Game queue types (RANKED_SOLO_5x5, RANKED_FLEX_SR, etc.)

```python
from app.core.enums import Tier, Platform

if rank.tier == Tier.CHALLENGER:
    print("Top player!")
```

### `models.py` - Base Model Class
- **`Base`**: SQLAlchemy declarative base
- **`BaseModel`**: Abstract base with common fields (`id`, `created_at`, `updated_at`)

```python
from app.core.models import BaseModel

class Player(BaseModel):
    __tablename__ = "players"

    puuid = Column(String, unique=True, nullable=False)
    game_name = Column(String)
    tag_line = Column(String)
```

### `validation.py` - Shared Validation Utilities
- Riot ID validation (game name + tag line)
- PUUID format validation
- Platform code validation

```python
from app.core.validation import validate_riot_id

game_name, tag_line = validate_riot_id("PlayerName#NA1")
```

### `decorators.py` - Utility Decorators
- **`@retry_on_rate_limit`**: Automatic retry with exponential backoff for rate-limited requests
- **`@circuit_breaker`**: Circuit breaker pattern for external API calls
- **`@measure_performance`**: Performance measurement and logging

```python
from app.core.decorators import retry_on_rate_limit

@retry_on_rate_limit(max_retries=3, backoff=2.0)
async def fetch_matches(puuid: str):
    return await riot_api_client.get_match_history(puuid)
```

### `riot_api/` - Riot API Integration
Complete Riot API client infrastructure with rate limiting, caching, and data transformation.

**See `backend/app/core/riot_api/AGENTS.md` for comprehensive Riot API documentation.**

Key modules:
- `client.py` - HTTP client with rate limiting
- `data_manager.py` - High-level data access (use this, not client directly)
- `rate_limiter.py` - Token bucket rate limiter
- `transformers.py` - API response transformations
- `endpoints.py` - Riot API endpoint definitions

## Architectural Rules

### Rule 1: Features Depend on Core (Never Reverse)
```python
# ✅ Correct: Feature imports from core
from app.core.database import get_db
from app.core.riot_api import RiotDataManager

# ❌ Wrong: Core imports from feature
from app.features.players.service import PlayerService  # Never in core/
```

### Rule 2: Use RiotDataManager, Not RiotAPIClient
```python
# ✅ Correct: Use data manager
from app.core.riot_api import RiotDataManager
data_manager = RiotDataManager()
player = await data_manager.get_summoner_by_puuid(puuid, platform, db)

# ❌ Wrong: Direct API client usage
from app.core.riot_api import RiotAPIClient
client = RiotAPIClient()
response = await client.get(url)  # Too low-level, no caching
```

### Rule 3: Use Dependency Injection
```python
# ✅ Correct: DI with FastAPI Depends
@router.get("/player")
async def get_player(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    pass

# ❌ Wrong: Direct instantiation
db = AsyncSessionLocal()
settings = Settings()
```

### Rule 4: Structured Logging with Context
```python
# ✅ Correct: Context keys
logger.info("player_fetched", puuid=puuid, platform=platform.value)

# ❌ Wrong: F-strings in log messages
logger.info(f"Fetched player {puuid} from {platform}")
```

## Adding to Core

**When to add to core:**
- Infrastructure used by multiple features
- Third-party integrations (APIs, services)
- Shared utilities and helpers
- Base classes and abstractions

**When NOT to add to core:**
- Feature-specific business logic
- Domain models (put in feature's `models.py`)
- Feature-specific services

## Import Examples

```python
# Database
from app.core.database import get_db, async_engine
from sqlalchemy.ext.asyncio import AsyncSession

# Configuration
from app.core.config import get_settings, Settings

# Riot API
from app.core.riot_api import RiotDataManager, RiotAPIClient
from app.core.riot_api.transformers import MatchDTOTransformer

# Enums
from app.core.enums import Tier, Platform, QueueType

# Exceptions
from app.core.exceptions import RiotAPIError, RateLimitError, PlayerNotFoundError

# Models
from app.core.models import Base, BaseModel

# Logging
import structlog
logger = structlog.get_logger()

# Dependencies
from app.core.dependencies import get_riot_data_manager
```

## See Also

- `backend/app/core/riot_api/AGENTS.md` - Riot API integration details
- `backend/app/AGENTS.md` - FastAPI application structure
- `backend/AGENTS.md` - Overall backend architecture
- `backend/app/features/AGENTS.md` - Feature development guide

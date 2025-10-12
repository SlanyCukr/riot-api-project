# Backend Development Guide

Backend-specific patterns and implementation details. **See root `CLAUDE.md` for common Docker/testing/database commands.**

## Directory Structure
- `app/api/` - FastAPI endpoints (players, matches, detection)
- `app/services/` - Business logic (players, matches, detection, stats)
- `app/models/` - SQLAlchemy models (see `docker/postgres/CLAUDE.md`)
- `app/riot_api/` - HTTP client with rate limiting
- `app/algorithms/` - Smurf detection (win_rate, rank_progression, performance)
- `app/config.py` - Pydantic settings

## Backend-Specific Patterns

### FastAPI Dependency Injection
Use dependency injection for services and database sessions:

```python
from fastapi import Depends
from app.services.player_service import PlayerService

@router.get("/players/{puuid}")
async def get_player(
    puuid: str,
    player_service: PlayerService = Depends()
):
    return await player_service.get_player(puuid)
```

### Error Handling
Use structured exceptions with proper HTTP status codes:

```python
from fastapi import HTTPException

# Client errors (400s)
raise HTTPException(status_code=404, detail="Player not found")
raise HTTPException(status_code=429, detail="Rate limit exceeded")

# Server errors (500s)
raise HTTPException(status_code=503, detail="Riot API unavailable")
```

### Structured Logging
Use structlog for consistent logging:

```python
import structlog

logger = structlog.get_logger()

logger.info("player_fetched", puuid=puuid, region=region)
logger.error("riot_api_error", error=str(e), endpoint=endpoint)
```

## Riot API Integration

### Authentication
- API key via `X-Riot-Token` header
- **Dev keys expire every 24h** - regenerate at https://developer.riotgames.com
- Rate limits: 20 req/sec, 100 req/2min (dev keys)
- Automatic backoff on 429 responses

### Key Endpoints
- **Account v1** - Riot ID ↔ PUUID (preferred for dev keys)
- **Match v5** - Match history and details
- **League v4** - Ranked information
- **Spectator v4** - Live game data

See `app/riot_api/endpoints.py` for complete mappings.

### Caching Strategy
- **Database-first**: PostgreSQL is primary cache
- **Flow**: DB → Riot API (if miss) → Store → Return
- **No TTL**: Data in DB is considered valid
- **Rate limiting**: `RiotAPIClient` returns `None` or raises `RateLimitError` when throttled
- Services handle `None` gracefully

## Smurf Detection Algorithms

Located in `app/algorithms/`. Each returns confidence score (0-100).

- **Win rate**: ≥65% win rate over 30+ ranked games
- **Account level vs rank**: Low level with high rank
- **Performance consistency**: Consistent high performance
- **Rank progression**: Rapid climbing

Final detection combines scores with configurable thresholds.

## Code Conventions
- **Type hints required** - Enforced by pyright
- **Pydantic models** - All request/response validation
- **SQLAlchemy ORM** - All database operations
- **Docstrings** - Required for public functions
- **Async/await** - Use async for I/O operations (DB, HTTP)
- **Service layer** - Business logic separated from API endpoints

Example service pattern:
```python
class PlayerService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.riot_client = RiotAPIClient()

    async def get_or_fetch_player(self, puuid: str) -> Player:
        # Check DB first
        player = await self.db.get(Player, puuid)
        if player:
            return player

        # Fetch from Riot API
        data = await self.riot_client.get_account(puuid)
        player = Player(**data)
        self.db.add(player)
        await self.db.commit()
        return player
```

# Service Layer Guide

**WHEN TO USE THIS**: Implementing business logic, orchestrating data operations, or managing transactions.

**QUICK START**: Adding logic? → [Jump to Service Pattern](#quick-recipe-add-service-method)

---

## 📁 Available Services

| Service | File | Responsibilities |
|---------|------|------------------|
| **PlayerService** | `players.py` | Player CRUD, tracking, search by Riot ID |
| **MatchService** | `matches.py` | Match retrieval, statistics, encounter tracking |
| **SmurfDetectionService** | `detection.py` | Run algorithms, store/retrieve results |
| **StatsService** | `stats.py` | Statistical analysis, aggregations |
| **JobService** | `jobs.py` | Job config management, execution tracking |

---

## 🎯 Quick Recipe: Add Service Method

### 1. Locate/Create Service Class

**File**: `backend/app/services/<domain>.py`

### 2. Add Method

```python
# app/services/players.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..riot_api.data_manager import RiotDataManager
from ..models.players import Player
import structlog

logger = structlog.get_logger(__name__)

class PlayerService:
    """Service for player data operations."""

    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        """Initialize with database and data manager."""
        self.db = db
        self.data_manager = riot_data_manager

    async def get_player_stats(self, puuid: str, days: int = 30) -> dict:
        """
        Get player statistics over time period.

        Args:
            puuid: Player's unique identifier
            days: Number of days to analyze

        Returns:
            Dictionary with aggregated stats

        Raises:
            ValueError: If player not found
        """
        logger.info("fetching_player_stats", puuid=puuid, days=days)

        # Fetch player from DB
        player = await self.db.get(Player, puuid)
        if not player:
            logger.warning("player_not_found", puuid=puuid)
            raise ValueError(f"Player {puuid} not found")

        # Fetch matches via data manager
        matches = await self.data_manager.get_match_history(puuid, count=50)

        # Calculate statistics
        stats = self._calculate_stats(matches, days)

        logger.info("stats_calculated", puuid=puuid, match_count=len(matches))
        return stats

    def _calculate_stats(self, matches: list, days: int) -> dict:
        """Private helper method for calculations."""
        # Implementation here
        return {"total_games": len(matches)}
```

### 3. Use in Endpoint

```python
# app/api/players.py
from ..api.dependencies import PlayerServiceDep

@router.get("/{puuid}/stats")
async def get_player_stats(
    puuid: str,
    player_service: PlayerServiceDep,
):
    return await player_service.get_player_stats(puuid)
```

---

## 🏗️ Service Architecture

### Service Responsibilities

**Services handle**:
- ✅ Business logic and validation
- ✅ Database queries and updates
- ✅ Riot API integration (via `RiotDataManager`)
- ✅ Data transformation and aggregation
- ✅ Transaction management
- ✅ Structured logging with context

**Services DO NOT**:
- ❌ Handle HTTP requests directly (that's endpoints)
- ❌ Validate request schemas (that's Pydantic)
- ❌ Call `RiotAPIClient` directly (use `RiotDataManager`)
- ❌ Return HTTP exceptions (raise domain exceptions)

### Dependency Injection Pattern

**Services receive dependencies via constructor**:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from ..riot_api.data_manager import RiotDataManager

class PlayerService:
    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        self.db = db
        self.data_manager = riot_data_manager
```

**Registered in `dependencies.py`**:

```python
# app/api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..riot_api.client import RiotAPIClient
from ..riot_api.data_manager import RiotDataManager
from ..services.players import PlayerService

async def get_riot_client() -> RiotAPIClient:
    return RiotAPIClient()

async def get_data_manager(
    db: AsyncSession = Depends(get_db),
    client: RiotAPIClient = Depends(get_riot_client),
) -> RiotDataManager:
    return RiotDataManager(db, client)

async def get_player_service(
    db: AsyncSession = Depends(get_db),
    data_manager: RiotDataManager = Depends(get_data_manager),
) -> PlayerService:
    return PlayerService(db, data_manager)
```

---

## 🔄 Database Patterns

### Basic Query

```python
from sqlalchemy import select
from ..models.players import Player

async def get_player(self, puuid: str) -> Player | None:
    """Get player by PUUID."""
    # Option 1: Simple get by primary key
    player = await self.db.get(Player, puuid)

    # Option 2: Query with conditions
    stmt = select(Player).where(Player.puuid == puuid)
    result = await self.db.execute(stmt)
    player = result.scalar_one_or_none()

    return player
```

### Query with Filters

```python
from sqlalchemy import select, and_, or_
from ..models.players import Player

async def search_players(
    self,
    game_name: str | None = None,
    is_tracked: bool | None = None,
) -> list[Player]:
    """Search players with filters."""
    stmt = select(Player)

    filters = []
    if game_name:
        filters.append(Player.game_name.ilike(f"%{game_name}%"))
    if is_tracked is not None:
        filters.append(Player.is_tracked == is_tracked)

    if filters:
        stmt = stmt.where(and_(*filters))

    result = await self.db.execute(stmt)
    return list(result.scalars().all())
```

### Insert/Update

```python
from ..models.players import Player

async def update_player(self, puuid: str, data: dict) -> Player:
    """Update player data."""
    player = await self.db.get(Player, puuid)
    if not player:
        raise ValueError("Player not found")

    # Update fields
    for key, value in data.items():
        setattr(player, key, value)

    await self.db.commit()
    await self.db.refresh(player)
    return player
```

### Transaction Management

```python
async def complex_operation(self, puuid: str):
    """Perform complex multi-step operation."""
    try:
        # Multiple DB operations
        player = await self.db.get(Player, puuid)
        player.is_tracked = True

        # Fetch and store matches
        matches = await self.data_manager.get_match_history(puuid, count=20)

        # Commit transaction
        await self.db.commit()
        logger.info("operation_success", puuid=puuid)

    except Exception as e:
        await self.db.rollback()
        logger.error("operation_failed", puuid=puuid, error=str(e))
        raise
```

### Pagination

```python
from sqlalchemy import select, func

async def list_players(
    self,
    skip: int = 0,
    limit: int = 10,
) -> tuple[list[Player], int]:
    """List players with pagination."""
    # Get paginated results
    stmt = select(Player).offset(skip).limit(limit)
    result = await self.db.execute(stmt)
    players = list(result.scalars().all())

    # Get total count
    count_stmt = select(func.count(Player.puuid))
    total = await self.db.scalar(count_stmt)

    return players, total
```

---

## 🌐 Riot API Integration

### Always Use RiotDataManager

```python
# ✅ GOOD - Use data manager
async def fetch_player(self, game_name: str, tag_line: str, platform: str):
    player = await self.data_manager.get_player_by_riot_id(
        game_name=game_name,
        tag_line=tag_line,
        platform=platform
    )
    if not player:
        raise ValueError("Player not found or rate limited")
    return player

# ❌ BAD - Don't call client directly
from ..riot_api.client import RiotAPIClient

async def fetch_player(self, game_name: str, tag_line: str):
    client = RiotAPIClient()
    data = await client.get_account(game_name, tag_line)  # Don't do this!
```

### Handle Rate Limiting

**RiotDataManager returns `None` on rate limit (no exception)**:

```python
async def fetch_matches(self, puuid: str) -> list:
    matches = await self.data_manager.get_match_history(puuid, count=20)

    if matches is None:
        logger.warning("rate_limit_hit", puuid=puuid)
        return []  # Return empty list or handle gracefully

    return matches
```

### Common Data Manager Methods

```python
# Get player by Riot ID (name#tag)
player = await self.data_manager.get_player_by_riot_id(
    game_name="Player", tag_line="EUW", platform="eun1"
)

# Get player by PUUID
player = await self.data_manager.get_player_by_puuid(puuid="...")

# Get match history
matches = await self.data_manager.get_match_history(
    puuid="...", count=20, queue_id=420  # queue_id optional
)

# Get single match
match = await self.data_manager.get_match(match_id="EUN1_1234567890")

# Get player rank
rank = await self.data_manager.get_player_rank(
    summoner_id="...", platform="eun1"
)
```

---

## 📝 Structured Logging

### Use structlog with Context

```python
import structlog

logger = structlog.get_logger(__name__)

async def track_player(self, puuid: str):
    """Track a player for monitoring."""
    logger.info("tracking_player", puuid=puuid)

    player = await self.db.get(Player, puuid)
    if not player:
        logger.warning("player_not_found", puuid=puuid)
        raise ValueError("Player not found")

    player.is_tracked = True
    await self.db.commit()

    logger.info(
        "player_tracked_successfully",
        puuid=puuid,
        game_name=player.game_name,
        tag_line=player.tag_line
    )
```

### Log Levels

```python
# INFO - Normal operations
logger.info("operation_started", puuid=puuid, count=10)

# WARNING - Non-critical issues
logger.warning("rate_limit_hit", puuid=puuid)

# ERROR - Errors that need attention
logger.error("database_error", puuid=puuid, error=str(e))

# DEBUG - Detailed diagnostic info
logger.debug("processing_match", match_id=match_id, participant_count=10)
```

---

## 🧪 Testing Services

### Basic Service Test

```python
# tests/services/test_players.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.players import PlayerService
from app.models.players import Player

@pytest.mark.asyncio
async def test_get_player(db: AsyncSession, riot_data_manager_mock):
    """Test player retrieval."""
    # Setup
    service = PlayerService(db, riot_data_manager_mock)
    player = Player(puuid="test-puuid", game_name="TestPlayer")
    db.add(player)
    await db.commit()

    # Execute
    result = await service.get_player("test-puuid")

    # Assert
    assert result is not None
    assert result.puuid == "test-puuid"
    assert result.game_name == "TestPlayer"
```

### Mocking RiotDataManager

```python
from unittest.mock import AsyncMock

@pytest.fixture
def riot_data_manager_mock():
    """Mock data manager for tests."""
    mock = AsyncMock()
    mock.get_player_by_riot_id.return_value = Player(
        puuid="test-puuid",
        game_name="TestPlayer",
        tag_line="EUW"
    )
    return mock
```

---

## 🚨 Common Pitfalls

1. **Don't forget to commit**
   - ✅ `await self.db.commit()` after changes
   - ❌ Changes without commit are lost

2. **Don't call RiotAPIClient directly**
   - ✅ Use `self.data_manager.get_player_by_riot_id(...)`
   - ❌ Don't instantiate/call `RiotAPIClient`

3. **Don't catch generic exceptions**
   - ✅ Catch specific: `except ValueError`, `except SQLAlchemyError`
   - ❌ Don't use bare `except Exception`

4. **Don't block the event loop**
   - ✅ Use `async def` and `await` for I/O
   - ❌ No `time.sleep()`, use `asyncio.sleep()`

5. **Don't mix transaction contexts**
   - ✅ Use one database session per request
   - ❌ Don't create multiple sessions in one flow

6. **Don't return database models directly to API**
   - ✅ Convert to Pydantic schema in endpoint
   - ❌ Don't expose SQLAlchemy models in response

---

## 🔗 Related Files

- **`../api/dependencies.py`** - Service dependency injection setup
- **`../riot_api/data_manager.py`** - Primary interface for Riot API
- **`../models/`** - SQLAlchemy database models
- **`../schemas/`** - Pydantic request/response schemas
- **`../database.py`** - Database session management

---

## 🔍 Keywords

Service layer, business logic, SQLAlchemy, async, database queries, transactions, RiotDataManager, dependency injection, structlog, testing, mocking

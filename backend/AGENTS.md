# Backend Development Guide

**WHEN TO USE THIS**: Working on Python backend, FastAPI endpoints, Riot API integration, player analysis, or background jobs.

**QUICK NAVIGATION**: Need to add/modify? → [Jump to Common Tasks](#common-tasks)

---

## 📁 File Structure Map

```
backend/app/
├── main.py                      # FastAPI app setup, CORS, middleware, startup/shutdown
├── config.py                    # Settings (Pydantic BaseSettings), env vars
├── database.py                  # SQLAlchemy async engine, session management
├── protocols.py                 # Type protocols for dependency injection
│
├── api/                         # 🔍 API endpoints (FastAPI routers)
│   ├── players.py              # Player search, tracking, rank endpoints
│   ├── matches.py              # Match history, stats, encounters
│   ├── detection.py            # Smurf detection analysis endpoints
│   ├── jobs.py                 # Job management and execution endpoints
│   └── dependencies.py         # FastAPI Depends() factories
│
├── services/                    # 🧠 Business logic layer
│   ├── players.py              # Player data operations, tracking
│   ├── matches.py              # Match retrieval, statistics
│   ├── detection.py            # Smurf detection orchestration
│   ├── stats.py                # Statistical analysis, aggregations
│   └── jobs.py                 # Job configuration management
│
├── riot_api/                    # 🌐 Riot Games API integration
│   ├── client.py               # HTTP client with auth & rate limiting
│   ├── data_manager.py         # Database-first data fetching (PRIMARY)
│   ├── rate_limiter.py         # Token bucket rate limiting
│   ├── transformers.py         # API response → DB model conversion
│   ├── endpoints.py            # Riot API endpoint definitions
│   ├── errors.py               # Custom exception classes
│   └── models.py               # Pydantic models for API responses
│
├── algorithms/                  # 🔍 Smurf detection algorithms
│   ├── win_rate.py             # Win rate pattern analysis
│   ├── rank_progression.py     # Rank climbing detection
│   └── performance.py          # Performance consistency analysis
│
├── jobs/                        # ⏰ Background job system
│   ├── scheduler.py            # APScheduler setup & lifecycle
│   ├── base.py                 # BaseJob class (extend for new jobs)
│   ├── tracked_player_updater.py  # Fetch matches for tracked players
│   ├── player_analyzer.py      # Run smurf detection on discovered players
│   └── log_handler.py          # Job execution logging
│
├── models/                      # 📊 SQLAlchemy ORM models
│   ├── players.py              # Player table
│   ├── matches.py              # Match table
│   ├── participants.py         # Match participant table
│   ├── ranks.py                # Player rank history
│   ├── smurf_detection.py      # Detection results
│   └── job_tracking.py         # Job configs & executions
│
├── schemas/                     # ✅ Pydantic validation schemas
│   └── (request/response models for API)
│
└── tests/                       # 🧪 Test suite
    ├── api/                    # API endpoint tests
    ├── services/               # Service layer tests
    ├── riot_api/               # Riot API client tests
    └── jobs/                   # Background job tests
```

---

## 🎯 Common Tasks

### I want to add a new API endpoint

1. **Choose/create router**: `app/api/<domain>.py` (e.g., `players.py`)
2. **Define endpoint**:

   ```python
   from fastapi import APIRouter, Depends
   from ..api.dependencies import PlayerServiceDep

   router = APIRouter(prefix="/players", tags=["players"])

   @router.get("/{puuid}/stats")
   async def get_player_stats(
       puuid: str,
       player_service: PlayerServiceDep,
   ):
       return await player_service.get_stats(puuid)
   ```

3. **Register in `main.py`**: Already done if router exists
4. **See**: `app/api/AGENTS.md` for patterns

### I want to add business logic

1. **Add to existing service**: `app/services/<domain>.py`
2. **Example**:

   ```python
   # app/services/players.py
   from sqlalchemy.ext.asyncio import AsyncSession
   from ..riot_api.data_manager import RiotDataManager
   import structlog

   logger = structlog.get_logger(__name__)

   class PlayerService:
       def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
           self.db = db
           self.data_manager = riot_data_manager

       async def my_new_method(self, puuid: str):
           logger.info("doing_thing", puuid=puuid)
           # Business logic here
   ```

3. **See**: `app/services/AGENTS.md` for patterns

### I want to fetch data from Riot API

1. **ALWAYS use `RiotDataManager`** (not `RiotAPIClient` directly)
2. **Pattern**:

   ```python
   from ..riot_api.data_manager import RiotDataManager

   # Inside service class
   player = await self.data_manager.get_player_by_riot_id(
       game_name="Player", tag_line="EUW", platform="eun1"
   )

   matches = await self.data_manager.get_match_history(
       puuid="player-puuid", count=20
   )
   ```

3. **See**: `app/riot_api/AGENTS.md` for data manager usage

### I want to add a smurf detection algorithm

1. **Create**: `app/algorithms/<name>.py`
2. **Implement**:

   ```python
   from typing import List
   from ..models.matches import Match

   class MyDetector:
       def calculate_confidence(self, matches: List[Match], **kwargs) -> float:
           """Return confidence score 0-100."""
           return 42.0
   ```

3. **Register**: Add to `SmurfDetectionService` in `app/services/detection.py`
4. **See**: `app/algorithms/AGENTS.md` for patterns

### I want to create a background job

1. **Create**: `app/jobs/<name>.py`
2. **Extend BaseJob**:

   ```python
   from .base import BaseJob
   from sqlalchemy.ext.asyncio import AsyncSession
   import structlog

   logger = structlog.get_logger(__name__)

   class MyJob(BaseJob):
       async def execute(self, db: AsyncSession) -> None:
           logger.info("job_starting", job_id=self.job_config.id)
           # Job logic
           self.increment_metric("records_processed", 10)
   ```

3. **Register**: Add to scheduler in `app/jobs/scheduler.py`
4. **See**: `app/jobs/AGENTS.md` for patterns

### I want to write tests

```bash
# Run all tests
docker compose exec backend uv run pytest

# Run specific test file
docker compose exec backend uv run pytest tests/api/test_players.py

# Run with coverage
docker compose exec backend uv run pytest --cov=app
```

**See**: `app/tests/AGENTS.md` for test patterns and fixtures

---

## 🛠️ Tech Stack

| Component           | Purpose       | Key Features                                   |
| ------------------- | ------------- | ---------------------------------------------- |
| **FastAPI**         | Web framework | Async, auto OpenAPI docs, dependency injection |
| **SQLAlchemy 2.0+** | ORM           | Async engine, declarative models               |
| **Pydantic v2**     | Validation    | Request/response schemas, settings             |
| **structlog**       | Logging       | Structured JSON logs with context              |
| **APScheduler**     | Job scheduler | Persistent jobs, async execution               |
| **httpx**           | HTTP client   | Async Riot API requests                        |
| **pytest**          | Testing       | Async support, fixtures, coverage              |

---

## ⚠️ Critical Conventions

### ✅ DO

- **Type hints on everything** (enforced by pyright)
- **Use async/await** for all I/O (DB, HTTP, file)
- **Use `RiotDataManager`** for all Riot API calls (handles caching, rate limits)
- **Log with context**: `logger.info("action", puuid=puuid, count=5)`
- **Service layer for logic**: Keep API endpoints thin
- **Dependency injection**: Use FastAPI `Depends()` pattern

### ❌ DON'T

- **Don't call `RiotAPIClient` directly** → Use `RiotDataManager` instead
- **Don't block event loop** → No `time.sleep()`, use `asyncio.sleep()`
- **Don't catch generic `Exception`** → Catch specific exceptions
- **Don't forget transactions** → Commit/rollback explicitly when needed
- **Don't hardcode config** → Use `app/config.py` settings

---

## 🔗 Related Documentation

- **`app/api/AGENTS.md`** - API endpoint patterns, dependency injection, error handling
- **`app/services/AGENTS.md`** - Service layer architecture, transaction handling
- **`app/riot_api/AGENTS.md`** - Riot API integration, data manager, rate limiting
- **`app/algorithms/AGENTS.md`** - Smurf detection algorithm implementation
- **`app/jobs/AGENTS.md`** - Background job creation, scheduler, monitoring
- **`app/tests/AGENTS.md`** - Testing patterns, fixtures, mocking
- **`../docker/postgres/AGENTS.md`** - Database schema, queries, performance tuning

---

## 🚨 Common Pitfalls

1. **Hot reload only works for code changes**

   - Changing dependencies requires rebuild: `docker compose build backend`
   - Modifying Dockerfile requires rebuild

2. **Rate limiting returns `None`, not exceptions**

   - Check for `None` return from `RiotDataManager` methods
   - Log and handle gracefully

3. **Database sessions must be closed**

   - Use FastAPI's `Depends(get_db)` (auto-closes)
   - Or use `async with` for manual session management

4. **Riot API dev keys expire every 24h**

   - Update `RIOT_API_KEY` in `.env` when you get 403 errors
   - Get new key: https://developer.riotgames.com

5. **Jobs can timeout**
   - Default: 10 minutes (`JOB_TIMEOUT_SECONDS`)
   - Long-running jobs should process in batches

---

## 🔍 Keywords for Search

Backend, FastAPI, Python, async, SQLAlchemy, Riot API, smurf detection, background jobs, scheduler, API endpoints, service layer, data manager, rate limiting, testing, pytest, dependency injection, ORM, Pydantic validation

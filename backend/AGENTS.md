# Backend Development Guide

Backend-specific patterns and implementation details. **See root `AGENTS.md` for common Docker/testing/database commands.**

## Directory Structure
- `app/api/` - FastAPI endpoints (players, matches, detection, jobs)
- `app/services/` - Business logic (players, matches, detection, stats, jobs)
- `app/models/` - SQLAlchemy models (see `docker/postgres/AGENTS.md`)
- `app/riot_api/` - HTTP client with rate limiting
- `app/algorithms/` - Smurf detection (win_rate, rank_progression, performance)
- `app/jobs/` - Background job system (scheduler, tracked player updater, player analyzer)
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

## Background Job System

The application includes an automated job system for continuous data fetching and player analysis.

### Job Configuration

Jobs are configured via environment variables in `.env`:

```bash
# Enable/disable the job scheduler
JOB_SCHEDULER_ENABLED=true

# How often jobs run (default: every 2 minutes = 120 seconds)
JOB_INTERVAL_SECONDS=120

# Job timeout (default: 90 seconds)
JOB_TIMEOUT_SECONDS=90

# Maximum tracked players (default: 10)
MAX_TRACKED_PLAYERS=10
```

### Job Types

**1. Tracked Player Updater Job** (`tracked_player_updater.py`)
- Runs every 2 minutes (configurable)
- Fetches new matches for players marked as "tracked" (`is_tracked=True`)
- Updates player rank information
- Discovers new players from match participants
- Respects API rate limits with automatic backoff

**2. Player Analyzer Job** (`player_analyzer.py`)
- Runs after the Tracked Player Updater
- Analyzes discovered players for smurf/boosted behavior
- Runs detection algorithms on players marked `is_analyzed=False`
- Checks ban status for previously detected accounts (every 7 days)

### Managing Tracked Players

**Track a player** (via API or frontend UI):
```bash
curl -X POST http://localhost:8000/api/v1/players/{puuid}/track
```

**Untrack a player**:
```bash
curl -X DELETE http://localhost:8000/api/v1/players/{puuid}/track
```

**List tracked players**:
```bash
curl http://localhost:8000/api/v1/players/tracked
```

### Monitoring Jobs

**View job status**:
```bash
curl http://localhost:8000/api/v1/jobs/status/overview
```

**View job execution history**:
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/executions
```

**Manually trigger a job**:
```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/trigger
```

### Job Architecture

Jobs extend the `BaseJob` class which provides:
- Automatic execution tracking (start time, end time, status)
- Metrics collection (API requests, records created/updated)
- Error handling and logging
- Database transaction management

Example job structure:
```python
from app.jobs.base import BaseJob

class MyCustomJob(BaseJob):
    def __init__(self, job_config: JobConfiguration):
        super().__init__(job_config)
        # Extract config
        self.my_setting = job_config.config_json.get("my_setting", "default")

    async def execute(self, db: AsyncSession) -> None:
        # Job logic here
        logger.info("Job starting", job_id=self.job_config.id)

        # Track metrics
        self.increment_metric("api_requests_made", 1)
        self.increment_metric("records_created", 5)

        # Add custom log entries
        self.add_log_entry("custom_metric", 123)

        logger.info("Job complete")
```

### Job Lifecycle

1. **Startup**: When the backend starts, the scheduler:
   - Marks stale "running" jobs as failed
   - Loads active job configurations from database
   - Schedules jobs based on their interval settings

2. **Execution**: When a job runs:
   - Creates a `JobExecution` record (status: "running")
   - Executes the job's `execute()` method
   - Updates the record with results (status: "success" or "failed")
   - Logs metrics (API requests, records created/updated, execution time)

3. **Shutdown**: When the backend stops:
   - Gracefully shuts down the scheduler
   - Waits for running jobs to complete (with timeout)

### Troubleshooting

**Jobs not running:**
- Check `JOB_SCHEDULER_ENABLED=true` in `.env`
- Verify backend logs for scheduler startup messages
- Check database for active job configurations

**Rate limit errors:**
- Jobs automatically back off when rate limits are hit
- Check `job_executions` table for error messages
- Adjust `JOB_INTERVAL_SECONDS` to run less frequently

**Job stuck in "running" state:**
- On next startup, stale jobs are automatically marked as failed
- Or manually update: `UPDATE job_executions SET status='failed' WHERE status='running'`

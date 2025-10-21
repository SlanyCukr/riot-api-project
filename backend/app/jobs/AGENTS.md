# Background Jobs System

## Tech Stack
- APScheduler for job scheduling
- BaseJob class for inheritance
- Job execution tracking with metrics
- Structured logging with correlation IDs
- Graceful rate limit handling

## Overview
The job system uses APScheduler for scheduling and a modular architecture
with specialized job types for different responsibilities.

## Job Types

### 1. TRACKED_PLAYER_UPDATER
- **Purpose**: Fetch new matches for manually tracked players
- **API Usage**: HIGH (fetches match history from Riot API)
- **Frequency**: Every 2 minutes (configurable)
- **Configuration**:
  - `max_new_matches_per_player`: Maximum matches to fetch per player
  - `max_tracked_players`: Maximum players to process per run

### 2. MATCH_FETCHER
- **Purpose**: Fetch match history for discovered players
- **API Usage**: HIGH (fetches match history from Riot API)
- **Frequency**: Frequent (configurable, respects rate limits)
- **Configuration**:
  - `discovered_players_per_run`: Players to process per run
  - `matches_per_player_per_run`: Matches to fetch per player
  - `target_matches_per_player`: Target match count before marking exhausted

### 3. SMURF_ANALYZER
- **Purpose**: Analyze players for smurf/boosted behavior
- **API Usage**: NONE (pure database analysis)
- **Frequency**: Can run very frequently (no API limits)
- **Configuration**:
  - `unanalyzed_players_per_run`: Players to analyze per run
  - `min_matches_required`: Minimum matches needed for analysis

### 4. BAN_CHECKER
- **Purpose**: Check if flagged players have been banned
- **API Usage**: LOW (infrequent ban status checks)
- **Frequency**: Daily (configurable)
- **Configuration**:
  - `ban_check_days`: Days since last check
  - `max_checks_per_run`: Maximum players to check per run

## Project Structure

- `scheduler.py` - APScheduler setup and lifecycle
- `base.py` - BaseJob class (extend this)
- `error_handling.py` - Error handling utilities and decorators
- `log_capture.py` - Structured logging for job execution
- `tracked_player_updater.py` - Fetch matches for tracked players
- `match_fetcher.py` - Fetch matches for discovered players
- `smurf_analyzer.py` - Analyze players for smurf behavior
- `ban_checker.py` - Check ban status for flagged players

## Architecture

### Job Status Lifecycle
- `PENDING`: Job created but not started
- `RUNNING`: Job actively executing
- `SUCCESS`: Job completed successfully
- `FAILED`: Job encountered an error
- `RATE_LIMITED`: Job hit API rate limit (not a failure - will retry)

### Rate Limit Handling
Jobs gracefully handle rate limits using `RateLimitSignal`:
- When Riot API returns 429, jobs stop and save progress
- Status set to `RATE_LIMITED` (not `FAILED`)
- Scheduler will retry on next scheduled run
- No data loss - progress is committed before stopping

### Error Handling Decorator
Use `@handle_riot_api_errors()` for consistent API error handling:

```python
@handle_riot_api_errors(
    operation="fetch player matches",
    critical=False,  # Don't fail entire job on single player error
    log_context=lambda self, player: {"puuid": player.puuid}
)
async def _fetch_player_matches(self, player):
    # Your implementation
    pass
```

**Parameters:**
- `operation`: Description for logs (e.g., "fetch matches")
- `critical`: If True, re-raise exceptions. If False, log and return None
- `log_context`: Function to extract context from args for structured logging

**Error behavior:**
- `RateLimitError` → Converts to `RateLimitSignal` (graceful termination)
- `AuthenticationError`/`ForbiddenError` → Always re-raises (critical)
- Other exceptions → Log error, re-raise if `critical=True`, else return `None`

## Creating New Jobs

1. **Extend `BaseJob`**:
```python
from .base import BaseJob
from .error_handling import handle_riot_api_errors

class MyJob(BaseJob):
    def __init__(self, job_config_id: int):
        super().__init__(job_config_id)

    def _load_configuration(self) -> None:
        # Load and validate config from self.job_config.config_json
        config = self.job_config.config_json or {}
        self.my_setting = config.get("my_setting")

        # Validate required fields
        if self.my_setting is None:
            raise ValueError("Missing required config: my_setting")

    async def execute(self, db: AsyncSession) -> None:
        self._load_configuration()
        # Your job logic here
        self.increment_metric("records_created")
```

2. **Add job type to enum** (`backend/app/models/job_tracking.py`):
```python
class JobType(str, PyEnum):
    MY_JOB = "MY_JOB"  # Use UPPERCASE
```

3. **Create Alembic migration** to seed default config:
```bash
./scripts/alembic.sh revision -m "add my_job config"
```

Example migration content:
```python
def upgrade():
    op.execute("""
        INSERT INTO app.job_configurations (
            job_type, name, schedule, is_active, config_json
        ) VALUES (
            'MY_JOB',
            'My Job',
            'interval(seconds=300)',
            true,
            '{"my_setting": 100}'::jsonb
        )
    """)
```

4. **Register in API** (`backend/app/api/jobs.py`):
```python
job_type_mapping = {
    JobType.MY_JOB: MyJob,
}
```

## Job Configuration

Job configs are stored in the `job_configurations` table and seeded via Alembic migrations (NOT entrypoint.sh).

See migration `67d72b54c74e_seed_initial_job_configurations.py` for examples.

## Commands

- Monitor via `/api/v1/jobs/status/overview`
- Manual trigger: `POST /api/v1/jobs/{id}/trigger`
- View logs: `./scripts/logs.sh backend`
- Check migrations: `./scripts/alembic.sh current`

## Monitoring

- **API**: `GET /api/v1/jobs/status/overview` - System status
- **API**: `GET /api/v1/jobs/{id}/executions` - Job execution history
- **Logs**: `./scripts/logs.sh backend` - View job logs
- **Metrics**: Each job tracks `api_requests_made`, `records_created`, `records_updated`

## Code Style

- Use `@handle_riot_api_errors()` for all API operations
- Track metrics with `self.increment_metric()`
- Use `self.safe_commit()` for database operations
- Load configuration in `_load_configuration()` and validate required fields
- Use structured logging: `logger.info("action", key=value)`
- Use UPPERCASE for enum values (e.g., `MY_JOB` not `my_job`)

## Do Not

- Don't call Riot API directly (use services/RiotDataManager)
- Don't catch `RateLimitSignal` (let it propagate to base class)
- Don't commit transactions manually (use `self.safe_commit()`)
- Don't block event loop (use `asyncio.sleep()`, not `time.sleep()`)
- Don't use lowercase enum values (use UPPERCASE)
- Don't forget to call `super().__init__()`
- Don't catch exceptions silently
# Background Jobs Feature

## Overview

The jobs feature manages background task scheduling and execution using APScheduler. This feature has unique architecture with job implementations, error handling, and execution tracking.

**See `README.md` for comprehensive API documentation and component descriptions.**

## Unique Architecture

Unlike standard features, jobs has:
- **`implementations/` subdirectory** - Concrete job implementations
- **`base.py`** - Abstract BaseJob class and job registry
- **`scheduler.py`** - APScheduler configuration and management
- **`error_handling.py`** - Riot API rate limit handling decorator
- **`log_capture.py`** - Job execution logging utilities

### Directory Structure

```
jobs/
├── __init__.py
├── router.py               # Job control endpoints
├── service.py              # Job management logic
├── models.py               # JobConfiguration, JobExecution models
├── schemas.py
├── dependencies.py
├── base.py                 # BaseJob abstract class, job registry
├── scheduler.py            # APScheduler setup and lifecycle
├── error_handling.py       # @handle_riot_api_errors decorator
├── log_capture.py          # Execution log capture
├── apscheduler_models.py   # APScheduler table metadata
├── implementations/        # Concrete job implementations
│   ├── tracked_player_updater.py
│   ├── match_fetcher.py
│   ├── smurf_analyzer.py
│   └── ban_checker.py
├── tests/
└── README.md
```

## Job System Architecture

### Job Types

Four specialized background jobs:

1. **Tracked Player Updater** - Updates tracked player data (every 15 min)
2. **Match Fetcher** - Fetches new matches for tracked players (every 30 min)
3. **Smurf Analyzer** - Runs smurf detection on tracked players (daily)
4. **Ban Checker** - Checks for banned accounts (daily)

### Job States

```python
class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"  # Riot API rate limit hit
```

### Job Lifecycle

```
┌─────────────┐
│   PENDING   │  Job scheduled
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ IN_PROGRESS │  Executing
└──────┬──────┘
       │
       ├─────────────┬─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
┌───────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────┐
│ COMPLETED │ │  FAILED  │ │RATE_LIMITED │ │ SKIPPED │
└───────────┘ └──────────┘ └─────────────┘ └─────────┘
```

## BaseJob Pattern

All jobs inherit from `BaseJob`:

```python
# base.py
from abc import ABC, abstractmethod
from datetime import datetime
import structlog

logger = structlog.get_logger()

class BaseJob(ABC):
    """Base class for all background jobs."""

    job_id: str           # Unique identifier
    name: str             # Human-readable name
    description: str      # What the job does
    default_schedule: str # Cron expression

    def __init__(self, job_id: str):
        self.job_id = job_id

    @abstractmethod
    async def execute(self, db: AsyncSession) -> dict:
        """Execute the job logic.

        :param db: Database session
        :returns: Execution result dict
        :raises: Any exception on failure
        """
        pass

    async def run(self, db: AsyncSession) -> JobExecution:
        """Run job with execution tracking.

        :param db: Database session
        :returns: JobExecution record
        """
        execution = JobExecution(
            job_id=self.job_id,
            status=JobStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(execution)
        await db.commit()

        try:
            result = await self.execute(db)
            execution.status = JobStatus.COMPLETED
            execution.result_data = result
            logger.info("job_completed", job_id=self.job_id)
        except RateLimitError:
            execution.status = JobStatus.RATE_LIMITED
            logger.warning("job_rate_limited", job_id=self.job_id)
        except Exception as e:
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            logger.error("job_failed", job_id=self.job_id, error=str(e))
        finally:
            execution.completed_at = datetime.utcnow()
            await db.commit()

        return execution
```

## Implementing a Job

### Example: Tracked Player Updater

```python
# implementations/tracked_player_updater.py
from app.features.jobs.base import BaseJob
from app.features.jobs.error_handling import handle_riot_api_errors
from app.features.players import PlayerService

class TrackedPlayerUpdater(BaseJob):
    """Updates tracked player data."""

    job_id = "TRACKED_PLAYER_UPDATER"
    name = "Tracked Player Updater"
    description = "Fetches new matches for all tracked players"
    default_schedule = "*/15 * * * *"  # Every 15 minutes

    def __init__(self, riot_data_manager: RiotDataManager):
        super().__init__(self.job_id)
        self.riot_data_manager = riot_data_manager

    @handle_riot_api_errors
    async def execute(self, db: AsyncSession) -> dict:
        """Execute tracked player update.

        :param db: Database session
        :returns: Execution summary
        """
        logger.info("tracked_player_updater_starting")

        # Get all tracked players
        result = await db.execute(
            select(Player).where(Player.is_tracked == True)
        )
        tracked_players = result.scalars().all()

        updated_count = 0
        for player in tracked_players:
            try:
                # Fetch new data from Riot API
                await self._update_player(player, db)
                updated_count += 1
            except Exception as e:
                logger.error(
                    "player_update_failed",
                    puuid=player.puuid,
                    error=str(e)
                )
                continue

        return {
            "total_tracked": len(tracked_players),
            "updated": updated_count,
            "failed": len(tracked_players) - updated_count
        }

    async def _update_player(self, player: Player, db: AsyncSession):
        """Update single player data."""
        # Implementation details...
        pass
```

### Job Registration

Register jobs in `__init__.py`:

```python
# __init__.py
from .base import job_registry
from .implementations.tracked_player_updater import TrackedPlayerUpdater
from .implementations.match_fetcher import MatchFetcher
from .implementations.smurf_analyzer import SmurfAnalyzer
from .implementations.ban_checker import BanChecker

# Register all job implementations
def initialize_jobs(riot_data_manager: RiotDataManager):
    """Register all job implementations.

    :param riot_data_manager: Riot data manager dependency
    """
    job_registry.register(TrackedPlayerUpdater(riot_data_manager))
    job_registry.register(MatchFetcher(riot_data_manager))
    job_registry.register(SmurfAnalyzer(riot_data_manager))
    job_registry.register(BanChecker(riot_data_manager))
```

## Scheduler Management

### APScheduler Setup (`scheduler.py`)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

class JobScheduler:
    """Manages APScheduler instance."""

    def __init__(self, database_url: str):
        jobstores = {
            'default': SQLAlchemyJobStore(url=database_url)
        }
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone='UTC'
        )

    async def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("scheduler_started")

    async def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("scheduler_stopped")

    def add_job(self, job: BaseJob, schedule: str):
        """Schedule a job.

        :param job: Job implementation
        :param schedule: Cron expression
        """
        self.scheduler.add_job(
            func=job.run,
            trigger='cron',
            **self._parse_cron(schedule),
            id=job.job_id,
            name=job.name,
            replace_existing=True
        )
```

### Scheduler Lifecycle

Scheduler starts/stops with FastAPI app:

```python
# main.py
from app.features.jobs import initialize_jobs, job_scheduler

@app.on_event("startup")
async def startup():
    """Start scheduler on app startup."""
    riot_data_manager = RiotDataManager()
    initialize_jobs(riot_data_manager)

    # Schedule all jobs
    for job in job_registry.get_all():
        config = await get_job_config(job.job_id)
        if config.enabled:
            job_scheduler.add_job(job, config.schedule)

    await job_scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    """Stop scheduler on app shutdown."""
    await job_scheduler.stop()
```

## Error Handling

### Riot API Rate Limit Handling

```python
# error_handling.py
from functools import wraps
from app.core.exceptions import RateLimitError

def handle_riot_api_errors(func):
    """Decorator for handling Riot API errors in jobs.

    :param func: Async function to wrap
    :returns: Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            logger.warning(
                "job_rate_limited",
                job=func.__name__,
                retry_after=e.retry_after
            )
            # Let job transition to RATE_LIMITED status
            raise
        except RiotAPIError as e:
            logger.error(
                "job_riot_api_error",
                job=func.__name__,
                status_code=e.status_code,
                error=str(e)
            )
            # Let job transition to FAILED status
            raise
    return wrapper
```

Usage:

```python
class MyJob(BaseJob):
    @handle_riot_api_errors
    async def execute(self, db: AsyncSession) -> dict:
        # Riot API calls here
        # Rate limits automatically handled
        pass
```

## Database Models

### JobConfiguration

```python
class JobConfiguration(BaseModel):
    """Job configuration model."""

    __tablename__ = "job_configurations"

    job_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    schedule = Column(String, nullable=False)  # Cron expression
    enabled = Column(Boolean, default=True, nullable=False)
    last_execution = Column(DateTime)
```

### JobExecution

```python
class JobExecution(BaseModel):
    """Job execution record."""

    __tablename__ = "job_executions"

    job_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    result_data = Column(JSON)
    error_message = Column(Text)
    logs = Column(Text)  # Captured stdout/stderr
```

## Job Control

### Manual Triggering

```python
@router.post("/jobs/{job_id}/trigger")
async def trigger_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """Manually trigger a job execution.

    :param job_id: Job identifier
    :param job_service: Job service dependency
    :returns: Execution record
    """
    execution = await job_service.trigger_job(job_id)
    return execution
```

### Enable/Disable Jobs

```python
@router.post("/jobs/{job_id}/enable")
async def enable_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Enable a job."""
    config = await get_job_config(job_id, db)
    config.enabled = True
    await db.commit()

    # Reschedule job
    job = job_registry.get(job_id)
    job_scheduler.add_job(job, config.schedule)

    return {"status": "enabled"}
```

## Adding a New Job

1. **Create job implementation** in `implementations/`:
   ```python
   class MyNewJob(BaseJob):
       job_id = "MY_NEW_JOB"
       name = "My New Job"
       description = "What it does"
       default_schedule = "0 */6 * * *"  # Every 6 hours

       @handle_riot_api_errors
       async def execute(self, db: AsyncSession) -> dict:
           # Job logic
           return {"result": "data"}
   ```

2. **Register in `__init__.py`**:
   ```python
   from .implementations.my_new_job import MyNewJob

   def initialize_jobs(riot_data_manager):
       job_registry.register(MyNewJob(riot_data_manager))
       # ... other jobs
   ```

3. **Create database migration** for job configuration:
   ```bash
   ./scripts/alembic.sh revision --autogenerate -m "Add MyNewJob configuration"
   ```

4. **Seed configuration** in migration:
   ```python
   def upgrade():
       op.execute("""
           INSERT INTO job_configurations (job_id, name, description, schedule, enabled)
           VALUES ('MY_NEW_JOB', 'My New Job', 'What it does', '0 */6 * * *', true)
       """)
   ```

5. **Add tests** in `tests/`

6. **Restart application** to load new job

## Testing

Test job logic independently from scheduler:

```python
@pytest.mark.asyncio
async def test_tracked_player_updater(db: AsyncSession):
    """Test tracked player updater job."""
    # Setup
    player = Player(puuid="test", is_tracked=True)
    db.add(player)
    await db.commit()

    # Execute
    job = TrackedPlayerUpdater(riot_data_manager)
    result = await job.execute(db)

    # Assert
    assert result["total_tracked"] == 1
    assert result["updated"] == 1
```

## Import Patterns

```python
# Using jobs feature from main.py
from app.features.jobs import initialize_jobs, job_scheduler

# Internal imports within feature
from .base import BaseJob, job_registry
from .error_handling import handle_riot_api_errors
from .implementations.tracked_player_updater import TrackedPlayerUpdater
```

## Monitoring

### Execution History

```bash
# Get recent executions
GET /api/v1/jobs/executions/recent?limit=10

# Get job-specific executions
GET /api/v1/jobs/{job_id}/executions?limit=10
```

### System Status

```bash
# Overall job system status
GET /api/v1/jobs/status/overview

# APScheduler status
GET /api/v1/jobs/scheduler/status
```

## See Also

- `README.md` - Comprehensive API documentation and component descriptions
- `backend/app/features/AGENTS.md` - General feature development guide
- `backend/app/core/AGENTS.md` - Core infrastructure
- `backend/MIGRATIONS.md` - Note about APScheduler table management

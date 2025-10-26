# Jobs Feature

## Purpose

Manages background job scheduling and execution for automated data updates, analysis tasks, and system maintenance. Provides job configuration, execution tracking, and centralized logging for all scheduled tasks.

## API Endpoints

### Job Management

- `GET /api/v1/jobs/` - List all configured jobs
- `GET /api/v1/jobs/{job_id}` - Get job configuration and status
- `PUT /api/v1/jobs/{job_id}` - Update job configuration
- `POST /api/v1/jobs/{job_id}/enable` - Enable a job
- `POST /api/v1/jobs/{job_id}/disable` - Disable a job

### Job Execution

- `POST /api/v1/jobs/{job_id}/trigger` - Manually trigger a job
- `GET /api/v1/jobs/{job_id}/executions` - Get execution history
- `GET /api/v1/jobs/executions/recent` - Get recent executions across all jobs

### System Status

- `GET /api/v1/jobs/status/overview` - Get system-wide job status
- `GET /api/v1/jobs/scheduler/status` - Get APScheduler status

## Key Components

### Router (`router.py`)

FastAPI router defining job control endpoints. Handles job configuration, triggering, and status retrieval.

### Service (`service.py`)

**JobService** - Core business logic for job management:

- Job configuration management
- Execution history tracking
- Job status monitoring
- Integration with scheduler

### Models (`models.py`)

**SQLAlchemy Models:**

- `JobConfiguration` - Job settings (ID, name, schedule, enabled status)
- `JobExecution` - Execution record (job ID, status, start/end times, logs, error messages)

### Schemas (`schemas.py`)

**Pydantic Schemas:**

- `JobConfigurationResponse` - Job configuration details
- `JobExecutionResponse` - Execution result and logs
- `JobStatusOverview` - System-wide job status summary
- `TriggerJobRequest` - Manual trigger request

### Scheduler (`scheduler.py`)

**APScheduler Setup:**

- Job scheduler initialization and configuration
- Cron schedule management
- Job registration and lifecycle management

### Base Job (`base.py`)

**BaseJob** - Abstract base class for all job implementations:

- Common job execution patterns
- Error handling integration
- Logging standardization
- Database session management

### Error Handling (`error_handling.py`)

**@handle_riot_api_errors** - Decorator for Riot API error handling:

- Rate limit management
- Retry logic with exponential backoff
- Error logging and tracking
- Graceful degradation

### Log Capture (`log_capture.py`)

Centralized job logging:

- Captures stdout/stderr during job execution
- Stores logs in database for historical review
- Provides log streaming for real-time monitoring

### Dependencies (`dependencies.py`)

- `get_job_service()` - Dependency injection for JobService
- `get_scheduler()` - Access to APScheduler instance

## Job Implementations

All job implementations are located in `implementations/`:

### 1. Tracked Player Updater (`tracked_player_updater.py`)

- **Purpose**: Updates data for all tracked players
- **Schedule**: Every 15 minutes
- **Operations**:
  - Fetches current rank for tracked players
  - Updates player summoner data
  - Checks for recent matches
  - Triggers match fetcher if new matches found

### 2. Match Fetcher (`match_fetcher.py`)

- **Purpose**: Retrieves new matches for tracked players
- **Schedule**: Every 30 minutes
- **Operations**:
  - Queries match history for tracked players
  - Fetches match details from Riot API
  - Stores match data and participant stats
  - Triggers player analysis for new matches

### 3. Player Analyzer (`player_analyzer.py`)

- **Purpose**: Runs player analysis on tracked players
- **Schedule**: Daily at 2:00 AM
- **Operations**:
  - Analyzes all tracked players for smurf indicators
  - Updates player analysis scores
  - Flags high-confidence smurf accounts
  - Generates analysis reports

### 4. Ban Checker (`ban_checker.py`)

- **Purpose**: Checks if tracked players are banned
- **Schedule**: Daily at 3:00 AM
- **Operations**:
  - Verifies account status via Riot API
  - Updates player status if banned
  - Logs ban events
  - Sends notifications (if configured)

## Dependencies

### Core Dependencies

- `core.database` - Database session management
- `core.config` - Application settings
- `core.riot_api` - Riot API client

### Feature Dependencies

- `features.players` - Player data management
- `features.matches` - Match data storage
- `features.player_analysis` - Player analysis execution

### External Libraries

- APScheduler - Job scheduling framework
- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Usage Examples

### Creating a New Job

```python
from app.features.jobs.base import BaseJob
from app.core.database import get_db

class MyCustomJob(BaseJob):
    job_id = "my_custom_job"
    job_name = "My Custom Job"

    async def execute(self):
        self.log("Starting custom job execution")

        # Your job logic here
        async for db in get_db():
            # Database operations
            pass

        self.log("Job completed successfully")
```

### Registering a Job with the Scheduler

```python
from app.features.jobs.scheduler import scheduler
from app.features.jobs.implementations.my_custom_job import MyCustomJob

# Register job with cron schedule
scheduler.add_job(
    MyCustomJob().run,
    trigger="cron",
    hour=4,
    minute=0,
    id="my_custom_job",
    name="My Custom Job",
    replace_existing=True
)
```

### Manually Triggering a Job

```python
from app.features.jobs.dependencies import get_job_service

async def trigger_job_example(
    job_service = Depends(get_job_service)
):
    execution = await job_service.trigger_job("tracked_player_updater")
    print(f"Job triggered. Execution ID: {execution.id}")
    print(f"Status: {execution.status}")
```

### Checking Job Status

```python
async def check_job_status(
    job_service = Depends(get_job_service)
):
    overview = await job_service.get_status_overview()

    print(f"Total Jobs: {overview.total_jobs}")
    print(f"Enabled Jobs: {overview.enabled_jobs}")
    print(f"Running Jobs: {overview.running_jobs}")

    for job in overview.jobs:
        print(f"{job.name}: {job.status}")
        print(f"  Last Run: {job.last_execution_time}")
        print(f"  Next Run: {job.next_execution_time}")
```

### Using Error Handling Decorator

```python
from app.features.jobs.error_handling import handle_riot_api_errors

class MyJob(BaseJob):
    @handle_riot_api_errors(max_retries=3, backoff_factor=2.0)
    async def execute(self):
        # This method will automatically retry on Riot API errors
        await self.call_riot_api()
```

## Job Execution Flow

1. **Scheduler Triggers Job** - APScheduler invokes job at scheduled time
2. **Create Execution Record** - JobExecution entry created with "running" status
3. **Execute Job Logic** - BaseJob.run() executes the job's execute() method
4. **Capture Logs** - Log capture records all output
5. **Handle Errors** - Error handling decorator manages API failures
6. **Update Execution Record** - Status updated to "completed" or "failed"
7. **Store Logs** - Execution logs saved to database

## Configuration

Job schedules can be configured via environment variables or database settings:

```python
# Environment variables
TRACKED_PLAYER_UPDATE_INTERVAL=15  # minutes
MATCH_FETCH_INTERVAL=30  # minutes
PLAYER_ANALYSIS_SCHEDULE="0 2 * * *"  # cron format
BAN_CHECK_SCHEDULE="0 3 * * *"  # cron format
```

## Monitoring and Troubleshooting

### View Recent Executions

```bash
curl http://localhost:8000/api/v1/jobs/executions/recent
```

### Check Specific Job

```bash
curl http://localhost:8000/api/v1/jobs/tracked_player_updater
```

### View Execution Logs

```bash
curl http://localhost:8000/api/v1/jobs/executions/{execution_id}
```

### Common Issues

**Job Not Running**

- Check if job is enabled: `GET /api/v1/jobs/{job_id}`
- Verify scheduler is running: `GET /api/v1/jobs/scheduler/status`
- Check execution logs for errors

**Rate Limiting**

- Jobs automatically handle Riot API rate limits
- If persistent, increase job intervals
- Check error handling configuration

**Database Locks**

- Jobs use separate database sessions
- Long-running jobs may need connection pool tuning
- Check for deadlocks in execution logs

## Related Features

- **Players** - Jobs update tracked player data
- **Matches** - Jobs fetch and store match data
- **Player Analysis** - Jobs run periodic player analysis
- All features can be integrated with the job system

## Future Enhancements

- Job prioritization and dependency management
- Dynamic schedule adjustment based on load
- Job failure alerting and notifications
- Job execution metrics and analytics
- Distributed job execution for scalability

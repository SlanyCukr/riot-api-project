# Background Jobs System Guide

**WHEN TO USE THIS**: Creating/modifying background jobs, managing scheduler, or monitoring job execution.

**QUICK START**: Creating job? → [Jump to Quick Recipe](#-quick-recipe-create-a-job)

---

## 📁 Job Files

```
backend/app/jobs/
├── scheduler.py                  # APScheduler setup & lifecycle
├── base.py                       # BaseJob class (extend this!)
├── tracked_player_updater.py     # Fetch matches for tracked players
├── player_analyzer.py            # Run smurf detection on players
└── log_handler.py                # Job execution logging utilities
```

---

## 🎯 Quick Recipe: Create a Job

### 1. Create Job File

**File**: `backend/app/jobs/<name>.py`

### 2. Extend BaseJob

```python
# app/jobs/rank_monitor.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import BaseJob
from ..models.players import Player
from ..models.job_tracking import JobConfiguration
import structlog

logger = structlog.get_logger(__name__)

class RankMonitor(BaseJob):
    """
    Monitor rank changes for tracked players.

    Checks for rank changes and logs significant movements.
    """

    def __init__(self, job_config: JobConfiguration):
        """Initialize with job configuration."""
        super().__init__(job_config)

        # Extract custom config (optional)
        self.rank_threshold = job_config.config_json.get("rank_threshold", 2)

    async def execute(self, db: AsyncSession) -> None:
        """
        Main job execution logic.

        Args:
            db: Database session (managed by scheduler)
        """
        logger.info(
            "rank_monitor_starting",
            job_id=self.job_config.id,
            threshold=self.rank_threshold
        )

        # Fetch tracked players
        stmt = select(Player).where(Player.is_tracked == True)
        result = await db.execute(stmt)
        players = list(result.scalars().all())

        logger.info("players_to_check", count=len(players))

        # Process each player
        rank_changes = 0
        for player in players:
            # Check rank changes (implement logic)
            changed = await self._check_rank_change(player, db)
            if changed:
                rank_changes += 1

        # Track metrics for monitoring
        self.increment_metric("players_checked", len(players))
        self.increment_metric("rank_changes_detected", rank_changes)

        # Add custom log entry
        self.add_log_entry("rank_changes", rank_changes)

        logger.info(
            "rank_monitor_complete",
            players_checked=len(players),
            rank_changes=rank_changes
        )

    async def _check_rank_change(self, player: Player, db: AsyncSession) -> bool:
        """Check if player's rank changed significantly."""
        # Implementation here
        return False
```

### 3. Register in Scheduler

```python
# app/jobs/scheduler.py
from .tracked_player_updater import TrackedPlayerUpdater
from .player_analyzer import PlayerAnalyzer
from .rank_monitor import RankMonitor  # Add import

class JobScheduler:
    # Job registry maps job names to classes
    JOB_REGISTRY = {
        "tracked_player_updater": TrackedPlayerUpdater,
        "player_analyzer": PlayerAnalyzer,
        "rank_monitor": RankMonitor,  # Add here
    }

    # Rest of scheduler implementation...
```

### 4. Create Job Configuration (via API or DB)

```bash
# Using API
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rank_monitor",
    "job_type": "rank_monitor",
    "interval_seconds": 300,
    "enabled": true,
    "config_json": {"rank_threshold": 2}
  }'

# Or manually in database
INSERT INTO job_configurations (name, job_type, interval_seconds, enabled, config_json)
VALUES ('rank_monitor', 'rank_monitor', 300, true, '{"rank_threshold": 2}');
```

---

## 🏗️ BaseJob Class

### Available Methods

```python
class BaseJob:
    """Base class for all background jobs."""

    def __init__(self, job_config: JobConfiguration):
        """Initialize with job configuration."""
        self.job_config = job_config
        self.metrics = {}  # For tracking execution metrics
        self.log_entries = {}  # For custom logging

    async def execute(self, db: AsyncSession) -> None:
        """
        OVERRIDE THIS: Main job execution logic.

        This is the only method you MUST implement.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def increment_metric(self, key: str, value: int = 1) -> None:
        """
        Track a metric during execution.

        Example:
            self.increment_metric("api_requests_made", 10)
            self.increment_metric("records_created", 5)
        """
        self.metrics[key] = self.metrics.get(key, 0) + value

    def add_log_entry(self, key: str, value: any) -> None:
        """
        Add custom data to job execution log.

        Example:
            self.add_log_entry("players_processed", 42)
            self.add_log_entry("errors_encountered", ["rate_limit", "timeout"])
        """
        self.log_entries[key] = value
```

### Metrics Tracking

```python
# Common metrics to track
self.increment_metric("api_requests_made", 15)
self.increment_metric("records_created", 10)
self.increment_metric("records_updated", 5)
self.increment_metric("errors_encountered", 2)

# Metrics are automatically saved to job_executions table
# Access via: GET /api/v1/jobs/executions/{execution_id}
```

---

## 📊 Existing Jobs

### Tracked Player Updater (`tracked_player_updater.py`)

**Purpose**: Fetch new matches for tracked players

**Runs**: Every 2 minutes (default)

**What it does**:
1. Fetches all tracked players (`is_tracked=True`)
2. Gets recent match IDs from Riot API
3. Fetches and stores new matches
4. Updates player rank information
5. Marks new players from matches for analysis

**Metrics tracked**:
- `players_updated`
- `new_matches_found`
- `api_requests_made`
- `new_players_discovered`

### Player Analyzer (`player_analyzer.py`)

**Purpose**: Run smurf detection on discovered players

**Runs**: Every 5 minutes (default)

**What it does**:
1. Finds players marked `is_analyzed=False`
2. Runs smurf detection algorithms
3. Stores detection results
4. Checks ban status for previously detected accounts

**Metrics tracked**:
- `players_analyzed`
- `smurfs_detected`
- `ban_checks_performed`

---

## ⚙️ Configuration

### Environment Variables

```bash
# .env file

# Enable/disable scheduler
JOB_SCHEDULER_ENABLED=true

# Global job interval (can be overridden per job)
JOB_INTERVAL_SECONDS=120

# Job timeout
JOB_TIMEOUT_SECONDS=600

# Maximum tracked players
MAX_TRACKED_PLAYERS=10
```

### Per-Job Configuration

```python
# Stored in job_configurations table
{
    "name": "tracked_player_updater",
    "job_type": "tracked_player_updater",
    "interval_seconds": 120,  # Run every 2 minutes
    "enabled": true,
    "config_json": {
        "max_matches_per_player": 20,
        "platforms": ["eun1", "euw1"]
    }
}
```

### Accessing Config in Job

```python
class MyJob(BaseJob):
    def __init__(self, job_config: JobConfiguration):
        super().__init__(job_config)

        # Access config values
        self.interval = job_config.interval_seconds
        self.custom_value = job_config.config_json.get("custom_key", "default")
```

---

## 🔄 Job Lifecycle

### 1. Application Startup

```python
# app/main.py
@app.on_event("startup")
async def startup_event():
    # Scheduler starts automatically
    await scheduler.start()

    # Marks stale jobs as failed
    # Loads active job configs from DB
    # Schedules jobs based on intervals
```

### 2. Job Execution

```
┌─────────────────────────────────────┐
│     Scheduler triggers job          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Create JobExecution record         │
│  Status: "running"                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Execute job.execute(db)            │
│  Track metrics & logs               │
└────────────┬────────────────────────┘
             │
         ┌───┴───┐
         │       │
    Success   Failure
         │       │
         ▼       ▼
    ┌─────┐  ┌────────┐
    │"success"│"failed"│
    └─────┘  └────────┘
         │       │
         └───┬───┘
             │
             ▼
┌─────────────────────────────────────┐
│  Update JobExecution record         │
│  - end_time                         │
│  - status                           │
│  - metrics                          │
│  - logs                             │
└─────────────────────────────────────┘
```

### 3. Application Shutdown

```python
# app/main.py
@app.on_event("shutdown")
async def shutdown_event():
    # Graceful shutdown
    await scheduler.shutdown(wait=True)

    # Waits for running jobs to complete
    # Or marks as failed after timeout
```

---

## 📈 Monitoring Jobs

### Via API

```bash
# Get job status overview
curl http://localhost:8000/api/v1/jobs/status/overview

# List all job configs
curl http://localhost:8000/api/v1/jobs/

# Get execution history
curl http://localhost:8000/api/v1/jobs/{job_id}/executions

# Get specific execution details
curl http://localhost:8000/api/v1/jobs/executions/{execution_id}
```

### Via Database

```sql
-- Recent job executions
SELECT
    jc.name,
    je.status,
    je.started_at,
    je.ended_at,
    je.metrics,
    je.log_data
FROM job_executions je
JOIN job_configurations jc ON je.job_id = jc.id
ORDER BY je.started_at DESC
LIMIT 20;

-- Failed jobs
SELECT * FROM job_executions
WHERE status = 'failed'
ORDER BY started_at DESC;

-- Job success rate
SELECT
    jc.name,
    COUNT(*) FILTER (WHERE je.status = 'success') as successes,
    COUNT(*) FILTER (WHERE je.status = 'failed') as failures,
    ROUND(
        COUNT(*) FILTER (WHERE je.status = 'success')::numeric / COUNT(*) * 100,
        2
    ) as success_rate
FROM job_executions je
JOIN job_configurations jc ON je.job_id = jc.id
GROUP BY jc.name;
```

---

## 🔧 Managing Jobs

### Enable/Disable Job

```bash
# Disable a job
curl -X PUT http://localhost:8000/api/v1/jobs/{job_id} \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Enable a job
curl -X PUT http://localhost:8000/api/v1/jobs/{job_id} \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Manually Trigger Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/trigger
```

### Update Job Interval

```bash
curl -X PUT http://localhost:8000/api/v1/jobs/{job_id} \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 300}'  # Every 5 minutes
```

---

## 🚨 Troubleshooting

### Job Not Running

**Check**:
1. Is scheduler enabled? `JOB_SCHEDULER_ENABLED=true`
2. Is job enabled in DB? `SELECT enabled FROM job_configurations WHERE id=...`
3. Check backend logs for scheduler startup messages
4. Verify job is registered in `JobScheduler.JOB_REGISTRY`

**Solution**:
```bash
# Restart backend to reload scheduler
./scripts/dev.sh
```

### Job Stuck in "running" State

**Cause**: Job crashed or was interrupted

**Solution**:
```sql
-- Mark as failed manually
UPDATE job_executions
SET status = 'failed',
    ended_at = NOW(),
    log_data = '{"error": "Marked as failed manually"}'
WHERE id = '<execution_id>';

-- Or restart backend (auto-marks stale jobs as failed)
./scripts/dev.sh
```

### Rate Limit Errors

**Symptoms**: Job executions show frequent rate limit warnings

**Solutions**:
1. **Increase interval**: Run less frequently
2. **Reduce batch size**: Process fewer items per execution
3. **Add delays**: Use `asyncio.sleep()` between API calls
4. **Upgrade API key**: Get production key with higher limits

```python
# Example: Add delay between requests
for player in players:
    await process_player(player)
    await asyncio.sleep(0.1)  # 100ms delay
```

### Job Timeout

**Symptoms**: Jobs marked as failed after 10 minutes

**Solutions**:
1. **Increase timeout**: Set `JOB_TIMEOUT_SECONDS=1200` (20 min)
2. **Process in batches**: Don't fetch all data at once
3. **Optimize queries**: Use pagination, indexes

```python
# Example: Process in batches
async def execute(self, db: AsyncSession):
    batch_size = 10
    offset = 0

    while True:
        stmt = select(Player).limit(batch_size).offset(offset)
        result = await db.execute(stmt)
        players = list(result.scalars().all())

        if not players:
            break

        await self.process_batch(players)
        offset += batch_size
```

---

## 🚨 Common Pitfalls

1. **Don't forget to call `super().__init__()`**
   - ✅ `super().__init__(job_config)` in `__init__()`
   - ❌ Forgetting breaks metrics/logging

2. **Don't commit transactions manually (usually)**
   - ✅ Scheduler handles commit/rollback
   - ❌ Manual `await db.commit()` can cause issues

3. **Don't block the event loop**
   - ✅ Use `async def` and `await`
   - ❌ No `time.sleep()`, use `asyncio.sleep()`

4. **Don't handle all exceptions silently**
   - ✅ Let exceptions bubble up (tracked by scheduler)
   - ❌ Catching and ignoring hides problems

5. **Don't forget to track metrics**
   - ✅ `self.increment_metric("records_processed", count)`
   - ❌ No visibility into job performance

---

## 🔗 Related Files

- **`scheduler.py`** - APScheduler setup and lifecycle
- **`base.py`** - BaseJob parent class
- **`../models/job_tracking.py`** - Database models for jobs
- **`../api/jobs.py`** - Job management API endpoints
- **`../services/jobs.py`** - Job service layer

---

## 🔍 Keywords

Background jobs, scheduler, APScheduler, async jobs, cron, job execution, monitoring, metrics, job configuration, tracked players, automation, data updates

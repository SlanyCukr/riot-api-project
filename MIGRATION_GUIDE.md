# Database Schema Update Guide

## Adding `detailed_logs` Column to Job Executions

This update adds a new `detailed_logs` JSONB column to the `job_executions` table to store all logs captured during job execution (INFO, WARNING, ERROR, etc.).

### Changes Made

1. **Backend Model** (`app/models/job_tracking.py`):
   - Added `detailed_logs` JSONB column to `JobExecution` model
   - Added to `to_dict()` method

2. **Backend Schema** (`app/schemas/jobs.py`):
   - Added `detailed_logs` field to `JobExecutionResponse` schema

3. **Frontend Schema** (`frontend/lib/schemas.ts`):
   - Added `detailed_logs` field to `JobExecutionSchema`

4. **Job Execution Logic** (`app/jobs/base.py`, `app/jobs/log_handler.py`):
   - Created `JobLogHandler` class to capture all logs during execution
   - Modified `BaseJob` to setup/teardown log capture
   - Logs are now automatically captured and stored in database

### Applying the Schema Changes

Since this project uses SQLAlchemy's `create_all()` approach (not Alembic migrations), you need to reset the database to apply schema changes.

#### For New Installations (Fresh Database)

No action needed! The column will be created automatically when you run:

```bash
docker compose exec backend uv run python -m app.init_db init
```

#### For Existing Databases

**⚠️ WARNING: This will delete all existing data!**

Reset the database to recreate all tables with the new schema:

```bash
docker compose exec backend uv run python -m app.init_db reset
```

Or use the production setup script which also reseeds the data:

```bash
./scripts/setup-production.sh
```

This will:
1. Drop all existing tables (deletes all data)
2. Recreate all tables with current schema (including `detailed_logs`)
3. Seed job configurations
4. Seed tracked players
5. Restart backend service

### Verifying the Migration

After running the migration, verify the column was added:

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "\d job_executions"
```

You should see the `detailed_logs` column listed as type `jsonb`.

### Testing the New Feature

1. Trigger a job manually:
   ```bash
   curl -X POST http://localhost:8000/api/v1/jobs/trigger/tracked_player_updater
   ```

2. Check the job execution to see the detailed logs:
   ```bash
   curl http://localhost:8000/api/v1/jobs/executions | jq '.executions[0].detailed_logs'
   ```

3. You should see a JSON object with:
   - `logs`: Array of all log entries captured during execution
   - `summary`: Summary with counts by log level, errors, and warnings

### Log Structure

Each log entry contains:
- `timestamp`: ISO timestamp when log was created
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger`: Logger name
- `message`: Log message
- `context`: Additional structured logging context (from structlog)
- `location`: File, line, and function where log was created
- `exception`: Exception details if present

The summary includes:
- `total_logs`: Total number of log entries
- `by_level`: Count of logs by level
- `errors`: List of error log entries
- `warnings`: List of warning log entries

### Rollback

If you need to remove the column:

```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "ALTER TABLE job_executions DROP COLUMN IF EXISTS detailed_logs;"
```

Note: This will delete all captured logs from existing job executions.

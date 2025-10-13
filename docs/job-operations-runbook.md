# Job Operations Runbook

This runbook provides operational guidance for managing the automated background job system.

## Overview

The job system continuously monitors tracked players, fetches new match data, and analyzes discovered players for smurf/boosted behavior. Jobs run every 2 minutes by default and automatically respect Riot API rate limits.

## Job Types

### 1. Tracked Player Updater (`tracked_player_updater`)
**Purpose**: Keep tracked players' data fresh
**Frequency**: Every 2 minutes (configurable)
**Tasks**:
- Fetch new matches for tracked players
- Update current rank information
- Discover new players from match participants
- Mark discovered players for analysis

**Configuration**:
```json
{
  "max_new_matches_per_player": 20,
  "max_tracked_players": 10
}
```

### 2. Player Analyzer (`player_analyzer`)
**Purpose**: Analyze discovered players for smurf/boosted behavior
**Frequency**: Every 2 minutes (after updater completes)
**Tasks**:
- Analyze unanalyzed discovered players
- Run smurf detection algorithms
- Check ban status for previously detected accounts

**Configuration**:
```json
{
  "unanalyzed_players_per_run": 15,
  "min_smurf_confidence": 0.5,
  "ban_check_days": 7
}
```

## Configuration

### Environment Variables

Edit `.env` to configure the job system:

```bash
# Enable/disable job scheduler
JOB_SCHEDULER_ENABLED=true

# Job execution interval (seconds) - default: 120 (2 minutes)
JOB_INTERVAL_SECONDS=120

# Job timeout (seconds) - default: 90
JOB_TIMEOUT_SECONDS=90

# Maximum tracked players - default: 10
MAX_TRACKED_PLAYERS=10
```

### Database Configuration

Job configurations are stored in the `job_configurations` table:

```sql
-- View job configurations
SELECT id, job_type, name, is_active, schedule, config_json
FROM job_configurations;

-- Enable/disable a job
UPDATE job_configurations SET is_active = false WHERE job_type = 'tracked_player_updater';

-- Update job configuration
UPDATE job_configurations
SET config_json = '{"max_new_matches_per_player": 30}'
WHERE job_type = 'tracked_player_updater';
```

## Monitoring Jobs

### View Job Status

**Via API**:
```bash
curl http://localhost:8000/api/v1/jobs/status/overview
```

**Via Database**:
```sql
-- View recent job executions
SELECT
  je.id,
  jc.job_type,
  je.status,
  je.started_at,
  je.completed_at,
  je.api_requests_made,
  je.records_created,
  je.error_message
FROM job_executions je
JOIN job_configurations jc ON je.job_config_id = jc.id
ORDER BY je.started_at DESC
LIMIT 10;

-- View job execution statistics
SELECT
  jc.job_type,
  COUNT(*) as total_executions,
  SUM(CASE WHEN je.status = 'success' THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN je.status = 'failed' THEN 1 ELSE 0 END) as failed,
  AVG(EXTRACT(EPOCH FROM (je.completed_at - je.started_at))) as avg_duration_seconds
FROM job_executions je
JOIN job_configurations jc ON je.job_config_id = jc.id
WHERE je.started_at > NOW() - INTERVAL '24 hours'
GROUP BY jc.job_type;
```

### Check Logs

**Backend logs**:
```bash
docker compose logs -f backend | grep -i job
```

**Structured log entries to watch for**:
- `"Job starting"` - Job execution began
- `"Job complete"` - Job finished successfully
- `"Rate limit approaching capacity"` - Nearing API rate limit
- `"Job failed"` - Job encountered an error

## Managing Tracked Players

### Track a Player

**Via API**:
```bash
# Track a player by PUUID
curl -X POST http://localhost:8000/api/v1/players/{puuid}/track

# Example
curl -X POST http://localhost:8000/api/v1/players/abc123.../track
```

**Via Database**:
```sql
UPDATE players SET is_tracked = true WHERE puuid = 'abc123...';
```

### Untrack a Player

**Via API**:
```bash
curl -X DELETE http://localhost:8000/api/v1/players/{puuid}/track
```

**Via Database**:
```sql
UPDATE players SET is_tracked = false WHERE puuid = 'abc123...';
```

### List Tracked Players

**Via API**:
```bash
curl http://localhost:8000/api/v1/players/tracked
```

**Via Database**:
```sql
SELECT puuid, summoner_name, riot_id, current_tier, current_rank, last_updated
FROM players
WHERE is_tracked = true;
```

## Manually Triggering Jobs

### Via API

```bash
# Get job ID
curl http://localhost:8000/api/v1/jobs

# Trigger specific job
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/trigger
```

### Via Python Script

```bash
docker compose exec backend python -c "
from app.jobs.scheduler import get_scheduler
scheduler = get_scheduler()
# Trigger job by ID
scheduler.get_job('tracked_player_updater').modify(next_run_time=datetime.now())
"
```

## Troubleshooting

### Jobs Not Running

**Symptoms**:
- No new job executions in database
- Backend logs show no job activity

**Diagnosis**:
1. Check if scheduler is enabled:
   ```bash
   docker compose exec backend env | grep JOB_SCHEDULER_ENABLED
   ```

2. Check backend logs for scheduler startup:
   ```bash
   docker compose logs backend | grep "scheduler"
   ```

3. Check if jobs are active in database:
   ```sql
   SELECT * FROM job_configurations WHERE is_active = true;
   ```

**Solutions**:
- Set `JOB_SCHEDULER_ENABLED=true` in `.env` and restart backend
- Ensure at least one job configuration exists with `is_active=true`
- Check for errors in backend logs during startup

### Rate Limit Errors

**Symptoms**:
- Job executions failing with 429 errors
- Logs show "Rate limit exceeded" messages

**Diagnosis**:
```bash
# Check recent failures
docker compose logs backend | grep -i "rate limit"

# Check job execution errors
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "
SELECT error_message FROM job_executions
WHERE error_message LIKE '%rate limit%'
ORDER BY started_at DESC LIMIT 5;
"
```

**Solutions**:
- **Temporary**: Wait 2 minutes for rate limit window to reset
- **Configuration**: Increase `JOB_INTERVAL_SECONDS` to run less frequently:
  ```bash
  # In .env
  JOB_INTERVAL_SECONDS=180  # Run every 3 minutes instead
  ```
- **Tracked Players**: Reduce number of tracked players to decrease API load
- **Dev API Key**: Development keys have lower rate limits - consider production key

### Jobs Stuck in "Running" State

**Symptoms**:
- Jobs show status="running" but are not actually executing
- Job hasn't completed after `JOB_TIMEOUT_SECONDS`

**Diagnosis**:
```sql
SELECT id, job_config_id, status, started_at,
       NOW() - started_at as duration
FROM job_executions
WHERE status = 'running'
ORDER BY started_at DESC;
```

**Solutions**:
- **Automatic**: On next backend startup, stale jobs are marked as failed
- **Manual**: Mark job as failed immediately:
  ```sql
  UPDATE job_executions
  SET status = 'failed',
      error_message = 'Job timeout - manually marked as failed',
      completed_at = NOW()
  WHERE status = 'running'
  AND started_at < NOW() - INTERVAL '1 hour';
  ```

### High API Request Usage

**Symptoms**:
- Jobs consuming large numbers of API requests
- Approaching rate limit frequently

**Diagnosis**:
```sql
-- Check API request usage per job
SELECT
  jc.job_type,
  AVG(je.api_requests_made) as avg_requests,
  MAX(je.api_requests_made) as max_requests
FROM job_executions je
JOIN job_configurations jc ON je.job_config_id = jc.id
WHERE je.started_at > NOW() - INTERVAL '24 hours'
GROUP BY jc.job_type;
```

**Solutions**:
1. **Reduce tracked players**: Fewer players = fewer API calls
2. **Adjust configuration**: Reduce `max_new_matches_per_player`:
   ```sql
   UPDATE job_configurations
   SET config_json = jsonb_set(config_json, '{max_new_matches_per_player}', '10')
   WHERE job_type = 'tracked_player_updater';
   ```
3. **Increase interval**: Run jobs less frequently
4. **Check for loops**: Ensure jobs aren't re-fetching the same data repeatedly

### Database Connection Errors

**Symptoms**:
- Jobs failing with database connection errors
- "Too many connections" errors

**Diagnosis**:
```bash
# Check active connections
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"
```

**Solutions**:
- Increase connection pool size in `.env`:
  ```bash
  DB_POOL_SIZE=20
  DB_MAX_OVERFLOW=40
  ```
- Restart backend to apply new pool settings:
  ```bash
  docker compose restart backend
  ```

## Performance Tuning

### Optimize Job Execution Time

**Goal**: Complete jobs within 90 seconds (default timeout)

**Strategies**:
1. **Limit batch sizes**: Reduce `max_new_matches_per_player` and `unanalyzed_players_per_run`
2. **Index optimization**: Ensure database indexes are created:
   ```sql
   -- Check for missing indexes
   SELECT * FROM pg_indexes WHERE tablename IN ('players', 'matches', 'job_executions');
   ```
3. **Monitor query performance**: Enable slow query logging
4. **Parallel processing**: Future enhancement - process players in parallel

### Balance API Usage

**Goal**: Use full 100 req/2min quota efficiently without exceeding

**Strategies**:
1. **Monitor capacity**: Watch for "Approaching rate limit capacity" warnings
2. **Adjust intervals**: Tune `JOB_INTERVAL_SECONDS` to match API usage patterns
3. **Prioritize tracked players**: Limit tracked player count to most important accounts
4. **Stagger jobs**: If needed, run jobs at different intervals

## Maintenance Tasks

### Weekly

- Review job execution success rates
- Check for players stuck as `is_analyzed=false`
- Review API request usage trends
- Clean up old job execution records (>30 days)

### Monthly

- Analyze detection quality metrics
- Review and update job configurations
- Update tracked player list
- Archive old job execution logs

### Quarterly

- Review rate limit usage patterns
- Evaluate need for production API key
- Optimize database indexes
- Review and update detection thresholds

## Emergency Procedures

### Disable All Jobs

```bash
# Via environment variable
echo "JOB_SCHEDULER_ENABLED=false" >> .env
docker compose restart backend

# Via database
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "
UPDATE job_configurations SET is_active = false;
"
```

### Clear Job Queue

```sql
-- Mark all running jobs as failed
UPDATE job_executions
SET status = 'failed',
    error_message = 'Emergency stop',
    completed_at = NOW()
WHERE status = 'running';
```

### Reset Job State

```sql
-- Delete all job execution history (keeps configurations)
TRUNCATE TABLE job_executions CASCADE;

-- Reset player tracking flags
UPDATE players SET is_tracked = false, is_analyzed = false;
```

## Monitoring Checklist

Daily:
- [ ] Check job execution success rate (target: >95%)
- [ ] Review error logs for patterns
- [ ] Verify API rate limit usage (<90%)
- [ ] Check tracked player count

Weekly:
- [ ] Review detection accuracy
- [ ] Check for stale/stuck jobs
- [ ] Verify database growth is reasonable
- [ ] Test manual job triggering

## Support

For additional help:
- Backend logs: `docker compose logs -f backend`
- Database queries: `docker compose exec postgres psql -U riot_api_user -d riot_api_db`
- API documentation: http://localhost:8000/docs
- Project documentation: `backend/CLAUDE.md`, `README.md`

# Tech Stack

- FastAPI with async/await support
- Pydantic for request/response validation
- Dependency injection with Depends()
- Auto-generated OpenAPI docs

# Project Structure

- `players.py` - Player search, tracking, rank endpoints
- `matches.py` - Match history, stats, encounters
- `detection.py` - Player analysis endpoints
- `matchmaking_analysis.py` - Matchmaking analysis endpoints
- `jobs.py` - Job management and execution endpoints
- `settings.py` - Runtime settings management
- `dependencies.py` - FastAPI dependency factories

# API Endpoints

## Jobs API (`/api/v1/jobs`)

**Key endpoints:**
- `GET /jobs/` - List all job configurations
- `PUT /jobs/{job_id}` - Update job configuration
- `GET /jobs/{job_id}/executions` - Get execution history for specific job
- `GET /jobs/executions/all` - Get execution history for all jobs
- `POST /jobs/{job_id}/trigger` - Manually trigger a job
- `GET /jobs/status/overview` - Get job system status

**Job statuses:**
- `PENDING` - Job created but not started
- `RUNNING` - Job actively executing
- `SUCCESS` - Job completed successfully
- `FAILED` - Job encountered an error
- `RATE_LIMITED` - Job hit API rate limit (not a failure, will retry)

**Job types:**
- `TRACKED_PLAYER_UPDATER` - Fetch matches for tracked players
- `MATCH_FETCHER` - Fetch matches for discovered players
- `SMURF_ANALYZER` - Analyze players for smurf behavior (no API calls)
- `BAN_CHECKER` - Check ban status for flagged players

See `backend/app/jobs/AGENTS.md` for detailed job documentation.

# Commands

- GET `/docs` - Interactive API documentation
- `./scripts/dev.sh` - Start dev server with hot reload

# Code Style

- Use dependency injection for services
- Always specify response_model parameter
- Handle errors with HTTPException
- Keep endpoints thin (delegate to services)

# Do Not

- Don't put business logic in endpoints
- Don't access database directly (use services)
- Don't return raw DB models (use schemas)
- Don't swallow exceptions

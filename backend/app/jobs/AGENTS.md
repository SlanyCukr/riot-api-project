# Tech Stack
- APScheduler for job scheduling
- BaseJob class for inheritance
- Job execution tracking with metrics
- Structured logging for monitoring

# Project Structure
- `scheduler.py` - APScheduler setup and lifecycle
- `base.py` - BaseJob class (extend this)
- `tracked_player_updater.py` - Fetch matches for tracked players
- `player_analyzer.py` - Run smurf detection

# Commands
- Job configs managed via API or database
- Monitor via `/api/v1/jobs/status/overview`
- Manual trigger: POST `/api/v1/jobs/{id}/trigger`

# Code Style
- Extend BaseJob class for new jobs
- Override execute() method only
- Track metrics with increment_metric()
- Use structlog for job logging

# Do Not
- Don't forget to call super().__init__()
- Don't commit transactions manually
- Don't block event loop (use asyncio.sleep)
- Don't catch exceptions silently

# Tech Stack

- Python 3.13 + FastAPI + SQLAlchemy 2.0+
- Pydantic v2 for validation
- structlog for structured logging
- APScheduler for background jobs
- httpx for async HTTP requests
- pytest for testing

# Project Structure

- `api/` - FastAPI endpoints and dependency injection
- `services/` - Business logic and data orchestration
- `riot_api/` - Riot Games API integration layer
- `models/` - SQLAlchemy ORM models
- `schemas/` - Pydantic request/response models
- `algorithms/` - Player analysis algorithms
- `jobs/` - Background job system

# Commands

- `docker compose exec backend uv run pytest` - Run tests
- `docker compose exec backend uv run pytest --cov=app` - Run with coverage
- `docker compose build backend` - Rebuild if dependencies change

# Code Style

- Use type hints everywhere (pyright enforced)
- Use async/await for all I/O operations
- Log with context: `logger.info("action", puuid=puuid)`
- Keep API endpoints thin, business logic in services

# Do Not

- Don't call RiotAPIClient directly (use RiotDataManager)
- Don't block event loop (no time.sleep(), use asyncio.sleep())
- Don't catch generic Exception (catch specific exceptions)
- Don't hardcode configuration (use app/config.py)

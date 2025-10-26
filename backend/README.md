# Riot API Backend

Backend service for Riot API player's performance and match history analysis.

## Features

- FastAPI-based REST API
- PostgreSQL database with async support
- In-memory Riot API response caching with TTL controls
- Riot API integration
- Player analysis algorithms
- Matchmaking analysis system
- Match history tracking

## Development

### Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
uv sync
```

### Running

```bash
# Recommended: run via Docker
docker compose up backend

# Or attach to an existing container shell
docker compose exec backend bash
```

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run the main file:

```bash
uv run python main.py
```

## Environment Variables

Copy `.env.example` to `.env` and configure your environment variables.

Key variables consumed by the backend service:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` - Database connection components (automatically constructed into connection URL)
- `LOG_LEVEL` - Logging verbosity
- `CORS_ORIGINS` - Allowed CORS origins
- `JWT_SECRET_KEY` - JWT signing secret

**Notes**:
- Riot API key is stored in database only (not in `.env`). Retrieved via `get_riot_api_key(db)` function.
- Region/platform hardcoded to europe/eun1 in backend code

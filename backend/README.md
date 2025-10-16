# Riot API Backend

Backend service for Riot API match history and player analysis.

## Features

- FastAPI-based REST API
- PostgreSQL database with async support
- In-memory Riot API response caching with TTL controls
- Riot API integration
- Smurf detection algorithms
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

- `RIOT_API_KEY`
- `DATABASE_URL`
- `LOG_LEVEL`
- `CORS_ORIGINS`

# Backend Development Guide

## Architecture

### Directory Structure

- **`app/api/`** - FastAPI endpoints (players, matches, detection)
- **`app/services/`** - Business logic (players, matches, detection, stats)
- **`app/models/`** - SQLAlchemy models (see `docker/postgres/CLAUDE.md` for schema details)
- **`app/riot_api/`** - HTTP client with rate limiting and caching
- **`app/algorithms/`** - Smurf detection algorithms (win_rate, rank_progression, performance)
- **`app/config.py`** - Pydantic settings for environment configuration

### Core Data Flow

1. Player search via Riot ID
2. PUUID resolution through Riot API
3. Match history retrieval and processing
4. Smurf detection algorithm analysis
5. Results cached and returned

### Key Services

- **PlayerService** - Player lookup, PUUID resolution, account validation
- **MatchService** - Match history fetching, parsing, and storage
- **DetectionService** - Multi-factor smurf detection orchestration
- **RiotApiClient** - Rate-limited HTTP client with automatic retry and caching

## Riot API Integration

### Authentication & Rate Limiting

- API key sent via `X-Riot-Token` header
- **Development keys expire every 24 hours** - regenerate at https://developer.riotgames.com
- Rate limits: 20 req/sec, 100 req/2min (development keys)
- Automatic backoff and retry on 429 (rate limit) responses
- Rate limit headers tracked and respected

### API Endpoints

- **Account v1** - Riot ID ↔ PUUID resolution (preferred method)
- **Summoner v4** - Deprecated for dev keys; use Account v1 instead
- **Match v5** - Match history and detailed match data
- **League v4** - Ranked information and league entries
- **Spectator v4** - Live game data (if needed)

Regional and platform routing handled automatically. See `app/riot_api/endpoints.py` for complete endpoint mapping.

### Caching Strategy

- **In-memory TTL cache** for Riot API responses (`app/riot_api/cache.py`)
- Configurable cache sizes and TTL per data type (PUUID, matches, summoner data)
- Cache statistics available at `/api/v1/health/cache-stats`
- Reduces API calls and improves response times

## Smurf Detection Algorithms

Multi-factor analysis combining:
- **Win rate threshold** - ≥65% win rate indicates potential smurf
- **Account level vs rank** - Low level with high rank is suspicious
- **Performance consistency** - Consistent high performance across matches
- **Rank progression speed** - Rapid climbing through ranks

Implementation in `app/algorithms/`. Each algorithm returns a confidence score (0-100). Final detection combines scores with configurable thresholds.

## Development

### Running the Backend

```bash
# Start backend service
docker compose up backend

# Access backend shell
docker compose exec backend bash

# Run tests
docker compose exec backend uv run pytest

# Run specific test file
docker compose exec backend uv run pytest tests/test_players.py -v
```

### Database Migrations

Migrations managed by Alembic and run automatically on startup (`alembic upgrade head`).

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations manually
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# View current migration
docker compose exec backend alembic current
```

See `docker/postgres/CLAUDE.md` for complete database documentation.

### Testing

- **pytest** for unit and integration tests
- Mock Riot API responses for integration tests
- Use `docker compose exec backend uv run pytest` to run tests

### Error Handling

- Use `HTTPException` for API errors with appropriate status codes
- Implement structured logging with `structlog`
- Handle Riot API rate limits gracefully with backoff
- Return user-friendly error messages

### Code Style

Code quality enforced by pre-commit hooks (see root `CLAUDE.md`):
- **ruff** - Fast Python linting
- **ruff-format** - Code formatting
- **pyright** - Type checking

## Environment Configuration

Backend-specific environment variables (loaded via `app/config.py`):

- **`RIOT_API_KEY`** - Riot API key (expires every 24h for dev keys)
- **`DATABASE_URL`** - PostgreSQL connection string
- **`API_HOST`** / **`API_PORT`** - Backend server binding
- **`LOG_LEVEL`** - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- **`CACHE_*`** - Cache configuration (TTL, sizes)

See root `CLAUDE.md` for general environment setup.

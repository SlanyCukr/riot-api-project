# Backend Development Guide

Agent-specific guidance for backend development. See root `README.md` for project context.

## Directory Structure
- `app/api/` - FastAPI endpoints (players, matches, detection)
- `app/services/` - Business logic (players, matches, detection, stats)
- `app/models/` - SQLAlchemy models (see `docker/postgres/CLAUDE.md`)
- `app/riot_api/` - HTTP client with rate limiting
- `app/algorithms/` - Smurf detection (win_rate, rank_progression, performance)
- `app/config.py` - Pydantic settings

## Development Commands

### Running Backend
```bash
docker compose up backend              # Start backend service
docker compose exec backend bash       # Access shell
```

### Testing
```bash
docker compose exec backend uv run pytest                       # All tests
docker compose exec backend uv run pytest tests/test_file.py    # Specific test file
docker compose exec backend uv run pytest tests/test_file.py::test_name -v
docker compose exec backend uv run pytest -k "test_pattern"     # Pattern matching
docker compose exec backend uv run pytest --lf                  # Last failed tests
```

### Database Migrations
```bash
docker compose exec backend alembic revision --autogenerate -m "description"  # Create migration
docker compose exec backend alembic upgrade head                              # Apply migrations
docker compose exec backend alembic downgrade -1                              # Rollback one
docker compose exec backend alembic current                                   # Current version
docker compose exec backend alembic history                                   # View history
```

### Code Quality
```bash
uvx pre-commit run --all-files         # Run all pre-commit hooks
uvx pre-commit run ruff                # Run specific hook
uvx pre-commit run ruff-format
uvx pre-commit run pyright
```

## Riot API Integration

### Authentication
- API key via `X-Riot-Token` header
- **Dev keys expire every 24h** - regenerate at https://developer.riotgames.com
- Rate limits: 20 req/sec, 100 req/2min (dev keys)
- Automatic backoff on 429 responses

### Key Endpoints
- **Account v1** - Riot ID ↔ PUUID (preferred for dev keys)
- **Match v5** - Match history and details
- **League v4** - Ranked information
- **Spectator v4** - Live game data

See `app/riot_api/endpoints.py` for complete mappings.

### Caching Strategy
- **Database-first**: PostgreSQL is primary cache
- **Flow**: DB → Riot API (if miss) → Store → Return
- **No TTL**: Data in DB is considered valid
- **Rate limiting**: `RiotAPIClient` returns `None` or raises `RateLimitError` when throttled
- Services handle `None` gracefully

## Smurf Detection Algorithms

Located in `app/algorithms/`. Each returns confidence score (0-100).

- **Win rate**: ≥65% win rate over 30+ ranked games
- **Account level vs rank**: Low level with high rank
- **Performance consistency**: Consistent high performance
- **Rank progression**: Rapid climbing

Final detection combines scores with configurable thresholds.

## Error Handling
- Use `HTTPException` for API errors with proper status codes
- Structured logging via `structlog`
- Graceful rate limit handling with backoff
- User-friendly error messages

## Environment Variables
- `RIOT_API_KEY` - API key (expires every 24h for dev keys)
- `DATABASE_URL` - PostgreSQL connection string
- `API_HOST` / `API_PORT` - Server binding (default: 0.0.0.0:8000)
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `DEBUG` - Debug mode (true/false)

See root `CLAUDE.md` for general setup.

## Code Conventions
- FastAPI dependency injection for services
- Pydantic models for request/response validation
- SQLAlchemy ORM for database operations
- Type hints required (enforced by pyright)
- Docstrings for public functions

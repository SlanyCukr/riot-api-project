# Backend Development Guide

## Backend Structure

- **API Layer**: FastAPI endpoints in `app/api/` (players, matches, detection)
- **Services**: Business logic in `app/services/` (players, matches, detection, stats)
- **Data Models**: SQLAlchemy models in `app/models/` (players, matches, participants, ranks, smurf_detection)
- **Riot API Client**: HTTP client with rate limiting in `app/riot_api/`
- **Algorithms**: Smurf detection algorithms in `app/algorithms/` (win_rate, rank_progression, performance)
- **Middleware**: Performance tracking, CORS, etc. in `app/middleware/`
- **Caching**: In-memory TTL cache in `app/riot_api/cache.py`

## Core Data Flow

Player search → PUUID resolution → Match history retrieval → Analysis → Smurf detection → Cached results

## Key Services

- **PlayerService**: Player lookup & PUUID resolution
- **MatchService**: Match history processing
- **DetectionService**: Smurf detection algorithms
- **RiotApiClient**: Rate-limited HTTP client

## Riot API Integration

### Authentication
- Uses `X-Riot-Token` header with API key from environment
- **Development keys expire every 24h** - regenerate at https://developer.riotgames.com
- Rate limiting: 20 requests/second, 100 requests/2 minutes (dev keys)
- Automatic backoff and retry on 429 responses

### Key Endpoints
- Account v1: Riot ID ↔ PUUID resolution (preferred)
- Summoner v4: Deprecated for dev keys - use Riot ID search
- Match v5, League v4, Spectator v4 for data retrieval
- Regional/Platform routing handled automatically
- See `app/riot_api/endpoints.py` for complete endpoint mapping

## Smurf Detection

Multi-factor analysis: win rate (≥65%), account level vs rank, performance consistency.
See `app/algorithms/` for implementation details.

## Database Schema

- `players`: PUUID-based player identification and metadata
- `matches`: Match details and game information
- `participants`: Individual player performance in matches
- `ranks`: Player rank and tier information
- `smurf_detection`: Smurf detection results and confidence scores

### Database Migrations
Migrations run automatically on container startup via `alembic upgrade head`.
Manual commands available via `docker compose exec backend alembic <command>`.

## Performance

### Caching
- In-memory TTL cache for Riot API responses
- Configurable cache sizes and TTLs per data type
- Cache statistics via `/api/v1/health/cache-stats`

## Development

### Code Style
Managed by pre-commit hooks (ruff, ruff-format, pyright). See main CLAUDE.md.

### Testing
Run tests with: `docker compose exec backend uv run pytest`
Integration tests mock Riot API responses automatically.

### Error Handling
- Use FastAPI's HTTPException for API errors
- Implement proper error logging with structlog
- Handle Riot API rate limits gracefully

## Environment Configuration

See main CLAUDE.md for complete environment variables. Backend-specific:
- All variables are loaded via pydantic-settings in `app/config.py`
- RIOT_API_KEY expires every 24h for development keys

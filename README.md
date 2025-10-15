# Riot API - Match History & Player Analysis

A comprehensive application for analyzing League of Legends match history and detecting potential smurf accounts using Riot API data.

## Project Scope

- Current project scope is described in `docs/project-scope.md`

## Features

- **Player Analysis**: Retrieve and analyze match histories for League of Legends players
- **Smurf Detection**: Identify potential smurf accounts based on win rate patterns and other heuristics
- **Encounter Tracking**: Track players you've encountered in matches and analyze their performance
- **Automated Background Jobs**: Continuous monitoring of tracked players with automatic data updates
- **Multi-Region Support**: Support for different Riot API regions and platforms
- **Real-time Data**: Live game spectator data and current rank information

## Architecture

This project runs as a Docker-first stack composed of the following services:

- **Backend**: Python 3.13 + FastAPI application with PostgreSQL persistence and Riot API integration
- **Frontend**: Next.js 15 + React 19 + shadcn/ui + Zod for type-safe UI with runtime validation
- **Database**: PostgreSQL 18 instance configured via Docker Compose
- **Tooling**: Optional utility scripts in `scripts/` for cleanup and data seeding

## Prerequisites

- Docker Engine with Compose v2 (`docker compose` CLI)
- Riot API Key (obtainable from [Riot Developer Portal](https://developer.riotgames.com/))
- Optional: [uv](https://github.com/astral-sh/uv) for running backend tooling outside containers

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd riot_api_project
```

### 2. Environment Configuration

Copy the environment template and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

- Set your Riot API key: `RIOT_API_KEY=your_actual_api_key`
- Configure database credentials
- Set appropriate region and platform for your use case

**⚠️ Important: Development API keys expire every 24 hours!**

To update your API key after expiry, use the provided script:

```bash
./scripts/update-riot-api-key.sh
```

This script will:

- Prompt you for the new API key
- Update the `.env` file
- Restart the backend container to apply changes immediately
- Verify the new key is loaded correctly

### 3. Docker Deployment

Build and start all services:

```bash
docker compose up --build
```

With the development override (`docker-compose.override.yml`) in place the services expose:

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000

### 4. Development Commands

This project runs through Docker containers:

```bash
# Start development environment
docker compose up --build

# Start specific service
docker compose up backend
docker compose up frontend

# Stop all services
docker compose down

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Database operations (tables are created automatically on startup)
docker compose exec backend uv run python -m app.init_db init  # Manually create tables
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# Run tests (inside containers)
docker compose exec backend uv run pytest
docker compose exec frontend npm run lint

# Backend linting and formatting (local - requires uv)
cd backend
uv run black .
uv run isort .
uv run flake8 .
uv run mypy .
```

## API Usage

The application provides the following main endpoints:

### Player Lookup

- Get player information by Riot ID or Summoner Name
- Retrieve match history with filtering options
- Analyze player statistics and performance patterns

### Player Analysis

- Calculate win rates over recent matches
- Flag accounts with suspicious performance patterns
- Provide confidence scores for smurf detection

### Encounter Analysis

- Track players encountered in your matches
- Analyze teammate and opponent performance
- Identify recurring players and their tendencies

### Background Jobs

The application includes an automated job system that continuously monitors tracked players:

**Tracked Player Updater**

- Runs every 2 minutes (configurable)
- Fetches new matches for tracked players
- Updates rank information
- Discovers new players from match participants

**Player Analyzer**

- Analyzes discovered players for smurf/boosted behavior
- Checks ban status for previously detected accounts
- Runs detection algorithms automatically

**Job Management Endpoints**

- `POST /api/v1/players/{puuid}/track` - Mark player as tracked
- `DELETE /api/v1/players/{puuid}/track` - Unmark player as tracked
- `GET /api/v1/players/tracked` - List all tracked players
- `GET /api/v1/jobs/status/overview` - View job system status
- `GET /api/v1/jobs/{id}/executions` - View job execution history
- `POST /api/v1/jobs/{id}/trigger` - Manually trigger a job

For detailed job configuration and monitoring, see `backend/AGENTS.md`.

## Environment Variables

| Variable                | Description                               | Default                                     |
| ----------------------- | ----------------------------------------- | ------------------------------------------- |
| `RIOT_API_KEY`          | Your Riot Games API key                   | Required                                    |
| `RIOT_REGION`           | Regional routing (e.g., europe, americas) | europe                                      |
| `RIOT_PLATFORM`         | Platform routing (e.g., eun1, euw1)       | eun1                                        |
| `NEXT_PUBLIC_API_URL`   | Backend URL for frontend API calls        | http://localhost:8000                       |
| `POSTGRES_DB`           | Database name                             | riot_api_db                                 |
| `POSTGRES_USER`         | Database username                         | riot_api_user                               |
| `POSTGRES_PASSWORD`     | Database password                         | Required                                    |
| `POSTGRES_PORT`         | Host port for PostgreSQL                  | 5432                                        |
| `BACKEND_PORT`          | Host port for backend service             | 8000                                        |
| `FRONTEND_PORT`         | Host port for frontend service            | 3000                                        |
| `DATABASE_URL`          | SQLAlchemy connection string              | See `.env.example`                          |
| `DEBUG`                 | Backend debug mode                        | false                                       |
| `LOG_LEVEL`             | Backend logging level                     | INFO                                        |
| `DB_POOL_SIZE`          | Connection pool size                      | 10                                          |
| `DB_MAX_OVERFLOW`       | Additional connections beyond pool        | 20                                          |
| `DB_POOL_TIMEOUT`       | Pool timeout (seconds)                    | 30                                          |
| `DB_POOL_RECYCLE`       | Pool recycle interval (seconds)           | 1800                                        |
| `CORS_ORIGINS`          | Allowed origins for frontend requests     | http://localhost:3000,http://127.0.0.1:3000 |
| `COMPOSE_PROJECT_NAME`  | Docker Compose project prefix             | riot_api_app                                |
| `JOB_SCHEDULER_ENABLED` | Enable background job scheduler           | true                                        |
| `JOB_INTERVAL_SECONDS`  | Job execution interval (seconds)          | 120                                         |
| `JOB_TIMEOUT_SECONDS`   | Job execution timeout (seconds)           | 90                                          |
| `MAX_TRACKED_PLAYERS`   | Maximum tracked players limit             | 10                                          |

## Rate Limiting

The application respects Riot API rate limits:

- 20 requests per second
- 100 requests per 2 minutes

Built-in backoff and retry mechanisms handle rate limit responses automatically.

## Data Model

### Core Entities

- **Players**: PUUID-based player identification
- **Matches**: Match details and participant information
- **Participants**: Individual player performance in matches
- **Encounters**: Player interaction tracking

### Player Analysis Heuristics

- Win rate ≥ 65% over 30+ ranked games
- Account level relative to rank
- Rank volatility and climbing speed
- Performance consistency across matches

## Development Workflow

1. **Feature Development**: Work in feature branches
2. **Testing**: Run comprehensive test suites
3. **Code Review**: Peer review process
4. **Integration**: Test with actual Riot API data
5. **Deployment**: Deploy through Docker containers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is for educational and research purposes. Please ensure compliance with Riot Games' API Terms of Service.

## Support

For issues and questions:

- Check the existing issues on GitHub
- Review the API documentation
- Contact the development team

## Disclaimer

This project is not affiliated with or endorsed by Riot Games. All League of Legends-related content is property of Riot Games, Inc.

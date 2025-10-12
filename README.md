# Riot API - Match History & Smurf Detection

A comprehensive application for analyzing League of Legends match history and detecting potential smurf accounts using Riot API data.

## Project Scope

- Current project scope is described in `docs/project-scope.md` 

## Features

- **Player Analysis**: Retrieve and analyze match histories for League of Legends players
- **Smurf Detection**: Identify potential smurf accounts based on win rate patterns and other heuristics
- **Encounter Tracking**: Track players you've encountered in matches and analyze their performance
- **Multi-Region Support**: Support for different Riot API regions and platforms
- **Real-time Data**: Live game spectator data and current rank information

## Architecture

This project runs as a Docker-first stack composed of the following services:

- **Backend**: FastAPI application with PostgreSQL persistence and Riot API integration
- **Frontend**: React + TypeScript interface served through Vite
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

# Database operations
docker compose exec backend alembic upgrade head
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

### Smurf Detection
- Calculate win rates over recent matches
- Flag accounts with suspicious performance patterns
- Provide confidence scores for smurf detection

### Encounter Analysis
- Track players encountered in your matches
- Analyze teammate and opponent performance
- Identify recurring players and their tendencies

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RIOT_API_KEY` | Your Riot Games API key | Required |
| `RIOT_REGION` | Regional routing (e.g., europe, americas) | europe |
| `RIOT_PLATFORM` | Platform routing (e.g., eun1, euw1) | eun1 |
| `API_URL` | Backend URL exposed to the frontend | http://localhost:8000 |
| `POSTGRES_DB` | Database name | riot_api_db |
| `POSTGRES_USER` | Database username | riot_api_user |
| `POSTGRES_PASSWORD` | Database password | Required |
| `POSTGRES_PORT` | Host port for PostgreSQL | 5432 |
| `BACKEND_PORT` | Host port for backend service | 8000 |
| `FRONTEND_PORT` | Host port for frontend service | 3000 |
| `DATABASE_URL` | SQLAlchemy connection string | See `.env.example` |
| `DEBUG` | Backend debug mode | false |
| `LOG_LEVEL` | Backend logging level | INFO |
| `DB_POOL_SIZE` | Connection pool size | 10 |
| `DB_MAX_OVERFLOW` | Additional connections beyond pool | 20 |
| `DB_POOL_TIMEOUT` | Pool timeout (seconds) | 30 |
| `DB_POOL_RECYCLE` | Pool recycle interval (seconds) | 1800 |
| `CORS_ORIGINS` | Allowed origins for frontend requests | http://localhost:3000,http://127.0.0.1:3000 |
| `COMPOSE_PROJECT_NAME` | Docker Compose project prefix | riot_api_app |

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

### Smurf Detection Heuristics
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

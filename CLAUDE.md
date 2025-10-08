# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack Riot API application for analyzing League of Legends match history and detecting smurf accounts. The system consists of a Python FastAPI backend, React TypeScript frontend, and PostgreSQL database, all containerized with Docker.

## Project Structure

- `backend/` - Python FastAPI backend with API services
- `frontend/` - React TypeScript frontend application
- `docker/` - Docker configuration and deployment guides
- `docker/postgres/` - Database-specific guidance
- `scripts/` - Utility scripts for development and deployment

## Specialized Documentation

For detailed guidance on specific areas, refer to the specialized CLAUDE.md files:

- **Backend Development**: `backend/CLAUDE.md` - FastAPI, services, Riot API integration
- **Frontend Development**: `frontend/CLAUDE.md` - React, TypeScript, styling
- **Database**: `docker/postgres/CLAUDE.md` - PostgreSQL schema, migrations, optimization
- **Docker/Deployment**: `docker/CLAUDE.md` - Container management, production deployment

## Quick Start

```bash
# Start all services with hot reload
docker compose up --build

# Start specific service
docker compose up backend
docker compose up frontend

# Stop all services
docker compose down
```

**Important Notes:**
- Database migrations run automatically on backend startup
- Development API keys expire every 24 hours - regenerate at https://developer.riotgames.com
- After updating `.env`, restart containers to load new values
- Use `docker compose` (v2) not `docker-compose` (v1)

## Core Technologies

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic
- **Frontend**: React, TypeScript, Tailwind CSS, Vite
- **Database**: PostgreSQL with connection pooling
- **Containerization**: Docker & Docker Compose
- **API**: Riot Games API with rate limiting

## Key Features

- Player search by Riot ID (recommended) or summoner name (deprecated endpoint)
- Match history retrieval and analysis
- Smurf detection using multiple algorithms
- Encounter tracking between players
- Cached responses for performance
- Docker-only development environment
- Automatic database migrations on startup
- Hot reload for backend and frontend

## Environment Variables

### Required
- `RIOT_API_KEY`: Riot Games API key (development keys expire every 24 hours)
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user

### Optional
- `RIOT_REGION`: Regional routing (default: europe)
- `RIOT_PLATFORM`: Platform routing (default: eun1)
- `DEBUG`: Debug mode (default: false)
- `LOG_LEVEL`: Logging level (default: INFO)

## Development Workflow

1. Make code changes in respective directories
2. Test using Docker containers
3. Follow code style guidelines in specialized docs
4. Run tests and linting in containers
5. Commit changes with proper messages

## Code Quality and Pre-commit Hooks

### Pre-commit Hook Setup

Pre-commit hooks automatically check code quality before commits. They run linters, formatters, and other checks to ensure consistent code style.

```bash
# Install pre-commit (one-time setup)
pip install pre-commit

# Install git hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run ruff-format --all-files
```

### Configured Hooks

- **ruff**: Fast Python linter (replaces flake8, isort, pylint)
- **ruff-format**: Python code formatter (replaces black)
- **bandit**: Security vulnerability scanner
- **pydocstyle**: Docstring style checker
- **pyright**: Static type checker
- **eslint**: JavaScript/TypeScript linter
- **prettier**: Frontend code formatter
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with newline
- **check-yaml**: Validates YAML syntax

### Common Issues and Fixes

**Ruff linting errors:**
```bash
# Auto-fix most issues
pre-commit run ruff --all-files

# Format code
pre-commit run ruff-format --all-files
```

**Pre-commit config issues:**
- Ensure npm package names with `@` are quoted in `.pre-commit-config.yaml`
- Use valid git tags for tool versions

**Running in Docker vs Host:**
Pre-commit hooks can run on the host system (recommended for speed) or inside Docker containers. Most hooks work better on the host as they have direct filesystem access.

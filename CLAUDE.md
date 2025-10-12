# CLAUDE.md

Central quick reference for working with this Riot API application. See `README.md` for project overview and architecture.

## Project Overview

Full-stack Riot API application for League of Legends match analysis and smurf detection. Features include player search, match analysis, smurf detection algorithms, and encounter tracking with Riot API integration.

## Project Scope

Overview of what exactly is in project's scope is in `docs/project-scope.md`, as well as tasks labeled as "SPY-XXX" or "BACKLOG", reserved for tasks with the lowest priority, or "EPIC", reserved for labeling a group of tasks. When doing tasks described in `docs/project-scope.md`, mark them as "WIP", instead of "TODO", and after user tests your code and approves it, mark it as done with ✅.

## Tech Stack
- **Backend**: Python 3.13 + FastAPI + SQLAlchemy
- **Frontend**: Next.js 15 + React 19 + TypeScript + shadcn/ui
- **Database**: PostgreSQL 18
- **Infrastructure**: Docker + Docker Compose

## Documentation Structure
This is the **central reference** for common commands. For domain-specific patterns:
- `backend/CLAUDE.md` - Riot API integration, smurf detection algorithms, FastAPI patterns
- `frontend/CLAUDE.md` - Next.js patterns, shadcn/ui, TanStack Query, form handling
- `docker/CLAUDE.md` - Production deployment, image management, advanced Docker operations
- `docker/postgres/CLAUDE.md` - Database schema, performance tuning, advanced queries

## Development Commands

### Start/Stop Services
```bash
# First time or if you encounter port conflicts:
./scripts/docker-cleanup.sh            # Clean up Docker resources and stop local PostgreSQL

docker compose up --build              # Start all with rebuild
docker compose up backend frontend     # Start specific services
docker compose down                    # Stop all
docker compose down -v                 # Stop and remove volumes (WARNING: deletes data)
```

### View Logs
```bash
docker compose logs -f backend         # Follow backend logs
docker compose logs --tail=100 postgres
```

### Execute Commands
```bash
docker compose exec backend bash       # Backend shell
docker compose exec frontend bash      # Frontend shell
docker compose exec postgres psql -U riot_api_user -d riot_api_db
```

**Port Conflicts?** See `docs/docker-troubleshooting.md` or run `./scripts/docker-cleanup.sh`

### Testing
```bash
docker compose exec backend uv run pytest                    # All tests
docker compose exec backend uv run pytest tests/test_file.py -v
docker compose exec frontend npm run lint
```

### Database Operations
```bash
# Database tables are automatically created on backend startup
# To manually initialize/reset the database:
docker compose exec backend uv run python -m app.init_db init    # Create tables
docker compose exec backend uv run python -m app.init_db reset   # Reset database (WARNING: deletes data)
./scripts/seed-dev-data.sh                                       # Seed test data
```

### Code Quality
```bash
uvx pre-commit run --all-files         # Run all hooks manually
uvx pre-commit autoupdate              # Update hook versions
```

## Environment Setup
Copy `.env.example` to `.env`:
- `RIOT_API_KEY` - Get from https://developer.riotgames.com (expires every 24h for dev keys)
- Database credentials
- Service ports

## File Organization
- `backend/` - FastAPI backend (see `backend/CLAUDE.md`)
- `frontend/` - Next.js frontend (see `frontend/CLAUDE.md`)
- `docker/` - Docker configs
- `scripts/` - Utility scripts

## Hot Reload (IMPORTANT)

⚠️ **Both backend and frontend support hot reload** - containers do NOT need to be restarted or rebuilt for code changes.

- **Frontend**: Next.js hot reload - saving any file automatically updates in browser
- **Backend**: FastAPI auto-reload - saving Python files automatically restarts the server

**Simply save your file and the changes will apply immediately.** Only rebuild containers when:
- Changing dependencies (package.json, pyproject.toml, uv.lock)
- Modifying Dockerfile or docker-compose.yml
- Adding new system packages

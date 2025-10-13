<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

Central quick reference for working with this Riot API application. See `README.md` for project overview and architecture.

## Project Overview

Full-stack Riot API application for League of Legends match analysis and smurf detection. Features include player search, match analysis, smurf detection algorithms, and encounter tracking with Riot API integration.

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

### Updating Riot API Key
Development API keys expire every 24 hours. To update your key:

```bash
./scripts/update-riot-api-key.sh       # Interactive script to update key
```

**Why this is needed:** Docker Compose reads `.env` at container creation time. Simply editing `.env` and restarting the container won't pick up changes. The script handles this by:
1. Updating the `.env` file
2. Stopping and removing the backend container
3. Recreating it fresh (which reads the new `.env` values)
4. Verifying the new key is loaded

**Manual alternative:**
```bash
# Edit .env file with new key, then:
docker compose stop backend
docker compose rm -f backend
docker compose up -d backend
```

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

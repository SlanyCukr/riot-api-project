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

# Quick Start

**Development** (automatic hot reload with volume mounts):

```bash
docker compose up -d                                # Start services
docker compose logs -f backend                      # View backend logs
docker compose exec backend uv run alembic current  # Check migration status
docker compose down                                 # Stop services
```

**Note:** Hot reload is automatic via volume mounts. Backend uses `uvicorn --reload` to watch Python files, frontend uses `next dev` to watch TypeScript/JSX. No rebuilds needed for code changes.

**Production**:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml logs -f
docker compose -f compose.yaml -f compose.prod.yaml down
```

**Building** (uses Docker Bake for parallel builds):

```bash
docker buildx bake -f docker/docker-bake.hcl dev --load   # Dev build
docker buildx bake -f docker/docker-bake.hcl prod --load  # Prod build
```

See `docker/AGENTS.md` for comprehensive command reference and deployment workflows.

# Project Structure

## Backend (Feature-Based Architecture)

- `backend/app/core/`: Infrastructure (database, config, Riot API client, shared enums)
- `backend/app/features/`: Domain features
  - `features/auth/`: User authentication and authorization (JWT-based)
  - `features/players/`: Player management (search, tracking, rank info) - **Uses enterprise pattern with repository layer**
  - `features/matches/`: Match data and statistics - **Uses enterprise pattern with repository layer**
  - `features/player_analysis/`: Player analysis algorithms
  - `features/matchmaking_analysis/`: Matchmaking fairness evaluation
  - `features/jobs/`: Background job scheduling and execution
  - `features/settings/`: System configuration management
  - Standard features: `router.py`, `service.py`, `models.py`, `schemas.py`, `dependencies.py`
  - Enterprise features (players, matches): + `repository.py`, `orm_models.py`, `transformers.py`

## Frontend (Feature-Based Architecture)

- `frontend/app/`: Next.js 16.0.0 pages (App Router) with React 19.2.0
- `frontend/features/`: Feature modules
  - `features/auth/`: Authentication (AuthProvider, ProtectedRoute, useAuth hook)
  - `features/players/`: Player components, hooks, utilities
  - `features/matches/`: Match components
  - `features/player-analysis/`: Analysis components
  - `features/matchmaking/`: Matchmaking analysis components
  - `features/jobs/`: Job management components
  - `features/settings/`: Settings components
- `frontend/components/`: Shared layout components and shadcn/ui
- `frontend/lib/core/`: Core utilities (API client, schemas, validations)
- **Tailwind CSS 4.1.14**: CSS-first configuration via `@theme` blocks in `globals.css` (no `tailwind.config.ts`)

# Code Style

- **Backend**: async/await, type hints, FastAPI patterns
- **Frontend**: TypeScript, function components with hooks
- **General**: Explicit imports, no .env edits

## Feature Organization

- **Core vs. Features**: Infrastructure code in `core/`, domain code in `features/`
- **Dependency Flow**: Features depend on core, never the reverse
- **Public API**: Some features expose public APIs through `__init__.py` exports (minimal to avoid circular dependencies)
- **Import Examples**:

  ```python
  # Backend - direct module imports (preferred)
  from app.features.players.service import PlayerService
  from app.features.players.models import Player
  from app.features.players.schemas import PlayerResponse
  from app.core.database import get_db
  from app.core.riot_api import RiotAPIClient

  # Frontend - import from features
  import { PlayerSearch } from '@/features/players'
  import { useAuth } from '@/features/auth'
  import { api } from '@/lib/core/api'
  ```

## Enterprise Patterns

The **players and matches features** use enterprise architecture:

- **Repository Pattern**: Data access abstraction
- **Rich Domain Models**: ORM models with business logic
- **Data Mapper**: Transformers separate ORM from Pydantic models
- **Gateway Pattern**: External API integration (matches feature)

See `backend/app/features/players/README.md` and `backend/app/features/matches/README.md` for details.

# Database Migrations

**ALWAYS use Alembic** for all database schema changes. Never use `create_all()`, or manual SQL.

```bash
# Create migration after changing models
docker compose exec backend uv run alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend uv run alembic upgrade head

# Check current migration status
docker compose exec backend uv run alembic current

# View migration history
docker compose exec backend uv run alembic history

# Rollback one migration
docker compose exec backend uv run alembic downgrade -1
```

**Important**: The entrypoint automatically runs `alembic upgrade head` on startup, so migrations are applied when containers start.

See `backend/alembic/AGENTS.md` for comprehensive migration documentation.

# Constraints

- ❌ **Never** use `create_all()` or manual SQL — **ALWAYS use Alembic migrations**
- ❌ Don't commit API keys or secrets
- ❌ Don't modify Riot API rate limiting
- ❌ Don't touch legacy code without explicit request
- ❌ Don't skip pre-commit hooks (always run checks before committing)
- ❌ Don't manage tables owned by external libraries (e.g., APScheduler) — they handle their own schema

# Production Environment

**When working on production issues, deployments, or server operations**, read `docs/production.md` for complete production server documentation.

# Documentation Structure

## Quick Reference

- `AGENTS.md` (this file): Project quick reference for development
- `CLAUDE.md`: Symlink to AGENTS.md

## Comprehensive Guides

- **Production**: `docs/production.md` - **Production server access, deployment, and troubleshooting**
- **Docker**: `docker/AGENTS.md` - **Comprehensive Docker Compose command reference**, builds, database operations, and production deployment
- **Backend**: `backend/AGENTS.md` - Riot API integration and FastAPI patterns
- **Migrations**: `backend/alembic/AGENTS.md` - Database migrations with Alembic
- **Frontend**: `frontend/AGENTS.md` - Next.js patterns and shadcn/ui
- **Replication**: `REPLICATION_SETUP_SUMMARY.md` - PostgreSQL logical replication setup
- **OpenSpec**: `openspec/AGENTS.md` - Change proposals and architecture decisions

## Architecture Documentation

- `docs/architecture/database.md` - Database schema and ERDs
- `docs/architecture/jobs.md` - Background job workflows and configuration

## How-To Guides

- `docs/guides/migration.md` - Feature-based architecture migration guide
- `docs/guides/riot-api.md` - Riot API integration patterns
- `docs/guides/docker-troubleshooting.md` - Docker and WSL troubleshooting

## Task Documentation

- `docs/tasks/auth.md` - Extended authentication system (planned)
- `docs/tasks/technical-debt.md` - Security improvements and tech debt tracking

## Feature Documentation

Each feature has its own README.md:

- `backend/app/features/*/README.md` - Backend feature docs
- `frontend/features/*/README.md` - Frontend feature docs (e.g., auth)

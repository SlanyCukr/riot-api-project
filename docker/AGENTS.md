# Docker Compose Command Reference

## Quick Command Reference

**Development** (from project root):
```bash
docker compose watch                    # Start with hot reload (recommended)
docker compose up                       # Start without watch
docker compose down                     # Stop all services
docker compose logs -f                  # Follow all logs
docker compose logs -f backend          # Follow backend logs only
docker compose restart backend          # Restart backend service
docker compose exec backend bash        # Access backend container
```

**Production** (from project root):
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d        # Start detached
docker compose -f compose.yaml -f compose.prod.yaml logs -f      # Follow logs
docker compose -f compose.yaml -f compose.prod.yaml down         # Stop all
docker compose -f compose.yaml -f compose.prod.yaml restart backend  # Restart service
```

**Building** (from project root):
```bash
docker buildx bake -f docker/docker-bake.hcl dev --load          # Build dev images
docker buildx bake -f docker/docker-bake.hcl prod --load         # Build prod images
docker buildx bake -f docker/docker-bake.hcl validate            # Run linting only
docker buildx bake -f docker/docker-bake.hcl backend-dev --load  # Build backend only
```

**Database Operations** (from project root):
```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db  # PostgreSQL shell
docker compose exec backend uv run alembic upgrade head             # Apply migrations
docker compose exec backend uv run alembic current                  # Check status
docker compose exec backend uv run alembic revision --autogenerate -m "description"  # Create migration
```

---

## Project Structure

**Compose Files** (project root):
- `compose.yaml` - Base configuration for all environments
- `compose.override.yaml` - Development overrides (auto-loaded when present)
- `compose.prod.yaml` - Production overrides (explicit `-f` flag required)

**Docker Files** (`docker/` directory):
- `docker-bake.hcl` - Docker Bake build configuration (parallel builds)
- `backend/Dockerfile` - Multi-stage Python build (base → deps → lint → dev → builder → production)
- `frontend/Dockerfile` - Multi-stage Node.js build (base → deps → lint → builder → runner → dev)
- `postgres/init.sql` - Database initialization script

---

## How Compose File Loading Works

### Development (Automatic Override)

When you run `docker compose` commands **without** the `-f` flag in the project root:

1. Docker Compose automatically finds and loads `compose.yaml`
2. If `compose.override.yaml` exists, it's **automatically merged** on top of `compose.yaml`
3. No need for `-f` flags or explicit file specification

**Example**:
```bash
# This automatically loads both compose.yaml AND compose.override.yaml:
docker compose watch

# Equivalent to:
docker compose -f compose.yaml -f compose.override.yaml watch
```

**What's in `compose.override.yaml`**:
- Development build targets (`target: development`)
- Hot reload configuration (`develop.watch` sections)
- Debug logging (`LOG_LEVEL: DEBUG`)
- Development-specific environment variables

### Production (Explicit Override)

For production, you **must** explicitly specify both files:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

**What's in `compose.prod.yaml`**:
- Production build targets (`target: production`)
- Production restart policies (`restart: always`)
- Read-only filesystems for security
- Production logging levels

---

## Docker Compose Watch (Hot Reload)

The `compose.override.yaml` file includes `develop.watch` configuration that enables hot reload for both backend and frontend.

**Start watch mode**:
```bash
docker compose watch
```

**What happens**:
- **Frontend**: Changes to `./frontend` → sync to container → Next.js hot reloads
- **Backend**: Changes to `./backend` → sync to container → FastAPI auto-reloads
- **No rebuild needed**: Code changes are synced in real-time

**When to rebuild**:
- Dependency changes (`package.json`, `pyproject.toml`)
- Dockerfile modifications
- System package changes

---

## Build System (Docker Bake)

All builds use Docker Bake for faster, parallel builds with local caching.

### Build Configuration (`docker/docker-bake.hcl`)

**Groups**:
- `dev` - Builds both backend-dev and frontend-dev
- `prod` - Builds both backend-prod and frontend-prod
- `validate` - Runs linting checks only (no image output)

**Targets**:
- `backend-dev`, `frontend-dev` - Development images
- `backend-prod`, `frontend-prod` - Production images
- `backend-lint`, `frontend-lint` - Linting only

**Cache**: Local filesystem cache at `/tmp/.buildx-cache`

### Build Commands

**Build all services (dev)**:
```bash
docker buildx bake -f docker/docker-bake.hcl dev --load
```

**Build all services (prod)**:
```bash
docker buildx bake -f docker/docker-bake.hcl prod --load
```

**Build specific service**:
```bash
docker buildx bake -f docker/docker-bake.hcl backend-dev --load
docker buildx bake -f docker/docker-bake.hcl frontend-prod --load
```

**Run linting checks (CI/CD)**:
```bash
docker buildx bake -f docker/docker-bake.hcl validate
```

**Preview build configuration**:
```bash
docker buildx bake -f docker/docker-bake.hcl dev --print
```

---

## Common Operations

### Starting Services

**Development (recommended)**:
```bash
docker compose watch
```

**Development (without watch)**:
```bash
docker compose up
```

**Production**:
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

### Stopping Services

**Development**:
```bash
docker compose down
```

**Production**:
```bash
docker compose -f compose.yaml -f compose.prod.yaml down
```

### Viewing Logs

**All services (follow)**:
```bash
docker compose logs -f
```

**Specific service**:
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

**Last N lines**:
```bash
docker compose logs --tail=100 backend
```

**Since timestamp**:
```bash
docker compose logs --since=10m backend  # Last 10 minutes
```

### Accessing Containers

**Interactive shell**:
```bash
docker compose exec backend bash
docker compose exec frontend sh
docker compose exec postgres bash
```

**Run one-time command**:
```bash
docker compose exec backend uv run pytest
docker compose exec frontend npm run lint
```

### Restarting Services

**Single service**:
```bash
docker compose restart backend
```

**All services**:
```bash
docker compose restart
```

### Container Status

**List running containers**:
```bash
docker compose ps
```

**List all containers (including stopped)**:
```bash
docker compose ps -a
```

**Formatted output**:
```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

---

## Database Operations

### PostgreSQL Shell

**Access psql**:
```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db
```

**Check connection**:
```bash
docker compose exec postgres pg_isready -U riot_api_user -d riot_api_db
```

### Database Migrations (Alembic)

**Apply all pending migrations**:
```bash
docker compose exec backend uv run alembic upgrade head
```

**Check current migration**:
```bash
docker compose exec backend uv run alembic current
```

**View migration history**:
```bash
docker compose exec backend uv run alembic history
```

**Create new migration**:
```bash
docker compose exec backend uv run alembic revision --autogenerate -m "description"
```

**Rollback one migration**:
```bash
docker compose exec backend uv run alembic downgrade -1
```

See `backend/alembic/AGENTS.md` for comprehensive migration documentation.

---

## Troubleshooting

### Rebuild Everything

**Development**:
```bash
docker compose down
docker buildx bake -f docker/docker-bake.hcl dev --load
docker compose up
```

**Production**:
```bash
docker compose -f compose.yaml -f compose.prod.yaml down
docker buildx bake -f docker/docker-bake.hcl prod --load
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

### Clear Build Cache

```bash
rm -rf /tmp/.buildx-cache
docker buildx bake -f docker/docker-bake.hcl dev --no-cache --load
```

### View Container Resource Usage

```bash
docker compose stats
```

### Inspect Service Configuration

```bash
docker compose config
```

### Check Docker System Usage

```bash
docker system df
```

### Cleanup Unused Resources

```bash
./scripts/docker-cleanup.sh  # Removes stopped containers, unused images, build cache
```

---

## Multi-Stage Dockerfiles

Both backend and frontend use optimized multi-stage builds:

1. **Base**: Common dependencies and system packages
2. **Deps**: Application dependencies (cached separately)
3. **Lint**: Linting and code quality checks
4. **Development**: Full dev environment with tools
5. **Builder**: Compiles/builds application
6. **Production**: Minimal runtime-only image

**Benefits**:
- Layer caching speeds up rebuilds
- Development images include dev tools
- Production images are minimal (only runtime dependencies)
- Dependencies cached separately from application code

---

## Best Practices

✅ **Do**:
- Run `docker compose watch` for development (automatic hot reload)
- Use service names (`backend`, `frontend`, `postgres`) not container names
- Let automatic override loading handle development configuration
- Use Docker Bake for all builds (parallel backend + frontend)
- Keep build cache at `/tmp/.buildx-cache` for faster rebuilds

❌ **Don't**:
- Restart containers after code changes (hot reload handles it)
- Manually specify `compose.override.yaml` with `-f` (auto-loaded)
- Clear `/tmp/.buildx-cache` unless troubleshooting build issues
- Remove volumes without backup confirmation
- Use `docker run` for services (use `docker compose` instead)

---

## Production Deployment

See `.github/workflows/deploy.yml` for the full production deployment workflow.

**Typical deployment**:
```bash
# Build production images
docker buildx bake -f docker/docker-bake.hcl prod --load

# Start production services
docker compose -f compose.yaml -f compose.prod.yaml up -d

# Verify health
docker compose -f compose.yaml -f compose.prod.yaml ps
curl http://localhost:8086/health  # Backend health check
curl http://localhost:8088          # Frontend check
```

---

## Environment Variables

Required `.env` file variables:
- `RIOT_API_KEY` - Riot API key
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Database credentials
- `DATABASE_URL` - Full PostgreSQL connection string
- `COMPOSE_PROJECT_NAME` - Project name (prefixes containers/networks/volumes)
- `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT` - Port mappings
- `NEXT_PUBLIC_API_URL` - Frontend API URL
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `JOB_SCHEDULER_ENABLED` - Enable background jobs (true/false)

Copy `.env.example` to `.env` and configure before first run.

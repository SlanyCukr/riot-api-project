# Docker Configuration

## Overview

Docker Compose orchestrates containers, while Docker Bake optimizes builds with parallel backend + frontend compilation.

## Project Structure
- `docker/docker-compose.yml` - Base compose configuration
- `docker/docker-compose.override.yml` - Development overrides (auto-loaded)
- `docker/docker-compose.prod.yml` - Production overrides
- `docker/docker-bake.hcl` - Docker Bake build configuration
- `docker/backend/Dockerfile` - Multi-stage Python build (base → deps → lint → dev → builder → production)
- `docker/frontend/Dockerfile` - Multi-stage Node.js build (base → deps → lint → builder → runner → dev)
- `docker/postgres/` - Database configuration and initialization

## Build System

### Docker Bake
All builds use Docker Bake for faster, parallel builds with local caching.

**Configuration**: `docker/docker-bake.hcl`
- **Dev group**: Builds development images with hot reload support
- **Prod group**: Builds optimized production images
- **Validate group**: Runs linting checks for CI/CD

**Build targets**:
- `backend-dev`, `frontend-dev` - Development images
- `backend-prod`, `frontend-prod` - Production images
- `backend-lint`, `frontend-lint` - Linting only (no image output)

**Cache**: Local filesystem cache at `/tmp/.buildx-cache` for faster rebuilds

### Multi-Stage Dockerfiles
Both services use optimized multi-stage builds:
1. **Base**: Common dependencies and system packages
2. **Deps**: Application dependencies (cached separately)
3. **Lint**: Linting and code quality checks
4. **Development**: Full dev environment with tools
5. **Builder**: Compiles/builds application
6. **Production**: Minimal runtime-only image

## Commands

For script usage and typical workflows, see `scripts/AGENTS.md`.

### Direct Docker Commands (Advanced)
```bash
# Preview Bake configuration
docker buildx bake -f docker/docker-bake.hcl dev --print

# Build specific target
docker buildx bake -f docker/docker-bake.hcl prod --load

# Run linting checks
docker buildx bake -f docker/docker-bake.hcl validate

# View logs
docker compose --env-file .env -f docker/docker-compose.yml logs -f backend

# Access database shell
docker compose --env-file .env -f docker/docker-compose.yml exec postgres psql -U riot_api_user -d riot_api_db

# Restart service
docker compose --env-file .env -f docker/docker-compose.yml restart backend
```

## Best Practices
- **Always use scripts** (`./scripts/dev.sh`, `./scripts/prod.sh`) instead of direct Docker commands
- **Builds are parallel**: Docker Bake builds backend and frontend simultaneously
- **Cache is local**: Builds use `/tmp/.buildx-cache` for faster rebuilds
- **Hot reload enabled**: No need to rebuild after code changes in development
- **Use service names**: `backend`, `frontend`, `postgres` (not container names)
- **Include `--env-file .env`** in all direct Docker Compose commands

## Build Optimization
- **Layer caching**: Dependencies cached separately from application code
- **Multi-stage builds**: Only runtime dependencies in final images
- **Parallel builds**: Backend and frontend build simultaneously with Bake
- **Local cache**: Shared cache across builds in `/tmp/.buildx-cache`
- **Non-root users**: All services run as non-root for security

## Do Not
- Restart containers after code changes - use hot reload
- Run Docker commands without `--env-file .env`
- Clear `/tmp/.buildx-cache` unless troubleshooting build issues
- Remove volumes without backup confirmation
- Edit files in `docker/postgres/` manually

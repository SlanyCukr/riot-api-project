# Utility Scripts

This directory contains utility scripts for Docker cleanup and database replication. All Docker Compose commands are now executed directly - see `docker/AGENTS.md` for comprehensive command reference.

## Available Scripts

### Docker Cleanup (`docker-cleanup.sh`)

Removes unused Docker resources and resolves port conflicts:

```bash
./scripts/docker-cleanup.sh
```

**What it cleans**:

- Stops local PostgreSQL service to prevent port conflicts
- Stops Docker Compose services
- Removes orphaned containers (riot_api, postgres on port 5432)
- Removes orphaned networks
- Verifies ports 3000, 5432, 8000 are free

**When to use**:

- Port conflicts on startup
- Disk space running low
- Build cache causing issues
- After major changes to Docker configuration
- Before switching between development and production

### PostgreSQL Replication Setup (`setup-replication-dev.sh`)

Sets up PostgreSQL logical replication from production to development environment:

```bash
./scripts/setup-replication-dev.sh
```

**What it does**:

- Configures development database as replica of production
- Sets up logical replication slots and subscriptions
- Handles connection and authentication setup
- Monitors replication status

**When to use**:

- Initial development environment setup
- After production database schema changes
- When replication needs to be re-established
- For testing production-like data locally

**Prerequisites**:

- Production database accessible from development environment
- Appropriate PostgreSQL permissions
- Network connectivity between environments

## Docker Compose Commands

**All Docker Compose commands are now executed directly from the project root.**

See `docker/AGENTS.md` for comprehensive command reference including:

- Development workflow (`docker compose up -d`)
- Production deployment (`docker compose -f compose.yaml -f compose.prod.yaml up -d`)
- Database operations (`docker compose exec postgres psql ...`)
- Alembic migrations (`docker compose exec backend uv run alembic ...`)
- Logging and debugging
- Building with Docker Bake

## Pre-commit Hooks

Always run pre-commit hooks before creating PRs:

```bash
pre-commit run --all-files
```

**Checks include**:

- **pydocstyle**: All docstrings present and formatted correctly
- **pyright**: No type errors (runs in Docker with full dependency access)
- **ruff**: Code style and quality
- **bandit**: Security vulnerabilities
- **vulture**: Dead code detection
- **radon**: Complexity analysis
- **Frontend checks**: ESLint, TypeScript, etc.

**Never skip pre-commit hooks** with `--no-verify` unless absolutely necessary and approved by team.

## Guidelines

✅ **Do**:

- Use direct Docker Compose commands (see `docker/AGENTS.md`)
- Run `./scripts/docker-cleanup.sh` when disk space is low
- Run pre-commit hooks before every commit
- Refer to `docker/AGENTS.md` for all Docker operations

❌ **Don't**:

- Clear `/tmp/.buildx-cache` manually (use `docker system prune -f` or docker-cleanup.sh)
- Skip pre-commit hooks with `--no-verify`
- Create wrapper scripts (use direct Docker commands instead)
- Run local PostgreSQL service while using Docker Compose (port conflicts)

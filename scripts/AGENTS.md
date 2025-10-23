# Utility Scripts

This directory contains utility scripts for Docker cleanup. All Docker Compose commands are now executed directly - see `docker/AGENTS.md` for comprehensive command reference.

## Available Scripts

### Docker Cleanup (`docker-cleanup.sh`)

Removes unused Docker resources to free up disk space:

```bash
./scripts/docker-cleanup.sh
```

**What it cleans**:

- Stopped containers
- Dangling images (untagged)
- Unused build cache
- Unused networks
- Dangling volumes

**When to use**:

- Disk space running low
- Build cache causing issues
- After major changes to Docker configuration

## Docker Compose Commands

**All Docker Compose commands are now executed directly from the project root.**

See `docker/AGENTS.md` for comprehensive command reference including:

- Development workflow (`docker compose watch`)
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

- Clear `/tmp/.buildx-cache` manually (use docker-cleanup.sh)
- Skip pre-commit hooks with `--no-verify`
- Create wrapper scripts (use direct Docker commands instead)

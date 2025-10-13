# Scripts Reference

## Development & Production

```bash
./scripts/dev.sh              # Start dev (hot reload + watch mode)
./scripts/prod.sh             # Start production
./scripts/dev.sh --help       # Show all options
```

**Key flags:** `--build`, `--reset-db`, `--clean`, `--down`

## Database Reset

```bash
./scripts/dev.sh --reset-db   # Wipe and recreate DB from SQLAlchemy models
./scripts/prod.sh --reset-db  # Production DB reset
```

## Utility Scripts

```bash
./scripts/docker-cleanup.sh   # Clean Docker resources, fix port conflicts
```

## Testing

```bash
docker compose -f docker/docker-compose.yml exec backend uv run pytest
uvx pre-commit run --all-files
```

See `docker/AGENTS.md` for logs, exec, and troubleshooting.

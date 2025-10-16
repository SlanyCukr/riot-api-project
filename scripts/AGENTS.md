# Development Scripts

Quick command reference for development workflows. For Docker build system details, see `docker/AGENTS.md`.

## Scripts

### Development (`dev.sh`)
```bash
./scripts/dev.sh                  # Start with hot reload
./scripts/dev.sh --build          # Rebuild (Docker Bake parallel builds)
./scripts/dev.sh --build backend  # Build only backend
./scripts/dev.sh --reset-db       # Reset database
./scripts/dev.sh --down           # Stop all services
./scripts/dev.sh --clean          # Clean Docker resources then start
./scripts/dev.sh --no-watch       # Start without watch mode
./scripts/dev.sh -d               # Start in detached mode
```

### Production (`prod.sh`)
```bash
./scripts/prod.sh                     # Start production environment
./scripts/prod.sh --build             # Rebuild with Docker Bake
./scripts/prod.sh --build --no-cache  # Clean build (for deployments)
./scripts/prod.sh --reset-db          # Reset production database (⚠️ destructive)
./scripts/prod.sh --down              # Stop all services
./scripts/prod.sh --logs              # Start and follow logs

# Typical deployment workflow
git pull && ./scripts/prod.sh --build
```

### Utilities
```bash
./scripts/docker-cleanup.sh       # Clean Docker resources
```

## Guidelines

- Always use scripts instead of direct Docker commands
- All builds use Docker Bake automatically (no flags needed)
- Builds use parallel backend + frontend builds with local caching
- Hot reload works for both frontend and backend (no restart needed)

**Do Not**:
- Run Docker commands directly - use scripts
- Clear `/tmp/.buildx-cache` unless troubleshooting
- Use production scripts for development
- Modify scripts without testing all options

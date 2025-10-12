# Docker Operations Guide

Agent-specific Docker commands. See root `README.md` for project context.

**Use `docker compose` (v2) not `docker-compose` (v1).**

## Service Management

### Start/Stop
```bash
docker compose up --build              # Start all with rebuild
docker compose up -d                   # Start detached (background)
docker compose up backend frontend     # Start specific services
docker compose down                    # Stop all
docker compose down -v                 # Stop and remove volumes (WARNING: deletes data)
docker compose restart backend         # Restart specific service
```

### Status & Logs
```bash
docker compose ps                      # Service status
docker compose stats                   # Resource usage
docker compose logs -f backend         # Follow logs
docker compose logs --tail=100 postgres
```

### Container Access
```bash
docker compose exec backend bash       # Backend shell
docker compose exec frontend bash      # Frontend shell
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# One-off commands
docker compose exec backend uv run python --version
docker compose exec frontend node --version
```

## Production Deployment

### Production Commands
```bash
# Start production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Scale services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2

# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop production
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Production Checklist
- Set environment variables in `.env` or export them
- Use specific image tags (not `latest`)
- Enable HTTPS (use reverse proxy like nginx/Traefik)
- Configure resource limits and health checks
- Containers run as non-root (already configured)

## Image Management

### Building
```bash
docker compose build                   # Build all
docker compose build backend           # Build specific service
docker compose build --no-cache        # Force rebuild without cache
```

### Cleaning
```bash
docker images                          # List images
docker image prune -a                  # Remove unused images
docker compose down --rmi all          # Remove all project images
```

## Volume Management

### Volumes
- `postgres-data` - Database storage (persistent)
- `backend-logs` - Backend logs (persistent)
- Source code - Mounted for hot reload (dev only)

### Backup Database
```bash
# Backup volume
docker run --rm \
  -v ${COMPOSE_PROJECT_NAME}_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volume
docker run --rm \
  -v ${COMPOSE_PROJECT_NAME}_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /data

# pg_dump backup (see docker/postgres/CLAUDE.md)
docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql
```

### Reset Database
```bash
# WARNING: Deletes all data
docker compose down -v
docker compose up --build
```

## Utility Scripts
```bash
./scripts/clean-local.sh               # Clean local artifacts
./scripts/seed-dev-data.sh             # Seed test data (Jim Morioriarty#2434, Level 794)
```

## Environment Configuration
```bash
# Custom .env file
docker compose --env-file .env.custom up

# Override variables
export RIOT_API_KEY=your_key
docker compose up
```

See root `CLAUDE.md` for required variables.

## Health Checks
Health checks configured for all services:
- **Backend**: HTTP check at `/health`
- **Frontend**: Application readiness
- **Database**: PostgreSQL connection

```bash
docker compose ps                      # View health status
docker compose logs --tail=50          # Check health logs
```

## Troubleshooting

### Common Issues
- **Port conflicts**: Ports 8000, 3000, 5432 must be available
- **Volume permissions**: Ensure Docker has project access
- **Out of memory**: Increase Docker Desktop memory

### Debug Commands
```bash
docker compose inspect backend         # Detailed container info
docker compose logs backend --tail=200 # Check error logs
docker compose restart backend         # Restart stuck service
docker compose down -v && docker compose up --build  # Full reset
```

## Networking
Services use Docker internal networking:
- Backend: http://localhost:8000 (dev)
- Frontend: http://localhost:3000 (dev)
- Database: Internal at `postgres:5432` (not exposed externally)

## Security Notes
- Containers run as non-root users (configured)
- Use specific image tags for production
- Enable HTTPS in production
- Never commit secrets (use env vars)
- Scan images: `docker scan <image>`

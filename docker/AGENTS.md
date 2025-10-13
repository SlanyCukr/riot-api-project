# Docker Operations Guide

Advanced Docker operations and production deployment.

**Quick Start:** Use `./scripts/dev.sh` or `./scripts/prod.sh` (see `scripts/AGENTS.md` for details)

## Common Operations

### View Logs
```bash
# Follow logs
docker compose -f docker/docker-compose.yml logs -f backend         # Follow backend logs
docker compose -f docker/docker-compose.yml logs -f frontend        # Follow frontend logs
docker compose -f docker/docker-compose.yml logs -f postgres        # Follow postgres logs
docker compose -f docker/docker-compose.yml logs -f                 # Follow all services

# Last N lines
docker compose -f docker/docker-compose.yml logs --tail=100 backend # Last 100 lines
docker compose -f docker/docker-compose.yml logs --since 5m         # Last 5 minutes
```

### Execute Commands in Containers
```bash
# Shell access
docker compose -f docker/docker-compose.yml exec backend bash       # Backend shell
docker compose -f docker/docker-compose.yml exec frontend bash      # Frontend shell

# Database access
docker compose -f docker/docker-compose.yml exec postgres psql -U riot_api_user -d riot_api_db

# Run specific commands
docker compose -f docker/docker-compose.yml exec backend uv run python -m app.some_module
docker compose -f docker/docker-compose.yml exec frontend npm run build
```

### Service Management
```bash
# Start/stop specific services
docker compose -f docker/docker-compose.yml start backend           # Start stopped service
docker compose -f docker/docker-compose.yml stop backend            # Stop without removing
docker compose -f docker/docker-compose.yml restart backend         # Restart service

# Check status
docker compose -f docker/docker-compose.yml ps                      # Service status
docker compose -f docker/docker-compose.yml top                     # Running processes
docker compose -f docker/docker-compose.yml stats                   # Resource usage
```

## Production Deployment

### Production Commands
```bash
# Start production stack
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build -d

# Scale services
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2

# View logs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f

# Stop production
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down
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
docker compose -f docker/docker-compose.yml build                   # Build all
docker compose -f docker/docker-compose.yml build backend           # Build specific service
docker compose -f docker/docker-compose.yml build --no-cache        # Force rebuild without cache
```

### Cleaning
```bash
docker images                                                # List images
docker image prune -a                                        # Remove unused images
docker compose -f docker/docker-compose.yml down --rmi all   # Remove all project images
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

# pg_dump backup (see docker/postgres/AGENTS.md)
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql
```

### Reset Database
```bash
# WARNING: Deletes all data
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up --build
```

## Environment Configuration

### Using Custom .env Files
```bash
docker compose -f docker/docker-compose.yml --env-file .env.prod up
docker compose -f docker/docker-compose.yml --env-file .env.staging up
```

### Runtime Overrides
```bash
export RIOT_API_KEY=<your-riot-api-key>
export DATABASE_URL=<your-database-url>
docker compose -f docker/docker-compose.yml up
```

### Multi-Environment Setup
```bash
# Development (default)
docker compose -f docker/docker-compose.yml up

# Staging
docker compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml up

# Production
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up
```

## Health Checks
Health checks configured for all services:
- **Backend**: HTTP check at `/health`
- **Frontend**: Application readiness
- **Database**: PostgreSQL connection

```bash
docker compose -f docker/docker-compose.yml ps                      # View health status
docker compose -f docker/docker-compose.yml logs --tail=50          # Check health logs
```

## Networking

### Internal Networking
Services communicate via Docker internal network:
```yaml
backend → postgres:5432      # Database connection
frontend → backend:8000      # API calls (server-side)
```

### Port Mapping
Development ports exposed to host:
- Backend: `localhost:8000` → container:8000
- Frontend: `localhost:3000` → container:3000
- Database: Not exposed (internal only)

### Production Networking
In production, use reverse proxy (nginx/Traefik) for:
- SSL/TLS termination
- Load balancing
- Rate limiting
- Domain routing

## Troubleshooting

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :8000
lsof -i :3000
lsof -i :5432

# Kill process or change ports in docker/docker-compose.yml
```

**Volume permissions:**
```bash
# Ensure Docker has access to project directory
# Docker Desktop: Check Settings → Resources → File Sharing
```

**Out of memory:**
```bash
# Increase Docker Desktop memory limit
# Settings → Resources → Memory (recommend 4GB+)

# Check container memory usage
docker compose -f docker/docker-compose.yml stats
```

**Container won't start:**
```bash
docker compose -f docker/docker-compose.yml logs backend --tail=200   # Check logs
docker compose -f docker/docker-compose.yml inspect backend           # Detailed info
docker compose -f docker/docker-compose.yml restart backend           # Try restart
docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml up --build  # Full reset
```

## Security Notes
- Containers run as non-root users (configured)
- Use specific image tags for production
- Enable HTTPS in production
- Never commit secrets (use env vars)
- Scan images: `docker scan <image>`

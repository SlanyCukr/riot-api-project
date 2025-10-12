# Docker Operations Guide

Advanced Docker operations and production deployment. **See root `CLAUDE.md` for common docker compose commands.**

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

## Environment Configuration

### Using Custom .env Files
```bash
docker compose --env-file .env.prod up
docker compose --env-file .env.staging up
```

### Runtime Overrides
```bash
export RIOT_API_KEY=<your-riot-api-key>
export DATABASE_URL=<your-database-url>
docker compose up
```

### Multi-Environment Setup
```bash
# Development (default)
docker compose up

# Staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## Health Checks
Health checks configured for all services:
- **Backend**: HTTP check at `/health`
- **Frontend**: Application readiness
- **Database**: PostgreSQL connection

```bash
docker compose ps                      # View health status
docker compose logs --tail=50          # Check health logs
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

# Kill process or change ports in docker-compose.yml
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
docker compose stats
```

**Container won't start:**
```bash
docker compose logs backend --tail=200   # Check logs
docker compose inspect backend           # Detailed info
docker compose restart backend           # Try restart
docker compose down -v && docker compose up --build  # Full reset
```

## Security Notes
- Containers run as non-root users (configured)
- Use specific image tags for production
- Enable HTTPS in production
- Never commit secrets (use env vars)
- Scan images: `docker scan <image>`

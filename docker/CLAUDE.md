# Docker Deployment Guide

## Overview

All services run exclusively through Docker containers. Hot reload, database migrations, and health checks are configured automatically for development.

**Use `docker compose` (v2) not `docker-compose` (v1).**

## Development Workflow

### Starting Services

```bash
# Start all services
docker compose up --build

# Start specific service
docker compose up backend
docker compose up frontend

# Start in background (detached)
docker compose up -d

# Stop all services
docker compose down
```

### Service Management

```bash
# Check service status
docker compose ps

# View resource usage
docker compose stats

# Restart specific service
docker compose restart backend

# View logs (follow mode)
docker compose logs -f backend frontend

# View recent logs
docker compose logs --tail=100 backend
```

### Container Access

```bash
# Access backend shell
docker compose exec backend bash

# Access frontend shell
docker compose exec frontend bash

# Access database shell
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# Execute one-off commands
docker compose exec backend uv run python --version
docker compose exec frontend node --version
```

## Production Deployment

### Production Commands

```bash
# Start production deployment
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Scale services horizontally
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2

# View production logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop production services
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Production Configuration

- Set environment variables in `.env` or export them
- Use specific image tags, not `latest`
- Enable HTTPS (configure reverse proxy like nginx or Traefik)
- Configure proper resource limits and health checks
- Run containers as non-root users (already configured)

## Networking

Services communicate through Docker internal networking:

- **Backend**: Accessible at `http://localhost:8000` (dev) or configured port
- **Frontend**: Accessible at `http://localhost:3000` (dev) or configured port
- **Database**: Internal service at `postgres:5432` (not exposed externally)

Backend and frontend services reference database via hostname `postgres`.

## Image Management

### Building Images

```bash
# Build all images
docker compose build

# Build specific service
docker compose build backend

# Force rebuild without cache
docker compose build --no-cache
```

### Cleaning Images

```bash
# List images
docker images

# Remove unused images
docker image prune -a

# Remove all project images
docker compose down --rmi all
```

## Volume Management

### Volumes

- **`postgres-data`**: Persistent database storage (named `${COMPOSE_PROJECT_NAME}_postgres-data`)
- **`backend-logs`**: Persisted backend log files (`${COMPOSE_PROJECT_NAME}_backend-logs`)
- **Source code**: Mounted for development hot reload via `docker-compose.override.yml`

### Backup & Restore

```bash
# Backup database volume
docker run --rm \
  -v ${COMPOSE_PROJECT_NAME}_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore database volume
docker run --rm \
  -v ${COMPOSE_PROJECT_NAME}_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /data

# Alternative: Use pg_dump (see docker/postgres/CLAUDE.md)
```

### Reset Database

```bash
# Remove volume and restart (WARNING: deletes all data)
docker compose down -v
docker compose up --build
```

## Utility Scripts

Located in `scripts/` directory:

```bash
# Clean local development artifacts
./scripts/clean-local.sh

# Seed development test data (Jim Morioriarty#2434 from EUNE, Level 794)
./scripts/seed-dev-data.sh
```

See `docker/postgres/CLAUDE.md` for database-specific operations.

## Environment Configuration

```bash
# Use custom .env file
docker compose --env-file .env.custom up

# Override specific variables
export RIOT_API_KEY=your_api_key
docker compose up
```

See root `CLAUDE.md` for required environment variables.

## Health Checks

Health checks configured for all services:

- **Backend**: HTTP health check at `/health`
- **Frontend**: Application readiness check
- **Database**: PostgreSQL connection test

```bash
# Check container health status
docker compose ps

# View health check logs
docker compose logs --tail=50
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports 8000, 3000, 5432 are available
2. **Volume permissions**: Ensure Docker has access to project directory
3. **Network issues**: Check firewall settings and Docker network configuration
4. **Out of memory**: Increase Docker Desktop memory allocation

### Debug Commands

```bash
# View detailed container info
docker compose inspect backend

# Check logs for errors
docker compose logs backend --tail=200

# Restart stuck service
docker compose restart backend

# Complete reset (removes volumes)
docker compose down -v && docker compose up --build
```

### Performance Issues

- Check resource usage: `docker compose stats`
- Review container logs for bottlenecks
- Ensure sufficient disk space for images and volumes
- Consider increasing Docker Desktop resource limits

## Security Best Practices

- Run containers as non-root users (already configured)
- Use specific image tags for reproducible builds
- Keep base images updated regularly
- Enable HTTPS in production
- Never commit secrets to git (use environment variables)
- Scan images for vulnerabilities: `docker scan <image>`
- Implement proper network isolation in production

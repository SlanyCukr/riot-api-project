# Docker Deployment Guide

## Docker-Only Development

Project runs exclusively through Docker containers. Database migrations, hot reload, and health checks configured automatically.

## Quick Start

```bash
# Start all services with hot reload
docker compose up --build

# Start specific service
docker compose up backend
docker compose up frontend

# Stop all services
docker compose down
```

Use `docker compose` (v2) not `docker-compose` (v1).

## Production Deployment

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Scale services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2

# View production logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Stop production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

## Service Management

```bash
# Check service status
docker-compose ps

# View resource usage
docker-compose stats

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend frontend
```

## Container Access

```bash
# Access backend shell
docker-compose exec backend bash

# Access frontend shell
docker-compose exec frontend bash

# Execute commands
docker-compose exec backend uv run python --version
docker-compose exec frontend node --version
```

## Networking

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Database: Internal service at `postgres:5432`

## Image Management

```bash
# Build images
docker-compose build
docker-compose build --no-cache

# View/clean images
docker images
docker image prune -a
```

## Volume Management

- Database data persisted in `postgres_data` volume
- Source code mounted for development hot reload

```bash
# Backup database volume
docker run --rm -v riot-api-project_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Environment Configuration

```bash
# Custom .env file
docker-compose --env-file .env.custom up

# Production variables
export RIOT_API_KEY=your_api_key
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Utility Scripts

```bash
# Clean local development artifacts
./scripts/clean-local.sh

# Seed test data (Jim Morioriarty#2434 from EUNE)
./scripts/seed-dev-data.sh
```

## Health Checks

- Backend: HTTP health check endpoint
- Database: PostgreSQL connection test
- Frontend: Application readiness check

```bash
# Check container health
docker-compose ps
docker-compose logs --tail=50
```

## Security

- Non-root users in containers
- Use specific image tags, not latest
- HTTPS in production
- Regular security updates

## Troubleshooting

```bash
# Debug commands
docker-compose logs backend
docker-compose logs --tail=100 backend
docker-compose inspect backend
```

Common issues: port conflicts, volume permissions, network firewall settings.

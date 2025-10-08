# Docker Deployment Guide

This file provides guidance for Docker-based development and deployment.

## Docker-Only Development

This project is designed to run exclusively through Docker containers. All development, testing, and deployment operations should be performed using Docker Compose.

### Important Notes
- **Database Migrations**: Automatically applied on backend container startup via `entrypoint.sh`
- **Hot Reload**: Both backend and frontend support hot reload in development mode
- **Health Checks**: All containers have health checks configured (backend, frontend, postgres)
- **Environment Variables**: Loaded from `.env` file - restart containers after updating `.env`

## Development Environment

### Basic Commands
```bash
# Start all services with hot reload
docker compose up --build

# Note: Use 'docker compose' (v2) not 'docker-compose' (v1)

# Start specific service
docker-compose up backend
docker-compose up frontend

# Stop all services
docker-compose down

# Clean up volumes (database data)
docker-compose down -v

# View logs
docker-compose logs -f [service]
docker-compose logs -f backend frontend

# Rebuild and start
docker-compose up --build --force-recreate
```

### Service Management
```bash
# Check service status
docker-compose ps

# View resource usage
docker-compose stats

# Restart specific service
docker-compose restart backend

# Stop specific service
docker-compose stop frontend

# Remove stopped containers
docker-compose rm -f
```

## Production Environment

### Production Deployment
```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Scale services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2

# View status
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Stop production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Clean up production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

### Production Monitoring
```bash
# View production logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Tail logs with timestamps
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --timestamps backend
```

## Container Management

### Development Containers
```bash
# Access backend container shell
docker-compose exec backend bash

# Access frontend container shell
docker-compose exec frontend bash

# Access database container
docker-compose exec postgres bash

# Execute commands in containers
docker-compose exec backend uv run python --version
docker-compose exec frontend node --version
```

### Production Containers
```bash
# Access production containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec backend bash

# View container processes
docker-compose top

# Inspect container configuration
docker-compose inspect backend
```

## Image Management

### Building Images
```bash
# Build specific service image
docker-compose build backend

# Build all images
docker-compose build

# Build with no cache
docker-compose build --no-cache

# Build specific image with tag
docker-compose build backend
docker tag riot-api-project_backend:latest my-registry/backend:v1.0.0
```

### Image Optimization
```bash
# View image sizes
docker images

# Remove unused images
docker image prune

# Remove all unused images
docker image prune -a

# View image history
docker history riot-api-project_backend:latest
```

## Networking

### Service Communication
- Backend available at `http://localhost:8000`
- Frontend available at `http://localhost:3000`
- Database accessible internally at `postgres:5432`

### Port Configuration
- Backend: 8000 (host) → 8000 (container)
- Frontend: 3000 (host) → 3000 (container)
- Database: 5432 (host) → 5432 (container)

## Volume Management

### Data Persistence
- Database data persisted in `postgres_data` volume
- Source code mounted for development hot reload

### Volume Commands
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect riot-api-project_postgres_data

# Remove unused volumes
docker volume prune

# Create backup of database volume
docker run --rm -v riot-api-project_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Health Checks

### Container Health
```bash
# Check container health
docker-compose ps

# View health check logs
docker-compose logs --tail=50

# Manually trigger health check
docker-compose exec backend curl -f http://localhost:8000/health || exit 1
```

### Custom Health Checks
- Backend: HTTP health check endpoint
- Database: PostgreSQL connection test
- Frontend: Application readiness check

## Environment Configuration

### Development Environment
```bash
# Override development settings
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Use custom .env file
docker-compose --env-file .env.custom up
```

### Production Environment
```bash
# Set production environment variables
export RIOT_API_KEY=your_api_key
export POSTGRES_PASSWORD=your_password
export SECRET_KEY=your_secret_key

# Use production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Security Considerations

### Container Security
- Use non-root users in containers
- Limit container capabilities
- Use specific image tags instead of latest
- Implement resource limits

### Network Security
- Use internal networks for service communication
- Implement proper firewall rules
- Use HTTPS in production
- Monitor network traffic

### Best Practices
- Regular security updates
- Scan images for vulnerabilities
- Use secrets management
- Implement proper logging

## Utility Scripts

### Clean Local Environment
Remove local development artifacts when switching to pure Docker development:

```bash
# Run cleanup script
./scripts/clean-local.sh
```

This script removes:
- Python virtual environments (.venv, venv)
- Node.js dependencies (node_modules)
- Build artifacts (dist, build)
- Cache files (.cache, .pytest_cache, .mypy_cache)
- Log files (*.log, logs/)
- Temporary files (*.tmp, .eslintcache)

### Seed Development Data
Insert test data into the database for development and testing:

```bash
# Seed test player data
./scripts/seed-dev-data.sh
```

This script:
- Inserts a real test player (Jim Morioriarty#2434 from EUNE)
- Can be run multiple times safely (uses upsert logic)
- Useful for testing player search, match history, and smurf detection features
- Requires database to be running and migrations applied

## Troubleshooting

### Common Issues
- Port conflicts: Check for running services
- Volume permissions: Check user permissions
- Network issues: Check firewall settings
- Image build failures: Check Dockerfile syntax

### Debug Commands
```bash
# View container logs
docker-compose logs backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Follow logs with timestamps
docker-compose logs -f --timestamps backend

# View system events
docker-compose events

# Inspect container
docker-compose inspect backend
```

# Docker Troubleshooting Guide

## Common Port Conflict Issues

### Problem: "Bind for 0.0.0.0:5432 failed: port is already allocated"

This happens when:
1. Local PostgreSQL service is running in WSL
2. Old Docker containers are still holding the ports
3. Multiple Docker Compose projects with conflicting names

### Quick Fix

Run the cleanup script:
```bash
./scripts/docker-cleanup.sh
```

Then start your services:
```bash
docker compose up --build
```

### Manual Fix

1. **Stop local PostgreSQL:**
   ```bash
   sudo service postgresql stop
   ```

2. **Stop all Docker Compose services:**
   ```bash
   docker compose down
   ```

3. **Find and remove orphaned containers:**
   ```bash
   docker ps -a | grep riot
   docker rm -f <container_id>
   ```

4. **Find and remove orphaned networks:**
   ```bash
   docker network ls | grep riot
   docker network rm <network_id>
   ```

5. **Verify ports are free:**
   ```bash
   netstat -tuln | grep -E ':(3000|5432|8000)'
   ```

6. **Start fresh:**
   ```bash
   docker compose up --build
   ```

## Alternative: Use Different Ports

If you need to keep local PostgreSQL running, edit `.env`:

```bash
# Change from:
POSTGRES_PORT=5432
FRONTEND_PORT=3000

# To:
POSTGRES_PORT=5433
FRONTEND_PORT=3001
```

Then update your connection strings accordingly.

## Useful Docker Commands

### View running containers
```bash
docker compose ps
```

### View logs
```bash
docker compose logs -f              # All services
docker compose logs -f frontend     # Frontend only
docker compose logs -f backend      # Backend only
docker compose logs -f postgres     # Database only
```

### Restart a specific service
```bash
docker compose restart frontend
docker compose restart backend
```

### Rebuild and restart
```bash
docker compose up --build -d
```

### Complete cleanup (removes volumes - DATA LOSS!)
```bash
docker compose down -v
```

## WSL-Specific Issues

### Docker Desktop Integration

Make sure Docker Desktop WSL integration is enabled:
1. Open Docker Desktop
2. Settings → Resources → WSL Integration
3. Enable integration for your WSL distribution

### Local Services Conflicting

Common services that might use ports in WSL:
- PostgreSQL: `sudo service postgresql stop`
- Node.js dev servers: Find and kill process using `lsof -i :3000`
- Other databases: `sudo service mysql stop`, etc.

## Health Checks

The containers have health checks configured. To see health status:
```bash
docker compose ps
```

Healthy containers show `(healthy)` in the STATUS column.

## Prevention

To avoid these issues:

1. **Always use the cleanup script** before starting:
   ```bash
   ./scripts/docker-cleanup.sh && docker compose up --build
   ```

2. **Use unique project names** in `.env`:
   ```bash
   COMPOSE_PROJECT_NAME=riot_api_app
   ```

3. **Stop services when done**:
   ```bash
   docker compose down
   ```

4. **Don't run local PostgreSQL** while using Docker PostgreSQL

## Getting Help

If you're still having issues:

1. Check what's using the ports:
   ```bash
   sudo lsof -i :5432
   sudo lsof -i :3000
   sudo lsof -i :8000
   ```

2. Check Docker logs:
   ```bash
   docker compose logs
   ```

3. Verify Docker Desktop is running and WSL integration is enabled

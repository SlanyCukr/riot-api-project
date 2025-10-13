# Docker Operations for Agents

**When to read this:** Direct Docker operations, debugging containers, or production deployment. For normal development, use `./scripts/dev.sh` or `./scripts/prod.sh` instead (see `scripts/AGENTS.md`).

## ⚠️ Critical: Hot Reload - DON'T RESTART CONTAINERS

**Agents often restart containers unnecessarily!** Both backend and frontend have hot reload:
- **Frontend**: Next.js hot reload - code changes auto-update in browser
- **Backend**: FastAPI auto-reload - Python file changes auto-restart server

**Only rebuild/restart when:**
- Changing dependencies (package.json, pyproject.toml, uv.lock)
- Modifying Dockerfile or docker-compose.yml
- Adding system packages

**For code changes: Just save the file. That's it.**

---

## Command Shorthand

All commands use this pattern:
```bash
docker compose --env-file .env -f docker/docker-compose.yml <command>
```

**For readability below, assume `$DC` represents the above.** In practice, always use the full command or create an alias:
```bash
alias dc="docker compose --env-file .env -f docker/docker-compose.yml"
```

---

## Quick Task Reference

**What do you want to do?**

| Task | Command | When to Use |
|------|---------|-------------|
| **View logs** | `$DC logs -f backend` | Debugging errors, monitoring |
| **Shell access** | `$DC exec backend bash` | Run commands inside container |
| **Database shell** | `$DC exec postgres psql -U riot_api_user -d riot_api_db` | Query database directly |
| **Check status** | `$DC ps` | See if services are healthy |
| **Restart service** | `$DC restart backend` | After config changes (not code!) |
| **Rebuild** | `$DC up --build -d` | After dependency changes |
| **Stop all** | `$DC down` | Clean shutdown |
| **Reset database** | `./scripts/dev.sh --reset-db` | Use scripts, not manual commands |

---

## Common Agent Tasks

### Debugging: View Logs
```bash
# Follow logs (real-time)
docker compose --env-file .env -f docker/docker-compose.yml logs -f backend
docker compose --env-file .env -f docker/docker-compose.yml logs -f frontend
docker compose --env-file .env -f docker/docker-compose.yml logs -f postgres

# Last N lines
docker compose --env-file .env -f docker/docker-compose.yml logs --tail=100 backend
docker compose --env-file .env -f docker/docker-compose.yml logs --since 5m
```

### Execute Commands in Containers
```bash
# Shell access
docker compose --env-file .env -f docker/docker-compose.yml exec backend bash
docker compose --env-file .env -f docker/docker-compose.yml exec frontend bash

# Database access (see docker/postgres/AGENTS.md for queries)
docker compose --env-file .env -f docker/docker-compose.yml exec postgres psql -U riot_api_user -d riot_api_db

# Run Python module
docker compose --env-file .env -f docker/docker-compose.yml exec backend uv run python -m app.module_name

# Run tests
docker compose --env-file .env -f docker/docker-compose.yml exec backend uv run pytest

# Frontend build
docker compose --env-file .env -f docker/docker-compose.yml exec frontend npm run build
```

### Check Service Health
```bash
# Service status and health
docker compose --env-file .env -f docker/docker-compose.yml ps

# Resource usage
docker compose --env-file .env -f docker/docker-compose.yml stats

# Running processes
docker compose --env-file .env -f docker/docker-compose.yml top
```

### Service Control (Rare - Use Scripts Instead)
```bash
# Restart after config changes (NOT for code changes!)
docker compose --env-file .env -f docker/docker-compose.yml restart backend

# Stop without removing
docker compose --env-file .env -f docker/docker-compose.yml stop backend

# Start stopped service
docker compose --env-file .env -f docker/docker-compose.yml start backend
```

## Production Deployment

**Prefer `./scripts/prod.sh` for production management.** Direct commands for advanced use only.

### Production Stack
```bash
# Start (use ./scripts/prod.sh instead)
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build -d

# Scale services
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --scale backend=3

# Stop
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down
```

### Production Checklist
- [ ] Set environment variables in `.env`
- [ ] Use specific image tags (not `latest`)
- [ ] Enable HTTPS via reverse proxy (nginx/Traefik)
- [ ] Configure resource limits and health checks
- [ ] Verify containers run as non-root (already configured)

---

## Advanced Operations

### Build & Clean
```bash
# Build
docker compose --env-file .env -f docker/docker-compose.yml build
docker compose --env-file .env -f docker/docker-compose.yml build --no-cache

# Clean up
docker image prune -a
docker compose --env-file .env -f docker/docker-compose.yml down --rmi all
```

### Database Backup & Reset
```bash
# Backup (prefer pg_dump - see docker/postgres/AGENTS.md)
docker compose --env-file .env -f docker/docker-compose.yml exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql

# Reset database (⚠️ DELETES ALL DATA)
./scripts/dev.sh --reset-db     # Preferred method
./scripts/prod.sh --reset-db    # Production reset

# Manual reset (not recommended)
docker compose --env-file .env -f docker/docker-compose.yml down -v
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

### Multi-Environment .env Files
```bash
# Use different .env files for different environments
docker compose --env-file .env.prod -f docker/docker-compose.yml up
docker compose --env-file .env.staging -f docker/docker-compose.yml up
```

---

## Architecture Reference

### Volumes (Persistent Data)
- `postgres-data` - Database storage (persistent)
- `backend-logs` - Backend logs (persistent)
- Source code - Mounted for hot reload (dev only)

### Internal Networking
Services communicate via Docker internal network:
- `backend → postgres:5432` - Database connection
- `frontend → backend:8000` - API calls (server-side)

### Port Mapping (Development)
- Backend: `localhost:${BACKEND_PORT}` → container:8000 (default: 8000)
- Frontend: `localhost:${FRONTEND_PORT}` → container:3000 (default: 3000)
- Database: `localhost:${POSTGRES_PORT}` → container:5432 (default: 5432)

### Health Checks
All services have health checks configured:
- **Backend**: HTTP check at `/health`
- **Frontend**: Application readiness
- **Database**: PostgreSQL connection

Check health: `docker compose --env-file .env -f docker/docker-compose.yml ps`

---

## Common Mistakes (Agents Read This!)

### ❌ Mistake: Restarting containers after code changes
**Why it's wrong:** Hot reload handles code changes automatically.
**Solution:** Just save the file. Only restart for dependency/config changes.

### ❌ Mistake: Not using scripts for database reset
**Why it's wrong:** Manual `down -v` loses data without confirmation.
**Solution:** Use `./scripts/dev.sh --reset-db` which handles it safely.

### ❌ Mistake: Running commands without `--env-file .env`
**Why it's wrong:** Docker Compose won't load environment variables.
**Solution:** Always include `--env-file .env` flag.

### ❌ Mistake: Checking logs without `-f` or `--tail`
**Why it's wrong:** Dumps entire log history, overwhelming output.
**Solution:** Use `logs -f` (follow) or `logs --tail=100` (last N lines).

## Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :8000
lsof -i :3000
lsof -i :5432

# Solution: Kill process or change ports in docker/docker-compose.yml
```

### Container Won't Start
```bash
# 1. Check logs first
docker compose --env-file .env -f docker/docker-compose.yml logs backend --tail=200

# 2. Check service status
docker compose --env-file .env -f docker/docker-compose.yml ps

# 3. Try restart
docker compose --env-file .env -f docker/docker-compose.yml restart backend

# 4. Full reset (last resort)
docker compose --env-file .env -f docker/docker-compose.yml down -v
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

### Out of Memory
```bash
# Check container memory usage
docker compose --env-file .env -f docker/docker-compose.yml stats

# Solution: Increase Docker Desktop memory limit
# Settings → Resources → Memory (recommend 4GB+)
```

### Volume Permissions
```bash
# Docker Desktop: Settings → Resources → File Sharing
# Ensure Docker has access to project directory
```

---

## Security Checklist

- [x] Containers run as non-root users (already configured)
- [ ] Use specific image tags for production (not `latest`)
- [ ] Enable HTTPS in production (via reverse proxy)
- [ ] Never commit secrets (use `.env` files, gitignored)
- [ ] Scan images: `docker scan <image>` (optional)

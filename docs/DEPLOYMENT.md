# Deployment Guide

This document outlines the deployment process for the Riot API application, including common issues and solutions.

## Table of Contents

- [Production Server Details](#production-server-details)
- [Deployment Types](#deployment-types)
- [Standard Deployment (Code Only)](#standard-deployment-code-only)
- [Deployment with Schema Changes](#deployment-with-schema-changes)
- [Common Issues & Solutions](#common-issues--solutions)
- [Verification Steps](#verification-steps)
- [Rollback Procedure](#rollback-procedure)

---

## Production Server Details

- **Server**: `89.221.212.146:2221`
- **User**: `pi`
- **Project Directory**: `~/riot-api`
- **Docker Compose File**: `docker-compose.prod.yml`
- **Services**:
  - Backend: Port 8086
  - Frontend: Port 8088
  - PostgreSQL: Port 5433

### Access

```bash
ssh -l pi 89.221.212.146 -p 2221
cd riot-api
```

---

## Deployment Types

### 1. Code-Only Deployment
When you only change application code without database schema modifications.

**Examples:**
- Bug fixes
- Feature additions that don't change models
- Configuration updates
- UI changes

### 2. Schema Deployment
When database schema changes are required.

**Examples:**
- Adding/removing model fields
- Creating new tables
- Modifying relationships
- Changing column types

---

## Standard Deployment (Code Only)

### Automatic Deployment via GitHub Actions

The project uses GitHub Actions with a self-hosted runner on the production server.

**Process:**
1. Push code to `main` branch
2. GitHub Actions automatically:
   - Pulls latest code on production server
   - Rebuilds Docker images if needed
   - Restarts services with `docker compose -f docker-compose.prod.yml up -d`

```bash
# Local development machine
git add .
git commit -m "Your commit message"
git push origin main

# GitHub Actions handles the rest automatically
```

### Manual Verification

After automatic deployment, SSH to production and verify:

```bash
ssh -l pi 89.221.212.146 -p 2221
cd riot-api

# Check latest commits
git log --oneline -5

# Verify services are running
docker compose -f docker-compose.prod.yml ps

# Check application health
curl http://localhost:8086/health
```

---

## Deployment with Schema Changes

When database schema changes, follow this process:

### Step 1: Deploy Code

Push code to GitHub (automatic deployment):

```bash
git push origin main
```

### Step 2: SSH to Production

```bash
ssh -l pi 89.221.212.146 -p 2221
cd riot-api
```

### Step 3: Reset Database and Seed Data

**Option A: Using Setup Script (Recommended)**

```bash
./scripts/setup-production.sh
```

**Option B: Manual Steps**

```bash
# 1. Reset database (WARNING: Deletes all data!)
docker compose -f docker-compose.prod.yml exec backend uv run python -m app.init_db reset

# 2. Seed job configurations
./scripts/seed-job-configs.sh

# 3. Seed tracked players
./scripts/seed-dev-data.sh

# 4. Restart backend to reload configurations
docker compose -f docker-compose.prod.yml restart backend

# 5. Wait for services to be healthy
sleep 10
```

### Step 4: Verify Deployment

```bash
# Check health
curl http://localhost:8086/health

# Check job scheduler
curl http://localhost:8086/api/v1/jobs/status/overview

# View backend logs
docker compose -f docker-compose.prod.yml logs backend --tail=50

# Check database
docker compose -f docker-compose.prod.yml exec postgres psql -U riot_api_user -d riot_api_db -c "
SELECT
    (SELECT COUNT(*) FROM matches) as match_count,
    (SELECT COUNT(*) FROM players) as player_count,
    (SELECT COUNT(*) FROM job_configurations) as job_count;
"
```

---

## Common Issues & Solutions

### Issue 1: Foreign Key Violations After Schema Reset

**Symptoms:**
```
ForeignKeyViolationError: insert or update on table "job_executions"
violates foreign key constraint "fk_job_executions_job_config_id_job_configurations"
```

**Cause:** Job scheduler started before job configurations were seeded.

**Solution:**
1. Seed job configurations: `./scripts/seed-job-configs.sh`
2. Restart backend: `docker compose -f docker-compose.prod.yml restart backend`

### Issue 2: Jobs Not Running

**Symptoms:**
- No job executions in logs
- Job status shows 0 active jobs

**Debugging:**
```bash
# Check job configurations in database
docker compose -f docker-compose.prod.yml exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT * FROM job_configurations;"

# Check backend logs for scheduler messages
docker compose -f docker-compose.prod.yml logs backend | grep -i scheduler

# Verify job status via API
curl http://localhost:8086/api/v1/jobs/status/overview
```

**Solution:**
1. Ensure job configurations exist (run `./scripts/seed-job-configs.sh`)
2. Restart backend to reload scheduler
3. Check Riot API key is valid (expires every 24h for dev keys)

### Issue 3: Transaction Errors

**Symptoms:**
```
This transaction is closed
InvalidRequestError: This Session's transaction has been rolled back
```

**Cause:** Multiple commits/rollbacks in nested function calls.

**Solution:** Ensure transaction boundaries are correct:
- Only commit at the top level of operation
- Handle rollback in single exception handler
- Don't commit/rollback in helper functions

### Issue 4: Service Won't Start After Schema Change

**Symptoms:**
```
sqlalchemy.exc.ProgrammingError: relation "table_name" does not exist
```

**Solution:**
1. Check if database tables exist:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U riot_api_user -d riot_api_db -c "\dt"
   ```
2. If tables missing, reset database:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend uv run python -m app.init_db reset
   ```

### Issue 5: Stale Docker Images

**Symptoms:**
- Code changes not appearing
- Old behavior persists after deployment

**Solution:**
```bash
# Rebuild images without cache
docker compose -f docker-compose.prod.yml build --no-cache

# Restart services
docker compose -f docker-compose.prod.yml up -d
```

---

## Verification Steps

### Post-Deployment Checklist

- [ ] **Health Check Passes**
  ```bash
  curl http://89.221.212.146:8086/health
  # Expected: {"status":"healthy","message":"Application is running"...}
  ```

- [ ] **All Services Running**
  ```bash
  docker compose -f docker-compose.prod.yml ps
  # Expected: All services showing "Up" and "healthy"
  ```

- [ ] **Job Scheduler Active**
  ```bash
  curl http://89.221.212.146:8086/api/v1/jobs/status/overview | python3 -m json.tool
  # Expected: "scheduler_running": true, "active_jobs": 2
  ```

- [ ] **Database Contains Data**
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U riot_api_user -d riot_api_db -c "
  SELECT COUNT(*) FROM job_configurations;
  SELECT COUNT(*) FROM players WHERE is_tracked = true;
  "
  # Expected: 2 job configs, at least 1 tracked player
  ```

- [ ] **No Errors in Logs**
  ```bash
  docker compose -f docker-compose.prod.yml logs backend --tail=100 | grep -i error
  # Expected: No critical errors (some warnings OK)
  ```

- [ ] **Frontend Accessible**
  ```bash
  curl -I http://89.221.212.146:8088
  # Expected: HTTP/1.1 200 OK
  ```

---

## Rollback Procedure

If deployment fails, follow these steps to rollback:

### 1. Identify Last Working Commit

```bash
git log --oneline -10
```

### 2. Revert to Previous Version

```bash
# On production server
cd riot-api
git checkout <previous-commit-hash>

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Restore Database (if needed)

If database backup exists:

```bash
# Restore from backup
docker compose -f docker-compose.prod.yml exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql
```

If no backup, reset and reseed:

```bash
docker compose -f docker-compose.prod.yml exec backend uv run python -m app.init_db reset
./scripts/seed-job-configs.sh
./scripts/seed-dev-data.sh
docker compose -f docker-compose.prod.yml restart backend
```

### 4. Verify Rollback

Run through [Verification Steps](#verification-steps) to ensure system is stable.

---

## Best Practices

### Before Deployment

1. **Test Locally**
   - Run all tests: `docker compose exec backend uv run pytest`
   - Test transaction boundaries
   - Verify schema changes work correctly

2. **Review Changes**
   - Check for schema modifications
   - Identify dependencies between changes
   - Plan deployment order

3. **Backup Database** (Production)
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres pg_dump -U riot_api_user riot_api_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

### During Deployment

1. **Monitor Logs**
   ```bash
   docker compose -f docker-compose.prod.yml logs -f backend
   ```

2. **Check Job Execution**
   - Watch for job start/completion messages
   - Verify no transaction errors
   - Monitor API request counts

3. **Test Critical Paths**
   - Search for player
   - View match history
   - Check smurf detection results

### After Deployment

1. **Monitor for 10-15 Minutes**
   - Watch for errors in logs
   - Verify jobs run successfully
   - Check API response times

2. **Update Documentation**
   - Document any issues encountered
   - Update this guide with solutions
   - Note any manual steps required

---

## Database Maintenance

### Reset Database (Development/Testing)

```bash
# WARNING: This deletes all data!
docker compose -f docker-compose.prod.yml exec backend uv run python -m app.init_db reset
```

### Create Database Backup

```bash
# Full database backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U riot_api_user riot_api_db > backup.sql

# Compressed backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U riot_api_user riot_api_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database Backup

```bash
# From SQL file
docker compose -f docker-compose.prod.yml exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql

# From compressed backup
gunzip -c backup.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U riot_api_user -d riot_api_db
```

---

## Emergency Contacts

- **Primary Developer**: Check project README
- **Server Administrator**: Check infrastructure documentation
- **GitHub Actions Issues**: Check `.github/workflows/` for configuration

---

## Deployment History

Document major deployments here:

| Date | Changes | Issues | Resolution |
|------|---------|--------|------------|
| 2025-10-13 | Fixed transaction management in tracked_player_updater | Foreign key violations after schema reset | Added setup-production.sh script, documented proper deployment order |

---

## Additional Resources

- [Backend Documentation](../backend/CLAUDE.md)
- [Frontend Documentation](../frontend/CLAUDE.md)
- [Docker Documentation](../docker/CLAUDE.md)
- [Database Documentation](../docker/postgres/CLAUDE.md)
- [Project README](../README.md)

---

## Quick Reference

```bash
# Deploy code only
git push origin main

# Deploy with schema changes
git push origin main
ssh -l pi 89.221.212.146 -p 2221
cd riot-api
./scripts/setup-production.sh

# Check status
curl http://89.221.212.146:8086/health
curl http://89.221.212.146:8086/api/v1/jobs/status/overview

# View logs
docker compose -f docker-compose.prod.yml logs backend --tail=50

# Emergency: Restart all services
docker compose -f docker-compose.prod.yml restart
```

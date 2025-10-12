# Database Operations Guide

Agent-specific database commands. See root `README.md` for project context.

## Schema Overview

### Core Tables
- **players** - PUUID-based player identification (primary key: PUUID)
- **matches** - Match details and game info (primary key: match_id)
- **participants** - Player performance in matches (links players to matches)
- **ranks** - Historical rank progression (tracks tier, division, LP)
- **smurf_detection** - Detection results and confidence scores

### Relationships
- Players → Participants (one-to-many)
- Matches → Participants (one-to-many)
- Players → Ranks (one-to-many)
- Players → Smurf Detection (one-to-many)

## Database Access

### Interactive Shell
```bash
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# Common psql commands
\dt                         # List all tables
\d players                  # Describe players table
\d+ participants            # Detailed table info
SELECT COUNT(*) FROM players;
```

### Quick Queries
```bash
# Total player count
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT COUNT(*) FROM players;"

# Recent matches
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT match_id, game_creation FROM matches ORDER BY game_creation DESC LIMIT 10;"
```

## Migrations

Migrations use **Alembic** (run via backend service):

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "Add new_column to players"

# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# View current version
docker compose exec backend alembic current

# View history
docker compose exec backend alembic history
```

See `backend/CLAUDE.md` for backend-specific details.

## Backup & Restore

### Using pg_dump
```bash
# Backup to SQL file
docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql

# Restore from SQL file
docker compose exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql

# Backup with compression
docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db | gzip > backup.sql.gz

# Restore from compressed backup
gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U riot_api_user -d riot_api_db
```

### Using Docker Volumes
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
```

See `docker/CLAUDE.md` for volume management.

## Performance Analysis

### Query Performance
```bash
# Access psql
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# Analyze query with EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM players WHERE region = 'eune' LIMIT 10;
```

### Database Size
```bash
# Total database size
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT pg_size_pretty(pg_database_size('riot_api_db'));"

# Individual table sizes
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Connection Stats
```bash
# Active connections count
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Detailed connection info
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT pid, usename, application_name, state, query_start
   FROM pg_stat_activity
   WHERE datname = 'riot_api_db';"
```

## Database Initialization

Initialization happens automatically on first startup:
1. `/docker/postgres/init.sql` runs (creates DB and user)
2. Backend starts and Alembic runs migrations (creates tables)

### Re-initialize Database
```bash
# WARNING: Destroys all data
docker compose down -v && docker compose up --build
```

### Seed Test Data
```bash
# Seed test player (Jim Morioriarty#2434 from EUNE, Level 794)
./scripts/seed-dev-data.sh
```

Can be run multiple times safely.

## Troubleshooting

### Common Issues
- **Connection timeouts**: Check pool settings, increase timeout
- **Slow queries**: Use `EXPLAIN ANALYZE`, add indexes
- **Migration failures**: Check Alembic logs, verify model/DB sync
- **Disk space**: Monitor database size growth
- **Too many connections**: Check for connection leaks

### Debug Commands
```bash
# Check PostgreSQL logs
docker compose logs postgres --tail=100

# Test connection from backend
docker compose exec backend python -c "from app.database import engine; print(engine.connect())"

# Verify migrations
docker compose exec backend alembic current
docker compose exec backend alembic history
```

### Reset Database
```bash
# Complete reset (WARNING: deletes all data)
docker compose down -v
docker compose up --build

# Reset just database volume
docker volume rm ${COMPOSE_PROJECT_NAME}_postgres-data
docker compose up postgres
```

## Indexing Strategy
- Primary keys: Auto-indexed
- Foreign keys: Indexed for efficient JOINs
- Composite indexes: For multi-column queries
- Partial indexes: For filtered queries

Use `EXPLAIN ANALYZE` to identify missing indexes.

## Security Notes
- Credentials in environment variables (never in code)
- Database user has limited permissions
- Enable SSL in production
- SQLAlchemy prevents SQL injection (parameterized queries)
- Network isolation (internal Docker network only)

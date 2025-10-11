# Database Guide

## Schema Overview

### Core Tables

- **`players`** - PUUID-based player identification and metadata
  - Primary key: PUUID (string)
  - Stores Riot ID, summoner name, account level, region
- **`matches`** - Match details and game information
  - Primary key: match_id
  - Stores game mode, duration, patch, creation time
- **`participants`** - Individual player performance in matches
  - Links players to matches with performance stats
  - Stores champion, KDA, CS, gold, damage, vision score
- **`ranks`** - Historical player rank and tier information
  - Tracks rank progression over time
  - Stores tier, division, LP, wins, losses
- **`smurf_detection`** - Smurf detection results and confidence scores
  - Historical detection results per player
  - Stores confidence score, detection factors, timestamp

### Entity Relationships

- **Players → Participants** (one-to-many): One player has many match participations
- **Matches → Participants** (one-to-many): One match has many participants
- **Players → Ranks** (one-to-many): Historical rank tracking
- **Players → Smurf Detection** (one-to-many): Historical detection results

### Design Principles

- **Third normal form** for data consistency
- **Foreign keys** enforce referential integrity
- **Composite indexes** optimize common query patterns
- **PUUID storage** as strings (no uuid-ossp extension needed)

## Database Initialization

### Setup Process

Database initialization happens automatically on first startup:

1. **`/docker/postgres/init.sql`** runs (mounted in docker-compose.yml)
   - Creates database and user
   - Sets up permissions
   - Does NOT create tables
2. **Backend starts** and Alembic automatically runs migrations
   - Creates all tables and indexes
   - Applies any pending schema changes

### Re-initialization

```bash
# WARNING: Destroys all data
docker compose down -v && docker compose up --build
```

### Development Test Data

```bash
# Seed test player data (Jim Morioriarty#2434 from EUNE, Level 794)
./scripts/seed-dev-data.sh
```

Can be run multiple times safely. Uses on-demand API calls instead of static SQL files.

## Database Migrations

Migrations managed by **Alembic** (Python migration tool) in the backend service.

### Common Migration Commands

```bash
# Create new migration after model changes
docker compose exec backend alembic revision --autogenerate -m "Add new_column to players"

# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# View current migration version
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history
```

See `backend/CLAUDE.md` for more backend-specific details.

## Database Access

### Interactive Shell

```bash
# Access PostgreSQL shell
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# Example queries in psql
\dt                    # List all tables
\d players             # Describe players table
SELECT COUNT(*) FROM players;
```

### Backup & Restore

```bash
# Backup database to SQL file
docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql

# Restore from SQL file
docker compose exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql

# Backup with compression
docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db | gzip > backup.sql.gz

# Restore from compressed backup
gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U riot_api_user -d riot_api_db
```

See `docker/CLAUDE.md` for volume-based backup strategies.

## Performance Optimization

### Indexing Strategy

- **Primary keys**: Auto-indexed for fast lookups
- **Foreign keys**: Indexed for efficient JOINs
- **Composite indexes**: For common multi-column queries
- **Partial indexes**: For filtered queries (e.g., WHERE smurf_detected = true)

### Query Optimization

```bash
# Analyze query performance
docker compose exec postgres psql -U riot_api_user -d riot_api_db

# In psql, use EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM players WHERE region = 'eune' LIMIT 10;
```

**Best practices:**
- Use `EXPLAIN ANALYZE` for slow queries
- Optimize JOIN operations (ensure proper indexes)
- Avoid `SELECT *` in production queries
- Implement pagination for large result sets
- Monitor slow query logs

### Connection Pooling

- SQLAlchemy handles connection pooling in backend
- Default pool size configured in backend settings
- Monitor active connections to prevent exhaustion

```bash
# Check active connections
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## Monitoring & Diagnostics

### Database Size

```bash
# Check total database size
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT pg_size_pretty(pg_database_size('riot_api_db'));"

# Check individual table sizes
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Connection Statistics

```bash
# Check active connections
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Detailed connection info
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT pid, usename, application_name, state, query_start
   FROM pg_stat_activity
   WHERE datname = 'riot_api_db';"
```

### Slow Query Analysis

Enable slow query logging in production:

```sql
-- Set in psql
ALTER DATABASE riot_api_db SET log_min_duration_statement = 1000; -- Log queries > 1s
```

## Security Best Practices

- **Credentials**: Stored in environment variables (never in code)
- **User permissions**: Database user has limited permissions (defined in `init.sql`)
- **SSL/TLS**: Enable SSL connections in production
- **Parameterized queries**: SQLAlchemy prevents SQL injection by default
- **Regular updates**: Keep PostgreSQL version updated for security patches
- **Network isolation**: Database not exposed externally (internal Docker network only)

## Troubleshooting

### Common Issues

1. **Connection timeouts**: Check connection pool settings, increase timeout values
2. **Slow queries**: Use `EXPLAIN ANALYZE` and add appropriate indexes
3. **Migration failures**: Check Alembic logs, ensure models match database state
4. **Disk space**: Monitor database size growth, implement data retention policies
5. **Too many connections**: Increase `max_connections` in PostgreSQL config or fix connection leaks

### Debug Steps

```bash
# Check PostgreSQL logs
docker compose logs postgres --tail=100

# Test database connection
docker compose exec backend python -c "from app.database import engine; print(engine.connect())"

# Verify migrations
docker compose exec backend alembic current
docker compose exec backend alembic history
```

### Reset and Rebuild

```bash
# Complete reset (WARNING: deletes all data)
docker compose down -v
docker compose up --build

# Reset without losing code/configs (just database)
docker volume rm riot-api-project_postgres_data
docker compose up postgres
```

# Database Operations Guide

Database schema, queries, and performance tuning. **See root `AGENTS.md` for common database commands.**

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

## Common psql Commands

```sql
-- Table inspection
\dt                              -- List all tables
\d players                       -- Describe table structure
\d+ participants                 -- Detailed table info with indexes
\di                              -- List all indexes
\df                              -- List functions

-- Data inspection
SELECT COUNT(*) FROM players;
SELECT * FROM players LIMIT 10;
SELECT match_id, game_creation FROM matches ORDER BY game_creation DESC LIMIT 10;

-- Schema info
\l                               -- List databases
\dn                              -- List schemas
\du                              -- List users/roles
```

## Useful Queries

### Player Statistics
```sql
-- Players by region
SELECT region, COUNT(*)
FROM players
GROUP BY region
ORDER BY COUNT(*) DESC;

-- High-level players
SELECT summoner_name, account_level, region
FROM players
WHERE account_level > 500
ORDER BY account_level DESC;
```

### Match Analysis
```sql
-- Recent matches with participant count
SELECT m.match_id, m.game_creation, m.game_duration, COUNT(p.puuid) as players
FROM matches m
LEFT JOIN participants p ON m.match_id = p.match_id
GROUP BY m.match_id
ORDER BY m.game_creation DESC
LIMIT 20;

-- Win rate by champion
SELECT champion_name,
       COUNT(*) as games_played,
       SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
       ROUND(100.0 * SUM(CASE WHEN win THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM participants
GROUP BY champion_name
HAVING COUNT(*) >= 10
ORDER BY win_rate DESC;
```

### Smurf Detection
```sql
-- Players with smurf detections
SELECT p.summoner_name, p.account_level, sd.confidence_score, sd.detection_method
FROM players p
JOIN smurf_detection sd ON p.puuid = sd.puuid
WHERE sd.is_smurf = true
ORDER BY sd.confidence_score DESC;
```

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

### Automated Backup Script
```bash
#!/bin/bash
# backup-db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${TIMESTAMP}.sql.gz"

docker compose exec postgres pg_dump -U riot_api_user -d riot_api_db | gzip > "$BACKUP_FILE"
echo "Backup saved to $BACKUP_FILE"

# Keep only last 7 backups
ls -t backup_*.sql.gz | tail -n +8 | xargs rm -f
```

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

## Indexing Strategy

### Existing Indexes
```sql
-- Primary keys (auto-indexed)
players(puuid)
matches(match_id)
participants(id)

-- Foreign keys (should be indexed)
participants(puuid) → players(puuid)
participants(match_id) → matches(match_id)
ranks(puuid) → players(puuid)
smurf_detection(puuid) → players(puuid)
```

### Adding Custom Indexes
```sql
-- For frequent queries by region
CREATE INDEX idx_players_region ON players(region);

-- For match history queries
CREATE INDEX idx_participants_puuid_match ON participants(puuid, match_id);

-- For time-based queries
CREATE INDEX idx_matches_game_creation ON matches(game_creation DESC);

-- For win rate calculations
CREATE INDEX idx_participants_champion_win ON participants(champion_name, win);
```

### Index Maintenance
```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Rebuild indexes (if needed)
REINDEX TABLE players;
REINDEX DATABASE riot_api_db;  -- Use with caution

-- Analyze tables for query planner
ANALYZE players;
ANALYZE matches;
ANALYZE participants;
```

## Troubleshooting

**Connection timeouts:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'riot_api_db';

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'riot_api_db'
AND state = 'idle'
AND query_start < NOW() - INTERVAL '5 minutes';
```

**Slow queries:**
```sql
-- Find slow queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
AND now() - query_start > INTERVAL '1 minute';

-- Enable query logging (PostgreSQL config)
ALTER DATABASE riot_api_db SET log_min_duration_statement = 1000;  -- Log queries > 1s
```

**Disk space:**
```bash
# Check database size
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "SELECT pg_size_pretty(pg_database_size('riot_api_db'));"

# Check table bloat and vacuum
docker compose exec postgres psql -U riot_api_user -d riot_api_db -c \
  "VACUUM ANALYZE;"
```

**Connection pool exhaustion:**
```python
# Check SQLAlchemy pool settings in backend
# app/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,          # Max connections
    max_overflow=20,       # Extra connections when pool is full
    pool_timeout=30,       # Seconds to wait for connection
    pool_pre_ping=True,    # Verify connections before use
)
```

## Security Best Practices
- ✅ Credentials in environment variables only
- ✅ Database user has limited permissions (no DROP DATABASE)
- ✅ Network isolation (internal Docker network)
- ✅ SQLAlchemy uses parameterized queries (prevents SQL injection)
- 🔒 Enable SSL/TLS in production
- 🔒 Regular backups (automated script above)
- 🔒 Row-level security for multi-tenant scenarios (if needed)

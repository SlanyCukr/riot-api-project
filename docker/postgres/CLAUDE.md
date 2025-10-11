# Database Guide

## Database Schema

### Core Tables
- `players`: PUUID-based player identification and metadata
- `matches`: Match details and game information
- `participants`: Individual player performance in matches
- `ranks`: Player rank and tier information
- `smurf_detection`: Smurf detection results and confidence scores

### Relationships
- Players → Participants (one-to-many)
- Matches → Participants (one-to-many)
- Players → Ranks (one-to-many, historical)
- Players → Smurf Detection (one-to-many, historical)

## Database Initialization

Database initialized via `/docker/postgres/init.sql` (mounted in docker-compose.yml):
- Creates `app` schema and user permissions
- Does NOT create tables (handled by Alembic migrations)
- PUUIDs stored as strings (no uuid-ossp extension needed)

### Execution Order
1. `init.sql` runs → creates database infrastructure
2. Backend starts → Alembic creates tables

**To re-initialize:** `docker-compose down -v && docker-compose up`

### Development Data
```bash
# Seed test data (Jim Morioriarty#2434 from EUNE, Level 794)
./scripts/seed-dev-data.sh
```

Can be run multiple times safely. On-demand seeding is easier than SQL files.

## Database Operations

### Migrations
```bash
# Create/apply migrations
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic current
```

### Database Access
```bash
# Database shell
docker-compose exec postgres psql -U riot_api_user -d riot_api_db

# Backup/restore
docker-compose exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql
docker-compose exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql
```

## Schema Design

### Design Principles
- Third normal form where practical
- Foreign keys for referential integrity
- Connection pooling with SQLAlchemy
- Proper indexing strategy

### Indexing
- Primary keys auto-indexed
- Foreign keys indexed
- Composite indexes for common query patterns
- Partial indexes for filtered queries

## Performance

### Connection Management
- SQLAlchemy connection pooling
- Configured pool size and timeouts
- Monitor connection usage

### Query Optimization
- Use EXPLAIN ANALYZE for slow queries
- Optimize JOIN operations
- Avoid SELECT * in production
- Implement proper pagination

## Security

- Environment variables for credentials
- Proper user roles and permissions
- SSL connections in production
- Parameterized queries to prevent SQL injection
- Regular security updates

## Monitoring

### Debug Commands
```bash
# Check database size
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT pg_size_pretty(pg_database_size('riot_api_db'));"

# Check table sizes
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Check active connections
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## Troubleshooting

Common issues: connection timeouts, slow queries, migration failures, disk space.

Use EXPLAIN ANALYZE for query optimization and monitor database size growth.

# Database Guide

This file provides guidance for working with the PostgreSQL database and schema.

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

### Init SQL Script
The database is initialized using `/docker/postgres/init.sql` (mounted in docker-compose.yml):

- Sets up database infrastructure (schemas, permissions, privileges)
- Creates `app` schema
- Configures user permissions and search paths
- **Note**: Does NOT create tables - tables are created by Alembic migrations
- **Note**: Does not use `uuid-ossp` extension - not needed since PUUIDs are stored as strings

### Execution Order
When PostgreSQL container starts for the first time:
1. `init.sql` runs → creates database infrastructure
2. Backend starts → Alembic creates all tables

**Important**: Init scripts only run on first container creation. To re-run:
```bash
docker-compose down -v  # Remove volume
docker-compose up       # Fresh database
```

### Development Seed Data
For development and testing, use the seed script instead of SQL files:

```bash
# Seed test player data into the database
./scripts/seed-dev-data.sh
```

This script inserts a real test player (Jim Morioriarty#2434 from EUNE, Level 794) into the database. The script can be run multiple times safely (uses `ON CONFLICT DO UPDATE`).

**Benefits over SQL files**:
- No need to modify docker-compose.yml
- Can be run on-demand, anytime after migrations
- Easier to maintain and extend
- Clear separation from initialization logic

## Database Operations (via Docker)

### Migrations
```bash
# Create database migrations
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migrations
docker-compose exec backend alembic downgrade -1

# View migration history
docker-compose exec backend alembic history

# Check current revision
docker-compose exec backend alembic current
```

### Database Shell
```bash
# Database shell
docker-compose exec postgres psql -U riot_api_user -d riot_api_db

# Alternative connection
docker-compose exec postgres psql -h localhost -U riot_api_user -d riot_api_db
```

### Backup and Restore
```bash
# Create backup
docker-compose exec postgres pg_dump -U riot_api_user -d riot_api_db > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U riot_api_user -d riot_api_db < backup.sql

# Copy backup out of container
docker cp postgres_container:/backup.sql ./backup.sql
```

## Schema Design Principles

### Normalization
- Follow third normal form where practical
- Use foreign keys for referential integrity
- Implement proper indexing strategy

### Performance Considerations
- Connection pooling with SQLAlchemy
- Proper indexing on frequently queried fields
- Read replicas for scaling (future enhancement)
- Query optimization for large datasets

### Indexing Strategy
- Primary keys automatically indexed
- Foreign keys should be indexed
- Composite indexes for common query patterns
- Partial indexes for filtered queries

## Database Optimization

### Connection Management
- Use SQLAlchemy connection pooling
- Configure appropriate pool size
- Implement connection timeout handling
- Monitor connection usage

### Query Optimization
- Use EXPLAIN ANALYZE for slow queries
- Optimize JOIN operations
- Avoid SELECT * in production
- Implement proper pagination

### Monitoring
- Monitor query performance
- Track database size growth
- Monitor connection pool usage
- Set up alerts for unusual activity

## Security Considerations

### Access Control
- Use environment variables for credentials
- Implement proper user roles and permissions
- Never commit database credentials to version control
- Use SSL connections in production

### Data Protection
- Encrypt sensitive data at rest
- Implement proper backup strategy
- Use parameterized queries to prevent SQL injection
- Sanitize all user inputs

### Best Practices
- Regular database maintenance
- Implement proper backup strategy
- Monitor database performance
- Keep software up to date

## Development Environment

### Local Development
- Database runs in Docker container
- Volume mounted for data persistence
- Environment variables for configuration
- Health checks for container monitoring

### Testing Database
- Separate test database for unit tests
- Test data cleanup between runs
- Mock database for integration tests
- Database migrations included in CI/CD

## Troubleshooting

### Common Issues
- Connection timeouts: Check pool configuration
- Slow queries: Use EXPLAIN ANALYZE
- Migration failures: Check migration scripts
- Disk space: Monitor database size

### Debug Commands
```bash
# Check database size
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT pg_size_pretty(pg_database_size('riot_api_db'));"

# Check table sizes
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Check active connections
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries
docker-compose exec postgres psql -U riot_api_user -d riot_api_db -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```
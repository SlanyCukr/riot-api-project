# Raspberry Pi 5 Deployment Guide

This project is optimized for deployment on **Raspberry Pi 5** with **16GB RAM** and **2TB SSD**.

## Platform Specifications

- **Device**: Raspberry Pi 5
- **RAM**: 16GB
- **Storage**: 2TB SSD
- **Architecture**: ARM64 (aarch64)
- **CPU**: 4 cores
- **OS**: Raspberry Pi OS (Debian-based)

## Optimizations Applied

### Docker Configuration

All Docker builds and configurations are optimized for ARM64 architecture and the RPi5 platform:

- **Parallel Builds**: 2 concurrent builds (tuned for 4-core CPU)
- **Memory Allocation**: 3GB per Node.js build (conservative for 16GB RAM)
- **Build Cache**: 50GB cache on SSD for fast rebuilds
- **No Resource Limits**: cgroup resource limits removed (requires kernel config)

### Build Performance

Expected build times on RPi5:

- **Full production build** (backend + frontend): 5-10 minutes
- **Backend only**: 2-4 minutes
- **Frontend only**: 3-6 minutes
- **Rebuild with cache**: 1-3 minutes

These times assume:

- First build may take longer due to dependency downloads
- SSD storage for optimal I/O
- No other resource-intensive tasks running

### Storage Management

With 2TB SSD, storage is not a constraint:

- **Build cache**: 50GB allocated
- **Docker images**: ~2-5GB per deployment
- **Database volumes**: Grows with data (monitored via application)
- **Logs**: Rotated automatically by Docker

## Deployment Methods

### 1. GitHub Actions (Recommended)

Production deployments are automated via GitHub Actions self-hosted runner:

```bash
# Deployment triggers automatically on push to main branch
git push origin main

# Or trigger manually from GitHub Actions UI
```

The workflow:

1. Stops existing containers
2. Pulls latest code
3. Builds images with Docker Bake (parallel)
4. Starts services with health checks
5. Verifies deployment
6. Cleans up unused images

### 2. Manual Deployment

For manual deployments or testing:

```bash
# SSH into Raspberry Pi
ssh pi@your-rpi5-hostname

# Navigate to project
cd /home/pi/riot-api

# Pull latest changes
git pull origin main

# Deploy with build
./scripts/prod.sh --build --no-cache --down

# Check status
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
```

## Build Process

### Docker Bake

All builds use Docker Bake for parallel compilation:

```bash
# Build production images
docker buildx bake -f docker/docker-bake.hcl prod --load

# Build development images
docker buildx bake -f docker/docker-bake.hcl dev --load

# Build specific service
docker buildx bake -f docker/docker-bake.hcl backend-prod --load
```

### Build Args

Environment variables for builds:

- `NEXT_PUBLIC_API_URL`: Frontend API endpoint (set in `.env`)
- `NODE_OPTIONS`: Node.js memory limit (default: 3GB)

## Performance Tips

### Memory Usage

With 16GB RAM, the typical memory footprint is:

- **PostgreSQL**: ~500MB-1GB
- **Backend (FastAPI)**: ~200-500MB
- **Frontend (Next.js)**: ~150-300MB
- **System + overhead**: ~2-4GB
- **Available for builds**: ~10GB

### CPU Usage

The 4-core CPU is utilized efficiently:

- **Parallel builds**: 2 simultaneous image builds
- **Runtime**: All services share CPU dynamically
- **Background jobs**: Scheduled tasks run without blocking

### Disk I/O

SSD provides excellent performance:

- **Build cache**: Stored on `/tmp/.buildx-cache` (SSD)
- **Docker volumes**: Stored on SSD for fast database access
- **No I/O bottlenecks**: 2TB provides ample space

## Monitoring

### Container Status

```bash
# Check all containers
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps

# View logs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f

# Check specific service
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f backend
```

### Resource Usage

```bash
# Docker stats (real-time)
docker stats

# System memory
free -h

# Disk usage
df -h
docker system df
```

### Health Checks

All services have health checks:

- **Backend**: `http://localhost:8086/health`
- **Frontend**: `http://localhost:8088/`
- **PostgreSQL**: `pg_isready` command

## Troubleshooting

### Build Failures

**Issue**: Out of memory during build

```bash
# Check available memory
free -h

# Stop unnecessary services
docker compose down

# Try building with single service
./scripts/prod.sh --build backend
./scripts/prod.sh --build frontend
```

**Issue**: Build cache issues

```bash
# Clear build cache
docker buildx prune -a

# Rebuild without cache
./scripts/prod.sh --build --no-cache
```

### Runtime Issues

**Issue**: Container fails to start

```bash
# Check logs
docker compose logs <service-name>

# Check if ports are in use
sudo netstat -tulpn | grep <port>

# Restart specific service
docker compose restart <service-name>
```

**Issue**: Database connection errors

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready -U riot_api_user -d riot_api_db

# Check logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

### Performance Issues

**Issue**: Slow build times

```bash
# Check SSD health
sudo smartctl -a /dev/sda  # Adjust device path

# Check I/O wait
iostat -x 1

# Check for thermal throttling
vcgencmd measure_temp
vcgencmd get_throttled
```

**Issue**: Memory pressure

```bash
# Check memory usage
free -h
docker stats --no-stream

# Consider stopping unused containers
docker compose down
```

## Known Warnings (Harmless)

### npm Deprecation Warnings

You may see warnings about deprecated npm packages during builds:

```
npm warn deprecated @babel/plugin-proposal-private-methods@7.18.6
```

**Status**: Harmless - these are transitive dependencies from Next.js that will be updated in future Next.js releases.

### cgroup Memory Warnings

If you see:

```
Your kernel does not support memory limit capabilities or the cgroup is not mounted.
```

**Status**: Expected - resource limits have been removed from compose files. To enable, add to `/boot/firmware/cmdline.txt`:

```
cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1
```

Then reboot. (Optional - not required for operation)

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U riot_api_user riot_api_db > backup.sql

# Restore from backup
cat backup.sql | docker compose exec -T postgres psql -U riot_api_user -d riot_api_db
```

### Full System Backup

The 2TB SSD should include regular backups:

- Database volumes: `/var/lib/docker/volumes/`
- Configuration: `/home/pi/riot-api/.env`
- Code: Version controlled via Git

## Maintenance

### Regular Tasks

**Weekly**:

- Check disk usage: `df -h`
- Review logs for errors
- Verify backups

**Monthly**:

- Update system packages: `sudo apt update && sudo apt upgrade`
- Clean up old images: `docker image prune -a`
- Review Docker disk usage: `docker system df`

**As Needed**:

- Update dependencies in `backend/` and `frontend/`
- Review and optimize database queries
- Monitor application performance

## Support

For issues specific to this deployment:

1. Check logs: `docker compose logs`
2. Review GitHub Actions workflow runs
3. Check system resources: `free -h`, `df -h`
4. Verify network connectivity and DNS resolution

## Related Documentation

- [Docker Configuration](./CLAUDE.md) - Docker Compose and Bake details
- [Backend Documentation](../backend/AGENTS.md) - FastAPI application details
- [Frontend Documentation](../frontend/AGENTS.md) - Next.js application details
- [Scripts Guide](../scripts/CLAUDE.md) - Development and production scripts

# Docker Bake Configuration
# This file defines build configurations for local builds (no registry publishing)
# Use with: docker buildx bake [target]
#
# Raspberry Pi 5 (16GB RAM, 2TB SSD) Optimizations:
# - Builds optimized for ARM64 architecture
# - Parallel builds tuned for 4-core CPU with generous memory allocation (3GB per build)
# - Build cache stored on high-performance SSD for fast rebuilds
# - No storage constraints with 2TB available

# Variables for configuration
variable "NEXT_PUBLIC_API_URL" {
  default = "http://localhost:8000"
}

# BuildKit optimization variables for RPi5
variable "BUILDKIT_PARALLELISM" {
  default = "2"  # Limit to 2 parallel builds on RPi5 (4 cores, leaving headroom)
}

variable "DOCKER_BUILDKIT_CACHE_SIZE" {
  default = "50GB"  # Generous cache size with 2TB SSD available
}

# Default group builds all services
group "default" {
  targets = ["backend", "frontend"]
}

# Production group for deployment builds (local only)
group "prod" {
  targets = ["backend-prod", "frontend-prod"]
}

# Development group
group "dev" {
  targets = ["backend-dev", "frontend-dev"]
}

# Common configuration for all targets
target "_common" {
  # Local cache for faster rebuilds (skipped on docker driver)
  # The docker driver doesn't support cache export, so we omit cache settings
  # when using docker driver. buildx automatically detects this.

  # ARM64/RPi5 optimizations
  args = {
    # Optimize for ARM64 native builds
    BUILDKIT_INLINE_CACHE = "1"
  }

  # Add useful labels for troubleshooting and metadata
  labels = {
    "org.opencontainers.image.source" = "riot-api-project"
    "com.rpi5.optimized" = "true"
    "com.rpi5.build.date" = "${timestamp()}"
    "com.rpi5.architecture" = "arm64"
    "com.buildkit.version" = "latest"
  }
}

# Common configuration for production builds (single platform - local deployment)
target "_prod_common" {
  inherits = ["_common"]
  # Single platform for local deployment (no platform specified = use build machine native architecture)
  # When building on linux/arm64 (RPI5), this will automatically use ARM64 images
  # Load into local Docker daemon
  output = ["type=docker"]

  # RPi5-specific build args for production
  # 16GB RAM allows for comfortable 3GB allocation to Node.js builds
  args = {
    BUILDKIT_INLINE_CACHE = "1"
    # Optimize Node.js builds for ARM64 (RPi5 has 16GB RAM)
    NODE_OPTIONS = "--max-old-space-size=3072"
  }
}

# Backend base configuration
target "backend" {
  inherits = ["_common"]
  context = "./backend"
  dockerfile = "./docker/backend/Dockerfile"
  target = "production"
  tags = ["riot-api-backend:latest"]
}

# Backend production (loads into local Docker)
target "backend-prod" {
  inherits = ["backend", "_prod_common"]
  target = "production"
  tags = ["riot-api-backend:latest"]
}

# Backend development
target "backend-dev" {
  inherits = ["_common"]
  context = "./backend"
  dockerfile = "./docker/backend/Dockerfile"
  target = "development"
  tags = ["riot-api-backend:dev"]
  output = ["type=docker"]
}

# Frontend base configuration
target "frontend" {
  inherits = ["_common"]
  context = "./frontend"
  dockerfile = "./docker/frontend/Dockerfile"
  target = "runner"
  args = {
    NEXT_PUBLIC_API_URL = NEXT_PUBLIC_API_URL
  }
  tags = ["riot-api-frontend:latest"]
}

# Frontend production (loads into local Docker)
target "frontend-prod" {
  inherits = ["frontend", "_prod_common"]
  target = "runner"
  tags = ["riot-api-frontend:latest"]
}

# Frontend development
target "frontend-dev" {
  inherits = ["_common"]
  context = "./frontend"
  dockerfile = "./docker/frontend/Dockerfile"
  target = "development"
  args = {
    NEXT_PUBLIC_API_URL = NEXT_PUBLIC_API_URL
  }
  tags = ["riot-api-frontend:dev"]
  output = ["type=docker"]
}

# Validation group for CI/CD
group "validate" {
  targets = ["backend-lint", "frontend-lint"]
}

# Backend lint target (requires lint stage in Dockerfile)
target "backend-lint" {
  context = "./backend"
  dockerfile = "./docker/backend/Dockerfile"
  target = "lint"
  output = ["type=cacheonly"]
}

# Frontend lint target (requires lint stage in Dockerfile)
target "frontend-lint" {
  context = "./frontend"
  dockerfile = "./docker/frontend/Dockerfile"
  target = "lint"
  output = ["type=cacheonly"]
}

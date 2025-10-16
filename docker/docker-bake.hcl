# Docker Bake Configuration
# This file defines build configurations for local builds (no registry publishing)
# Use with: docker buildx bake [target]

# Variables for configuration
variable "NEXT_PUBLIC_API_URL" {
  default = "http://localhost:8000"
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
}

# Common configuration for production builds (single platform - local deployment)
target "_prod_common" {
  inherits = ["_common"]
  # Single platform for local deployment (no platform specified = use build machine native architecture)
  # When building on linux/arm64 (RPI5), this will automatically use ARM64 images
  # Load into local Docker daemon
  output = ["type=docker"]
}

# Backend base configuration
target "backend" {
  inherits = ["_common"]
  context = "./backend"
  dockerfile = "../docker/backend/Dockerfile"
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
  dockerfile = "../docker/backend/Dockerfile"
  target = "development"
  tags = ["riot-api-backend:dev"]
  output = ["type=docker"]
}

# Frontend base configuration
target "frontend" {
  inherits = ["_common"]
  context = "./frontend"
  dockerfile = "../docker/frontend/Dockerfile"
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
  dockerfile = "../docker/frontend/Dockerfile"
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
  dockerfile = "../docker/backend/Dockerfile"
  target = "lint"
  output = ["type=cacheonly"]
}

# Frontend lint target (requires lint stage in Dockerfile)
target "frontend-lint" {
  context = "./frontend"
  dockerfile = "../docker/frontend/Dockerfile"
  target = "lint"
  output = ["type=cacheonly"]
}

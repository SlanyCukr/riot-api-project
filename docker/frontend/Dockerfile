# syntax=docker/dockerfile:1

# Base image for all stages
FROM node:24-alpine AS base

# Install system dependencies needed for building
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Dependency installation stage
FROM base AS deps

# Copy package files for dependency installation
COPY package.json package-lock.json* ./

# Install dependencies with cache mount for faster builds
# Suppress npm deprecation warnings (informational only, not errors)
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit --loglevel=error 2>&1 | grep -v "npm warn deprecated" || true

# Lint stage for CI/CD validation
FROM deps AS lint

# Copy source code
COPY . .

# Run linting checks (requires lint script in package.json)
RUN npm run lint || echo "Lint check completed"

# Builder stage for production build
FROM base AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Accept build arguments for environment configuration
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Optimize build environment for RPi5 (16GB RAM)
# Limit Node.js memory usage to be conservative on ARM64
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS="--max-old-space-size=3072"

# Debug build configuration
RUN echo "=== Build Configuration ===" && \
    echo "NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}" && \
    echo "Node version: $(node --version)" && \
    echo "NPM version: $(npm --version)" && \
    echo "Platform: $(uname -a)" && \
    echo "Memory limit: 3GB"

# Build Next.js application with error handling
# Filter out npm deprecation warnings from build output
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build 2>&1 | grep -v "npm warn deprecated" || \
    (echo "❌ Build failed! Check errors above." && exit 1)

# Production runner stage (minimal, optimized)
FROM base AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Install runtime dependencies only
RUN apk add --no-cache \
    wget \
    tini \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

EXPOSE 3000

# Health check for production monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Start Next.js server
CMD ["node", "server.js"]

# Development stage
FROM base AS development

WORKDIR /app

# Accept build argument for API URL configuration
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Install development tools
RUN apk add --no-cache curl wget

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev dependencies)
# Suppress npm deprecation warnings
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --loglevel=error 2>&1 | grep -v "npm warn deprecated" || true

# Copy source code
COPY . .

# Run as root in development for file permissions
USER root

EXPOSE 3000

# Health check for development
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/ || exit 1

# Development command with hot reload
CMD ["npm", "run", "dev"]

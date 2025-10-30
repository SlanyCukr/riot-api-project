# Tech Stack

- **Next.js 16.0.0** with App Router + **React 19.2.0**
- **TypeScript 5** with strict mode
- **Tailwind CSS 4.1.14** with CSS-first configuration (@theme blocks)
- **shadcn/ui** components (New York style)
- **TanStack Query v5.90.2** for data fetching and caching
- **Zod v4.1.12** for runtime validation
- **react-hook-form v7.65.0** + @hookform/resolvers v5.2.2 for form handling
- **Axios v1.12.2** for HTTP client
- **next-themes v0.4.6** for dark mode support
- **sonner v2.0.7** for toast notifications
- **lucide-react v0.545.0** for icons

# Project Structure

```
frontend/
├── app/                        # Next.js App Router pages
│   ├── layout.tsx             # Root layout with providers
│   ├── page.tsx               # Home/dashboard
│   ├── globals.css            # Global styles + Tailwind CSS 4 @theme
│   ├── error.tsx              # Global error boundary
│   ├── loading.tsx            # Global loading state
│   ├── not-found.tsx          # 404 page
│   ├── player-analysis/       # Player analysis page
│   ├── matchmaking-analysis/  # Matchmaking analysis page
│   ├── jobs/                  # Background jobs page
│   ├── tracked-players/       # Player tracking page
│   ├── settings/              # System settings page
│   ├── sign-in/               # Authentication pages
│   ├── license/               # License page
│   └── privacy-policy/        # Privacy policy page
├── features/                   # Feature-based modules
│   ├── auth/                  # Authentication (AuthProvider, ProtectedRoute, useAuth)
│   ├── players/               # Player components (search, cards, stats)
│   ├── matches/               # Match components (history, encounters)
│   ├── player-analysis/       # Player analysis components
│   ├── matchmaking/           # Matchmaking analysis components
│   ├── jobs/                  # Job management components
│   └── settings/              # Settings components
├── components/
│   ├── ui/                    # shadcn/ui components (never edit manually)
│   ├── sidebar-nav.tsx        # Navigation sidebar
│   ├── theme-provider.tsx     # Theme context provider
│   ├── theme-toggle.tsx       # Dark mode toggle
│   ├── providers.tsx          # TanStack Query provider
│   └── loading-skeleton.tsx   # Loading states
├── lib/
│   ├── core/                  # Core utilities
│   │   ├── api.ts            # API client with Zod validation
│   │   ├── schemas.ts        # Zod schemas for API types
│   │   └── validations.ts    # Form validation schemas
│   └── utils.ts               # Generic utilities (cn helper)
├── hooks/
│   └── use-toast.ts           # Toast notifications
└── components.json            # shadcn/ui configuration
```

## Architectural Principles

### 1. Feature Organization

- **Feature modules** contain domain-specific UI, logic, and utilities
- **Shared components** are layout/infrastructure only
- **Pages** import from features and compose them

### 2. Component Placement Rules

- If component is used by ONE feature → `features/<feature>/components/`
- If component is shared layout/infrastructure → `components/`
- If component is shadcn/ui → `components/ui/` (never move)

### 3. Public Exports

Features expose clean public APIs via `index.ts`:

```typescript
// features/players/index.ts
export { PlayerSearch } from './components/player-search';
export { PlayerCard } from './components/player-card';
export { PlayerStats } from './components/player-stats';
```

## Feature Modules (`features/`)

Each feature contains components, hooks, and utilities specific to that domain:

**`features/auth/`** - Authentication

- `components/protected-route.tsx` - Route protection component
- `components/sign-in-form.tsx` - Login form with validation
- `context/auth-context.tsx` - Authentication state management
- `types.ts` - TypeScript type definitions
- `utils/token-manager.ts` - Token management utilities

**`features/players/`** - Player management

- `components/player-search.tsx` - Player search with autocomplete
- `components/player-card.tsx` - Player info display
- `components/player-stats.tsx` - Player statistics
- `components/add-tracked-player.tsx` - Add to tracking
- `components/tracked-players-list.tsx` - Tracked players table
- `components/track-player-button.tsx` - Track player button

**`features/matches/`** - Match data

- `components/match-history.tsx` - Match history table
- `components/encounter-stats.tsx` - Opponent encounter statistics
- `components/recent-opponents.tsx` - Recent opponents list

**`features/player-analysis/`** - Player analysis

- `components/player-analysis.tsx` - Player analysis results

**`features/matchmaking/`** - Matchmaking analysis

- `components/matchmaking-analysis.tsx` - Analysis input form
- `components/matchmaking-analysis-results.tsx` - Fairness results

**`features/jobs/`** - Background jobs

- `components/job-card.tsx` - Individual job display
- `components/job-executions.tsx` - Execution history
- `components/system-status.tsx` - System overview

**`features/settings/`** - System settings

- `components/` - Settings components

### Shared Components (`components/`)

Only shared/layout components (NOT feature-specific):

- `sidebar-nav.tsx` - Navigation sidebar
- `theme-provider.tsx` - Theme context provider
- `theme-toggle.tsx` - Dark mode toggle
- `providers.tsx` - TanStack Query provider
- `loading-skeleton.tsx` - Generic loading states
- `ui/` - **shadcn/ui primitives (DO NOT MOVE)**

### Core Utilities (`lib/core/`)

Shared infrastructure:

- `api.ts` - Axios API client configuration
- `schemas.ts` - Shared Zod schemas
- `validations.ts` - Validation utilities

### Generic Utilities (`lib/`)

- `utils.ts` - Generic utilities (cn(), formatters, etc.)

### Shared Hooks (`hooks/`)

- `use-toast.ts` - Toast notifications

## Architectural Principles

### 1. Feature Organization

- **Feature modules** contain domain-specific UI, logic, and utilities
- **Shared components** are layout/infrastructure only
- **Pages** import from features and compose them

### 2. Component Placement Rules

- If component is used by ONE feature → `features/<feature>/components/`
- If component is shared layout/infrastructure → `components/`
- If component is shadcn/ui → `components/ui/` (never move)

### 3. Public Exports

Features expose clean public APIs:

```typescript
// features/players/index.ts
export { PlayerSearch } from './components/player-search';
export { PlayerCard } from './components/player-card';
export { PlayerStats } from './components/player-stats';
export { AddTrackedPlayer } from './components/add-tracked-player';
export { TrackedPlayersList } from './components/tracked-players-list';
export { TrackPlayerButton } from './components/track-player-button';
```

## Import Patterns

### Importing from Features (Recommended)

```typescript
// Import from feature's public API via index.ts
import { PlayerSearch, PlayerCard } from '@/features/players';
import { ProtectedRoute, useAuth } from '@/features/auth';
import { MatchHistory } from '@/features/matches';
import { JobCard } from '@/features/jobs';
```

### Importing from Core

```typescript
import { api } from '@/lib/core/api';
import { playerSchema } from '@/lib/core/schemas';
import { cn } from '@/lib/utils';
```

### Importing Shared Components

```typescript
import { Button } from '@/components/ui/button';
import { SidebarNav } from '@/components/sidebar-nav';
import { LoadingSkeleton } from '@/components/loading-skeleton';
```

### Page Composition Example

```typescript
// app/player-analysis/page.tsx
import { PlayerSearch, PlayerStats } from '@/features/players'
import { PlayerAnalysisResults } from '@/features/player-analysis'
import { LoadingSkeleton } from '@/components/loading-skeleton'

export default function PlayerAnalysisPage() {
  return (
    <div className="space-y-8">
      <PlayerSearch />
      <PlayerAnalysisResults />
    </div>
  )
}
```

# Commands

- `npm run dev` - Start dev server with hot reload
- `npm run build` - Type-check, lint, and build
- `npm run start` - Start production server
- `rm -rf .next` - Clear build cache

# Code Style

- Use TypeScript strict mode (no `any`)
- kebab-case for files, PascalCase for components
- `"use client"` for hooks/events/browser APIs
- Follow shadcn/ui patterns, never create custom UI primitives
- Use TanStack Query for all data fetching
- Handle both success and error states in `ApiResponse<T>`
- Implement debouncing for search inputs (use useEffect + setTimeout)
- Use keyboard navigation for autocomplete (ArrowUp/Down, Enter, Escape)
- Track selection state for keyboard and mouse interactions

## Adding New Features

When creating a new feature module:

1. **Create feature directory**: `features/my-feature/`
2. **Create subdirectories**:
   - `components/` - Feature-specific components
   - `hooks/` - Feature-specific hooks (optional)
   - `utils/` - Feature-specific utilities (optional)
3. **Create index file**: `features/my-feature/index.ts`
   ```typescript
   // Export public API
   export { MyComponent } from './components/my-component';
   export { useMyHook } from './hooks/use-my-hook';
   ```
4. **Import in pages**:
   ```typescript
   import { MyComponent } from '@/features/my-feature';
   ```

## Adding Components to Existing Features

1. Add component to feature's `components/` directory
2. Export from feature's `index.ts`
3. Import in pages using feature's public API
4. If the component is shared across features, move it to `components/` instead

# Do Not

- Edit `components/ui/` files manually (use shadcn CLI)
- Restart containers for frontend code changes (hot reload enabled)
- Use direct axios calls in components (use TanStack Query instead)
- Create forms without react-hook-form + Zod validation
- Use environment variables without `NEXT_PUBLIC_` prefix

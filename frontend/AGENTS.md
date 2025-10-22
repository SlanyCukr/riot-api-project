# Tech Stack
- Next.js 15 + React 19 (App Router)
- TypeScript + Tailwind CSS 4 + shadcn/ui (New York)
- TanStack Query v5 + Zod v4
- react-hook-form + Axios + next-themes
- sonner + lucide-react
- Autocomplete/suggestions with debouncing

# Project Structure

## Feature-Based Architecture

The frontend uses **feature-based organization** where related components, hooks, and utilities are grouped by domain:

### Pages (`app/`)
Next.js App Router pages (routing structure unchanged):
- `app/page.tsx` - Home/dashboard
- `app/player-analysis/page.tsx` - Smurf detection analysis
- `app/matchmaking-analysis/page.tsx` - Matchmaking fairness
- `app/tracked-players/page.tsx` - Tracked players management
- `app/jobs/page.tsx` - Background jobs control
- `app/settings/page.tsx` - System settings

### Feature Modules (`features/`)

Each feature contains components, hooks, and utilities specific to that domain:

**`features/players/`** - Player management
- `components/player-search.tsx` - Player search with autocomplete
- `components/player-card.tsx` - Player info display
- `components/player-stats.tsx` - Player statistics
- `components/add-tracked-player.tsx` - Add to tracking
- `components/tracked-players-list.tsx` - Tracked players table
- `hooks/` - Player-specific hooks
- `utils/` - Player utility functions
- `index.ts` - Public exports

**`features/matches/`** - Match data
- `components/match-history.tsx` - Match history table
- `components/encounter-stats.tsx` - Opponent encounter statistics
- `components/recent-opponents.tsx` - Recent opponents list

**`features/smurf-detection/`** - Smurf analysis
- `components/player-analysis.tsx` - Smurf detection results

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
export { PlayerSearch } from './components/player-search'
export { PlayerCard } from './components/player-card'
export { PlayerStats } from './components/player-stats'
```

## Import Patterns

### Importing from Features
```typescript
// Import from feature's public API
import { PlayerSearch, PlayerCard } from '@/features/players'
import { MatchHistory } from '@/features/matches'
import { JobCard } from '@/features/jobs'

// Or import directly
import { PlayerSearch } from '@/features/players/components/player-search'
```

### Importing from Core
```typescript
import { api } from '@/lib/core/api'
import { playerSchema } from '@/lib/core/schemas'
```

### Importing Shared Components
```typescript
import { Button } from '@/components/ui/button'
import { SidebarNav } from '@/components/sidebar-nav'
```

### Page Composition Example
```typescript
// app/player-analysis/page.tsx
import { PlayerSearch, PlayerAnalysis } from '@/features/players'
import { SmurfDetectionResults } from '@/features/smurf-detection'

export default function PlayerAnalysisPage() {
  return (
    <div>
      <PlayerSearch />
      <SmurfDetectionResults />
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
   export { MyComponent } from './components/my-component'
   export { useMyHook } from './hooks/use-my-hook'
   ```
4. **Import in pages**:
   ```typescript
   import { MyComponent } from '@/features/my-feature'
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

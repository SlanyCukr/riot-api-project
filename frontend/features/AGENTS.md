# Frontend Feature Development Guide

## Overview

The `frontend/features/` directory contains domain-specific UI components, hooks, and utilities organized by feature. Each feature is self-contained with all related frontend code, mirroring the backend's feature-based architecture.

## Feature-Based Architecture

### Principles

1. **Feature Cohesion**: All UI code related to a domain feature lives together
2. **Clear Boundaries**: Features expose public APIs via `index.ts`
3. **Page Composition**: Pages in `app/` import and compose feature components
4. **Shared vs Feature**: Shared layout/infrastructure in `components/`, feature-specific in `features/`

### Existing Features

- **`players/`** - Player search, cards, stats, tracked players management
- **`matches/`** - Match history, opponent statistics
- **`smurf-detection/`** - Smurf analysis results display
- **`matchmaking/`** - Matchmaking fairness analysis
- **`jobs/`** - Background job management and monitoring
- **`settings/`** - System settings UI

## Standard Feature Structure

Every feature follows this structure:

```
features/<feature-name>/
├── components/          # Feature-specific components
│   ├── player-search.tsx
│   ├── player-card.tsx
│   └── player-stats.tsx
├── hooks/               # Feature-specific hooks (optional)
│   ├── use-player-search.ts
│   └── use-player-data.ts
├── utils/               # Feature-specific utilities (optional)
│   └── player-formatters.ts
└── index.ts             # Public API exports
```

### File Responsibilities

#### `index.ts` - Public API

Export the feature's public interface for use by pages:

```typescript
// features/players/index.ts
export { PlayerSearch } from "./components/player-search";
export { PlayerCard } from "./components/player-card";
export { PlayerStats } from "./components/player-stats";
export { AddTrackedPlayer } from "./components/add-tracked-player";
export { TrackedPlayersList } from "./components/tracked-players-list";

// Export hooks if they're part of the public API
export { usePlayerSearch } from "./hooks/use-player-search";
```

#### `components/` - Feature Components

React components specific to this feature:

```typescript
// features/players/components/player-search.tsx
"use client"

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/core/api'

interface PlayerSearchProps {
  onPlayerSelect?: (player: Player) => void
}

export function PlayerSearch({ onPlayerSelect }: PlayerSearchProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debouncing pattern
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  // TanStack Query for data fetching
  const { data, isLoading, error } = useQuery({
    queryKey: ['player-suggestions', debouncedSearch],
    queryFn: () => api.get(`/players/suggestions?q=${debouncedSearch}`),
    enabled: debouncedSearch.length >= 3,
  })

  return (
    <div className="space-y-4">
      <Input
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="Search players..."
      />
      {isLoading && <p>Loading...</p>}
      {error && <p>Error loading suggestions</p>}
      {/* Render suggestions */}
    </div>
  )
}
```

**Component Guidelines:**

- Use `"use client"` for interactivity/hooks/browser APIs
- TypeScript interface for props
- Handle loading, error, and success states
- Use shadcn/ui primitives from `@/components/ui/`
- Use TanStack Query for data fetching
- kebab-case file names, PascalCase component names

#### `hooks/` - Custom Hooks

Reusable logic extracted into hooks:

```typescript
// features/players/hooks/use-player-search.ts
"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/core/api";

export function usePlayerSearch(initialQuery: string = "") {
  const [searchTerm, setSearchTerm] = useState(initialQuery);
  const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const query = useQuery({
    queryKey: ["player-search", debouncedSearch],
    queryFn: () => api.get(`/players/suggestions?q=${debouncedSearch}`),
    enabled: debouncedSearch.length >= 3,
  });

  return {
    searchTerm,
    setSearchTerm,
    suggestions: query.data,
    isLoading: query.isLoading,
    error: query.error,
  };
}
```

#### `utils/` - Feature Utilities

Helper functions specific to the feature:

```typescript
// features/players/utils/player-formatters.ts
export function formatRiotId(gameName: string, tagLine: string): string {
  return `${gameName}#${tagLine}`;
}

export function formatRank(tier: string, rank: string, lp: number): string {
  return `${tier} ${rank} (${lp} LP)`;
}
```

## Creating a New Feature

### Step-by-Step Guide

1. **Create feature directory**:

   ```bash
   mkdir -p frontend/features/my-feature/components
   ```

2. **Create components** in `components/`:

   ```typescript
   // features/my-feature/components/my-component.tsx
   "use client"

   export function MyComponent() {
     return <div>My Feature</div>
   }
   ```

3. **Create `index.ts`** with exports:

   ```typescript
   // features/my-feature/index.ts
   export { MyComponent } from "./components/my-component";
   ```

4. **Use in pages**:

   ```typescript
   // app/my-page/page.tsx
   import { MyComponent } from '@/features/my-feature'

   export default function MyPage() {
     return <MyComponent />
   }
   ```

## Import Patterns

### Within Feature (Internal)

```typescript
// Import sibling components/hooks/utils
import { PlayerCard } from "./player-card";
import { usePlayerData } from "../hooks/use-player-data";
import { formatRank } from "../utils/player-formatters";
```

### From Core Lib

```typescript
import { api } from "@/lib/core/api";
import { playerSchema } from "@/lib/core/schemas";
import { cn } from "@/lib/utils";
```

### From Shared Components

```typescript
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { SidebarNav } from "@/components/sidebar-nav";
```

### From Other Features (Use Public API)

```typescript
// ✅ Correct: Import from public API
import { PlayerCard } from "@/features/players";

// ❌ Wrong: Import internal components
import { PlayerCard } from "@/features/players/components/player-card";
```

### In Pages (Feature Composition)

```typescript
// app/player-analysis/page.tsx
import { PlayerSearch, PlayerStats } from '@/features/players'
import { SmurfAnalysis } from '@/features/smurf-detection'

export default function PlayerAnalysisPage() {
  return (
    <div>
      <PlayerSearch />
      <SmurfAnalysis />
    </div>
  )
}
```

## Common Patterns

### Data Fetching with TanStack Query

```typescript
"use client"

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/core/api'

export function PlayerList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['players'],
    queryFn: () => api.get('/players'),
    refetchInterval: 30000, // Auto-refresh every 30s
  })

  if (isLoading) return <LoadingSkeleton />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      {data.map((player) => (
        <PlayerCard key={player.id} player={player} />
      ))}
    </div>
  )
}
```

### Mutations with TanStack Query

```typescript
"use client"

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/core/api'
import { toast } from 'sonner'

export function AddPlayerButton() {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (playerData: PlayerCreate) =>
      api.post('/players', playerData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['players'] })
      toast.success('Player added successfully')
    },
    onError: (error) => {
      toast.error(`Failed to add player: ${error.message}`)
    },
  })

  return (
    <Button
      onClick={() => mutation.mutate({ gameName: 'Test', tagLine: 'NA1' })}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? 'Adding...' : 'Add Player'}
    </Button>
  )
}
```

### Forms with react-hook-form + Zod

```typescript
"use client"

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const playerSchema = z.object({
  gameName: z.string().min(3).max(16),
  tagLine: z.string().min(2).max(5),
})

type PlayerForm = z.infer<typeof playerSchema>

export function PlayerForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PlayerForm>({
    resolver: zodResolver(playerSchema),
  })

  const onSubmit = (data: PlayerForm) => {
    console.log(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input {...register('gameName')} placeholder="Game Name" />
      {errors.gameName && <p>{errors.gameName.message}</p>}

      <Input {...register('tagLine')} placeholder="Tag Line" />
      {errors.tagLine && <p>{errors.tagLine.message}</p>}

      <Button type="submit">Submit</Button>
    </form>
  )
}
```

### Debouncing Pattern

```typescript
"use client"

import { useState, useEffect } from 'react'

export function SearchInput() {
  const [input, setInput] = useState('')
  const [debouncedValue, setDebouncedValue] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(input)
    }, 300)

    return () => clearTimeout(timer)
  }, [input])

  // Use debouncedValue for API calls
  useEffect(() => {
    if (debouncedValue.length >= 3) {
      // Fetch data
    }
  }, [debouncedValue])

  return (
    <input
      value={input}
      onChange={(e) => setInput(e.target.value)}
      placeholder="Search..."
    />
  )
}
```

### Keyboard Navigation

```typescript
"use client"

import { useState, useRef, KeyboardEvent } from 'react'

export function Autocomplete({ suggestions }: { suggestions: string[] }) {
  const [selectedIndex, setSelectedIndex] = useState(-1)

  const handleKeyDown = (e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) =>
          Math.min(prev + 1, suggestions.length - 1)
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, -1))
        break
      case 'Enter':
        if (selectedIndex >= 0) {
          // Handle selection
        }
        break
      case 'Escape':
        setSelectedIndex(-1)
        break
    }
  }

  return <div onKeyDown={handleKeyDown}>{/* Render suggestions */}</div>
}
```

## Component Placement Rules

### Feature-Specific → `features/<feature>/components/`

- Used by ONE feature only
- Domain-specific business logic
- Example: `PlayerSearch`, `SmurfAnalysisResults`

### Shared Layout/Infrastructure → `components/`

- Used across multiple features
- Generic layout components
- Example: `SidebarNav`, `LoadingSkeleton`, `ThemeToggle`

### shadcn/ui Primitives → `components/ui/`

- **Never edit manually** - use shadcn CLI
- Generic UI primitives (Button, Card, Input, etc.)
- Example: `Button`, `Card`, `Dialog`

## See Also

- `frontend/AGENTS.md` - Overall frontend architecture
- `frontend/app/AGENTS.md` - Next.js App Router and page composition
- `frontend/components/AGENTS.md` - Shared components guide
- `frontend/lib/AGENTS.md` - Core utilities (API client, schemas)

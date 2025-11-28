# Frontend Feature Development Guide

## Overview

The `frontend/features/` directory contains domain-specific UI components, hooks, and utilities
organized by feature. Each feature is self-contained with all related frontend code, mirroring the
backend's feature-based architecture.

## Feature-Based Architecture

### Principles

1. **Feature Cohesion**: All UI code related to a domain feature lives together
2. **Clear Boundaries**: Features expose public APIs via `index.ts`
3. **Page Composition**: Pages in `app/` import and compose feature components
4. **Shared vs Feature**: Shared layout/infrastructure in `components/`, feature-specific in
   `features/`

### Existing Features

- **`auth/`** - Authentication (AuthProvider, ProtectedRoute, useAuth)
- **`players/`** - Player search, cards, stats, tracked players management
- **`matches/`** - Match history, opponent statistics
- **`player-analysis/`** - Player analysis results display
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
export { PlayerSearch } from './components/player-search';
export { PlayerCard } from './components/player-card';
export { PlayerStats } from './components/player-stats';
export { AddTrackedPlayer } from './components/add-tracked-player';
export { TrackedPlayersList } from './components/tracked-players-list';
export { TrackPlayerButton } from './components/track-player-button';
```

#### `components/` - Feature Components

React components specific to this feature:

```typescript
// features/players/components/player-search.tsx
'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Search, User, AlertCircle, UserPlus, Loader2 } from 'lucide-react';
import { z } from 'zod';

import { Player, PlayerSchema } from '@/lib/core/schemas';
import { playerSearchSchema, type PlayerSearchForm } from '@/lib/core/validations';
import { validatedGet, addTrackedPlayer, searchPlayerSuggestions } from '@/lib/core/api';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

// Constants for autocomplete behavior
const SUGGESTION_DEBOUNCE_MS = 300;
const MIN_SEARCH_LENGTH = 1;

interface PlayerSearchProps {
  onPlayerFound: (player: Player) => void;
}

export function PlayerSearch({ onPlayerFound }: PlayerSearchProps) {
  const [showTrackOption, setShowTrackOption] = useState(false);
  const [lastSearchParams, setLastSearchParams] = useState<PlayerSearchForm | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debouncedSearchValue, setDebouncedSearchValue] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const form = useForm<PlayerSearchForm>({
    resolver: zodResolver(playerSearchSchema),
    defaultValues: {
      searchValue: '',
      platform: 'eun1',
    },
  });

  // eslint-disable-next-line react-hooks/incompatible-library -- React Hook Form watch() is intentionally not memoizable
  const searchValue = form.watch('searchValue');
  const platform = form.watch('platform');

  // Debounce search value for autocomplete
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchValue(searchValue);
    }, SUGGESTION_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchValue]);

  // Fetch suggestions when debounced value changes
  const { data: suggestionsResult, isLoading: suggestionsLoading } = useQuery({
    queryKey: ['player-suggestions', debouncedSearchValue, platform],
    queryFn: async () => {
      if (debouncedSearchValue.length < MIN_SEARCH_LENGTH) {
        return { success: true as const, data: [] };
      }

      const result = await searchPlayerSuggestions({
        q: debouncedSearchValue,
        platform: platform,
        limit: 5,
      });

      return result;
    },
    enabled: debouncedSearchValue.length >= MIN_SEARCH_LENGTH,
    retry: 1,
    retryDelay: 500,
  });

  const suggestions = useMemo(() => {
    return suggestionsResult?.success ? suggestionsResult.data : [];
  }, [suggestionsResult]);

  // ... (rest of the component continues with keyboard navigation, mutations, etc.)
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
// features/auth/context/auth-context.tsx
"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { getToken, setToken, removeToken } from "../utils/token-manager";
import type { User, LoginCredentials, AuthContextType } from "../types";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Check for token synchronously on initialization to avoid flash
  const [isLoading, setIsLoading] = useState(() => {
    if (typeof window === "undefined") return true;
    return !!getToken();
  });
  const router = useRouter();

  // Check authentication status on mount and after login
  const checkAuth = useCallback(async () => {
    const token = getToken();

    if (!token) {
      setUser(null);
      setIsLoading(false);
      removeToken(); // Ensure both localStorage and cookie are cleared
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setToken(token); // Ensure token is in sync across storage mechanisms
      } else {
        // Token invalid or expired
        removeToken();
        setUser(null);
      }
    } catch (error) {
      // Only log errors in development
      if (process.env.NODE_ENV === "development") {
        console.error("Auth check failed:", error);
      }
      removeToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      // OAuth2 password flow requires form-data format
      const formData = new URLSearchParams();
      formData.append("username", credentials.email); // OAuth2 uses 'username' field
      formData.append("password", credentials.password);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();

      // Store token using centralized token manager
      setToken(data.access_token);

      // Fetch user data
      await checkAuth();

      // Redirect to home page
      router.push("/");
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  const logout = () => {
    removeToken(); // Use centralized token removal
    setUser(null);
    router.push("/sign-in");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
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
   export { MyComponent } from './components/my-component';
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
import { PlayerCard } from './player-card';
import { usePlayerData } from '../hooks/use-player-data';
import { formatRank } from '../utils/player-formatters';
```

### From Core Lib

```typescript
import { api } from '@/lib/core/api';
import { playerSchema } from '@/lib/core/schemas';
import { cn } from '@/lib/utils';
```

### From Shared Components

```typescript
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { SidebarNav } from '@/components/sidebar-nav';
```

### From Other Features (Use Public API)

```typescript
// ✅ Correct: Import from public API
import { PlayerCard } from '@/features/players';

// ❌ Wrong: Import internal components
import { PlayerCard } from '@/features/players/components/player-card';
```

### In Pages (Feature Composition)

```typescript
// app/player-analysis/page.tsx
import { PlayerSearch, PlayerStats } from '@/features/players'
import { PlayerAnalysisComponent } from '@/features/player-analysis'

export default function PlayerAnalysisPage() {
  return (
    <div>
      <PlayerSearch />
      <PlayerAnalysisComponent />
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
- Example: `PlayerSearch`, `PlayerAnalysisComponentResults`

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

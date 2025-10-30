# Next.js 16 App Router Guide

This guide covers the Next.js 16 App Router patterns used in this project.

# Tech Stack

- **Next.js 16.0.0** App Router with React 19.2.0
- **TypeScript 5** with strict mode
- **Tailwind CSS 4.1.14** with CSS-first configuration (@theme)
- **TanStack Query v5.90.2** for data fetching
- **Zod v4.1.12** for runtime validation
- **next-themes v0.4.6** for dark mode support

# App Router Structure

```
app/
├── layout.tsx                 # Root layout (Server Component)
├── page.tsx                   # Home/dashboard (Server Component)
├── globals.css                # Global styles + Tailwind @theme config
├── error.tsx                  # Root error boundary
├── loading.tsx                # Root loading state
├── not-found.tsx              # 404 page
├── player-analysis/           # Player analysis page
│   ├── layout.tsx             # Feature layout
│   └── page.tsx               # Server Component page
├── matchmaking-analysis/      # Matchmaking analysis page
│   ├── layout.tsx             # Feature layout
│   └── page.tsx               # Server Component page
├── jobs/                      # Background jobs page
│   ├── layout.tsx             # Feature layout
│   └── page.tsx               # Server Component page
├── tracked-players/           # Player tracking page
│   └── page.tsx               # Server Component page
├── settings/                  # System settings page
│   └── page.tsx               # Server Component page
├── sign-in/                   # Authentication pages
│   └── page.tsx               # Sign-in page
├── license/                   # License page
│   └── page.tsx               # Static page
└── privacy-policy/            # Privacy policy page
    └── page.tsx               # Static page
```

## Layout Pattern

Root layout with providers and navigation:

```tsx
// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from '@/components/providers';
import { SidebarNav } from '@/components/sidebar-nav';
import { Toaster } from 'sonner';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'League Analysis',
  description: 'Player analysis and matchmaking evaluation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <SidebarNav />
          <div id='content' className='min-h-screen'>
            <main className='container mx-auto py-8 px-4'>{children}</main>
          </div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
```

## Page Composition

Pages import and compose feature components:

```tsx
// app/player-analysis/page.tsx
import { PlayerSearch } from '@/features/players';
import { PlayerAnalysisResults } from '@/features/player-analysis';

export default function PlayerAnalysisPage() {
  return (
    <div className='space-y-8'>
      <div id='header-card' className='p-6 rounded-lg text-white'>
        <h1 className='text-3xl font-bold tracking-tight'>Player Analysis</h1>
        <p className='text-white/80'>Analyze player performance and behavior patterns</p>
      </div>

      <PlayerSearch />
      <PlayerAnalysisResults />
    </div>
  );
}
```

## Client Components

Use `"use client"` directive for interactivity:

```tsx
// app/components/ClientComponent.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchPlayerSuggestions } from '@/lib/core/api';
import { LoadingSkeleton } from '@/components/loading-skeleton';

export function ClientComponent() {
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['player-suggestions', searchTerm, 'eun1'],
    queryFn: () =>
      searchPlayerSuggestions({
        q: searchTerm,
        platform: 'eun1',
        limit: 5,
      }),
    enabled: searchTerm.length >= 1,
  });

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <input
        value={searchTerm}
        onChange={e => setSearchTerm(e.target.value)}
        placeholder='Search players...'
        className='w-full px-3 py-2 border border-gray-300 rounded-md'
      />
      {/* Render data */}
    </div>
  );
}
```

## Data Fetching Patterns

### Server Components (No "use client")

```tsx
// app/dashboard/page.tsx
import { api } from '@/lib/core/api'; // Import server-side API client
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default async function DashboardPage() {
  // Direct server-side data fetching
  const stats = await api.get('/analytics/stats');

  return (
    <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
      <Card>
        <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
          <CardTitle className='text-sm font-medium'>Total Players</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-2xl font-bold'>{stats.totalPlayers}</div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Client Components with TanStack Query

```tsx
// app/player-search/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/core/api';
import { PlayerSearch } from '@/features/players';

export default function PlayerSearchPage() {
  return (
    <div>
      <h1 className='text-3xl font-bold mb-8'>Search Players</h1>
      <PlayerSearch />
    </div>
  );
}
```

## Loading States

### Global Loading

```tsx
// app/loading.tsx
import { LoadingSkeleton } from '@/components/loading-skeleton';

export default function Loading() {
  return (
    <div className='flex items-center justify-center min-h-screen'>
      <LoadingSkeleton />
    </div>
  );
}
```

### Route-Specific Loading

```tsx
// app/player-analysis/loading.tsx
import { LoadingSkeleton } from '@/components/loading-skeleton';

export default function Loading() {
  return (
    <div className='space-y-8'>
      <div className='space-y-2'>
        <div className='h-8 bg-gray-200 rounded w-1/4 animate-pulse' />
        <div className='h-4 bg-gray-200 rounded w-1/2 animate-pulse' />
      </div>
      <LoadingSkeleton />
    </div>
  );
}
```

## Error Handling

### Global Error Boundary

```tsx
// app/error.tsx
'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className='flex flex-col items-center justify-center min-h-[400px]'>
      <h2 className='text-2xl font-bold mb-4'>Something went wrong!</h2>
      <p className='text-muted-foreground mb-4'>
        {error.message || 'An unexpected error occurred'}
      </p>
      <button
        onClick={reset}
        className='px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600'
      >
        Try again
      </button>
    </div>
  );
}
```

### Route-Specific Error Boundary

```tsx
// app/player-analysis/error.tsx
'use client';

import { AlertTriangle } from 'lucide-react';

export default function PlayerAnalysisError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className='flex flex-col items-center justify-center space-y-4'>
      <AlertTriangle className='h-12 w-12 text-red-500' />
      <h2 className='text-xl font-semibold'>Analysis Error</h2>
      <p className='text-muted-foreground text-center max-w-md'>
        Unable to analyze player data. Please check your search and try again.
      </p>
      <button
        onClick={reset}
        className='px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90'
      >
        Retry Analysis
      </button>
    </div>
  );
}
```

## Not Found Pages

```tsx
// app/not-found.tsx
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className='flex flex-col items-center justify-center min-h-[400px] space-y-4'>
      <h1 className='text-4xl font-bold'>404</h1>
      <p className='text-muted-foreground'>Page not found</p>
      <Link
        href='/'
        className='px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90'
      >
        Go home
      </Link>
    </div>
  );
}
```

# Routing & Navigation

## Static Routes

```tsx
// app/about/page.tsx
export default function AboutPage() {
  return <div>About page</div>;
}
```

## Dynamic Routes

```tsx
// app/players/[id]/page.tsx
interface PlayerPageProps {
  params: { id: string };
}

export default function PlayerPage({ params }: PlayerPageProps) {
  return <div>Player ID: {params.id}</div>;
}
```

## Search Params

```tsx
// app/search/page.tsx
'use client';

import { useSearchParams } from 'next/navigation';

export default function SearchPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q');

  return <div>Search results for: {query}</div>;
}
```

# Streaming & Suspense

## Suspense Boundaries

```tsx
// app/dashboard/page.tsx
import { Suspense } from 'react';
import { StatsCards } from '@/components/stats-cards';
import { RecentMatches } from '@/components/recent-matches';
import { LoadingSkeleton } from '@/components/loading-skeleton';

export default function DashboardPage() {
  return (
    <div className='space-y-8'>
      <Suspense fallback={<LoadingSkeleton />}>
        <StatsCards />
      </Suspense>

      <Suspense fallback={<LoadingSkeleton />}>
        <RecentMatches />
      </Suspense>
    </div>
  );
}
```

# Global Styles

## CSS-first Configuration

```css
/* app/globals.css */
@import 'tailwindcss';

@theme {
  --color-primary: oklch(0.7 0.2 250);
  --color-secondary: oklch(0.9 0.1 200);
  --font-sans: 'Inter', system-ui, sans-serif;

  /* Custom spacing */
  --spacing-container: max(1rem, 4vw);
}

@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground;
  }
}

@custom-variant dark (&:is(.dark, .dark *)) {
  --color-background: oklch(0.15 0 0);
  --color-foreground: oklch(0.95 0 0);
}
```

# Best Practices

## Server vs Client Components

✅ **Use Server Components when:**

- Fetching data from server-side APIs
- Rendering static content
- SEO is important
- No interactivity needed

✅ **Use Client Components when:**

- Need interactivity (hooks, events)
- Managing client state
- Using browser APIs
- TanStack Query for data fetching

## Data Fetching

```tsx
// ✅ Good: Server-side fetching for static data
export default async function StatsPage() {
  const stats = await api.get('/analytics/stats');
  return <div>{stats.total}</div>;
}

// ✅ Good: Client-side fetching with TanStack Query
('use client');
export function LiveStats() {
  const { data } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get('/analytics/stats'),
    refetchInterval: 30000,
  });
  return <div>{data?.total}</div>;
}
```

## Error Handling

Always implement proper error boundaries and loading states:

```tsx
// ✅ Good: Comprehensive error handling
export function PlayerCard({ playerId }: { playerId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['player', playerId],
    queryFn: () => api.get(`/players/${playerId}`),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage error={error} />;
  if (!data) return <NotFoundMessage />;

  return <div>{data.name}</div>;
}
```

# Commands

```bash
# Create new page
mkdir -p app/my-page && echo 'export default function MyPage() { return <div>My Page</div> }' > app/my-page/page.tsx

# Add navigation link
# Edit: components/sidebar-nav.tsx

# Test layout
# Navigate to: http://localhost:3000

# Type check
npx tsc --noEmit

# Build test
npm run build
```

# Do Not

❌ **Don't mix server/client patterns incorrectly**

- Don't use "use client" in layout.tsx
- Don't use browser APIs in server components
- Don't fetch data with TanStack Query in server components

❌ **Don't skip error boundaries**

- Always implement error.tsx for critical pages
- Don't let errors crash the entire app
- Provide useful error messages and recovery options

❌ **Don't ignore loading states**

- Always implement loading.tsx for data-heavy pages
- Use LoadingSkeleton for consistent UX
- Don't block the entire UI for non-critical data

❌ **Don't break streaming**

- Keep suspense boundaries granular
- Don't wrap everything in a single suspense
- Allow partial page loading for better performance

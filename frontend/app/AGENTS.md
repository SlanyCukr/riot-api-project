# Next.js App Router - Agent Instructions

Instructions for generating pages, routing, and layouts. **See `frontend/AGENTS.md` for overview.**

## Purpose

This document provides code generation patterns for AI agents working on Next.js App Router pages.

## Directory Structure

```
app/
  ├── layout.tsx                 # Root layout with QueryClientProvider
  ├── page.tsx                   # Home/Landing page
  ├── globals.css                # Global styles + Tailwind + shadcn variables
  ├── error.tsx                  # Error boundary
  ├── loading.tsx                # Root loading state
  ├── not-found.tsx              # 404 page
  ├── smurf-detection/
  │   └── page.tsx               # Smurf detection & player analysis page
  └── jobs/
      └── page.tsx               # Background jobs monitoring page
```

## Application Pages

### `/` - Home/Landing Page

- Project overview and introduction
- Navigation to main features
- Quick links to smurf detection and jobs monitoring

### `/smurf-detection` - Player Analysis

- Player search by Riot ID (gameName#tagLine) or summoner name
- Real-time match history fetching from Riot API
- Multi-factor smurf detection analysis with detailed breakdown
- Recent opponents tracking with encounter statistics
- Player tracking toggle for automatic updates
- Auto-refreshing match data

**Key Components Used:**

- `player-search.tsx` - Search form with platform selection
- `player-card.tsx` - Player info with rank badges
- `player-stats.tsx` - Match statistics overview
- `match-history.tsx` - Match history table with filters
- `smurf-detection.tsx` - Smurf analysis factors
- `recent-opponents.tsx` - Opponent encounter tracking
- `track-player-button.tsx` - Player tracking toggle

### `/jobs` - Background Jobs Monitoring

- Job configuration cards with manual trigger buttons
- Real-time execution history with status updates
- System health dashboard with database/API status
- Auto-refresh every 15 seconds for live monitoring

**Key Components Used:**

- `job-card.tsx` - Job configuration card
- `job-executions.tsx` - Execution history table
- `system-status.tsx` - Health dashboard

## Layouts

### Root Layout (`app/layout.tsx`)

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
            {children}
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
```

**Key Features:**

- `suppressHydrationWarning` on `<html>` to prevent theme flash
- QueryClientProvider for TanStack Query
- ThemeProvider for dark mode support
- Global font configuration (Geist)

## Code Generation Patterns

### Basic Page Template

```tsx
export default function MyPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Page Title</h1>
      {/* Page content */}
    </div>
  );
}
```

### Client-Side Page Template (Most Common)

**Use this template for pages with data fetching or interactivity:**

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import { MyDataSchema } from "@/lib/schemas";

export default function MyPage() {
  const { data: result, isLoading } = useQuery({
    queryKey: ["myData"],
    queryFn: () => validatedGet(MyDataSchema, "/api/mydata"),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (!result?.success) return <ErrorMessage error={result?.error} />;

  return <div>{/* Render data */}</div>;
}
```

### Page with Auto-Refresh Template

**Use for real-time monitoring pages (jobs, system status):**

```tsx
const { data: result, isLoading } = useQuery({
  queryKey: ["jobs"],
  queryFn: () => validatedGet(JobsSchema, "/jobs"),
  refetchInterval: 15000, // Refresh every 15 seconds
});
```

## Navigation

Navigation is handled by `components/sidebar-nav.tsx`:

```tsx
const navItems = [
  {
    title: "Home",
    href: "/",
    icon: HomeIcon,
  },
  {
    title: "Smurf Detection",
    href: "/smurf-detection",
    icon: SearchIcon,
  },
  {
    title: "Jobs",
    href: "/jobs",
    icon: PlayIcon,
  },
];
```

To add a new page to navigation:

1. Create page at `app/my-page/page.tsx`
2. Add entry to `navItems` in `components/sidebar-nav.tsx`
3. Import appropriate icon from `lucide-react`

## Routing Conventions

### File-Based Routing

- `app/page.tsx` → `/`
- `app/jobs/page.tsx` → `/jobs`
- `app/smurf-detection/page.tsx` → `/smurf-detection`

### Dynamic Routes (if needed)

```
app/
  └── players/
      └── [puuid]/
          └── page.tsx         # /players/:puuid
```

```tsx
export default function PlayerPage({ params }: { params: { puuid: string } }) {
  const { puuid } = params;
  // Use puuid to fetch player data
}
```

### Route Groups (if needed)

```
app/
  └── (dashboard)/
      ├── layout.tsx           # Shared layout
      ├── settings/
      │   └── page.tsx
      └── profile/
          └── page.tsx
```

## Global Styles (`app/globals.css`)

Contains:

- Tailwind directives (`@tailwind base`, `@tailwind components`, `@tailwind utilities`)
- CSS custom properties for theming (light/dark mode)
- shadcn/ui variable definitions
- Font imports (Geist Sans, Geist Mono)

**DO NOT modify CSS variables** - they're managed by shadcn/ui configuration.

## Error Handling

### Error Boundary (`app/error.tsx`)

```tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

### Not Found Page (`app/not-found.tsx`)

```tsx
export default function NotFound() {
  return (
    <div>
      <h2>404 - Page Not Found</h2>
      <Link href="/">Return Home</Link>
    </div>
  );
}
```

## Loading States

### Root Loading (`app/loading.tsx`)

```tsx
export default function Loading() {
  return <LoadingSkeleton />;
}
```

### Component-Level Loading

```tsx
const { isLoading } = useQuery(...);

if (isLoading) return <LoadingSkeleton />;
```

Use `components/loading-skeleton.tsx` for consistent loading states.

## Agent Tasks

### Generate New Page

1. Create `app/my-page/page.tsx`
2. Add `"use client"` if using hooks/browser APIs
3. Implement page component
4. Add to navigation in `components/sidebar-nav.tsx`
5. Add route to sidebar navigation

### Add Auto-Refresh Pattern

```tsx
const { data } = useQuery({
  queryKey: ["data"],
  queryFn: fetchData,
  refetchInterval: 15000, // 15 seconds
});
```

### Generate Page-Specific Layout

Create `app/my-page/layout.tsx`:

```tsx
export default function MyPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="custom-layout">
      <Sidebar />
      <main>{children}</main>
    </div>
  );
}
```

## Troubleshooting

**Page not rendering:**

- Check file is named `page.tsx`
- Ensure default export exists
- Clear `.next` folder and restart

**Client-side code not working:**

- Add `"use client"` directive at top of file
- Check browser console for errors

**Hydration mismatch:**

- Ensure server and client render same content
- Use `useEffect` for client-only code
- Add `suppressHydrationWarning` if needed (already on `<html>`)

**Environment variables not accessible:**

- Must use `NEXT_PUBLIC_` prefix for client components
- Restart dev server after changes

**Styles not applying:**

- Clear `.next` folder
- Check Tailwind class names are correct
- Verify `globals.css` is imported in `layout.tsx`

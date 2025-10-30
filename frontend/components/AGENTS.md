# Tech Stack

- React 19.2.0 + TypeScript 5
- shadcn/ui (New York style)
- Tailwind CSS 4.1.14 + next-themes v0.4.6
- react-hook-form v7.65.0 + Zod v4.1.12 validation
- TanStack Query v5.90.2 + sonner v2.0.7

# Project Structure

```
components/
├── ui/                        # shadcn/ui primitives (DO NOT edit manually)
├── sidebar-nav.tsx           # Navigation sidebar
├── theme-provider.tsx        # Theme context provider
├── theme-toggle.tsx          # Dark mode toggle
├── providers.tsx             # TanStack Query provider
└── loading-skeleton.tsx      # Loading states
```

## Shared Component Patterns

### Layout Components

**Sidebar Navigation** - Global navigation with active state tracking:

```tsx
// components/sidebar-nav.tsx
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import { Menu, X, User, LogOut, Settings, Wrench } from 'lucide-react';
import { useAuth } from '@/features/auth';

interface NavItem {
  name: string;
  path: string;
}

const navItems: NavItem[] = [
  { name: 'Home', path: '/' },
  { name: 'Player Analysis', path: '/player-analysis' },
  { name: 'Matchmaking Analysis', path: '/matchmaking-analysis' },
  { name: 'Tracked Players', path: '/tracked-players' },
];

export function SidebarNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Hide sidebar on sign-in page
  if (pathname === '/sign-in') {
    return null;
  }

  const isActive = (path: string) => {
    if (path === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile Hamburger Button */}
      <button
        className='fixed left-4 top-4 z-50 rounded-md bg-[#0a1428] p-2 text-white shadow-lg transition-colors hover:bg-[#0d1a33] md:hidden'
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label='Toggle menu'
      >
        {menuOpen ? <X className='h-6 w-6' /> : <Menu className='h-6 w-6' />}
      </button>

      {/* Sidebar Menu */}
      <aside
        suppressHydrationWarning
        style={{ backgroundColor: '#0a1428' }}
        className={`fixed inset-y-0 left-0 z-40 w-[240px] transform shadow-xl transition-transform duration-300 ease-in-out md:sticky md:top-0 md:h-screen md:w-[220px] lg:w-[240px] ${
          menuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className='flex h-full flex-col'>
          {/* Logo Section */}
          <div className='border-b border-white/10 p-6'>
            <Link
              href='/'
              className='block cursor-pointer transition-opacity duration-300 hover:opacity-80'
              onClick={() => setMenuOpen(false)}
            >
              <div className='relative mx-auto hidden h-[60px] w-full max-w-[200px] md:block md:max-w-[180px]'>
                <Image
                  src='/logo-v3.png'
                  alt='League Analysis Logo'
                  fill
                  sizes='(max-width: 768px) 200px, 180px'
                  className='object-contain'
                  priority
                />
              </div>
              <div className='text-center text-xl font-bold text-white md:hidden'>
                League Analysis
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className='flex-1 py-6 overflow-y-auto' suppressHydrationWarning>
            <ul className='space-y-2'>
              {navItems.map(item => (
                <li key={item.name}>
                  <Link
                    href={item.path}
                    onClick={() => setMenuOpen(false)}
                    className={`block border-l-4 px-6 py-3 text-white transition-all duration-300 hover:bg-white/10 ${
                      isActive(item.path)
                        ? 'border-[#cfa93a] bg-white/5'
                        : 'border-transparent hover:border-[#cfa93a]/50'
                    }`}
                  >
                    <span
                      suppressHydrationWarning
                      className={`transition-colors duration-300 ${
                        isActive(item.path) ? 'text-[#cfa93a] font-medium' : 'hover:text-[#cfa93a]'
                      }`}
                    >
                      {item.name}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* User Info and Bottom Links */}
          {user && (
            <div className='border-t border-white/10'>
              <div className='text-xs'>
                <div className='flex items-center gap-2 text-white p-4 pb-2'>
                  <User className='h-4 w-4 text-[#cfa93a]' />
                  <p className='font-medium'>{user.display_name}</p>
                </div>

                <Link
                  href='/jobs'
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-2 px-4 py-2 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] ${
                    isActive('/jobs') ? 'text-[#cfa93a] font-medium' : ''
                  }`}
                >
                  <Wrench className='h-4 w-4 text-[#cfa93a]' />
                  Jobs
                </Link>

                <Link
                  href='/settings'
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-2 px-4 py-2 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] ${
                    isActive('/settings') ? 'text-[#cfa93a] font-medium' : ''
                  }`}
                >
                  <Settings className='h-4 w-4 text-[#cfa93a]' />
                  Settings
                </Link>

                <button
                  onClick={logout}
                  className='flex items-center gap-2 px-4 py-2 pb-4 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] w-full text-left'
                >
                  <LogOut className='h-4 w-4 text-[#cfa93a] scale-x-[-1]' />
                  Sign Out
                </button>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className='border-t border-white/10 p-6'>
            <p className='text-center text-xs leading-relaxed text-white/70'>
              © 2025 All rights reserved.
              <br />
              <Link
                href='/license'
                className='underline transition-colors duration-300 hover:text-[#cfa93a]'
              >
                License
              </Link>
              {' | '}
              <Link
                href='/privacy-policy'
                className='underline transition-colors duration-300 hover:text-[#cfa93a]'
              >
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {menuOpen && (
        <div
          className='fixed inset-0 z-30 bg-black/50 md:hidden'
          onClick={() => setMenuOpen(false)}
        />
      )}
    </>
  );
}
```

### Theme Provider

**Dark Mode Support** - Built with next-themes:

```tsx
// components/theme-provider.tsx
'use client';

import * as React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider
      attribute='class'
      defaultTheme='system'
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
```

**Theme Toggle Button**:

```tsx
// components/theme-toggle.tsx
'use client';

import { useTheme } from 'next-themes';
import { Sun, Moon } from 'lucide-react';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
      className='p-2 rounded-md border'
    >
      <Sun className='h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0' />
      <Moon className='absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100' />
    </button>
  );
}
```

### Providers

**TanStack Query Provider with Global Configuration**:

```tsx
// components/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AuthProvider } from '@/features/auth';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
```

### Loading States

**Consistent Loading Skeletons**:

```tsx
// components/loading-skeleton.tsx
export function LoadingSkeleton() {
  return (
    <div className='space-y-3'>
      <div className='h-4 bg-gray-200 rounded animate-pulse' />
      <div className='h-4 bg-gray-200 rounded animate-pulse w-3/4' />
      <div className='h-4 bg-gray-200 rounded animate-pulse w-1/2' />
    </div>
  );
}

export function PlayerCardSkeleton() {
  return (
    <div className='p-4 border rounded-lg space-y-3'>
      <div className='flex items-center space-x-3'>
        <div className='h-12 w-12 bg-gray-200 rounded-full animate-pulse' />
        <div className='space-y-2'>
          <div className='h-4 bg-gray-200 rounded animate-pulse w-32' />
          <div className='h-3 bg-gray-200 rounded animate-pulse w-24' />
        </div>
      </div>
      <div className='h-3 bg-gray-200 rounded animate-pulse' />
    </div>
  );
}
```

## shadcn/ui Integration

### Never Edit Manually

**All components in `ui/` are managed by shadcn CLI:**

```bash
# Add new components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add form

# Components are added to components/ui/ directory
# Customization is done via Tailwind CSS classes
```

### Customization Examples

**Custom Button Variants**:

```tsx
import { Button } from "@/components/ui/button"

// Built-in variants work out of the box
<Button variant="default">Default</Button>
<Button variant="destructive">Destructive</Button>
<Button variant="outline">Outline</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>
```

**Custom Card Layout**:

```tsx
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';

<Card className='w-full max-w-md'>
  <CardHeader>
    <CardTitle>Player Statistics</CardTitle>
  </CardHeader>
  <CardContent>
    <div className='space-y-2'>
      <div className='flex justify-between'>
        <span>KDA:</span>
        <span className='font-mono'>3.2</span>
      </div>
      <div className='flex justify-between'>
        <span>Win Rate:</span>
        <span className='font-mono'>65%</span>
      </div>
    </div>
  </CardContent>
</Card>;
```

# Key Features

## Player Search Autocomplete

`player-search.tsx` implements autocomplete/suggestions for enhanced UX:

**Features:**

- Debounced search (300ms) to reduce API calls
- Keyboard navigation (Arrow Up/Down, Enter, Escape)
- Server-side suggestions with platform filtering
- Loading states with spinner indicator
- Automatic suggestion display on focus
- Mouse and keyboard interaction support

**Implementation details:**

- Uses TanStack Query for fetching suggestions
- Popover component for suggestion dropdown
- Tracks selected index for keyboard navigation
- Minimum search length: 3 characters (configurable via `MIN_SEARCH_LENGTH`)
- Shows Riot ID (Name#TAG) or Summoner Name
- Displays both formats when available

**Key state:**

- `showSuggestions` - Controls dropdown visibility
- `debouncedSearchValue` - Delayed search term for API
- `selectedIndex` - Currently selected suggestion (keyboard nav)

**API:**

- Endpoint: `/players/suggestions`
- Query params: `q` (search term), `platform`, `limit`
- Returns: Array of Player objects matching search

**Debouncing pattern:**

```tsx
useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedSearchValue(searchValue);
  }, SUGGESTION_DEBOUNCE_MS);
  return () => clearTimeout(timer);
}, [searchValue]);
```

**Keyboard navigation:**

```tsx
const handleKeyDown = (e: React.KeyboardEvent) => {
  switch (e.key) {
    case 'ArrowDown': // Move down
    case 'ArrowUp': // Move up
    case 'Enter': // Select current
    case 'Escape': // Close dropdown
  }
};
```

# Commands

- Add shadcn component: `npx shadcn@latest add <component>`
- Create component: `components/my-component.tsx`
- Use form pattern with react-hook-form + Zod
- Handle mutations with TanStack Query

# Code Style

- Add `"use client"` for hooks/events/browser APIs
- Use shadcn/ui primitives from `components/ui/`
- Define TypeScript interface for props
- Handle loading/error/success states
- Use cn() utility for conditional classes
- Follow PascalCase for component names

# Do Not

- Edit files in `components/ui/` manually
- Create custom UI primitives (use shadcn instead)
- Skip TypeScript prop interfaces
- Use direct axios calls (use TanStack Query)
- Forget loading and error states
- Use camelCase for component file names

# Tech Stack

- React 19 + TypeScript
- shadcn/ui (New York style)
- Tailwind CSS 4 + next-themes
- react-hook-form + Zod validation
- TanStack Query + sonner

# Project Structure

- `ui/` - shadcn/ui primitives (DO NOT edit manually)
- `player-analysis.tsx` - Player analysis
- `player-search.tsx` - Player search form with autocomplete
- `player-card.tsx` - Player info display
- `player-stats.tsx` - Match statistics
- `match-history.tsx` - Match history table
- `job-card.tsx` - Job configuration
- `sidebar-nav.tsx` - Navigation sidebar
- `loading-skeleton.tsx` - Loading states

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
    case "ArrowDown": // Move down
    case "ArrowUp":   // Move up
    case "Enter":     // Select current
    case "Escape":    // Close dropdown
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

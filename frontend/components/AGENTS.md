# Tech Stack

- React 19 + TypeScript
- shadcn/ui (New York style)
- Tailwind CSS 4 + next-themes
- react-hook-form + Zod validation
- TanStack Query + sonner

# Project Structure

- `ui/` - shadcn/ui primitives (DO NOT edit manually)
- `player-analysis.tsx` - Player analysis
- `player-search.tsx` - Player search form
- `player-card.tsx` - Player info display
- `player-stats.tsx` - Match statistics
- `match-history.tsx` - Match history table
- `job-card.tsx` - Job configuration
- `sidebar-nav.tsx` - Navigation sidebar
- `loading-skeleton.tsx` - Loading states

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

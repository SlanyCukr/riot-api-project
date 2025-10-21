# Tech Stack
- Next.js 15 + React 19 (App Router)
- TypeScript + Tailwind CSS 4 + shadcn/ui (New York)
- TanStack Query v5 + Zod v4
- react-hook-form + Axios + next-themes
- sonner + lucide-react
- Autocomplete/suggestions with debouncing

# Project Structure
- `app/` - Pages & routing
- `components/` - UI components
- `components/ui/` - shadcn/ui primitives
- `lib/` - API client & utilities
- `hooks/` - Custom React hooks
- `types/` - TypeScript types
- `public/` - Static assets

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

# Do Not
- Edit `components/ui/` files manually (use shadcn CLI)
- Restart containers for frontend code changes (hot reload enabled)
- Use direct axios calls in components (use TanStack Query instead)
- Create forms without react-hook-form + Zod validation
- Use environment variables without `NEXT_PUBLIC_` prefix

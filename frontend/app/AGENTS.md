# Tech Stack
- Next.js 15 App Router + React 19
- TypeScript + Tailwind CSS 4
- TanStack Query + Zod validation
- next-themes for dark mode

# Project Structure
- `layout.tsx` - Root layout with providers
- `page.tsx` - Home landing page
- `globals.css` - Global styles + Tailwind + shadcn
- `error.tsx` - Error boundary
- `loading.tsx` - Root loading state
- `not-found.tsx` - 404 page
- `smurf-detection/` - Player analysis page
- `jobs/` - Background jobs monitoring

# Commands
- Create page: `app/my-page/page.tsx`
- Add navigation: Update `components/sidebar-nav.tsx`
- Auto-refresh: Add `refetchInterval: 15000` to useQuery

# Code Style
- Add `"use client"` for hooks/interactivity
- Use container class: `className="container mx-auto py-8"`
- Handle loading states with LoadingSkeleton
- Use validatedGet from lib/api for data fetching
- Follow ApiResponse<T> success/error pattern

# Do Not
- Modify CSS variables in globals.css (managed by shadcn)
- Create pages without proper error handling
- Forget to add new pages to sidebar navigation
- Use browser APIs without `"use client"` directive
- Skip loading and error states in pages

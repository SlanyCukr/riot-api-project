# Frontend - Riot API Web Application

Next.js 15 frontend for the Riot API Match History & Player Analysis application. Provides an intuitive interface for analyzing League of Legends player data and matchmaking fairness.

## Tech Stack

- **Framework**: Next.js 15 with App Router + React 19
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4 + shadcn/ui components
- **Data Fetching**: TanStack Query (React Query) for caching and state management
- **Forms**: react-hook-form with Zod validation
- **HTTP Client**: Axios
- **Icons**: Lucide React + Radix UI Icons
- **Theme**: next-themes for dark mode support

## Project Structure

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx             # Root layout with providers
│   ├── page.tsx               # Dashboard (main route)
│   └── globals.css            # Global styles + CSS variables
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── player-search.tsx      # Player search form
│   ├── player-card.tsx        # Player information display
│   ├── match-history.tsx      # Match history table
│   ├── player-analysis.tsx    # Player analysis results
│   ├── matchmaking-analysis.tsx  # Matchmaking analysis component
│   └── providers.tsx          # Client providers (TanStack Query)
├── lib/
│   ├── utils.ts               # Utility functions (cn helper)
│   ├── api.ts                 # API client with Zod validation
│   ├── schemas.ts             # Zod schemas for API types
│   └── validations.ts         # Form validation schemas
├── components.json            # shadcn/ui configuration
├── next.config.ts             # Next.js configuration
├── tailwind.config.ts         # Tailwind CSS configuration
└── tsconfig.json              # TypeScript configuration
```

## Development

### Prerequisites

- Node.js 24+ (or Docker)
- Backend API running (see root README.md)

### Running with Docker (Recommended)

```bash
# From project root
docker compose up frontend

# Access at http://localhost:3000
```

The Docker setup includes:

- Hot reload for development
- Automatic environment variable injection
- Integrated with backend service

### Running Locally

```bash
# Install dependencies
npm install

# Set environment variables
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev

# Open http://localhost:3000
```

### Available Scripts

```bash
npm run dev      # Start development server with Turbopack
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

## Features

### Player Search

- Search by Riot ID (GameName#TagLine) or Summoner Name
- Multi-region support (EUW, EUNE, NA, etc.)
- Real-time validation with Zod schemas

### Match History

- Display recent ranked games
- Performance metrics (KDA, CS, damage)
- Champion and role information
- Win/loss indicators

### Player Analysis

- Multi-factor player analysis
- Confidence score visualization
- Detection factors breakdown
- Historical detection results

### Matchmaking Analysis

- Teammate vs opponent win rate analysis
- Real-time progress tracking
- Asynchronous analysis execution
- Results visualization and comparison

### Encounter Tracking

- Track players you've played with/against
- Performance statistics
- Recurring player identification

## Architecture Patterns

### Type-Safe API Integration

All API responses are validated at runtime using Zod schemas:

```typescript
import { validatedGet } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";

const player = await validatedGet(PlayerSchema, "/players/search", {
  riot_id: "PlayerName#TAG",
});
```

### Form Validation

Forms use react-hook-form with Zod for type-safe validation:

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const form = useForm({
  resolver: zodResolver(searchSchema),
  defaultValues: { searchValue: "", platform: "eun1" },
});
```

### Data Fetching & Caching

TanStack Query provides automatic caching and background refetching:

```typescript
import { useQuery } from "@tanstack/react-query";

const { data, isLoading } = useQuery({
  queryKey: ["player", riotId],
  queryFn: () => fetchPlayer(riotId),
});
```

## Styling

### shadcn/ui Components

All UI components are from shadcn/ui library and fully customizable:

```bash
# Add new components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add form
```

Components are added to `components/ui/` and can be customized.

### Tailwind CSS

Custom design system with CSS variables defined in `app/globals.css`:

```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    /* ... */
  }
}
```

### Dark Mode

Theme switching powered by next-themes. Toggle available in UI.

## Environment Variables

Environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Docker**: Environment variables are automatically passed from the root `.env` file.

**Local development**: Create `.env.local` file (gitignored).

## Building for Production

```bash
# Build optimized production bundle
npm run build

# Test production build locally
npm run start
```

Production build includes:

- Static optimization for performance
- Automatic code splitting
- Image optimization
- Minification and compression

## Code Quality

### Linting

ESLint with Next.js recommended configuration:

```bash
npm run lint
```

### Type Checking

TypeScript strict mode enabled:

```bash
npx tsc --noEmit
```

### Pre-commit Hooks

Code quality checks run automatically on commit (configured in project root).

## Adding Features

### Add a New Page

1. Create `app/my-page/page.tsx`
2. Export default component
3. Add navigation link in layout

### Add a New API Endpoint

1. Define Zod schema in `lib/schemas.ts`
2. Use `validatedGet`/`validatedPost` in component
3. Wrap with TanStack Query hooks

### Add a New Form

1. Create validation schema in `lib/validations.ts`
2. Use `react-hook-form` with `zodResolver`
3. Use shadcn Form components

### Customize a Component

Edit files in `components/ui/` directly. Changes persist.

## Troubleshooting

### "Module not found" errors

Clear Next.js cache and restart:

```bash
rm -rf .next
npm run dev
```

### Environment variables not loading

- Ensure `NEXT_PUBLIC_` prefix for client-side variables
- Restart dev server after changing `.env.local`
- Check browser console for loaded values

### Hydration errors

- Ensure consistent server/client rendering
- Avoid using browser-only APIs during initial render
- Check for mismatched HTML structure

### TypeScript errors

```bash
# Delete TypeScript cache
rm -rf .next tsconfig.tsbuildinfo
npx tsc --noEmit
```

## Resources

- **Next.js**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com/
- **TanStack Query**: https://tanstack.com/query/latest
- **Zod**: https://zod.dev/
- **react-hook-form**: https://react-hook-form.com/
- **Tailwind CSS**: https://tailwindcss.com/docs

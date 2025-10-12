# Frontend Development Guide

Agent-specific guidance for frontend development. See root `README.md` for project context.

## Tech Stack

- **Next.js 15** with App Router + **React 19**
- **TypeScript** + **Tailwind CSS** + **shadcn/ui**
- **TanStack Query** for data fetching
- **Zod** for schema validation
- **react-hook-form** + **@hookform/resolvers** for forms
- **Axios** for HTTP client

## Directory Structure

```
app/                        # Next.js App Router
  ├── layout.tsx           # Root layout with providers
  ├── page.tsx             # Dashboard (main route)
  └── globals.css          # Global styles + shadcn variables
components/
  ├── ui/                  # shadcn/ui components (auto-generated)
  ├── player-search.tsx    # Player search form
  ├── player-card.tsx      # Player info display
  ├── match-history.tsx    # Match history table
  ├── smurf-detection.tsx  # Smurf analysis
  └── providers.tsx        # Client-side providers
lib/
  ├── utils.ts             # Utilities (cn helper)
  ├── api.ts               # API client with Zod validation
  ├── schemas.ts           # Zod schemas for API types
  └── validations.ts       # Form validation schemas
```

## Development Commands

### Running Frontend

```bash
docker compose up frontend             # Start with Docker
docker compose exec frontend bash      # Access shell

# Or run directly (requires Node.js 24+)
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000

### Building

```bash
docker compose exec frontend npm run build     # Production build
cd frontend && npm run build                   # Local build
```

### Linting & Type Checking

```bash
docker compose exec frontend npm run lint      # ESLint
docker compose exec frontend npx tsc --noEmit  # Type check
```

### Adding shadcn/ui Components

```bash
cd frontend
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add form
```

Components are added to `components/ui/`.

## Code Patterns

### Client Components

Most components need `"use client"` directive:

```tsx
"use client";

import { Card } from "@/components/ui/card";

interface Props {
  data: string;
}

export function MyComponent({ data }: Props) {
  return <Card>{data}</Card>;
}
```

### Zod Schema Validation

Define schemas in `lib/schemas.ts`:

```typescript
import { z } from "zod";

export const PlayerSchema = z.object({
  puuid: z.string(),
  summoner_name: z.string(),
  account_level: z.number().int(),
});

export type Player = z.infer<typeof PlayerSchema>;
```

### Form Handling

Use react-hook-form + Zod:

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const formSchema = z.object({
  searchValue: z.string().min(1, "Required"),
  platform: z.string(),
});

type FormData = z.infer<typeof formSchema>;

export function MyForm() {
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { searchValue: "", platform: "eun1" },
  });

  const onSubmit = (data: FormData) => {
    // Handle submission
  };

  return <Form {...form}>...</Form>;
}
```

### API Integration with TanStack Query

```typescript
import { useQuery, useMutation } from "@tanstack/react-query";
import { validatedGet, validatedPost } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";

// Query
const { data, isLoading } = useQuery({
  queryKey: ["player", riotId],
  queryFn: () =>
    validatedGet(PlayerSchema, "/players/search", { riot_id: riotId }),
});

// Mutation
const { mutate } = useMutation({
  mutationFn: (data) => validatedPost(PlayerSchema, "/players", data),
  onSuccess: (player) => console.log("Created:", player),
});
```

### Styling with shadcn/ui

```tsx
import { cn } from "@/lib/utils";

<div
  className={cn(
    "base-classes",
    condition && "conditional-classes",
    variant === "primary" && "primary-classes",
  )}
/>;
```

## Environment Variables

Must be prefixed with `NEXT_PUBLIC_`:

- `NEXT_PUBLIC_API_URL` - Backend API endpoint (e.g., http://localhost:8000)

Create `.env.local` for local overrides (gitignored):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart dev server after changing env vars.

## Common Tasks

### Add New API Endpoint

1. Define Zod schema in `lib/schemas.ts`
2. Use `validatedGet`/`validatedPost` in component
3. Wrap with TanStack Query hooks

### Add New Form

1. Create validation schema in `lib/validations.ts`
2. Use `react-hook-form` with `zodResolver`
3. Use shadcn Form components

### Add New Page

1. Create `app/my-page/page.tsx`
2. Export default component
3. Add navigation link

## Troubleshooting

### Module not found

```bash
rm -rf .next
npm run dev
```

### Environment variables not working

- Ensure `NEXT_PUBLIC_` prefix
- Restart dev server

### Hydration errors

- Ensure server/client render same content
- Avoid browser-only APIs during render
- Use `suppressHydrationWarning` on `<html>` if needed

## Code Conventions

- Use TypeScript for all files
- Zod schemas for all API types
- shadcn/ui for all UI components
- TanStack Query for all data fetching
- react-hook-form for all forms
- Functional components only

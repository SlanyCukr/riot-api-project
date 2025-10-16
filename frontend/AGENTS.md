# Frontend Agent Instructions

Instructions for AI agents working on frontend code. **See root `AGENTS.md` for Docker/testing/build commands.**

## Documentation Structure

This is the **frontend overview**. For detailed patterns and code generation:

- **`app/AGENTS.md`** - Next.js App Router patterns, page generation, routing
- **`components/AGENTS.md`** - Component generation patterns, shadcn/ui, forms
- **`lib/AGENTS.md`** - API client usage, Zod schema definitions, utilities

## Tech Stack

- **Next.js 15** with App Router + **React 19** (Turbopack in dev)
- **TypeScript** + **Tailwind CSS 4** + **shadcn/ui** (New York style)
- **TanStack Query v5** for data fetching and caching
- **Zod v4** for schema validation
- **react-hook-form** + **@hookform/resolvers** for forms
- **Axios** for HTTP client with interceptors
- **next-themes** for dark mode support
- **sonner** for toast notifications
- **lucide-react** for icons

## Quick Reference

### Directory Structure

```
frontend/
  ├── app/              # Pages & routing → See app/AGENTS.md
  ├── components/       # UI components → See components/AGENTS.md
  ├── lib/              # API & utilities → See lib/AGENTS.md
  ├── hooks/            # Custom React hooks
  ├── types/            # TypeScript types (use lib/schemas.ts instead)
  └── public/           # Static assets
```

### Application Pages

- **`/`** - Home/Landing page
- **`/player-analysis`** - Player analysis & smurf detection
- **`/jobs`** - Background jobs monitoring

### Common Tasks for Agents

#### Generate New Page

→ See `app/AGENTS.md` for complete code templates

1. Create `app/my-page/page.tsx` with appropriate structure
2. Add `"use client"` directive if using hooks/interactivity
3. Add navigation entry in `components/sidebar-nav.tsx`
4. Follow existing page patterns for consistency

#### Generate New Component

→ See `components/AGENTS.md` for component templates

1. Create file in `components/` with descriptive kebab-case name
2. Add `"use client"` directive if using hooks, events, or browser APIs
3. Use shadcn/ui primitives from `components/ui/` (never create custom UI primitives)
4. Define TypeScript interface for props with proper types
5. Implement component following established patterns

#### Add API Endpoint Integration

→ See `lib/AGENTS.md` for API patterns and schema definitions

1. Define or update Zod schema in `lib/schemas.ts`
2. Export inferred TypeScript type from schema
3. Use `validatedGet`/`validatedPost`/`validatedPut`/`validatedDelete` from `lib/api.ts`
4. Wrap with TanStack Query `useQuery` or `useMutation`
5. Always handle both success and error cases in `ApiResponse<T>`

#### Generate Form Component

→ See `components/AGENTS.md` for complete form templates

1. Define validation schema in `lib/validations.ts` using Zod
2. Use `react-hook-form` with `zodResolver` for validation
3. Use shadcn Form components (Form, FormField, FormItem, FormLabel, FormControl, FormMessage)
4. Handle submission with proper error handling and toast notifications

### Code Generation Templates

#### Data Fetching with TanStack Query

**Always use this pattern for API data fetching:**

```tsx
"use client";
import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import { DataSchema } from "@/lib/schemas"; // Import appropriate schema
import { LoadingSkeleton } from "@/components/loading-skeleton";

export function MyComponent({ id }: { id: string }) {
  const { data: result, isLoading } = useQuery({
    queryKey: ["data", id], // Unique key including all params
    queryFn: () => validatedGet(DataSchema, `/api/endpoint/${id}`),
    refetchInterval: 15000, // Optional: for auto-refresh
  });

  if (isLoading) return <LoadingSkeleton />;

  if (!result?.success) {
    return <div>Error: {result?.error.message}</div>;
  }

  const data = result.data; // Type-safe data access
  return <div>{/* Use data here */}</div>;
}
```

#### Form with Validation

**Always use this pattern for forms:**

```tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const formSchema = z.object({
  name: z.string().min(1, "Name is required"),
});

type FormData = z.infer<typeof formSchema>;

export function MyForm() {
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "" },
  });

  const onSubmit = (data: FormData) => {
    // Handle submission
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  );
}
```

#### Adding shadcn/ui Components

**When new UI primitives are needed:**

```bash
npx shadcn@latest add <component-name>
```

Available: button, card, form, input, select, tabs, table, dialog, progress, badge, alert, label, skeleton

### Critical Rules for Agents

1. **Client Directive**: Add `"use client"` at the top of any component using:

   - React hooks (useState, useEffect, etc.)
   - Event handlers (onClick, onChange, etc.)
   - Browser APIs (localStorage, window, document)
   - TanStack Query hooks (useQuery, useMutation)

2. **API Response Handling**: Always handle both success and error states:

   ```tsx
   if (!result?.success) {
     return <div>Error: {result?.error.message}</div>;
   }
   const data = result.data; // Type-safe
   ```

3. **Never Edit `components/ui/`**: These are auto-generated by shadcn. Use CLI to add/update.

4. **Schema-First**: Always define Zod schema in `lib/schemas.ts` before using API endpoints.

5. **Type Safety**: Use `z.infer<typeof Schema>` for TypeScript types from Zod schemas.

6. **Environment Variables**: Must use `NEXT_PUBLIC_` prefix for client-side access:

   ```bash
   # .env.local (gitignored)
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

7. **File Naming**: Use kebab-case for files, PascalCase for component names.

### Important Notes for Agents

**Hot Reload**: Frontend supports hot reload - do NOT restart containers for code changes. Only rebuild when:

- Changing dependencies (package.json, package-lock.json)
- Modifying Dockerfile or docker-compose.yml
- Adding system packages

**No Container Restart Needed**: When you modify `.tsx`, `.ts`, or `.css` files, changes apply immediately. The user does not need to restart anything.

### Common Commands

```bash
cd frontend

# Development
npm run dev           # Start dev server (hot reload enabled)

# Production
npm run build         # Type-check, lint, and build
npm run start         # Start production server

# Maintenance
rm -rf .next          # Clear build cache
npm install           # Install dependencies
```

### Troubleshooting Quick Fixes

**Build cache issues:**

```bash
rm -rf .next && npm run dev
```

**Hot reload not working:**

- Save file and wait a moment
- Check file is in `app/` or `components/`
- Clear `.next` and restart

**Environment variables not working:**

- Use `NEXT_PUBLIC_` prefix
- Restart dev server
- Check `.env.local` exists

**Hydration errors:**

- Use `useEffect` for client-only code
- Avoid browser APIs during initial render
- Check server/client render same content

**TanStack Query not refetching:**

```typescript
queryClient.invalidateQueries({ queryKey: ["myData"] });
```

### Code Conventions for Generated Code

**MUST follow these conventions:**

- **TypeScript only** - No JavaScript files (strict mode enabled)
- **Zod schemas** - All API types defined in `lib/schemas.ts`
- **shadcn/ui only** - Never create custom UI primitives (button, input, card, etc.)
- **TanStack Query** - All data fetching uses useQuery/useMutation (never fetch/axios directly in components)
- **react-hook-form** - All forms use react-hook-form + Zod validation
- **Functional components** - No class components
- **`"use client"`** - Required for hooks/events/browser APIs
- **File naming** - kebab-case for files, PascalCase for component names
- **Error handling** - Always handle both success and error in ApiResponse<T>
- **Loading states** - Use LoadingSkeleton component from `components/loading-skeleton.tsx`

### Key Features

#### Player Analysis

- Player search by Riot ID or summoner name
- Real-time match history from Riot API
- Multi-factor smurf analysis
- Opponent encounter tracking
- Player tracking for auto-updates

#### Background Jobs

- Job configuration & triggering
- Real-time execution monitoring
- System health dashboard
- Auto-refresh every 15 seconds

#### Dark Mode

System-aware dark mode with `next-themes` and theme toggle.

## When to Consult Detailed Docs

- **Generating pages or routing?** → Consult `app/AGENTS.md` for complete patterns
- **Creating components or forms?** → Consult `components/AGENTS.md` for templates
- **Working with APIs or schemas?** → Consult `lib/AGENTS.md` for API client details
- **Troubleshooting?** → Check troubleshooting sections in specific docs

## Quick Checklist Before Code Generation

- [ ] Determined if component needs `"use client"` directive
- [ ] Checked if Zod schema exists in `lib/schemas.ts` (create if needed)
- [ ] Using shadcn/ui components from `components/ui/` (not creating custom UI)
- [ ] Following kebab-case file naming convention
- [ ] Implementing proper error handling for API responses
- [ ] Using TanStack Query for data fetching (not direct axios calls)
- [ ] Adding loading states with LoadingSkeleton
- [ ] Following TypeScript strict mode (proper types, no `any`)

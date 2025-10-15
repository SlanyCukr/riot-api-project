# Component Generation - Agent Instructions

Code generation patterns for React components. **See `frontend/AGENTS.md` for overview.**

## Purpose

This document provides component templates and patterns for AI agents generating React components with shadcn/ui.

## Directory Structure

```
components/
  ├── ui/                        # shadcn/ui components (auto-generated, DO NOT edit manually)
  │   ├── button.tsx
  │   ├── card.tsx
  │   ├── form.tsx
  │   ├── input.tsx
  │   ├── select.tsx
  │   ├── tabs.tsx
  │   ├── table.tsx
  │   ├── dialog.tsx
  │   ├── progress.tsx
  │   ├── badge.tsx
  │   ├── alert.tsx
  │   ├── label.tsx
  │   └── skeleton.tsx
  ├── player-search.tsx          # Player search form with platform select
  ├── player-card.tsx            # Player info display with rank badges
  ├── player-stats.tsx           # Match statistics overview
  ├── match-history.tsx          # Match history table with filters
  ├── smurf-detection.tsx        # Player analysis with factors breakdown
  ├── recent-opponents.tsx       # Recent opponents with encounter tracking
  ├── encounter-stats.tsx        # Detailed encounter statistics
  ├── track-player-button.tsx   # Player tracking toggle button
  ├── job-card.tsx               # Job configuration card with trigger
  ├── job-executions.tsx         # Job execution history table
  ├── system-status.tsx          # System health dashboard
  ├── sidebar-nav.tsx            # Navigation sidebar
  ├── loading-skeleton.tsx       # Loading state skeletons
  ├── theme-toggle.tsx           # Dark mode toggle button
  ├── theme-provider.tsx         # next-themes provider wrapper
  └── providers.tsx              # Client-side providers (QueryClient)
```

## shadcn/ui Components

### Installation

**Add new components:**

```bash
cd frontend
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add form
```

**Currently Installed:**

- button, card, form, input, select
- tabs, table, dialog, progress
- badge, alert, label, skeleton

**Configuration:**

- Style: "New York"
- CSS Variables: Yes
- Tailwind prefix: None
- Location: `components/ui`

### Usage Pattern

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Title</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="default">Click Me</Button>
      </CardContent>
    </Card>
  );
}
```

**DO NOT edit files in `components/ui/` manually** - regenerate with shadcn CLI if changes are needed.

## Component Generation Templates

### Client Component Template (Most Common)

**Use this template for interactive components:**

Most components need `"use client"` directive:

```tsx
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";

interface Props {
  title: string;
  data: string[];
}

export function MyComponent({ title, data }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <Card>
      <h2>{title}</h2>
      {data.map((item) => (
        <button key={item} onClick={() => setSelected(item)}>
          {item}
        </button>
      ))}
    </Card>
  );
}
```

**When to use `"use client"`:**

- Using React hooks (useState, useEffect, etc.)
- Event handlers (onClick, onChange, etc.)
- Browser APIs (localStorage, window, document)
- TanStack Query hooks (useQuery, useMutation)

### Server Component Template (Rare)

**Only use for purely static content without any interactivity:**

```tsx
interface Props {
  title: string;
}

export function StaticComponent({ title }: Props) {
  return <h1>{title}</h1>;
}
```

**No `"use client"` needed** for purely presentational components without hooks/events.

### Component with Data Fetching Template

**Use this pattern for components that fetch their own data:**

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";
import { Card } from "@/components/ui/card";
import { LoadingSkeleton } from "./loading-skeleton";

interface Props {
  puuid: string;
}

export function PlayerCard({ puuid }: Props) {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["player", puuid],
    queryFn: () => validatedGet(PlayerSchema, `/players/${puuid}`),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (!result?.success) return <div>Error: {result?.error.message}</div>;

  const player = result.data;

  return (
    <Card>
      <h2>{player.summoner_name}</h2>
      <p>Level: {player.account_level}</p>
    </Card>
  );
}
```

### Component with Mutation Template

**Use for components that modify data (create, update, delete):**

```tsx
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { validatedPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function TrackPlayerButton({ puuid }: { puuid: string }) {
  const queryClient = useQueryClient();

  const { mutate: track, isPending } = useMutation({
    mutationFn: () => validatedPost(null, `/players/${puuid}/track`, {}),
    onSuccess: (result) => {
      if (result.success) {
        toast.success("Player tracked successfully");
        queryClient.invalidateQueries({ queryKey: ["player", puuid] });
      } else {
        toast.error(result.error.message);
      }
    },
  });

  return (
    <Button onClick={() => track()} disabled={isPending}>
      {isPending ? "Tracking..." : "Track Player"}
    </Button>
  );
}
```

## Form Components

### Form with react-hook-form + Zod

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const formSchema = z.object({
  searchValue: z.string().min(1, "Search value is required"),
  platform: z.string(),
});

type FormData = z.infer<typeof formSchema>;

export function SearchForm() {
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      searchValue: "",
      platform: "eun1",
    },
  });

  const onSubmit = (data: FormData) => {
    console.log(data);
    // Handle form submission
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="searchValue"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Player Name</FormLabel>
              <FormControl>
                <Input placeholder="PlayerName#TAG" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="platform"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Platform</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select platform" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="eun1">EUN1</SelectItem>
                  <SelectItem value="euw1">EUW1</SelectItem>
                  <SelectItem value="na1">NA1</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit">Search</Button>
      </form>
    </Form>
  );
}
```

**Key Points:**

- Use `zodResolver` for validation
- `FormField` wraps each input
- `FormControl` connects to shadcn input
- `FormMessage` shows validation errors
- `form.handleSubmit` handles validation

## Styling Components

### Using cn() Utility

```tsx
import { cn } from "@/lib/utils";

<div
  className={cn(
    "base-classes p-4 rounded-lg",
    isActive && "bg-blue-500",
    isDisabled && "opacity-50 cursor-not-allowed",
    className // Accept className prop for customization
  )}
/>;
```

### Conditional Styling

```tsx
<Button
  variant={isPrimary ? "default" : "outline"}
  size={isLarge ? "lg" : "sm"}
  className={cn(isSpecial && "bg-gradient-to-r from-purple-500 to-pink-500")}
>
  Click Me
</Button>
```

### Dark Mode Aware Styling

```tsx
<div className="bg-white dark:bg-slate-900 text-black dark:text-white">
  Content adapts to theme
</div>
```

## Common Component Patterns

### Loading States

```tsx
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-8 w-2/3" />
    </div>
  );
}
```

### Error States

```tsx
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

export function ErrorMessage({ error }: { error: string }) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{error}</AlertDescription>
    </Alert>
  );
}
```

### Empty States

```tsx
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p>{message}</p>
    </div>
  );
}
```

### Data Tables

```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function DataTable({ data }: { data: Item[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow key={item.id}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.status}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Modals/Dialogs

```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function MyDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Open Dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>Dialog description text</DialogDescription>
        </DialogHeader>
        <div>Dialog content goes here</div>
      </DialogContent>
    </Dialog>
  );
}
```

## Toast Notifications

Uses `sonner` library:

```tsx
import { toast } from "sonner";

// Success
toast.success("Player tracked successfully");

// Error
toast.error("Failed to track player");

// Info
toast.info("Processing request...");

// Promise
toast.promise(apiCall(), {
  loading: "Loading...",
  success: "Success!",
  error: "Error occurred",
});
```

## Icons

Use `lucide-react` for all icons:

```tsx
import { Search, User, Settings, AlertCircle } from "lucide-react";

<Button>
  <Search className="mr-2 h-4 w-4" />
  Search
</Button>;
```

**Advantages:**

- Tree-shakeable (only imports used icons)
- Consistent style across app
- Large icon library
- Customizable size/color with Tailwind

## Component Composition

### Compound Components

```tsx
export function Card({ children }: { children: React.ReactNode }) {
  return <div className="card">{children}</div>;
}

Card.Header = function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="card-header">{children}</div>;
};

Card.Body = function CardBody({ children }: { children: React.ReactNode }) {
  return <div className="card-body">{children}</div>;
};

// Usage
<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
</Card>;
```

### Render Props

```tsx
interface Props {
  data: Item[];
  renderItem: (item: Item) => React.ReactNode;
}

export function List({ data, renderItem }: Props) {
  return <div>{data.map(renderItem)}</div>;
}
```

## Performance Optimization

### React.memo for Expensive Components

```tsx
import { memo } from "react";

export const ExpensiveComponent = memo(function ExpensiveComponent({
  data,
}: {
  data: string;
}) {
  return <div>{data}</div>;
});
```

### Lazy Loading Components

```tsx
import dynamic from "next/dynamic";

const HeavyComponent = dynamic(() => import("./heavy-component"), {
  loading: () => <LoadingSkeleton />,
});
```

## Agent Tasks

### Add New shadcn/ui Component

```bash
npx shadcn@latest add <component-name>
```

### Generate New Custom Component

1. Create file in `components/` (not `components/ui/`)
2. Add `"use client"` if needed
3. Define TypeScript interface for props
4. Implement component logic
5. Export component

### Reuse Component Across Pages

1. Create reusable component in `components/`
2. Import where needed
3. Use props for customization
4. Avoid page-specific logic in shared components

## Troubleshooting

**shadcn component not found:**

- Run `npx shadcn@latest add <component>`
- Check import path uses `@/components/ui/`

**"use client" errors:**

- Add directive to top of file
- Check all dependencies are client-compatible

**Form validation not working:**

- Verify Zod schema matches form structure
- Check `zodResolver` is passed to `useForm`
- Ensure `FormMessage` components are present

**Styling not applying:**

- Check Tailwind classes are correct
- Use `cn()` for conditional classes
- Verify dark mode classes with `dark:` prefix

**Component re-rendering too often:**

- Wrap with `React.memo`
- Check dependencies in useEffect/useMemo/useCallback
- Use TanStack Query caching effectively

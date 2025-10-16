# Library Utilities - Agent Instructions

API client usage, Zod schema definitions, and utilities. **See `frontend/AGENTS.md` for overview.**

## Purpose

This document provides patterns for AI agents working with the API client, defining Zod schemas, and using utility functions.

## Directory Structure

```
lib/
  ├── api.ts              # API client with Zod validation & error handling
  ├── schemas.ts          # Zod schemas for all API types
  ├── validations.ts      # Form validation schemas
  └── utils.ts            # Utility functions (cn helper)
```

## API Client (`lib/api.ts`)

### Overview

Centralized API client with:

- Axios for HTTP requests
- Zod schema validation for type safety
- Error handling and normalization
- Request/response interceptors
- 30-second timeout with auto-retry

### API Response Type

All API functions return `ApiResponse<T>`:

```typescript
type ApiResponse<T> =
  | { success: true; data: T }
  | { success: false; error: ApiError };

interface ApiError {
  message: string;
  status?: number;
  details?: unknown;
}
```

**Always handle both success and error cases:**

```typescript
const result = await validatedGet(PlayerSchema, "/players/123");

if (result.success) {
  const player = result.data; // Type-safe player data
  console.log(player.summoner_name);
} else {
  console.error(result.error.message);
  toast.error(result.error.message);
}
```

### Core API Functions

#### `validatedGet<T>`

```typescript
validatedGet<T>(
  schema: z.ZodSchema<T>,
  url: string,
  params?: Record<string, string | number | boolean>
): Promise<ApiResponse<T>>
```

**Example:**

```typescript
import { validatedGet } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";

const result = await validatedGet(PlayerSchema, "/players/search", {
  riot_id: "PlayerName#TAG",
  platform: "eun1",
});
```

#### `validatedPost<T>`

```typescript
validatedPost<T>(
  schema: z.ZodSchema<T> | null,
  url: string,
  data?: unknown
): Promise<ApiResponse<T>>
```

**Example:**

```typescript
import { validatedPost } from "@/lib/api";

const result = await validatedPost(null, "/jobs/123/trigger", {
  priority: "high",
});
```

#### `validatedPut<T>`

```typescript
validatedPut<T>(
  schema: z.ZodSchema<T> | null,
  url: string,
  data?: unknown
): Promise<ApiResponse<T>>
```

#### `validatedDelete<T>`

```typescript
validatedDelete<T>(
  schema: z.ZodSchema<T> | null,
  url: string
): Promise<ApiResponse<T>>
```

### Specialized API Functions

#### Player Tracking

```typescript
// Track a player
const result = await trackPlayer(puuid);

// Untrack a player
const result = await untrackPlayer(puuid);

// Get tracking status
const result = await getTrackingStatus(puuid);

// Get all tracked players
const result = await getTrackedPlayers();
```

### TanStack Query Integration Patterns

#### Query Pattern (Data Fetching)

**Always use this pattern for GET requests:**

```typescript
import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";

const {
  data: result,
  isLoading,
  error,
} = useQuery({
  queryKey: ["player", puuid],
  queryFn: () => validatedGet(PlayerSchema, `/players/${puuid}`),
  refetchInterval: 15000, // Optional: auto-refresh
});

if (isLoading) return <LoadingSkeleton />;
if (!result?.success) return <ErrorMessage error={result?.error.message} />;

const player = result.data; // Type-safe!
```

#### Mutation Pattern (Data Modification)

**Always use this pattern for POST/PUT/DELETE requests:**

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { validatedPost } from "@/lib/api";
import { toast } from "sonner";

const queryClient = useQueryClient();

const { mutate, isPending } = useMutation({
  mutationFn: (data) => validatedPost(PlayerSchema, "/players", data),
  onSuccess: (result) => {
    if (result.success) {
      toast.success("Player created");
      queryClient.invalidateQueries({ queryKey: ["players"] });
    } else {
      toast.error(result.error.message);
    }
  },
});

// Trigger mutation
mutate({ summoner_name: "Player", platform: "eun1" });
```

### Error Handling

The API client normalizes all errors into `ApiError` format:

```typescript
interface ApiError {
  message: string; // Human-readable error message
  status?: number; // HTTP status code (if available)
  details?: unknown; // Additional error details
}
```

**Error Sources:**

1. **Network errors** - Connection failures, timeouts
2. **HTTP errors** - 4xx, 5xx responses
3. **Validation errors** - Zod schema validation failures
4. **Unknown errors** - Unexpected exceptions

**Error Logging:**

- All errors are logged to console with context
- Validation failures include schema path
- Network errors include request details

### API Configuration

**Base URL:**

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

**Axios Configuration:**

- Timeout: 30 seconds
- Headers: `Content-Type: application/json`
- Retry: 3 attempts for network errors
- Retry delay: 1 second

**Environment Variable:**

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Zod Schemas (`lib/schemas.ts`)

### Overview

Centralized Zod schemas for all API types. Provides:

- Runtime validation
- TypeScript type inference
- API contract enforcement
- Self-documenting types

### Schema Definition Pattern

```typescript
import { z } from "zod";

// Define schema
export const PlayerSchema = z.object({
  puuid: z.string(),
  summoner_name: z.string(),
  account_level: z.number().int(),
  platform: z.string(),
  is_tracked: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

// Infer TypeScript type
export type Player = z.infer<typeof PlayerSchema>;
```

### Available Schemas

#### Player Schemas

```typescript
// Player object
export const PlayerSchema = z.object({
  puuid: z.string(),
  summoner_name: z.string(),
  account_level: z.number().int(),
  platform: z.string(),
  is_tracked: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

// Rank information
export const RankSchema = z.object({
  tier: z.string().nullable(),
  rank: z.string().nullable(),
  league_points: z.number().int().nullable(),
  wins: z.number().int().nullable(),
  losses: z.number().int().nullable(),
});

// Player statistics
export const PlayerStatsSchema = z.object({
  total_matches: z.number().int(),
  wins: z.number().int(),
  losses: z.number().int(),
  win_rate: z.number(),
  avg_kills: z.number(),
  avg_deaths: z.number(),
  avg_assists: z.number(),
  avg_kda: z.number(),
});
```

#### Match Schemas

```typescript
export const MatchSchema = z.object({
  match_id: z.string(),
  game_creation: z.string(),
  game_duration: z.number().int(),
  queue_id: z.number().int(),
  game_mode: z.string(),
  // ... additional fields
});

export const MatchParticipantSchema = z.object({
  puuid: z.string(),
  summoner_name: z.string(),
  champion_name: z.string(),
  kills: z.number().int(),
  deaths: z.number().int(),
  assists: z.number().int(),
  win: z.boolean(),
  // ... additional fields
});
```

#### Player Analysis Schemas

```typescript
export const SmurfDetectionSchema = z.object({
  is_likely_smurf: z.boolean(),
  confidence_score: z.number(),
  factors: z.array(
    z.object({
      factor: z.string(),
      score: z.number(),
      weight: z.number(),
      description: z.string(),
    })
  ),
});
```

#### Job Schemas

```typescript
export const JobSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  description: z.string().nullable(),
  is_enabled: z.boolean(),
  schedule_interval_minutes: z.number().int().nullable(),
  last_run_at: z.string().nullable(),
  next_run_at: z.string().nullable(),
});

export const JobExecutionSchema = z.object({
  id: z.number().int(),
  job_id: z.number().int(),
  status: z.enum(["pending", "running", "completed", "failed"]),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  error_message: z.string().nullable(),
  records_processed: z.number().int().nullable(),
});
```

#### System Status Schema

```typescript
export const SystemStatusSchema = z.object({
  database: z.object({
    status: z.string(),
    connected: z.boolean(),
  }),
  riot_api: z.object({
    status: z.string(),
    available: z.boolean(),
  }),
});
```

### Schema Usage Patterns

#### Type Inference Pattern

**Always infer types from schemas:**

```typescript
import { PlayerSchema } from "@/lib/schemas";
import type { Player } from "@/lib/schemas";

// Option 1: Import inferred type
const player: Player = {
  /* ... */
};

// Option 2: Inline inference
type Player = z.infer<typeof PlayerSchema>;
```

#### Manual Validation Pattern

**Use when validating data outside API client:**

```typescript
import { PlayerSchema } from "@/lib/schemas";

const unknownData = await fetchData();

// Safe parse (returns result object)
const result = PlayerSchema.safeParse(unknownData);
if (result.success) {
  const player = result.data; // Type-safe
} else {
  console.error(result.error); // Validation errors
}

// Parse (throws on error)
try {
  const player = PlayerSchema.parse(unknownData);
} catch (error) {
  console.error(error);
}
```

#### Array Schemas

```typescript
// Single schema
const PlayersSchema = z.array(PlayerSchema);

// Use with API
const result = await validatedGet(z.array(PlayerSchema), "/players");

if (result.success) {
  const players = result.data; // Player[]
}
```

#### Optional Fields

```typescript
export const PartialPlayerSchema = PlayerSchema.partial();
// All fields optional

export const UpdatePlayerSchema = PlayerSchema.pick({
  summoner_name: true,
  is_tracked: true,
});
// Only specific fields
```

### Schema Best Practices

1. **Define once, use everywhere** - Single source of truth
2. **Validate at boundaries** - API responses, form inputs
3. **Use type inference** - `type Player = z.infer<typeof PlayerSchema>`
4. **Add descriptions** - `.describe("Field description")`
5. **Use refinements** - `.refine()` for complex validation
6. **Compose schemas** - Extend and combine existing schemas

### Adding New Schema

1. Define schema in `lib/schemas.ts`
2. Export schema and inferred type
3. Use with API functions
4. Use type in components

```typescript
// lib/schemas.ts
export const MyDataSchema = z.object({
  id: z.number(),
  name: z.string(),
});
export type MyData = z.infer<typeof MyDataSchema>;

// In component
import { validatedGet } from "@/lib/api";
import { MyDataSchema } from "@/lib/schemas";
import type { MyData } from "@/lib/schemas";

const result = await validatedGet(MyDataSchema, "/my-data");
```

## Form Validations (`lib/validations.ts`)

Form-specific validation schemas (currently minimal):

```typescript
import { z } from "zod";

export const searchFormSchema = z.object({
  searchValue: z.string().min(1, "Search value is required"),
  platform: z.string(),
});

export type SearchFormData = z.infer<typeof searchFormSchema>;
```

**Usage in forms:**

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { searchFormSchema } from "@/lib/validations";

const form = useForm({
  resolver: zodResolver(searchFormSchema),
  defaultValues: { searchValue: "", platform: "eun1" },
});
```

## Utilities (`lib/utils.ts`)

### `cn()` - Class Name Utility

Combines Tailwind classes with conditional logic:

```typescript
import { cn } from "@/lib/utils";

// Basic usage
<div className={cn("p-4", "rounded-lg")} />

// Conditional classes
<div className={cn(
  "base-class",
  isActive && "active-class",
  isDisabled && "disabled-class"
)} />

// Override classes
<button className={cn("default-button-styles", props.className)} />
```

**Implementation:**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Benefits:**

- Merges Tailwind classes intelligently
- Handles conditional logic
- Prevents class conflicts
- Type-safe with TypeScript

## Agent Tasks

### Define Schema for New API Endpoint

1. Define Zod schema in `lib/schemas.ts`
2. Export schema and type
3. Use with `validatedGet`/`validatedPost` in component
4. Handle `ApiResponse<T>` success/error states

```typescript
// 1. Schema
export const NewDataSchema = z.object({
  id: z.number(),
  value: z.string(),
});
export type NewData = z.infer<typeof NewDataSchema>;

// 2. Use in component
const result = await validatedGet(NewDataSchema, "/new-data");
```

### Define Form Validation Schema

1. Define schema in `lib/validations.ts`
2. Use with `react-hook-form` and `zodResolver`

```typescript
// 1. Validation schema
export const myFormSchema = z.object({
  email: z.string().email(),
  age: z.number().min(18),
});

// 2. Use in component
const form = useForm({
  resolver: zodResolver(myFormSchema),
});
```

### Debug Schema Validation

```typescript
const result = PlayerSchema.safeParse(data);
if (!result.success) {
  console.log("Validation errors:", result.error.flatten());
}
```

### Extend or Modify Schema

```typescript
import { PlayerSchema } from "@/lib/schemas";

const ExtendedPlayerSchema = PlayerSchema.extend({
  extra_field: z.string(),
});
```

## Troubleshooting

**Validation failing unexpectedly:**

- Check API response format matches schema
- Use `.safeParse()` to inspect errors
- Verify field types (string vs number)
- Check for null/undefined handling

**TypeScript errors with inferred types:**

- Ensure schema is exported
- Import type with `import type { Player }`
- Check schema definition matches usage

**API timeout errors:**

- Default timeout is 30 seconds
- Check backend response time
- Consider increasing timeout for slow endpoints

**Environment variable not accessible:**

- Must use `NEXT_PUBLIC_` prefix
- Restart dev server after changes
- Check `.env.local` exists

**Zod version mismatch:**

- Project uses Zod v4
- Check package.json for conflicts
- Run `npm install` to resolve

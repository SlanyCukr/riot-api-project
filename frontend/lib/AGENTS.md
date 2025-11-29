# Tech Stack

- **Axios v1.12.2** for HTTP client
- **Zod v4.1.12** for runtime validation and type safety
- **TanStack Query v5.90.2** for data fetching and caching
- **TypeScript 5** with strict mode
- **next-themes v0.4.6** for dark mode support

# Project Structure

```
lib/
├── core/                      # Core utilities
│   ├── api.ts                # API client with Zod validation
│   ├── schemas.ts            # Zod schemas for API types
│   └── validations.ts        # Form validation schemas
└── utils.ts                  # Generic utilities (cn helper)
```

## API Client with Zod Validation

### Base API Client

```typescript
// lib/core/api.ts
import axios, { AxiosError } from 'axios';
import { z } from 'zod';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Enhanced error type
export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: unknown;
}

// Enhanced response type
export type ApiResponse<T> = { success: true; data: T } | { success: false; error: ApiError };

// Request interceptor for logging
api.interceptors.request.use(
  config => {
    // Only log in development if needed - comment out to reduce console noise
    // console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    // Don't log 404 player-not-found as errors (expected behavior)
    const status = error.response?.status;
    if (status !== 404) {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);
```

### Type-Safe API Methods

```typescript
// lib/core/api.ts (continued)
// Helper to format errors
function formatError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    // Handle 404 player not found as expected case
    if (status === 404 && typeof detail === 'string') {
      return {
        message: detail,
        code: 'PLAYER_NOT_FOUND',
        status: 404,
        details: error.response?.data,
      };
    }

    return {
      message: error.response?.data?.detail || error.message,
      code: error.code,
      status: error.response?.status,
      details: error.response?.data,
    };
  }

  if (error instanceof z.ZodError) {
    return {
      message: 'Data validation failed',
      code: 'VALIDATION_ERROR',
      details: error.issues,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      code: 'UNKNOWN_ERROR',
    };
  }

  return {
    message: 'An unknown error occurred',
    code: 'UNKNOWN_ERROR',
  };
}

// Generic validated GET request
export async function validatedGet<T>(
  schema: z.ZodType<T>,
  url: string,
  params?: Record<string, unknown>
): Promise<ApiResponse<T>> {
  try {
    const response = await api.get(url, { params });
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      // FAIL LOUDLY: Log validation errors with full details
      console.error('🔴 ZOD VALIDATION FAILED 🔴');
      console.error('URL:', url);
      console.error('Response data:', response.data);
      console.error('Validation errors:', parsed.error.issues);

      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

export async function validatedPost<T>(
  schema: z.ZodType<T>,
  url: string,
  data?: unknown
): Promise<ApiResponse<T>> {
  try {
    const response = await api.post(url, data);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      // FAIL LOUDLY: Log validation errors with full details
      console.error('🔴 ZOD VALIDATION FAILED 🔴');
      console.error('URL:', url);
      console.error('Response data:', response.data);
      console.error('Validation errors:', parsed.error.issues);

      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

export async function validatedPut<T>(
  schema: z.ZodType<T>,
  url: string,
  data?: unknown
): Promise<ApiResponse<T>> {
  try {
    const response = await api.put(url, data);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      // FAIL LOUDLY: Log validation errors with full details
      console.error('🔴 ZOD VALIDATION FAILED 🔴');
      console.error('URL:', url);
      console.error('Response data:', response.data);
      console.error('Validation errors:', parsed.error.issues);

      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

export async function validatedDelete<T>(
  schema: z.ZodType<T>,
  url: string
): Promise<ApiResponse<T>> {
  try {
    const response = await api.delete(url);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      // FAIL LOUDLY: Log validation errors with full details
      console.error('🔴 ZOD VALIDATION FAILED 🔴');
      console.error('URL:', url);
      console.error('Response data:', response.data);
      console.error('Validation errors:', parsed.error.issues);

      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}
```

## Zod Schemas for API Types

### Player Schema

```typescript
// lib/core/schemas.ts
import { z } from 'zod';

// Player schemas
export const PlayerSchema = z.object({
  id: z.string(),
  game_name: z.string(),
  tag_line: z.string(),
  summoner_name: z.string().optional(),
  region: z.string(),
  rank: z
    .object({
      tier: z.string(),
      rank: z.string(),
      league_points: z.number(),
      wins: z.number(),
      losses: z.number(),
    })
    .optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const PlayerSuggestionSchema = z.object({
  id: z.string(),
  game_name: z.string(),
  tag_line: z.string(),
  summoner_name: z.string().optional(),
  region: z.string(),
});

// API Response wrappers
export const ApiResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    message: z.string().optional(),
    success: z.boolean(),
  });

export const PlayerResponseSchema = ApiResponseSchema(PlayerSchema);
export const PlayersResponseSchema = ApiResponseSchema(z.array(PlayerSchema));
export const PlayerSuggestionsResponseSchema = ApiResponseSchema(z.array(PlayerSuggestionSchema));

// Type inference
export type Player = z.infer<typeof PlayerSchema>;
export type PlayerSuggestion = z.infer<typeof PlayerSuggestionSchema>;
export type PlayerResponse = z.infer<typeof PlayerResponseSchema>;
export type PlayersResponse = z.infer<typeof PlayersResponseSchema>;
export type PlayerSuggestionsResponse = z.infer<typeof PlayerSuggestionsResponseSchema>;
```

### Match Schema

```typescript
// lib/core/schemas.ts (continued)
export const MatchSchema = z.object({
  id: z.string(),
  game_id: z.string(),
  player_id: z.string(),
  champion_name: z.string(),
  role: z.string(),
  kills: z.number(),
  deaths: z.number(),
  assists: z.number(),
  creep_score: z.number(),
  damage_dealt: z.number(),
  damage_taken: z.number(),
  game_duration: z.number(),
  win: z.boolean(),
  game_mode: z.string(),
  created_at: z.string().datetime(),
});

export const MatchesResponseSchema = ApiResponseSchema(z.array(MatchSchema));
export type Match = z.infer<typeof MatchSchema>;
export type MatchesResponse = z.infer<typeof MatchesResponseSchema>;
```

### Job Schema

```typescript
// lib/core/schemas.ts (continued)
export const JobSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  cron_expression: z.string(),
  is_active: z.boolean(),
  last_run: z.string().datetime().optional(),
  next_run: z.string().datetime(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const JobExecutionSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  status: z.enum(['pending', 'running', 'completed', 'failed']),
  started_at: z.string().datetime(),
  completed_at: z.string().datetime().optional(),
  error_message: z.string().optional(),
  result: z.record(z.any()).optional(),
});

export const JobsResponseSchema = ApiResponseSchema(z.array(JobSchema));
export const JobExecutionsResponseSchema = ApiResponseSchema(z.array(JobExecutionSchema));

export type Job = z.infer<typeof JobSchema>;
export type JobExecution = z.infer<typeof JobExecutionSchema>;
export type JobsResponse = z.infer<typeof JobsResponseSchema>;
export type JobExecutionsResponse = z.infer<typeof JobExecutionsResponseSchema>;
```

## Form Validation Schemas

### Authentication

```typescript
// lib/core/validations.ts
import { z } from 'zod';

export const signInSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type SignInForm = z.infer<typeof signInSchema>;
```

### Player Search

```typescript
// lib/core/validations.ts (continued)
export const playerSearchSchema = z.object({
  searchValue: z.string().min(3, 'Search term must be at least 3 characters'),
  platform: z.enum([
    'eun1',
    'euw1',
    'na1',
    'kr',
    'jp1',
    'br1',
    'la1',
    'la2',
    'oc1',
    'tr1',
    'ru',
    'ph2',
    'sg2',
    'th2',
    'tw2',
    'vn2',
  ]),
});

export type PlayerSearchForm = z.infer<typeof playerSearchSchema>;
```

### Matchmaking Analysis

```typescript
// lib/core/validations.ts (continued)
export const matchmakingAnalysisSchema = z.object({
  player_id: z.string().min(1, 'Please select a player'),
  teammate_1_id: z.string().optional(),
  teammate_2_id: z.string().optional(),
  teammate_3_id: z.string().optional(),
  teammate_4_id: z.string().optional(),
  opponent_1_id: z.string().optional(),
  opponent_2_id: z.string().optional(),
  opponent_3_id: z.string().optional(),
  opponent_4_id: z.string().optional(),
  opponent_5_id: z.string().optional(),
  analysis_type: z.enum(['win_rate', 'performance', 'full']),
});

export type MatchmakingAnalysisForm = z.infer<typeof matchmakingAnalysisSchema>;
```

## Usage Examples

### Data Fetching with Validation

```typescript
// hooks/use-player.ts
'use client';

import { useQuery } from '@tanstack/react-query';
import { validatedGet } from '@/lib/core/api';
import { PlayerResponseSchema, PlayerSuggestionsResponseSchema } from '@/lib/core/schemas';
import { PlayerSearchForm } from '@/lib/core/validations';

export function usePlayer(playerId: string) {
  return useQuery({
    queryKey: ['player', playerId],
    queryFn: () => validatedGet(PlayerResponseSchema, `/players/${playerId}`),
    enabled: !!playerId,
  });
}

export function usePlayerSuggestions(formData: PlayerSearchForm) {
  const { searchValue, platform } = formData;

  return useQuery({
    queryKey: ['player-suggestions', searchValue, platform],
    queryFn: () =>
      validatedGet(
        PlayerSuggestionsResponseSchema,
        `/players/suggestions?q=${encodeURIComponent(searchValue)}&platform=${platform}&limit=10`
      ),
    enabled: searchValue.length >= 3,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
```

### Mutations with Validation

```typescript
// hooks/use-jobs.ts
'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { validatedPost, validatedDelete } from '@/lib/core/api';
import { JobResponseSchema, JobsResponseSchema } from '@/lib/core/schemas';
import { toast } from 'sonner';

export function useCreateJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobData: any) => validatedPost(JobResponseSchema, '/jobs', jobData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create job: ${error.message}`);
    },
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => validatedDelete(JobResponseSchema, `/jobs/${jobId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete job: ${error.message}`);
    },
  });
}
```

### Form Integration

```typescript
// components/PlayerSearchForm.tsx
"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { usePlayerSuggestions } from "@/hooks/use-player"
import { playerSearchSchema, type PlayerSearchForm } from "@/lib/core/validations"

export function PlayerSearchForm() {
  const form = useForm<PlayerSearchForm>({
    resolver: zodResolver(playerSearchSchema),
    defaultValues: {
      searchValue: "",
      platform: "eun1",
    },
  })

  const { data, isLoading } = usePlayerSuggestions(form.watch())

  const onSubmit = (data: PlayerSearchForm) => {
    console.log("Search for:", data)
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label>Player Search</label>
        <input {...form.register("searchValue")} />
        {form.formState.errors.searchValue && (
          <span>{form.formState.errors.searchValue.message}</span>
        )}
      </div>

      <div>
        <label>Platform</label>
        <select {...form.register("platform")}>
          <option value="eun1">EUNE</option>
          <option value="euw1">EUW</option>
          <option value="na1">NA</option>
        </select>
      </div>

      <button type="submit" disabled={isLoading}>
        Search
      </button>
    </form>
  )
}
```

## Utility Functions

### Class Name Helper

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

## Best Practices

### Always Use Schema Validation

✅ **Correct:** Validate all API responses

```typescript
const player = await validatedGet(PlayerResponseSchema, '/players/123');
```

❌ **Wrong:** Direct axios usage without validation

```typescript
const response = await api.get('/players/123');
const player = response.data; // No validation!
```

### Handle Both Success and Error Cases

✅ **Correct:** Comprehensive error handling

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ["player", id],
  queryFn: () => validatedGet(PlayerResponseSchema, `/players/${id}`),
})

if (isLoading) return <LoadingSkeleton />
if (error) return <ErrorMessage error={error} />
if (!data) return <NotFoundMessage />
return <PlayerCard player={data.data} />
```

### Use Type Inference

✅ **Correct:** Infer types from schemas

```typescript
import { Player, PlayerSchema } from '@/lib/core/schemas';

const player: Player = {
  id: '123',
  game_name: 'PlayerName',
  // ... TypeScript will validate this structure
};
```

## Commands

- **API call**: `validatedGet(Schema, "/endpoint")`
- **Mutation**: `validatedPost(Schema, "/endpoint", data)`
- **Validation**: `Schema.safeParse(data)`
- **Types**: `type MyType = z.infer<typeof MySchema>`
- **Add schema**: Define in `lib/core/schemas.ts`
- **Add validation**: Define in `lib/core/validations.ts`

## Do Not

❌ **Don't use direct axios calls in components** - Always use validated methods ❌ **Skip error
handling in API responses** - Handle loading, error, and success states ❌ **Create TypeScript types
without Zod schemas** - Use schema inference for type safety ❌ **Use environment variables without
NEXT*PUBLIC* prefix** - Only public vars work in browser ❌ **Forget to invalidate queries after
mutations** - Keep cache in sync ❌ **Mix validation and API schemas** - Keep separate concerns
clean ❌ **Ignore runtime validation errors** - Schema validation prevents runtime bugs

# Tech Stack
- Axios + Zod v4 for validation
- TanStack Query v5 for data fetching
- TypeScript strict mode
- next-themes for dark mode

# Project Structure
- `api.ts` - API client with Zod validation
- `schemas.ts` - Zod schemas for all API types
- `validations.ts` - Form validation schemas
- `utils.ts` - Utility functions (cn helper)

# Commands
- API call: `validatedGet(Schema, "/endpoint")`
- Mutation: `validatedPost(Schema, "/endpoint", data)`
- Validation: `Schema.safeParse(data)`
- Types: `type MyType = z.infer<typeof MySchema>`

# Code Style
- Always handle both success and error cases
- Use Zod schemas for runtime validation
- Infer TypeScript types from schemas
- Use TanStack Query for all API calls
- Follow ApiResponse<T> pattern
- Add validation schemas before using endpoints

# Do Not
- Use direct axios calls in components
- Skip error handling in API responses
- Create TypeScript types without Zod schemas
- Use environment variables without NEXT_PUBLIC_ prefix
- Forget to invalidate queries after mutations
- Mix validation and API schemas

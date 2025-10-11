# Frontend Development Guide

## Technology Stack

- **React 19** with TypeScript
- **Tailwind CSS** for styling
- **Vite** for build tooling and dev server
- **TanStack Query** for data fetching and caching
- **Axios** for HTTP client

See `package.json` for complete dependencies and versions.

## Project Structure

- **`src/components/`** - Reusable UI components (PlayerSearch, PlayerCard, MatchHistory, etc.)
- **`src/pages/`** - Page-level route components
- **`src/hooks/`** - Custom React hooks for shared logic
- **`src/lib/`** - Utilities and helper functions
- **`src/types/`** - TypeScript type definitions and interfaces
- **`src/services/`** - API client and backend integration

## Development Guidelines

### Component Patterns

- Use **functional components** with TypeScript interfaces
- Define prop types with `interface` or `type`
- Follow existing naming conventions (PascalCase for components)
- Keep components focused and composable
- Extract reusable logic into custom hooks

Example:

```tsx
interface PlayerCardProps {
  player: Player;
  onSelect: (id: string) => void;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({ player, onSelect }) => {
  // Component implementation
};
```

### API Integration

- **TanStack Query** for all data fetching (queries and mutations)
- Centralized API client in `src/services/api.ts`
- Implement proper loading, error, and empty states
- Leverage TanStack Query's built-in caching and refetching

Example:

```tsx
const { data, isLoading, error } = useQuery({
  queryKey: ["player", riotId],
  queryFn: () => fetchPlayer(riotId),
});
```

### Styling

- **Tailwind CSS** utility-first approach
- Use Tailwind classes directly in JSX
- Follow responsive design patterns (`sm:`, `md:`, `lg:` breakpoints)
- Maintain consistent spacing and color schemes
- Extract repeated utility combinations into components when needed

### Accessibility

- Use semantic HTML elements (`<button>`, `<nav>`, `<main>`)
- Include ARIA labels where needed
- Ensure keyboard navigation works properly
- Test with screen readers when possible

## Performance Optimization

- **Code splitting**: Use React.lazy() and Suspense for route-based splitting
- **Memoization**: Use `React.memo`, `useCallback`, `useMemo` judiciously
- **Bundle optimization**: Vite handles tree shaking automatically
- **Image optimization**: Use appropriate formats and lazy loading
- **TanStack Query**: Leverages caching to reduce unnecessary API calls

## Development Workflow

### Running Locally

```bash
# Start frontend with hot reload
docker compose up frontend

# Access frontend shell
docker compose exec frontend bash

# Install new dependencies
docker compose exec frontend npm install <package>
```

### Building

```bash
# Production build
docker compose exec frontend npm run build

# Preview production build
docker compose exec frontend npm run preview
```

### Linting & Formatting

```bash
# Run ESLint
docker compose exec frontend npm run lint

# Fix linting issues
docker compose exec frontend npm run lint:fix
```

## Environment Configuration

Frontend environment variables (prefix with `VITE_`):

- **`VITE_API_URL`** - Backend API endpoint (e.g., `http://localhost:8000`)
- **`VITE_ENVIRONMENT`** - Environment name (development/production)

Create `.env.local` for local overrides (not committed to git).

## Testing

Testing framework planned using **React Testing Library** and **Vitest**.

- Unit tests for components and hooks
- Integration tests with mocked API responses
- Follow Arrange-Act-Assert pattern

## Security Best Practices

- **Never expose secrets** in client-side code
- Use environment variables for configuration
- **Input validation**: Validate and sanitize user inputs
- **XSS prevention**: React handles this by default, but be careful with `dangerouslySetInnerHTML`
- **HTTPS only** in production
- Implement proper CORS handling (configured on backend)

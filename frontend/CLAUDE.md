# Frontend Development Guide

## Technology Stack

React 19.2.0 + TypeScript + Tailwind CSS, built with Vite. See `package.json` for complete dependencies.

## Project Structure

- **src/components/**: UI components (PlayerSearch, PlayerCard, MatchHistory, etc.)
- **src/pages/**: Page-level components
- **src/hooks/**: Custom React hooks
- **src/lib/**: Utilities and helpers
- **src/types/**: TypeScript definitions

## Development Guidelines

### Code Style & Components

- Use functional components with TypeScript interfaces
- Follow existing patterns and naming conventions
- ESLint + Prettier for formatting

### API Integration

- Use TanStack Query + Axios for data fetching
- Centralized API client in `src/services/`
- Implement proper loading/error states and caching

## Performance

- Implement route-based code splitting and lazy loading
- Use React.memo, useCallback, useMemo for optimization
- Optimize bundle size with tree shaking

## Styling

- Tailwind CSS utility-first approach
- Responsive design patterns
- Accessibility: ARIA labels, semantic HTML, keyboard navigation

## Development

### Commands

```bash
# Start frontend with hot reload
docker-compose up frontend

# Build for production
docker-compose exec frontend npm run build

# Frontend linting (inside container)
docker-compose exec frontend npm run lint
```

### Environment

- `VITE_API_URL`: Backend API endpoint
- `VITE_ENVIRONMENT`: Development/production environment

## Testing

Testing framework planned (React Testing Library). Mock API responses for integration tests.

## Security

- Never expose sensitive data in client-side code
- Use environment variables for configuration
- Implement proper input validation and XSS prevention

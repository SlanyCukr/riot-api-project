# Frontend Development Guide

This file provides guidance for working with the React TypeScript frontend.

## Technology Stack

- **Framework**: React 19.2.0 with TypeScript
- **Styling**: Tailwind CSS with class-variance-authority and clsx
- **Build Tool**: Vite
- **Package Manager**: npm
- **Routing**: React Router DOM
- **State Management**: TanStack Query (React Query)
- **Form Handling**: React Hook Form with Zod validation
- **HTTP Client**: Axios
- **UI Components**: Radix UI primitives, Lucide React icons
- **Linting**: ESLint with TypeScript
- **Testing**: React Testing Library (planned)

## Project Structure

- **src/components/**: Reusable UI components
  - `PlayerSearch.tsx`: Player search form component
  - `PlayerCard.tsx`: Player information display
  - `MatchHistory.tsx`: Match history list component
  - `SmurfDetection.tsx`: Smurf detection results display
  - `LoadingSpinner.tsx`: Loading state component
  - `ErrorMessage.tsx`: Error display component
- **src/pages/**: Page-level components
- **src/hooks/**: Custom React hooks
- **src/lib/**: Utility libraries and helpers
- **src/types/**: TypeScript type definitions
- **src/utils/**: Utility functions

## Development Guidelines

### Code Style
- ESLint with TypeScript
- Prettier formatting
- Follow existing patterns and naming conventions
- Use functional components with hooks

### Component Structure
- Prefer function components over class components
- Use TypeScript interfaces for props
- Implement proper error boundaries
- Follow React best practices for state management

### Testing (Planned)
- React Testing Library for component tests
- Mock API responses in tests
- Integration tests for user flows

## API Integration

### Service Layer
- Centralized API client in `src/services/`
- Proper error handling and loading states
- Request/response interception
- Authentication handling

### Data Fetching
- Uses TanStack Query (React Query) for server state management
- Axios for HTTP requests to backend API
- Implement proper caching strategies with React Query
- Handle loading and error states gracefully
- Use optimistic updates where appropriate

## Performance Considerations

### Code Splitting
- Implement route-based code splitting
- Lazy load components when possible
- Use dynamic imports for large dependencies

### Optimization
- Implement React.memo for expensive components
- Use useCallback and useMemo appropriately
- Optimize bundle size with tree shaking
- Implement proper image optimization

## Styling Guidelines

### Tailwind CSS
- Use utility-first approach
- Create custom components for repeated patterns
- Maintain consistent spacing and color scheme
- Use responsive design patterns

### Accessibility
- Implement proper ARIA labels
- Ensure keyboard navigation support
- Use semantic HTML elements
- Test with screen readers

## Testing and Code Quality

```bash
# Frontend linting (inside container)
docker-compose exec frontend npm run lint

# Run tests (when implemented)
docker-compose exec frontend npm test
```

## Development Workflow

### Hot Reload
The development environment supports hot reload:
```bash
# Start frontend with hot reload
docker-compose up frontend
```

### Build Process
```bash
# Build for production
docker-compose exec frontend npm run build

# Preview production build
docker-compose exec frontend npm run preview
```

## Environment Configuration

### API Configuration
- Backend API URL configured via environment
- Proper CORS handling
- Development vs production API endpoints

### Required Environment Variables
- `VITE_API_URL`: Backend API endpoint
- `VITE_ENVIRONMENT`: Development/production environment

## Security Considerations

- Never expose sensitive data in client-side code
- Use environment variables for configuration
- Implement proper input validation
- Sanitize user inputs to prevent XSS attacks
- Use HTTPS in production
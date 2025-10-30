# Auth Feature

## Purpose

Provides JWT-based authentication for the application with protected routes, login/logout
functionality, and user session management.

## Architecture

**Authentication Flow:**

```
User → Sign In Form → API → JWT Token → LocalStorage → Auth Context → Protected Routes
```

## Key Components

### Auth Context (`context/AuthContext.tsx`)

**AuthProvider** - React context provider for authentication state

**Responsibilities:**

- Manages authentication state (user, token, loading)
- Provides login/logout functions
- Validates JWT token on app load
- Persists token to localStorage

**Hook:**

```typescript
const { user, token, isLoading, login, logout } = useAuth();
```

**State:**

- `user: { email: string } | null` - Current user info
- `token: string | null` - JWT token
- `isLoading: boolean` - Loading state during token validation

**Methods:**

- `login(email: string, password: string)` - Authenticate user
- `logout()` - Clear session and redirect to sign-in

### Protected Route (`components/ProtectedRoute.tsx`)

**ProtectedRoute** - Higher-order component for route protection

**Usage:**

```typescript
<ProtectedRoute>
  <YourComponent />
</ProtectedRoute>
```

**Behavior:**

- Shows loading skeleton while validating token
- Redirects to `/sign-in` if not authenticated
- Renders children if authenticated

### Sign In Form (`components/SignInForm.tsx`)

**SignInForm** - Login form with validation

**Features:**

- Email and password inputs
- Client-side validation with react-hook-form + Zod
- Error handling and display
- Loading state during authentication

**Validation Schema:**

```typescript
{
  email: string (valid email format),
  password: string (min 8 characters)
}
```

### Types (`types.ts`)

**TypeScript definitions:**

- `User` - User object shape
- `AuthContextType` - Context value type
- `LoginCredentials` - Login form data

## Usage Examples

### Protecting a Page

```typescript
// app/dashboard/page.tsx
import { ProtectedRoute } from '@/features/auth';

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <div>Protected Dashboard Content</div>
    </ProtectedRoute>
  );
}
```

### Using Auth Context

```typescript
'use client';

import { useAuth } from '@/features/auth';

export function UserProfile() {
  const { user, logout } = useAuth();

  return (
    <div>
      <p>Logged in as: {user?.email}</p>
      <button onClick={logout}>Sign Out</button>
    </div>
  );
}
```

### Checking Authentication Status

```typescript
'use client';

import { useAuth } from '@/features/auth';

export function ConditionalComponent() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <div>Loading...</div>;

  if (!user) {
    return <div>Please sign in to continue</div>;
  }

  return <div>Welcome, {user.email}!</div>;
}
```

## API Integration

### Login Endpoint

**POST** `/api/v1/auth/login`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Token Validation

**GET** `/api/v1/auth/me`

**Headers:**

```
Authorization: Bearer <token>
```

**Response:**

```json
{
  "email": "user@example.com"
}
```

## Token Management

### Storage

JWT token stored in **localStorage**:

- Key: `auth_token`
- Value: JWT string
- Cleared on logout or token expiration

### Validation

Token validation on app load:

1. Check localStorage for `auth_token`
2. Call `/api/v1/auth/me` to validate
3. If valid, set user state
4. If invalid, clear token and redirect to sign-in

### Expiration

- Token expiration handled by backend
- 401 responses trigger automatic logout
- User redirected to sign-in page

## Public Routes

Routes accessible without authentication:

- `/sign-in` - Login page
- `/license` - License information
- `/privacy-policy` - Privacy policy

## Security Considerations

### Current Implementation

✅ **Implemented:**

- JWT token authentication
- Protected routes via HOC
- Token validation on app load
- Automatic logout on 401 errors
- Client-side form validation

⚠️ **Limitations:**

- Token stored in localStorage (XSS vulnerable)
- No refresh token mechanism
- No token expiration handling on client
- No CSRF protection

### Recommended Improvements

See `docs/tasks/technical-debt.md` and `docs/tasks/auth.md` for planned security enhancements:

- HTTP-only cookies for token storage
- Refresh token implementation
- Token revocation
- Rate limiting on login endpoint
- Account lockout after failed attempts

## Related Features

- **Settings** - User can configure API keys and preferences
- **Jobs** - Background jobs require authentication to configure
- All protected routes depend on this feature

## Testing

### Manual Testing

1. **Login Flow:**

   ```bash
   # Navigate to sign-in page
   # Enter valid credentials
   # Verify redirect to dashboard
   # Check localStorage for auth_token
   ```

2. **Protected Route:**

   ```bash
   # Clear localStorage auth_token
   # Navigate to /dashboard
   # Verify redirect to /sign-in
   ```

3. **Logout:**
   ```bash
   # Click logout button
   # Verify localStorage cleared
   # Verify redirect to /sign-in
   ```

### Test Users

See backend documentation for creating test users with `backend/scripts/manage_admin.py`.

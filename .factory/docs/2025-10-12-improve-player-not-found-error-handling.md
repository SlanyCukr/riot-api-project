# Improve Player Not Found Error Handling

## Problem Analysis
Currently, when a player is not found:
1. Backend returns HTTP 404 with generic error message in the `detail` field
2. Frontend logs "API Error: Object" to console (from axios interceptor)
3. Frontend shows a generic error message to the user
4. Console shows "Failed to load resource: 404" error

This is normal behavior for non-existent players, but the error handling doesn't distinguish between expected "player not found" cases and actual errors.

## Solution

### 1. Backend: Add specific error codes in response (Optional Enhancement)
**File**: `backend/app/api/players.py`

While the current backend behavior is acceptable (returning 404 with "Player not found: {name}"), we could enhance it by:
- Catching the specific `ValueError` from the service layer
- Returning a structured error with a distinguishable message pattern

Example:
```python
except ValueError as e:
    # Player not found - expected case
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    # Unexpected error
    logger.error("Unexpected error in player search", error=str(e))
    raise HTTPException(status_code=500, detail="An unexpected error occurred while searching for player")
```

### 2. Frontend: Improve error detection and display
**File**: `frontend/lib/api.ts`

Update `formatError` to detect 404 player-not-found cases:
```typescript
function formatError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    // Handle 404 player not found as expected case
    if (status === 404 && typeof detail === 'string') {
      return {
        message: detail, // Keep the server message like "Player not found: name"
        code: 'PLAYER_NOT_FOUND',
        status: 404,
        details: error.response?.data,
      };
    }

    // Other errors...
  }
  // Rest of error handling...
}
```

Update the response interceptor to NOT log 404 errors as errors:
```typescript
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Don't log 404 player-not-found as errors
    const status = error.response?.status;
    if (status !== 404) {
      console.error("API Error:", error.response?.data || error.message);
    }
    return Promise.reject(error);
  },
);
```

### 3. Frontend: Display user-friendly message
**File**: `frontend/components/player-search.tsx`

The component already shows the error message to users. We can improve the display by checking for the error code:

```typescript
{error && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      {error instanceof Error && error.message.includes("Player not found")
        ? error.message // Show the specific "Player not found: name" message
        : "Failed to search for player. Please check your input and try again."}
    </AlertDescription>
  </Alert>
)}
```

Or create a more sophisticated error display that checks the error code from the API response.

## Changes Summary

1. **frontend/lib/api.ts**:
   - Add `PLAYER_NOT_FOUND` error code for 404 responses
   - Remove console error logging for 404 status codes (player not found is expected)

2. **frontend/components/player-search.tsx**:
   - Improve error message display to handle player-not-found cases more gracefully
   - Show the actual backend error message which includes the player name

3. **Optional - backend/app/api/players.py**:
   - Better exception handling to distinguish between expected ValueError (player not found) and unexpected errors

## Expected Outcome

- No console errors for player-not-found cases
- Clear, user-friendly message displayed: "Player not found: PlayerName"
- Console errors only for actual unexpected errors
- Better debugging experience by reducing noise in console

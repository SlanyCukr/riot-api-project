import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Decode JWT token payload without verification.
 * This is used for quick checks like expiration. Full verification happens on the backend.
 *
 * @param token - JWT token string
 * @returns Decoded payload or null if invalid
 */
function decodeJWT(token: string): { exp?: number } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }

    // Decode the payload (second part)
    const payload = JSON.parse(
      Buffer.from(parts[1], "base64url").toString("utf-8"),
    );
    return payload;
  } catch {
    return null;
  }
}

/**
 * Check if JWT token is expired.
 *
 * @param token - JWT token string
 * @returns true if token is expired or invalid, false otherwise
 */
function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token);

  if (!payload || !payload.exp) {
    return true; // Invalid token structure
  }

  // Check if token is expired (exp is in seconds, Date.now() is in ms)
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow sign-in page
  if (pathname === "/sign-in") {
    return NextResponse.next();
  }

  // Check for auth token in cookies
  const token = request.cookies.get("auth_token")?.value;

  // If no token, redirect to sign-in
  if (!token) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  // Validate token structure and expiration
  if (isTokenExpired(token)) {
    // Token is expired or invalid, redirect to sign-in
    const response = NextResponse.redirect(new URL("/sign-in", request.url));

    // Clear the invalid token cookie
    response.cookies.delete("auth_token");

    return response;
  }

  // Token exists and is valid, allow the request to proceed
  return NextResponse.next();
}

// Configure which paths to run middleware on
export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - /sign-in (the login page)
     * - /api routes (if any)
     * - /_next/static (static files)
     * - /_next/image (image optimization files)
     * - /favicon.ico, /logo.png (metadata files)
     */
    "/((?!sign-in|api|_next/static|_next/image|favicon.ico|logo.png).*)",
  ],
};

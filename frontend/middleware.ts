import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow sign-in page
  if (pathname === "/sign-in") {
    return NextResponse.next();
  }

  // Check for auth token in cookies or localStorage (we'll use a cookie)
  const token = request.cookies.get("auth_token")?.value;

  // If no token and trying to access protected route, redirect to sign-in
  if (!token) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  // Allow the request to proceed
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

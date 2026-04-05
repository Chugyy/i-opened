import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for public/auth routes and static assets
  const publicPaths = ['/login', '/setup', '/book'];
  const isPublic = publicPaths.some((p) => pathname.startsWith(p));

  if (isPublic) return NextResponse.next();

  // Note: JWT is stored in localStorage (client-side) — middleware can only check cookies.
  // Auth enforcement happens client-side via API 401 → redirect to /login.
  // This middleware handles cookie-based tokens if set.
  const token = request.cookies.get('access_token')?.value;
  if (token) return NextResponse.next();

  // If no cookie token, allow through — client-side will redirect if needed
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|api|login|setup|book).*)',
  ],
};

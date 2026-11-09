import { NextResponse, type NextRequest } from "next/server";

// Keep in sync with lib/server/backend.ts (middleware runs on the edge runtime).
const AUTH_COOKIE_NAME = process.env.AUTH_COOKIE_NAME || "sentiboard_session";
const PUBLIC_PAGES = ["/login", "/register", "/about"];
const AUTH_PAGES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const signedIn = Boolean(request.cookies.get(AUTH_COOKIE_NAME)?.value);

  if (signedIn && AUTH_PAGES.includes(pathname)) {
    return NextResponse.redirect(new URL("/analyze", request.url));
  }

  if (!signedIn && !PUBLIC_PAGES.includes(pathname)) {
    const login = new URL("/login", request.url);
    if (pathname !== "/") login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }

  return NextResponse.next();
}

export const config = {
  // Pages only: skip API routes, Next internals and static files.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};

import { NextResponse, type NextRequest } from "next/server";

// Optimistic check only: no session cookie -> send to login. Real authorisation (role and
// ownership) is enforced by the API on every request and by each dashboard layout.
export function proxy(request: NextRequest) {
  if (!request.cookies.get("propcheck_session")) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/dashboard/:path*"] };

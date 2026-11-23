import { NextRequest, NextResponse } from "next/server";

// Production proxy: forwards /api/* to the private backend and attaches the shared secret server-side,
// so the secret never reaches the browser or the git repo. Without the env vars (local dev) it does nothing
// and next.config.ts rewrites to localhost:8000 as before.
export function middleware(req: NextRequest) {
  const api = process.env.OMNISCAN_API_URL;
  const secret = process.env.OMNISCAN_API_SECRET;
  if (!api || !secret) return NextResponse.next();
  const headers = new Headers(req.headers);
  headers.set("x-omniscan-key", secret);
  headers.set("bypass-tunnel-reminder", "1");
  const dest = new URL(req.nextUrl.pathname + req.nextUrl.search, api);
  return NextResponse.rewrite(dest, { request: { headers } });
}

export const config = { matcher: "/api/:path*" };

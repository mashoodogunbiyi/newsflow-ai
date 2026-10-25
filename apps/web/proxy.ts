import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { shouldOptimisticallyRedirectFromDashboard } from "@/lib/route-protection";

export function proxy(request: NextRequest) {
  const shouldRedirect = shouldOptimisticallyRedirectFromDashboard(
    request.nextUrl.pathname,
    request.cookies.has("newsflow_session"),
  );

  if (shouldRedirect) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("reason", "authentication_required");
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};

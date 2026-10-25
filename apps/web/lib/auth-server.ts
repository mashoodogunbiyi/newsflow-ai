import { cookies } from "next/headers";

import { isAuthenticatedUser, type AuthenticationState } from "@/lib/auth-types";

const SESSION_COOKIE_NAME = "newsflow_session";

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
}

export async function getAuthenticationState(): Promise<AuthenticationState> {
  const sessionCookie = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!sessionCookie) {
    return { status: "unauthenticated" };
  }

  try {
    const response = await fetch(`${getBackendBaseUrl()}/api/v1/auth/me`, {
      headers: {
        Cookie: `${SESSION_COOKIE_NAME}=${encodeURIComponent(sessionCookie)}`,
      },
      cache: "no-store",
    });

    if (response.status === 401) {
      return { status: "unauthenticated" };
    }
    if (!response.ok) {
      return { status: "unavailable" };
    }

    const user: unknown = await response.json();
    if (!isAuthenticatedUser(user)) {
      return { status: "unavailable" };
    }
    return { status: "authenticated", user };
  } catch {
    return { status: "unavailable" };
  }
}

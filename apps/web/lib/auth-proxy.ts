const AUTHENTICATION_ACTIONS = {
  login: ["POST"],
  logout: ["POST"],
  me: ["GET"],
  register: ["POST"],
} as const;

type AuthenticationAction = keyof typeof AUTHENTICATION_ACTIONS;

const AUTHENTICATION_COOKIE_NAMES = new Set(["newsflow_csrf", "newsflow_session"]);

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
}

function isAllowedAction(action: string, method: string): action is AuthenticationAction {
  if (!(action in AUTHENTICATION_ACTIONS)) {
    return false;
  }

  return (AUTHENTICATION_ACTIONS[action as AuthenticationAction] as readonly string[]).includes(
    method,
  );
}

function copySetCookieHeaders(source: Headers, destination: Headers) {
  const headersWithCookies = source as Headers & { getSetCookie?: () => string[] };
  const setCookies = headersWithCookies.getSetCookie?.() ?? [];

  for (const cookie of setCookies) {
    destination.append("Set-Cookie", cookie);
  }
}

function selectAuthenticationCookies(cookieHeader: string) {
  return cookieHeader
    .split(";")
    .map((cookie) => cookie.trim())
    .filter((cookie) => {
      const separatorIndex = cookie.indexOf("=");
      const name = separatorIndex === -1 ? cookie : cookie.slice(0, separatorIndex);
      return AUTHENTICATION_COOKIE_NAMES.has(name);
    })
    .join("; ");
}

export async function proxyAuthenticationRequest(
  request: Request,
  action: string,
): Promise<Response> {
  if (!isAllowedAction(action, request.method)) {
    return Response.json(
      {
        error: {
          code: "authentication_route_not_found",
          message: "The requested authentication operation is not available.",
        },
      },
      { status: 404 },
    );
  }

  const forwardedHeaders = new Headers();
  for (const name of ["content-type", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value) {
      forwardedHeaders.set(name, value);
    }
  }
  const authenticationCookies = selectAuthenticationCookies(request.headers.get("cookie") ?? "");
  if (authenticationCookies) {
    forwardedHeaders.set("cookie", authenticationCookies);
  }

  try {
    const backendResponse = await fetch(`${getBackendBaseUrl()}/api/v1/auth/${action}`, {
      method: request.method,
      headers: forwardedHeaders,
      body: request.method === "GET" ? undefined : await request.text(),
      cache: "no-store",
    });
    const responseHeaders = new Headers({
      "Cache-Control": "no-store",
      "Content-Type": backendResponse.headers.get("content-type") ?? "application/json",
    });
    copySetCookieHeaders(backendResponse.headers, responseHeaders);

    return new Response(
      backendResponse.status === 204 ? null : await backendResponse.arrayBuffer(),
      {
        status: backendResponse.status,
        headers: responseHeaders,
      },
    );
  } catch {
    return Response.json(
      {
        error: {
          code: "authentication_unavailable",
          message: "Authentication is temporarily unavailable. Please try again.",
        },
      },
      {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      },
    );
  }
}

const AUTHENTICATION_COOKIE_NAMES = new Set(["newsflow_csrf", "newsflow_session"]);

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
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

export async function proxyGenerationRequest(request: Request): Promise<Response> {
  const forwardedHeaders = new Headers();
  for (const name of ["content-type", "idempotency-key", "x-csrf-token"]) {
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
    const backendResponse = await fetch(`${getBackendBaseUrl()}/api/generations`, {
      method: "POST",
      headers: forwardedHeaders,
      body: await request.text(),
      cache: "no-store",
    });
    const responseHeaders = new Headers({
      "Cache-Control": "no-store",
      "Content-Type": backendResponse.headers.get("content-type") ?? "application/json",
    });
    const retryAfter = backendResponse.headers.get("retry-after");
    if (retryAfter) {
      responseHeaders.set("Retry-After", retryAfter);
    }

    return new Response(await backendResponse.arrayBuffer(), {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      {
        error: {
          code: "generation_unavailable",
          message: "Draft generation is temporarily unavailable. Please try again.",
        },
      },
      {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      },
    );
  }
}

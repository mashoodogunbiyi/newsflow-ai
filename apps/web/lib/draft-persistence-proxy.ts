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

export async function proxyDraftCreation(request: Request): Promise<Response> {
  const headers = new Headers();
  for (const name of ["content-type", "idempotency-key", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const cookies = selectAuthenticationCookies(request.headers.get("cookie") ?? "");
  if (cookies) headers.set("cookie", cookies);

  try {
    const backendResponse = await fetch(`${getBackendBaseUrl()}/api/v1/drafts`, {
      method: "POST",
      headers,
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(await backendResponse.arrayBuffer(), {
      status: backendResponse.status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      {
        error: {
          code: "draft_persistence_unavailable",
          message: "The draft could not be saved right now. Please try again.",
        },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}

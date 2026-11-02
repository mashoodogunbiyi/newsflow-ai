const AUTHENTICATION_COOKIE_NAMES = new Set(["newsflow_csrf", "newsflow_session"]);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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

export async function proxyDraftDeletion(request: Request, draftId: string): Promise<Response> {
  if (!UUID_PATTERN.test(draftId)) {
    return Response.json(
      { error: { code: "private_resource_not_found", message: "The draft was not found." } },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }

  const headers = new Headers();
  const csrfToken = request.headers.get("x-csrf-token");
  if (csrfToken) headers.set("x-csrf-token", csrfToken);
  const cookies = selectAuthenticationCookies(request.headers.get("cookie") ?? "");
  if (cookies) headers.set("cookie", cookies);

  try {
    const backendResponse = await fetch(
      `${getBackendBaseUrl()}/api/v1/drafts/${encodeURIComponent(draftId)}`,
      { method: "DELETE", headers, cache: "no-store" },
    );
    const body = backendResponse.status === 204 ? null : await backendResponse.arrayBuffer();
    return new Response(body, {
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
          code: "content_deletion_unavailable",
          message: "Draft deletion is temporarily unavailable. Please try again.",
        },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}

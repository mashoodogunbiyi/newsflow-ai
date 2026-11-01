import { isPreviewImageId } from "@/types/preview";

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

function unavailableResponse() {
  return Response.json(
    {
      error: {
        code: "image_generation_unavailable",
        message: "Illustration generation is temporarily unavailable. Please try again.",
      },
    },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}

export async function proxyImageGenerationRequest(
  request: Request,
  parentImageId: string | null = null,
): Promise<Response> {
  if (parentImageId !== null && !isPreviewImageId(parentImageId)) {
    return Response.json(
      { error: { code: "invalid_image_id", message: "The selected image is not valid." } },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }

  const forwardedHeaders = new Headers();
  for (const name of ["content-type", "idempotency-key", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value) forwardedHeaders.set(name, value);
  }
  const cookies = selectAuthenticationCookies(request.headers.get("cookie") ?? "");
  if (cookies) forwardedHeaders.set("cookie", cookies);

  const backendPath = parentImageId
    ? `/api/images/${encodeURIComponent(parentImageId)}/regenerate`
    : "/api/images";
  try {
    const backendResponse = await fetch(`${getBackendBaseUrl()}${backendPath}`, {
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
    if (retryAfter && /^\d+$/.test(retryAfter)) responseHeaders.set("Retry-After", retryAfter);

    return new Response(await backendResponse.arrayBuffer(), {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch {
    return unavailableResponse();
  }
}

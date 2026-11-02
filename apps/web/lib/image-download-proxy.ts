import { isPreviewImageId } from "@/types/preview";

const SESSION_COOKIE_NAME = "newsflow_session";
const MEDIA_TYPE_EXTENSIONS = new Map([
  ["image/jpeg", "jpg"],
  ["image/png", "png"],
  ["image/webp", "webp"],
]);
const PRIVATE_RESPONSE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0",
  Pragma: "no-cache",
  Vary: "Cookie",
  "X-Content-Type-Options": "nosniff",
};

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
}

function selectSessionCookie(cookieHeader: string) {
  return (
    cookieHeader
      .split(";")
      .map((cookie) => cookie.trim())
      .find((cookie) => cookie.startsWith(`${SESSION_COOKIE_NAME}=`)) ?? null
  );
}

function failureResponse(status: 401 | 404 | 503) {
  const message =
    status === 401
      ? "Your session has expired. Sign in again before downloading."
      : status === 404
        ? "The selected illustration is no longer available."
        : "The illustration could not be downloaded. Please try again.";
  return Response.json(
    {
      error: {
        code:
          status === 401
            ? "authentication_required"
            : status === 404
              ? "image_not_found"
              : "image_download_unavailable",
        message,
      },
    },
    { status, headers: PRIVATE_RESPONSE_HEADERS },
  );
}

export async function proxyImageDownloadRequest(
  request: Request,
  imageId: string,
): Promise<Response> {
  if (!isPreviewImageId(imageId)) {
    return failureResponse(404);
  }

  const sessionCookie = selectSessionCookie(request.headers.get("cookie") ?? "");
  if (!sessionCookie) {
    return failureResponse(401);
  }

  try {
    const backendResponse = await fetch(
      `${getBackendBaseUrl()}/api/images/${encodeURIComponent(imageId)}/download`,
      {
        method: "GET",
        headers: {
          Accept: "image/png, image/jpeg, image/webp",
          Cookie: sessionCookie,
        },
        cache: "no-store",
      },
    );
    if (!backendResponse.ok) {
      if (backendResponse.status === 401) return failureResponse(401);
      if (backendResponse.status === 404) return failureResponse(404);
      return failureResponse(503);
    }

    const mediaType = backendResponse.headers.get("content-type")?.split(";", 1)[0].trim();
    const extension = mediaType ? MEDIA_TYPE_EXTENSIONS.get(mediaType) : undefined;
    if (!mediaType || !extension) {
      return failureResponse(503);
    }

    return new Response(await backendResponse.arrayBuffer(), {
      status: 200,
      headers: {
        ...PRIVATE_RESPONSE_HEADERS,
        "Content-Disposition": `attachment; filename="newsflow-ai-illustration-${imageId}.${extension}"`,
        "Content-Type": mediaType,
      },
    });
  } catch {
    return failureResponse(503);
  }
}

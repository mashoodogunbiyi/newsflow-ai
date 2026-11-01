import { isPreviewImageId } from "@/types/preview";

const SESSION_COOKIE_NAME = "newsflow_session";
const ALLOWED_IMAGE_MEDIA_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
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

function unavailableResponse(status = 503) {
  return Response.json(
    {
      error: {
        code: "image_preview_unavailable",
        message: "The illustration is temporarily unavailable.",
      },
    },
    { status, headers: PRIVATE_RESPONSE_HEADERS },
  );
}

export async function proxyImageContentRequest(
  request: Request,
  imageId: string,
): Promise<Response> {
  if (!isPreviewImageId(imageId)) {
    return unavailableResponse(404);
  }

  const sessionCookie = selectSessionCookie(request.headers.get("cookie") ?? "");
  const headers = new Headers({ Accept: "image/png, image/jpeg, image/webp" });
  if (sessionCookie) {
    headers.set("Cookie", sessionCookie);
  }

  try {
    const backendResponse = await fetch(
      `${getBackendBaseUrl()}/api/images/${encodeURIComponent(imageId)}/content`,
      {
        method: "GET",
        headers,
        cache: "no-store",
      },
    );

    if (!backendResponse.ok) {
      const safeStatus =
        backendResponse.status === 401 || backendResponse.status === 404
          ? backendResponse.status
          : 503;
      return unavailableResponse(safeStatus);
    }

    const mediaType = backendResponse.headers.get("content-type")?.split(";", 1)[0].trim();
    if (!mediaType || !ALLOWED_IMAGE_MEDIA_TYPES.has(mediaType)) {
      return unavailableResponse();
    }

    return new Response(await backendResponse.arrayBuffer(), {
      status: 200,
      headers: {
        ...PRIVATE_RESPONSE_HEADERS,
        "Content-Type": mediaType,
      },
    });
  } catch {
    return unavailableResponse();
  }
}

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { proxyImageDownloadRequest } from "@/lib/image-download-proxy";

const imageId = "10000000-0000-4000-8000-000000000071";

describe("secure image download gateway", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000/");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("forwards only the session and returns approved bytes with a safe filename", async () => {
    const bytes = new Uint8Array([137, 80, 78, 71]);
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(bytes, {
        status: 200,
        headers: {
          "Content-Disposition": `attachment; filename="backend-private-${imageId}.png"`,
          "Content-Type": "image/png",
        },
      }),
    );
    const request = new Request(`http://localhost:3000/api/images/${imageId}/download`, {
      headers: {
        Authorization: "do-not-forward",
        Cookie:
          "analytics_id=do-not-forward; newsflow_session=session-value; newsflow_csrf=do-not-forward",
      },
    });

    const response = await proxyImageDownloadRequest(request, imageId);

    expect(fetch).toHaveBeenCalledWith(
      `http://backend:8000/api/images/${imageId}/download`,
      expect.objectContaining({ cache: "no-store", method: "GET" }),
    );
    const forwardedHeaders = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(forwardedHeaders.get("cookie")).toBe("newsflow_session=session-value");
    expect(forwardedHeaders.get("authorization")).toBeNull();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("content-disposition")).toBe(
      `attachment; filename="newsflow-ai-illustration-${imageId}.png"`,
    );
    expect(response.headers.get("cache-control")).toBe("private, no-store, max-age=0");
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(bytes);
  });

  test("requires a session before contacting FastAPI", async () => {
    const response = await proxyImageDownloadRequest(
      new Request(`http://localhost:3000/api/images/${imageId}/download`),
      imageId,
    );

    expect(response.status).toBe(401);
    expect(fetch).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "authentication_required",
        message: "Your session has expired. Sign in again before downloading.",
      },
    });
  });

  test("masks missing, unavailable, and unsupported backend responses", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response("private detail", { status: 404 }))
      .mockResolvedValueOnce(
        new Response("unsafe", { status: 200, headers: { "Content-Type": "text/html" } }),
      )
      .mockRejectedValueOnce(new Error("private network detail"));
    const request = new Request(`http://localhost:3000/api/images/${imageId}/download`, {
      headers: { Cookie: "newsflow_session=session-value" },
    });

    const missing = await proxyImageDownloadRequest(request, imageId);
    const unsupported = await proxyImageDownloadRequest(request, imageId);
    const unavailable = await proxyImageDownloadRequest(request, imageId);

    expect(missing.status).toBe(404);
    expect(unsupported.status).toBe(503);
    expect(unavailable.status).toBe(503);
    expect(await unsupported.text()).not.toContain("unsafe");
  });

  test("rejects an invalid image identifier before contacting FastAPI", async () => {
    const response = await proxyImageDownloadRequest(
      new Request("http://localhost:3000/api/images/not-a-uuid/download"),
      "not-a-uuid",
    );

    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });
});

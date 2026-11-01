import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { proxyImageContentRequest } from "@/lib/image-content-proxy";

const imageId = "10000000-0000-4000-8000-000000000031";

describe("private image preview gateway", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000/");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("forwards only the session cookie and returns approved private image bytes", async () => {
    const bytes = new Uint8Array([137, 80, 78, 71]);
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(bytes, { status: 200, headers: { "Content-Type": "image/png" } }),
    );
    const request = new Request(`http://localhost:3000/api/images/${imageId}/content`, {
      headers: {
        Authorization: "do-not-forward",
        Cookie:
          "analytics_id=do-not-forward; newsflow_session=session-value; newsflow_csrf=do-not-forward",
      },
    });

    const response = await proxyImageContentRequest(request, imageId);

    expect(fetch).toHaveBeenCalledWith(
      `http://backend:8000/api/images/${imageId}/content`,
      expect.objectContaining({ cache: "no-store", method: "GET" }),
    );
    const forwardedHeaders = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(forwardedHeaders.get("cookie")).toBe("newsflow_session=session-value");
    expect(forwardedHeaders.get("authorization")).toBeNull();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("cache-control")).toBe("private, no-store, max-age=0");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(bytes);
  });

  test("rejects an invalid image identifier before contacting FastAPI", async () => {
    const response = await proxyImageContentRequest(
      new Request("http://localhost:3000/api/images/not-a-uuid/content"),
      "not-a-uuid",
    );

    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });

  test("does not relay an unsupported response as executable content", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("<script>unsafe</script>", {
        status: 200,
        headers: { "Content-Type": "text/html" },
      }),
    );

    const response = await proxyImageContentRequest(
      new Request(`http://localhost:3000/api/images/${imageId}/content`),
      imageId,
    );

    expect(response.status).toBe(503);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).not.toContain("unsafe");
  });

  test("returns safe failures for private not-found and unavailable responses", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response("private backend detail", { status: 404 }))
      .mockRejectedValueOnce(new Error("private network detail"));
    const request = new Request(`http://localhost:3000/api/images/${imageId}/content`);

    const missing = await proxyImageContentRequest(request, imageId);
    const unavailable = await proxyImageContentRequest(request, imageId);

    expect(missing.status).toBe(404);
    expect(unavailable.status).toBe(503);
    await expect(missing.json()).resolves.toEqual({
      error: {
        code: "image_preview_unavailable",
        message: "The illustration is temporarily unavailable.",
      },
    });
  });
});

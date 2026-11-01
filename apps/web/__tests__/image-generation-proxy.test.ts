import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { proxyImageGenerationRequest } from "@/lib/image-generation-proxy";

const imageId = "20000000-0000-4000-8000-000000000005";

describe("image generation gateway", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000/");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("forwards only approved headers and authentication cookies", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ image_id: imageId }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const body = JSON.stringify({ style: "editorial_illustration" });
    const request = new Request("http://localhost:3000/api/images", {
      method: "POST",
      headers: {
        Authorization: "do-not-forward",
        Cookie: "analytics_id=hidden; newsflow_session=session-value; newsflow_csrf=csrf-value",
        "Content-Type": "application/json",
        "Idempotency-Key": "image:11111111-1111-4111-8111-111111111111",
        "X-CSRF-Token": "csrf-value",
      },
      body,
    });

    const response = await proxyImageGenerationRequest(request);

    expect(fetch).toHaveBeenCalledWith(
      "http://backend:8000/api/images",
      expect.objectContaining({ method: "POST", body, cache: "no-store" }),
    );
    const headers = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(headers.get("cookie")).toBe("newsflow_session=session-value; newsflow_csrf=csrf-value");
    expect(headers.get("authorization")).toBeNull();
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  test("targets the owner-scoped regeneration endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("{}", { status: 201 }));

    await proxyImageGenerationRequest(
      new Request(`http://localhost:3000/api/images/${imageId}/regenerate`, {
        method: "POST",
        body: "{}",
      }),
      imageId,
    );

    expect(fetch).toHaveBeenCalledWith(
      `http://backend:8000/api/images/${imageId}/regenerate`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  test("rejects malformed image IDs before contacting FastAPI", async () => {
    const response = await proxyImageGenerationRequest(
      new Request("http://localhost:3000/api/images/not-an-id/regenerate", {
        method: "POST",
      }),
      "not-an-id",
    );

    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });
});

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { proxyGenerationRequest } from "@/lib/generation-proxy";

describe("generation gateway", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000/");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("forwards only the generation contract headers and authentication cookies", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ generation_id: "generated-id" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const body = JSON.stringify({
      article_id: "10000000-0000-4000-8000-000000000003",
      tone: "professional",
      length: "medium",
    });
    const request = new Request("http://localhost:3000/api/generations", {
      method: "POST",
      headers: {
        Authorization: "do-not-forward",
        Cookie:
          "analytics_id=do-not-forward; newsflow_session=session-value; newsflow_csrf=csrf-value",
        "Content-Type": "application/json",
        "Idempotency-Key": "generation:11111111-1111-4111-8111-111111111111",
        "X-CSRF-Token": "csrf-value",
      },
      body,
    });

    const response = await proxyGenerationRequest(request);

    expect(fetch).toHaveBeenCalledWith(
      "http://backend:8000/api/generations",
      expect.objectContaining({ method: "POST", body, cache: "no-store" }),
    );
    const forwardedHeaders = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(forwardedHeaders.get("cookie")).toBe(
      "newsflow_session=session-value; newsflow_csrf=csrf-value",
    );
    expect(forwardedHeaders.get("authorization")).toBeNull();
    expect(forwardedHeaders.get("content-type")).toBe("application/json");
    expect(forwardedHeaders.get("idempotency-key")).toBe(
      "generation:11111111-1111-4111-8111-111111111111",
    );
    expect(forwardedHeaders.get("x-csrf-token")).toBe("csrf-value");
    expect(response.status).toBe(201);
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  test("preserves a backend retry delay without forwarding unrelated headers", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "generation_limit_exceeded", message: "Please try again later." },
        }),
        {
          status: 429,
          headers: {
            "Content-Type": "application/json",
            "Retry-After": "30",
            "X-Internal-Request-Id": "hidden",
          },
        },
      ),
    );

    const response = await proxyGenerationRequest(
      new Request("http://localhost:3000/api/generations", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(429);
    expect(response.headers.get("retry-after")).toBe("30");
    expect(response.headers.get("x-internal-request-id")).toBeNull();
  });

  test("returns a safe service error when FastAPI cannot be reached", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("connection details must stay private"));

    const response = await proxyGenerationRequest(
      new Request("http://localhost:3000/api/generations", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "generation_unavailable",
        message: "Draft generation is temporarily unavailable. Please try again.",
      },
    });
  });
});

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { requestImageGeneration } from "@/lib/image-generation-api";

const textGenerationId = "20000000-0000-4000-8000-000000000004";
const imageId = "20000000-0000-4000-8000-000000000005";
const imageRunId = "20000000-0000-4000-8000-000000000006";
const postId = "20000000-0000-4000-8000-000000000007";
const requestKey = "image:11111111-1111-4111-8111-111111111111";

const response = {
  image_id: imageId,
  parent_image_id: null,
  generation_id: imageRunId,
  generated_post_id: postId,
  regeneration_sequence: 0,
  status: "completed",
  safety_status: "pending",
  is_ai_generated: true,
  review_required: true,
  created_at: "2026-11-01T12:00:00Z",
};

const request = {
  action: "generate" as const,
  generation_id: textGenerationId,
  style: "editorial_illustration" as const,
  aspect_ratio: "landscape" as const,
  composition: "balanced" as const,
};

describe("image generation client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    document.cookie = "newsflow_csrf=csrf-test-token; path=/";
  });

  afterEach(() => {
    document.cookie = "newsflow_csrf=; Max-Age=0; path=/";
    vi.unstubAllGlobals();
  });

  test("submits a validated initial request with CSRF and idempotency protection", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(response), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const result = await requestImageGeneration(request, requestKey);

    expect(result.status).toBe("success");
    expect(fetch).toHaveBeenCalledWith(
      "/api/images",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({
          generation_id: textGenerationId,
          style: "editorial_illustration",
          aspect_ratio: "landscape",
          composition: "balanced",
        }),
      }),
    );
    const headers = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(headers.get("x-csrf-token")).toBe("csrf-test-token");
    expect(headers.get("idempotency-key")).toBe(requestKey);
  });

  test("maps a backend usage limit to a retryable image state", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "generation_limit_exceeded", message: "Daily image limit reached." },
        }),
        { status: 429, headers: { "Content-Type": "application/json", "Retry-After": "45" } },
      ),
    );

    const result = await requestImageGeneration(request, requestKey);

    expect(result).toEqual({
      error: {
        category: "usage_limit",
        message: "Daily image limit reached.",
        retryAfterSeconds: 45,
        retryable: true,
      },
      status: "error",
    });
  });

  test("treats rejected CSRF proof as an expired authenticated session", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "csrf_validation_failed", message: "CSRF validation failed." },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    );

    const result = await requestImageGeneration(request, requestKey);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.category).toBe("authentication");
      expect(result.error.retryable).toBe(false);
      expect(result.error.message).toMatch(/session has expired/i);
    }
  });

  test("rejects an initial response that pretends to be a child version", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({ ...response, parent_image_id: imageId, regeneration_sequence: 1 }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );

    const result = await requestImageGeneration(request, requestKey);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.message).toMatch(/could not be verified/i);
    }
  });
});

import { afterEach, describe, expect, test, vi } from "vitest";

import { proxyDraftCreation } from "@/lib/draft-persistence-proxy";

describe("draft creation proxy", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("forwards the JSON body, request identity, CSRF proof, and only authentication cookies", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ id: "saved" }, { status: 201 })),
    );
    const request = new Request("http://localhost/api/drafts", {
      method: "POST",
      headers: {
        Cookie: "analytics=hidden; newsflow_session=session-value; newsflow_csrf=csrf-value",
        "Content-Type": "application/json",
        "Idempotency-Key": "draft:request-id",
        "X-CSRF-Token": "csrf-value",
      },
      body: JSON.stringify({ edited_text: "Reviewed draft" }),
    });

    const response = await proxyDraftCreation(request);

    expect(response.status).toBe(201);
    const [url, options] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe("http://localhost:8000/api/v1/drafts");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(JSON.stringify({ edited_text: "Reviewed draft" }));
    const headers = new Headers(options?.headers);
    expect(headers.get("cookie")).toBe("newsflow_session=session-value; newsflow_csrf=csrf-value");
    expect(headers.get("idempotency-key")).toBe("draft:request-id");
    expect(headers.get("x-csrf-token")).toBe("csrf-value");
    expect(headers.get("analytics")).toBeNull();
  });

  test("returns a controlled no-store response when FastAPI cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const response = await proxyDraftCreation(
      new Request("http://localhost/api/drafts", { method: "POST", body: "{}" }),
    );

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(await response.json()).toEqual({
      error: {
        code: "draft_persistence_unavailable",
        message: "The draft could not be saved right now. Please try again.",
      },
    });
  });
});

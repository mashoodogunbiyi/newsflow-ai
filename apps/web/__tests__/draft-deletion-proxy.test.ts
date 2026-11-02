import { afterEach, describe, expect, test, vi } from "vitest";

import { proxyDraftDeletion } from "@/lib/draft-deletion-proxy";

const draftId = "72000000-0000-4000-8000-000000000003";

describe("draft deletion proxy", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("forwards only authentication cookies and the CSRF header", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const request = new Request(`http://localhost/api/drafts/${draftId}`, {
      method: "DELETE",
      headers: {
        Cookie: "analytics=hidden; newsflow_session=session-value; newsflow_csrf=csrf-value",
        "X-CSRF-Token": "csrf-value",
      },
    });

    const response = await proxyDraftDeletion(request, draftId);

    expect(response.status).toBe(204);
    const options = vi.mocked(fetch).mock.calls[0]?.[1];
    const headers = new Headers(options?.headers);
    expect(headers.get("cookie")).toBe("newsflow_session=session-value; newsflow_csrf=csrf-value");
    expect(headers.get("x-csrf-token")).toBe("csrf-value");
    expect(headers.get("analytics")).toBeNull();
  });

  test("rejects an invalid identifier without contacting the backend", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const response = await proxyDraftDeletion(
      new Request("http://localhost/api/drafts/not-a-uuid", { method: "DELETE" }),
      "not-a-uuid",
    );
    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });
});

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { proxyAuthenticationRequest } from "@/lib/auth-proxy";

describe("authentication gateway", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000/");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("forwards only authentication cookies and the CSRF header", async () => {
    const backendHeaders = new Headers({ "Content-Type": "application/json" });
    backendHeaders.append(
      "Set-Cookie",
      "newsflow_session=session-value; Path=/; HttpOnly; SameSite=Lax",
    );
    backendHeaders.append("Set-Cookie", "newsflow_csrf=csrf-value; Path=/; SameSite=Lax");
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Logout successful" }), {
        status: 200,
        headers: backendHeaders,
      }),
    );
    const request = new Request("http://localhost:3000/api/auth/logout", {
      method: "POST",
      headers: {
        Cookie:
          "analytics_id=do-not-forward; newsflow_session=session-value; newsflow_csrf=csrf-value",
        "X-CSRF-Token": "csrf-value",
      },
    });

    const response = await proxyAuthenticationRequest(request, "logout");

    expect(fetch).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
        headers: expect.any(Headers),
      }),
    );
    const forwardedOptions = vi.mocked(fetch).mock.calls[0]?.[1];
    const forwardedHeaders = new Headers(forwardedOptions?.headers);
    expect(forwardedHeaders.get("cookie")).toBe(
      "newsflow_session=session-value; newsflow_csrf=csrf-value",
    );
    expect(forwardedHeaders.get("x-csrf-token")).toBe("csrf-value");
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.getSetCookie()).toHaveLength(2);
  });

  test("rejects unsupported actions without contacting the backend", async () => {
    const response = await proxyAuthenticationRequest(
      new Request("http://localhost:3000/api/auth/admin", { method: "POST" }),
      "admin",
    );

    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });

  test("returns a safe service error when the backend cannot be reached", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("connection failed"));

    const response = await proxyAuthenticationRequest(
      new Request("http://localhost:3000/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "member@example.com", password: "not-logged" }),
      }),
      "login",
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toMatchObject({
      error: { code: "authentication_unavailable" },
    });
  });
});

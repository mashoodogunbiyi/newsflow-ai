import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { getAuthenticationState } from "@/lib/auth-server";

const cookieState = vi.hoisted(() => ({ session: undefined as string | undefined }));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) =>
      name === "newsflow_session" && cookieState.session
        ? { name, value: cookieState.session }
        : undefined,
  }),
}));

describe("server authentication state", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000");
    vi.stubGlobal("fetch", vi.fn());
    cookieState.session = undefined;
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("treats a missing session cookie as unauthenticated", async () => {
    await expect(getAuthenticationState()).resolves.toEqual({ status: "unauthenticated" });
    expect(fetch).not.toHaveBeenCalled();
  });

  test("restores a valid session from the backend current-user endpoint", async () => {
    cookieState.session = "session-value";
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "9bb4cb73-dd34-4883-b823-2b67aa6a9128",
          email: "member@example.com",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(getAuthenticationState()).resolves.toEqual({
      status: "authenticated",
      user: {
        id: "9bb4cb73-dd34-4883-b823-2b67aa6a9128",
        email: "member@example.com",
      },
    });
    expect(fetch).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/auth/me",
      expect.objectContaining({
        headers: { Cookie: "newsflow_session=session-value" },
        cache: "no-store",
      }),
    );
  });

  test("rejects an expired or invalid session", async () => {
    cookieState.session = "expired-session";
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 401 }));

    await expect(getAuthenticationState()).resolves.toEqual({ status: "unauthenticated" });
  });

  test("distinguishes a backend outage from an invalid session", async () => {
    cookieState.session = "session-value";
    vi.mocked(fetch).mockRejectedValueOnce(new Error("connection failed"));

    await expect(getAuthenticationState()).resolves.toEqual({ status: "unavailable" });
  });
});

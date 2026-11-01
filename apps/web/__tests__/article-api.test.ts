import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { getArticlePage } from "@/lib/article-api";

const cookieState = vi.hoisted(() => ({ session: undefined as string | undefined }));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) =>
      name === "newsflow_session" && cookieState.session
        ? { name, value: cookieState.session }
        : undefined,
  }),
}));

const articlePage = {
  items: [
    {
      id: "10000000-0000-4000-8000-000000000003",
      title: "Synthetic technology update",
      description: "A fictional summary used for development.",
      source_url: "https://example.invalid/newsflow-ai/fixture-technology-001",
      provider: "fixture-v1",
      published_at: "2026-10-12T09:00:00Z",
      category: "Technology",
      attribution: {
        display_name: "NewsFlow AI synthetic fixture",
        text: "Source: NewsFlow AI synthetic fixture - not live news",
        byline: null,
        copyright_notice: null,
      },
    },
  ],
  next_cursor: "next-page",
};

describe("article catalogue API client", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000");
    vi.stubGlobal("fetch", vi.fn());
    cookieState.session = "session-value";
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("loads one authorised page with the session and exact backend query", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(articlePage), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      getArticlePage({ cursor: "cursor-value", search: "technology", sort: "oldest" }),
    ).resolves.toEqual({ status: "success", data: articlePage });

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(
      "http://backend:8000/api/articles?limit=9&sort=oldest&cursor=cursor-value&search=technology",
      {
        headers: {
          Accept: "application/json",
          Cookie: "newsflow_session=session-value",
        },
        cache: "no-store",
      },
    );
  });

  test("does not contact FastAPI without an authenticated session", async () => {
    cookieState.session = undefined;

    await expect(getArticlePage()).resolves.toEqual({
      status: "error",
      reason: "authentication_required",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  test("maps invalid queries and unavailable services to controlled states", async () => {
    await expect(getArticlePage({ search: "x".repeat(201) })).resolves.toEqual({
      status: "error",
      reason: "invalid_request",
    });
    expect(fetch).not.toHaveBeenCalled();

    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 503 }));
    await expect(getArticlePage()).resolves.toEqual({
      status: "error",
      reason: "unavailable",
    });
  });

  test("rejects malformed or unsafe backend data instead of rendering it", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...articlePage,
          items: [{ ...articlePage.items[0], source_url: "javascript:alert(1)" }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(getArticlePage()).resolves.toEqual({
      status: "error",
      reason: "unavailable",
    });
  });
});

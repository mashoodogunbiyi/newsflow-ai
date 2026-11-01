import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ArticleCatalogue } from "@/components/articles/article-catalogue";

const articleApi = vi.hoisted(() => ({ getArticlePage: vi.fn() }));
const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/article-api", () => ({
  getArticlePage: articleApi.getArticlePage,
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
  useRouter: () => navigation,
}));

const article = {
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
};

describe("article dashboard integration", () => {
  beforeEach(() => {
    articleApi.getArticlePage.mockReset();
    navigation.redirect.mockReset();
    navigation.refresh.mockReset();
    navigation.replace.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("renders authorised articles and a cursor-based next-page control", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "success",
      data: { items: [article], next_cursor: "next cursor" },
    });

    render(
      await ArticleCatalogue({
        searchParams: Promise.resolve({
          category: "technology",
          search: "technology",
          sort: "oldest",
        }),
      }),
    );

    expect(screen.getByRole("heading", { name: article.title })).toBeDefined();
    expect(articleApi.getArticlePage).toHaveBeenCalledWith({
      category: "technology",
      cursor: undefined,
      search: "technology",
      sort: "oldest",
    });
    expect(screen.getByRole("link", { name: "Next articles" }).getAttribute("href")).toBe(
      "/dashboard?cursor=next+cursor&category=technology&search=technology&sort=oldest",
    );
  });

  test("renders a helpful empty catalogue state", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "success",
      data: { items: [], next_cursor: null },
    });

    render(await ArticleCatalogue({ searchParams: Promise.resolve({}) }));

    expect(
      screen.getByRole("heading", { name: "No articles are available right now." }),
    ).toBeDefined();
    expect(screen.getByText(/live CNN access remains disabled/i)).toBeDefined();
  });

  test("renders a controlled service error and retries with a route refresh", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "error",
      reason: "unavailable",
    });

    render(await ArticleCatalogue({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("alert")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(navigation.refresh).toHaveBeenCalledOnce();
  });

  test("redirects when FastAPI rejects the session", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "error",
      reason: "authentication_required",
    });

    await expect(ArticleCatalogue({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "NEXT_REDIRECT",
    );
    expect(navigation.redirect).toHaveBeenCalledWith("/login?reason=authentication_required");
  });
});

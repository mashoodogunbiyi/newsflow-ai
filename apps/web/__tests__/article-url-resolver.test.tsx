import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ArticleUrlResolver } from "@/components/articles/article-url-resolver";

const articleApi = vi.hoisted(() => ({
  normaliseSourceUrl: vi.fn((value: string) => (value.startsWith("https://") ? value : null)),
  resolveArticleUrl: vi.fn(),
}));
const navigation = vi.hoisted(() => ({ redirect: vi.fn() }));

vi.mock("@/lib/article-api", () => articleApi);
vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));

const approvedUrl = "https://example.invalid/newsflow/synthetic-clean-energy";

describe("article URL resolver", () => {
  beforeEach(() => {
    articleApi.normaliseSourceUrl.mockClear();
    articleApi.resolveArticleUrl.mockReset();
    navigation.redirect.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("renders a primary URL form without resolving an empty value", async () => {
    render(await ArticleUrlResolver({ searchParams: Promise.resolve({}) }));

    expect(screen.getByLabelText("Search URL")).toHaveProperty("type", "url");
    expect(screen.getByRole("button", { name: "Use this article" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Try the synthetic demo URL" })).toBeDefined();
    expect(articleApi.resolveArticleUrl).not.toHaveBeenCalled();
  });

  test("redirects an exact approved URL to its generation workspace", async () => {
    articleApi.resolveArticleUrl.mockResolvedValue({
      status: "success",
      data: { id: "10000000-0000-4000-8000-000000000003" },
    });

    await expect(
      ArticleUrlResolver({ searchParams: Promise.resolve({ url: approvedUrl }) }),
    ).rejects.toThrow("NEXT_REDIRECT");
    expect(articleApi.resolveArticleUrl).toHaveBeenCalledWith(approvedUrl);
    expect(navigation.redirect).toHaveBeenCalledWith(
      "/generate?articleId=10000000-0000-4000-8000-000000000003",
    );
  });

  test("explains when a URL is not in the approved catalogue", async () => {
    articleApi.resolveArticleUrl.mockResolvedValue({ status: "error", reason: "not_found" });

    render(
      await ArticleUrlResolver({
        searchParams: Promise.resolve({ url: "https://example.com/unapproved" }),
      }),
    );

    expect(screen.getByRole("alert").textContent).toContain(
      "not in the approved article catalogue",
    );
  });

  test("rejects duplicate URL parameters without calling the catalogue", async () => {
    render(
      await ArticleUrlResolver({
        searchParams: Promise.resolve({ url: [approvedUrl, "https://example.com/other"] }),
      }),
    );

    expect(screen.getByRole("alert").textContent).toContain("Enter one complete HTTPS");
    expect(articleApi.resolveArticleUrl).not.toHaveBeenCalled();
  });
});

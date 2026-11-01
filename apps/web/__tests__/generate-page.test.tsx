import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import GeneratePage from "@/app/(workspace)/generate/page";

const articleApi = vi.hoisted(() => ({ getArticleDetail: vi.fn() }));
const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/article-api", () => ({
  getArticleDetail: articleApi.getArticleDetail,
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
  useRouter: () => navigation,
}));

const articleDetail = {
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
  generation: { allowed: true, status: "available" },
};

describe("create-post article selection integration", () => {
  beforeEach(() => {
    articleApi.getArticleDetail.mockReset();
    navigation.redirect.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("retrieves and displays the selected article source panel", async () => {
    articleApi.getArticleDetail.mockResolvedValue({ status: "success", data: articleDetail });

    render(
      await GeneratePage({
        searchParams: Promise.resolve({ articleId: articleDetail.id }),
      }),
    );

    expect(articleApi.getArticleDetail).toHaveBeenCalledWith(articleDetail.id);
    expect(screen.getByRole("heading", { name: articleDetail.title })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Configure your LinkedIn draft." })).toBeDefined();
    expect((screen.getByRole("radio", { name: /professional/i }) as HTMLInputElement).checked).toBe(
      true,
    );
  });

  test("asks for a selection without requesting article details", async () => {
    render(await GeneratePage({ searchParams: Promise.resolve({}) }));

    expect(articleApi.getArticleDetail).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Choose an article before continuing." }),
    ).toBeDefined();
  });

  test("handles duplicated and missing article selections safely", async () => {
    render(
      await GeneratePage({
        searchParams: Promise.resolve({ articleId: [articleDetail.id, articleDetail.id] }),
      }),
    );
    expect(articleApi.getArticleDetail).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "This article selection link is not valid." }),
    ).toBeDefined();
    cleanup();

    articleApi.getArticleDetail.mockResolvedValue({ status: "error", reason: "not_found" });
    render(
      await GeneratePage({
        searchParams: Promise.resolve({ articleId: articleDetail.id }),
      }),
    );
    expect(
      screen.getByRole("heading", { name: "This article is no longer available." }),
    ).toBeDefined();
  });

  test("redirects when the backend rejects the session", async () => {
    articleApi.getArticleDetail.mockResolvedValue({
      status: "error",
      reason: "authentication_required",
    });

    await expect(
      GeneratePage({ searchParams: Promise.resolve({ articleId: articleDetail.id }) }),
    ).rejects.toThrow("NEXT_REDIRECT");
    expect(navigation.redirect).toHaveBeenCalledWith("/login?reason=authentication_required");
  });

  test("shows disabled controls when current source rights restrict generation", async () => {
    articleApi.getArticleDetail.mockResolvedValue({
      status: "success",
      data: {
        ...articleDetail,
        generation: { allowed: false, status: "restricted" },
      },
    });

    render(
      await GeneratePage({
        searchParams: Promise.resolve({ articleId: articleDetail.id }),
      }),
    );

    expect(screen.getByText(/source permissions do not allow AI generation/i)).toBeDefined();
    expect(screen.getByRole("button", { name: "Generate LinkedIn draft" })).toHaveProperty(
      "disabled",
      true,
    );
  });
});

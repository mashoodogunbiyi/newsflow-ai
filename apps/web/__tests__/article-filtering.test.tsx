import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ArticleCatalogue, CatalogueControls } from "@/components/articles/article-catalogue";
import { CategoryFilter } from "@/components/articles/category-filter";

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

describe("article category filtering and browsing state", () => {
  beforeEach(() => {
    articleApi.getArticlePage.mockReset();
    navigation.redirect.mockReset();
    navigation.refresh.mockReset();
    navigation.replace.mockReset();
  });

  afterEach(() => cleanup());

  test("provides every approved category through a labelled native select", () => {
    render(<CategoryFilter selectedCategory="technology" />);

    const category = screen.getByLabelText("Category") as HTMLSelectElement;
    expect(category.tagName).toBe("SELECT");
    expect(category.value).toBe("technology");
    expect(
      Array.from(category.options).map((option) => [option.value, option.textContent]),
    ).toEqual([
      ["", "All categories"],
      ["technology", "Technology"],
      ["business", "Business"],
      ["world_news", "World News"],
      ["science", "Science"],
      ["other", "Other"],
    ]);

    category.focus();
    fireEvent.change(category, { target: { value: "science" } });
    expect(document.activeElement).toBe(category);
    expect(category.value).toBe("science");
  });

  test("submits URL state without the previous cursor when filters change", () => {
    const { container } = render(
      <CatalogueControls category="business" search="markets" sort="oldest" />,
    );

    const form = container.querySelector("form");
    expect(form?.getAttribute("action")).toBe("/dashboard");
    expect(form?.getAttribute("method")).toBe("get");
    expect(screen.getByLabelText("Category")).toHaveProperty("value", "business");
    expect(screen.getByLabelText("Search permitted topics")).toHaveProperty("value", "markets");
    expect(screen.getByLabelText("Publication order")).toHaveProperty("value", "oldest");
    expect(form?.querySelector('[name="cursor"]')).toBeNull();
  });

  test("restores the selected URL category and sends one filtered API request", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "success",
      data: { items: [], next_cursor: null },
    });

    render(
      await ArticleCatalogue({
        searchParams: Promise.resolve({ category: "science", sort: "oldest" }),
      }),
    );

    expect(screen.getByLabelText("Category")).toHaveProperty("value", "science");
    expect(articleApi.getArticlePage).toHaveBeenCalledOnce();
    expect(articleApi.getArticlePage).toHaveBeenCalledWith({
      category: "science",
      cursor: undefined,
      search: undefined,
      sort: "oldest",
    });
    expect(screen.getByRole("heading", { name: "No articles found in Science." })).toBeDefined();
  });

  test("preserves search and sort when the selected category is cleared", async () => {
    articleApi.getArticlePage.mockResolvedValue({
      status: "success",
      data: { items: [], next_cursor: null },
    });

    render(
      await ArticleCatalogue({
        searchParams: Promise.resolve({
          category: "technology",
          search: "energy",
          sort: "oldest",
        }),
      }),
    );

    expect(screen.getByRole("link", { name: "Clear category filter" }).getAttribute("href")).toBe(
      "/dashboard?search=energy&sort=oldest",
    );
  });

  test("rejects an invalid category without making an API request", async () => {
    render(
      await ArticleCatalogue({
        searchParams: Promise.resolve({ category: "restricted-value" }),
      }),
    );

    expect(articleApi.getArticlePage).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "This article page link is not valid." }),
    ).toBeDefined();
  });

  test("rejects duplicated category parameters without making an API request", async () => {
    render(
      await ArticleCatalogue({
        searchParams: Promise.resolve({ category: ["technology", "business"] }),
      }),
    );

    expect(articleApi.getArticlePage).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "This article page link is not valid." }),
    ).toBeDefined();
  });
});

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { ArticleCard } from "@/components/articles/article-card";
import { ArticleGrid } from "@/components/articles/article-grid";
import type { Article } from "@/types/article";

const article: Article = {
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
    byline: "By Example Writer",
    copyright_notice: "Synthetic fixture only",
  },
};

describe("article dashboard components", () => {
  afterEach(() => cleanup());

  test("renders every approved article field and safe actions", () => {
    render(<ArticleCard article={article} />);

    expect(screen.getByRole("heading", { name: article.title })).toBeDefined();
    expect(screen.getByText(article.attribution.display_name)).toBeDefined();
    expect(screen.getByText("12 Oct 2026")).toBeDefined();
    expect(screen.getByText("Technology")).toBeDefined();
    expect(screen.getByText(article.description as string)).toBeDefined();
    expect(screen.getByText(article.attribution.text)).toBeDefined();
    expect(screen.getByText("By Example Writer")).toBeDefined();
    expect(screen.getByText("Synthetic fixture only")).toBeDefined();

    const sourceLink = screen.getByRole("link", {
      name: `View original source for ${article.title}`,
    });
    expect(sourceLink.getAttribute("href")).toBe(article.source_url);
    expect(sourceLink.getAttribute("target")).toBe("_blank");
    expect(sourceLink.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByRole("link", { name: "Select article" }).getAttribute("href")).toBe(
      `/generate?articleId=${article.id}`,
    );
  });

  test("keeps the card valid when no permitted summary or category is available", () => {
    render(<ArticleCard article={{ ...article, category: null, description: null }} />);

    expect(screen.getByText("No permitted summary is available for this article.")).toBeDefined();
    expect(screen.queryByText("Technology")).toBeNull();
  });

  test("renders HTML-like source text as text rather than executable markup", () => {
    const unsafeLookingTitle = '<img src=x onerror="alert(1)"> Synthetic title';
    const { container } = render(
      <ArticleCard article={{ ...article, title: unsafeLookingTitle }} />,
    );

    expect(screen.getByText(unsafeLookingTitle)).toBeDefined();
    expect(container.querySelector("img")).toBeNull();
  });

  test("uses a responsive one, two, and three-column catalogue grid", () => {
    const { container } = render(<ArticleGrid articles={[article]} />);
    const list = container.querySelector("ul");

    expect(list?.className).toContain("grid");
    expect(list?.className).toContain("md:grid-cols-2");
    expect(list?.className).toContain("xl:grid-cols-3");
  });
});

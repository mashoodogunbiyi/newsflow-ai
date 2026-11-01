import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { SourcePanel } from "@/components/articles/source-panel";
import type { ArticleDetail } from "@/types/article";

const article: ArticleDetail = {
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
  generation: {
    allowed: true,
    status: "available",
  },
};

describe("selected article source panel", () => {
  afterEach(() => cleanup());

  test("displays only permitted source information and a safe original link", () => {
    const { container } = render(<SourcePanel article={article} />);

    expect(screen.getByRole("heading", { name: article.title })).toBeDefined();
    expect(screen.getByText(article.attribution.display_name)).toBeDefined();
    expect(screen.getByText("12 October 2026")).toBeDefined();
    expect(screen.getByText("Technology")).toBeDefined();
    expect(screen.getByText(article.description as string)).toBeDefined();
    expect(screen.getByText(article.source_url)).toBeDefined();
    expect(screen.getByText(article.attribution.text)).toBeDefined();
    expect(
      screen.getByText(/AI output must be checked against the original source/i),
    ).toBeDefined();

    const source = screen.getByRole("link", {
      name: `Open original source for ${article.title}`,
    });
    expect(source.getAttribute("href")).toBe(article.source_url);
    expect(source.getAttribute("target")).toBe("_blank");
    expect(source.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByRole("link", { name: "Continue with this source" })).toBeDefined();

    const details = container.querySelector("dl");
    expect(details?.className).toContain("sm:grid-cols-2");
    expect(details?.className).toContain("xl:grid-cols-4");
  });

  test("disables continuation when current generation rights are restricted", () => {
    render(
      <SourcePanel
        article={{
          ...article,
          generation: { allowed: false, status: "restricted" },
        }}
      />,
    );

    expect(screen.getByText("AI generation restricted")).toBeDefined();
    expect(screen.getByRole("button", { name: "Continue with this source" })).toHaveProperty(
      "disabled",
      true,
    );
    expect(screen.queryByRole("link", { name: "Continue with this source" })).toBeNull();
  });

  test("explains insufficient authorised grounding without inventing a summary", () => {
    render(
      <SourcePanel
        article={{
          ...article,
          description: null,
          generation: {
            allowed: false,
            status: "insufficient_source_information",
          },
        }}
      />,
    );

    expect(screen.getByText("More source information required")).toBeDefined();
    expect(screen.getByText(/will not invent missing source information/i)).toBeDefined();
  });

  test("renders HTML-like source data as text", () => {
    const unsafeLookingTitle = '<img src=x onerror="alert(1)"> Synthetic title';
    const { container } = render(
      <SourcePanel article={{ ...article, title: unsafeLookingTitle }} />,
    );

    expect(screen.getByText(unsafeLookingTitle)).toBeDefined();
    expect(container.querySelector("img")).toBeNull();
  });
});

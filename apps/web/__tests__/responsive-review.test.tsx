import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ArticleGrid } from "@/components/articles/article-grid";
import { CatalogueControls } from "@/components/articles/article-catalogue";
import { SourcePanel } from "@/components/articles/source-panel";
import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import { AppShell } from "@/components/layout/app-shell";
import type { Article, ArticleDetail } from "@/types/article";
import type { DraftEditorDocument } from "@/types/draft";

const navigation = vi.hoisted(() => ({
  pathname: "/dashboard",
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => navigation,
}));

const article: Article = {
  id: "10000000-0000-4000-8000-000000000003",
  title: "Synthetic technology update with a deliberately long but readable title",
  description: "A fictional summary used to verify responsive article presentation.",
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

const articleDetail: ArticleDetail = {
  ...article,
  generation: { allowed: true, status: "available" },
};

const draft: DraftEditorDocument = {
  articleId: article.id,
  generatedText: `A long draft remains readable on narrow screens. ${"reviewed context ".repeat(30)}`,
  generationId: "20000000-0000-4000-8000-000000000004",
  groundingStatus: "passed_automated_checks",
  length: "medium",
  sourceAttribution: article.attribution.text,
  sourceName: article.attribution.display_name,
  sourceTitle: article.title,
  sourceUrl: article.source_url,
  validationWarnings: [],
};

describe("NFA-65 responsive layout contracts", () => {
  afterEach(() => cleanup());

  test("the workspace shell switches between mobile and desktop navigation without fixed content widths", () => {
    const { container } = render(
      <AppShell userEmail="member@example.com">
        <h1>Workspace content</h1>
      </AppShell>,
    );

    expect(container.querySelector("aside")?.className).toContain("lg:flex");
    expect(container.querySelector("header")?.className).toContain("lg:hidden");
    expect(container.querySelector("main")?.className).toContain("w-full");
    expect(container.querySelector("main")?.className).toContain("sm:px-8");
    expect(container.querySelector("main")?.className).toContain("lg:px-12");
    expect(container.querySelector(".min-w-0")).not.toBeNull();
  });

  test("dashboard filters and article cards adapt at tablet and desktop breakpoints", () => {
    const { container } = render(
      <>
        <CatalogueControls category="technology" sort="newest" />
        <ArticleGrid articles={[article]} />
      </>,
    );

    const form = container.querySelector("form");
    const list = container.querySelector("ul");
    expect(form?.className).toContain("sm:grid-cols-2");
    expect(form?.className).toContain("xl:grid-cols-");
    expect(list?.className).toContain("md:grid-cols-2");
    expect(list?.className).toContain("xl:grid-cols-3");
  });

  test("source identifiers, editor text, preview text, and controls remain overflow safe", () => {
    render(
      <>
        <SourcePanel article={articleDetail} />
        <LinkedInEditor draft={draft} />
      </>,
    );

    expect(screen.getByText(article.id).className).toContain("break-all");
    const editor = screen.getByRole("textbox", { name: "LinkedIn draft text" });
    expect(editor.className).toContain("w-full");
    expect(screen.getByTestId("draft-preview").className).toContain("break-words");
    expect(screen.getByLabelText("LinkedIn-inspired preview").className).toContain("min-w-0");
    expect(editor.closest("section")?.parentElement?.className).toContain(
      "xl:grid-cols-[1.08fr_0.92fr]",
    );
    expect(screen.getByRole("button", { name: "Generate image" }).className).toContain("w-full");
  });
});

import { cleanup, render } from "@testing-library/react";
import axe from "axe-core";
import { afterAll, afterEach, beforeAll, describe, expect, test, vi } from "vitest";

import Home from "@/app/page";
import { ArticleCard } from "@/components/articles/article-card";
import { CatalogueControls } from "@/components/articles/article-catalogue";
import { SourcePanel } from "@/components/articles/source-panel";
import { AuthPageShell } from "@/components/auth/auth-page-shell";
import { CredentialsForm } from "@/components/auth/credentials-form";
import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import { AppShell } from "@/components/layout/app-shell";
import type { ArticleDetail } from "@/types/article";
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

const article: ArticleDetail = {
  id: "10000000-0000-4000-8000-000000000003",
  title: "Synthetic technology update",
  description: "A fictional summary used for accessibility testing.",
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
  generation: { allowed: true, status: "available" },
};

const draft: DraftEditorDocument = {
  articleId: article.id,
  generatedText: "A synthetic draft prepared for human review.",
  generationId: "20000000-0000-4000-8000-000000000004",
  groundingStatus: "passed_automated_checks",
  length: "medium",
  sourceAttribution: article.attribution.text,
  sourceName: article.attribution.display_name,
  sourceTitle: article.title,
  sourceUrl: article.source_url,
  validationWarnings: [],
};

async function expectNoAxeViolations(container: HTMLElement) {
  const result = await axe.run(container, {
    rules: {
      // jsdom has no layout or canvas. Contrast is covered by the separate
      // deterministic WCAG contrast-token tests and manual browser review.
      "color-contrast": { enabled: false },
    },
  });
  expect(
    result.violations.map((violation) => ({
      id: violation.id,
      nodes: violation.nodes.map((node) => node.target),
    })),
  ).toEqual([]);
}

describe("NFA-65 automated accessibility audit", () => {
  let canvasContextSpy: ReturnType<typeof vi.spyOn>;

  beforeAll(() => {
    canvasContextSpy = vi
      .spyOn(HTMLCanvasElement.prototype, "getContext")
      .mockImplementation(() => null);
  });

  afterAll(() => canvasContextSpy.mockRestore());
  afterEach(() => cleanup());

  test("homepage has no detectable WCAG A or AA structural violations", async () => {
    const { container } = render(<Home />);
    await expectNoAxeViolations(container);
  });

  test("authentication shell and labelled form pass the automated audit", async () => {
    const { container } = render(
      <AuthPageShell
        alternateHref="/register"
        alternateLabel="Create account"
        alternatePrompt="New here?"
        description="Sign in to continue to your private workspace."
        eyebrow="Welcome back"
        title="Sign in securely."
      >
        <CredentialsForm mode="login" />
      </AuthPageShell>,
    );
    await expectNoAxeViolations(container);
  });

  test("responsive workspace shell and navigation pass the automated audit", async () => {
    const { container } = render(
      <AppShell userEmail="member@example.com">
        <h1>Authorised article dashboard</h1>
        <p>Rights-approved synthetic records.</p>
      </AppShell>,
    );
    await expectNoAxeViolations(container);
  });

  test("article discovery card and filter controls pass the automated audit", async () => {
    const { container } = render(
      <main>
        <h1>Authorised article dashboard</h1>
        <CatalogueControls category="technology" search="synthetic" sort="newest" />
        <section aria-label="Authorised articles">
          <ArticleCard article={article} />
        </section>
      </main>,
    );
    await expectNoAxeViolations(container);
  });

  test("source panel, editor, image controls, and preview pass the automated audit", async () => {
    const { container } = render(
      <main>
        <h1>Create a post</h1>
        <SourcePanel article={article} />
        <LinkedInEditor draft={draft} />
      </main>,
    );
    await expectNoAxeViolations(container);
  });
});

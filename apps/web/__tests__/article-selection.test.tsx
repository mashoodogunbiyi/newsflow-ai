import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { ArticleSelection } from "@/components/articles/article-selection";

describe("article selection", () => {
  afterEach(() => cleanup());

  test("preserves only the selected article identifier in the creation URL", () => {
    render(<ArticleSelection articleId="10000000-0000-4000-8000-000000000003" />);

    const link = screen.getByRole("link", { name: "Select article" });
    expect(link.getAttribute("href")).toBe(
      "/generate?articleId=10000000-0000-4000-8000-000000000003",
    );
    expect(link.getAttribute("href")).not.toContain("title");
  });
});

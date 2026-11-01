import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { LinkedInPreview } from "@/components/preview/linkedin-preview";
import type { LinkedInPreviewContent, PreviewImageSelection } from "@/types/preview";

const imageOne: PreviewImageSelection = {
  altText: "Conceptual network nodes surrounding a reviewed news document",
  id: "10000000-0000-4000-8000-000000000031",
};
const imageTwo: PreviewImageSelection = {
  altText: "Abstract green pathways representing verified information",
  id: "20000000-0000-4000-8000-000000000032",
};

const content: LinkedInPreviewContent = {
  draftText: "A reviewed opening paragraph.\n\nA second paragraph with context.",
  groundingStatus: "passed_automated_checks",
  image: imageOne,
  source: {
    attribution: "Source: NewsFlow AI synthetic fixture - not live news",
    name: "NewsFlow AI synthetic fixture",
    title: "Synthetic technology update",
    url: "https://example.invalid/newsflow-ai/fixture-technology-001",
  },
  warnings: [],
};

describe("LinkedIn-inspired content preview", () => {
  afterEach(() => cleanup());

  test("renders multiline draft text, source attribution, and preview limitations", () => {
    render(<LinkedInPreview {...content} />);

    const draft = screen.getByTestId("draft-preview");
    expect(draft.textContent).toBe(content.draftText);
    expect(draft.className).toContain("whitespace-pre-wrap");
    expect(screen.getByText(content.source.title)).toBeDefined();
    expect(screen.getByText(content.source.attribution)).toBeDefined();
    expect(screen.getByRole("link", { name: "Review the original source" })).toHaveProperty(
      "href",
      content.source.url,
    );
    expect(screen.getByText(/not affiliated with LinkedIn/i)).toBeDefined();
    expect(screen.queryByText(/likes|comments|reposts/i)).toBeNull();
  });

  test("displays a selected private illustration with accessible AI labelling", () => {
    render(<LinkedInPreview {...content} />);

    const image = screen.getByRole("img", { name: imageOne.altText });
    expect(new URL(image.getAttribute("src") ?? "").pathname).toBe(
      `/api/images/${imageOne.id}/content`,
    );
    expect(screen.getByText("AI-generated illustration")).toBeDefined();
    expect(screen.getByText("Not authentic news photography")).toBeDefined();
  });

  test("updates when the edited draft or selected image changes", () => {
    const { rerender } = render(<LinkedInPreview {...content} />);

    rerender(
      <LinkedInPreview {...content} draftText="A newly reviewed version." image={imageTwo} />,
    );

    expect(screen.getByTestId("draft-preview").textContent).toBe("A newly reviewed version.");
    expect(
      new URL(screen.getByRole("img", { name: imageTwo.altText }).getAttribute("src") ?? "")
        .pathname,
    ).toBe(`/api/images/${imageTwo.id}/content`);
    expect(screen.queryByRole("img", { name: imageOne.altText })).toBeNull();
  });

  test("keeps the text preview usable when no image is selected", () => {
    render(<LinkedInPreview {...content} image={null} />);

    expect(screen.getByTestId("preview-image-empty")).toBeDefined();
    expect(screen.getByText("No illustration selected")).toBeDefined();
    expect(screen.getByTestId("draft-preview").textContent).toBe(content.draftText);
  });

  test("uses a controlled fallback when private image delivery fails", () => {
    render(<LinkedInPreview {...content} />);

    fireEvent.error(screen.getByRole("img", { name: imageOne.altText }));

    expect(screen.getByRole("status").textContent).toContain("Illustration unavailable");
    expect(screen.queryByRole("img", { name: imageOne.altText })).toBeNull();
    expect(screen.getByTestId("draft-preview").textContent).toBe(content.draftText);
  });

  test("handles empty drafts and renders HTML-like text literally", () => {
    const unsafeText = '<script>alert("not executed")</script>';
    const { rerender } = render(<LinkedInPreview {...content} draftText="" />);

    expect(screen.getByTestId("draft-preview").textContent).toBe(
      "Your edited draft will appear here.",
    );

    rerender(<LinkedInPreview {...content} draftText={unsafeText} />);
    const draft = screen.getByTestId("draft-preview");
    expect(draft.textContent).toBe(unsafeText);
    expect(draft.querySelector("script")).toBeNull();
  });

  test("shows automated warnings and rejects an unsafe source link", () => {
    render(
      <LinkedInPreview
        {...content}
        groundingStatus="review_required"
        source={{ ...content.source, url: "javascript:alert('unsafe')" }}
        warnings={[
          {
            category: "unsupported_claim",
            code: "unsupported_claim_review",
            message: "Check the numerical claim against the selected source.",
            severity: "review",
          },
        ]}
      />,
    );

    expect(screen.getByText("1 automated review warning")).toBeDefined();
    expect(
      screen.getByText("Check the numerical claim against the selected source."),
    ).toBeDefined();
    expect(screen.getByText("Source link unavailable.")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Review the original source" })).toBeNull();
  });

  test("uses fluid and responsive layout classes without fixed viewport widths", () => {
    const { container } = render(<LinkedInPreview {...content} />);

    const previewCard = container.querySelector(".w-full");
    expect(previewCard).not.toBeNull();
    expect(previewCard?.className).toContain("sm:rounded-3xl");
    expect(previewCard?.className).toContain("overflow-hidden");
  });
});

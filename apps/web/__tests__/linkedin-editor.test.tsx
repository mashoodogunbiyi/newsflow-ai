import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import type { DraftEditorDocument } from "@/types/draft";

const draft: DraftEditorDocument = {
  articleId: "10000000-0000-4000-8000-000000000003",
  generatedText: "A synthetic draft for review.\n\n#ResponsibleAI",
  generationId: "20000000-0000-4000-8000-000000000004",
  groundingStatus: "passed_automated_checks",
  length: "medium",
  sourceAttribution: "Source: NewsFlow AI synthetic fixture - not live news",
  sourceName: "NewsFlow AI synthetic fixture",
  sourceTitle: "Synthetic technology update",
  sourceUrl: "https://example.invalid/newsflow-ai/fixture-technology-001",
  validationWarnings: [],
};

describe("LinkedIn draft editor", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  test("loads the generated draft with its source and human-review guidance", () => {
    render(<LinkedInEditor draft={draft} />);

    expect(screen.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveProperty(
      "value",
      draft.generatedText,
    );
    expect(screen.getByText(draft.sourceTitle)).toBeDefined();
    expect(screen.getByText(draft.sourceAttribution)).toBeDefined();
    expect(screen.getByText(/human fact-check required/i)).toBeDefined();
    expect(screen.getByText(/nothing is saved or published automatically/i)).toBeDefined();
  });

  test("updates editable text, character count, and preview without a backend request", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<LinkedInEditor draft={draft} />);
    const textarea = screen.getByRole("textbox", { name: "LinkedIn draft text" });
    const edited = "My reviewed opening.\n\nA second paragraph.";

    fireEvent.change(textarea, { target: { value: edited } });

    expect(textarea).toHaveProperty("value", edited);
    expect(screen.getByLabelText("Draft character count").textContent).toContain(
      `${edited.length} characters`,
    );
    expect(screen.getByTestId("draft-preview").textContent).toBe(edited);
    expect(screen.getByText("Unsaved local edits")).toBeDefined();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("integrates a selected illustration into the live preview", () => {
    const selectedImage = {
      altText: "Conceptual illustration of a reviewed information network",
      id: "10000000-0000-4000-8000-000000000031",
    };
    render(<LinkedInEditor draft={draft} selectedImage={selectedImage} />);

    const image = screen.getByRole("img", { name: selectedImage.altText });
    expect(new URL(image.getAttribute("src") ?? "").pathname).toBe(
      `/api/images/${selectedImage.id}/content`,
    );
    expect(screen.getByText("AI-generated illustration")).toBeDefined();
  });

  test("handles an empty draft and keeps the textarea available", () => {
    render(<LinkedInEditor draft={{ ...draft, generatedText: "" }} />);

    expect(screen.getByText("Generated draft loaded")).toBeDefined();
    expect(screen.getByText(/the draft is empty/i)).toBeDefined();
    expect(screen.getByTestId("draft-preview").textContent).toContain(
      "Your edited draft will appear here.",
    );
    expect(screen.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveProperty(
      "value",
      "",
    );
  });

  test("displays every grounding warning and preserves it after editing", () => {
    const warningDraft: DraftEditorDocument = {
      ...draft,
      groundingStatus: "review_required",
      validationWarnings: [
        {
          category: "unsupported_claim",
          code: "unsupported_claim_review",
          message: "Check the numerical claim against the selected source.",
          severity: "review",
        },
      ],
    };
    render(<LinkedInEditor draft={warningDraft} />);

    fireEvent.change(screen.getByRole("textbox", { name: "LinkedIn draft text" }), {
      target: { value: "Edited after reviewing the source." },
    });

    expect(screen.getByText(warningDraft.validationWarnings[0].message)).toBeDefined();
    expect(screen.getByText(/warnings remain visible after editing/i)).toBeDefined();
  });

  test("preserves edits during rerenders and refuses to overwrite them with a newer draft", () => {
    const { rerender } = render(<LinkedInEditor draft={draft} />);
    const textarea = screen.getByRole("textbox", { name: "LinkedIn draft text" });
    fireEvent.change(textarea, { target: { value: "My protected local edit." } });

    rerender(<LinkedInEditor draft={{ ...draft }} />);
    expect(textarea).toHaveProperty("value", "My protected local edit.");

    const newerDraft = {
      ...draft,
      generatedText: "A newly generated alternative.",
      generationId: "30000000-0000-4000-8000-000000000005",
    };
    rerender(<LinkedInEditor draft={newerDraft} />);

    expect(screen.getByText(/a newer generated draft is available/i)).toBeDefined();
    expect(textarea).toHaveProperty("value", "My protected local edit.");

    fireEvent.click(screen.getByRole("button", { name: "Replace my edits" }));
    expect(textarea).toHaveProperty("value", newerDraft.generatedText);
    expect(screen.getByText("Generated draft loaded")).toBeDefined();
  });

  test("warns before navigation would discard local edits", () => {
    const confirm = vi.fn(() => false);
    vi.stubGlobal("confirm", confirm);
    render(
      <>
        <a href="/dashboard">Leave editor</a>
        <LinkedInEditor draft={draft} />
      </>,
    );
    fireEvent.change(screen.getByRole("textbox", { name: "LinkedIn draft text" }), {
      target: { value: "Unsaved local edit." },
    });

    fireEvent.click(screen.getByRole("link", { name: "Leave editor" }));

    expect(confirm).toHaveBeenCalledWith(
      "You have unsaved draft edits. Leave this page and discard those local changes?",
    );

    const beforeUnload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(beforeUnload);
    expect(beforeUnload.defaultPrevented).toBe(true);
  });

  test("renders HTML-like user text literally instead of executing it", () => {
    render(<LinkedInEditor draft={draft} />);
    const unsafeText = '<img src="x" onerror="alert(1)">Reviewed text';

    fireEvent.change(screen.getByRole("textbox", { name: "LinkedIn draft text" }), {
      target: { value: unsafeText },
    });

    const preview = screen.getByTestId("draft-preview");
    expect(preview.textContent).toBe(unsafeText);
    expect(preview.querySelector("img")).toBeNull();
  });

  test("provides native keyboard editing and configured length guidance", () => {
    render(<LinkedInEditor draft={draft} />);
    const textarea = screen.getByRole("textbox", { name: "LinkedIn draft text" });

    textarea.focus();
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(document.activeElement).toBe(textarea);
    expect(screen.getByText(/medium application guidance/i)).toBeDefined();
    expect(screen.getByText(/not a claimed LinkedIn platform limit/i)).toBeDefined();
  });

  test("shows a controlled state when no valid generation response is available", () => {
    render(<LinkedInEditor draft={null} />);

    expect(screen.getByRole("alert").textContent).toContain(
      "The generated draft could not be loaded.",
    );
    expect(screen.queryByRole("textbox", { name: "LinkedIn draft text" })).toBeNull();
  });
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import type { DraftEditorDocument } from "@/types/draft";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const imageId = "10000000-0000-4000-8000-000000000071";
const originalCreateObjectUrl = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const originalRevokeObjectUrl = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
const draft: DraftEditorDocument = {
  articleId: "10000000-0000-4000-8000-000000000003",
  generatedText: "Original draft.\n\nA second paragraph.",
  generationId: "20000000-0000-4000-8000-000000000004",
  groundingStatus: "passed_automated_checks",
  length: "medium",
  sourceAttribution: "Source: NewsFlow AI synthetic fixture - not live news",
  sourceName: "NewsFlow AI synthetic fixture",
  sourceTitle: "Synthetic technology update",
  sourceUrl: "https://example.invalid/newsflow-ai/fixture-technology-001",
  validationWarnings: [],
};

describe("NFA-71 content export", () => {
  const clipboardWrite = vi.fn();
  const anchorClick = vi.fn();

  beforeEach(() => {
    clipboardWrite.mockReset();
    anchorClick.mockReset();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboardWrite },
    });
    vi.stubGlobal("fetch", vi.fn());
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:newsflow-export"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(anchorClick);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    if (originalCreateObjectUrl) {
      Object.defineProperty(URL, "createObjectURL", originalCreateObjectUrl);
    } else {
      Reflect.deleteProperty(URL, "createObjectURL");
    }
    if (originalRevokeObjectUrl) {
      Object.defineProperty(URL, "revokeObjectURL", originalRevokeObjectUrl);
    } else {
      Reflect.deleteProperty(URL, "revokeObjectURL");
    }
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
  });

  test("copies the current edited plain text with line breaks and confirms success", async () => {
    clipboardWrite.mockResolvedValue(undefined);
    render(<LinkedInEditor draft={draft} />);
    const edited = "My reviewed opening.\n\nMy reviewed conclusion.\n\n#NewsFlowAI";
    fireEvent.change(screen.getByRole("textbox", { name: "LinkedIn draft text" }), {
      target: { value: edited },
    });

    fireEvent.click(screen.getByRole("button", { name: "Copy Post" }));

    await waitFor(() => expect(clipboardWrite).toHaveBeenCalledWith(edited));
    expect(
      screen.getByText("Current edited post copied with its line breaks preserved."),
    ).toBeDefined();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("reports clipboard permission failures without changing the editor", async () => {
    clipboardWrite.mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
    render(<LinkedInEditor draft={draft} />);

    fireEvent.click(screen.getByRole("button", { name: "Copy Post" }));

    expect(
      await screen.findByText(
        "Clipboard access was denied. Check your browser permission and try again.",
      ),
    ).toBeDefined();
    expect(screen.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveProperty(
      "value",
      draft.generatedText,
    );
  });

  test("reports when the browser clipboard API is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
    render(<LinkedInEditor draft={draft} />);

    fireEvent.click(screen.getByRole("button", { name: "Copy Post" }));

    expect(
      await screen.findByText("Clipboard copying is not supported by this browser."),
    ).toBeDefined();
  });

  test("prevents an empty draft from being copied", () => {
    render(<LinkedInEditor draft={{ ...draft, generatedText: "   " }} />);

    expect(screen.getByRole("button", { name: "Copy Post" })).toHaveProperty("disabled", true);
    expect(screen.getByText("Add reviewed text before copying.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Download Image" })).toHaveProperty("disabled", true);
    expect(
      screen.getByText("Select an approved generated illustration to enable download."),
    ).toBeDefined();
    expect(clipboardWrite).not.toHaveBeenCalled();
  });

  test("downloads the selected owned image with the safe response filename", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: {
          "Content-Disposition": `attachment; filename="newsflow-ai-illustration-${imageId}.png"`,
          "Content-Type": "image/png",
        },
      }),
    );
    render(
      <LinkedInEditor
        draft={draft}
        selectedImage={{ altText: "Synthetic generated illustration", id: imageId }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Download Image" }));

    expect(
      await screen.findByText("The AI-generated illustration download has started."),
    ).toBeDefined();
    expect(fetch).toHaveBeenCalledWith(`/api/images/${imageId}/download`, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });
    expect(anchorClick).toHaveBeenCalledOnce();
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:newsflow-export");
    expect(vi.mocked(fetch).mock.calls.every(([url]) => !String(url).includes("linkedin"))).toBe(
      true,
    );
  });

  test("handles expired sessions and missing images with understandable feedback", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 404 }));
    render(
      <LinkedInEditor
        draft={draft}
        selectedImage={{ altText: "Synthetic generated illustration", id: imageId }}
      />,
    );
    const button = screen.getByRole("button", { name: "Download Image" });

    fireEvent.click(button);
    expect(
      await screen.findByText("Your session has expired. Sign in again before downloading."),
    ).toBeDefined();
    fireEvent.click(button);
    expect(
      await screen.findByText("The selected illustration is no longer available."),
    ).toBeDefined();
    expect(anchorClick).not.toHaveBeenCalled();
  });

  test("keeps source, human-review, AI-image, and manual-publishing notices visible", () => {
    render(
      <LinkedInEditor
        draft={draft}
        selectedImage={{ altText: "Synthetic generated illustration", id: imageId }}
      />,
    );

    expect(screen.getByText(draft.sourceAttribution)).toBeDefined();
    expect(screen.getByText(/human fact-check required/i)).toBeDefined();
    expect(screen.getAllByText(/AI-generated illustration/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/do not publish to LinkedIn/i)).toBeDefined();
  });

  test("uses keyboard-focusable native controls", () => {
    render(
      <LinkedInEditor
        draft={draft}
        selectedImage={{ altText: "Synthetic generated illustration", id: imageId }}
      />,
    );
    const copyButton = screen.getByRole("button", { name: "Copy Post" });
    const downloadButton = screen.getByRole("button", { name: "Download Image" });

    copyButton.focus();
    expect(document.activeElement).toBe(copyButton);
    expect(copyButton.tagName).toBe("BUTTON");
    downloadButton.focus();
    expect(document.activeElement).toBe(downloadButton);
    expect(downloadButton.tagName).toBe("BUTTON");
  });
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import type { DraftEditorDocument } from "@/types/draft";

const navigation = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));

const draft: DraftEditorDocument = {
  articleId: "10000000-0000-4000-8000-000000000003",
  generatedText: "A synthetic draft for review.",
  generationId: "20000000-0000-4000-8000-000000000004",
  groundingStatus: "passed_automated_checks",
  length: "medium",
  sourceAttribution: "Source: NewsFlow AI synthetic fixture",
  sourceName: "NewsFlow AI synthetic fixture",
  sourceTitle: "Synthetic technology update",
  sourceUrl: "https://example.invalid/newsflow-ai/fixture-technology-001",
  validationWarnings: [],
};

const originalId = "20000000-0000-4000-8000-000000000005";
const childId = "20000000-0000-4000-8000-000000000006";
const postId = "20000000-0000-4000-8000-000000000007";

function imageResponse(imageId: string, parentId: string | null, sequence: number) {
  return {
    image_id: imageId,
    parent_image_id: parentId,
    generation_id: "20000000-0000-4000-8000-000000000008",
    generated_post_id: postId,
    regeneration_sequence: sequence,
    status: "completed",
    safety_status: "pending",
    is_ai_generated: true,
    review_required: true,
    created_at: "2026-11-01T12:00:00Z",
  };
}

describe("image generation controls", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    document.cookie = "newsflow_csrf=csrf-test-token; path=/";
    navigation.refresh.mockReset();
    navigation.replace.mockReset();
  });

  afterEach(() => {
    cleanup();
    document.cookie = "newsflow_csrf=; Max-Age=0; path=/";
    vi.unstubAllGlobals();
  });

  test("generates a private image and updates the live preview", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(imageResponse(originalId, null, 0)), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<LinkedInEditor draft={draft} />);

    fireEvent.click(screen.getByRole("button", { name: "Generate image" }));

    expect(await screen.findByText("Your private illustration is ready for review.")).toBeDefined();
    expect(screen.getByRole("radio", { name: "Use original in preview" })).toHaveProperty(
      "checked",
      true,
    );
    expect(screen.getByText("AI-generated illustration")).toBeDefined();
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/api/images");
  });

  test("regenerates without overwriting the original or edited draft", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify(imageResponse(originalId, null, 0)), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(imageResponse(childId, originalId, 1)), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      );
    render(<LinkedInEditor draft={draft} />);
    const textarea = screen.getByRole("textbox", { name: "LinkedIn draft text" });
    fireEvent.change(textarea, { target: { value: "My reviewed local edit." } });

    fireEvent.click(screen.getByRole("button", { name: "Generate image" }));
    await screen.findByRole("radio", { name: "Use original in preview" });
    fireEvent.click(screen.getByRole("button", { name: "Regenerate image" }));

    expect(await screen.findByRole("radio", { name: "Use version 2 in preview" })).toHaveProperty(
      "checked",
      true,
    );
    expect(screen.getByRole("radio", { name: "Use original in preview" })).toBeDefined();
    expect(textarea).toHaveProperty("value", "My reviewed local edit.");
    expect(vi.mocked(fetch).mock.calls[1]?.[0]).toBe(`/api/images/${originalId}/regenerate`);
  });

  test("prevents duplicate clicks while a provider request is active", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => undefined));
    render(<LinkedInEditor draft={draft} />);

    const button = screen.getByRole("button", { name: "Generate image" });
    fireEvent.click(button);
    fireEvent.submit(button.closest("form") as HTMLFormElement);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Generating illustration..." })).toHaveProperty(
        "disabled",
        true,
      ),
    );
    expect(fetch).toHaveBeenCalledOnce();
  });
});

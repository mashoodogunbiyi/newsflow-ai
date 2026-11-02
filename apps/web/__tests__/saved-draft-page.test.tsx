import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import SavedDraftPage from "@/app/(workspace)/library/[draftId]/page";

const draftApi = vi.hoisted(() => ({ getSavedDraft: vi.fn() }));
const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/draft-api", () => ({
  getSavedDraft: draftApi.getSavedDraft,
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
  useRouter: () => navigation,
}));

const savedDraft = {
  id: "10000000-0000-4000-8000-000000000001",
  generated_post_id: "10000000-0000-4000-8000-000000000002",
  current_post_version_id: "10000000-0000-4000-8000-000000000003",
  selected_image_id: "10000000-0000-4000-8000-000000000004",
  selected_image: {
    id: "10000000-0000-4000-8000-000000000004",
    alt_text: "Synthetic saved illustration",
    mime_type: "image/png" as const,
    width_px: 1536,
    height_px: 1024,
    ai_generated: true,
    ai_disclosure_required: true,
  },
  title: "Saved technology briefing",
  edited_text: "The exact saved text restored for another editing session.",
  tone: "professional" as const,
  length: "medium" as const,
  status: "saved" as const,
  version: 3,
  source: {
    article_id: "10000000-0000-4000-8000-000000000005",
    title: "Synthetic technology update",
    url: "https://example.invalid/newsflow/source-001",
    attribution: "Source: NewsFlow AI synthetic fixture - not live news",
  },
  generation: {
    generation_id: "10000000-0000-4000-8000-000000000006",
    original_post_version_id: "10000000-0000-4000-8000-000000000007",
    model_identifier: "synthetic-model",
    prompt_version: "linkedin_post_v1",
    created_at: "2026-11-01T09:00:00Z",
  },
  created_at: "2026-11-01T09:05:00Z",
  updated_at: "2026-11-02T10:00:00Z",
};

describe("NFA-69 saved draft reopening", () => {
  beforeEach(() => {
    draftApi.getSavedDraft.mockReset();
    navigation.redirect.mockReset();
    navigation.refresh.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("restores the saved text, source, and selected private image in the editor", async () => {
    draftApi.getSavedDraft.mockResolvedValue({ status: "success", data: savedDraft });

    render(
      await SavedDraftPage({
        params: Promise.resolve({ draftId: savedDraft.id }),
      }),
    );

    expect(draftApi.getSavedDraft).toHaveBeenCalledWith(savedDraft.id);
    expect(screen.getByText("Saved version loaded")).toBeDefined();
    expect(screen.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveProperty(
      "value",
      savedDraft.edited_text,
    );
    expect(screen.getAllByText(savedDraft.source.title).length).toBeGreaterThan(0);
    expect(screen.getByText(savedDraft.source.attribution)).toBeDefined();
    expect(screen.getByRole("img", { name: savedDraft.selected_image.alt_text })).toBeDefined();

    fireEvent.change(screen.getByRole("textbox", { name: "LinkedIn draft text" }), {
      target: { value: "A continued local edit." },
    });
    expect(screen.getByTestId("draft-preview").textContent).toBe("A continued local edit.");
    expect(screen.getByText("Unsaved local edits")).toBeDefined();
  });

  test("shows the same safe missing state for unavailable private records", async () => {
    draftApi.getSavedDraft.mockResolvedValue({ status: "error", reason: "not_found" });

    render(
      await SavedDraftPage({
        params: Promise.resolve({ draftId: savedDraft.id }),
      }),
    );

    expect(
      screen.getByRole("heading", { name: "This saved draft is no longer available." }),
    ).toBeDefined();
    expect(screen.getByText(/may not belong to this account/i)).toBeDefined();
    expect(screen.queryByRole("textbox", { name: "LinkedIn draft text" })).toBeNull();
  });

  test("redirects when the saved-draft request has no active session", async () => {
    draftApi.getSavedDraft.mockResolvedValue({
      status: "error",
      reason: "authentication_required",
    });

    await expect(
      SavedDraftPage({ params: Promise.resolve({ draftId: savedDraft.id }) }),
    ).rejects.toThrow("NEXT_REDIRECT");
    expect(navigation.redirect).toHaveBeenCalledWith("/login?reason=authentication_required");
  });
});

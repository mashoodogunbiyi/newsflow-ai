import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ContentLibrary } from "@/components/library/content-library";

const draftApi = vi.hoisted(() => ({ getSavedDraftPage: vi.fn() }));
const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/draft-api", () => ({
  getSavedDraftPage: draftApi.getSavedDraftPage,
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
    alt_text: "Synthetic illustration of a responsible technology network",
    mime_type: "image/png" as const,
    width_px: 1536,
    height_px: 1024,
    ai_generated: true,
    ai_disclosure_required: true,
  },
  title: "Responsible technology briefing",
  edited_text: "A reviewed LinkedIn draft saved for later editing.",
  tone: "professional" as const,
  length: "medium" as const,
  status: "saved" as const,
  version: 2,
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

describe("NFA-69 content library", () => {
  beforeEach(() => {
    draftApi.getSavedDraftPage.mockReset();
    navigation.redirect.mockReset();
    navigation.refresh.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("renders saved draft metadata, secure thumbnail, and keyboard-accessible links", async () => {
    draftApi.getSavedDraftPage.mockResolvedValue({
      status: "success",
      data: {
        items: [savedDraft],
        page: 1,
        page_size: 6,
        total_items: 1,
        total_pages: 1,
        sort: "updated_at_desc",
      },
    });

    const { container } = render(await ContentLibrary({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: savedDraft.title })).toBeDefined();
    expect(screen.getByText(savedDraft.edited_text)).toBeDefined();
    expect(screen.getByText(savedDraft.source.title)).toBeDefined();
    expect(screen.getByText(savedDraft.source.attribution)).toBeDefined();
    expect(screen.getByText(/last modified/i)).toBeDefined();
    const openLink = screen.getByRole("link", { name: `Open saved draft: ${savedDraft.title}` });
    expect(openLink.getAttribute("href")).toBe(`/library/${savedDraft.id}`);
    openLink.focus();
    expect(document.activeElement).toBe(openLink);
    const thumbnail = screen.getByRole("img", { name: savedDraft.selected_image.alt_text });
    expect(new URL(thumbnail.getAttribute("src") ?? "").pathname).toBe(
      `/api/images/${savedDraft.selected_image.id}/content`,
    );
    expect(container.querySelector(".md\\:grid-cols-2")).not.toBeNull();
    expect(container.querySelector(".xl\\:grid-cols-3")).not.toBeNull();
  });

  test("renders the empty-library state with a route into content creation", async () => {
    draftApi.getSavedDraftPage.mockResolvedValue({
      status: "success",
      data: {
        items: [],
        page: 1,
        page_size: 6,
        total_items: 0,
        total_pages: 0,
        sort: "updated_at_desc",
      },
    });

    render(await ContentLibrary({ searchParams: Promise.resolve({}) }));

    expect(
      screen.getByRole("heading", { name: "You have not saved any drafts yet." }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Browse authorised articles" })).toHaveProperty(
      "href",
      "http://localhost:3000/dashboard",
    );
  });

  test("uses backend pagination and provides previous and next navigation", async () => {
    draftApi.getSavedDraftPage.mockResolvedValue({
      status: "success",
      data: {
        items: [savedDraft],
        page: 2,
        page_size: 6,
        total_items: 13,
        total_pages: 3,
        sort: "updated_at_desc",
      },
    });

    render(await ContentLibrary({ searchParams: Promise.resolve({ page: "2" }) }));

    expect(draftApi.getSavedDraftPage).toHaveBeenCalledWith(2);
    expect(screen.getByText("Page 2 of 3")).toBeDefined();
    expect(screen.getByRole("link", { name: "Previous drafts" }).getAttribute("href")).toBe(
      "/library",
    );
    expect(screen.getByRole("link", { name: "Next drafts" }).getAttribute("href")).toBe(
      "/library?page=3",
    );
  });

  test("shows a safe API failure and retries with a route refresh", async () => {
    draftApi.getSavedDraftPage.mockResolvedValue({ status: "error", reason: "unavailable" });

    render(await ContentLibrary({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("alert").textContent).not.toContain("database");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(navigation.refresh).toHaveBeenCalledOnce();
  });

  test("rejects duplicated page values without calling the backend", async () => {
    render(
      await ContentLibrary({
        searchParams: Promise.resolve({ page: ["1", "2"] }),
      }),
    );

    expect(draftApi.getSavedDraftPage).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "This content-library link is not valid." }),
    ).toBeDefined();
  });

  test("redirects when the backend rejects the authenticated session", async () => {
    draftApi.getSavedDraftPage.mockResolvedValue({
      status: "error",
      reason: "authentication_required",
    });

    await expect(ContentLibrary({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "NEXT_REDIRECT",
    );
    expect(navigation.redirect).toHaveBeenCalledWith("/login?reason=authentication_required");
  });
});

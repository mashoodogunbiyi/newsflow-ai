import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  getSavedDraft,
  getSavedDraftPage,
  getSavedDraftVersion,
  getSavedDraftVersions,
  LIBRARY_PAGE_SIZE,
} from "@/lib/draft-api";

const cookieState = vi.hoisted(() => ({ session: undefined as string | undefined }));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) =>
      name === "newsflow_session" && cookieState.session
        ? { name, value: cookieState.session }
        : undefined,
  }),
}));

const savedDraft = {
  id: "10000000-0000-4000-8000-000000000001",
  generated_post_id: "10000000-0000-4000-8000-000000000002",
  current_post_version_id: "10000000-0000-4000-8000-000000000003",
  selected_image_id: "10000000-0000-4000-8000-000000000004",
  selected_image: {
    id: "10000000-0000-4000-8000-000000000004",
    alt_text: "Synthetic illustration of a responsible technology network",
    mime_type: "image/png",
    width_px: 1536,
    height_px: 1024,
    ai_generated: true,
    ai_disclosure_required: true,
  },
  title: "Responsible technology briefing",
  edited_text: "A reviewed LinkedIn draft saved for later editing.",
  tone: "professional",
  length: "medium",
  status: "saved",
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

const draftPage = {
  items: [savedDraft],
  page: 2,
  page_size: LIBRARY_PAGE_SIZE,
  total_items: 7,
  total_pages: 2,
  sort: "updated_at_desc",
};

const savedDraftVersion = {
  id: "10000000-0000-4000-8000-000000000008",
  draft_id: savedDraft.id,
  post_version_id: savedDraft.current_post_version_id,
  selected_image_id: savedDraft.selected_image_id,
  selected_image: savedDraft.selected_image,
  generation_id: null,
  restored_from_version_id: null,
  version_number: 2,
  change_type: "manual_edit",
  title: savedDraft.title,
  edited_text: savedDraft.edited_text,
  tone: savedDraft.tone,
  length: savedDraft.length,
  source: savedDraft.source,
  created_at: savedDraft.updated_at,
};

const historyPage = {
  items: [savedDraftVersion],
  page: 1,
  page_size: 20,
  total_items: 1,
  total_pages: 1,
  sort: "version_desc",
};

describe("saved draft API client", () => {
  beforeEach(() => {
    vi.stubEnv("API_INTERNAL_BASE_URL", "http://backend:8000");
    vi.stubGlobal("fetch", vi.fn());
    cookieState.session = "session-value";
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("loads a bounded owner-scoped page with the server session", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(draftPage), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getSavedDraftPage(2)).resolves.toEqual({
      status: "success",
      data: draftPage,
    });
    expect(fetch).toHaveBeenCalledWith("http://backend:8000/api/v1/drafts?page=2&page_size=6", {
      headers: {
        Accept: "application/json",
        Cookie: "newsflow_session=session-value",
      },
      cache: "no-store",
    });
  });

  test("does not contact FastAPI without a session or with an invalid page", async () => {
    cookieState.session = undefined;
    await expect(getSavedDraftPage()).resolves.toEqual({
      status: "error",
      reason: "authentication_required",
    });
    await expect(getSavedDraftPage(0)).resolves.toEqual({
      status: "error",
      reason: "invalid_request",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  test("rejects malformed collection data and unsafe image metadata", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...draftPage,
          items: [
            {
              ...savedDraft,
              selected_image: { ...savedDraft.selected_image, mime_type: "text/html" },
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(getSavedDraftPage(2)).resolves.toEqual({
      status: "error",
      reason: "unavailable",
    });
  });

  test("loads one saved draft and maps missing records safely", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify(savedDraft), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 404 }));

    await expect(getSavedDraft(savedDraft.id)).resolves.toEqual({
      status: "success",
      data: savedDraft,
    });
    expect(fetch).toHaveBeenNthCalledWith(1, `http://backend:8000/api/v1/drafts/${savedDraft.id}`, {
      headers: {
        Accept: "application/json",
        Cookie: "newsflow_session=session-value",
      },
      cache: "no-store",
    });
    await expect(getSavedDraft(savedDraft.id)).resolves.toEqual({
      status: "error",
      reason: "not_found",
    });
  });

  test("validates draft identifiers before making a backend request", async () => {
    await expect(getSavedDraft("not-a-draft-id")).resolves.toEqual({
      status: "error",
      reason: "invalid_request",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  test("loads and validates immutable draft history", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify(historyPage), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(savedDraftVersion), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    await expect(getSavedDraftVersions(savedDraft.id)).resolves.toEqual({
      status: "success",
      data: historyPage,
    });
    await expect(getSavedDraftVersion(savedDraft.id, savedDraftVersion.id)).resolves.toEqual({
      status: "success",
      data: savedDraftVersion,
    });
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      `http://backend:8000/api/v1/drafts/${savedDraft.id}/versions?page=1&page_size=20`,
      {
        headers: {
          Accept: "application/json",
          Cookie: "newsflow_session=session-value",
        },
        cache: "no-store",
      },
    );
  });

  test("rejects malformed version change types", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...historyPage,
          items: [{ ...savedDraftVersion, change_type: "history_rewrite" }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(getSavedDraftVersions(savedDraft.id)).resolves.toEqual({
      status: "error",
      reason: "unavailable",
    });
  });
});

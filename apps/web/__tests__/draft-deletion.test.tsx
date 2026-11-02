import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DeleteDraftDialog } from "@/components/library/delete-draft-dialog";

const navigation = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));

const draftId = "72000000-0000-4000-8000-000000000003";

describe("saved draft deletion", () => {
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

  test("requires explicit confirmation and allows cancellation", () => {
    render(<DeleteDraftDialog draftId={draftId} title="Synthetic draft" />);
    fireEvent.click(screen.getByRole("button", { name: "Delete draft" }));
    expect(screen.getByRole("dialog")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("sends CSRF-protected deletion and returns to the library", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<DeleteDraftDialog draftId={draftId} title="Synthetic draft" />);
    fireEvent.click(screen.getByRole("button", { name: "Delete draft" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete permanently" }));

    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/library?deleted=1"));
    expect(fetch).toHaveBeenCalledWith(`/api/drafts/${draftId}`, {
      method: "DELETE",
      headers: { "X-CSRF-Token": "csrf-test-token" },
    });
    expect(navigation.refresh).toHaveBeenCalledOnce();
  });

  test("keeps the dialog open and reports a controlled failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      Response.json({ error: { code: "unavailable" } }, { status: 503 }),
    );
    render(<DeleteDraftDialog draftId={draftId} title="Synthetic draft" />);
    fireEvent.click(screen.getByRole("button", { name: "Delete draft" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete permanently" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "The draft could not be deleted right now",
    );
    expect(screen.getByRole("dialog")).toBeDefined();
  });
});

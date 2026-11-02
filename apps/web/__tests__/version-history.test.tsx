import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { VersionHistory } from "@/components/library/version-history";
import type { SavedDraftVersion } from "@/types/library";

const DRAFT_ID = "70000000-0000-4000-8000-000000000001";

function version(
  versionNumber: number,
  changeType: SavedDraftVersion["change_type"],
): SavedDraftVersion {
  return {
    id: `70000000-0000-4000-8000-${String(versionNumber).padStart(12, "0")}`,
    draft_id: DRAFT_ID,
    post_version_id: `71000000-0000-4000-8000-${String(versionNumber).padStart(12, "0")}`,
    selected_image_id: null,
    selected_image: null,
    generation_id: null,
    restored_from_version_id: null,
    version_number: versionNumber,
    change_type: changeType,
    title: "Synthetic history",
    edited_text: `Synthetic text for version ${versionNumber}.`,
    tone: "professional",
    length: "medium",
    source: {
      article_id: "72000000-0000-4000-8000-000000000001",
      title: "Synthetic source",
      url: "https://example.invalid/nfa-70",
      attribution: "Source: synthetic authorised fixture",
    },
    created_at: `2026-11-02T10:0${versionNumber}:00Z`,
  };
}

describe("NFA-70 version history", () => {
  afterEach(() => cleanup());

  test("renders versions in supplied newest-first order with distinct change labels", () => {
    render(
      <VersionHistory
        currentVersion={3}
        draftId={DRAFT_ID}
        versions={[
          version(3, "image_regeneration"),
          version(2, "manual_edit"),
          version(1, "initial_save"),
        ]}
      />,
    );

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Review version 3",
      "Review version 2",
      "Review version 1",
    ]);
    expect(screen.getByText("Current")).toBeDefined();
    expect(screen.getByText("Image regeneration")).toBeDefined();
    expect(screen.getByText("Manual edit")).toBeDefined();
    expect(screen.getByText("Initial save")).toBeDefined();
    expect(links[1]).toHaveProperty(
      "href",
      `http://localhost:3000/library/${DRAFT_ID}/versions/70000000-0000-4000-8000-000000000002`,
    );
  });
});

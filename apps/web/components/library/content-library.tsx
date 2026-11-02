import { redirect } from "next/navigation";

import { DraftList } from "@/components/library/draft-list";
import { LibraryEmptyState } from "@/components/library/library-empty-state";
import { LibraryErrorState } from "@/components/library/library-error-state";
import { LibraryPagination } from "@/components/library/library-pagination";
import { getSavedDraftPage } from "@/lib/draft-api";

export type LibrarySearchParams = {
  page?: string | string[];
};

function parsePage(value: string | string[] | undefined) {
  if (value === undefined) {
    return 1;
  }
  if (Array.isArray(value) || !/^[1-9][0-9]*$/.test(value)) {
    return null;
  }
  const page = Number(value);
  return Number.isSafeInteger(page) ? page : null;
}

export async function ContentLibrary({
  searchParams,
}: {
  searchParams: Promise<LibrarySearchParams>;
}) {
  const page = parsePage((await searchParams).page);
  const result = page
    ? await getSavedDraftPage(page)
    : ({ status: "error", reason: "invalid_request" } as const);

  if (result.status === "error") {
    if (result.reason === "authentication_required") {
      redirect("/login?reason=authentication_required");
    }
    return <LibraryErrorState reason={result.reason} />;
  }
  if (result.data.items.length === 0 && result.data.total_items === 0) {
    return <LibraryEmptyState />;
  }
  if (result.data.items.length === 0 || result.data.page > result.data.total_pages) {
    return <LibraryErrorState reason="invalid_request" />;
  }

  return (
    <section aria-labelledby="saved-drafts-title">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2
            className="text-2xl font-semibold tracking-[-0.03em] text-emerald-950"
            id="saved-drafts-title"
          >
            Saved drafts
          </h2>
          <p className="mt-2 text-sm leading-6 text-emerald-950/70">
            {result.data.total_items} private saved{" "}
            {result.data.total_items === 1 ? "draft" : "drafts"}, newest updates first.
          </p>
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">
          Up to {result.data.page_size} per page
        </p>
      </div>
      <DraftList drafts={result.data.items} />
      <LibraryPagination page={result.data.page} totalPages={result.data.total_pages} />
    </section>
  );
}

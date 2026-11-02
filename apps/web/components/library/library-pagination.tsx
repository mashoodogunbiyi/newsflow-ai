import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";

function libraryPageHref(page: number) {
  return page === 1 ? "/library" : `/library?page=${page}`;
}

export function LibraryPagination({ page, totalPages }: { page: number; totalPages: number }) {
  return (
    <nav
      aria-label="Content library pagination"
      className="mt-8 flex flex-col items-center justify-between gap-4 rounded-3xl border border-emerald-950/10 bg-white px-5 py-4 sm:flex-row"
    >
      <p className="text-sm text-emerald-950/70">
        Page {page} of {totalPages}
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        {page > 1 ? (
          <Link
            className={buttonStyles("secondary")}
            href={libraryPageHref(page - 1)}
            prefetch={false}
            rel="prev"
          >
            Previous drafts
          </Link>
        ) : (
          <span className="inline-flex min-h-11 items-center px-3 text-sm font-semibold text-emerald-950/55">
            First page
          </span>
        )}
        {page < totalPages ? (
          <Link
            className={buttonStyles("primary")}
            href={libraryPageHref(page + 1)}
            prefetch={false}
            rel="next"
          >
            Next drafts
          </Link>
        ) : (
          <span className="inline-flex min-h-11 items-center px-3 text-sm font-semibold text-emerald-950/55">
            End of library
          </span>
        )}
      </div>
    </nav>
  );
}

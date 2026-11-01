import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";

type ArticleEmptyStateProps = {
  categoryLabel?: string;
  clearCategoryHref?: string;
  clearSearchHref?: string;
  hasSearch: boolean;
};

export function ArticleEmptyState({
  categoryLabel,
  clearCategoryHref,
  clearSearchHref,
  hasSearch,
}: ArticleEmptyStateProps) {
  return (
    <section className="rounded-3xl border border-emerald-950/10 bg-white px-6 py-14 text-center">
      <div className="mx-auto max-w-xl">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
          Authorised catalogue
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          {categoryLabel
            ? `No articles found in ${categoryLabel}.`
            : hasSearch
              ? "No matching articles were found."
              : "No articles are available right now."}
        </h2>
        <p className="mt-4 leading-7 text-emerald-950/60">
          {categoryLabel
            ? "No currently permitted articles match this category and search state. Clear the category or choose another one."
            : hasSearch
              ? "Try another topic or clear the search to see all currently permitted fixture articles."
              : "Only rights-approved article metadata appears here. Live CNN access remains disabled while authorisation is pending."}
        </p>
        {categoryLabel && clearCategoryHref ? (
          <Link className={`${buttonStyles("secondary")} mt-7`} href={clearCategoryHref}>
            Clear category filter
          </Link>
        ) : hasSearch ? (
          <Link
            className={`${buttonStyles("secondary")} mt-7`}
            href={clearSearchHref ?? "/dashboard"}
          >
            Clear search
          </Link>
        ) : null}
      </div>
    </section>
  );
}

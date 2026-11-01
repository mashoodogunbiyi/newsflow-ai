import Link from "next/link";
import { redirect } from "next/navigation";

import { ArticleEmptyState } from "@/components/articles/article-empty-state";
import { ArticleErrorState } from "@/components/articles/article-error-state";
import { ArticleGrid } from "@/components/articles/article-grid";
import { buttonStyles } from "@/components/ui/button";
import { getArticlePage, type ArticleSort } from "@/lib/article-api";

export type DashboardSearchParams = {
  cursor?: string | string[];
  search?: string | string[];
  sort?: string | string[];
};

type ArticleCatalogueProps = {
  searchParams: Promise<DashboardSearchParams>;
};

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function normaliseSearch(value: string | string[] | undefined) {
  const cleaned = firstValue(value)?.trim();
  return cleaned || undefined;
}

function normaliseSort(value: string | string[] | undefined): ArticleSort {
  return firstValue(value) === "oldest" ? "oldest" : "newest";
}

function dashboardHref({
  cursor,
  search,
  sort,
}: {
  cursor?: string;
  search?: string;
  sort: ArticleSort;
}) {
  const parameters = new URLSearchParams();
  if (cursor) {
    parameters.set("cursor", cursor);
  }
  if (search) {
    parameters.set("search", search);
  }
  if (sort !== "newest") {
    parameters.set("sort", sort);
  }
  const query = parameters.toString();
  return query ? `/dashboard?${query}` : "/dashboard";
}

function CatalogueControls({ search, sort }: { search?: string; sort: ArticleSort }) {
  return (
    <form
      action="/dashboard"
      className="grid gap-4 rounded-3xl border border-emerald-950/10 bg-white p-5 shadow-sm sm:grid-cols-[minmax(0,1fr)_11rem_auto] sm:items-end sm:p-6"
      method="get"
    >
      <div>
        <label className="text-sm font-semibold text-emerald-950" htmlFor="article-search">
          Search permitted topics
        </label>
        <input
          className="mt-2 min-h-11 w-full rounded-2xl border border-emerald-950/15 bg-white px-4 py-2.5 text-sm text-emerald-950 outline-none transition placeholder:text-emerald-950/35 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/15"
          defaultValue={search}
          id="article-search"
          maxLength={200}
          name="search"
          placeholder="For example: technology"
          type="search"
        />
      </div>
      <div>
        <label className="text-sm font-semibold text-emerald-950" htmlFor="article-sort">
          Publication order
        </label>
        <select
          className="mt-2 min-h-11 w-full rounded-2xl border border-emerald-950/15 bg-white px-4 py-2.5 text-sm text-emerald-950 outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/15"
          defaultValue={sort}
          id="article-sort"
          name="sort"
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>
      <button className={buttonStyles("primary")} type="submit">
        Find articles
      </button>
    </form>
  );
}

export async function ArticleCatalogue({ searchParams }: ArticleCatalogueProps) {
  const parameters = await searchParams;
  const cursor = firstValue(parameters.cursor)?.trim() || undefined;
  const search = normaliseSearch(parameters.search);
  const sort = normaliseSort(parameters.sort);
  const result = await getArticlePage({ cursor, search, sort });

  if (result.status === "error" && result.reason === "authentication_required") {
    redirect("/login?reason=authentication_required");
  }

  return (
    <section aria-labelledby="article-catalogue-title" className="mt-8">
      <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2
            className="text-2xl font-semibold tracking-[-0.03em] text-emerald-950"
            id="article-catalogue-title"
          >
            Authorised article catalogue
          </h2>
          <p className="mt-2 text-sm leading-6 text-emerald-950/60">
            Only approved metadata and required source attribution are displayed.
          </p>
        </div>
        {search ? (
          <Link className={buttonStyles("quiet")} href="/dashboard">
            Clear search
          </Link>
        ) : null}
      </div>

      <CatalogueControls search={search} sort={sort} />

      <div className="mt-5">
        {result.status === "error" ? (
          <ArticleErrorState invalidRequest={result.reason === "invalid_request"} />
        ) : result.data.items.length === 0 ? (
          <ArticleEmptyState hasSearch={Boolean(search)} />
        ) : (
          <>
            <ArticleGrid articles={result.data.items} />
            <nav
              aria-label="Article catalogue pagination"
              className="mt-8 flex flex-col items-center justify-between gap-4 rounded-3xl border border-emerald-950/10 bg-white px-5 py-4 sm:flex-row"
            >
              <p className="text-sm text-emerald-950/55">
                Showing up to 9 rights-approved articles on this page.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                {cursor ? (
                  <Link
                    className={buttonStyles("secondary")}
                    href={dashboardHref({ search, sort })}
                    prefetch={false}
                  >
                    First page
                  </Link>
                ) : null}
                {result.data.next_cursor ? (
                  <Link
                    className={buttonStyles("primary")}
                    href={dashboardHref({ cursor: result.data.next_cursor, search, sort })}
                    prefetch={false}
                  >
                    Next articles
                  </Link>
                ) : (
                  <span className="inline-flex min-h-11 items-center px-3 text-sm font-semibold text-emerald-950/45">
                    End of catalogue
                  </span>
                )}
              </div>
            </nav>
          </>
        )}
      </div>
    </section>
  );
}

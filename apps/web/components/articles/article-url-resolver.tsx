import Link from "next/link";
import { redirect } from "next/navigation";

import type { DashboardSearchParams } from "@/components/articles/article-catalogue";
import { buttonStyles } from "@/components/ui/button";
import { normaliseSourceUrl, resolveArticleUrl } from "@/lib/article-api";

const DEMO_ARTICLE_URL = "https://example.invalid/newsflow/synthetic-clean-energy";

type ArticleUrlResolverProps = {
  searchParams: Promise<DashboardSearchParams>;
};

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function errorMessage(reason: "invalid_request" | "not_found" | "unavailable") {
  if (reason === "invalid_request") {
    return "Enter one complete HTTPS article URL without a username, password, or page fragment.";
  }
  if (reason === "not_found") {
    return "That URL is not in the approved article catalogue yet. Choose an article below or ask an administrator to add it through an authorised source.";
  }
  return "The article catalogue is temporarily unavailable. Your URL was not sent to another website.";
}

export async function ArticleUrlResolver({ searchParams }: ArticleUrlResolverProps) {
  const parameters = await searchParams;
  const submittedUrl = firstValue(parameters.url)?.trim();
  const duplicateUrl = Array.isArray(parameters.url) && parameters.url.length !== 1;
  let failure: "invalid_request" | "not_found" | "unavailable" | null = null;

  if (submittedUrl) {
    const result = duplicateUrl
      ? ({ status: "error", reason: "invalid_request" } as const)
      : await resolveArticleUrl(submittedUrl);

    if (result.status === "success") {
      redirect(`/generate?articleId=${encodeURIComponent(result.data.id)}`);
    }
    if (result.reason === "authentication_required") {
      redirect("/login?reason=authentication_required");
    }
    failure = result.reason;
  } else if (duplicateUrl) {
    failure = "invalid_request";
  }

  const normalisedSubmittedUrl = submittedUrl ? normaliseSourceUrl(submittedUrl) : null;

  return (
    <section
      aria-labelledby="url-workflow-title"
      className="relative overflow-hidden rounded-[2rem] border border-emerald-900 bg-emerald-950 px-6 py-8 text-white shadow-xl shadow-emerald-950/10 sm:px-8 sm:py-10"
    >
      <div
        aria-hidden="true"
        className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-lime-300/15 blur-3xl"
      />
      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)] xl:items-end">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-lime-300">
            Start with a source
          </p>
          <h2
            className="mt-3 max-w-3xl text-3xl font-semibold tracking-[-0.04em] sm:text-4xl"
            id="url-workflow-title"
          >
            Paste an approved article URL. Shape the story in your voice.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-emerald-50/75 sm:text-base">
            NewsFlow AI matches the link against the rights-approved catalogue, then takes you to
            tone, language, and length controls. It does not scrape an unknown page from this box.
          </p>

          <form action="/dashboard" className="mt-7" method="get">
            <label className="text-sm font-semibold text-white" htmlFor="article-url">
              Search URL
            </label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <input
                aria-describedby="article-url-help article-url-status"
                aria-invalid={failure ? true : undefined}
                className="min-h-12 min-w-0 flex-1 rounded-2xl border border-white/20 bg-white px-4 py-3 text-sm text-emerald-950 outline-none transition placeholder:text-emerald-950/50 focus:border-lime-300 focus:ring-4 focus:ring-lime-300/20"
                defaultValue={normalisedSubmittedUrl ?? submittedUrl}
                id="article-url"
                inputMode="url"
                maxLength={2048}
                name="url"
                placeholder="https://approved-source.example/article"
                required
                type="url"
              />
              <button
                className="inline-flex min-h-12 shrink-0 items-center justify-center rounded-full bg-lime-300 px-6 py-3 text-sm font-semibold text-emerald-950 transition hover:bg-lime-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime-300"
                type="submit"
              >
                Use this article
              </button>
            </div>
            <p className="mt-3 text-xs leading-5 text-emerald-50/70" id="article-url-help">
              HTTPS links only. Matching happens inside the approved catalogue; no arbitrary URL is
              downloaded.
            </p>
            <div aria-live="polite" id="article-url-status">
              {failure ? (
                <p
                  className="mt-4 rounded-2xl border border-amber-200/30 bg-amber-100/10 px-4 py-3 text-sm leading-6 text-amber-50"
                  role="alert"
                >
                  {errorMessage(failure)}
                </p>
              ) : null}
            </div>
          </form>

          <div className="mt-5 flex flex-wrap items-center gap-3 text-sm">
            <Link
              className="font-semibold text-lime-300 underline decoration-lime-300/40 underline-offset-4 hover:text-lime-200"
              href={`/dashboard?url=${encodeURIComponent(DEMO_ARTICLE_URL)}`}
              prefetch={false}
            >
              Try the synthetic demo URL
            </Link>
            <span className="text-emerald-50/70">or</span>
            <a
              className="font-semibold text-emerald-50 underline decoration-white/25 underline-offset-4 hover:text-white"
              href="#article-catalogue-title"
            >
              browse the catalogue
            </a>
          </div>
        </div>

        <ol className="grid gap-3" aria-label="Content creation workflow">
          {[
            ["01", "Choose a permitted source", "Paste its exact URL or select it below."],
            ["02", "Set your writing style", "Choose a tone, language, and post length."],
            ["03", "Review before saving", "Edit the AI draft and keep attribution visible."],
          ].map(([number, title, description]) => (
            <li
              className="grid grid-cols-[2.5rem_1fr] gap-3 rounded-2xl border border-white/10 bg-white/[0.06] p-4"
              key={number}
            >
              <span className="font-mono text-xs font-semibold text-lime-300">{number}</span>
              <span>
                <strong className="block text-sm text-white">{title}</strong>
                <span className="mt-1 block text-xs leading-5 text-emerald-50/65">
                  {description}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function DashboardShortcuts() {
  return (
    <nav aria-label="Workspace shortcuts" className="mt-6 grid gap-3 sm:grid-cols-3">
      <Link className={buttonStyles("secondary")} href="#article-catalogue-title">
        Browse approved articles
      </Link>
      <Link className={buttonStyles("secondary")} href="/library">
        Open content library
      </Link>
      <Link className={buttonStyles("quiet")} href="/account">
        Review account
      </Link>
    </nav>
  );
}

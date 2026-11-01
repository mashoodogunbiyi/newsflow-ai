import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { ArticleDetail } from "@/types/article";

function formatPublishedDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(value));
}

function GenerationAvailability({ article }: { article: ArticleDetail }) {
  const { generation } = article;
  const content =
    generation.status === "available"
      ? {
          description:
            "Current permissions and authorised grounding information allow this article to continue to draft setup.",
          label: "AI generation permitted",
        }
      : generation.status === "restricted"
        ? {
            description:
              "Current source permissions do not allow this article to be used for AI-generated output. Choose another article.",
            label: "AI generation restricted",
          }
        : {
            description:
              "The source can be displayed, but it does not contain enough authorised information to ground a detailed draft.",
            label: "More source information required",
          };

  return (
    <section
      aria-labelledby="generation-availability-title"
      className="border-t border-emerald-950/10 pt-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
            Generation availability
          </p>
          <h3
            className="mt-2 text-xl font-semibold tracking-[-0.025em] text-emerald-950"
            id="generation-availability-title"
          >
            {content.label}
          </h3>
          <p className="mt-2 text-sm leading-6 text-emerald-950/70">{content.description}</p>
        </div>
        <StatusBadge tone={generation.allowed ? "success" : "warning"}>
          {generation.allowed ? "Available" : "Unavailable"}
        </StatusBadge>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        {generation.allowed ? (
          <a className={buttonStyles("primary")} href="#generation-controls">
            Continue with this source
          </a>
        ) : (
          <button className={buttonStyles("primary")} disabled type="button">
            Continue with this source
          </button>
        )}
        <Link className={buttonStyles("secondary")} href="/dashboard">
          Choose another article
        </Link>
      </div>
      <p className="mt-4 text-xs leading-5 text-emerald-950/70">
        FastAPI will check the current source permissions again before any AI request is made.
      </p>
    </section>
  );
}

export function SourcePanel({ article }: { article: ArticleDetail }) {
  return (
    <Card className="overflow-hidden p-0 sm:p-0">
      <article aria-labelledby="selected-source-title">
        <div className="border-b border-emerald-950/10 bg-emerald-50/70 px-5 py-5 sm:px-7">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              Selected source
            </p>
            <StatusBadge tone="success">Authorised for display</StatusBadge>
          </div>
          <h2
            className="mt-4 max-w-4xl text-2xl font-semibold leading-8 tracking-[-0.035em] text-emerald-950 sm:text-3xl sm:leading-10"
            id="selected-source-title"
          >
            {article.title}
          </h2>
        </div>

        <div className="space-y-7 p-5 sm:p-7">
          <dl className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-950/70">
                Source provider
              </dt>
              <dd className="mt-2 text-sm font-semibold text-emerald-950">
                {article.attribution.display_name}
              </dd>
              <dd className="mt-1 font-mono text-xs text-emerald-950/70">{article.provider}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-950/70">
                Published
              </dt>
              <dd className="mt-2 text-sm font-semibold text-emerald-950">
                <time dateTime={article.published_at}>
                  {formatPublishedDate(article.published_at)}
                </time>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-950/70">
                Category
              </dt>
              <dd className="mt-2 text-sm font-semibold text-emerald-950">
                {article.category ?? "Not provided"}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-950/70">
                Article ID
              </dt>
              <dd className="mt-2 break-all font-mono text-xs text-emerald-950/65">{article.id}</dd>
            </div>
          </dl>

          <section
            aria-labelledby="permitted-summary-title"
            className="border-t border-emerald-950/10 pt-6"
          >
            <h3
              className="text-lg font-semibold tracking-[-0.02em] text-emerald-950"
              id="permitted-summary-title"
            >
              Permitted summary
            </h3>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-emerald-950/65">
              {article.description ??
                "No permitted summary is available. NewsFlow AI will not invent missing source information."}
            </p>
          </section>

          <section
            aria-labelledby="source-reference-title"
            className="border-t border-emerald-950/10 pt-6"
          >
            <h3
              className="text-lg font-semibold tracking-[-0.02em] text-emerald-950"
              id="source-reference-title"
            >
              Source reference
            </h3>
            <p className="mt-3 break-all font-mono text-xs leading-5 text-emerald-950/70">
              {article.source_url}
            </p>
            <a
              aria-label={`Open original source for ${article.title}`}
              className={`${buttonStyles("secondary")} mt-4`}
              href={article.source_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open original source
              <span aria-hidden="true" className="ml-1.5">
                ↗
              </span>
            </a>
            <div className="mt-5 rounded-2xl border border-emerald-950/10 bg-stone-50 px-4 py-3 text-xs leading-5 text-emerald-950/70">
              <p>{article.attribution.text}</p>
              {article.attribution.byline ? (
                <p className="mt-1">{article.attribution.byline}</p>
              ) : null}
              {article.attribution.copyright_notice ? (
                <p className="mt-1">{article.attribution.copyright_notice}</p>
              ) : null}
            </div>
          </section>

          <GenerationAvailability article={article} />

          <aside className="rounded-2xl border border-amber-700/15 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-950">
            <strong>Review reminder:</strong> AI output must be checked against the original source.
            Availability does not mean a generated draft is factually verified.
          </aside>
        </div>
      </article>
    </Card>
  );
}

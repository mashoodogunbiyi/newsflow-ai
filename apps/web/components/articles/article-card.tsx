import { ArticleSelection } from "@/components/articles/article-selection";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Article } from "@/types/article";

function formatPublishedDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(new Date(value));
}

export function ArticleCard({ article }: { article: Article }) {
  const publishedDate = formatPublishedDate(article.published_at);

  return (
    <Card className="flex h-full flex-col p-0 sm:p-0">
      <article className="flex h-full flex-col">
        <div className="border-b border-emerald-950/10 bg-emerald-50/60 px-5 py-4 sm:px-6">
          <div className="flex flex-wrap items-center gap-2">
            {article.category ? <StatusBadge>{article.category}</StatusBadge> : null}
            <span className="font-mono text-xs font-semibold uppercase tracking-[0.12em] text-emerald-950/70">
              {article.provider}
            </span>
          </div>
        </div>

        <div className="flex flex-1 flex-col p-5 sm:p-6">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-emerald-950/70">
            <span className="font-semibold text-emerald-900">
              {article.attribution.display_name}
            </span>
            <span aria-hidden="true">-</span>
            <time dateTime={article.published_at}>{publishedDate}</time>
          </div>

          <h2 className="mt-4 text-xl font-semibold leading-7 tracking-[-0.025em] text-emerald-950">
            {article.title}
          </h2>

          <p className="mt-3 text-sm leading-6 text-emerald-950/65">
            {article.description ?? "No permitted summary is available for this article."}
          </p>

          <div className="mt-6 border-t border-emerald-950/10 pt-4 text-xs leading-5 text-emerald-950/70">
            <p>{article.attribution.text}</p>
            {article.attribution.byline ? (
              <p className="mt-1">{article.attribution.byline}</p>
            ) : null}
            {article.attribution.copyright_notice ? (
              <p className="mt-1">{article.attribution.copyright_notice}</p>
            ) : null}
          </div>

          <div className="mt-auto flex flex-col gap-2 pt-6 sm:flex-row">
            <ArticleSelection articleId={article.id} className="flex-1" />
            <a
              aria-label={`View source: ${article.title} (opens in a new tab)`}
              className={`${buttonStyles("secondary")} flex-1`}
              href={article.source_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              View source
              <span aria-hidden="true" className="ml-1.5">
                ↗
              </span>
            </a>
          </div>
        </div>
      </article>
    </Card>
  );
}

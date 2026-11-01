import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SourcePanel } from "@/components/articles/source-panel";
import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { getArticleDetail, type ArticleDetailResult } from "@/lib/article-api";

export const metadata: Metadata = {
  title: "Create Post - NewsFlow AI",
  description: "Review an authorised source before preparing a LinkedIn post.",
};

type GenerateSearchParams = {
  articleId?: string | string[];
};

type GeneratePageProps = {
  searchParams: Promise<GenerateSearchParams>;
};

type ArticleDetailErrorResult = Extract<ArticleDetailResult, { status: "error" }>;

function SelectionState({ result }: { result?: ArticleDetailErrorResult }) {
  const content = !result
    ? {
        eyebrow: "Article required",
        title: "Choose an article before continuing.",
        description:
          "Open the authorised catalogue and select the source you want to review. Only its identifier will be carried into this creation flow.",
      }
    : result.reason === "not_found"
      ? {
          eyebrow: "Source unavailable",
          title: "This article is no longer available.",
          description:
            "The article may have been removed, expired, or become inaccessible. Restricted source details are not disclosed.",
        }
      : result.reason === "invalid_request"
        ? {
            eyebrow: "Invalid selection",
            title: "This article selection link is not valid.",
            description:
              "Return to the catalogue and select an article again. Article content must never be placed in the URL.",
          }
        : {
            eyebrow: "Safe recovery",
            title: "Source information could not be loaded.",
            description:
              "The article catalogue is temporarily unavailable. Your account and saved content have not been changed.",
          };

  return (
    <Card className="mt-10 text-center" role={result ? "alert" : undefined}>
      <div className="mx-auto max-w-xl py-6 sm:py-10">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
          {content.eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          {content.title}
        </h2>
        <p className="mt-4 leading-7 text-emerald-950/60">{content.description}</p>
        <Link className={`${buttonStyles("primary")} mt-7`} href="/dashboard">
          Browse authorised articles
        </Link>
      </div>
    </Card>
  );
}

export default async function GeneratePage({ searchParams }: GeneratePageProps) {
  const parameters = await searchParams;
  const rawArticleId = parameters.articleId;
  const duplicatedId = Array.isArray(rawArticleId);
  const articleId = typeof rawArticleId === "string" ? rawArticleId.trim() : undefined;
  const result = !articleId ? undefined : await getArticleDetail(articleId);

  if (result?.status === "error" && result.reason === "authentication_required") {
    redirect("/login?reason=authentication_required");
  }

  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("secondary")} href="/dashboard">
            Change article
          </Link>
        }
        description="Inspect the permitted source fields, attribution, and current generation availability before asking AI to prepare a draft."
        eyebrow="Create Post"
        title="Review the source before generating."
      />

      {duplicatedId ? (
        <SelectionState result={{ status: "error", reason: "invalid_request" }} />
      ) : !result ? (
        <SelectionState />
      ) : result.status === "error" ? (
        <SelectionState result={result} />
      ) : (
        <div className="mt-10 space-y-6">
          <SourcePanel article={result.data} />
          {result.data.generation.allowed ? (
            <Card id="generation-controls" tone="muted">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-2xl">
                  <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                    Source ready
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-emerald-950">
                    The selected article can continue to draft preferences.
                  </h2>
                  <p className="mt-3 text-sm leading-6 text-emerald-950/60">
                    The article identifier remains in this page URL. Tone, length, and draft
                    generation controls will build on this source-safe state in the next creation
                    task.
                  </p>
                </div>
                <StatusBadge tone="success">Selection preserved</StatusBadge>
              </div>
            </Card>
          ) : null}
        </div>
      )}
    </>
  );
}

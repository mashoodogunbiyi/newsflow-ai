import type { Metadata } from "next";
import { Suspense } from "react";

import {
  ArticleCatalogue,
  type DashboardSearchParams,
} from "@/components/articles/article-catalogue";
import { ArticleDashboardSkeleton } from "@/components/articles/article-dashboard-skeleton";
import { ArticleUrlResolver, DashboardShortcuts } from "@/components/articles/article-url-resolver";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Article Dashboard - NewsFlow AI",
  description: "Start from an approved article URL or browse permitted source metadata.",
};

type DashboardPageProps = {
  searchParams: Promise<DashboardSearchParams>;
};

export default function DashboardPage({ searchParams }: DashboardPageProps) {
  return (
    <>
      <PageHeader
        description="Bring an approved source, choose how the story should sound, and turn it into a review-ready LinkedIn draft without losing attribution."
        eyebrow="Your content workspace"
        title="From trusted link to thoughtful post."
      />

      <div className="mt-8">
        <Suspense
          fallback={<div className="h-96 animate-pulse rounded-[2rem] bg-emerald-950/10" />}
        >
          <ArticleUrlResolver searchParams={searchParams} />
        </Suspense>
        <DashboardShortcuts />
      </div>

      <div className="mt-8 flex flex-wrap gap-2" aria-label="Catalogue safeguards">
        <StatusBadge tone="success">Rights-approved fields only</StatusBadge>
        <StatusBadge tone="warning">Synthetic fixture mode</StatusBadge>
        <StatusBadge>Human review required</StatusBadge>
      </div>
      <p className="mt-4 max-w-4xl text-sm leading-6 text-emerald-950/70">
        Live CNN access is not enabled. The catalogue currently contains synthetic development
        records so the full selection workflow can be tested without implying provider
        authorisation. A live provider requires its own written approval and adapter.
      </p>

      <Suspense fallback={<ArticleDashboardSkeleton />}>
        <ArticleCatalogue searchParams={searchParams} />
      </Suspense>
    </>
  );
}

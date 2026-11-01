import type { Metadata } from "next";
import { Suspense } from "react";

import {
  ArticleCatalogue,
  type DashboardSearchParams,
} from "@/components/articles/article-catalogue";
import { ArticleDashboardSkeleton } from "@/components/articles/article-dashboard-skeleton";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Article Dashboard - NewsFlow AI",
  description: "Browse rights-approved article metadata for LinkedIn content creation.",
};

type DashboardPageProps = {
  searchParams: Promise<DashboardSearchParams>;
};

export default function DashboardPage({ searchParams }: DashboardPageProps) {
  return (
    <>
      <PageHeader
        description="Explore permitted news metadata, preserve source attribution, and choose a grounded starting point for your next LinkedIn draft."
        eyebrow="News discovery"
        title="Find a story worth sharing."
      />

      <div className="mt-8 flex flex-wrap gap-2" aria-label="Catalogue safeguards">
        <StatusBadge tone="success">Rights-approved fields only</StatusBadge>
        <StatusBadge tone="warning">Synthetic fixture mode</StatusBadge>
        <StatusBadge>Human review required</StatusBadge>
      </div>
      <p className="mt-4 max-w-3xl text-sm leading-6 text-emerald-950/70">
        Live CNN access is not enabled. The catalogue currently contains synthetic development
        records so the workflow can be tested without implying provider authorisation.
      </p>

      <Suspense fallback={<ArticleDashboardSkeleton />}>
        <ArticleCatalogue searchParams={searchParams} />
      </Suspense>
    </>
  );
}

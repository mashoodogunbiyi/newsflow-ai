import { ArticleDashboardSkeleton } from "@/components/articles/article-dashboard-skeleton";

export default function DashboardLoading() {
  return (
    <>
      <div className="max-w-3xl" aria-hidden="true">
        <div className="h-3 w-36 animate-pulse rounded-full bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-5 h-12 w-4/5 animate-pulse rounded-2xl bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-5 h-20 animate-pulse rounded-2xl bg-emerald-950/10 motion-reduce:animate-none" />
      </div>
      <ArticleDashboardSkeleton />
    </>
  );
}

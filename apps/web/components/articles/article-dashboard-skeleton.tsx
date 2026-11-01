export function ArticleDashboardSkeleton() {
  return (
    <section aria-busy="true" aria-label="Loading authorised articles" className="mt-8">
      <span className="sr-only">Loading authorised articles...</span>
      <div className="h-24 animate-pulse rounded-3xl border border-emerald-950/10 bg-white motion-reduce:animate-none" />
      <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (
          <div
            aria-hidden="true"
            className="h-80 animate-pulse rounded-3xl border border-emerald-950/10 bg-white motion-reduce:animate-none"
            key={index}
          />
        ))}
      </div>
    </section>
  );
}

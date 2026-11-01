export default function GenerateLoading() {
  return (
    <div aria-busy="true" aria-label="Loading selected source">
      <span className="sr-only">Loading selected source...</span>
      <div className="h-36 max-w-3xl animate-pulse rounded-3xl bg-emerald-950/10 motion-reduce:animate-none" />
      <div className="mt-10 h-[34rem] animate-pulse rounded-3xl border border-emerald-950/10 bg-white motion-reduce:animate-none" />
    </div>
  );
}

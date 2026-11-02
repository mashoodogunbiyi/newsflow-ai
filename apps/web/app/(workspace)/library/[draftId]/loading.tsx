export default function SavedDraftLoading() {
  return (
    <div aria-busy="true" aria-label="Loading saved draft">
      <span className="sr-only">Loading saved draft...</span>
      <div className="h-36 max-w-3xl animate-pulse rounded-3xl bg-emerald-950/10 motion-reduce:animate-none" />
      <div className="mt-10 h-[42rem] animate-pulse rounded-3xl border border-emerald-950/10 bg-white motion-reduce:animate-none" />
    </div>
  );
}

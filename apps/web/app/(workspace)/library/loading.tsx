export default function LibraryLoading() {
  return (
    <div aria-busy="true" aria-label="Loading saved drafts">
      <span className="sr-only">Loading saved drafts...</span>
      <div className="max-w-3xl" aria-hidden="true">
        <div className="h-3 w-36 animate-pulse rounded-full bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-5 h-12 w-4/5 animate-pulse rounded-2xl bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-5 h-20 animate-pulse rounded-2xl bg-emerald-950/10 motion-reduce:animate-none" />
      </div>
      <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <div
            className="h-[31rem] animate-pulse rounded-3xl border border-emerald-950/10 bg-white motion-reduce:animate-none"
            key={index}
          />
        ))}
      </div>
    </div>
  );
}

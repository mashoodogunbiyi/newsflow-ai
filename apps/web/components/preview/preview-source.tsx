import type { PreviewSourceReference } from "@/types/preview";

function isSafeSourceUrl(value: string) {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

export function PreviewSource({ source }: { source: PreviewSourceReference }) {
  const safeSourceUrl = isSafeSourceUrl(source.url);

  return (
    <section
      aria-label="Original article source"
      className="border-t border-emerald-950/10 px-4 py-4 sm:px-6"
    >
      <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
        Original article source
      </p>
      <p className="mt-2 break-words text-sm font-semibold leading-6 text-emerald-950">
        {source.title}
      </p>
      <p className="mt-1 text-xs leading-5 text-emerald-950/70">{source.name}</p>
      <p className="mt-2 text-xs leading-5 text-emerald-950/70">{source.attribution}</p>
      {safeSourceUrl ? (
        <a
          className="mt-3 inline-block break-all rounded-sm text-xs font-semibold text-emerald-800 underline decoration-emerald-700/50 underline-offset-4 hover:decoration-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
          href={source.url}
          rel="noopener noreferrer"
          target="_blank"
        >
          Review the original source
        </a>
      ) : (
        <p className="mt-3 text-xs font-semibold text-red-700">Source link unavailable.</p>
      )}
    </section>
  );
}

import { PreviewImage } from "@/components/preview/preview-image";
import { PreviewSource } from "@/components/preview/preview-source";
import type { LinkedInPreviewContent } from "@/types/preview";

export function LinkedInPreview({
  draftText,
  groundingStatus,
  image,
  source,
  warnings,
}: LinkedInPreviewContent) {
  const emptyDraft = draftText.trim().length === 0;

  return (
    <section aria-label="LinkedIn-inspired preview" className="min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-emerald-950">LinkedIn-inspired preview</h3>
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">
          Preview only
        </span>
      </div>

      <div className="mt-3 w-full overflow-hidden rounded-2xl border border-emerald-950/10 bg-white shadow-sm sm:rounded-3xl">
        <header className="flex items-center gap-3 px-4 py-4 sm:px-6">
          <span
            aria-hidden="true"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-emerald-950 text-xs font-bold text-white"
          >
            NF
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-emerald-950">
              NewsFlow AI content preview
            </p>
            <p className="text-xs leading-5 text-emerald-950/50">
              AI-assisted draft - human review required
            </p>
          </div>
        </header>

        <p
          className={`min-h-56 whitespace-pre-wrap break-words border-t border-emerald-950/10 px-4 py-5 text-sm leading-7 sm:px-6 ${
            emptyDraft ? "italic text-emerald-950/45" : "text-emerald-950/80"
          }`}
          data-testid="draft-preview"
        >
          {emptyDraft ? "Your edited draft will appear here." : draftText}
        </p>

        <PreviewSource source={source} />
        <PreviewImage image={image} />

        <aside
          aria-label="Preview review warning"
          className="border-t border-amber-700/15 bg-amber-50/70 px-4 py-4 text-xs leading-5 text-amber-950 sm:px-6"
        >
          <p className="font-semibold">
            {warnings.length === 0
              ? "Human fact-check required"
              : `${warnings.length} automated review ${warnings.length === 1 ? "warning" : "warnings"}`}
          </p>
          {warnings.length === 0 ? (
            <p className="mt-1">
              Automated checks do not verify every claim. Compare the full draft with the original
              source before saving or exporting it.
            </p>
          ) : (
            <>
              <p className="mt-1">
                These warnings remain visible after editing. Check the revised draft against the
                source.
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {warnings.map((warning) => (
                  <li key={`${warning.code}:${warning.category}`}>{warning.message}</li>
                ))}
              </ul>
            </>
          )}
          <p className="mt-2 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-amber-900/70">
            Grounding status: {groundingStatus.replaceAll("_", " ")}
          </p>
        </aside>

        <p className="border-t border-emerald-950/10 bg-stone-50 px-4 py-3 text-[0.68rem] leading-5 text-emerald-950/50 sm:px-6">
          This planning preview is not affiliated with LinkedIn and may differ from live platform
          rendering. Nothing is published from this screen.
        </p>
      </div>
    </section>
  );
}

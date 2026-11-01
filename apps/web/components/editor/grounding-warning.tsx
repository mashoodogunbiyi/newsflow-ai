import type { DraftEditorDocument } from "@/types/draft";

type GroundingWarningProps = {
  groundingStatus: DraftEditorDocument["groundingStatus"];
  warnings: DraftEditorDocument["validationWarnings"];
};

export function GroundingWarning({ groundingStatus, warnings }: GroundingWarningProps) {
  if (warnings.length === 0) {
    return (
      <aside className="rounded-2xl border border-amber-700/20 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-950">
        <p className="font-semibold">Human fact-check required</p>
        <p className="mt-1">
          No automated warning was returned, but automated checks do not verify every claim. Check
          this draft against the source before use.
        </p>
      </aside>
    );
  }

  return (
    <aside
      aria-labelledby="grounding-warning-title"
      className="rounded-2xl border border-amber-700/20 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-950"
    >
      <p className="font-semibold" id="grounding-warning-title">
        Review {warnings.length === 1 ? "warning" : "warnings"} from automated checks
      </p>
      <p className="mt-1">
        These warnings remain visible after editing. Substantial changes require another factual
        check against the source.
      </p>
      <ul className="mt-3 list-disc space-y-2 pl-5">
        {warnings.map((warning) => (
          <li key={`${warning.code}:${warning.category}`}>
            {warning.message}
            {warning.severity === "blocking" ? " This warning blocks normal use." : ""}
          </li>
        ))}
      </ul>
      <p className="mt-3 font-mono text-xs uppercase tracking-[0.12em] text-amber-900/70">
        Grounding status: {groundingStatus.replaceAll("_", " ")}
      </p>
    </aside>
  );
}

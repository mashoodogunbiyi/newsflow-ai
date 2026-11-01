import type { ActiveGenerationState } from "@/types/generation-state";

export function GenerationLoading({ state }: { state: ActiveGenerationState }) {
  const isText = state.kind === "text";
  const submittingMessage = isText
    ? "Submitting your LinkedIn draft request..."
    : "Submitting your illustration request...";
  const processingMessage = isText
    ? "Generating your LinkedIn draft..."
    : "Creating your illustration...";

  return (
    <div
      aria-live="polite"
      className="rounded-2xl border border-emerald-700/20 bg-emerald-50 px-4 py-4 text-sm leading-6 text-emerald-950 outline-none"
      role="status"
      tabIndex={-1}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-1 h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-emerald-800/20 border-t-emerald-800"
        />
        <div>
          <p className="font-semibold">
            {state.phase === "submitting" ? submittingMessage : processingMessage}
          </p>
          <p className="mt-1 text-emerald-950/70">
            {state.phase === "submitting"
              ? "NewsFlow AI is validating and preparing the request."
              : "This can take a little while. Keep this page open and avoid submitting again."}
          </p>
        </div>
      </div>
      <p className="sr-only">
        {isText
          ? "Your LinkedIn draft generation request is being processed."
          : "Your illustration generation request is being processed."}
      </p>
    </div>
  );
}

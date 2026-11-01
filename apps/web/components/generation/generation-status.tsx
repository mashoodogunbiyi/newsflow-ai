import type { ReactNode, RefObject } from "react";

import { GenerationError } from "@/components/generation/generation-error";
import { GenerationLoading } from "@/components/generation/generation-loading";
import type { GenerationState } from "@/types/generation-state";

type GenerationStatusProps<TResult> = {
  completionDetails?: ReactNode;
  onRetry?: () => void;
  retrySeconds?: number;
  state: GenerationState<TResult>;
  statusRef?: RefObject<HTMLDivElement | null>;
};

export function GenerationStatus<TResult>({
  completionDetails,
  onRetry,
  retrySeconds = 0,
  state,
  statusRef,
}: GenerationStatusProps<TResult>) {
  if (state.phase === "submitting" || state.phase === "processing") {
    return (
      <div className="outline-none" ref={statusRef} tabIndex={-1}>
        <GenerationLoading state={state} />
      </div>
    );
  }

  if (state.phase === "failed") {
    return (
      <div className="outline-none" ref={statusRef} tabIndex={-1}>
        <GenerationError onRetry={onRetry} retrySeconds={retrySeconds} state={state} />
      </div>
    );
  }

  if (state.phase === "completed") {
    const isText = state.kind === "text";
    return (
      <div
        aria-live="polite"
        className="rounded-2xl border border-emerald-700/20 bg-emerald-50 px-4 py-4 text-sm leading-6 text-emerald-950 outline-none"
        ref={statusRef}
        role="status"
        tabIndex={-1}
      >
        <p className="font-semibold">
          {isText
            ? "Your private draft has been generated."
            : "Your private illustration is ready for review."}
        </p>
        <p className="mt-1">
          {isText
            ? "It requires human review before it is copied, saved, exported, or used. Nothing has been published to LinkedIn."
            : "Review the illustration before it is saved, downloaded, or used. It has not been published anywhere."}
        </p>
        {completionDetails}
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl border border-emerald-950/10 bg-white px-4 py-3 text-sm leading-6 text-emerald-950/60"
      ref={statusRef}
    >
      <p className="font-semibold text-emerald-950">
        {state.kind === "text" ? "Ready to generate a draft." : "Ready to create an illustration."}
      </p>
      <p className="mt-1">No generation request has started.</p>
    </div>
  );
}

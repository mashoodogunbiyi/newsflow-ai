import { Button } from "@/components/ui/button";
import type { FailedGenerationState } from "@/types/generation-state";

type GenerationErrorProps = {
  onRetry?: () => void;
  retrySeconds?: number;
  state: FailedGenerationState;
};

export function GenerationError({ onRetry, retrySeconds = 0, state }: GenerationErrorProps) {
  const isText = state.kind === "text";

  return (
    <div
      aria-live="assertive"
      className="rounded-2xl border border-red-700/20 bg-red-50 px-4 py-4 text-sm leading-6 text-red-900 outline-none"
      role="alert"
      tabIndex={-1}
    >
      <p className="font-semibold">
        {isText ? "The draft could not be generated." : "The illustration could not be generated."}
      </p>
      <p className="mt-1">{state.error.message}</p>
      {state.error.retryable && onRetry ? (
        <Button
          className="mt-4"
          disabled={retrySeconds > 0}
          onClick={onRetry}
          type="button"
          variant="secondary"
        >
          {retrySeconds > 0 ? `Try again in ${retrySeconds}s` : "Try again"}
        </Button>
      ) : null}
    </div>
  );
}

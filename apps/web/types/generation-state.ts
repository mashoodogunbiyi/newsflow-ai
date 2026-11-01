export type GenerationKind = "text" | "image";

export type GenerationFailureCategory =
  | "authentication"
  | "permissions"
  | "validation"
  | "usage_limit"
  | "timeout"
  | "conflict"
  | "network"
  | "service";

export type GenerationFailure = {
  category: GenerationFailureCategory;
  message: string;
  retryAfterSeconds: number | null;
  retryable: boolean;
};

type GenerationStateBase = {
  kind: GenerationKind;
};

export type IdleGenerationState = GenerationStateBase & {
  error: null;
  phase: "idle";
  requestId: null;
  result: null;
};

export type ActiveGenerationState = GenerationStateBase & {
  error: null;
  phase: "submitting" | "processing";
  requestId: string;
  result: null;
  startedAt: number;
};

export type CompletedGenerationState<TResult> = GenerationStateBase & {
  completedAt: number;
  error: null;
  phase: "completed";
  requestId: string;
  result: TResult;
};

export type FailedGenerationState = GenerationStateBase & {
  error: GenerationFailure;
  failedAt: number;
  phase: "failed";
  requestId: string;
  result: null;
};

export type GenerationState<TResult> =
  | IdleGenerationState
  | ActiveGenerationState
  | CompletedGenerationState<TResult>
  | FailedGenerationState;

export type GenerationOperationResult<TResult> =
  { data: TResult; status: "success" } | { error: GenerationFailure; status: "error" };

export function createIdleGenerationState(kind: GenerationKind): IdleGenerationState {
  return {
    error: null,
    kind,
    phase: "idle",
    requestId: null,
    result: null,
  };
}

export function isGenerationBusy<TResult>(state: GenerationState<TResult>) {
  return state.phase === "submitting" || state.phase === "processing";
}

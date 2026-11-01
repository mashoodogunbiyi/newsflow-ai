"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  createIdleGenerationState,
  isGenerationBusy,
  type GenerationFailure,
  type GenerationKind,
  type GenerationOperationResult,
  type GenerationState,
} from "@/types/generation-state";

export type GenerationOperationContext = {
  requestId: string;
  signal: AbortSignal;
};

export type GenerationOperation<TInput, TResult> = (
  input: TInput,
  context: GenerationOperationContext,
) => Promise<GenerationOperationResult<TResult>>;

type UseGenerationOptions<TInput, TResult> = {
  execute: GenerationOperation<TInput, TResult>;
  kind: GenerationKind;
};

export type GenerationRunResult<TResult> =
  | { accepted: false }
  | {
      accepted: true;
      applied: boolean;
      outcome: GenerationOperationResult<TResult>;
      requestId: string;
    };

function unexpectedFailure(kind: GenerationKind): GenerationFailure {
  return {
    category: "network",
    message:
      kind === "text"
        ? "Draft generation is temporarily unavailable. Your selections are still here."
        : "Illustration generation is temporarily unavailable. Your selections are still here.",
    retryAfterSeconds: null,
    retryable: true,
  };
}

export function useGeneration<TInput, TResult>({
  execute,
  kind,
}: UseGenerationOptions<TInput, TResult>) {
  const [state, setState] = useState<GenerationState<TResult>>(() =>
    createIdleGenerationState(kind),
  );
  const stateRef = useRef<GenerationState<TResult>>(state);
  const activeRequestIdRef = useRef<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const lastInputRef = useRef<TInput | null>(null);
  const sequenceRef = useRef(0);
  const mountedRef = useRef(true);

  const publish = useCallback((nextState: GenerationState<TResult>) => {
    stateRef.current = nextState;
    if (mountedRef.current) {
      setState(nextState);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      sequenceRef.current += 1;
      activeRequestIdRef.current = null;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, []);

  const start = useCallback(
    async (input: TInput): Promise<GenerationRunResult<TResult>> => {
      if (activeRequestIdRef.current !== null) {
        return { accepted: false };
      }

      sequenceRef.current += 1;
      const requestId = `${kind}:${sequenceRef.current}`;
      const controller = new AbortController();
      const startedAt = Date.now();
      activeRequestIdRef.current = requestId;
      controllerRef.current = controller;
      lastInputRef.current = input;
      publish({
        error: null,
        kind,
        phase: "submitting",
        requestId,
        result: null,
        startedAt,
      });

      await Promise.resolve();
      if (activeRequestIdRef.current !== requestId) {
        return {
          accepted: true,
          applied: false,
          outcome: { error: unexpectedFailure(kind), status: "error" },
          requestId,
        };
      }

      publish({
        error: null,
        kind,
        phase: "processing",
        requestId,
        result: null,
        startedAt,
      });

      let outcome: GenerationOperationResult<TResult>;
      try {
        outcome = await execute(input, { requestId, signal: controller.signal });
      } catch {
        outcome = { error: unexpectedFailure(kind), status: "error" };
      }

      if (activeRequestIdRef.current !== requestId || controller.signal.aborted) {
        return { accepted: true, applied: false, outcome, requestId };
      }

      activeRequestIdRef.current = null;
      controllerRef.current = null;
      if (outcome.status === "success") {
        publish({
          completedAt: Date.now(),
          error: null,
          kind,
          phase: "completed",
          requestId,
          result: outcome.data,
        });
      } else {
        publish({
          error: outcome.error,
          failedAt: Date.now(),
          kind,
          phase: "failed",
          requestId,
          result: null,
        });
      }

      return { accepted: true, applied: true, outcome, requestId };
    },
    [execute, kind, publish],
  );

  const retry = useCallback(async (): Promise<GenerationRunResult<TResult>> => {
    const current = stateRef.current;
    if (current.phase !== "failed" || !current.error.retryable || lastInputRef.current === null) {
      return { accepted: false };
    }
    return start(lastInputRef.current);
  }, [start]);

  const reset = useCallback(() => {
    sequenceRef.current += 1;
    activeRequestIdRef.current = null;
    controllerRef.current?.abort();
    controllerRef.current = null;
    lastInputRef.current = null;
    publish(createIdleGenerationState(kind));
  }, [kind, publish]);

  return {
    isBusy: isGenerationBusy(state),
    reset,
    retry,
    start,
    state,
  };
}

export function useTextGeneration<TInput, TResult>(execute: GenerationOperation<TInput, TResult>) {
  return useGeneration({ execute, kind: "text" });
}

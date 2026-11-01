"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import { GenerationStatus } from "@/components/generation/generation-status";
import { LengthSelector } from "@/components/generation/length-selector";
import { ToneSelector } from "@/components/generation/tone-selector";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type GenerationRunResult, useTextGeneration } from "@/hooks/use-generation";
import {
  createGenerationRequestKey,
  generateLinkedInDraft,
  type GenerationResult,
} from "@/lib/generation-api";
import type { ArticleGenerationStatus } from "@/types/article";
import { toDraftEditorDocument } from "@/types/draft";
import {
  isArticleId,
  isGenerationLength,
  isGenerationTone,
  type GenerationLength,
  type GenerationTone,
} from "@/types/generation";
import type { GenerationFailure, GenerationOperationResult } from "@/types/generation-state";

type GenerationControlsProps = {
  articleId: string | null;
  availabilityStatus: ArticleGenerationStatus | "missing";
  generationAllowed: boolean;
};

function unavailableMessage(
  articleId: string | null,
  availabilityStatus: GenerationControlsProps["availabilityStatus"],
) {
  if (!articleId) {
    return "Choose an article from the authorised catalogue before generating a draft.";
  }
  if (!isArticleId(articleId)) {
    return "This article selection is not valid. Return to the catalogue and choose it again.";
  }
  if (availabilityStatus === "insufficient_source_information") {
    return "This source does not contain enough permitted information to ground a draft.";
  }
  return "Current source permissions do not allow AI generation for this article.";
}

function generationFailure(
  result: Extract<GenerationResult, { status: "error" }>,
): GenerationFailure {
  const category =
    result.reason === "authentication_required"
      ? "authentication"
      : result.reason === "generation_restricted"
        ? "permissions"
        : result.reason === "invalid_request"
          ? "validation"
          : result.reason === "request_conflict"
            ? "conflict"
            : result.reason === "usage_limited"
              ? "usage_limit"
              : result.reason === "timeout"
                ? "timeout"
                : result.reason === "network_failure"
                  ? "network"
                  : "service";
  const retryable =
    category === "conflict" ||
    category === "usage_limit" ||
    category === "timeout" ||
    category === "network" ||
    category === "service";

  return {
    category,
    message: result.message,
    retryAfterSeconds: result.retryAfterSeconds,
    retryable,
  };
}

export function GenerationControls({
  articleId,
  availabilityStatus,
  generationAllowed,
}: GenerationControlsProps) {
  const router = useRouter();
  const [tone, setTone] = useState<GenerationTone>("professional");
  const [length, setLength] = useState<GenerationLength>("medium");
  const [editorDraft, setEditorDraft] = useState<
    Extract<GenerationResult, { status: "success" }>["data"] | null
  >(null);
  const [retrySeconds, setRetrySeconds] = useState(0);
  const statusRef = useRef<HTMLDivElement>(null);
  const requestKeyRef = useRef<{ key: string; signature: string } | null>(null);
  const executeGeneration = useCallback(
    async (
      request: { article_id: string; tone: GenerationTone; length: GenerationLength },
      { signal }: { signal: AbortSignal },
    ): Promise<
      GenerationOperationResult<Extract<GenerationResult, { status: "success" }>["data"]>
    > => {
      const signature = `${request.article_id}:${request.tone}:${request.length}`;
      if (!requestKeyRef.current || requestKeyRef.current.signature !== signature) {
        requestKeyRef.current = { key: createGenerationRequestKey(), signature };
      }
      const result = await generateLinkedInDraft(request, requestKeyRef.current.key, signal);
      if (result.status === "success") {
        return { data: result.data, status: "success" };
      }
      if (result.reason === "request_conflict" && result.retryAfterSeconds === null) {
        requestKeyRef.current = null;
      }
      return { error: generationFailure(result), status: "error" };
    },
    [],
  );
  const generation = useTextGeneration(executeGeneration);
  const validArticle = articleId !== null && isArticleId(articleId);
  const isAvailable = validArticle && generationAllowed && availabilityStatus === "available";
  const controlsDisabled = !isAvailable || generation.isBusy;

  useEffect(() => {
    if (generation.state.phase === "completed" || generation.state.phase === "failed") {
      statusRef.current?.focus();
    }
  }, [generation.state.phase]);

  useEffect(() => {
    if (retrySeconds <= 0) {
      return;
    }

    const timer = window.setInterval(() => {
      setRetrySeconds((current) => Math.max(0, current - 1));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [retrySeconds]);

  function resetRequestIdentity() {
    requestKeyRef.current = null;
    generation.reset();
  }

  function updateTone(value: GenerationTone) {
    setTone(value);
    resetRequestIdentity();
  }

  function updateLength(value: GenerationLength) {
    setLength(value);
    resetRequestIdentity();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isAvailable || !articleId || !isGenerationTone(tone) || !isGenerationLength(length)) {
      return;
    }
    if (retrySeconds > 0) {
      return;
    }
    handleRunResult(await generation.start({ article_id: articleId, tone, length }));
  }

  function handleRunResult(
    run: GenerationRunResult<Extract<GenerationResult, { status: "success" }>["data"]>,
  ) {
    if (!run.accepted || !run.applied) {
      return;
    }
    if (run.outcome.status === "success") {
      setEditorDraft(run.outcome.data);
      return;
    }
    if (run.outcome.error.category === "authentication") {
      router.replace("/login?reason=session_expired");
      router.refresh();
      return;
    }
    if (run.outcome.error.retryAfterSeconds) {
      setRetrySeconds(run.outcome.error.retryAfterSeconds);
    }
  }

  async function retryGeneration() {
    if (retrySeconds > 0) {
      return;
    }
    handleRunResult(await generation.retry());
  }

  const unavailable = unavailableMessage(articleId, availabilityStatus);

  return (
    <>
      <Card className="scroll-mt-24" id="generation-controls" tone="muted">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              Draft preferences
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-emerald-950">
              Configure your LinkedIn draft.
            </h2>
            <p className="mt-3 text-sm leading-6 text-emerald-950/70" id="generation-help">
              Choose a tone and length, then make one deliberate generation request. The backend
              rechecks your session, source rights, and preferences before OpenAI is contacted.
            </p>
          </div>
          <span className="rounded-full border border-emerald-950/10 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-950/65">
            Defaults: Professional and Medium
          </span>
        </div>

        {!isAvailable ? (
          <div
            aria-live="polite"
            className="mt-6 rounded-2xl border border-amber-700/20 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950"
            id="generation-unavailable"
            role="status"
          >
            <strong>Generation unavailable:</strong> {unavailable}
          </div>
        ) : null}

        <form
          aria-busy={generation.isBusy}
          aria-describedby={
            isAvailable ? "generation-help" : "generation-help generation-unavailable"
          }
          className="mt-7 space-y-7"
          noValidate
          onSubmit={handleSubmit}
        >
          <ToneSelector disabled={controlsDisabled} onChange={updateTone} value={tone} />
          <LengthSelector disabled={controlsDisabled} onChange={updateLength} value={length} />

          <GenerationStatus
            completionDetails={
              generation.state.phase === "completed" ? (
                <>
                  {generation.state.result.validation_warnings.length > 0 ? (
                    <p className="mt-2 font-semibold text-amber-900">
                      Automated checks added {generation.state.result.validation_warnings.length}{" "}
                      review{" "}
                      {generation.state.result.validation_warnings.length === 1
                        ? "warning"
                        : "warnings"}
                      .
                    </p>
                  ) : null}
                  <p className="mt-2 break-all font-mono text-xs text-emerald-950/70">
                    Generation ID: {generation.state.result.generation_id}
                  </p>
                </>
              ) : null
            }
            onRetry={() => void retryGeneration()}
            retrySeconds={retrySeconds}
            state={generation.state}
            statusRef={statusRef}
          />

          <div className="flex flex-col gap-3 border-t border-emerald-950/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-xs leading-5 text-emerald-950/70">
              Generation creates a private AI draft for review. It never publishes automatically and
              it never sends an OpenAI credential to your browser.
            </p>
            <Button
              aria-describedby={isAvailable ? "generation-help" : "generation-unavailable"}
              className="w-full shrink-0 sm:w-auto"
              disabled={!isAvailable || generation.isBusy || retrySeconds > 0}
              type="submit"
            >
              {generation.state.phase === "submitting"
                ? "Submitting request..."
                : generation.state.phase === "processing"
                  ? "Generating draft..."
                  : retrySeconds > 0
                    ? "Generation temporarily limited"
                    : "Generate LinkedIn draft"}
            </Button>
          </div>
        </form>
      </Card>

      {editorDraft ? <LinkedInEditor draft={toDraftEditorDocument(editorDraft)} /> : null}
    </>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, type RefObject, useEffect, useRef, useState } from "react";

import { LengthSelector } from "@/components/generation/length-selector";
import { ToneSelector } from "@/components/generation/tone-selector";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  createGenerationRequestKey,
  generateLinkedInDraft,
  type GenerationResult,
} from "@/lib/generation-api";
import type { ArticleGenerationStatus } from "@/types/article";
import {
  isArticleId,
  isGenerationLength,
  isGenerationTone,
  type GenerationLength,
  type GenerationTone,
} from "@/types/generation";

type GenerationControlsProps = {
  articleId: string | null;
  availabilityStatus: ArticleGenerationStatus | "missing";
  generationAllowed: boolean;
};

type Feedback =
  | { kind: "error"; message: string }
  | {
      generationId: string;
      kind: "success";
      warningCount: number;
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

function FeedbackPanel({
  feedback,
  feedbackRef,
}: {
  feedback: Feedback;
  feedbackRef: RefObject<HTMLDivElement | null>;
}) {
  if (feedback.kind === "error") {
    return (
      <div
        aria-live="assertive"
        className="rounded-2xl border border-red-700/20 bg-red-50 px-4 py-4 text-sm leading-6 text-red-900 outline-none"
        ref={feedbackRef}
        role="alert"
        tabIndex={-1}
      >
        <p className="font-semibold">The draft could not be generated.</p>
        <p className="mt-1">{feedback.message}</p>
      </div>
    );
  }

  return (
    <div
      aria-live="polite"
      className="rounded-2xl border border-emerald-700/20 bg-emerald-50 px-4 py-4 text-sm leading-6 text-emerald-950 outline-none"
      ref={feedbackRef}
      role="status"
      tabIndex={-1}
    >
      <p className="font-semibold">Your private draft has been generated.</p>
      <p className="mt-1">
        It requires human review before it is copied, saved, exported, or used. Nothing has been
        published to LinkedIn.
      </p>
      {feedback.warningCount > 0 ? (
        <p className="mt-2 font-semibold text-amber-900">
          Automated checks added {feedback.warningCount} review{" "}
          {feedback.warningCount === 1 ? "warning" : "warnings"}.
        </p>
      ) : null}
      <p className="mt-2 font-mono text-xs text-emerald-950/50">
        Generation ID: {feedback.generationId}
      </p>
    </div>
  );
}

export function GenerationControls({
  articleId,
  availabilityStatus,
  generationAllowed,
}: GenerationControlsProps) {
  const router = useRouter();
  const [tone, setTone] = useState<GenerationTone>("professional");
  const [length, setLength] = useState<GenerationLength>("medium");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [retrySeconds, setRetrySeconds] = useState(0);
  const activeRequestRef = useRef(false);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const requestKeyRef = useRef<{ key: string; signature: string } | null>(null);
  const validArticle = articleId !== null && isArticleId(articleId);
  const isAvailable = validArticle && generationAllowed && availabilityStatus === "available";
  const controlsDisabled = !isAvailable || isSubmitting;

  useEffect(() => {
    if (feedback) {
      feedbackRef.current?.focus();
    }
  }, [feedback]);

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
    setFeedback(null);
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
    if (activeRequestRef.current) {
      return;
    }
    if (!isAvailable || !articleId || !isGenerationTone(tone) || !isGenerationLength(length)) {
      setFeedback({
        kind: "error",
        message: unavailableMessage(articleId, availabilityStatus),
      });
      return;
    }
    if (retrySeconds > 0) {
      setFeedback({
        kind: "error",
        message: `Please wait ${retrySeconds} ${retrySeconds === 1 ? "second" : "seconds"} before trying again.`,
      });
      return;
    }

    activeRequestRef.current = true;
    setIsSubmitting(true);
    setFeedback(null);
    const signature = `${articleId}:${tone}:${length}`;
    if (!requestKeyRef.current || requestKeyRef.current.signature !== signature) {
      requestKeyRef.current = { key: createGenerationRequestKey(), signature };
    }

    let result: GenerationResult;
    try {
      result = await generateLinkedInDraft(
        { article_id: articleId, tone, length },
        requestKeyRef.current.key,
      );
    } finally {
      activeRequestRef.current = false;
      setIsSubmitting(false);
    }

    if (result.status === "success") {
      setFeedback({
        generationId: result.data.generation_id,
        kind: "success",
        warningCount: result.data.validation_warnings.length,
      });
      return;
    }

    if (result.reason === "authentication_required") {
      router.replace("/login?reason=session_expired");
      router.refresh();
      return;
    }
    if (result.reason === "request_conflict" && result.retryAfterSeconds === null) {
      requestKeyRef.current = null;
    }
    if (result.retryAfterSeconds) {
      setRetrySeconds(result.retryAfterSeconds);
    }
    setFeedback({ kind: "error", message: result.message });
  }

  const unavailable = unavailableMessage(articleId, availabilityStatus);

  return (
    <Card className="scroll-mt-24" id="generation-controls" tone="muted">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
            Draft preferences
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-emerald-950">
            Configure your LinkedIn draft.
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-950/60" id="generation-help">
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
        aria-busy={isSubmitting}
        aria-describedby={
          isAvailable ? "generation-help" : "generation-help generation-unavailable"
        }
        className="mt-7 space-y-7"
        noValidate
        onSubmit={handleSubmit}
      >
        <ToneSelector disabled={controlsDisabled} onChange={updateTone} value={tone} />
        <LengthSelector disabled={controlsDisabled} onChange={updateLength} value={length} />

        {feedback ? <FeedbackPanel feedback={feedback} feedbackRef={feedbackRef} /> : null}

        <div className="flex flex-col gap-3 border-t border-emerald-950/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-xs leading-5 text-emerald-950/50">
            Generation creates a private AI draft for review. It never publishes automatically and
            it never sends an OpenAI credential to your browser.
          </p>
          <Button
            aria-describedby={isAvailable ? "generation-help" : "generation-unavailable"}
            className="w-full shrink-0 sm:w-auto"
            disabled={!isAvailable || isSubmitting || retrySeconds > 0}
            type="submit"
          >
            {isSubmitting
              ? "Generating draft..."
              : retrySeconds > 0
                ? `Try again in ${retrySeconds}s`
                : "Generate LinkedIn draft"}
          </Button>
        </div>

        <p aria-live="polite" className="sr-only">
          {isSubmitting ? "Your LinkedIn draft generation request is being processed." : ""}
        </p>
      </form>
    </Card>
  );
}

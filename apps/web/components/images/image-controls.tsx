"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { GenerationStatus } from "@/components/generation/generation-status";
import { ImagePreferenceControls } from "@/components/images/image-preference-controls";
import {
  ImageVersionGallery,
  type DisplayImageVersion,
} from "@/components/images/image-version-gallery";
import { Button } from "@/components/ui/button";
import { useImageGeneration } from "@/hooks/use-image-generation";
import { createImageRequestKey, requestImageGeneration } from "@/lib/image-generation-api";
import type { GenerationRunResult } from "@/hooks/use-generation";
import type {
  ImageAspectRatio,
  ImageComposition,
  ImageGenerationRequest,
  ImageStyle,
  ImageVersion,
} from "@/types/image-generation";
import { IMAGE_STYLES } from "@/types/image-generation";
import type { PreviewImageSelection } from "@/types/preview";

type ImageControlsProps = {
  generationId: string;
  onSelectionChange: (image: PreviewImageSelection) => void;
  sourceTitle: string;
};

export function ImageControls({
  generationId,
  onSelectionChange,
  sourceTitle,
}: ImageControlsProps) {
  const [style, setStyle] = useState<ImageStyle>("editorial_illustration");
  const [aspectRatio, setAspectRatio] = useState<ImageAspectRatio>("landscape");
  const [composition, setComposition] = useState<ImageComposition>("balanced");
  const [versions, setVersions] = useState<DisplayImageVersion[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [retrySeconds, setRetrySeconds] = useState(0);
  const statusRef = useRef<HTMLDivElement>(null);
  const requestKeyRef = useRef<{ key: string; signature: string } | null>(null);
  const execute = useCallback(
    async (request: ImageGenerationRequest, { signal }: { signal: AbortSignal }) => {
      const context =
        request.action === "generate" ? request.generation_id : request.parent_image_id;
      const signature = `${request.action}:${context}:${request.style}:${request.aspect_ratio}:${request.composition}`;
      if (!requestKeyRef.current || requestKeyRef.current.signature !== signature) {
        requestKeyRef.current = { key: createImageRequestKey(), signature };
      }
      return requestImageGeneration(request, requestKeyRef.current.key, signal);
    },
    [],
  );
  const generation = useImageGeneration(execute);

  useEffect(() => {
    if (generation.state.phase === "completed" || generation.state.phase === "failed") {
      statusRef.current?.focus();
    }
  }, [generation.state.phase]);

  useEffect(() => {
    if (retrySeconds <= 0) return;
    const timer = window.setInterval(
      () => setRetrySeconds((current) => Math.max(0, current - 1)),
      1_000,
    );
    return () => window.clearInterval(timer);
  }, [retrySeconds]);

  function resetRequestIdentity() {
    requestKeyRef.current = null;
    generation.reset();
  }

  function updateStyle(value: ImageStyle) {
    setStyle(value);
    resetRequestIdentity();
  }

  function updateAspectRatio(value: ImageAspectRatio) {
    setAspectRatio(value);
    resetRequestIdentity();
  }

  function updateComposition(value: ImageComposition) {
    setComposition(value);
    resetRequestIdentity();
  }

  function selectVersion(version: DisplayImageVersion) {
    setSelectedId(version.id);
    onSelectionChange({ altText: version.altText, id: version.id });
  }

  function applyResult(run: GenerationRunResult<ImageVersion>) {
    if (!run.accepted || !run.applied) return;
    if (run.outcome.status === "error") {
      if (run.outcome.error.retryAfterSeconds) {
        setRetrySeconds(run.outcome.error.retryAfterSeconds);
      }
      return;
    }

    const label = IMAGE_STYLES.find((option) => option.value === style)?.label ?? "News";
    const version: DisplayImageVersion = {
      ...run.outcome.data,
      altText: `AI-generated ${label.toLowerCase()} illustration for ${sourceTitle}`,
    };
    setVersions((current) =>
      current.some((item) => item.id === version.id) ? current : [...current, version],
    );
    selectVersion(version);
    requestKeyRef.current = null;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (generation.isBusy || retrySeconds > 0) return;
    const common = { aspect_ratio: aspectRatio, composition, style };
    const request: ImageGenerationRequest =
      versions.length === 0
        ? { action: "generate", generation_id: generationId, ...common }
        : {
            action: "regenerate",
            parent_image_id: selectedId || versions[versions.length - 1].id,
            ...common,
          };
    applyResult(await generation.start(request));
  }

  async function retry() {
    if (retrySeconds > 0) return;
    applyResult(await generation.retry());
  }

  const hasVersions = versions.length > 0;
  return (
    <section
      aria-labelledby="image-controls-title"
      className="mt-6 rounded-2xl border border-emerald-950/10 bg-stone-100/70 p-4 sm:p-5"
    >
      <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
        Optional illustration
      </p>
      <h3 className="mt-2 text-lg font-semibold text-emerald-950" id="image-controls-title">
        Generate an AI illustration
      </h3>
      <p className="mt-2 text-xs leading-5 text-emerald-950/70" id="image-generation-help">
        Choose from the approved styles. The backend rechecks source rights and safety rules. It
        creates an illustration, not authentic news photography, and never publishes it.
      </p>

      <form aria-busy={generation.isBusy} className="mt-5 space-y-5" onSubmit={submit}>
        <ImagePreferenceControls
          aspectRatio={aspectRatio}
          composition={composition}
          disabled={generation.isBusy}
          onAspectRatioChange={updateAspectRatio}
          onCompositionChange={updateComposition}
          onStyleChange={updateStyle}
          style={style}
        />

        <GenerationStatus
          completionDetails={
            generation.state.phase === "completed" ? (
              <p className="mt-2 text-xs text-emerald-950/70">
                Safety status: {generation.state.result.safetyStatus}. Human review remains
                required.
              </p>
            ) : undefined
          }
          onRetry={() => void retry()}
          retrySeconds={retrySeconds}
          state={generation.state}
          statusRef={statusRef}
        />

        {hasVersions ? (
          <ImageVersionGallery
            disabled={generation.isBusy}
            onSelect={selectVersion}
            selectedId={selectedId}
            versions={versions}
          />
        ) : null}

        <div className="flex flex-col gap-3 border-t border-emerald-950/10 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-emerald-950/70">
            Each request may use your generation allowance. Regeneration keeps every earlier
            version.
          </p>
          <Button
            aria-describedby="image-generation-help"
            className="w-full shrink-0 sm:w-auto"
            disabled={generation.isBusy || retrySeconds > 0}
            type="submit"
          >
            {generation.state.phase === "submitting"
              ? "Submitting request..."
              : generation.state.phase === "processing"
                ? "Generating illustration..."
                : hasVersions
                  ? "Regenerate image"
                  : "Generate image"}
          </Button>
        </div>
      </form>
    </section>
  );
}

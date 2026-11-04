"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CharacterCounter } from "@/components/editor/character-counter";
import { ContentExportActions } from "@/components/export/content-export-actions";
import { ImageControls } from "@/components/images/image-controls";
import { LinkedInPreview } from "@/components/preview/linkedin-preview";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useDraftEditor } from "@/hooks/use-draft-editor";
import { saveGeneratedDraft } from "@/lib/draft-persistence";
import type { DraftEditorDocument } from "@/types/draft";
import type { PreviewImageSelection } from "@/types/preview";

type LinkedInEditorProps = {
  draft: DraftEditorDocument | null;
  origin?: "generated" | "saved";
  selectedImage?: PreviewImageSelection | null;
};

export function LinkedInEditor({
  draft,
  origin = "generated",
  selectedImage = null,
}: LinkedInEditorProps) {
  const router = useRouter();
  const editor = useDraftEditor(draft);
  const activeDraft = editor.activeDocument;
  const savedDraft = origin === "saved";
  const [generatedSelection, setGeneratedSelection] = useState<{
    generationId: string;
    image: PreviewImageSelection;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (!activeDraft) {
    return (
      <Card className="scroll-mt-24" id="draft-editor">
        <div role="alert">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
            Draft unavailable
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-emerald-950">
            The generated draft could not be loaded.
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-950/70">
            Return to the generation controls and request a valid draft. No content has been saved
            or published.
          </p>
        </div>
      </Card>
    );
  }

  const emptyDraft = editor.editedText.trim().length === 0;
  const activeImage =
    generatedSelection?.generationId === activeDraft.generationId
      ? generatedSelection.image
      : selectedImage;
  const activeGenerationId = activeDraft.generationId;
  const activeSourceTitle = activeDraft.sourceTitle;

  async function saveToLibrary() {
    setSaving(true);
    setSaveError(null);
    const result = await saveGeneratedDraft({
      editedText: editor.editedText,
      generationId: activeGenerationId,
      selectedImageId: activeImage?.id ?? null,
      title: activeSourceTitle,
    });
    if (result.status === "success") {
      router.push(`/library/${result.data.id}`);
      router.refresh();
      return;
    }
    setSaveError(result.message);
    setSaving(false);
  }

  return (
    <Card className="scroll-mt-24" id="draft-editor">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
            {savedDraft ? "Saved draft" : "AI-assisted draft"}
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-emerald-950">
            {savedDraft ? "Continue reviewing your saved draft." : "Review and edit before use."}
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-950/70" id="draft-editor-help">
            This content may contain errors. Edit the wording, then verify its claims, source
            reference, and context. Nothing is saved or published automatically.
          </p>
        </div>
        <span
          aria-live="polite"
          className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
            editor.hasUnsavedChanges
              ? "border-amber-700/20 bg-amber-50 text-amber-900"
              : "border-emerald-700/20 bg-emerald-50 text-emerald-800"
          }`}
          role="status"
        >
          {editor.hasUnsavedChanges
            ? "Unsaved local edits"
            : savedDraft
              ? "Saved version loaded"
              : "Generated draft loaded"}
        </span>
      </div>

      {editor.pendingDocument ? (
        <div
          className="mt-6 rounded-2xl border border-amber-700/20 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-950"
          role="alert"
        >
          <p className="font-semibold">A newer generated draft is available.</p>
          <p className="mt-1">
            Your local edits were not overwritten. Choose whether to replace them with the newer
            draft or keep editing the current version.
          </p>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <Button onClick={editor.replaceWithPending} type="button" variant="secondary">
              Replace my edits
            </Button>
            <Button onClick={editor.keepCurrentEdits} type="button" variant="quiet">
              Keep my edits
            </Button>
          </div>
        </div>
      ) : null}

      <div className="mt-7 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <section aria-labelledby="editor-input-title">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <label
              className="text-base font-semibold text-emerald-950"
              htmlFor="linkedin-draft-editor"
              id="editor-input-title"
            >
              LinkedIn draft text
            </label>
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">
              Editable
            </span>
          </div>
          <textarea
            aria-describedby="draft-editor-help draft-editor-format-help"
            className="mt-3 min-h-80 w-full resize-y rounded-2xl border border-emerald-950/15 bg-white px-4 py-4 text-base leading-7 text-emerald-950 shadow-sm transition placeholder:text-emerald-950/65 focus:border-emerald-700 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            id="linkedin-draft-editor"
            onChange={(event) => editor.updateText(event.target.value)}
            placeholder="Add or revise the LinkedIn draft here."
            spellCheck
            value={editor.editedText}
          />
          <p className="mt-2 text-xs leading-5 text-emerald-950/70" id="draft-editor-format-help">
            Line breaks are preserved in the preview. Text is displayed literally, so HTML-like
            content is not executed.
          </p>
          <div className="mt-3 border-t border-emerald-950/10 pt-3">
            <CharacterCounter length={activeDraft.length} text={editor.editedText} />
          </div>
          {emptyDraft ? (
            <p
              className="mt-4 rounded-2xl border border-amber-700/20 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950"
              role="status"
            >
              The draft is empty. Add reviewed text manually or request another generated draft.
            </p>
          ) : null}
          <ImageControls
            generationId={activeDraft.generationId}
            key={activeDraft.generationId}
            onSelectionChange={(image) =>
              setGeneratedSelection({ generationId: activeDraft.generationId, image })
            }
            sourceTitle={activeDraft.sourceTitle}
          />
        </section>

        <LinkedInPreview
          draftText={editor.editedText}
          groundingStatus={activeDraft.groundingStatus}
          image={activeImage}
          source={{
            attribution: activeDraft.sourceAttribution,
            name: activeDraft.sourceName,
            title: activeDraft.sourceTitle,
            url: activeDraft.sourceUrl,
          }}
          warnings={activeDraft.validationWarnings}
        />
      </div>

      <ContentExportActions imageId={activeImage?.id ?? null} text={editor.editedText} />

      {!savedDraft ? (
        <div className="mt-6 border-t border-emerald-950/10 pt-5">
          {saveError ? (
            <p
              className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {saveError}
            </p>
          ) : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-2xl text-xs leading-5 text-emerald-950/70">
              Saving creates a private library copy of your reviewed text and selected image. It
              does not publish anything to LinkedIn.
            </p>
            <Button
              className="w-full shrink-0 sm:w-auto"
              disabled={saving || emptyDraft}
              onClick={() => void saveToLibrary()}
              type="button"
            >
              {saving ? "Saving draft..." : "Save to library"}
            </Button>
          </div>
        </div>
      ) : null}

      <p className="mt-6 border-t border-emerald-950/10 pt-5 text-xs leading-5 text-emerald-950/70">
        {savedDraft
          ? "This saved version is loaded from your private library. New edits remain local until the update controls are added in a separate E7 task. Leaving with local edits triggers a discard warning."
          : "Edits remain on this page until you save them to your private content library. Leaving with local edits triggers a discard warning."}
      </p>
    </Card>
  );
}

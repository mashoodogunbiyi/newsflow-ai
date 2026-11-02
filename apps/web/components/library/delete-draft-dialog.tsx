"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { deleteSavedDraft, type DraftDeletionResult } from "@/lib/draft-deletion";

const errorMessages: Record<Exclude<DraftDeletionResult, { status: "success" }>["reason"], string> =
  {
    authentication_required: "Your session has ended. Sign in again before deleting this draft.",
    not_found: "This draft is no longer available. Return to the library to refresh your list.",
    security_error: "The security check failed. Refresh the page and try again.",
    unavailable: "The draft could not be deleted right now. Please try again.",
  };

export function DeleteDraftDialog({ draftId, title }: { draftId: string; title: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const triggerButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelButton.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !deleting) {
        setOpen(false);
        triggerButton.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [deleting, open]);

  async function confirmDeletion() {
    setDeleting(true);
    setError(null);
    const result = await deleteSavedDraft(draftId);
    if (result.status === "success") {
      router.replace("/library?deleted=1");
      router.refresh();
      return;
    }
    setError(errorMessages[result.reason]);
    setDeleting(false);
  }

  function cancel() {
    setOpen(false);
    setError(null);
    triggerButton.current?.focus();
  }

  return (
    <>
      <Button ref={triggerButton} onClick={() => setOpen(true)} variant="danger">
        Delete draft
      </Button>
      {open ? (
        <div
          aria-labelledby="delete-draft-title"
          aria-describedby="delete-draft-description"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/55 p-4"
          role="dialog"
        >
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-red-700">
              Permanent deletion
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-emerald-950" id="delete-draft-title">
              Delete this saved draft?
            </h2>
            <p className="mt-3 leading-7 text-emerald-950/75" id="delete-draft-description">
              {title} will disappear from your library immediately. Its private history and any
              unreferenced image files will then follow the documented retention process. This
              action has no self-service undo.
            </p>
            {error ? (
              <p
                className="mt-4 rounded-2xl bg-red-50 p-3 text-sm font-medium text-red-800"
                role="alert"
              >
                {error}
              </p>
            ) : null}
            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <Button disabled={deleting} onClick={cancel} ref={cancelButton} variant="secondary">
                Cancel
              </Button>
              <Button disabled={deleting} onClick={confirmDeletion} variant="danger">
                {deleting ? "Deleting..." : "Delete permanently"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

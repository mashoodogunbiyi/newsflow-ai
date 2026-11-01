"use client";

import { useCallback, useEffect, useState } from "react";

import type { DraftEditorDocument } from "@/types/draft";

type EditorSession = {
  activeDocument: DraftEditorDocument | null;
  editedText: string;
  observedGenerationId: string | null;
  originalText: string;
  pendingDocument: DraftEditorDocument | null;
};

function createSession(document: DraftEditorDocument | null): EditorSession {
  return {
    activeDocument: document,
    editedText: document?.generatedText ?? "",
    observedGenerationId: document?.generationId ?? null,
    originalText: document?.generatedText ?? "",
    pendingDocument: null,
  };
}

function isModified(session: EditorSession) {
  return session.editedText !== session.originalText;
}

const UNSAVED_MESSAGE =
  "You have unsaved draft edits. Leave this page and discard those local changes?";

export function useDraftEditor(incomingDocument: DraftEditorDocument | null) {
  const [session, setSession] = useState<EditorSession>(() => createSession(incomingDocument));
  const incomingGenerationId = incomingDocument?.generationId ?? null;

  if (incomingGenerationId !== session.observedGenerationId) {
    if (isModified(session) && session.activeDocument) {
      setSession({
        ...session,
        observedGenerationId: incomingGenerationId,
        pendingDocument: incomingDocument,
      });
    } else {
      setSession(createSession(incomingDocument));
    }
  }

  const hasUnsavedChanges = isModified(session);

  useEffect(() => {
    if (!hasUnsavedChanges) {
      return;
    }

    function warnBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = true;
    }

    function warnBeforeInternalNavigation(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const anchor = target.closest("a");
      if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) {
        return;
      }

      const destination = new URL(anchor.href, window.location.href);
      const current = new URL(window.location.href);
      const leavesEditor =
        destination.origin !== current.origin ||
        destination.pathname !== current.pathname ||
        destination.search !== current.search;
      if (leavesEditor && !window.confirm(UNSAVED_MESSAGE)) {
        event.preventDefault();
        event.stopPropagation();
      }
    }

    window.addEventListener("beforeunload", warnBeforeUnload);
    document.addEventListener("click", warnBeforeInternalNavigation, true);
    return () => {
      window.removeEventListener("beforeunload", warnBeforeUnload);
      document.removeEventListener("click", warnBeforeInternalNavigation, true);
    };
  }, [hasUnsavedChanges]);

  const updateText = useCallback((value: string) => {
    setSession((current) => ({ ...current, editedText: value }));
  }, []);

  const replaceWithPending = useCallback(() => {
    setSession((current) =>
      current.pendingDocument ? createSession(current.pendingDocument) : current,
    );
  }, []);

  const keepCurrentEdits = useCallback(() => {
    setSession((current) => ({ ...current, pendingDocument: null }));
  }, []);

  return {
    activeDocument: session.activeDocument,
    editedText: session.editedText,
    hasUnsavedChanges,
    keepCurrentEdits,
    pendingDocument: session.pendingDocument,
    replaceWithPending,
    updateText,
  };
}

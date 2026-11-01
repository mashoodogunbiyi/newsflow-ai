"use client";

import { ErrorState } from "@/components/ui/error-state";

export default function WorkspaceError({
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <ErrorState
      description="We could not display this workspace page. No private content was changed."
      onRetry={retry}
      title="This page could not be loaded."
    />
  );
}

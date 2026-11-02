import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LinkedInEditor } from "@/components/editor/linkedin-editor";
import { LibraryErrorState } from "@/components/library/library-error-state";
import { VersionHistory } from "@/components/library/version-history";
import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { getSavedDraft, getSavedDraftVersions } from "@/lib/draft-api";
import { toSavedDraftEditorDocument, toSavedDraftImageSelection } from "@/types/library";

export const metadata: Metadata = {
  title: "Saved Draft - NewsFlow AI",
  description: "Continue reviewing a private saved LinkedIn draft.",
};

function formatUpdatedDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default async function SavedDraftPage({ params }: { params: Promise<{ draftId: string }> }) {
  const { draftId } = await params;
  const [result, historyResult] = await Promise.all([
    getSavedDraft(draftId),
    getSavedDraftVersions(draftId),
  ]);

  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("secondary")} href="/library">
            Back to library
          </Link>
        }
        description="Review the saved text, original source, and selected illustration before making further local edits."
        eyebrow="Content Library"
        title="Continue editing your saved draft."
      />

      <div className="mt-10">
        {result.status === "error" ? (
          result.reason === "authentication_required" ? (
            redirect("/login?reason=authentication_required")
          ) : (
            <LibraryErrorState reason={result.reason} />
          )
        ) : (
          <div className="space-y-6">
            <Card
              className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between"
              tone="muted"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone="success">Saved</StatusBadge>
                  <span className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/65">
                    Version {result.data.version}
                  </span>
                </div>
                <h2 className="mt-3 truncate text-xl font-semibold text-emerald-950">
                  {result.data.title?.trim() || result.data.source.title}
                </h2>
                <p className="mt-2 text-sm text-emerald-950/70">
                  Last modified {formatUpdatedDate(result.data.updated_at)} UTC
                </p>
              </div>
              <a
                className={buttonStyles("secondary")}
                href={result.data.source.url}
                rel="noopener noreferrer"
                target="_blank"
              >
                Review original source
              </a>
            </Card>
            <LinkedInEditor
              draft={toSavedDraftEditorDocument(result.data)}
              origin="saved"
              selectedImage={toSavedDraftImageSelection(result.data)}
            />
            {historyResult.status === "success" ? (
              <VersionHistory
                currentVersion={result.data.version}
                draftId={result.data.id}
                versions={historyResult.data.items}
              />
            ) : (
              <Card role="status" tone="muted">
                <h2 className="text-lg font-semibold text-emerald-950">
                  Version history is temporarily unavailable.
                </h2>
                <p className="mt-2 text-sm text-emerald-950/70">
                  Your current saved draft is still available. Refresh this page to try loading its
                  history again.
                </p>
              </Card>
            )}
          </div>
        )}
      </div>
    </>
  );
}

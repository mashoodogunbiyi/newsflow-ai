import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LibraryErrorState } from "@/components/library/library-error-state";
import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { getSavedDraftVersion } from "@/lib/draft-api";

export const metadata: Metadata = {
  title: "Draft History - NewsFlow AI",
  description: "Review one immutable saved LinkedIn draft version.",
};

const CHANGE_LABELS = {
  initial_save: "Initial save",
  manual_edit: "Manual edit",
  text_regeneration: "Text regeneration",
  image_selection: "Image selection",
  image_regeneration: "Image regeneration",
  metadata_update: "Title update",
  version_restoration: "Version restored",
} as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default async function SavedDraftVersionPage({
  params,
}: {
  params: Promise<{ draftId: string; versionId: string }>;
}) {
  const { draftId, versionId } = await params;
  const result = await getSavedDraftVersion(draftId, versionId);

  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("secondary")} href={`/library/${draftId}`}>
            Back to current draft
          </Link>
        }
        description="Historical entries are read-only. Your current saved work has not been changed."
        eyebrow="Version History"
        title="Review an earlier draft state."
      />
      <div className="mt-10">
        {result.status === "error" ? (
          result.reason === "authentication_required" ? (
            redirect("/login?reason=authentication_required")
          ) : (
            <LibraryErrorState reason={result.reason} />
          )
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge>{CHANGE_LABELS[result.data.change_type]}</StatusBadge>
                <span className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/65">
                  Version {result.data.version_number}
                </span>
              </div>
              <h2 className="mt-5 text-xl font-semibold text-emerald-950">
                {result.data.title?.trim() || result.data.source.title}
              </h2>
              <p className="mt-2 text-sm text-emerald-950/65">
                Recorded {formatDate(result.data.created_at)} UTC
              </p>
              <div className="mt-6 whitespace-pre-wrap rounded-3xl border border-emerald-950/10 bg-emerald-50/50 p-5 text-sm leading-7 text-emerald-950 sm:p-7">
                {result.data.edited_text}
              </div>
              {result.data.selected_image ? (
                <figure className="mt-6 overflow-hidden rounded-3xl border border-emerald-950/10">
                  {/* The gateway applies session and object-level checks before returning bytes. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    alt={result.data.selected_image.alt_text || "Historical AI illustration"}
                    className="h-auto w-full object-cover"
                    src={`/api/images/${result.data.selected_image.id}/content`}
                  />
                </figure>
              ) : null}
            </Card>
            <Card className="h-fit" tone="muted">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                Source preserved
              </p>
              <h2 className="mt-3 font-semibold text-emerald-950">{result.data.source.title}</h2>
              <p className="mt-3 text-sm leading-6 text-emerald-950/70">
                {result.data.source.attribution}
              </p>
              <a
                className={`${buttonStyles("secondary")} mt-5 w-full`}
                href={result.data.source.url}
                rel="noopener noreferrer"
                target="_blank"
              >
                Review original source
              </a>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}

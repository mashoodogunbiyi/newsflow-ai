import Link from "next/link";

import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { SavedDraftVersion } from "@/types/library";

const CHANGE_LABELS: Record<SavedDraftVersion["change_type"], string> = {
  initial_save: "Initial save",
  manual_edit: "Manual edit",
  text_regeneration: "Text regeneration",
  image_selection: "Image selection",
  image_regeneration: "Image regeneration",
  metadata_update: "Title update",
  version_restoration: "Version restored",
};

function formatVersionDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

type VersionHistoryProps = {
  currentVersion: number;
  draftId: string;
  versions: SavedDraftVersion[];
};

export function VersionHistory({ currentVersion, draftId, versions }: VersionHistoryProps) {
  return (
    <Card aria-labelledby="version-history-heading" className="overflow-hidden p-0">
      <div className="border-b border-emerald-950/10 px-5 py-5 sm:px-7">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
          Change record
        </p>
        <h2 className="mt-2 text-xl font-semibold text-emerald-950" id="version-history-heading">
          Version history
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-950/70">
          Each entry is read-only. Restoring an earlier entry creates a new version and keeps this
          record intact.
        </p>
      </div>
      <ol className="divide-y divide-emerald-950/10">
        {versions.map((version) => {
          const isCurrent = version.version_number === currentVersion;
          return (
            <li className="px-5 py-5 sm:px-7" key={version.id}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/65">
                      Version {version.version_number}
                    </span>
                    <StatusBadge tone={isCurrent ? "success" : "neutral"}>
                      {isCurrent ? "Current" : CHANGE_LABELS[version.change_type]}
                    </StatusBadge>
                    {isCurrent ? (
                      <span className="text-xs font-medium text-emerald-950/60">
                        {CHANGE_LABELS[version.change_type]}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm text-emerald-950/70">
                    {formatVersionDate(version.created_at)} UTC
                  </p>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-emerald-950/80">
                    {version.edited_text}
                  </p>
                </div>
                <Link
                  className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-full border border-emerald-950/15 bg-white px-5 py-2.5 text-sm font-semibold text-emerald-950 transition hover:border-emerald-950/30 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                  href={`/library/${draftId}/versions/${version.id}`}
                >
                  Review version {version.version_number}
                </Link>
              </div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

import Link from "next/link";

import { DraftThumbnail } from "@/components/library/draft-thumbnail";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { SavedDraft } from "@/types/library";

function formatUpdatedDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    timeZone: "UTC",
    timeZoneName: "short",
    year: "numeric",
  }).format(new Date(value));
}

function draftExcerpt(value: string) {
  const cleaned = value.replaceAll(/\s+/g, " ").trim();
  return cleaned.length > 180 ? `${cleaned.slice(0, 177).trimEnd()}...` : cleaned;
}

export function DraftCard({ draft }: { draft: SavedDraft }) {
  const title = draft.title?.trim() || draft.source.title;
  const excerpt = draftExcerpt(draft.edited_text);

  return (
    <Card className="flex h-full flex-col overflow-hidden p-0 sm:p-0">
      <article className="flex h-full flex-col" aria-labelledby={`draft-${draft.id}-title`}>
        <DraftThumbnail image={draft.selected_image} />
        <div className="flex flex-1 flex-col p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <StatusBadge tone="success">Saved</StatusBadge>
            <span className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/65">
              Version {draft.version}
            </span>
          </div>

          <h2
            className="mt-4 text-xl font-semibold leading-7 tracking-[-0.025em] text-emerald-950"
            id={`draft-${draft.id}-title`}
          >
            {title}
          </h2>
          <p className="mt-3 line-clamp-4 text-sm leading-6 text-emerald-950/70">{excerpt}</p>

          <section
            aria-label="Saved draft source"
            className="mt-5 border-t border-emerald-950/10 pt-4"
          >
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
              Original source
            </p>
            <p className="mt-2 line-clamp-2 text-sm font-semibold leading-6 text-emerald-950">
              {draft.source.title}
            </p>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-emerald-950/65">
              {draft.source.attribution}
            </p>
          </section>

          <p className="mt-5 text-xs leading-5 text-emerald-950/65">
            Last modified:{" "}
            <time dateTime={draft.updated_at}>{formatUpdatedDate(draft.updated_at)}</time>
          </p>

          <div className="mt-auto flex flex-col gap-2 pt-6 sm:flex-row">
            <Link
              aria-label={`Open saved draft: ${title}`}
              className={`${buttonStyles("primary")} flex-1`}
              href={`/library/${encodeURIComponent(draft.id)}`}
              prefetch={false}
            >
              Open draft
            </Link>
            <a
              aria-label={`View original source for ${draft.source.title}`}
              className={`${buttonStyles("secondary")} flex-1`}
              href={draft.source.url}
              rel="noopener noreferrer"
              target="_blank"
            >
              View source
            </a>
          </div>
        </div>
      </article>
    </Card>
  );
}

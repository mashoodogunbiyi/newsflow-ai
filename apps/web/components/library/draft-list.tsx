import { DraftCard } from "@/components/library/draft-card";
import type { SavedDraft } from "@/types/library";

export function DraftList({ drafts }: { drafts: SavedDraft[] }) {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {drafts.map((draft) => (
        <DraftCard draft={draft} key={draft.id} />
      ))}
    </div>
  );
}

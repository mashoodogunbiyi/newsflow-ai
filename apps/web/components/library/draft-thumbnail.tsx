"use client";

import Image from "next/image";
import { useState } from "react";

import type { SavedDraftImage } from "@/types/library";

function ThumbnailFallback({ unavailable = false }: { unavailable?: boolean }) {
  return (
    <div
      className="grid aspect-[16/9] min-h-36 place-items-center bg-emerald-950/[0.045] px-5 text-center"
      data-testid={unavailable ? "draft-thumbnail-error" : "draft-thumbnail-empty"}
      role={unavailable ? "status" : undefined}
    >
      <div>
        <span
          aria-hidden="true"
          className="mx-auto grid h-10 w-10 place-items-center rounded-2xl border border-emerald-950/10 bg-white text-emerald-800 shadow-sm"
        >
          {unavailable ? "!" : "NF"}
        </span>
        <p className="mt-3 text-xs font-semibold text-emerald-950/70">
          {unavailable ? "Private illustration unavailable" : "Text-only saved draft"}
        </p>
      </div>
    </div>
  );
}

export function DraftThumbnail({ image }: { image: SavedDraftImage | null }) {
  const [failed, setFailed] = useState(false);

  if (!image) {
    return <ThumbnailFallback />;
  }
  if (failed) {
    return <ThumbnailFallback unavailable />;
  }

  return (
    <figure className="relative overflow-hidden border-b border-emerald-950/10">
      <div className="relative aspect-[16/9] min-h-36 bg-emerald-950/5">
        <Image
          alt={image.alt_text?.trim() || "AI-generated illustration for this saved draft."}
          className="object-cover"
          fill
          onError={() => setFailed(true)}
          sizes="(max-width: 639px) 100vw, (max-width: 1279px) 50vw, 33vw"
          src={`/api/images/${encodeURIComponent(image.id)}/content`}
          unoptimized
        />
      </div>
      <figcaption className="absolute bottom-2 left-2 rounded-full border border-amber-900/10 bg-amber-50/95 px-2.5 py-1 text-[0.68rem] font-semibold text-amber-950 shadow-sm">
        AI-generated illustration
      </figcaption>
    </figure>
  );
}
